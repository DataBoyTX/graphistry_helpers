"""Quote management router."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.quote import Quote, QuoteLineItem, QuoteStatus, TemplateType
from app.models.settings import ApprovalSettings
from app.models.user import User, UserRole
from app.routers.auth import get_admin_user, get_current_active_user
from app.schemas.quote import (
    QuoteAcceptRequest,
    QuoteApprovalRequest,
    QuoteCreate,
    QuoteDetailResponse,
    QuoteLineItemResponse,
    QuoteListResponse,
    QuoteResponse,
    QuoteUpdate,
)

router = APIRouter(prefix="/quotes", tags=["Quotes"])


async def generate_quote_number(db: AsyncSession, settings: Settings) -> str:
    """Generate a unique quote number in format Q-YYYY-NNNN."""
    year = datetime.now(timezone.utc).year
    prefix = f"{settings.quote_number_prefix}-{year}-"

    # Get the highest existing number for this year
    result = await db.execute(
        select(Quote.quote_number)
        .where(Quote.quote_number.like(f"{prefix}%"))
        .order_by(Quote.quote_number.desc())
        .limit(1)
    )
    last_number = result.scalar_one_or_none()

    if last_number:
        # Extract the sequence number and increment
        seq = int(last_number.split("-")[-1]) + 1
    else:
        seq = 1

    return f"{prefix}{seq:04d}"


async def generate_order_number(db: AsyncSession, settings: Settings) -> str:
    """Generate a unique order number in format O-YYYY-NNNN."""
    year = datetime.now(timezone.utc).year
    prefix = f"{settings.order_number_prefix}-{year}-"

    result = await db.execute(
        select(Order.order_number)
        .where(Order.order_number.like(f"{prefix}%"))
        .order_by(Order.order_number.desc())
        .limit(1)
    )
    last_number = result.scalar_one_or_none()

    if last_number:
        seq = int(last_number.split("-")[-1]) + 1
    else:
        seq = 1

    return f"{prefix}{seq:04d}"


async def check_requires_approval(
    quote: Quote,
    db: AsyncSession,
) -> bool:
    """Check if a quote requires approval based on settings."""
    result = await db.execute(select(ApprovalSettings).limit(1))
    settings = result.scalar_one_or_none()

    if not settings:
        return False

    # Check threshold
    if quote.total >= settings.threshold_amount:
        return True

    # Check international requirement
    if settings.require_approval_international and quote.template_type == TemplateType.INTERNATIONAL:
        return True

    return False


@router.get("", response_model=QuoteListResponse)
async def list_quotes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
    status_filter: Optional[QuoteStatus] = Query(None, alias="status"),
    customer_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> QuoteListResponse:
    """List all quotes with optional filters."""
    query = select(Quote)

    if status_filter:
        query = query.where(Quote.status == status_filter)

    if customer_id:
        query = query.where(Quote.customer_id == customer_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(Quote.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    quotes = result.scalars().all()

    return QuoteListResponse(
        quotes=[QuoteResponse.model_validate(q) for q in quotes],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=QuoteDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    quote_data: QuoteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QuoteDetailResponse:
    """Create a new quote."""
    # Verify customer exists
    result = await db.execute(
        select(Customer).where(Customer.id == quote_data.customer_id, Customer.is_active == True)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Generate quote number
    quote_number = await generate_quote_number(db, settings)

    # Set default validity
    valid_until = quote_data.valid_until
    if not valid_until:
        valid_until = date.today() + timedelta(days=settings.default_quote_validity_days)

    # Create quote
    quote = Quote(
        quote_number=quote_number,
        customer_id=quote_data.customer_id,
        created_by=current_user.id,
        template_type=quote_data.template_type,
        currency=quote_data.currency,
        discount_percent=quote_data.discount_percent,
        tax_rate=quote_data.tax_rate,
        terms_and_conditions=quote_data.terms_and_conditions,
        notes=quote_data.notes,
        valid_until=valid_until,
    )
    db.add(quote)

    # Add line items
    for idx, item_data in enumerate(quote_data.line_items):
        line_item = QuoteLineItem(
            quote_id=quote.id,
            product_id=item_data.product_id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            discount_percent=item_data.discount_percent,
            sort_order=idx,
        )
        line_item.calculate_total()
        quote.line_items.append(line_item)

    # Calculate totals
    quote.calculate_totals()

    await db.commit()
    await db.refresh(quote)

    # Load relationships for response
    result = await db.execute(
        select(Quote)
        .where(Quote.id == quote.id)
        .options(selectinload(Quote.line_items), selectinload(Quote.customer))
    )
    quote = result.scalar_one()

    return QuoteDetailResponse(
        **QuoteResponse.model_validate(quote).model_dump(),
        line_items=[QuoteLineItemResponse.model_validate(li) for li in quote.line_items],
        customer=quote.customer,
    )


@router.get("/{quote_id}", response_model=QuoteDetailResponse)
async def get_quote(
    quote_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> QuoteDetailResponse:
    """Get a specific quote with line items and customer."""
    result = await db.execute(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(selectinload(Quote.line_items), selectinload(Quote.customer))
    )
    quote = result.scalar_one_or_none()

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    return QuoteDetailResponse(
        **QuoteResponse.model_validate(quote).model_dump(),
        line_items=[QuoteLineItemResponse.model_validate(li) for li in quote.line_items],
        customer=quote.customer,
    )


@router.put("/{quote_id}", response_model=QuoteDetailResponse)
async def update_quote(
    quote_id: str,
    quote_data: QuoteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> QuoteDetailResponse:
    """Update a quote (only if in draft status)."""
    result = await db.execute(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(selectinload(Quote.line_items), selectinload(Quote.customer))
    )
    quote = result.scalar_one_or_none()

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    if quote.status != QuoteStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft quotes can be modified",
        )

    # Handle line items separately
    update_data = quote_data.model_dump(exclude_unset=True)
    new_line_items = update_data.pop("line_items", None)

    # Update quote fields
    for field, value in update_data.items():
        setattr(quote, field, value)

    # Update line items if provided
    if new_line_items is not None:
        # Delete existing line items
        for item in quote.line_items:
            await db.delete(item)
        quote.line_items = []

        # Add new line items
        for idx, item_data in enumerate(new_line_items):
            line_item = QuoteLineItem(
                quote_id=quote.id,
                product_id=item_data.get("product_id"),
                description=item_data["description"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                discount_percent=item_data.get("discount_percent", Decimal("0")),
                sort_order=idx,
            )
            line_item.calculate_total()
            quote.line_items.append(line_item)

    # Recalculate totals
    quote.calculate_totals()

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(selectinload(Quote.line_items), selectinload(Quote.customer))
    )
    quote = result.scalar_one()

    return QuoteDetailResponse(
        **QuoteResponse.model_validate(quote).model_dump(),
        line_items=[QuoteLineItemResponse.model_validate(li) for li in quote.line_items],
        customer=quote.customer,
    )


@router.delete("/{quote_id}")
async def delete_quote(
    quote_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Delete a quote (only if in draft status)."""
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    if quote.status != QuoteStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft quotes can be deleted",
        )

    await db.delete(quote)
    await db.commit()

    return {"message": "Quote deleted successfully"}


