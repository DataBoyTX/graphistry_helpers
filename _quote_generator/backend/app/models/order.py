"""Order model for accepted quotes."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.quote import Quote


class OrderStatus(str, Enum):
    """Order status."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class Order(Base, TimestampMixin):
    """Order model - created when a quote is accepted."""

    __tablename__ = "orders"

    id: Mapped[uuid_pk]
    order_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # References
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)

    # Status
    status: Mapped[OrderStatus] = mapped_column(String(20), default=OrderStatus.PENDING)

    # Acceptance details
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    accepted_by: Mapped[Optional[str]] = mapped_column(String(255))  # Customer name/email

    # Financial snapshot (copied from quote at acceptance)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    quote: Mapped["Quote"] = relationship(back_populates="order")
    customer: Mapped["Customer"] = relationship(back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order {self.order_number}>"
