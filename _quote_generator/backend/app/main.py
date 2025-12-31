"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import close_db, init_db
from app.routers import (
    auth_router,
    customers_router,
    dashboard_router,
    orders_router,
    products_router,
    quotes_router,
    users_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler for startup and shutdown."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Quote Generator API - Generate and manage quotes and order forms",
    lifespan=lifespan,
)

# Add session middleware (required for OAuth state)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=3600,  # 1 hour session
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(quotes_router)
app.include_router(orders_router)
app.include_router(dashboard_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}
