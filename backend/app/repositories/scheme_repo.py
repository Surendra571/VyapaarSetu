import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.pricing import Scheme, SchemeRule


async def list_active_schemes(session: AsyncSession) -> List[Scheme]:
    """Retrieve all active trade schemes with rules."""
    stmt = (
        select(Scheme)
        .where(Scheme.is_active == True)
        .options(
            selectinload(Scheme.rules).selectinload(SchemeRule.qualifying_product),
            selectinload(Scheme.rules).selectinload(SchemeRule.free_product),
        )
        .order_by(Scheme.priority)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_schemes_for_product(
    session: AsyncSession,
    product_id: uuid.UUID,
) -> List[Scheme]:
    """Find active schemes qualifying a specific product."""
    stmt = (
        select(Scheme)
        .join(SchemeRule, SchemeRule.scheme_id == Scheme.id)
        .where(
            Scheme.is_active == True,
            SchemeRule.qualifying_product_id == product_id,
        )
        .options(selectinload(Scheme.rules))
        .order_by(Scheme.priority)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())

