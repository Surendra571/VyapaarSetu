import uuid
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.catalog import Inventory


class InventoryService:
    """Thread-safe inventory check and reservation engine using row locks."""

    @staticmethod
    async def get_availability(
        session: AsyncSession,
        product_id: uuid.UUID,
    ) -> Tuple[int, int, int]:
        """Returns: (stock_cases, reserved_cases, available_cases)."""
        stmt = select(Inventory).where(Inventory.product_id == product_id)
        result = await session.execute(stmt)
        inv = result.scalar_one_or_none()
        if not inv:
            return (0, 0, 0)
        return (inv.stock_cases, inv.reserved_cases, inv.available_cases)

    @staticmethod
    async def reserve_inventory(
        session: AsyncSession,
        product_id: uuid.UUID,
        cases_to_reserve: int,
    ) -> bool:
        """
        Atomically reserve inventory cases for a newly submitted order.
        Returns True if reservation was successful, False if insufficient stock.
        """
        # Select row FOR UPDATE to prevent race conditions during concurrent orders
        stmt = (
            select(Inventory)
            .where(Inventory.product_id == product_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        inv = result.scalar_one_or_none()

        if not inv or inv.available_cases < cases_to_reserve:
            return False

        inv.reserved_cases += cases_to_reserve
        inv.available_cases = inv.stock_cases - inv.reserved_cases
        return True

    @staticmethod
    async def release_reserved_inventory(
        session: AsyncSession,
        product_id: uuid.UUID,
        cases_to_release: int,
    ) -> None:
        """Release previously reserved cases upon order cancellation or rejection."""
        stmt = (
            select(Inventory)
            .where(Inventory.product_id == product_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        inv = result.scalar_one_or_none()
        if inv:
            inv.reserved_cases = max(0, inv.reserved_cases - cases_to_release)
            inv.available_cases = inv.stock_cases - inv.reserved_cases

    @staticmethod
    async def commit_stock_deduction(
        session: AsyncSession,
        product_id: uuid.UUID,
        cases_to_deduct: int,
    ) -> None:
        """Deduct physical stock upon final order approval / dispatch."""
        stmt = (
            select(Inventory)
            .where(Inventory.product_id == product_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        inv = result.scalar_one_or_none()
        if inv:
            inv.stock_cases = max(0, inv.stock_cases - cases_to_deduct)
            inv.reserved_cases = max(0, inv.reserved_cases - cases_to_deduct)
            inv.available_cases = inv.stock_cases - inv.reserved_cases

