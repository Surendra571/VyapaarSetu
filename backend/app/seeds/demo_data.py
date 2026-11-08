"""
Synthetic demo data seeder for VyapaarSetu.
Clearly marks all generated pricing, credit limits, and balances as DEMO ASSUMPTIONS.
Adheres strictly to business constraints:
- Price basis per pack/case is marked UNRESOLVED_PACK_OR_CASE
- Zero GST calculations
"""
import asyncio
from decimal import Decimal
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import (
    User,
    Retailer,
    Product,
    Inventory,
    RetailerPrice,
    Scheme,
    SchemeRule,
    SKUAlias,
    AuditLog,
)


async def seed_demo_data():
    """Seed synthetic master data, catalog, inventory, schemes and retailers."""
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing_user = await session.execute(
            select(User).where(User.phone_number == "9826000000")
        )
        if existing_user.scalar_one_or_none():
            print("Database already contains demo seed data. Skipping seed.")
            return

        print("Seeding synthetic demo data for VyapaarSetu (Jabalpur FMCG)...")

        # ----------------------------------------------------------------------
        # 1. Users & Retailers
        # ----------------------------------------------------------------------
        # 1a. Order Desk Demo User
        desk_user = User(
            id=uuid.uuid4(),
            phone_number="9826000000",
            full_name="Sanjay Sharma (Order Desk Supervisor)",
            role="ROLE_ORDER_DESK",
            is_active=True,
        )
        session.add(desk_user)

        # 1b. Retailer 1: Patel Kirana
        user_ret1 = User(
            id=uuid.uuid4(),
            phone_number="9826011111",
            full_name="Ramesh Patel",
            role="ROLE_RETAILER",
            is_active=True,
        )
        retailer_1 = Retailer(
            id=uuid.uuid4(),
            user=user_ret1,
            retailer_code="RET-JBP-001",
            store_name="Patel Kirana & General Stores",
            owner_name="Ramesh Patel",
            address="Gorakhpur Main Market, Jabalpur, MP",
            city="Jabalpur",
            gst_number="23AAACP1234A1Z5",
            # Demo Assumptions:
            credit_limit=Decimal("50000.00"),
            outstanding_amount=Decimal("18400.00"),
            available_credit=Decimal("31600.00"),
            is_credit_locked=False,
            pricing_tier="TIER_GOLD",
        )
        session.add_all([user_ret1, retailer_1])

        # 1c. Retailer 2: Agrawal Provision (Near credit limit for testing)
        user_ret2 = User(
            id=uuid.uuid4(),
            phone_number="9826022222",
            full_name="Mohan Lal Agrawal",
            role="ROLE_RETAILER",
            is_active=True,
        )
        retailer_2 = Retailer(
            id=uuid.uuid4(),
            user=user_ret2,
            retailer_code="RET-JBP-002",
            store_name="Agrawal Provision Store",
            owner_name="Mohan Lal Agrawal",
            address="Sadar Cantonment Bazar, Jabalpur, MP",
            city="Jabalpur",
            gst_number="23AABCA5678B1Z2",
            # Demo Assumptions:
            credit_limit=Decimal("100000.00"),
            outstanding_amount=Decimal("92500.00"),
            available_credit=Decimal("7500.00"),  # Low available credit for hold simulation
            is_credit_locked=False,
            pricing_tier="TIER_SILVER",
        )
        session.add_all([user_ret2, retailer_2])

        # 1d. Retailer 3: Mahaveer Daily Needs (Credit Locked for testing)
        user_ret3 = User(
            id=uuid.uuid4(),
            phone_number="9826033333",
            full_name="Sunil Jain",
            role="ROLE_RETAILER",
            is_active=True,
        )
        retailer_3 = Retailer(
            id=uuid.uuid4(),
            user=user_ret3,
            retailer_code="RET-JBP-003",
            store_name="Mahaveer Daily Needs",
            owner_name="Sunil Jain",
            address="Wright Town, Near Stadium, Jabalpur, MP",
            city="Jabalpur",
            gst_number=None,
            # Demo Assumptions:
            credit_limit=Decimal("25000.00"),
            outstanding_amount=Decimal("25000.00"),
            available_credit=Decimal("0.00"),
            is_credit_locked=True,  # Credit hold state
            pricing_tier="STANDARD",
        )
        session.add_all([user_ret3, retailer_3])

        # ----------------------------------------------------------------------
        # 2. Approved Products & Inventory
        # ----------------------------------------------------------------------
        # Product 1: SKU-BS-075 (Glucose biscuit 75 g, Case of 96, ₹8.10, 340 cases)
        prod_biscuit = Product(
            id=uuid.uuid4(),
            sku_code="SKU-BS-075",
            name="Glucose Biscuit 75g",
            brand="Parle",
            category="Packaged Food",
            pack_size_description="75 g",
            units_per_case=96,
            default_dealer_price=Decimal("8.10"),
            mrp=Decimal("10.00"),
            # Basis unresolved per constraint 1:
            price_basis="UNRESOLVED_PACK_OR_CASE",
            image_url="/images/products/SKU-BS-075.webp",
            is_active=True,
        )
        inv_biscuit = Inventory(
            product=prod_biscuit,
            stock_cases=340,
            reserved_cases=0,
            available_cases=340,
            reorder_level_cases=30,
        )

        # Product 2: SKU-DT-1KG (Detergent powder 1 kg, Case of 20, ₹101.50, 85 cases)
        prod_detergent = Product(
            id=uuid.uuid4(),
            sku_code="SKU-DT-1KG",
            name="Detergent Powder 1kg",
            brand="Surf",
            category="Home Care",
            pack_size_description="1 kg",
            units_per_case=20,
            default_dealer_price=Decimal("101.50"),
            mrp=Decimal("125.00"),
            # Basis unresolved per constraint 1:
            price_basis="UNRESOLVED_PACK_OR_CASE",
            image_url="/images/products/SKU-DT-1KG.webp",
            is_active=True,
        )
        inv_detergent = Inventory(
            product=prod_detergent,
            stock_cases=85,
            reserved_cases=0,
            available_cases=85,
            reorder_level_cases=15,
        )

        # Product 3: SKU-TE-250 (Tea leaf 250 g, Case of 40, ₹118.00, 0 cases - Stockout)
        prod_tea = Product(
            id=uuid.uuid4(),
            sku_code="SKU-TE-250",
            name="Tea Leaf 250g",
            brand="Tata Tea",
            category="Packaged Food",
            pack_size_description="250 g",
            units_per_case=40,
            default_dealer_price=Decimal("118.00"),
            mrp=Decimal("140.00"),
            # Basis unresolved per constraint 1:
            price_basis="UNRESOLVED_PACK_OR_CASE",
            image_url="/images/products/SKU-TE-250.webp",
            is_active=True,
        )
        inv_tea = Inventory(
            product=prod_tea,
            stock_cases=0,
            reserved_cases=0,
            available_cases=0,
            reorder_level_cases=20,
        )

        session.add_all([
            prod_biscuit, inv_biscuit,
            prod_detergent, inv_detergent,
            prod_tea, inv_tea,
        ])

        # ----------------------------------------------------------------------
        # 3. Trade Promotion Schemes
        # ----------------------------------------------------------------------
        # Scheme 1: Buy 10 cases, get 1 free on SKU-BS-075
        scheme_biscuit = Scheme(
            id=uuid.uuid4(),
            scheme_code="SCH-BS-10P1",
            name="Buy 10 Cases Biscuit Get 1 Case Free",
            description="Buy 10 cases of Glucose Biscuit 75g and receive 1 case free of charge.",
            is_active=True,
            is_stackable=False,  # Business Constraint 3
            priority=1,
        )
        rule_biscuit = SchemeRule(
            id=uuid.uuid4(),
            scheme=scheme_biscuit,
            rule_type="BUY_X_GET_Y_FREE",
            qualifying_product=prod_biscuit,
            min_quantity=10,
            free_product=prod_biscuit,
            free_quantity=1,
        )

        # Scheme 2: 3% discount on 5 or more cases on SKU-DT-1KG
        scheme_detergent = Scheme(
            id=uuid.uuid4(),
            scheme_code="SCH-DT-5DISC3",
            name="3% Volume Discount on 5+ Detergent Cases",
            description="Order 5 or more cases of Detergent Powder 1kg and receive 3% invoice discount (Excl. GST).",
            is_active=True,
            is_stackable=False,  # Business Constraint 3
            priority=2,
        )
        rule_detergent = SchemeRule(
            id=uuid.uuid4(),
            scheme=scheme_detergent,
            rule_type="PERCENTAGE_DISCOUNT",
            qualifying_product=prod_detergent,
            min_quantity=5,
            discount_percentage=Decimal("3.00"),
        )

        session.add_all([scheme_biscuit, rule_biscuit, scheme_detergent, rule_detergent])

        # ----------------------------------------------------------------------
        # 4. Retailer Custom Pricing (Demo Assumptions)
        # ----------------------------------------------------------------------
        price_ret1_biscuit = RetailerPrice(
            id=uuid.uuid4(),
            retailer=retailer_1,
            product=prod_biscuit,
            custom_price=Decimal("7.90"),  # Discounted from ₹8.10
            price_basis="UNRESOLVED_PACK_OR_CASE",
        )
        price_ret1_detergent = RetailerPrice(
            id=uuid.uuid4(),
            retailer=retailer_1,
            product=prod_detergent,
            custom_price=Decimal("99.00"),  # Discounted from ₹101.50
            price_basis="UNRESOLVED_PACK_OR_CASE",
        )
        price_ret2_detergent = RetailerPrice(
            id=uuid.uuid4(),
            retailer=retailer_2,
            product=prod_detergent,
            custom_price=Decimal("98.50"),  # Discounted from ₹101.50
            price_basis="UNRESOLVED_PACK_OR_CASE",
        )

        session.add_all([price_ret1_biscuit, price_ret1_detergent, price_ret2_detergent])

        # ----------------------------------------------------------------------
        # 5. SKU Aliases for AI Matching
        # ----------------------------------------------------------------------
        aliases = [
            # Biscuit Aliases
            SKUAlias(id=uuid.uuid4(), product=prod_biscuit, retailer=None, alias_text="parle g"),
            SKUAlias(id=uuid.uuid4(), product=prod_biscuit, retailer=None, alias_text="glucose biscuit"),
            SKUAlias(id=uuid.uuid4(), product=prod_biscuit, retailer=None, alias_text="parle biscuit 75g"),
            SKUAlias(id=uuid.uuid4(), product=prod_biscuit, retailer=retailer_1, alias_text="chhota parle"),
            # Detergent Aliases
            SKUAlias(id=uuid.uuid4(), product=prod_detergent, retailer=None, alias_text="surf excel 1kg"),
            SKUAlias(id=uuid.uuid4(), product=prod_detergent, retailer=None, alias_text="surf powder"),
            SKUAlias(id=uuid.uuid4(), product=prod_detergent, retailer=None, alias_text="detergent 1kg"),
            SKUAlias(id=uuid.uuid4(), product=prod_detergent, retailer=retailer_2, alias_text="surf bada"),
            # Tea Aliases
            SKUAlias(id=uuid.uuid4(), product=prod_tea, retailer=None, alias_text="chai patti"),
            SKUAlias(id=uuid.uuid4(), product=prod_tea, retailer=None, alias_text="tata tea 250g"),
            SKUAlias(id=uuid.uuid4(), product=prod_tea, retailer=None, alias_text="tea leaf 250g"),
        ]
        session.add_all(aliases)

        # ----------------------------------------------------------------------
        # 6. Initial Audit Log
        # ----------------------------------------------------------------------
        audit_init = AuditLog(
            id=uuid.uuid4(),
            entity_name="Database",
            entity_id="MASTER_SEED",
            action="CREATE",
            user=desk_user,
            reason="Initialized Phase 2 synthetic demo data seed for Jabalpur FMCG",
            new_values={
                "products_seeded": 3,
                "retailers_seeded": 3,
                "schemes_seeded": 2,
                "note": "Demo prices and balances are working assumptions; price basis marked unresolved",
            },
        )
        session.add(audit_init)

        await session.commit()
        print("Successfully seeded all synthetic demo data!")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())

