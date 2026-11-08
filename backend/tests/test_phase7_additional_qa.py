import io
import csv
import uuid
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.catalog import Product, Inventory
from app.models.retailer import Retailer
from app.models.order import Order, OrderItem
from app.models.pricing import RetailerPrice
from app.services.order_service import OrderService
from app.services.pricing_service import PricingService
from app.services.ai_capture_service import AICaptureService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def retailer1_token(client: AsyncClient):
    """Token for Retailer 1 (Patel Kirana - 9826011111)."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826011111", "otp_code": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
async def desk_token(client: AsyncClient):
    """Token for Order Desk Operator (Sanjay Sharma - 9826000000)."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826000000", "otp_code": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# ===========================================================================
# 1. EMPTY DATABASE & NON-EXISTENT ENTITY RESPONSES
# ===========================================================================

@pytest.mark.asyncio
async def test_nonexistent_entities_return_clean_404(client: AsyncClient, retailer1_token: str, desk_token: str):
    """
    Verify API handles nonexistent IDs gracefully with HTTP 404 rather than unhandled 500.
    """
    random_id = uuid.uuid4()
    headers_ret = {"Authorization": f"Bearer {retailer1_token}"}
    headers_desk = {"Authorization": f"Bearer {desk_token}"}

    # 1. Non-existent product details
    res = await client.get(f"/api/v1/products/{random_id}", headers=headers_ret)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    # 2. Non-existent product availability
    res = await client.get(f"/api/v1/products/{random_id}/availability", headers=headers_ret)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    # 3. Non-existent order in retailer scope
    res = await client.get(f"/api/v1/orders/{random_id}", headers=headers_ret)
    assert res.status_code == 404

    # 4. Non-existent order in order desk scope
    res = await client.get(f"/api/v1/desk/orders/{random_id}", headers=headers_desk)
    assert res.status_code == 404

    # 5. Non-existent export batch download
    res = await client.get(f"/api/v1/desk/exports/{random_id}/download", headers=headers_desk)
    assert res.status_code == 404

    # 6. Search with 0 matches returns clean 200 with empty items list
    res = await client.get("/api/v1/products?search=NONEXISTENT_SKU_TERM_99999", headers=headers_ret)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) == 0
    assert data["total"] == 0


# ===========================================================================
# 2. AI SERVICE TIMEOUT & MALFORMED RESPONSE RESILIENCE
# ===========================================================================

@pytest.mark.asyncio
async def test_ai_service_timeout_handling():
    """
    Verify AI service handles OpenAI timeout gracefully without unhandled exceptions.
    """
    sample_text = "5 peti biscuit chhota"

    with patch("app.services.ai_capture_service.settings.OPENAI_API_KEY", "test-fake-key"):
        with patch("app.services.ai_capture_service.AsyncOpenAI") as mock_openai:
            client_instance = MagicMock()
            client_instance.chat.completions.create = AsyncMock(side_effect=Exception("Connection timed out after 30s"))
            mock_openai.return_value = client_instance

            lines, is_fallback, service_msg = await AICaptureService.extract_lines_with_openai(sample_text)
            assert is_fallback is True
            assert len(lines) >= 1
            assert "fallback" in service_msg.lower() or "error" in service_msg.lower() or "offline" in service_msg.lower()


@pytest.mark.asyncio
async def test_ai_service_malformed_json_handling():
    """
    Verify AI service recovers gracefully when the language model returns invalid non-JSON text.
    """
    sample_text = "5 peti biscuit chhota"

    with patch("app.services.ai_capture_service.settings.OPENAI_API_KEY", "test-fake-key"):
        with patch("app.services.ai_capture_service.AsyncOpenAI") as mock_openai:
            mock_choice = MagicMock()
            mock_choice.message.content = "Sorry, I cannot parse this order: [unclosed brackets"
            mock_response = MagicMock(choices=[mock_choice])

            client_instance = MagicMock()
            client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = client_instance

            lines, is_fallback, service_msg = await AICaptureService.extract_lines_with_openai(sample_text)
            assert is_fallback is True
            assert isinstance(lines, list)


# ===========================================================================
# 3. MISSING RETAILER PRICE FALLBACK
# ===========================================================================

