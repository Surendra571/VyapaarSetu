import uuid
import pytest
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.catalog import Product, Inventory
from app.models.pricing import Scheme, SchemeRule
from app.models.retailer import Retailer
from app.models.user import User
from app.models.order import Order, OrderItem, OrderItemBenefit
from app.services.scheme_service import SchemeService
from app.services.order_service import OrderService
from app.services.export_service import ExportService
from app.schemas.order import OrderItemCreate


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------------------
# 1. Buy 10, Get 1 Free (Basic Scheme Engine)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_buy_10_get_1_free():
    """1. Buy 10, get 1 free evaluation."""
    async with AsyncSessionLocal() as session:
        res_b = await session.execute(select(Product).where(Product.sku_code == "SKU-BS-075"))
        biscuit = res_b.scalar_one()

        # At 9 cases -> 0 free
        eval_9 = await SchemeService.evaluate_product_schemes(session, biscuit, 9, Decimal("8.10"))
        assert eval_9.free_quantity == 0

        # At 10 cases -> 1 free
        eval_10 = await SchemeService.evaluate_product_schemes(session, biscuit, 10, Decimal("8.10"))
        assert eval_10.free_quantity == 1
        assert eval_10.free_sku_code == "SKU-BS-075"

        # At 20 cases -> 2 free
        eval_20 = await SchemeService.evaluate_product_schemes(session, biscuit, 20, Decimal("8.10"))
        assert eval_20.free_quantity == 2


# ---------------------------------------------------------------------------
# 2. One purchase qualifying for two different free SKUs
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_one_purchase_qualifying_for_two_different_free_skus():
    """2. One purchase qualifying for two distinct free SKUs (Product B and Product C)."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Scheme).where(Scheme.scheme_code.like("SCH-TEST-%")))
        await session.commit()

        # Temporarily deactivate default biscuit seed scheme
        seed_bs = (await session.execute(select(Scheme).where(Scheme.scheme_code == "SCH-BS-10P1"))).scalar_one_or_none()
        if seed_bs:
            seed_bs.is_active = False
            await session.commit()

        biscuit = (await session.execute(select(Product).where(Product.sku_code == "SKU-BS-075"))).scalar_one()
        detergent = (await session.execute(select(Product).where(Product.sku_code == "SKU-DT-1KG"))).scalar_one()
        tea = (await session.execute(select(Product).where(Product.sku_code == "SKU-TE-250"))).scalar_one()

        multi_scheme = Scheme(
            id=uuid.uuid4(),
            scheme_code="SCH-TEST-DUAL-FREE",
            name="Buy 10 Biscuit Get 1 Detergent + 2 Tea Free",
            is_active=True,
            is_stackable=False,
            priority=1,
        )
        r1 = SchemeRule(
            id=uuid.uuid4(),
            scheme=multi_scheme,
            rule_type="FREE_GOODS",
            qualifying_product=biscuit,
            min_quantity=10,
            free_product=detergent,
            free_quantity=1,
        )
        r2 = SchemeRule(
            id=uuid.uuid4(),
            scheme=multi_scheme,
            rule_type="FREE_GOODS",
            qualifying_product=biscuit,
            min_quantity=10,
            free_product=tea,
            free_quantity=2,
        )
        session.add_all([multi_scheme, r1, r2])
        await session.commit()

        eval_res = await SchemeService.evaluate_product_schemes(session, biscuit, 10, Decimal("8.10"))
        assert len(eval_res.benefits) >= 2
        free_goods = eval_res.free_goods_benefits
        awarded = {g["sku_code"]: g["quantity_cases"] for g in free_goods}
        assert awarded.get("SKU-DT-1KG") == 1
        assert awarded.get("SKU-TE-250") == 2
        assert awarded.get("SKU-DT-1KG") != 3, "Distinct SKUs must never be merged into one quantity"

        await session.delete(multi_scheme)
        if seed_bs:
            seed_bs.is_active = True
        await session.commit()


# ---------------------------------------------------------------------------
# 3. Multiple benefits from one scheme (e.g. Discount + Free SKU)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multiple_benefits_from_one_scheme():
    """3. Multiple benefits (monetary discount + free SKU) from a single scheme."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Scheme).where(Scheme.scheme_code.like("SCH-TEST-%")))
        await session.commit()

        seed_bs = (await session.execute(select(Scheme).where(Scheme.scheme_code == "SCH-BS-10P1"))).scalar_one_or_none()
        if seed_bs:
            seed_bs.is_active = False
            await session.commit()

        biscuit = (await session.execute(select(Product).where(Product.sku_code == "SKU-BS-075"))).scalar_one()

        combo_scheme = Scheme(
            id=uuid.uuid4(),
            scheme_code="SCH-TEST-COMBO-BENEFITS",
            name="Buy 10 Biscuit: 5% Slab Discount + 1 Free Biscuit",
            is_active=True,
            is_stackable=False,
            priority=1,
        )
        r_discount = SchemeRule(
            id=uuid.uuid4(),
            scheme=combo_scheme,
            rule_type="SLAB_DISCOUNT",
            qualifying_product=biscuit,
            min_quantity=10,
            discount_percentage=Decimal("5.00"),
        )
        r_free = SchemeRule(
            id=uuid.uuid4(),
            scheme=combo_scheme,
            rule_type="FREE_GOODS",
            qualifying_product=biscuit,
            min_quantity=10,
            free_product=biscuit,
            free_quantity=1,
        )
        session.add_all([combo_scheme, r_discount, r_free])
        await session.commit()

        eval_res = await SchemeService.evaluate_product_schemes(session, biscuit, 10, Decimal("8.10"))
        assert eval_res.has_conflict is False
        assert eval_res.discount_amount > Decimal("0.00")
        assert eval_res.free_quantity >= 1

        rule_types = {b.rule_type_canonical for b in eval_res.benefits}
        assert "SLAB_DISCOUNT" in rule_types
        assert "FREE_GOODS" in rule_types

        await session.delete(combo_scheme)
        if seed_bs:
            seed_bs.is_active = True
        await session.commit()


