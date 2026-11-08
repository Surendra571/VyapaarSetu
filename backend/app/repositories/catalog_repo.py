import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.catalog import Product, Inventory, SKUAlias
from app.models.pricing import RetailerPrice


async def get_product_by_id(
    session: AsyncSession,
    product_id: uuid.UUID,
) -> Optional[Product]:
    """Fetch product by primary key with inventory loaded."""
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.inventory))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_product_by_sku(
    session: AsyncSession,
    sku_code: str,
) -> Optional[Product]:
    """Fetch product by unique SKU code."""
    stmt = (
        select(Product)
        .where(Product.sku_code == sku_code)
        .options(selectinload(Product.inventory))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_products(
    session: AsyncSession,
    category: Optional[str] = None,
    only_active: bool = True,
) -> List[Product]:
    """List products with inventory."""
    stmt = (
        select(Product)
        .options(selectinload(Product.inventory))
        .order_by(Product.name)
    )
    if only_active:
        stmt = stmt.where(Product.is_active == True)
    if category:
        stmt = stmt.where(Product.category == category)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_retailer_effective_price(
    session: AsyncSession,
    retailer_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Tuple[Decimal, str, bool]:
    """
    Resolve effective dealer price for a retailer.
    Returns: (effective_price, price_basis, is_custom_price)
    Falls back to Product.default_dealer_price if no retailer-specific price is active.
    """
    # Check for custom price
    custom_stmt = (
        select(RetailerPrice)
        .where(
            RetailerPrice.retailer_id == retailer_id,
            RetailerPrice.product_id == product_id,
        )
    )
    custom_res = await session.execute(custom_stmt)
    custom_price = custom_res.scalar_one_or_none()

    if custom_price:
        return (custom_price.custom_price, custom_price.price_basis, True)

    # Fallback to master catalog
    product_stmt = select(Product).where(Product.id == product_id)
    product_res = await session.execute(product_stmt)
    product = product_res.scalar_one_or_none()

    if not product:
        raise ValueError(f"Product {product_id} does not exist.")

    return (product.default_dealer_price, product.price_basis, False)


async def find_products_by_alias(
    session: AsyncSession,
    alias_query: str,
    retailer_id: Optional[uuid.UUID] = None,
) -> List[Product]:
    """
    Find matching products by alias query (checks global and retailer-specific aliases).
    """
    cleaned_query = alias_query.strip().lower()
    stmt = (
        select(Product)
        .join(SKUAlias, SKUAlias.product_id == Product.id)
        .where(
            SKUAlias.alias_text == cleaned_query,
            or_(
                SKUAlias.retailer_id == retailer_id,
                SKUAlias.retailer_id.is_(None),
            ),
        )
        .options(selectinload(Product.inventory))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())

