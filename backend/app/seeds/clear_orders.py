"""
Utility to reset all order transactions for a clean production state.
Leaves master catalogue, products, inventory, prices, schemes, and users untouched.
Results in an empty orders state across Retailer and Order Desk dashboards.
"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def clear_all_orders():
    print("Clearing all orders and transaction logs for clean production state...")
    async with AsyncSessionLocal() as session:
        # Delete dependent tables first or cascade
        await session.execute(text("DELETE FROM order_item_benefits;"))
        await session.execute(text("DELETE FROM order_items;"))
        await session.execute(text("DELETE FROM audit_logs WHERE entity_name = 'Order';"))
        await session.execute(text("DELETE FROM export_batches;"))
        await session.execute(text("DELETE FROM orders;"))
        
        # Reset retailer outstanding amounts back to 0.00 and available credit back to credit_limit
        await session.execute(text("""
            UPDATE retailers
            SET outstanding_amount = 0.00,
                available_credit = credit_limit,
                is_credit_locked = FALSE;
        """))
        
        await session.commit()
        print("Successfully cleared all sample orders! App is now in clean empty-orders production state.")

if __name__ == "__main__":
    asyncio.run(clear_all_orders())
