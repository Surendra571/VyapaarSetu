import uuid
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.retailer import Retailer


async def get_retailer_by_id(
    session: AsyncSession,
    retailer_id: uuid.UUID,
) -> Optional[Retailer]:
    """Fetch retailer by primary key UUID."""
    stmt = (
        select(Retailer)
        .where(Retailer.id == retailer_id)
        .options(selectinload(Retailer.user))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_retailer_by_user_id(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[Retailer]:
    """Fetch retailer by associated user ID."""
    stmt = (
        select(Retailer)
        .where(Retailer.user_id == user_id)
        .options(selectinload(Retailer.user))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_retailer_by_code(
    session: AsyncSession,
    retailer_code: str,
) -> Optional[Retailer]:
    """Fetch retailer by unique retailer code."""
    stmt = select(Retailer).where(Retailer.retailer_code == retailer_code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_retailers(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> List[Retailer]:
    """List retailers with pagination."""
    stmt = (
        select(Retailer)
        .order_by(Retailer.store_name)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_retailer_credit_balance(
    session: AsyncSession,
    retailer_id: uuid.UUID,
    new_outstanding: Decimal,
    is_credit_locked: Optional[bool] = None,
) -> Optional[Retailer]:
    """Update retailer outstanding balance and recompute available credit."""
    retailer = await get_retailer_by_id(session, retailer_id)
    if not retailer:
        return None

    retailer.outstanding_amount = new_outstanding
    retailer.available_credit = retailer.credit_limit - new_outstanding
    if is_credit_locked is not None:
        retailer.is_credit_locked = is_credit_locked

    await session.commit()
    await session.refresh(retailer)
    return retailer

