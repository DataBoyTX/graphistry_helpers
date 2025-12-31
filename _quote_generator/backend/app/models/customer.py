"""Customer model for storing client information."""
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.quote import Quote
    from app.models.order import Order
    from app.models.user import User


class Customer(Base, TimestampMixin):
    """Customer model for storing client/company information."""

    __tablename__ = "customers"

    id: Mapped[uuid_pk]
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100), default="US")

    # Tax information
    tax_id: Mapped[Optional[str]] = mapped_column(String(50))  # VAT number for international
    is_international: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Tracking
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    created_by_user: Mapped["User"] = relationship(back_populates="customers")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="customer")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer {self.company_name}>"

    @property
    def full_address(self) -> str:
        """Return formatted full address."""
        parts = [
            self.address_line1,
            self.address_line2,
            f"{self.city}, {self.state} {self.postal_code}".strip(", "),
            self.country,
        ]
        return "\n".join(p for p in parts if p and p.strip())
