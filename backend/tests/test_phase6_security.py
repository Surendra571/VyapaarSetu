import io
import csv
import uuid
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
import jwt
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.core.database import AsyncSessionLocal
from app.core.rate_limiter import ai_rate_limiter
from app.models.catalog import Product, Inventory
from app.models.retailer import Retailer
from app.models.order import Order
from app.models.pricing import RetailerPrice
from app.services.order_service import OrderService
from app.services.export_service import ExportService, sanitize_csv_cell
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
async def retailer2_token(client: AsyncClient):
    """Token for Retailer 2 (Agrawal Provision - 9826022222)."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826022222", "otp_code": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
async def desk_token(client: AsyncClient):
    """Token for Order Desk Officer (Sanjay Sharma - 9826000000)."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826000000", "otp_code": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# ===========================================================================
# 1. RETAILER ACCESSING ORDER DESK (Scenario 1 & 6)
# ===========================================================================

@pytest.mark.asyncio
async def test_retailer_cannot_access_order_desk_endpoints(client: AsyncClient, retailer1_token: str):
    """
    Negative Test 1: Retailer role attempting to access restricted Order Desk endpoints.
    Must be blocked with HTTP 403 Forbidden.
    """
    headers = {"Authorization": f"Bearer {retailer1_token}"}

    # 1. Listing all orders across retailers
    res_orders = await client.get("/api/v1/desk/orders", headers=headers)
    assert res_orders.status_code == 403
    assert "restricted to order desk operators" in res_orders.json()["detail"].lower()

    # 2. Generating Tally ERP export batches
    res_export = await client.post("/api/v1/desk/exports", json={}, headers=headers)
    assert res_export.status_code == 403

    # 3. Listing export batches
    res_batches = await client.get("/api/v1/desk/exports", headers=headers)
    assert res_batches.status_code == 403


@pytest.mark.asyncio
async def test_unauthorized_order_approval(client: AsyncClient, retailer1_token: str):
    """
    Negative Test 6: A retailer attempting to approve an order must receive HTTP 403 Forbidden.
    """
    fake_order_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {retailer1_token}"}
    res = await client.post(
        f"/api/v1/desk/orders/{fake_order_id}/approve",
        json={"notes": "Retailer self-approval attempt"},
        headers=headers,
    )
    assert res.status_code == 403
    assert "restricted to order desk" in res.json()["detail"].lower()


# ===========================================================================
# 2. MULTI-TENANT ISOLATION: ORDERS & PRICES (Scenario 2, 3, 4)
# ===========================================================================

@pytest.mark.asyncio
async def test_retailer_cannot_view_another_retailers_order(
    client: AsyncClient,
    retailer1_token: str,
    retailer2_token: str,
):
    """
    Negative Test 2: Retailer 1 creates an order; Retailer 2 attempts to query it by ID.
    Must be blocked with HTTP 403 Forbidden.
    """
    # 1. Retailer 1 creates an order
    h1 = {"Authorization": f"Bearer {retailer1_token}"}
    prod_res = await client.get("/api/v1/products", headers=h1)
    biscuit_id = next(p["id"] for p in prod_res.json()["items"] if p["sku_code"] == "SKU-BS-075")

    order_res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": biscuit_id, "quantity_cases": 2, "uom_type": "CASE"}]},
        headers=h1,
    )
    assert order_res.status_code == 201
    r1_order_id = order_res.json()["id"]

    # 2. Retailer 2 attempts to view Retailer 1's order
    h2 = {"Authorization": f"Bearer {retailer2_token}"}
    tamper_res = await client.get(f"/api/v1/orders/{r1_order_id}", headers=h2)
    assert tamper_res.status_code == 403
    assert "not authorized to view this retailer order" in tamper_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_retailer_cannot_view_another_retailers_custom_prices(
    client: AsyncClient,
    retailer1_token: str,
    retailer2_token: str,
):
    """
    Negative Test 3: Retailer only receives prices negotiated for their own account.
    """
    h1 = {"Authorization": f"Bearer {retailer1_token}"}
    h2 = {"Authorization": f"Bearer {retailer2_token}"}

    r1_prices = await client.get("/api/v1/retailers/me/prices", headers=h1)
    r2_prices = await client.get("/api/v1/retailers/me/prices", headers=h2)

    assert r1_prices.status_code == 200
    assert r2_prices.status_code == 200

    # Ensure client cannot pass a foreign retailer_id in headers or query to read other prices
    foreign_query = await client.get(
        "/api/v1/retailers/me/prices?retailer_id=00000000-0000-0000-0000-000000000000",
        headers=h1,
    )
    # The server strictly reads the retailer bound to the authenticated JWT session
    assert foreign_query.status_code == 200
    assert len(foreign_query.json()) == len(r1_prices.json())


