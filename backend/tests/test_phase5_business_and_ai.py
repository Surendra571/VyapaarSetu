import uuid
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from openai import APIConnectionError

from app.main import app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.catalog import Product, SKUAlias, Inventory
from app.models.pricing import Scheme, SchemeRule
from app.models.retailer import Retailer
from app.schemas.ai_capture import OpenAIExtractionPayload, OpenAILineExtraction
from app.services.scheme_service import SchemeService, SchemeEvaluationResult
from app.services.ai_capture_service import AICaptureService
from app.services.credit_service import CreditService
from app.services.order_service import OrderService
from app.schemas.order import OrderItemCreate


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def retailer_token(client: AsyncClient):
    """Obtain JWT token for Retailer 1 (Patel Kirana - 9826011111)."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826011111", "otp_code": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# ===========================================================================
# 1. SCHEME ENGINE TESTS (Part A)
# ===========================================================================

@pytest.mark.asyncio
async def test_scheme_threshold_eligibility():
    """Verify that orders below minimum threshold do not qualify for promotions."""
    async with AsyncSessionLocal() as session:
        prod_stmt = select(Product).where(Product.sku_code == "SKU-BS-075")
        res = await session.execute(prod_stmt)
        biscuit = res.scalar_one()

        # Buy 10 get 1 free: 9 cases ordered -> Below threshold (0 free goods)
        result = await SchemeService.evaluate_product_schemes(
            session=session,
            product=biscuit,
            quantity_cases=9,
            unit_price=Decimal("8.10"),
        )
        assert result.free_quantity == 0
        assert result.discount_amount == Decimal("0.00")
        assert result.scheme_name is None


@pytest.mark.asyncio
async def test_scheme_multiple_qualifying_free_goods():
    """Verify that multiple qualification tiers compute free goods proportionally."""
    async with AsyncSessionLocal() as session:
        prod_stmt = select(Product).where(Product.sku_code == "SKU-BS-075")
        res = await session.execute(prod_stmt)
        biscuit = res.scalar_one()

        # Tier 1: 10 cases -> 1 free case
        r10 = await SchemeService.evaluate_product_schemes(
            session=session,
            product=biscuit,
            quantity_cases=10,
            unit_price=Decimal("8.10"),
        )
        assert r10.free_quantity == 1
        assert "Glucose Biscuit 75g" in (r10.free_product_name or "")
        assert "1 free case(s)" in (r10.explanation or "")

        # Tier 2: 25 cases -> 2 free cases (25 // 10 = 2)
        r25 = await SchemeService.evaluate_product_schemes(
            session=session,
            product=biscuit,
            quantity_cases=25,
            unit_price=Decimal("8.10"),
        )
        assert r25.free_quantity == 2
        assert "2 free case(s)" in (r25.explanation or "")


@pytest.mark.asyncio
async def test_scheme_slab_discount_calculation():
    """Verify percentage slab discount calculation on qualified quantities."""
    async with AsyncSessionLocal() as session:
        prod_stmt = select(Product).where(Product.sku_code == "SKU-DT-1KG")
        res = await session.execute(prod_stmt)
        detergent = res.scalar_one()

        # 3% discount on 5+ cases: 4 cases -> 0 discount
        r4 = await SchemeService.evaluate_product_schemes(
            session=session,
            product=detergent,
            quantity_cases=4,
            unit_price=Decimal("101.50"),
        )
        assert r4.discount_amount == Decimal("0.00")

        # 5 cases @ 101.50 = 507.50 => 3% discount = 15.225 -> round(15.23, 2)
        r5 = await SchemeService.evaluate_product_schemes(
            session=session,
            product=detergent,
            quantity_cases=5,
            unit_price=Decimal("101.50"),
        )
        assert r5.discount_amount == Decimal("15.23")
        assert "slab discount" in (r5.explanation or "")
        assert "15.23" in (r5.explanation or "")


@pytest.mark.asyncio
async def test_scheme_conflicts_and_unresolved_stacking_policy():
    """
    Business Constraint 3: Scheme stacking must not be assumed.
    If multiple schemes conflict and stacking policy is unresolved,
    flag the result for review instead of silently stacking or choosing.
    """
    async with AsyncSessionLocal() as session:
        prod_stmt = select(Product).where(Product.sku_code == "SKU-BS-075")
        res = await session.execute(prod_stmt)
        biscuit = res.scalar_one()

        # Create a second competing scheme for the same product
        competing_scheme = Scheme(
            id=uuid.uuid4(),
            scheme_code="TEST-SCH-COMPETE",
            name="Festive 5% Biscuit Discount",
            description="Competing festive slab discount",
            is_active=True,
            is_stackable=False,
            priority=2,
        )
        competing_rule = SchemeRule(
            id=uuid.uuid4(),
            scheme=competing_scheme,
            rule_type="SLAB_DISCOUNT",
            qualifying_product_id=biscuit.id,
            min_quantity=5,
            discount_percentage=Decimal("5.00"),
        )
        session.add(competing_scheme)
        session.add(competing_rule)
        await session.flush()

        try:
            # Evaluate with 15 cases -> qualifies for BOTH:
            # 1) Buy 10 get 1 free
            # 2) Festive 5% discount (min 5)
            # Stacking is disabled, policy is FLAG_CONFLICT_FOR_REVIEW
            res_eval = await SchemeService.evaluate_product_schemes(
                session=session,
                product=biscuit,
                quantity_cases=15,
                unit_price=Decimal("8.10"),
                override_stacking=False,
                override_policy="FLAG_CONFLICT_FOR_REVIEW",
            )

            assert res_eval.has_conflict is True
            assert "Scheme conflict detected" in (res_eval.conflict_note or "")
            assert "Flagged for Order Desk manual review" in (res_eval.conflict_note or "")
            assert res_eval.is_stacked is False

        finally:
            await session.rollback()


# ===========================================================================
# 2. AI CAPTURE & SKU MATCHING TESTS (Part B, C, D)
# ===========================================================================

@pytest.mark.asyncio
async def test_ai_capture_sample_message_extraction():
    """
    Test extraction of the approved FMCG test sample:
    'bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti'
    """
    sample_text = "bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti"
    lines = AICaptureService._extract_lines_local(sample_text)

    assert len(lines) == 3

    # Line 1: biscuit chhota
    assert lines[0].quantity == 5
    assert lines[0].unit == "CASE"
    assert "biscuit chhota" in lines[0].product_description.lower()
    assert lines[0].language == "Hinglish"

    # Line 2: washing powder 1 kilo
    assert lines[1].quantity == 2
    assert lines[1].unit == "CASE"
    assert "washing powder 1 kilo" in lines[1].product_description.lower()

    # Line 3: chai patti 250 wala
    assert lines[2].quantity == 1
    assert lines[2].unit == "CASE"
    assert "chai patti 250" in lines[2].product_description.lower()


@pytest.mark.asyncio
async def test_sku_matching_high_confidence():
    """Verify that specific product descriptions match exact catalog SKUs with high confidence."""
    async with AsyncSessionLocal() as session:
        ret_stmt = select(Retailer).limit(1)
        res = await session.execute(ret_stmt)
        retailer = res.scalar_one()

        # 1. Glucose biscuit 75g
        p1, score1, alts1, clar1 = await AICaptureService.match_item_to_catalog(
            session=session,
            item_query="biscuit chhota",
            retailer_id=retailer.id,
        )
        assert p1 is not None
        assert p1.sku_code == "SKU-BS-075"
        assert score1 >= Decimal("0.85")
        assert clar1 is None

        # 2. Detergent powder 1 kg
        p2, score2, alts2, clar2 = await AICaptureService.match_item_to_catalog(
            session=session,
            item_query="washing powder 1 kilo",
            retailer_id=retailer.id,
        )
        assert p2 is not None
        assert p2.sku_code == "SKU-DT-1KG"
        assert score2 >= Decimal("0.85")

        # 3. Tea leaf 250 g
        p3, score3, alts3, clar3 = await AICaptureService.match_item_to_catalog(
            session=session,
            item_query="chai patti 250 wala",
            retailer_id=retailer.id,
        )
        assert p3 is not None
        assert p3.sku_code == "SKU-TE-250"
        assert score3 >= Decimal("0.85")


@pytest.mark.asyncio
async def test_ambiguous_product_matching():
    """
    Part D: If product is ambiguous (e.g. generic 'biscuit' without variant),
    show alternatives and require explicit human selection.
    """
    async with AsyncSessionLocal() as session:
        ret_stmt = select(Retailer).limit(1)
        res = await session.execute(ret_stmt)
        retailer = res.scalar_one()

        prod, score, alts, clar = await AICaptureService.match_item_to_catalog(
            session=session,
            item_query="biscuit",  # Generic query
            retailer_id=retailer.id,
        )
        assert score < Decimal("0.85")
        assert clar is not None


@pytest.mark.asyncio
async def test_unknown_product_matching():
    """
    Part C & D: Unknown product not in catalogue must NEVER invent a product ID or SKU.
    Must return confidence 0.00, matched_product None, and clear clarification prompt.
    """
    async with AsyncSessionLocal() as session:
        ret_stmt = select(Retailer).limit(1)
        res = await session.execute(ret_stmt)
        retailer = res.scalar_one()

        prod, score, alts, clar = await AICaptureService.match_item_to_catalog(
            session=session,
            item_query="iPhone 15 pro max smartphone",
            retailer_id=retailer.id,
        )
        assert prod is None
        assert score == Decimal("0.00")
        assert "could not be identified" in (clar or "")


@pytest.mark.asyncio
async def test_unclear_unit_handling():
    """
    Part D: If unit is unclear (e.g., '5 biscuit' without peti or packet):
    Do not guess. Ask whether the quantity means case or piece.
    """
    raw = "5 biscuit"
    lines = AICaptureService._extract_lines_local(raw)
    assert len(lines) == 1
    assert lines[0].unit_clarification_needed is True
    assert lines[0].unit == "unclear"

    async with AsyncSessionLocal() as session:
        ret_stmt = select(Retailer).limit(1)
        res = await session.execute(ret_stmt)
        retailer = res.scalar_one()

        prod, score, alts, clar = await AICaptureService.match_item_to_catalog(
            session=session,
            item_query=lines[0].product_description,
            retailer_id=retailer.id,
            unit_clarification_needed=True,
        )
        assert score < Decimal("0.85")
        assert "whole cases (peti) or individual" in (clar or "")


# ===========================================================================
# 3. AI SERVICE RESILIENCE & FAILURE TESTS (Part D)
# ===========================================================================

@pytest.mark.asyncio
async def test_ai_service_api_connection_failure():
    """
    Part D: If the AI service fails or encounters network error:
    Preserve original message, fall back to local parser, and provide retry/manual entry.
    """
    sample_text = "5 peti biscuit chhota"

    with patch("app.services.ai_capture_service.settings.OPENAI_API_KEY", "test-fake-key"):
        with patch("app.services.ai_capture_service.AsyncOpenAI") as mock_openai:
            # Simulate APIConnectionError
            client_instance = MagicMock()
            client_instance.chat.completions.create = AsyncMock(
                side_effect=APIConnectionError(request=MagicMock())
            )
            mock_openai.return_value = client_instance

            lines, is_fallback, service_msg = await AICaptureService.extract_lines_with_openai(sample_text)

            assert is_fallback is True
            assert "fallback parser" in (service_msg or "").lower()
            assert len(lines) == 1
            assert lines[0].quantity == 5


@pytest.mark.asyncio
async def test_ai_invalid_json_response_handling():
    """
    Part D: Validate AI output using Pydantic before using it.
    If LLM returns invalid JSON or schema violation, gracefully fallback.
    """
    sample_text = "5 peti biscuit chhota"

    with patch("app.services.ai_capture_service.settings.OPENAI_API_KEY", "test-fake-key"):
        with patch("app.services.ai_capture_service.AsyncOpenAI") as mock_openai:
            # Mock invalid response content
            mock_choice = MagicMock()
            mock_choice.message.content = "INVALID_NON_JSON_CONTENT"
            mock_response = MagicMock(choices=[mock_choice])

            client_instance = MagicMock()
            client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = client_instance

            lines, is_fallback, service_msg = await AICaptureService.extract_lines_with_openai(sample_text)

            assert is_fallback is True
            assert len(lines) == 1


# ===========================================================================
# 4. HUMAN CONFIRMATION & ALIAS PERSISTENCE (Part E & F)
# ===========================================================================

@pytest.mark.asyncio
async def test_human_confirmation_workflow(client: AsyncClient, retailer_token: str):
    """
    Part E: The workflow must be:
    Text input -> AI extraction -> SKU matching -> Confidence evaluation
    -> Human correction -> Human confirmation -> Order preview.
    AI must NEVER directly submit an order.
    """
    headers = {"Authorization": f"Bearer {retailer_token}"}

    # 1. Text input with an ambiguous item
    capture_res = await client.post(
        "/api/v1/ai-capture/text",
        json={"raw_text": "5 biscuit, 2 peti washing powder 1 kilo"},
        headers=headers,
    )
    assert capture_res.status_code == 201
    cap_data = capture_res.json()
    session_id = cap_data["id"]

    # There should be unconfirmed lines because '5 biscuit' has unclear unit
    assert cap_data["has_unconfirmed_lines"] is True
    line_unclear = next(l for l in cap_data["lines"] if "biscuit" in l["parsed_item_name"].lower())
    assert line_unclear["is_confirmed"] is False

    # 2. Attempting to confirm session prematurely must be REJECTED (HTTP 400)
    premature_res = await client.post(
        f"/api/v1/ai-capture/{session_id}/confirm",
        headers=headers,
    )
    assert premature_res.status_code == 400
    assert "require human review" in premature_res.json()["detail"].lower()

    # 3. Human reviewer resolves the unclear line and chooses to save as store alias
    patch_res = await client.patch(
        f"/api/v1/ai-capture/{session_id}/lines/{line_unclear['id']}",
        json={
            "resolved_product_id": line_unclear["matched_product_id"],
            "resolved_quantity": 5,
            "is_confirmed": True,
            "save_as_retailer_alias": True,
            "alias_phrase": "chhota biscuit",
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_confirmed"] is True
    assert patch_res.json()["saved_as_alias"] is True

    # 4. Confirm any remaining lines if needed
    session_get = await client.get(f"/api/v1/ai-capture/{session_id}", headers=headers)
    for l in session_get.json()["lines"]:
        if not l["is_confirmed"]:
            await client.patch(
                f"/api/v1/ai-capture/{session_id}/lines/{l['id']}",
                json={"is_confirmed": True},
                headers=headers,
            )

    # 5. Now session confirmation succeeds and generates order preview
    confirm_res = await client.post(
        f"/api/v1/ai-capture/{session_id}/confirm",
        headers=headers,
    )
    assert confirm_res.status_code == 200
    preview_data = confirm_res.json()
    assert preview_data["session_id"] == session_id
    assert preview_data["order_preview"]["total_cases"] >= 5


@pytest.mark.asyncio
async def test_retailer_alias_persistence_and_matching(client: AsyncClient, retailer_token: str):
    """
    Part F: When an authorized reviewer saves a corrected phrase as a retailer-specific alias,
    subsequent AI queries match that product with high confidence (0.98).
    """
    headers = {"Authorization": f"Bearer {retailer_token}"}

    # Fetch a product to alias
    async with AsyncSessionLocal() as session:
        tea_stmt = select(Product).where(Product.sku_code == "SKU-TE-250")
        res = await session.execute(tea_stmt)
        tea = res.scalar_one()

    # Create retailer alias 'jabalpur kadak chai'
    alias_res = await client.post(
        "/api/v1/ai-capture/aliases",
        json={
            "product_id": str(tea.id),
            "alias_text": "jabalpur kadak chai",
            "notes": "Custom dialect alias for Jabalpur store",
        },
        headers=headers,
    )
    assert alias_res.status_code == 201

    # Now parse a text using that alias
    cap_res = await client.post(
        "/api/v1/ai-capture/text",
        json={"raw_text": "3 peti jabalpur kadak chai"},
        headers=headers,
    )
    assert cap_res.status_code == 201
    cap_data = cap_res.json()
    assert len(cap_data["lines"]) == 1
    matched_line = cap_data["lines"][0]
    assert matched_line["matched_sku_code"] == "SKU-TE-250"
    assert Decimal(str(matched_line["confidence_score"])) >= Decimal("0.95")


# ===========================================================================
# 5. CREDIT HOLDS & INSUFFICIENT STOCK (Part G)
# ===========================================================================

@pytest.mark.asyncio
async def test_credit_hold_standing_and_separate_fields():
    """
    Part G: Separate fields for credit limit, outstanding amount, available credit.
    If proposed order amount breaches available credit, order enters CREDIT_HOLD.
    """
    retailer = Retailer(
        id=uuid.uuid4(),
        retailer_code="RET-TEST-001",
        store_name="Test Kirana Store",
        credit_limit=Decimal("10000.00"),
        outstanding_amount=Decimal("8000.00"),
        available_credit=Decimal("2000.00"),
        is_credit_locked=False,
    )

    # Order 1: Within limit (₹1,500 <= ₹2,000 available)
    eval_ok = CreditService.evaluate_credit_standing(retailer, Decimal("1500.00"))
    assert eval_ok.is_credit_breached is False
    assert eval_ok.will_trigger_credit_hold is False
    assert eval_ok.available_credit == Decimal("2000.00")

    # Order 2: Exceeds limit (₹2,500 > ₹2,000 available)
    eval_breach = CreditService.evaluate_credit_standing(retailer, Decimal("2500.00"))
    assert eval_breach.is_credit_breached is True
    assert eval_breach.will_trigger_credit_hold is True
    assert "exceeds available credit limit by ₹500.00" in eval_breach.notice


@pytest.mark.asyncio
async def test_insufficient_stock_prevents_silent_partial_orders(client: AsyncClient, retailer_token: str):
    """
    Part G & Business Constraint 4: Insufficient stock handling must be explicit.
    Never silently reduce quantities or create partial orders.
    """
    headers = {"Authorization": f"Bearer {retailer_token}"}

    # SKU-TE-250 has 0 cases in stock in seed data
    async with AsyncSessionLocal() as session:
        tea_stmt = select(Product).where(Product.sku_code == "SKU-TE-250")
        res = await session.execute(tea_stmt)
        tea = res.scalar_one()

    # Attempt to place order with 5 cases of Tea (stock is 0)
    order_res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(tea.id), "quantity_cases": 5, "uom_type": "CASE"}]},
        headers=headers,
    )

    assert order_res.status_code == 409
    detail = order_res.json()["detail"]
    assert "insufficient stock" in detail.lower()
    assert "SKU-TE-250" in detail
    assert "short by 5" in detail.lower()
    assert "strictly prevents silent partial orders" in detail
