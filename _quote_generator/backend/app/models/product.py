"""Product model for storing products and pricing."""
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.quote import QuoteLineItem


class ProductCategory(str, Enum):
    """Product category types."""

    LICENSE = "license"
    SERVICE = "service"
    TRAINING = "training"
    SUBSCRIPTION = "subscription"


class BillingPeriod(str, Enum):
    """Billing period for recurring products."""

    ONE_TIME = "one-time"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class Product(Base, TimestampMixin):
    """Product model for available products and services."""

    __tablename__ = "products"

    id: Mapped[uuid_pk]
    sku: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Categorization
    category: Mapped[ProductCategory] = mapped_column(
        String(20), default=ProductCategory.SERVICE
    )

    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Billing
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    billing_period: Mapped[BillingPeriod] = mapped_column(
        String(20), default=BillingPeriod.ONE_TIME
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    line_items: Mapped[list["QuoteLineItem"]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return f"<Product {self.name} ({self.sku})>"