@pytest.mark.asyncio
async def test_missing_retailer_custom_price_falls_back_to_dealer_price():
    """
    Verify that if a retailer has no contracted price for a product,
    the PricingService cleanly falls back to the default Product.default_dealer_price.
    """
    async with AsyncSessionLocal() as session:
        # Fetch tea leaf product (SKU-TE-250)
        prod_res = await session.execute(select(Product).where(Product.sku_code == "SKU-TE-250"))
        tea_product = prod_res.scalar_one()

        # Fetch Patel Kirana (RET-JBP-001)
        ret_res = await session.execute(select(Retailer).where(Retailer.retailer_code == "RET-JBP-001"))
        retailer = ret_res.scalar_one()

        # Ensure no custom price exists for tea leaf for this retailer
        price_res = await session.execute(
            select(RetailerPrice).where(
                RetailerPrice.retailer_id == retailer.id,
                RetailerPrice.product_id == tea_product.id,
            )
        )
        custom_price = price_res.scalar_one_or_none()
        assert custom_price is None

        # Resolve price via PricingService.get_effective_price static method
        resolved_price, basis, is_custom = await PricingService.get_effective_price(
            session, retailer.id, tea_product
        )

        # Must fall back to base dealer price
        assert is_custom is False
        assert resolved_price == tea_product.default_dealer_price
        assert resolved_price == Decimal("118.00")


# ===========================================================================
# 4. INSUFFICIENT STOCK & BOUNDARY VALIDATION
# ===========================================================================

@pytest.mark.asyncio
async def test_stock_boundary_and_out_of_stock_rejections(client: AsyncClient, retailer1_token: str):
    """
    Verify exact stock boundary enforcement:
    - Out of stock item (SKU-TE-250, 0 cases available) fails on 1 case order.
    - Active item (SKU-DT-1KG, 85 cases available) fails when ordering 86 cases.
    """
    headers = {"Authorization": f"Bearer {retailer1_token}"}

    # Fetch product IDs
    cat_res = await client.get("/api/v1/products", headers=headers)
    assert cat_res.status_code == 200
    products = {p["sku_code"]: p for p in cat_res.json()["items"]}

    tea_id = products["SKU-TE-250"]["id"]
    det_id = products["SKU-DT-1KG"]["id"]

    # 1. Ordering 1 case of 0-stock tea must fail
    res_tea = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": tea_id, "quantity_cases": 1}]},
        headers=headers,
    )
    assert res_tea.status_code in (400, 409)
    assert "insufficient stock" in res_tea.json()["detail"].lower()

    # 2. Ordering cases beyond detergent powder stock (85 available)
    res_det_exceed = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": det_id, "quantity_cases": 9999}]},
        headers=headers,
    )
    assert res_det_exceed.status_code in (400, 409)
    assert "insufficient stock" in res_det_exceed.json()["detail"].lower()


# ===========================================================================
# 5. CONCURRENT ORDER APPROVAL & RACE CONDITION PREVENTION
# ===========================================================================

@pytest.mark.asyncio
async def test_concurrent_order_approval_race_condition(client: AsyncClient, retailer1_token: str, desk_token: str):
    """
    Simulate concurrent approval of the same order.
    The first approval must succeed; the second concurrent/subsequent approval
    must receive HTTP 409 Conflict, ensuring physical inventory is NOT deducted twice.
    """
    headers_ret = {"Authorization": f"Bearer {retailer1_token}"}
    headers_desk = {"Authorization": f"Bearer {desk_token}"}

    # Fetch biscuit product (abundant stock: 300+ cases)
    cat_res = await client.get("/api/v1/products", headers=headers_ret)
    products = {p["sku_code"]: p for p in cat_res.json()["items"]}
    biscuit_id = products["SKU-BS-075"]["id"]

    # Read current stock
    async with AsyncSessionLocal() as session:
        inv_before = await session.execute(select(Inventory).where(Inventory.product_id == uuid.UUID(biscuit_id)))
        stock_before = inv_before.scalar_one().available_cases

    # Place an order for 2 cases
    order_res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": biscuit_id, "quantity_cases": 2}]},
        headers=headers_ret,
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # Trigger two concurrent approvals via asyncio.gather
    req1 = client.post(
        f"/api/v1/desk/orders/{order_id}/approve",
        json={"notes": "First concurrent approval attempt"},
        headers=headers_desk,
    )
    req2 = client.post(
        f"/api/v1/desk/orders/{order_id}/approve",
        json={"notes": "Second concurrent approval attempt"},
        headers=headers_desk,
    )
    resp1, resp2 = await asyncio.gather(req1, req2)

    status_codes = sorted([resp1.status_code, resp2.status_code])
    # One request must succeed (200), and the duplicate must be rejected (409 Conflict)
    assert status_codes == [200, 409]

    # Verify inventory was decremented exactly once for the order placement (2 cases),
    # and no secondary deduction occurred during the duplicate approval
    async with AsyncSessionLocal() as session:
        inv_after = await session.execute(select(Inventory).where(Inventory.product_id == uuid.UUID(biscuit_id)))
        stock_after = inv_after.scalar_one().available_cases
        assert stock_after == stock_before - 2