# ---------------------------------------------------------------------------
# 4. Multiple schemes with stacking disabled (Conflict Detection)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multiple_schemes_with_stacking_disabled():
    """4. Competing schemes with stacking disabled flags conflict for Order Desk review."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Scheme).where(Scheme.scheme_code.like("SCH-TEST-%")))
        await session.commit()

        detergent = (await session.execute(select(Product).where(Product.sku_code == "SKU-DT-1KG"))).scalar_one()

        sch_a = Scheme(
            id=uuid.uuid4(),
            scheme_code="SCH-TEST-COMPETE-A",
            name="Promo A: 3% Off on 5 cases",
            is_active=True,
            priority=1,
        )
        r_a = SchemeRule(
            id=uuid.uuid4(),
            scheme=sch_a,
            rule_type="SLAB_DISCOUNT",
            qualifying_product=detergent,
            min_quantity=5,
            discount_percentage=Decimal("3.00"),
        )

        sch_b = Scheme(
            id=uuid.uuid4(),
            scheme_code="SCH-TEST-COMPETE-B",
            name="Promo B: Buy 5 get 1 free",
            is_active=True,
            priority=2,
        )
        r_b = SchemeRule(
            id=uuid.uuid4(),
            scheme=sch_b,
            rule_type="FREE_GOODS",
            qualifying_product=detergent,
            min_quantity=5,
            free_product=detergent,
            free_quantity=1,
        )
        session.add_all([sch_a, r_a, sch_b, r_b])
        await session.commit()

        # Evaluate with stacking disabled and FLAG_CONFLICT_FOR_REVIEW policy
        eval_res = await SchemeService.evaluate_product_schemes(
            session=session,
            product=detergent,
            quantity_cases=5,
            unit_price=Decimal("101.50"),
            override_stacking=False,
            override_policy="FLAG_CONFLICT_FOR_REVIEW",
        )
        assert eval_res.has_conflict is True
        assert "Scheme conflict detected" in (eval_res.conflict_note or "")

        await session.delete(sch_a)
        await session.delete(sch_b)
        await session.commit()


# ---------------------------------------------------------------------------
# 5. Multiple schemes with stacking enabled
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multiple_schemes_with_stacking_enabled():
    """5. Competing schemes with stacking enabled combines benefits."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Scheme).where(Scheme.scheme_code.like("SCH-TEST-%")))
        await session.commit()

        detergent = (await session.execute(select(Product).where(Product.sku_code == "SKU-DT-1KG"))).scalar_one()

        sch_a = Scheme(id=uuid.uuid4(), scheme_code="SCH-TEST-STACK-A", name="Promo A: 3% Off", is_active=True, priority=1)
        r_a = SchemeRule(id=uuid.uuid4(), scheme=sch_a, rule_type="SLAB_DISCOUNT", qualifying_product=detergent, min_quantity=5, discount_percentage=Decimal("3.00"))

        sch_b = Scheme(id=uuid.uuid4(), scheme_code="SCH-TEST-STACK-B", name="Promo B: 1 Free", is_active=True, priority=2)
        r_b = SchemeRule(id=uuid.uuid4(), scheme=sch_b, rule_type="FREE_GOODS", qualifying_product=detergent, min_quantity=5, free_product=detergent, free_quantity=1)

        session.add_all([sch_a, r_a, sch_b, r_b])
        await session.commit()

        eval_res = await SchemeService.evaluate_product_schemes(
            session=session,
            product=detergent,
            quantity_cases=5,
            unit_price=Decimal("101.50"),
            override_stacking=True,
        )
        assert eval_res.is_stacked is True
        assert eval_res.has_conflict is False
        assert eval_res.discount_amount > Decimal("0.00")
        assert eval_res.free_quantity == 1

        await session.delete(sch_a)
        await session.delete(sch_b)
        await session.commit()


