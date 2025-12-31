"""Pydantic schemas package."""
from app.schemas.auth import GoogleAuthURL, Token, TokenPayload
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.schemas.order import (
    OrderDetailResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
)
from app.schemas.product import (
    ProductCreate,
    ProductImportRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.quote import (
    QuoteAcceptRequest,
    QuoteApprovalRequest,
    QuoteCreate,
    QuoteDetailResponse,
    QuoteLineItemCreate,
    QuoteLineItemResponse,
    QuoteLineItemUpdate,
    QuoteListResponse,
    QuoteResponse,
    QuoteSendRequest,
    QuoteSubmitRequest,
    QuoteUpdate,
)
from app.schemas.user import (
    CurrentUser,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Auth
    "Token",
    "TokenPayload",
    "GoogleAuthURL",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "CurrentUser",
    # Customer
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "CustomerListResponse",
    # Product
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductListResponse",
    "ProductImportRequest",
    # Quote
    "QuoteCreate",
    "QuoteUpdate",
    "QuoteResponse",
    "QuoteDetailResponse",
    "QuoteListResponse",
    "QuoteLineItemCreate",
    "QuoteLineItemUpdate",
    "QuoteLineItemResponse",
    "QuoteSubmitRequest",
    "QuoteApprovalRequest",
    "QuoteSendRequest",
    "QuoteAcceptRequest",
    # Order
    "OrderResponse",
    "OrderDetailResponse",
    "OrderListResponse",
    "OrderStatusUpdate",
]
