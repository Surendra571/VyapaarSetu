import math
import uuid
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.retailer import Retailer
from app.models.order import Order, OrderItem
from app.schemas.order import (
    OrderPreviewRequest,
    OrderPreviewResponse,
    OrderCreateRequest,
    OrderResponse,
    OrderDetailResponse,
    OrderItemResponse,
    AuditLogResponse,
    RepeatOrderPreviewResponse,
)
from app.schemas.common import PaginatedResponse
from app.api.deps import require_retailer
from app.services.order_service import OrderService

router = APIRouter()


@router.post(
    "/orders/preview",
    response_model=OrderPreviewResponse,
    summary="Preview Order Pricing, Schemes, and Credit Check",
    description="Evaluates shopping cart lines, active schemes, free items, stock sufficiency, and credit hold notice.",
)
async def preview_order(
    payload: OrderPreviewRequest,
    retailer_auth: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
) -> OrderPreviewResponse:
    _, retailer = retailer_auth
    return await OrderService.preview_order(db, retailer, payload.items)


@router.post(
    "/orders",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Order",
    description="Atomically reserves inventory, validates credit, persists order items with snapshots, and updates ledger.",
)
async def submit_order(
    payload: OrderCreateRequest,
    retailer_auth: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
) -> OrderDetailResponse:
    _, retailer = retailer_auth
    order = await OrderService.create_order(
        db, retailer, payload.items, payload.delivery_notes, payload.client_order_id
    )

    # Reload with relationships
    stmt = (
        select(Order)
        .where(Order.id == order.id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.benefits),
            selectinload(Order.audit_logs),
            selectinload(Order.retailer),
        )
    )
    res = await db.execute(stmt)
    full_order = res.scalar_one()

    return OrderDetailResponse(
        id=full_order.id,
        order_number=full_order.order_number,
        retailer_id=full_order.retailer_id,
        status=full_order.status,
        subtotal_excl_gst=full_order.subtotal_excl_gst,
        credit_hold_reason=full_order.credit_hold_reason,
        desk_notes=full_order.desk_notes,
        created_at=full_order.created_at,
        updated_at=full_order.updated_at,
        item_count=len(full_order.items),
        items=[OrderItemResponse.model_validate(i) for i in full_order.items],
        audit_logs=[AuditLogResponse.model_validate(a) for a in full_order.audit_logs],
        retailer_name=retailer.store_name,
        retailer_code=retailer.retailer_code,
    )


@router.post(
    "/orders/{id}/repeat-preview",
    response_model=RepeatOrderPreviewResponse,
    summary="Preview Repeat Order with Live Revalidation",
    description="Loads a historical order, revalidates real-time catalog prices, stock availability, active schemes, and credit standing.",
)
async def preview_repeat_order(
    id: uuid.UUID,
    retailer_auth: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
) -> RepeatOrderPreviewResponse:
    _, retailer = retailer_auth
    return await OrderService.preview_repeat_order(db, retailer, id)


@router.get(
    "/orders",
    response_model=PaginatedResponse[OrderResponse],
    summary="List Retailer Order History",
    description="Paginated order history for the authenticated retailer only (Tenant isolated).",
)
async def list_retailer_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    retailer_auth: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OrderResponse]:
    _, retailer = retailer_auth

    # Business Constraint 9: Multi-tenant partition - strictly scoped to retailer.id
    stmt = (
        select(Order)
        .where(Order.retailer_id == retailer.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    count_stmt = select(func.count(Order.id)).where(Order.retailer_id == retailer.id)

    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
        count_stmt = count_stmt.where(Order.status == status_filter)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    res = await db.execute(stmt)
    orders = res.scalars().all()

    items = [
        OrderResponse(
            id=o.id,
            order_number=o.order_number,
            retailer_id=o.retailer_id,
            status=o.status,
            subtotal_excl_gst=o.subtotal_excl_gst,
            credit_hold_reason=o.credit_hold_reason,
            desk_notes=o.desk_notes,
            created_at=o.created_at,
            updated_at=o.updated_at,
            item_count=len(o.items),
        )
        for o in orders
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse[OrderResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/orders/{id}",
    response_model=OrderDetailResponse,
    summary="Get Order Detail by UUID",
    description="Full details of an order including line item snapshots and audit events.",
)
async def get_order_detail(
    id: uuid.UUID,
    retailer_auth: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
) -> OrderDetailResponse:
    _, retailer = retailer_auth

    stmt = (
        select(Order)
        .where(Order.id == id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.benefits),
            selectinload(Order.audit_logs),
            selectinload(Order.retailer),
        )
    )
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{id}' was not found.",
        )

    # Business Constraint 9: Never allow access to another retailer's order
    if order.retailer_id != retailer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this retailer order.",
        )

    return OrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        retailer_id=order.retailer_id,
        status=order.status,
        subtotal_excl_gst=order.subtotal_excl_gst,
        credit_hold_reason=order.credit_hold_reason,
        desk_notes=order.desk_notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        item_count=len(order.items),
        items=[OrderItemResponse.model_validate(i) for i in order.items],
        audit_logs=[AuditLogResponse.model_validate(a) for a in order.audit_logs],
        retailer_name=order.retailer.store_name if order.retailer else None,
        retailer_code=order.retailer.retailer_code if order.retailer else None,
    )