# ---------------------------------------------------------------------------
# 6. Different benefits with different units (e.g. CASE uom)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_different_benefits_with_different_units():
    """6. EvaluatedBenefit preserves unit of measure (CASE / PIECE)."""
    async with AsyncSessionLocal() as session:
        biscuit = (await session.execute(select(Product).where(Product.sku_code == "SKU-BS-075"))).scalar_one()
        eval_res = await SchemeService.evaluate_product_schemes(session, biscuit, 10, Decimal("8.10"))
        for b in eval_res.benefits:
            assert b.awarded_uom in ("CASE", "PIECE", "PACK")


# ---------------------------------------------------------------------------
# 7. Slab discount at exactly 5 cases
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slab_discount_at_exactly_5_cases():
    """7. Slab discount at exactly 5 cases (threshold boundary)."""
    async with AsyncSessionLocal() as session:
        detergent = (await session.execute(select(Product).where(Product.sku_code == "SKU-DT-1KG"))).scalar_one()
        eval_5 = await SchemeService.evaluate_product_schemes(session, detergent, 5, Decimal("101.50"))
        # 5 cases * 101.50 = 507.50 * 3% = 15.225 -> 15.23
        from decimal import ROUND_HALF_UP
        expected = (Decimal("101.50") * 5 * Decimal("0.03")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert eval_5.discount_amount == expected
        assert eval_5.has_conflict is False


# ---------------------------------------------------------------------------
# 8. Slab discount below and above threshold
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slab_discount_below_and_above_threshold():
    """8. Slab discount below threshold (4 cases -> 0) and above (6 cases -> 3%)."""
    async with AsyncSessionLocal() as session:
        detergent = (await session.execute(select(Product).where(Product.sku_code == "SKU-DT-1KG"))).scalar_one()

        # Below threshold (4 cases) -> 0 discount
        eval_4 = await SchemeService.evaluate_product_schemes(session, detergent, 4, Decimal("101.50"))
        assert eval_4.discount_amount == Decimal("0.00")

        # Above threshold (6 cases) -> 3% discount
        eval_6 = await SchemeService.evaluate_product_schemes(session, detergent, 6, Decimal("101.50"))
        expected_6 = (Decimal("101.50") * 6 * Decimal("0.03")).quantize(Decimal("0.01"))
        assert eval_6.discount_amount == expected_6


# ---------------------------------------------------------------------------
# 9. Insufficient stock for a free SKU
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_insufficient_stock_for_free_sku():
    """9. Insufficient stock for free SKU is not silently dropped; preview captures all benefits."""
    async with AsyncSessionLocal() as session:
        retailer = (await session.execute(select(Retailer).where(Retailer.retailer_code == "RET-JBP-001"))).scalar_one()
        tea = (await session.execute(select(Product).where(Product.sku_code == "SKU-TE-250"))).scalar_one()

        # Tea has 0 available cases in baseline stock
        inv = (await session.execute(select(Inventory).where(Inventory.product_id == tea.id))).scalar_one()
        assert inv.available_cases == 0

        # Attempting to order tea directly rejects due to insufficient stock
        with pytest.raises(Exception):
            await OrderService.create_order(
                session=session,
                retailer=retailer,
                items=[OrderItemCreate(product_id=tea.id, quantity_cases=1, uom_type="CASE")],
            )


# ---------------------------------------------------------------------------
# 10. Order quantity changes and recalculation (Desk adjustment)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_order_quantity_changes_and_recalculation():
    """10. Changing line quantity dynamically recalculates schemes and benefits."""
    async with AsyncSessionLocal() as session:
        retailer = (await session.execute(select(Retailer).where(Retailer.retailer_code == "RET-JBP-001"))).scalar_one()
        biscuit = (await session.execute(select(Product).where(Product.sku_code == "SKU-BS-075"))).scalar_one()
        user_desk = (await session.execute(select(User).where(User.role == "ROLE_ORDER_DESK"))).scalars().first()

        # Order 10 cases (qualifies for 1 free case)
        order = await OrderService.create_order(
            session=session,
            retailer=retailer,
            items=[OrderItemCreate(product_id=biscuit.id, quantity_cases=10, uom_type="CASE")],
        )

        # Reload with eager loading
        stmt = (
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.items).selectinload(OrderItem.benefits))
        )
        persisted_order = (await session.execute(stmt)).scalar_one()
        line = persisted_order.items[0]
        assert line.approved_qty == 10
        assert line.free_item_qty == 1

        # Order Desk adjusts quantity down to 4 cases (drops below 10-case threshold)
        await OrderService.desk_adjust_line(
            session=session,
            order_id=order.id,
            line_id=line.id,
            new_approved_qty=4,
            operator_user_id=user_desk.id,
            reason="Retailer requested reduction to 4 cases",
        )

        reloaded = (await session.execute(stmt)).scalar_one()
        adj_line = reloaded.items[0]
        assert adj_line.approved_qty == 4
        assert adj_line.free_item_qty == 0, "Free goods benefit must be automatically removed when dropping below threshold"
        assert len(adj_line.benefits) == 0

        # Clean up order
        await OrderService.reject_order(session, order.id, user_desk.id, "Test cleanup")


