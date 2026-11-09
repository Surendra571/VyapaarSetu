"""
Synthetic demo data seeder for VyapaarSetu.
Clearly marks all generated pricing, credit limits, and balances as DEMO ASSUMPTIONS.
Adheres strictly to business constraints:
- Price basis per pack/case is marked UNRESOLVED_PACK_OR_CASE
- Zero GST calculations
"""
import asyncio
from datetime import datetime, timezone
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
    Order,
    OrderItem,
    OrderItemBenefit,
)


async def seed_demo_data():
    """Seed synthetic master data, catalog, inventory, schemes, retailers, and realistic demo orders."""
    async with AsyncSessionLocal() as session:
        # Check if master data already seeded
        existing_user = await session.execute(
            select(User).where(User.phone_number == "9826000000")
        )
        if existing_user.scalar_one_or_none():
            print("Database already contains master demo seed data. Checking orders...")
            await seed_demo_orders(session)
            await session.commit()
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
        await seed_demo_orders(session)
        await session.commit()
        print("Successfully seeded all synthetic demo data!")


async def seed_demo_orders(session):
    """Seed realistic demo orders for Order Desk verification (PENDING, CREDIT_HOLD, APPROVED)."""
    existing_orders = await session.execute(select(Order).limit(1))
    if existing_orders.scalar_one_or_none():
        print("Database already contains orders. Skipping order seed.")
        return

    print("Seeding realistic demo orders for Order Desk verification...")
    # Fetch required master references
    desk_user = (await session.execute(select(User).where(User.phone_number == "9826000000"))).scalar_one_or_none()
    ret1 = (await session.execute(select(Retailer).where(Retailer.retailer_code == "RET-JBP-001"))).scalar_one_or_none()
    ret2 = (await session.execute(select(Retailer).where(Retailer.retailer_code == "RET-JBP-002"))).scalar_one_or_none()
    prod_biscuit = (await session.execute(select(Product).where(Product.sku_code == "SKU-BS-075"))).scalar_one_or_none()
    prod_detergent = (await session.execute(select(Product).where(Product.sku_code == "SKU-DT-1KG"))).scalar_one_or_none()
    scheme_biscuit = (await session.execute(select(Scheme).where(Scheme.scheme_code == "SCH-BS-10P1"))).scalar_one_or_none()
    scheme_detergent = (await session.execute(select(Scheme).where(Scheme.scheme_code == "SCH-DT-5DISC3"))).scalar_one_or_none()

    if not (desk_user and ret1 and ret2 and prod_biscuit and prod_detergent):
        print("Missing master records needed for demo orders. Skipping order seed.")
        return

    # --------------------------------------------------------------------------
    # ORDER 1: PENDING_DESK_APPROVAL (Patel Kirana)
    # Includes schemes: Buy 10 Get 1 Free on Biscuits, 3% discount on Detergent
    # --------------------------------------------------------------------------
    ord1_id = uuid.uuid4()
    order1 = Order(
        id=ord1_id,
        order_number="ORD-2026-001",
        retailer_id=ret1.id,
        status="PENDING_DESK_APPROVAL",
        subtotal_excl_gst=Decimal("20624.40"),
        credit_hold_reason=None,
        desk_notes="Kirana app order. Review scheme free-goods benefits and stock allocation.",
    )
    # Line 1: 12 cases Glucose Biscuit (qualifies for Buy 10 Get 1 Free)
    item1_1 = OrderItem(
        id=uuid.uuid4(),
        order_id=ord1_id,
        product_id=prod_biscuit.id,
        ordered_qty=12,
        approved_qty=12,
        uom_type="CASE",
        applied_scheme_id=scheme_biscuit.id if scheme_biscuit else None,
        scheme_discount_amount=Decimal("0.00"),
        free_item_qty=1,
        line_subtotal_excl_gst=Decimal("9100.80"),
        product_name_snapshot="Glucose Biscuit 75g",
        sku_code_snapshot="SKU-BS-075",
        price_per_unit_snapshot=Decimal("7.90"),
        price_basis_snapshot="UNRESOLVED_PACK_OR_CASE",
        scheme_name_snapshot="Buy 10 Cases Biscuit Get 1 Case Free",
        free_product_name_snapshot="Glucose Biscuit 75g",
        free_sku_code_snapshot="SKU-BS-075",
    )
    benefit1_1 = OrderItemBenefit(
        id=uuid.uuid4(),
        order_item=item1_1,
        scheme_id=scheme_biscuit.id if scheme_biscuit else None,
        scheme_name="Buy 10 Cases Biscuit Get 1 Case Free",
        benefit_type="FREE_GOODS",
        awarded_product_id=prod_biscuit.id,
        awarded_sku_code="SKU-BS-075",
        awarded_product_name="Glucose Biscuit 75g",
        awarded_quantity=1,
        awarded_uom="CASE",
        discount_amount=Decimal("0.00"),
        calculation_details="Ordered 12 cases >= 10 cases threshold. 1 promotional free case awarded.",
    )
    # Line 2: 6 cases Detergent Powder (qualifies for 3% volume discount)
    item1_2 = OrderItem(
        id=uuid.uuid4(),
        order_id=ord1_id,
        product_id=prod_detergent.id,
        ordered_qty=6,
        approved_qty=6,
        uom_type="CASE",
        applied_scheme_id=scheme_detergent.id if scheme_detergent else None,
        scheme_discount_amount=Decimal("356.40"),
        free_item_qty=0,
        line_subtotal_excl_gst=Decimal("11523.60"),
        product_name_snapshot="Detergent Powder 1kg",
        sku_code_snapshot="SKU-DT-1KG",
        price_per_unit_snapshot=Decimal("99.00"),
        price_basis_snapshot="UNRESOLVED_PACK_OR_CASE",
        scheme_name_snapshot="3% Volume Discount on 5+ Detergent Cases",
        discount_percentage_snapshot=Decimal("3.00"),
    )
    benefit1_2 = OrderItemBenefit(
        id=uuid.uuid4(),
        order_item=item1_2,
        scheme_id=scheme_detergent.id if scheme_detergent else None,
        scheme_name="3% Volume Discount on 5+ Detergent Cases",
        benefit_type="SLAB_DISCOUNT",
        awarded_product_id=None,
        awarded_quantity=0,
        awarded_uom="CASE",
        discount_amount=Decimal("356.40"),
        calculation_details="Ordered 6 cases >= 5 cases threshold. 3% discount applied to line subtotal.",
    )
    audit1 = AuditLog(
        id=uuid.uuid4(),
        entity_name="Order",
        entity_id=str(ord1_id),
        action="CREATE",
        order=order1,
        user_id=ret1.user_id,
        reason="Retailer submitted order via VyapaarSetu App",
        new_values={"order_number": "ORD-2026-001", "status": "PENDING_DESK_APPROVAL", "total_excl_gst": "20624.40"},
    )
    session.add_all([order1, item1_1, benefit1_1, item1_2, benefit1_2, audit1])

    # --------------------------------------------------------------------------
    # ORDER 2: CREDIT_HOLD (Agrawal Provision)
    # Order total (₹17,730.00) exceeds remaining available credit (₹7,500.00)
    # --------------------------------------------------------------------------
    ord2_id = uuid.uuid4()
    order2 = Order(
        id=ord2_id,
        order_number="ORD-2026-002",
        retailer_id=ret2.id,
        status="CREDIT_HOLD",
        subtotal_excl_gst=Decimal("17730.00"),
        credit_hold_reason="Order total (₹17,730.00) exceeds available credit limit (₹7,500.00)",
        desk_notes="Requires supervisor credit override or partial advance payment before release.",
    )
    item2_1 = OrderItem(
        id=uuid.uuid4(),
        order_id=ord2_id,
        product_id=prod_detergent.id,
        ordered_qty=9,
        approved_qty=9,
        uom_type="CASE",
        applied_scheme_id=None,
        scheme_discount_amount=Decimal("0.00"),
        free_item_qty=0,
        line_subtotal_excl_gst=Decimal("17730.00"),
        product_name_snapshot="Detergent Powder 1kg",
        sku_code_snapshot="SKU-DT-1KG",
        price_per_unit_snapshot=Decimal("98.50"),
        price_basis_snapshot="UNRESOLVED_PACK_OR_CASE",
    )
    audit2 = AuditLog(
        id=uuid.uuid4(),
        entity_name="Order",
        entity_id=str(ord2_id),
        action="HOLD",
        order=order2,
        user_id=ret2.user_id,
        reason="Credit check failed: outstanding balance ₹92,500 + order ₹17,730 exceeds ₹100,000 credit limit",
        new_values={"order_number": "ORD-2026-002", "status": "CREDIT_HOLD", "credit_limit": "100000.00", "outstanding": "92500.00"},
    )
    session.add_all([order2, item2_1, audit2])

    # --------------------------------------------------------------------------
    # ORDER 3: APPROVED (Patel Kirana)
    # Ready for Van Loading and Tally Export
    # --------------------------------------------------------------------------
    ord3_id = uuid.uuid4()
    order3 = Order(
        id=ord3_id,
        order_number="ORD-2026-003",
        retailer_id=ret1.id,
        status="APPROVED",
        subtotal_excl_gst=Decimal("7584.00"),
        desk_notes="Approved for Zone 1 morning van dispatch.",
        approved_by_user_id=desk_user.id,
        approved_at=datetime.now(timezone.utc),
    )
    item3_1 = OrderItem(
        id=uuid.uuid4(),
        order_id=ord3_id,
        product_id=prod_biscuit.id,
        ordered_qty=10,
        approved_qty=10,
        uom_type="CASE",
        applied_scheme_id=scheme_biscuit.id if scheme_biscuit else None,
        scheme_discount_amount=Decimal("0.00"),
        free_item_qty=1,
        line_subtotal_excl_gst=Decimal("7584.00"),
        product_name_snapshot="Glucose Biscuit 75g",
        sku_code_snapshot="SKU-BS-075",
        price_per_unit_snapshot=Decimal("7.90"),
        price_basis_snapshot="UNRESOLVED_PACK_OR_CASE",
        scheme_name_snapshot="Buy 10 Cases Biscuit Get 1 Case Free",
        free_product_name_snapshot="Glucose Biscuit 75g",
        free_sku_code_snapshot="SKU-BS-075",
    )
    benefit3_1 = OrderItemBenefit(
        id=uuid.uuid4(),
        order_item=item3_1,
        scheme_id=scheme_biscuit.id if scheme_biscuit else None,
        scheme_name="Buy 10 Cases Biscuit Get 1 Case Free",
        benefit_type="FREE_GOODS",
        awarded_product_id=prod_biscuit.id,
        awarded_sku_code="SKU-BS-075",
        awarded_product_name="Glucose Biscuit 75g",
        awarded_quantity=1,
        awarded_uom="CASE",
        discount_amount=Decimal("0.00"),
        calculation_details="Buy 10 Get 1 Free promotional rule verified and approved.",
    )
    audit3 = AuditLog(
        id=uuid.uuid4(),
        entity_name="Order",
        entity_id=str(ord3_id),
        action="APPROVE",
        order=order3,
        user_id=desk_user.id,
        reason="Order Desk approved lines and allocated stock for van dispatch",
        new_values={"order_number": "ORD-2026-003", "status": "APPROVED", "approved_qty_cases": 10, "free_cases": 1},
    )
    session.add_all([order3, item3_1, benefit3_1, audit3])
    print("Successfully seeded 3 realistic demo orders (PENDING, CREDIT_HOLD, APPROVED)!")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())