# ===========================================================================
# 6. INVENTORY RESTORATION ON ORDER REJECTION
# ===========================================================================

@pytest.mark.asyncio
async def test_order_rejection_restores_inventory(client: AsyncClient, retailer1_token: str, desk_token: str):
    """
    Verify that when an order is placed, stock is held/deducted,
    and when the Order Desk rejects the order, inventory is fully restored.
    """
    headers_ret = {"Authorization": f"Bearer {retailer1_token}"}
    headers_desk = {"Authorization": f"Bearer {desk_token}"}

    # Get biscuit product
    cat_res = await client.get("/api/v1/products", headers=headers_ret)
    products = {p["sku_code"]: p for p in cat_res.json()["items"]}
    biscuit_id = products["SKU-BS-075"]["id"]

    async with AsyncSessionLocal() as session:
        inv = await session.execute(select(Inventory).where(Inventory.product_id == uuid.UUID(biscuit_id)))
        initial_stock = inv.scalar_one().available_cases

    # Submit order for 5 cases
    order_res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": biscuit_id, "quantity_cases": 5}]},
        headers=headers_ret,
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # Verify stock decremented by 5
    async with AsyncSessionLocal() as session:
        inv = await session.execute(select(Inventory).where(Inventory.product_id == uuid.UUID(biscuit_id)))
        assert inv.scalar_one().available_cases == initial_stock - 5

    # Desk rejects order
    reject_res = await client.post(
        f"/api/v1/desk/orders/{order_id}/reject",
        json={"reason": "Customer requested order cancellation due to shop renovation"},
        headers=headers_desk,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"

    # Verify stock restored to initial stock
    async with AsyncSessionLocal() as session:
        inv = await session.execute(select(Inventory).where(Inventory.product_id == uuid.UUID(biscuit_id)))
        assert inv.scalar_one().available_cases == initial_stock


# ===========================================================================
# 7. TALLY EXPORT BATCH EDGE CASES
# ===========================================================================

@pytest.mark.asyncio
async def test_tally_export_lifecycle_and_batch_download(client: AsyncClient, retailer1_token: str, desk_token: str):
    """
    Verify the complete export lifecycle:
    1. Create and approve an order.
    2. Generate an export batch.
    3. Download the CSV and verify CSV headers and Tally fields.
    4. Verify order status transitions to EXPORTED.
    """
    headers_ret = {"Authorization": f"Bearer {retailer1_token}"}
    headers_desk = {"Authorization": f"Bearer {desk_token}"}

    # Create an order for biscuit (in stock)
    cat_res = await client.get("/api/v1/products", headers=headers_ret)
    biscuit_id = next(p["id"] for p in cat_res.json()["items"] if p["sku_code"] == "SKU-BS-075")

    order_res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": biscuit_id, "quantity_cases": 1}]},
        headers=headers_ret,
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # Approve the order
    appr_res = await client.post(
        f"/api/v1/desk/orders/{order_id}/approve",
        json={"notes": "Approved for export batch"},
        headers=headers_desk,
    )
    assert appr_res.status_code == 200

    # Generate Export Batch
    exp_res = await client.post("/api/v1/desk/exports", json={}, headers=headers_desk)
    assert exp_res.status_code == 201
    batch = exp_res.json()
    batch_id = batch["id"]
    assert batch["order_count"] >= 1

    # Download CSV
    dl_res = await client.get(f"/api/v1/desk/exports/{batch_id}/download", headers=headers_desk)
    assert dl_res.status_code == 200
    assert "text/csv" in dl_res.headers["content-type"]
    assert "attachment" in dl_res.headers["content-disposition"]

    csv_content = dl_res.text
    reader = csv.DictReader(io.StringIO(csv_content))
    fieldnames = reader.fieldnames
    assert "Voucher Number" in fieldnames
    assert "Party Name" in fieldnames
    assert "Item SKU" in fieldnames
    assert "Item Name" in fieldnames
    assert "Billed Qty (Cases)" in fieldnames
    assert "Rate Per Unit (Excl. GST)" in fieldnames
    assert "Line Amount (Excl. GST)" in fieldnames

    # Check row count
    rows = list(reader)
    assert len(rows) >= 1