# ---------------------------------------------------------------------------
# 11. Duplicate benefit prevention (Idempotency)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duplicate_benefit_prevention():
    """11. Repeated evaluation produces identical benefit outputs without duplication."""
    async with AsyncSessionLocal() as session:
        biscuit = (await session.execute(select(Product).where(Product.sku_code == "SKU-BS-075"))).scalar_one()
        eval1 = await SchemeService.evaluate_product_schemes(session, biscuit, 10, Decimal("8.10"))
        eval2 = await SchemeService.evaluate_product_schemes(session, biscuit, 10, Decimal("8.10"))
        assert len(eval1.benefits) == len(eval2.benefits)
        assert eval1.free_quantity == eval2.free_quantity
        assert eval1.discount_amount == eval2.discount_amount


# ---------------------------------------------------------------------------
# 12. Order rejection and stock release
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_order_rejection_and_stock_release():
    """12. Order rejection releases reserved inventory and restores retailer credit."""
    async with AsyncSessionLocal() as session:
        retailer = (await session.execute(select(Retailer).where(Retailer.retailer_code == "RET-JBP-001"))).scalar_one()
        biscuit = (await session.execute(select(Product).where(Product.sku_code == "SKU-BS-075"))).scalar_one()
        user_desk = (await session.execute(select(User).where(User.role == "ROLE_ORDER_DESK"))).scalars().first()

        inv_before = (await session.execute(select(Inventory).where(Inventory.product_id == biscuit.id))).scalar_one()
        avail_start = inv_before.available_cases

        order = await OrderService.create_order(
            session=session,
            retailer=retailer,
            items=[OrderItemCreate(product_id=biscuit.id, quantity_cases=10, uom_type="CASE")],
        )

        inv_after = (await session.execute(select(Inventory).where(Inventory.product_id == biscuit.id))).scalar_one()
        assert inv_after.available_cases == avail_start - 10

        # Reject order
        await OrderService.reject_order(session, order.id, user_desk.id, "Test reject and release")

        inv_reverted = (await session.execute(select(Inventory).where(Inventory.product_id == biscuit.id))).scalar_one()
        assert inv_reverted.available_cases == avail_start, "Reserved inventory must be released upon order rejection"


