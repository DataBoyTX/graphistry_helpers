"""Order schemas for API validation."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.models.order import OrderStatus
from app.schemas.customer import CustomerResponse


class OrderResponse(BaseModel):
    """Schema for order responses."""

    id: str
    order_number: str
    quote_id: str
    customer_id: str
    status: OrderStatus

    # Acceptance
    accepted_at: Optional[datetime] = None
    accepted_by: Optional[str] = None

    # Financial
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str

    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    """Schema for detailed order response with customer info."""

    customer: Optional[CustomerResponse] = None


class OrderListResponse(BaseModel):
    """Schema for listing orders."""

    orders: list[OrderResponse]
    total: int
    page: int
    page_size: int


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status."""

    status: OrderStatus
    notes: Optional[str] = None
