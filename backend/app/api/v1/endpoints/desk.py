import csv
import io
import math
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.retailer import Retailer
from app.models.catalog import Product
from app.models.order import Order, OrderItem, OrderItemBenefit
from app.schemas.order import (
    OrderResponse,
    OrderDetailResponse,
    OrderItemResponse,
    AuditLogResponse,
    BenefitDetail,
)
from app.schemas.desk import (
    DeskOrderLinePatchRequest,
    DeskOrderHoldRequest,
    DeskOrderRejectRequest,
    DeskOrderApproveRequest,
    VanLoadingListResponse,
    VanLoadingItem,
    VanLoadingStoreBreakdown,
    InactiveRetailersResponse,
    InactiveRetailerItem,
)
from app.schemas.common import PaginatedResponse
from app.api.deps import require_order_desk
from app.services.order_service import OrderService
from app.services.export_service import sanitize_csv_cell

router = APIRouter()


async def _get_full_order(db: AsyncSession, order_id: uuid.UUID) -> Order:
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.benefits),
            selectinload(Order.retailer),
            selectinload(Order.audit_logs),
        )
    )
    res = await db.execute(stmt)
    return res.scalar_one()


def _serialize_order_detail(order: Order) -> OrderDetailResponse:
    item_responses = [
        OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            ordered_qty=item.ordered_qty,
            approved_qty=item.approved_qty,
            uom_type=item.uom_type,
            applied_scheme_id=item.applied_scheme_id,
            scheme_discount_amount=item.scheme_discount_amount,
            free_item_qty=item.free_item_qty,
            line_subtotal_excl_gst=item.line_subtotal_excl_gst,
            product_name_snapshot=item.product_name_snapshot,
            sku_code_snapshot=item.sku_code_snapshot,
            price_per_unit_snapshot=item.price_per_unit_snapshot,
            price_basis_snapshot=item.price_basis_snapshot,
            scheme_name_snapshot=item.scheme_name_snapshot,
            discount_percentage_snapshot=item.discount_percentage_snapshot,
            free_product_name_snapshot=item.free_product_name_snapshot,
            free_sku_code_snapshot=item.free_sku_code_snapshot,
            benefits=[BenefitDetail.model_validate(b) for b in (item.benefits or [])],
        )
        for item in (order.items or [])
    ]
    audit_responses = [
        AuditLogResponse(
            id=log.id,
            action=log.action,
            created_at=log.created_at,
            old_values=log.old_values,
            new_values=log.new_values,
            reason=log.reason,
        )
        for log in sorted(order.audit_logs or [], key=lambda l: l.created_at, reverse=True)
    ]
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
        item_count=len(order.items or []),
        items=item_responses,
        audit_logs=audit_responses,
        retailer_name=order.retailer.store_name if order.retailer else None,
        retailer_code=order.retailer.retailer_code if order.retailer else None,
    )


@router.get(
    "/orders",
    response_model=PaginatedResponse[OrderResponse],
    summary="List Distributor Orders for Order Desk",
    description="Paginated list of all retailer orders with optional filtering by status or retailer.",
)
async def list_desk_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status (PENDING_APPROVAL, CREDIT_HOLD, APPROVED, REJECTED, EXPORTED)"),
    retailer_id: Optional[uuid.UUID] = Query(None, description="Filter orders by specific retailer UUID"),
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OrderResponse]:
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.benefits),
            selectinload(Order.retailer),
        )
        .order_by(Order.created_at.desc())
    )
    count_stmt = select(func.count(Order.id))

    if status:
        stmt = stmt.where(Order.status == status)
        count_stmt = count_stmt.where(Order.status == status)
    if retailer_id:
        stmt = stmt.where(Order.retailer_id == retailer_id)
        count_stmt = count_stmt.where(Order.retailer_id == retailer_id)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    orders = result.scalars().all()

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
            item_count=len(o.items or []),
            retailer_name=o.retailer.store_name if o.retailer else None,
            retailer_code=o.retailer.retailer_code if o.retailer else None,
        )
        for o in orders
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/orders/{id}",
    response_model=OrderDetailResponse,
    summary="Get Detailed Order for Desk Review",
    description="Full order information including line items, snapshot pricing, audit history, and retailer information.",
)
async def get_desk_order_detail(
    id: uuid.UUID,
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
) -> OrderDetailResponse:
    stmt = (
        select(Order)
        .where(Order.id == id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.benefits),
            selectinload(Order.retailer),
            selectinload(Order.audit_logs),
        )
    )
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return _serialize_order_detail(order)