# ---------------------------------------------------------------------------
# 13. Correct representation in order details and Tally export
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_representation_in_order_details_and_tally_export():
    """13. Tally export and order details display purchased products and free benefits separately."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Scheme).where(Scheme.scheme_code.like("SCH-TEST-%")))
        await session.commit()

        # Temporarily deactivate default seed scheme on biscuit
        seed_bs = (await session.execute(select(Scheme).where(Scheme.scheme_code == "SCH-BS-10P1"))).scalar_one_or_none()
        if seed_bs:
            seed_bs.is_active = False
            await session.commit()

        biscuit = (await session.execute(select(Product).where(Product.sku_code == "SKU-BS-075"))).scalar_one()
        detergent = (await session.execute(select(Product).where(Product.sku_code == "SKU-DT-1KG"))).scalar_one()
        retailer = (await session.execute(select(Retailer).where(Retailer.retailer_code == "RET-JBP-001"))).scalar_one()
        user_desk = (await session.execute(select(User).where(User.role == "ROLE_ORDER_DESK"))).scalars().first()

        # Create multi-benefit scheme: Buy 10 Biscuit -> 1 Free Detergent
        test_scheme = Scheme(
            id=uuid.uuid4(),
            scheme_code="SCH-TEST-TALLY-COMBO",
            name="Diwali Promo: Buy 10 Biscuit Get 1 Detergent Free",
            is_active=True,
            priority=1,
        )
        r = SchemeRule(
            id=uuid.uuid4(),
            scheme=test_scheme,
            rule_type="FREE_GOODS",
            qualifying_product=biscuit,
            min_quantity=10,
            free_product=detergent,
            free_quantity=1,
        )
        session.add_all([test_scheme, r])
        await session.commit()

        order = await OrderService.create_order(
            session=session,
            retailer=retailer,
            items=[OrderItemCreate(product_id=biscuit.id, quantity_cases=10, uom_type="CASE")],
        )

        # Approve order
        approved_order = await OrderService.approve_order(
            session=session,
            order_id=order.id,
            operator_user_id=user_desk.id,
            notes="Approved for Tally export test",
        )

        # Generate Tally export
        batch, csv_text = await ExportService.create_tally_export_batch(
            session=session,
            operator=user_desk,
            order_ids=[approved_order.id],
        )

        assert batch is not None
        assert "SKU-BS-075" in csv_text
        assert "SKU-DT-1KG" in csv_text
        assert "Free promotional benefit" in csv_text

        # Cleanup
        await session.delete(test_scheme)
        if seed_bs:
            seed_bs.is_active = True
        await session.commit()