@router.post("/{quote_id}/submit", response_model=QuoteResponse)
async def submit_quote(
    quote_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> QuoteResponse:
    """Submit a quote for approval (or mark as approved if not required)."""
    result = await db.execute(
        select(Quote).where(Quote.id == quote_id).options(selectinload(Quote.line_items))
    )
    quote = result.scalar_one_or_none()

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    if quote.status != QuoteStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft quotes can be submitted",
        )

    if not quote.line_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote must have at least one line item",
        )

    # Check if approval is required
    requires_approval = await check_requires_approval(quote, db)

    if requires_approval and current_user.role != UserRole.ADMIN:
        quote.status = QuoteStatus.PENDING_APPROVAL
        quote.requires_approval = True
    else:
        quote.status = QuoteStatus.APPROVED
        quote.approved_by = current_user.id
        quote.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(quote)

    return QuoteResponse.model_validate(quote)


@router.post("/{quote_id}/approve", response_model=QuoteResponse)
async def approve_quote(
    quote_id: str,
    approval: QuoteApprovalRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_admin_user)],
) -> QuoteResponse:
    """Approve a quote (admin only)."""
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    if quote.status != QuoteStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote is not pending approval",
        )

    quote.status = QuoteStatus.APPROVED
    quote.approved_by = current_user.id
    quote.approved_at = datetime.now(timezone.utc)
    if approval.notes:
        quote.notes = (quote.notes or "") + f"\n\nApproval notes: {approval.notes}"

    await db.commit()
    await db.refresh(quote)

    return QuoteResponse.model_validate(quote)


@router.post("/{quote_id}/reject", response_model=QuoteResponse)
async def reject_quote(
    quote_id: str,
    rejection: QuoteApprovalRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_admin_user)],
) -> QuoteResponse:
    """Reject a quote (admin only)."""
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    if quote.status != QuoteStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote is not pending approval",
        )

    quote.status = QuoteStatus.REJECTED
    if rejection.notes:
        quote.notes = (quote.notes or "") + f"\n\nRejection reason: {rejection.notes}"

    await db.commit()
    await db.refresh(quote)

    return QuoteResponse.model_validate(quote)