@router.patch(
    "/orders/{id}/lines/{line_id}",
    response_model=OrderDetailResponse,
    summary="Adjust Order Line Quantity",
    description="Adjust approved quantity on a line item, automatically updating inventory reservations and line totals.",
)
async def desk_adjust_order_line(
    id: uuid.UUID,
    line_id: uuid.UUID,
    payload: DeskOrderLinePatchRequest,
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
) -> OrderDetailResponse:
    order = await OrderService.desk_adjust_line(
        session=db,
        order_id=id,
        line_id=line_id,
        new_approved_qty=payload.approved_qty,
        operator_user_id=current_user.id,
        reason=payload.reason,
    )
    full_order = await _get_full_order(db, order.id)
    return _serialize_order_detail(full_order)


@router.post(
    "/orders/{id}/approve",
    response_model=OrderDetailResponse,
    summary="Approve Order for Fulfillment",
    description="Approves order and commits inventory deductions from available stock.",
)
async def desk_approve_order(
    id: uuid.UUID,
    payload: DeskOrderApproveRequest,
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
) -> OrderDetailResponse:
    order = await OrderService.approve_order(
        session=db,
        order_id=id,
        operator_user_id=current_user.id,
        notes=payload.notes,
        override_credit=payload.override_credit_hold,
    )
    full_order = await _get_full_order(db, order.id)
    return _serialize_order_detail(full_order)


@router.post(
    "/orders/{id}/hold",
    response_model=OrderDetailResponse,
    summary="Place Order on Hold",
    description="Places order on credit or administrative hold pending review.",
)
async def desk_hold_order(
    id: uuid.UUID,
    payload: DeskOrderHoldRequest,
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
) -> OrderDetailResponse:
    order = await OrderService.hold_order(
        session=db,
        order_id=id,
        operator_user_id=current_user.id,
        reason=payload.reason,
    )
    full_order = await _get_full_order(db, order.id)
    return _serialize_order_detail(full_order)


@router.post(
    "/orders/{id}/reject",
    response_model=OrderDetailResponse,
    summary="Reject Order",
    description="Rejects order, releases all reserved inventory, and restores retailer credit availability.",
)
async def desk_reject_order(
    id: uuid.UUID,
    payload: DeskOrderRejectRequest,
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
) -> OrderDetailResponse:
    order = await OrderService.reject_order(
        session=db,
        order_id=id,
        operator_user_id=current_user.id,
        reason=payload.reason,
    )
    full_order = await _get_full_order(db, order.id)
    return _serialize_order_detail(full_order)


# ---------------------------------------------------------------------------
# Priority D: Van Loading List
# ---------------------------------------------------------------------------

