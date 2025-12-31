"""User model for authentication and authorization."""
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.quote import Quote


class UserRole(str, Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    USER = "user"


class User(Base, TimestampMixin):
    """User model for authentication and team management."""

    __tablename__ = "users"

    id: Mapped[uuid_pk]
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.USER)

    # Google OAuth tokens (encrypted in production)
    google_access_token: Mapped[Optional[str]] = mapped_column(Text)
    google_refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    google_token_expiry: Mapped[Optional[str]] = mapped_column(String(50))

    # Profile
    picture_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    customers: Mapped[list["Customer"]] = relationship(back_populates="created_by_user")
    quotes: Mapped[list["Quote"]] = relationship(
        back_populates="created_by_user",
        foreign_keys="Quote.created_by",
    )
    approved_quotes: Mapped[list["Quote"]] = relationship(
        back_populates="approved_by_user",
        foreign_keys="Quote.approved_by",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
