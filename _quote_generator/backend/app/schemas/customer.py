"""Customer schemas for API validation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class CustomerBase(BaseModel):
    """Base customer schema."""

    company_name: str
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    tax_id: Optional[str] = None
    is_international: bool = False
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""

    pass


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""

    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    is_international: Optional[bool] = None
    notes: Optional[str] = None


class CustomerResponse(CustomerBase):
    """Schema for customer responses."""

    id: str
    created_by: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    """Schema for listing customers."""

    customers: list[CustomerResponse]
    total: int
    page: int
    page_size: int
