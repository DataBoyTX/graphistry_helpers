"""Authentication router with Google OAuth."""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.config import Settings, get_settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import GoogleAuthURL, Token
from app.schemas.user import CurrentUser

router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth setup
oauth = OAuth()


def setup_oauth(settings: Settings) -> None:
    """Configure OAuth with Google."""
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": " ".join(settings.google_scopes)},
    )


def create_access_token(user_id: str, settings: Settings) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try to get token from cookie or header
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Get current user if they have admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    try:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            get_current_user(request, db, settings)
        )
    except HTTPException:
        return None


@router.get("/google", response_model=GoogleAuthURL)
async def google_login(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleAuthURL:
    """Get Google OAuth authorization URL."""
    setup_oauth(settings)
    redirect_uri = settings.google_redirect_uri
    authorization_url = await oauth.google.create_authorization_url(redirect_uri)
    # Store state in session for CSRF protection
    request.session["oauth_state"] = authorization_url["state"]
    return GoogleAuthURL(authorization_url=authorization_url["url"])


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    """Handle Google OAuth callback."""
    setup_oauth(settings)

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {str(e)}",
        )

    # Get user info from Google
    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Google",
        )

    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")

    # Find or create user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Check if first user - make them admin
        result = await db.execute(select(User).limit(1))
        is_first_user = result.scalar_one_or_none() is None

        user = User(
            email=email,
            name=name,
            google_id=google_id,
            picture_url=picture,
            role=UserRole.ADMIN if is_first_user else UserRole.USER,
            google_access_token=token.get("access_token"),
            google_refresh_token=token.get("refresh_token"),
        )
        db.add(user)
    else:
        # Update existing user tokens
        user.name = name
        user.picture_url = picture
        user.google_access_token = token.get("access_token")
        if token.get("refresh_token"):
            user.google_refresh_token = token.get("refresh_token")

    await db.commit()
    await db.refresh(user)

    # Create JWT token
    access_token = create_access_token(user.id, settings)

    # Redirect to frontend with token in cookie
    response = RedirectResponse(url=settings.frontend_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@router.get("/me", response_model=CurrentUser)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CurrentUser:
    """Get current authenticated user."""
    return CurrentUser(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        picture_url=current_user.picture_url,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        has_google_tokens=bool(current_user.google_access_token),
    )


@router.post("/logout")
async def logout(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Logout current user by clearing the access token cookie."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
    )
    return {"message": "Logged out successfully"}


@router.post("/dev-login")
async def dev_login(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Development-only login endpoint that creates a session for a test user.

    WARNING: This endpoint is only available in development mode.
    """
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is only available in development mode",
        )

    # Find or create test user
    result = await db.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalar_one_or_none()

    if user is None:
        # Create test user
        user = User(
            email="test@example.com",
            name="Test User",
            google_id="dev-test-user",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Create JWT token
    access_token = create_access_token(user.id, settings)

    # Set cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )

    return {
        "message": "Logged in as test user",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role if isinstance(user.role, str) else user.role.value,
        },
    }
