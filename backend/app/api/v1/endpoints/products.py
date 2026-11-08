import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.catalog import Product, Inventory
from app.models.pricing import Scheme, SchemeRule
from app.schemas.catalog import (
    ProductResponse,
    ProductDetailResponse,
    InventoryAvailabilityResponse,
    SchemeResponse,
)
from app.schemas.common import PaginatedResponse
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get(
    "/products",
    response_model=PaginatedResponse[ProductResponse],
    summary="List Product Master Catalogue",
    description="Paginated list of active FMCG products with case availability and provisional price basis.",
)
async def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter by category (Packaged Food, Home Care)"),
    search: Optional[str] = Query(None, description="Search query across SKU code, title, and brand"),
    only_active: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[ProductResponse]:
    stmt = (
        select(Product)
        .options(selectinload(Product.inventory))
        .order_by(Product.name)
    )
    count_stmt = select(func.count(Product.id))

    if only_active:
        stmt = stmt.where(Product.is_active == True)
        count_stmt = count_stmt.where(Product.is_active == True)

    if category:
        stmt = stmt.where(Product.category == category)
        count_stmt = count_stmt.where(Product.category == category)

    if search:
        term = f"%{search.strip()}%"
        search_filter = or_(
            Product.name.ilike(term),
            Product.sku_code.ilike(term),
            Product.brand.ilike(term),
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    # Total count
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    res = await db.execute(stmt)
    products = res.scalars().all()

    items = [
        ProductResponse(
            id=p.id,
            sku_code=p.sku_code,
            name=p.name,
            brand=p.brand,
            category=p.category,
            pack_size_description=p.pack_size_description,
            units_per_case=p.units_per_case,
            default_dealer_price=p.default_dealer_price,
            mrp=p.mrp,
            price_basis=p.price_basis,
            is_active=p.is_active,
            image_url=p.image_url or f"/images/products/{p.sku_code}.webp",
            available_cases=p.inventory.available_cases if p.inventory else 0,
        )
        for p in products
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse[ProductResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/products/{id}",
    response_model=ProductDetailResponse,
    summary="Get Product Detail by UUID",
    description="Product specifications, live stock availability, and associated trade schemes.",
)
async def get_product_detail(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductDetailResponse:
    stmt = (
        select(Product)
        .where(Product.id == id)
        .options(
            selectinload(Product.inventory),
            selectinload(Product.qualifying_schemes)
            .selectinload(SchemeRule.scheme)
            .selectinload(Scheme.rules),
        )
    )
    res = await db.execute(stmt)
    p = res.scalar_one_or_none()

    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{id}' was not found.",
        )

    # Assemble inventory
    inv_response = None
    if p.inventory:
        inv_response = InventoryAvailabilityResponse(
            product_id=p.id,
            stock_cases=p.inventory.stock_cases,
            reserved_cases=p.inventory.reserved_cases,
            available_cases=p.inventory.available_cases,
            reorder_level_cases=p.inventory.reorder_level_cases,
            is_in_stock=p.inventory.available_cases > 0,
        )

    # Active Schemes
    active_schemes_list = []
    seen_scheme_ids = set()
    for rule in p.qualifying_schemes:
        if rule.scheme.is_active and rule.scheme.id not in seen_scheme_ids:
            active_schemes_list.append(SchemeResponse.model_validate(rule.scheme))
            seen_scheme_ids.add(rule.scheme.id)

    return ProductDetailResponse(
        id=p.id,
        sku_code=p.sku_code,
        name=p.name,
        brand=p.brand,
        category=p.category,
        pack_size_description=p.pack_size_description,
        units_per_case=p.units_per_case,
        default_dealer_price=p.default_dealer_price,
        mrp=p.mrp,
        price_basis=p.price_basis,
        is_active=p.is_active,
        image_url=p.image_url or f"/images/products/{p.sku_code}.webp",
        available_cases=p.inventory.available_cases if p.inventory else 0,
        inventory=inv_response,
        active_schemes=active_schemes_list,
    )


@router.get(
    "/products/{id}/availability",
    response_model=InventoryAvailabilityResponse,
    summary="Check Live Inventory Availability",
    description="Physical stock, reserved orders, and available cases for checkout.",
)
async def get_product_availability(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryAvailabilityResponse:
    stmt = select(Inventory).where(Inventory.product_id == id)
    res = await db.execute(stmt)
    inv = res.scalar_one_or_none()

    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory record for product '{id}' was not found.",
        )

    return InventoryAvailabilityResponse(
        product_id=inv.product_id,
        stock_cases=inv.stock_cases,
        reserved_cases=inv.reserved_cases,
        available_cases=inv.available_cases,
        reorder_level_cases=inv.reorder_level_cases,
        is_in_stock=inv.available_cases > 0,
    )
