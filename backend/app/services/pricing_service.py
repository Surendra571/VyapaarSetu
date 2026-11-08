import uuid
from decimal import Decimal
from typing import Tuple, List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.catalog import Product
from app.models.pricing import RetailerPrice
from app.schemas.catalog import RetailerPriceResponse


class PricingService:
    """Business service resolving negotiated vs catalog dealer prices (Excl. GST)."""

    @staticmethod
    async def get_effective_price(
        session: AsyncSession,
        retailer_id: uuid.UUID,
        product: Product,
    ) -> Tuple[Decimal, str, bool]:
        """
        Resolves effective price for a retailer.
        Returns: (price, price_basis, is_custom_price)
        """
        stmt = select(RetailerPrice).where(
            RetailerPrice.retailer_id == retailer_id,
            RetailerPrice.product_id == product.id,
        )
        result = await session.execute(stmt)
        custom = result.scalar_one_or_none()

        if custom:
            return (custom.custom_price, custom.price_basis, True)
        return (product.default_dealer_price, product.price_basis, False)

    @staticmethod
    async def get_retailer_full_pricelist(
        session: AsyncSession,
        retailer_id: uuid.UUID,
    ) -> List[RetailerPriceResponse]:
        """Retrieve full active price schedule for the authenticated retailer."""
        # 1. Fetch all active products
        prod_stmt = select(Product).where(Product.is_active == True).order_by(Product.name)
        prod_res = await session.execute(prod_stmt)
        products = prod_res.scalars().all()

        # 2. Fetch all custom prices for this retailer
        price_stmt = select(RetailerPrice).where(RetailerPrice.retailer_id == retailer_id)
        price_res = await session.execute(price_stmt)
        custom_map: Dict[uuid.UUID, RetailerPrice] = {
            cp.product_id: cp for cp in price_res.scalars().all()
        }

        # 3. Assemble response
        price_list: List[RetailerPriceResponse] = []
        for p in products:
            if p.id in custom_map:
                effective = custom_map[p.id].custom_price
                basis = custom_map[p.id].price_basis
                is_custom = True
            else:
                effective = p.default_dealer_price
                basis = p.price_basis
                is_custom = False

            price_list.append(
                RetailerPriceResponse(
                    product_id=p.id,
                    sku_code=p.sku_code,
                    product_name=p.name,
                    effective_price=effective,
                    price_basis=basis,
                    is_custom_price=is_custom,
                    units_per_case=p.units_per_case,
                )
            )
        return price_list

