"""Authentication schemas."""
from pydantic import BaseModel


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    exp: int


class GoogleAuthURL(BaseModel):
    """Google OAuth authorization URL response."""

    authorization_url: str
