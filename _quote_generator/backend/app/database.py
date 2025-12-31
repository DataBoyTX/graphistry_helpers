"""Database configuration and session management."""
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Type annotations for common column types
uuid_pk = Annotated[
    str,
    mapped_column(String(36), primary_key=True, default=lambda: str(uuid4())),
]
created_at = Annotated[
    datetime,
    mapped_column(DateTime, server_default=func.now()),
]
updated_at = Annotated[
    datetime,
    mapped_column(DateTime, server_default=func.now(), onupdate=func.now()),
]


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
