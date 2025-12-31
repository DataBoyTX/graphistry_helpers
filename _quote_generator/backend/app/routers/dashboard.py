"""Dashboard statistics router."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.quote import Quote, QuoteStatus
from app.models.user import User
from app.routers.auth import get_current_active_user
from app.schemas.dashboard import DashboardStatsResponse, RecentActivityItem

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> DashboardStatsResponse:
    """Get dashboard statistics."""
    # Counts
    total_customers = await db.scalar(
        select(func.count()).select_from(Customer).where(Customer.is_active == True)
    )
    total_products = await db.scalar(
        select(func.count()).select_from(Product).where(Product.is_active == True)
    )
    total_quotes = await db.scalar(select(func.count()).select_from(Quote))
    total_orders = await db.scalar(select(func.count()).select_from(Order))

    # Quotes by status
    draft_quotes = await db.scalar(
        select(func.count()).select_from(Quote).where(Quote.status == QuoteStatus.DRAFT)
    )
    pending_quotes = await db.scalar(
        select(func.count())
        .select_from(Quote)
        .where(Quote.status == QuoteStatus.PENDING_APPROVAL)
    )
    sent_quotes = await db.scalar(
        select(func.count()).select_from(Quote).where(Quote.status == QuoteStatus.SENT)
    )

    # Orders by status
    pending_orders = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.status == OrderStatus.PENDING)
    )
    confirmed_orders = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.status == OrderStatus.CONFIRMED)
    )

    # Revenue (sum of all order totals)
    total_revenue = await db.scalar(
        select(func.sum(Order.total)).select_from(Order)
    )

    # Monthly revenue (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    monthly_revenue = await db.scalar(
        select(func.sum(Order.total))
        .select_from(Order)
        .where(Order.created_at >= thirty_days_ago)
    )

    # Quote value (sum of all quote totals for sent/approved quotes)
    quote_pipeline = await db.scalar(
        select(func.sum(Quote.total))
        .select_from(Quote)
        .where(Quote.status.in_([QuoteStatus.APPROVED, QuoteStatus.SENT]))
    )

    return DashboardStatsResponse(
        total_customers=total_customers or 0,
        total_products=total_products or 0,
        total_quotes=total_quotes or 0,
        total_orders=total_orders or 0,
        draft_quotes=draft_quotes or 0,
        pending_quotes=pending_quotes or 0,
        sent_quotes=sent_quotes or 0,
        pending_orders=pending_orders or 0,
        confirmed_orders=confirmed_orders or 0,
        total_revenue=total_revenue or Decimal("0.00"),
        monthly_revenue=monthly_revenue or Decimal("0.00"),
        quote_pipeline=quote_pipeline or Decimal("0.00"),
    )


@router.get("/recent", response_model=list[RecentActivityItem])
async def get_recent_activity(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
    limit: int = 10,
) -> list[RecentActivityItem]:
    """Get recent activity (quotes and orders)."""
    activities = []

    # Recent quotes
    result = await db.execute(
        select(Quote)
        .order_by(Quote.updated_at.desc())
        .limit(limit)
    )
    quotes = result.scalars().all()

    for quote in quotes:
        activity_type = "quote_created" if quote.status == QuoteStatus.DRAFT else f"quote_{quote.status.value}"
        activities.append(
            RecentActivityItem(
                id=quote.id,
                type=activity_type,
                reference=quote.quote_number,
                description=f"Quote {quote.quote_number}",
                status=quote.status.value,
                amount=quote.total,
                currency=quote.currency,
                timestamp=quote.updated_at,
            )
        )

    # Recent orders
    result = await db.execute(
        select(Order)
        .order_by(Order.updated_at.desc())
        .limit(limit)
    )
    orders = result.scalars().all()

    for order in orders:
        activities.append(
            RecentActivityItem(
                id=order.id,
                type=f"order_{order.status.value}",
                reference=order.order_number,
                description=f"Order {order.order_number}",
                status=order.status.value,
                amount=order.total,
                currency=order.currency,
                timestamp=order.updated_at,
            )
        )

    # Sort by timestamp and return top N
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    return activities[:limit]