async def _build_van_loading_data(
    db: AsyncSession,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Tuple[VanLoadingListResponse, str]:
    stmt = (
        select(Order)
        .where(Order.status == "APPROVED")
        .options(
            selectinload(Order.items).selectinload(OrderItem.benefits),
            selectinload(Order.retailer),
        )
        .order_by(Order.order_number)
    )
    if from_date:
        try:
            dt_from = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
            stmt = stmt.where(Order.created_at >= dt_from)
        except Exception:
            pass
    if to_date:
        try:
            dt_to = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
            stmt = stmt.where(Order.created_at <= dt_to)
        except Exception:
            pass

    res = await db.execute(stmt)
    approved_orders = res.scalars().all()

    prod_stmt = select(Product)
    prod_res = await db.execute(prod_stmt)
    product_map = {p.id: p for p in prod_res.scalars().all()}
    sku_map = {p.sku_code: p for p in product_map.values()}

    sku_aggregates: Dict[str, Dict[str, Any]] = {}
    total_dispatch_cases = 0
    total_purchased_cases = 0
    total_free_cases = 0

    for ord in approved_orders:
        store_name = ord.retailer.store_name if ord.retailer else "Unknown Store"
        ret_code = ord.retailer.retailer_code if ord.retailer else "N/A"

        for itm in ord.items:
            sku = itm.sku_code_snapshot
            if sku not in sku_aggregates:
                prod = sku_map.get(sku)
                sku_aggregates[sku] = {
                    "sku_code": sku,
                    "product_name": itm.product_name_snapshot,
                    "pack_size": prod.pack_size_description if prod else "Standard Pack",
                    "default_dealer_price": itm.price_per_unit_snapshot,
                    "purchased_cases": 0,
                    "free_cases": 0,
                    "total_cases": 0,
                    "stores": [],
                }

            sku_aggregates[sku]["purchased_cases"] += itm.approved_qty
            sku_aggregates[sku]["total_cases"] += itm.approved_qty
            total_purchased_cases += itm.approved_qty
            total_dispatch_cases += itm.approved_qty

            free_for_line = 0
            if itm.benefits:
                for b in itm.benefits:
                    if b.benefit_type == "FREE_GOODS" and b.awarded_quantity > 0:
                        b_sku = b.awarded_sku_code or sku
                        if b_sku not in sku_aggregates:
                            b_prod = sku_map.get(b_sku)
                            sku_aggregates[b_sku] = {
                                "sku_code": b_sku,
                                "product_name": b.awarded_product_name or (b_prod.name if b_prod else "Free Goods"),
                                "pack_size": b_prod.pack_size_description if b_prod else "Standard Pack",
                                "default_dealer_price": b_prod.default_dealer_price if b_prod else Decimal("0.00"),
                                "purchased_cases": 0,
                                "free_cases": 0,
                                "total_cases": 0,
                                "stores": [],
                            }
                        sku_aggregates[b_sku]["free_cases"] += b.awarded_quantity
                        sku_aggregates[b_sku]["total_cases"] += b.awarded_quantity
                        total_free_cases += b.awarded_quantity
                        total_dispatch_cases += b.awarded_quantity
            elif itm.free_item_qty > 0:
                sku_aggregates[sku]["free_cases"] += itm.free_item_qty
                sku_aggregates[sku]["total_cases"] += itm.free_item_qty
                free_for_line = itm.free_item_qty
                total_free_cases += itm.free_item_qty
                total_dispatch_cases += itm.free_item_qty

            sku_aggregates[sku]["stores"].append(
                VanLoadingStoreBreakdown(
                    store_name=store_name,
                    retailer_code=ret_code,
                    order_number=ord.order_number,
                    purchased_cases=itm.approved_qty,
                    free_cases=free_for_line,
                    total_cases=itm.approved_qty + free_for_line,
                )
            )

    items = [
        VanLoadingItem(
            sku_code=data["sku_code"],
            product_name=data["product_name"],
            pack_size=data["pack_size"],
            default_dealer_price=data["default_dealer_price"],
            purchased_cases=data["purchased_cases"],
            free_cases=data["free_cases"],
            total_cases=data["total_cases"],
            store_count=len(data["stores"]),
            stores=data["stores"],
        )
        for data in sorted(sku_aggregates.values(), key=lambda x: x["sku_code"])
    ]

    response_obj = VanLoadingListResponse(
        generated_at=datetime.now(timezone.utc),
        total_approved_orders=len(approved_orders),
        total_dispatch_cases=total_dispatch_cases,
        total_purchased_cases=total_purchased_cases,
        total_free_goods_cases=total_free_cases,
        items=items,
    )

    # Build sanitized CSV payload
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow([
        "SKU Code",
        "Product Name",
        "Pack Size",
        "Purchased Cases",
        "Free Promotional Cases",
        "Total Dispatch Cases",
        "Destinations Count",
    ])
    for it in items:
        writer.writerow([
            sanitize_csv_cell(it.sku_code),
            sanitize_csv_cell(it.product_name),
            sanitize_csv_cell(it.pack_size),
            it.purchased_cases,
            it.free_cases,
            it.total_cases,
            it.store_count,
        ])
    csv_payload = output.getvalue()
    return response_obj, csv_payload


@router.get(
    "/van-loading-list",
    summary="Generate Van Loading List for Warehouse Dispatch",
    description="Aggregates all approved orders by SKU with independent purchased and free-goods case counts.",
)
async def get_van_loading_list(
    from_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    format: Optional[str] = Query(None, description="Set to 'csv' for raw CSV download"),
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
):
    data, csv_text = await _build_van_loading_data(db, from_date, to_date)
    if format == "csv":
        filename = f"Van_Loading_List_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    return data


@router.get(
    "/van-loading-list/export-csv",
    summary="Download Van Loading List as CSV",
    description="Generates sanitized CSV dispatch sheet for warehouse packing and delivery drivers.",
)
async def export_van_loading_list_csv(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
):
    _, csv_text = await _build_van_loading_data(db, from_date, to_date)
    filename = f"Van_Loading_List_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Priority E: Retailer Inactivity Reporting (14+ Days)
# ---------------------------------------------------------------------------

async def _build_inactive_retailers_data(
    db: AsyncSession,
    days: int = 14,
    search: Optional[str] = None,
) -> Tuple[List[InactiveRetailerItem], str]:
    stmt = (
        select(Retailer)
        .options(
            selectinload(Retailer.user),
            selectinload(Retailer.orders),
        )
        .order_by(Retailer.store_name)
    )
    res = await db.execute(stmt)
    retailers = res.scalars().all()

    now_utc = datetime.now(timezone.utc)
    inactive_items: List[InactiveRetailerItem] = []

    for r in retailers:
        # Exclude rejected/cancelled orders
        valid_orders = [
            o for o in r.orders
            if o.status in ("APPROVED", "EXPORTED", "PENDING_DESK_APPROVAL")
        ]

        last_date = None
        days_inactive = None
        tier = "NEVER_ORDERED"

        if valid_orders:
            sorted_orders = sorted(valid_orders, key=lambda o: o.created_at, reverse=True)
            last_order = sorted_orders[0]
            last_date = last_order.created_at
            delta = now_utc - last_date
            days_inactive = max(0, delta.days)

            if days_inactive >= 21:
                tier = "CRITICAL"
            elif days_inactive >= days:
                tier = "WARNING"
            else:
                continue
        else:
            tier = "NEVER_ORDERED"

        # Apply search filter if provided
        if search:
            q = search.lower().strip()
            match = (
                q in r.store_name.lower()
                or q in r.retailer_code.lower()
                or q in r.owner_name.lower()
                or (r.user and q in (r.user.phone_number or ""))
            )
            if not match:
                continue

        inactive_items.append(
            InactiveRetailerItem(
                retailer_id=r.id,
                retailer_code=r.retailer_code,
                store_name=r.store_name,
                owner_name=r.owner_name,
                phone_number=r.user.phone_number if r.user else "N/A",
                city=r.city,
                address=r.address,
                credit_limit=r.credit_limit,
                outstanding_amount=r.outstanding_amount,
                available_credit=r.available_credit,
                is_credit_locked=r.is_credit_locked,
                last_order_date=last_date,
                days_since_last_order=days_inactive,
                inactivity_tier=tier,
            )
        )

    # Sort critical first, then highest days inactive
    inactive_items.sort(key=lambda x: (x.days_since_last_order or 9999), reverse=True)

    # Build sanitized CSV payload
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow([
        "Retailer Code",
        "Store Name",
        "Owner Name",
        "Phone Number",
        "City",
        "Credit Limit",
        "Outstanding Amount",
        "Available Credit",
        "Last Order Date",
        "Days Inactive",
        "Inactivity Tier",
    ])
    for it in inactive_items:
        writer.writerow([
            sanitize_csv_cell(it.retailer_code),
            sanitize_csv_cell(it.store_name),
            sanitize_csv_cell(it.owner_name),
            sanitize_csv_cell(it.phone_number),
            sanitize_csv_cell(it.city),
            f"{it.credit_limit:.2f}",
            f"{it.outstanding_amount:.2f}",
            f"{it.available_credit:.2f}",
            it.last_order_date.strftime("%Y-%m-%d %H:%M") if it.last_order_date else "Never Ordered",
            it.days_since_last_order if it.days_since_last_order is not None else "N/A",
            it.inactivity_tier,
        ])
    csv_payload = output.getvalue()
    return inactive_items, csv_payload


@router.get(
    "/retailers/inactive",
    summary="Retailers with No Confirmed Orders in 14+ Days",
    description="Identifies kirana stores requiring sales rep visit or WhatsApp follow-up. Excludes rejected orders.",
)
async def get_inactive_retailers(
    days: int = Query(default=14, ge=1, le=180, description="Inactivity threshold in days"),
    search: Optional[str] = Query(None, description="Search by store name, owner, or code"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    format: Optional[str] = Query(None, description="Set to 'csv' for direct CSV download"),
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
):
    inactive_items, csv_text = await _build_inactive_retailers_data(db, days=days, search=search)
    if format == "csv":
        filename = f"Inactive_Retailers_{days}d_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    total = len(inactive_items)
    offset = (page - 1) * page_size
    paged = inactive_items[offset : offset + page_size]
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return InactiveRetailersResponse(
        threshold_days=days,
        total_inactive_retailers=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        retailers=paged,
    )


@router.get(
    "/retailers/inactive/export-csv",
    summary="Download Inactive Retailers Report as CSV",
    description="Generates sanitized CSV of inactive stores for sales team outreach.",
)
async def export_inactive_retailers_csv(
    days: int = Query(default=14, ge=1, le=180),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
):
    _, csv_text = await _build_inactive_retailers_data(db, days=days, search=search)
    filename = f"Inactive_Retailers_{days}d_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/desk/orders/clear-sample-data",
    summary="Clear all sample orders and reset balances (Production State)",
    description="Removes all sample/demo orders, order lines, and benefits, resetting credit ledgers to clean 0.00 outstanding. Requires Order Desk supervisor role.",
)
async def clear_sample_orders(
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text
    await db.execute(text("DELETE FROM order_item_benefits;"))
    await db.execute(text("DELETE FROM order_items;"))
    await db.execute(text("DELETE FROM audit_logs WHERE entity_name = 'Order';"))
    await db.execute(text("DELETE FROM export_batches;"))
    await db.execute(text("DELETE FROM orders;"))
    await db.execute(text("""
        UPDATE retailers
        SET outstanding_amount = 0.00,
            available_credit = credit_limit,
            is_credit_locked = FALSE;
    """))
    await db.commit()
    return {
        "status": "success",
        "message": "All sample/demo orders cleared successfully. App is now in clean empty-orders production state.",
    }
