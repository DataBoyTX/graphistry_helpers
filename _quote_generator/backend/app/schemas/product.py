"""Product schemas for API validation."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.product import BillingPeriod, ProductCategory


class ProductBase(BaseModel):
    """Base product schema."""

    name: str
    sku: Optional[str] = None
    description: Optional[str] = None
    category: ProductCategory = ProductCategory.SERVICE
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str = "USD"
    is_recurring: bool = False
    billing_period: BillingPeriod = BillingPeriod.ONE_TIME


class ProductCreate(ProductBase):
    """Schema for creating a product."""

    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    name: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ProductCategory] = None
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = None
    is_recurring: Optional[bool] = None
    billing_period: Optional[BillingPeriod] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Schema for product responses."""

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    """Schema for listing products."""

    products: list[ProductResponse]
    total: int


class ProductImportRequest(BaseModel):
    """Schema for importing products from Google Sheets."""

    spreadsheet_id: str
    sheet_name: str = "Products"
