"""User schemas for API validation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user (used internally)."""

    google_id: str
    picture_url: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user responses."""

    id: str
    role: UserRole
    picture_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Schema for listing users."""

    users: list[UserResponse]
    total: int


class CurrentUser(UserResponse):
    """Schema for current authenticated user with additional info."""

    has_google_tokens: bool = False
