import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem
from app.models.audit import AuditLog


async def get_order_by_id(
    session: AsyncSession,
    order_id: uuid.UUID,
) -> Optional[Order]:
    """Fetch order by primary key with items and retailer loaded."""
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.retailer),
            selectinload(Order.audit_logs),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_order_by_number(
    session: AsyncSession,
    order_number: str,
) -> Optional[Order]:
    """Fetch order by unique order number."""
    stmt = (
        select(Order)
        .where(Order.order_number == order_number)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.retailer),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_orders(
    session: AsyncSession,
    retailer_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Order]:
    """List orders with optional retailer and status filtering."""
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.retailer),
        )
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if retailer_id:
        stmt = stmt.where(Order.retailer_id == retailer_id)
    if status:
        stmt = stmt.where(Order.status == status)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_order_status(
    session: AsyncSession,
    order_id: uuid.UUID,
    new_status: str,
    action_user_id: Optional[uuid.UUID] = None,
    reason: Optional[str] = None,
) -> Optional[Order]:
    """Update order status and append an immutable audit log entry."""
    order = await get_order_by_id(session, order_id)
    if not order:
        return None

    old_status = order.status
    order.status = new_status
    if new_status == "APPROVED":
        order.approved_by_user_id = action_user_id
        order.approved_at = datetime.now(timezone.utc)

    # Record Audit Log
    audit = AuditLog(
        id=uuid.uuid4(),
        entity_name="Order",
        entity_id=str(order.id),
        action="UPDATE_STATUS",
        order_id=order.id,
        user_id=action_user_id,
        old_values={"status": old_status},
        new_values={"status": new_status},
        reason=reason,
    )
    session.add(audit)
    await session.commit()
    await session.refresh(order)
    return order

