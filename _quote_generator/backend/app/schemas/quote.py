"""Quote and QuoteLineItem schemas for API validation."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.quote import QuoteStatus, TemplateType
from app.schemas.customer import CustomerResponse


class QuoteLineItemBase(BaseModel):
    """Base line item schema."""

    product_id: Optional[str] = None
    description: str
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0)
    unit_price: Decimal = Field(ge=0)
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)


class QuoteLineItemCreate(QuoteLineItemBase):
    """Schema for creating a line item."""

    pass


class QuoteLineItemUpdate(BaseModel):
    """Schema for updating a line item."""

    product_id: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    discount_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    sort_order: Optional[int] = None


class QuoteLineItemResponse(QuoteLineItemBase):
    """Schema for line item responses."""

    id: str
    quote_id: str
    line_total: Decimal
    sort_order: int

    model_config = {"from_attributes": True}


class QuoteBase(BaseModel):
    """Base quote schema."""

    customer_id: str
    template_type: TemplateType = TemplateType.US
    currency: str = "USD"
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    valid_until: Optional[date] = None


class QuoteCreate(QuoteBase):
    """Schema for creating a quote."""

    line_items: list[QuoteLineItemCreate] = []


class QuoteUpdate(BaseModel):
    """Schema for updating a quote."""

    customer_id: Optional[str] = None
    template_type: Optional[TemplateType] = None
    currency: Optional[str] = None
    discount_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    tax_rate: Optional[Decimal] = Field(default=None, ge=0)
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    valid_until: Optional[date] = None
    line_items: Optional[list[QuoteLineItemCreate]] = None


class QuoteResponse(QuoteBase):
    """Schema for quote responses."""

    id: str
    quote_number: str
    created_by: str
    status: QuoteStatus

    # Calculated fields
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal

    # Approval
    requires_approval: bool
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Google integration
    drive_doc_id: Optional[str] = None
    drive_pdf_id: Optional[str] = None
    gmail_draft_id: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class QuoteDetailResponse(QuoteResponse):
    """Schema for detailed quote response with line items and customer."""

    line_items: list[QuoteLineItemResponse] = []
    customer: Optional[CustomerResponse] = None


class QuoteListResponse(BaseModel):
    """Schema for listing quotes."""

    quotes: list[QuoteResponse]
    total: int
    page: int
    page_size: int


class QuoteSubmitRequest(BaseModel):
    """Schema for submitting a quote for approval."""

    pass


class QuoteApprovalRequest(BaseModel):
    """Schema for approving/rejecting a quote."""

    notes: Optional[str] = None


class QuoteSendRequest(BaseModel):
    """Schema for sending a quote to customer."""

    recipient_email: Optional[str] = None  # Override customer email
    subject: Optional[str] = None
    message: Optional[str] = None


class QuoteAcceptRequest(BaseModel):
    """Schema for accepting a quote (converting to order)."""

    accepted_by: str  # Customer name or email
    notes: Optional[str] = None
