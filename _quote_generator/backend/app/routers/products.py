"""Product management router."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.product import Product, ProductCategory
from app.models.user import User
from app.routers.auth import get_current_active_user
from app.schemas.product import (
    ProductCreate,
    ProductImportRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
    search: Optional[str] = Query(None, description="Search by name, SKU, or description"),
    category: Optional[ProductCategory] = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only show active products"),
) -> ProductListResponse:
    """List all products with optional filters."""
    query = select(Product)

    if active_only:
        query = query.where(Product.is_active == True)

    if search:
        search_filter = or_(
            Product.name.ilike(f"%{search}%"),
            Product.sku.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if category:
        query = query.where(Product.category == category)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Get results
    query = query.order_by(Product.name)
    result = await db.execute(query)
    products = result.scalars().all()

    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        total=total,
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> ProductResponse:
    """Create a new product."""
    # Check for duplicate SKU
    if product_data.sku:
        result = await db.execute(
            select(Product).where(Product.sku == product_data.sku)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product with this SKU already exists",
            )

    product = Product(**product_data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return ProductResponse.model_validate(product)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> ProductResponse:
    """Get a specific product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> ProductResponse:
    """Update a product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Check for duplicate SKU if changing
    if product_data.sku and product_data.sku != product.sku:
        sku_check = await db.execute(
            select(Product).where(Product.sku == product_data.sku)
        )
        if sku_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product with this SKU already exists",
            )

    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    return ProductResponse.model_validate(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Deactivate a product (soft delete)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    product.is_active = False
    await db.commit()

    return {"message": "Product deactivated successfully"}


@router.post("/import", response_model=ProductListResponse)
async def import_products_from_sheets(
    import_request: ProductImportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ProductListResponse:
    """Import products from a Google Sheet.

    The sheet should have columns: Name, SKU, Description, Category,
    Unit Price, Currency, Is Recurring, Billing Period
    """
    from app.services.google_sheets import import_products_from_sheet

    if not current_user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not connected. Please sign out and sign back in.",
        )

    try:
        product_data = import_products_from_sheet(
            user=current_user,
            spreadsheet_id=import_request.spreadsheet_id,
            sheet_name=import_request.sheet_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import products: {str(e)}",
        )

    if not product_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No products found in the sheet",
        )

    # Create products
    created_products = []
    for data in product_data:
        # Check for duplicate SKU
        if data.get("sku"):
            result = await db.execute(
                select(Product).where(Product.sku == data["sku"])
            )
            if result.scalar_one_or_none():
                # Skip duplicate SKUs
                continue

        product = Product(**data)
        db.add(product)
        created_products.append(product)

    await db.commit()

    # Refresh products to get IDs
    for product in created_products:
        await db.refresh(product)

    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in created_products],
        total=len(created_products),
    )