@pytest.mark.asyncio
async def test_retailer_cannot_access_or_modify_another_retailers_ai_capture(
    client: AsyncClient,
    retailer1_token: str,
    retailer2_token: str,
):
    """
    Negative Test 4: Retailer 1 creates an AI capture session; Retailer 2 attempts to read or patch it.
    Must be blocked with HTTP 404 (or 403) to prevent information leakage.
    """
    h1 = {"Authorization": f"Bearer {retailer1_token}"}
    h2 = {"Authorization": f"Bearer {retailer2_token}"}

    # 1. Retailer 1 submits raw text
    cap_res = await client.post(
        "/api/v1/ai-capture/text",
        json={"raw_text": "5 peti biscuit chhota"},
        headers=h1,
    )
    assert cap_res.status_code == 201
    cap_data = cap_res.json()
    r1_session_id = cap_data["id"]
    r1_line_id = cap_data["lines"][0]["id"]

    # 2. Retailer 2 attempts to view Retailer 1's AI capture
    view_tamper = await client.get(f"/api/v1/ai-capture/{r1_session_id}", headers=h2)
    assert view_tamper.status_code == 404
    assert "does not belong to current retailer" in view_tamper.json()["detail"].lower()

    # 3. Retailer 2 attempts to patch Retailer 1's AI capture line
    patch_tamper = await client.patch(
        f"/api/v1/ai-capture/{r1_session_id}/lines/{r1_line_id}",
        json={"is_confirmed": True},
        headers=h2,
    )
    assert patch_tamper.status_code == 404

    # 4. Retailer 2 attempts to confirm Retailer 1's capture session
    confirm_tamper = await client.post(
        f"/api/v1/ai-capture/{r1_session_id}/confirm",
        headers=h2,
    )
    assert confirm_tamper.status_code == 404


# ===========================================================================
# 3. AUTHENTICATION & SESSION INVALIDITY (Scenario 5 & 8)
# ===========================================================================

@pytest.mark.asyncio
async def test_unauthenticated_order_submission(client: AsyncClient):
    """
    Negative Test 5: Submitting order without valid authentication token.
    Must return HTTP 401 Unauthorized.
    """
    res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(uuid.uuid4()), "quantity_cases": 1, "uom_type": "CASE"}]},
    )
    assert res.status_code == 401
    assert "missing" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_expired_or_tampered_jwt_tokens(client: AsyncClient):
    """
    Negative Test 8: Expired, forged, or garbage JWT tokens must be rejected.
    """
    # 1. Expired token (issued 2 hours ago, expired 1 hour ago)
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "role": "ROLE_RETAILER",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    res_expired = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == 401
    assert "invalid or expired" in res_expired.json()["detail"].lower()

    # 2. Token signed with wrong secret key (forged)
    forged_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "ROLE_ORDER_DESK", "exp": now + timedelta(hours=1)},
        "malicious-attacker-secret-key-123",
        algorithm="HS256",
    )
    res_forged = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert res_forged.status_code == 401

    # 3. Garbage token string
    res_garbage = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer NOT_A_REAL_JWT_TOKEN_XYZ"},
    )
    assert res_garbage.status_code == 401


# ===========================================================================
# 4. DUPLICATE ORDER APPROVAL (Scenario 7)
# ===========================================================================

@pytest.mark.asyncio
async def test_duplicate_order_approval_rejected(client: AsyncClient, retailer1_token: str, desk_token: str):
    """
    Negative Test 7: Attempting to approve an order that has already been approved.
    Must return HTTP 409 Conflict and prevent duplicate stock deductions.
    """
    h_ret = {"Authorization": f"Bearer {retailer1_token}"}
    h_desk = {"Authorization": f"Bearer {desk_token}"}

    # 1. Create order
    prod_res = await client.get("/api/v1/products", headers=h_ret)
    biscuit_id = next(p["id"] for p in prod_res.json()["items"] if p["sku_code"] == "SKU-BS-075")

    order_res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": biscuit_id, "quantity_cases": 1, "uom_type": "CASE"}]},
        headers=h_ret,
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # 2. First approval succeeds
    appr1 = await client.post(
        f"/api/v1/desk/orders/{order_id}/approve",
        json={"notes": "First valid approval"},
        headers=h_desk,
    )
    assert appr1.status_code == 200
    assert appr1.json()["status"] == "APPROVED"

    # 3. Second approval attempt on the same order must FAIL with HTTP 409 Conflict
    appr2 = await client.post(
        f"/api/v1/desk/orders/{order_id}/approve",
        json={"notes": "Duplicate second approval"},
        headers=h_desk,
    )
    assert appr2.status_code == 409
    assert "already approved" in appr2.json()["detail"].lower()


# ===========================================================================
# 5. MALICIOUS REQUEST PAYLOADS (Scenario 9)
# ===========================================================================