@router.post("/{quote_id}/accept")
async def accept_quote(
    quote_id: str,
    accept_request: QuoteAcceptRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Accept a quote and convert it to an order."""
    result = await db.execute(
        select(Quote).where(Quote.id == quote_id).options(selectinload(Quote.order))
    )
    quote = result.scalar_one_or_none()

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    if quote.status not in [QuoteStatus.APPROVED, QuoteStatus.SENT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved or sent quotes can be accepted",
        )

    if quote.order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote has already been converted to an order",
        )

    # Check if quote has expired
    if quote.valid_until and quote.valid_until < date.today():
        quote.status = QuoteStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote has expired",
        )

    # Generate order number
    order_number = await generate_order_number(db, settings)

    # Create order
    order = Order(
        order_number=order_number,
        quote_id=quote.id,
        customer_id=quote.customer_id,
        status=OrderStatus.PENDING,
        accepted_at=datetime.now(timezone.utc),
        accepted_by=accept_request.accepted_by,
        subtotal=quote.subtotal,
        discount_amount=quote.discount_amount,
        tax_amount=quote.tax_amount,
        total=quote.total,
        currency=quote.currency,
        notes=accept_request.notes,
    )
    db.add(order)

    # Update quote status
    quote.status = QuoteStatus.ACCEPTED

    await db.commit()
    await db.refresh(order)

    return {
        "message": "Quote accepted successfully",
        "order_id": order.id,
        "order_number": order.order_number,
    }


@router.get("/{quote_id}/pdf")
async def get_quote_pdf(
    quote_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> Response:
    """Generate and download a PDF for a quote."""
    from app.services.pdf_generator import generate_quote_pdf

    result = await db.execute(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(selectinload(Quote.line_items), selectinload(Quote.customer))
    )
    quote = result.scalar_one_or_none()

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    # Generate PDF
    pdf_content = generate_quote_pdf(quote)

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{quote.quote_number}.pdf"'
        },
    )


@router.post("/{quote_id}/send")
async def send_quote(
    quote_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Send a quote: upload to Drive and create Gmail draft.

    This endpoint:
    1. Generates the quote PDF and HTML
    2. Uploads both to Google Drive in a customer-specific folder
    3. Creates a Gmail draft with the PDF attached
    4. Updates the quote status to 'sent'

    Returns URLs to the Drive files and Gmail draft.
    """
    from app.services.google_drive import upload_quote_to_drive
    from app.services.google_gmail import create_quote_draft
    from app.services.pdf_generator import generate_quote_html, generate_quote_pdf

    # Verify user has Google credentials
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected. Please sign out and sign back in.",
        )

    result = await db.execute(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(selectinload(Quote.line_items), selectinload(Quote.customer))
    )
    quote = result.scalar_one_or_none()

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    if quote.status not in [QuoteStatus.APPROVED, QuoteStatus.SENT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved quotes can be sent",
        )

    if not quote.customer.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer does not have an email address",
        )

    # Generate PDF and HTML
    pdf_content = generate_quote_pdf(quote)
    html_content = generate_quote_html(quote)

    # Upload to Google Drive
    try:
        drive_result = upload_quote_to_drive(
            user=current_user,
            pdf_content=pdf_content,
            html_content=html_content,
            quote_number=quote.quote_number,
            customer_name=quote.customer.company_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to Google Drive: {str(e)}",
        )

    # Create Gmail draft
    try:
        gmail_result = create_quote_draft(
            user=current_user,
            to_email=quote.customer.email,
            quote_number=quote.quote_number,
            customer_name=quote.customer.company_name,
            contact_name=quote.customer.contact_name,
            total=f"{quote.total:,.2f}",
            currency=quote.currency,
            valid_until=quote.valid_until.strftime("%B %d, %Y") if quote.valid_until else None,
            pdf_content=pdf_content,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Gmail draft: {str(e)}",
        )

    # Update quote with Google IDs and status
    quote.drive_pdf_id = drive_result["pdf_file_id"]
    quote.drive_doc_id = drive_result["doc_file_id"]
    quote.gmail_draft_id = gmail_result["draft_id"]
    quote.status = QuoteStatus.SENT
    quote.sent_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(quote)

    return {
        "message": "Quote sent successfully",
        "drive_pdf_link": drive_result["pdf_web_link"],
        "drive_doc_link": drive_result["doc_web_link"],
        "gmail_draft_id": gmail_result["draft_id"],
    }
