"""Dashboard schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response."""

    # Counts
    total_customers: int
    total_products: int
    total_quotes: int
    total_orders: int

    # Quote status counts
    draft_quotes: int
    pending_quotes: int
    sent_quotes: int

    # Order status counts
    pending_orders: int
    confirmed_orders: int

    # Financial
    total_revenue: Decimal
    monthly_revenue: Decimal
    quote_pipeline: Decimal

    model_config = {"from_attributes": True}


class RecentActivityItem(BaseModel):
    """Recent activity item."""

    id: str
    type: str  # quote_created, quote_sent, order_pending, etc.
    reference: str  # Quote or order number
    description: str
    status: str
    amount: Decimal
    currency: str
    timestamp: datetime

    model_config = {"from_attributes": True}