@pytest.mark.asyncio
async def test_negative_quantity_payload_rejected(client: AsyncClient, retailer1_token: str):
    """
    Negative Test 9a: Submitting orders with negative or zero quantities.
    Must be blocked by Pydantic validation with HTTP 422 Unprocessable Entity.
    """
    headers = {"Authorization": f"Bearer {retailer1_token}"}

    # Case A: Negative quantity (-5)
    bad_res_neg = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(uuid.uuid4()), "quantity_cases": -5, "uom_type": "CASE"}]},
        headers=headers,
    )
    assert bad_res_neg.status_code == 422

    # Case B: Zero quantity (0)
    bad_res_zero = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(uuid.uuid4()), "quantity_cases": 0, "uom_type": "CASE"}]},
        headers=headers,
    )
    assert bad_res_zero.status_code == 422


@pytest.mark.asyncio
async def test_csv_formula_injection_prevention(client: AsyncClient, retailer1_token: str, desk_token: str):
    """
    Negative Test 9b: Malicious retailer supplies CSV injection formula in delivery notes or store name.
    e.g. "=cmd|' /C calc'!A0", "+SUM(A1:A10)", "-2+3*4", "@SUM(1,1)".
    Must be sanitized with leading single quote (') in Tally CSV export.
    """
    h_ret = {"Authorization": f"Bearer {retailer1_token}"}
    h_desk = {"Authorization": f"Bearer {desk_token}"}

    # 1. Test unit sanitization function directly on all formula triggers
    assert sanitize_csv_cell("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
    assert sanitize_csv_cell("+SUM(A1:A10)") == "'+SUM(A1:A10)"
    assert sanitize_csv_cell("-12345") == "'-12345"
    assert sanitize_csv_cell("@SUM(1,1)") == "'@SUM(1,1)"
    assert sanitize_csv_cell("\tTAB_INJECTION") == "'\tTAB_INJECTION"
    assert sanitize_csv_cell("Normal Text") == "Normal Text"

    # 2. Submit order with formula injection payload in delivery_notes
    prod_res = await client.get("/api/v1/products", headers=h_ret)
    biscuit_id = next(p["id"] for p in prod_res.json()["items"] if p["sku_code"] == "SKU-BS-075")

    malicious_note = "=cmd|' /C calc'!A0"
    order_res = await client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_id": biscuit_id, "quantity_cases": 1, "uom_type": "CASE"}],
            "delivery_notes": malicious_note,
        },
        headers=h_ret,
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # 3. Approve order via desk
    appr_res = await client.post(
        f"/api/v1/desk/orders/{order_id}/approve",
        json={"notes": "Approved for export test"},
        headers=h_desk,
    )
    assert appr_res.status_code == 200

    # 4. Generate Tally CSV Export Batch
    exp_res = await client.post(
        "/api/v1/desk/exports",
        json={"order_ids": [order_id]},
        headers=h_desk,
    )
    assert exp_res.status_code == 201
    batch_id = exp_res.json()["id"]

    # 5. Download generated CSV
    dl_res = await client.get(f"/api/v1/desk/exports/{batch_id}/download", headers=h_desk)
    assert dl_res.status_code == 200
    csv_text = dl_res.text

    # Parse CSV and ensure the formula is neutralized with prepended quote
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) >= 2  # Header + line
    remarks_col_idx = 13  # "Desk Approval Remarks"
    assert rows[1][remarks_col_idx] == f"'{malicious_note}"
    # Verify raw executable formula does NOT appear bare
    assert f",=cmd|" not in csv_text


@pytest.mark.asyncio
async def test_ai_endpoint_rate_limiting(client: AsyncClient, retailer1_token: str, monkeypatch):
    """
    Negative Test 9c: Rapid automated spam on AI text capture endpoint triggers HTTP 429 Too Many Requests.
    """
    async def mock_extract(raw_text: str):
        return AICaptureService._extract_lines_local(raw_text), True, "Mock local fallback"

    monkeypatch.setattr(AICaptureService, "extract_lines_with_gemini", mock_extract)
    monkeypatch.setattr(AICaptureService, "extract_lines_with_openai", mock_extract)

    headers = {"Authorization": f"Bearer {retailer1_token}"}
    ai_rate_limiter.reset()

    # Rate limit is 15 requests per 60s
    for i in range(15):
        res = await client.post(
            "/api/v1/ai-capture/text",
            json={"raw_text": f"biscuit 5 peti order {i}"},
            headers=headers,
        )
        assert res.status_code == 201

    # 16th request must trigger HTTP 429 Too Many Requests
    breach_res = await client.post(
        "/api/v1/ai-capture/text",
        json={"raw_text": "biscuit 5 peti order 16"},
        headers=headers,
    )
    assert breach_res.status_code == 429
    assert "rate limit exceeded" in breach_res.json()["detail"].lower()
    assert "retry-after" in breach_res.headers

    # Reset limiter after test
    ai_rate_limiter.reset()

