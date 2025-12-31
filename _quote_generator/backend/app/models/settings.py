"""Application settings models stored in database."""
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.user import User


class ApprovalSettings(Base, TimestampMixin):
    """Approval workflow settings."""

    __tablename__ = "approval_settings"

    id: Mapped[uuid_pk]

    # Threshold for requiring approval
    threshold_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("10000.00")
    )

    # Always require approval for international quotes
    require_approval_international: Mapped[bool] = mapped_column(
        Boolean, default=True
    )

    # Default tax rates
    default_us_tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )
    default_international_vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )

    # Default terms and conditions
    default_us_terms: Mapped[Optional[str]] = mapped_column(String(5000))
    default_international_terms: Mapped[Optional[str]] = mapped_column(String(5000))

    # Tracking
    updated_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))

    # Relationships
    updated_by_user: Mapped[Optional["User"]] = relationship()

    def __repr__(self) -> str:
        return f"<ApprovalSettings threshold={self.threshold_amount}>"
