from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.database import AsyncSessionLocal
from app.models import (
    User,
    Retailer,
    Product,
    Inventory,
    RetailerPrice,
    Scheme,
    SchemeRule,
    Order,
    OrderItem,
    SKUAlias,
    AuditLog,
)
from app.repositories import (
    get_retailer_by_code,
    get_product_by_sku,
    get_retailer_effective_price,
    find_products_by_alias,
    update_order_status,
)


@pytest.mark.asyncio
async def test_seed_data_correctness():
    """Verify that all seed entities match exact approved business requirements."""
    async with AsyncSessionLocal() as session:
        # 1. Verify 3 synthetic products
        biscuit = await get_product_by_sku(session, "SKU-BS-075")
        assert biscuit is not None
        assert biscuit.name == "Glucose Biscuit 75g"
        assert biscuit.units_per_case == 96
        assert biscuit.default_dealer_price == Decimal("8.10")
        assert biscuit.price_basis == "UNRESOLVED_PACK_OR_CASE"
        assert biscuit.inventory.stock_cases > 0
        assert biscuit.inventory.available_cases == biscuit.inventory.stock_cases - biscuit.inventory.reserved_cases

        detergent = await get_product_by_sku(session, "SKU-DT-1KG")
        assert detergent is not None
        assert detergent.units_per_case == 20
        assert detergent.default_dealer_price == Decimal("101.50")
        assert detergent.inventory.stock_cases > 0
        assert detergent.inventory.available_cases == detergent.inventory.stock_cases - detergent.inventory.reserved_cases

        tea = await get_product_by_sku(session, "SKU-TE-250")
        assert tea is not None
        assert tea.units_per_case == 40
        assert tea.default_dealer_price == Decimal("118.00")
        assert tea.inventory.stock_cases == 0
        assert tea.inventory.available_cases == 0

        # 2. Verify Retailers and isolated credit fields (Constraint 5)
        ret1 = await get_retailer_by_code(session, "RET-JBP-001")
        assert ret1 is not None
        assert ret1.credit_limit == Decimal("50000.00")
        assert ret1.available_credit == ret1.credit_limit - ret1.outstanding_amount
        assert ret1.outstanding_amount > Decimal("0.00")
        assert ret1.is_credit_locked is False

        ret3 = await get_retailer_by_code(session, "RET-JBP-003")
        assert ret3 is not None
        assert ret3.available_credit == Decimal("0.00")
        assert ret3.is_credit_locked is True

        # 3. Verify Order Desk User
        desk_user_res = await session.execute(
            select(User).where(User.role == "ROLE_ORDER_DESK")
        )
        desk_user = desk_user_res.scalar_one_or_none()
        assert desk_user is not None
        assert desk_user.phone_number == "9826000000"

        # 4. Verify Schemes and Non-Stacking configuration (Constraint 3)
        scheme_biscuit_res = await session.execute(
            select(Scheme).where(Scheme.scheme_code == "SCH-BS-10P1")
        )
        scheme_biscuit = scheme_biscuit_res.scalar_one_or_none()
        assert scheme_biscuit is not None
        assert scheme_biscuit.is_stackable is False
        assert len(scheme_biscuit.rules) == 1
        assert scheme_biscuit.rules[0].min_quantity == 10
        assert scheme_biscuit.rules[0].free_quantity == 1


@pytest.mark.asyncio
async def test_unique_sku_constraint():
    """Verify that inserting duplicate SKU code violates database constraint."""
    async with AsyncSessionLocal() as session:
        duplicate_prod = Product(
            id=uuid.uuid4(),
            sku_code="SKU-BS-075",  # Already exists in seed data
            name="Duplicate Biscuit",
            brand="Parle",
            category="Food",
            pack_size_description="75 g",
            units_per_case=96,
            default_dealer_price=Decimal("8.10"),
            price_basis="UNRESOLVED_PACK_OR_CASE",
        )
        session.add(duplicate_prod)
        try:
            await session.commit()
            pytest.fail("Expected IntegrityError on duplicate SKU")
        except IntegrityError:
            await session.rollback()


