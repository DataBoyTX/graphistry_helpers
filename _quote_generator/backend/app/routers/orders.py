"""Order management router."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.routers.auth import get_current_active_user
from app.schemas.customer import CustomerResponse
from app.schemas.order import (
    OrderDetailResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=OrderListResponse)
async def list_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    customer_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> OrderListResponse:
    """List all orders with optional filters."""
    query = select(Order)

    if status_filter:
        query = query.where(Order.status == status_filter)

    if customer_id:
        query = query.where(Order.customer_id == customer_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> OrderDetailResponse:
    """Get a specific order with customer details."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.customer))
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return OrderDetailResponse(
        **OrderResponse.model_validate(order).model_dump(),
        customer=CustomerResponse.model_validate(order.customer) if order.customer else None,
    )


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> OrderResponse:
    """Update an order's status."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Validate status transitions
    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.CONFIRMED: [OrderStatus.FULFILLED, OrderStatus.CANCELLED],
        OrderStatus.FULFILLED: [],  # Terminal state
        OrderStatus.CANCELLED: [],  # Terminal state
    }

    if status_update.status not in valid_transitions.get(order.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {order.status.value} to {status_update.status.value}",
        )

    order.status = status_update.status
    if status_update.notes:
        order.notes = (order.notes or "") + f"\n\nStatus update: {status_update.notes}"

    await db.commit()
    await db.refresh(order)

    return OrderResponse.model_validate(order)
