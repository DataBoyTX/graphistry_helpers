"""Customer management router."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import Customer
from app.models.user import User
from app.routers.auth import get_current_active_user
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
    search: Optional[str] = Query(None, description="Search by company name, contact name, or email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CustomerListResponse:
    """List all customers with optional search and pagination."""
    query = select(Customer).where(Customer.is_active == True)

    if search:
        search_filter = or_(
            Customer.company_name.ilike(f"%{search}%"),
            Customer.contact_name.ilike(f"%{search}%"),
            Customer.email.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(Customer.company_name).offset(offset).limit(page_size)
    result = await db.execute(query)
    customers = result.scalars().all()

    return CustomerListResponse(
        customers=[CustomerResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CustomerResponse:
    """Create a new customer."""
    customer = Customer(
        **customer_data.model_dump(),
        created_by=current_user.id,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return CustomerResponse.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> CustomerResponse:
    """Get a specific customer."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.is_active == True)
    )
    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_data: CustomerUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> CustomerResponse:
    """Update a customer."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.is_active == True)
    )
    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)

    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Soft delete a customer."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.is_active == True)
    )
    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    customer.is_active = False
    await db.commit()

    return {"message": "Customer deleted successfully"}