@pytest.mark.asyncio
async def test_retailer_custom_pricing_resolution():
    """Verify retailer-specific pricing override vs catalog fallback."""
    async with AsyncSessionLocal() as session:
        ret1 = await get_retailer_by_code(session, "RET-JBP-001")
        ret2 = await get_retailer_by_code(session, "RET-JBP-002")
        biscuit = await get_product_by_sku(session, "SKU-BS-075")

        # Retailer 1 has contracted custom price ₹7.90
        price1, basis1, is_custom1 = await get_retailer_effective_price(
            session, ret1.id, biscuit.id
        )
        assert price1 == Decimal("7.90")
        assert is_custom1 is True

        # Retailer 2 has no custom price for biscuit, falls back to default ₹8.10
        price2, basis2, is_custom2 = await get_retailer_effective_price(
            session, ret2.id, biscuit.id
        )
        assert price2 == Decimal("8.10")
        assert is_custom2 is False


@pytest.mark.asyncio
async def test_order_creation_with_snapshots_and_audit():
    """Verify order relationships, point-in-time snapshots, and audit logging."""
    async with AsyncSessionLocal() as session:
        ret1 = await get_retailer_by_code(session, "RET-JBP-001")
        biscuit = await get_product_by_sku(session, "SKU-BS-075")

        test_order_number = f"TEST-ORD-{uuid.uuid4().hex[:6].upper()}"
        order = Order(
            id=uuid.uuid4(),
            order_number=test_order_number,
            retailer_id=ret1.id,
            status="PENDING_DESK_APPROVAL",
            subtotal_excl_gst=Decimal("81.00"),  # Excl. GST
        )

        item = OrderItem(
            id=uuid.uuid4(),
            order=order,
            product_id=biscuit.id,
            ordered_qty=10,
            approved_qty=10,
            uom_type="CASE",
            scheme_discount_amount=Decimal("0.00"),
            free_item_qty=1,
            line_subtotal_excl_gst=Decimal("81.00"),
            # Snapshots:
            product_name_snapshot="Glucose Biscuit 75g",
            sku_code_snapshot="SKU-BS-075",
            price_per_unit_snapshot=Decimal("8.10"),
            price_basis_snapshot="UNRESOLVED_PACK_OR_CASE",
            scheme_name_snapshot="Buy 10 Cases Biscuit Get 1 Case Free",
        )
        session.add_all([order, item])
        await session.commit()

        # Update order status to APPROVED and verify Audit Log
        desk_user_res = await session.execute(
            select(User).where(User.role == "ROLE_ORDER_DESK")
        )
        desk_user = desk_user_res.scalar_one()

        updated_order = await update_order_status(
            session,
            order.id,
            new_status="APPROVED",
            action_user_id=desk_user.id,
            reason="Desk verification completed with physical stock check",
        )
        assert updated_order.status == "APPROVED"
        assert updated_order.approved_by_user_id == desk_user.id
        assert updated_order.approved_at is not None

        # Verify audit log recorded
        audit_res = await session.execute(
            select(AuditLog).where(AuditLog.order_id == order.id)
        )
        audit_entry = audit_res.scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.action == "UPDATE_STATUS"
        assert audit_entry.old_values == {"status": "PENDING_DESK_APPROVAL"}
        assert audit_entry.new_values == {"status": "APPROVED"}


@pytest.mark.asyncio
async def test_sku_alias_matching():
    """Verify global and retailer-specific natural language alias lookups."""
    async with AsyncSessionLocal() as session:
        ret1 = await get_retailer_by_code(session, "RET-JBP-001")
        ret2 = await get_retailer_by_code(session, "RET-JBP-002")

        # Global alias "parle g" matches SKU-BS-075 for any retailer
        global_matches = await find_products_by_alias(session, "parle g", retailer_id=ret2.id)
        assert len(global_matches) == 1
        assert global_matches[0].sku_code == "SKU-BS-075"

        # Retailer 1 custom alias "chhota parle" matches for Retailer 1
        ret1_matches = await find_products_by_alias(session, "chhota parle", retailer_id=ret1.id)
        assert len(ret1_matches) == 1
        assert ret1_matches[0].sku_code == "SKU-BS-075"

        # Retailer 2 does NOT match Retailer 1's private alias
        ret2_matches = await find_products_by_alias(session, "chhota parle", retailer_id=ret2.id)
        assert len(ret2_matches) == 0
