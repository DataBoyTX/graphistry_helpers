"""Quote and QuoteLineItem models."""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.product import Product
    from app.models.user import User


class QuoteStatus(str, Enum):
    """Quote workflow status."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TemplateType(str, Enum):
    """Quote template types."""

    US = "us"
    INTERNATIONAL = "international"


class Quote(Base, TimestampMixin):
    """Quote model for customer quotes."""

    __tablename__ = "quotes"

    id: Mapped[uuid_pk]
    quote_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # References
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Status
    status: Mapped[QuoteStatus] = mapped_column(String(20), default=QuoteStatus.DRAFT)

    # Financial
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Template and content
    template_type: Mapped[TemplateType] = mapped_column(
        String(20), default=TemplateType.US
    )
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    valid_until: Mapped[Optional[date]] = mapped_column(Date)

    # Approval workflow
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Google integration
    drive_doc_id: Mapped[Optional[str]] = mapped_column(String(255))
    drive_pdf_id: Mapped[Optional[str]] = mapped_column(String(255))
    gmail_draft_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Timestamps
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="quotes")
    created_by_user: Mapped["User"] = relationship(
        back_populates="quotes", foreign_keys=[created_by]
    )
    approved_by_user: Mapped[Optional["User"]] = relationship(
        back_populates="approved_quotes", foreign_keys=[approved_by]
    )
    line_items: Mapped[list["QuoteLineItem"]] = relationship(
        back_populates="quote",
        cascade="all, delete-orphan",
        order_by="QuoteLineItem.sort_order",
    )
    order: Mapped[Optional["Order"]] = relationship(back_populates="quote")

    def __repr__(self) -> str:
        return f"<Quote {self.quote_number}>"

    def calculate_totals(self) -> None:
        """Recalculate subtotal, tax, and total from line items."""
        self.subtotal = sum(item.line_total for item in self.line_items)

        # Apply discount
        if self.discount_percent > 0:
            self.discount_amount = self.subtotal * (self.discount_percent / 100)
        after_discount = self.subtotal - self.discount_amount

        # Apply tax
        if self.tax_rate > 0:
            self.tax_amount = after_discount * (self.tax_rate / 100)

        self.total = after_discount + self.tax_amount


class QuoteLineItem(Base):
    """Line item for a quote."""

    __tablename__ = "quote_line_items"

    id: Mapped[uuid_pk]
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    product_id: Mapped[Optional[str]] = mapped_column(ForeignKey("products.id"))

    # Item details
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1.00"))
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Ordering
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    quote: Mapped["Quote"] = relationship(back_populates="line_items")
    product: Mapped[Optional["Product"]] = relationship(back_populates="line_items")

    def __repr__(self) -> str:
        return f"<QuoteLineItem {self.description[:30]}>"

    def calculate_total(self) -> None:
        """Calculate line total based on quantity, price, and discount."""
        subtotal = self.quantity * self.unit_price
        if self.discount_percent > 0:
            discount = subtotal * (self.discount_percent / 100)
            self.line_total = subtotal - discount
        else:
            self.line_total = subtotal
