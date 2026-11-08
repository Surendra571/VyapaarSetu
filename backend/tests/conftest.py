import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.catalog import Product, Inventory


async def _restore_baseline_stock():
    """Restore approved baseline stock levels."""
    async with AsyncSessionLocal() as session:
        prod_res = await session.execute(select(Product))
        products = {p.sku_code: p.id for p in prod_res.scalars().all()}

        target_levels = {
            "SKU-BS-075": 340,
            "SKU-DT-1KG": 85,
            "SKU-TE-250": 0,
        }
        for sku, target_avail in target_levels.items():
            if sku in products:
                inv_res = await session.execute(
                    select(Inventory).where(Inventory.product_id == products[sku])
                )
                inv = inv_res.scalar_one_or_none()
                if inv:
                    inv.available_cases = target_avail
                    inv.stock_cases = target_avail
                    inv.reserved_cases = 0
        await session.commit()


@pytest.fixture(autouse=True)
async def reset_stock_levels():
    """
    Ensure baseline stock availability before and after every test:
    - SKU-BS-075: 340 cases
    - SKU-DT-1KG: 85 cases
    - SKU-TE-250: 0 cases
    Guarantees test idempotency and isolation.
    """
    await _restore_baseline_stock()
    yield
    await _restore_baseline_stock()
