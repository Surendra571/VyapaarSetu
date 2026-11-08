import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


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
    """Obtain JWT token for Retailer 1 (Patel Kirana)."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826011111", "otp_code": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
async def retailer2_token(client: AsyncClient):
    """Obtain JWT token for Retailer 2 (Agrawal Provision)."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826022222", "otp_code": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
async def desk_token(client: AsyncClient):
    """Obtain JWT token for Order Desk Officer (Sanjay Sharma)."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826000000", "otp_code": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# =====================================================================
# 1. AUTHENTICATION MODULE TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_auth_demo_login_retailer(client: AsyncClient):
    """Verify retailer mock OTP authentication."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826011111", "otp_code": "123456"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ROLE_RETAILER"
    assert data["user"]["retailer"]["store_name"] == "Patel Kirana & General Stores"
    assert data["user"]["retailer"]["retailer_code"] == "RET-JBP-001"
    assert Decimal(str(data["user"]["retailer"]["credit_limit"])) == Decimal("50000.00")


@pytest.mark.asyncio
async def test_auth_demo_login_order_desk(client: AsyncClient):
    """Verify order desk mock OTP authentication."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826000000", "otp_code": "123456"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "ROLE_ORDER_DESK"
    assert data["user"]["retailer"] is None


@pytest.mark.asyncio
async def test_auth_invalid_otp(client: AsyncClient):
    """Verify invalid OTP rejection with 401."""
    res = await client.post(
        "/api/v1/auth/demo-login",
        json={"phone_number": "9826011111", "otp_code": "999999"},
    )
    assert res.status_code == 401
    assert "Invalid OTP code" in res.json()["detail"]


@pytest.mark.asyncio
async def test_auth_me_and_logout(client: AsyncClient, retailer_token: str):
    """Verify /auth/me returns profile and /auth/logout invalidates session."""
    headers = {"Authorization": f"Bearer {retailer_token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["phone_number"] == "9826011111"

    # Unauthenticated request fails
    fail_res = await client.get("/api/v1/auth/me")
    assert fail_res.status_code == 401

    # Logout
    logout_res = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "success"


# =====================================================================
# 2. CATALOGUE AND PRICING TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_catalog_products_and_availability(client: AsyncClient, retailer_token: str):
    """Verify product list, pagination, and single product stock query."""
    headers = {"Authorization": f"Bearer {retailer_token}"}
    res = await client.get("/api/v1/products?page=1&page_size=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3

    # Check unauthoritative price notice
    item = data["items"][0]
    assert "exclude GST" in item["price_notice"]

    # Get specific product by ID
    product_id = item["id"]
    detail_res = await client.get(f"/api/v1/products/{product_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == product_id
    assert "inventory" in detail

    # Check availability endpoint
    avail_res = await client.get(f"/api/v1/products/{product_id}/availability", headers=headers)
    assert avail_res.status_code == 200
    avail = avail_res.json()
    assert "available_cases" in avail
    assert "stock_cases" in avail


@pytest.mark.asyncio
async def test_retailer_contracted_prices(client: AsyncClient, retailer_token: str):
    """Verify contracted pricing: Retailer 1 has custom price overrides."""
    headers = {"Authorization": f"Bearer {retailer_token}"}
    res = await client.get("/api/v1/retailers/me/prices", headers=headers)
    assert res.status_code == 200
    pricelist = res.json()
    assert len(pricelist) >= 3

    biscuit_price = next(p for p in pricelist if p["sku_code"] == "SKU-BS-075")
    assert Decimal(str(biscuit_price["effective_price"])) == Decimal("7.90")
    assert biscuit_price["is_custom_price"] is True

    # Detergent has custom price ₹99.00 for Retailer 1
    detergent_price = next(p for p in pricelist if p["sku_code"] == "SKU-DT-1KG")
    assert Decimal(str(detergent_price["effective_price"])) == Decimal("99.00")
    assert detergent_price["is_custom_price"] is True

    # Tea leaf has no custom price, should fallback to default 118.00
    tea_price = next(p for p in pricelist if p["sku_code"] == "SKU-TE-250")
    assert Decimal(str(tea_price["effective_price"])) == Decimal("118.00")
    assert tea_price["is_custom_price"] is False


@pytest.mark.asyncio
async def test_schemes_listing(client: AsyncClient, retailer_token: str):
    """Verify active schemes listing."""
    headers = {"Authorization": f"Bearer {retailer_token}"}
    res = await client.get("/api/v1/schemes", headers=headers)
    assert res.status_code == 200
    schemes = res.json()
    assert len(schemes) >= 2
    codes = [s["scheme_code"] for s in schemes]
    assert "SCH-BS-10P1" in codes
    assert "SCH-DT-5DISC3" in codes


# =====================================================================
# 3. ORDERS MODULE TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_order_preview_calculation(client: AsyncClient, retailer_token: str):
    """Verify order preview applies trade schemes, free goods, and credit standing."""
    headers = {"Authorization": f"Bearer {retailer_token}"}

    # Fetch product IDs
    prod_res = await client.get("/api/v1/products", headers=headers)
    products = {p["sku_code"]: p for p in prod_res.json()["items"]}

    biscuit_id = products["SKU-BS-075"]["id"]
    detergent_id = products["SKU-DT-1KG"]["id"]

    # Preview 10 cases of biscuit (Qualifies for 1 free case) and 5 cases of detergent (3% discount)
    payload = {
        "items": [
            {"product_id": biscuit_id, "quantity_cases": 10, "uom_type": "CASE"},
            {"product_id": detergent_id, "quantity_cases": 5, "uom_type": "CASE"},
        ]
    }
    res = await client.post("/api/v1/orders/preview", json=payload, headers=headers)
    assert res.status_code == 200
    preview = res.json()

    # Verify free goods on biscuit line
    b_line = next(l for l in preview["lines"] if l["sku_code"] == "SKU-BS-075")
    assert b_line["free_goods_qty"] == 1
    assert Decimal(str(b_line["unit_price_excl_gst"])) == Decimal("7.90")  # Custom price for Ret 1

    # Verify 3% discount on detergent line
    d_line = next(l for l in preview["lines"] if l["sku_code"] == "SKU-DT-1KG")
    assert Decimal(str(d_line["discount_amount_excl_gst"])) > Decimal("0.00")

    # Verify GST disclaimer
    assert "exclude GST" in preview["tax_notice"]
    assert preview["credit_check"]["will_trigger_credit_hold"] is False


@pytest.mark.asyncio
async def test_order_submission_insufficient_stock_fails(client: AsyncClient, retailer_token: str):
    """Business Constraint 4: Explicit insufficient-stock handling (Never create silent partial orders)."""
    headers = {"Authorization": f"Bearer {retailer_token}"}
    prod_res = await client.get("/api/v1/products", headers=headers)
    products = {p["sku_code"]: p for p in prod_res.json()["items"]}

    tea_id = products["SKU-TE-250"]["id"]  # 0 cases in stock

    payload = {
        "items": [
            {"product_id": tea_id, "quantity_cases": 5, "uom_type": "CASE"}
        ]
    }
    res = await client.post("/api/v1/orders", json=payload, headers=headers)
    assert res.status_code == 409  # Conflict
    assert "insufficient stock" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_order_submission_and_multi_tenant_isolation(
    client: AsyncClient, retailer_token: str, retailer2_token: str
):
    """Verify order creation, inventory reservation, and multi-tenant access restriction."""
    headers1 = {"Authorization": f"Bearer {retailer_token}"}
    headers2 = {"Authorization": f"Bearer {retailer2_token}"}

    prod_res = await client.get("/api/v1/products", headers=headers1)
    biscuit_id = next(p["id"] for p in prod_res.json()["items"] if p["sku_code"] == "SKU-BS-075")

    # Submit valid order
    order_payload = {
        "items": [
            {"product_id": biscuit_id, "quantity_cases": 10, "uom_type": "CASE"}
        ],
        "delivery_notes": "Urgent delivery to Gorakhpur store",
    }
    res = await client.post("/api/v1/orders", json=order_payload, headers=headers1)
    assert res.status_code == 201
    order_data = res.json()
    order_id = order_data["id"]
    assert order_data["status"] == "PENDING_DESK_APPROVAL"
    assert len(order_data["items"]) == 1
    assert order_data["items"][0]["free_item_qty"] == 1

    # Retailer 1 can access own order
    own_res = await client.get(f"/api/v1/orders/{order_id}", headers=headers1)
    assert own_res.status_code == 200

    # Business Constraint 9: Retailer 2 attempts to view Retailer 1's order -> 403 Forbidden
    cross_res = await client.get(f"/api/v1/orders/{order_id}", headers=headers2)
    assert cross_res.status_code == 403
    assert "not authorized" in cross_res.json()["detail"].lower()


# =====================================================================
# 4. AI ORDER CAPTURE TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_ai_capture_pipeline(client: AsyncClient, retailer_token: str):
    """Test AI capture text parsing, disambiguation patch, and cart preview confirmation."""
    headers = {"Authorization": f"Bearer {retailer_token}"}

    # 1. Parse raw WhatsApp order
    raw_text = "5 case parle g aur 10 case detergent powder"
    post_res = await client.post(
        "/api/v1/ai-capture/text",
        json={"raw_text": raw_text},
        headers=headers,
    )
    assert post_res.status_code == 201
    capture = post_res.json()
    capture_id = capture["id"]
    assert len(capture["lines"]) == 2
    assert "AI cannot place orders automatically" in capture["notice"]

    # 2. Get AI capture by session ID
    get_res = await client.get(f"/api/v1/ai-capture/{capture_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == capture_id

    # 3. Patch uncertain or review line
    line_to_patch = capture["lines"][0]
    patch_res = await client.patch(
        f"/api/v1/ai-capture/{capture_id}/lines/{line_to_patch['id']}",
        json={
            "resolved_quantity": 6,
            "is_confirmed": True,
            "resolution_note": "Confirmed 6 cases with store owner",
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    patched_line = patch_res.json()
    assert patched_line["is_confirmed"] is True
    assert patched_line["resolved_quantity"] == 6

    # 4. Confirm session into cart preview
    line2 = capture["lines"][1]
    if not line2["is_confirmed"]:
        await client.patch(
            f"/api/v1/ai-capture/{capture_id}/lines/{line2['id']}",
            json={"is_confirmed": True},
            headers=headers,
        )

    confirm_res = await client.post(f"/api/v1/ai-capture/{capture_id}/confirm", headers=headers)
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["confirmed_lines_count"] == 2
    assert "order_preview" in confirm_data


# =====================================================================
# 5. ORDER DESK WORKFLOW TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_order_desk_role_security(client: AsyncClient, retailer_token: str):
    """Verify that a Retailer role is forbidden from Order Desk endpoints."""
    headers = {"Authorization": f"Bearer {retailer_token}"}
    res = await client.get("/api/v1/desk/orders", headers=headers)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_order_desk_review_and_dispatch_lifecycle(
    client: AsyncClient, retailer_token: str, desk_token: str
):
    """
    Complete Order Desk lifecycle:
    1. Retailer creates order.
    2. Desk lists orders and reviews order detail.
    3. Desk modifies line item quantity.
    4. Desk places order on hold, then approves order.
    5. Desk triggers Tally export batch and downloads CSV.
    """
    retailer_h = {"Authorization": f"Bearer {retailer_token}"}
    desk_h = {"Authorization": f"Bearer {desk_token}"}

    # Fetch product ID
    prod_res = await client.get("/api/v1/products", headers=retailer_h)
    detergent_id = next(p["id"] for p in prod_res.json()["items"] if p["sku_code"] == "SKU-DT-1KG")

    # 1. Retailer submits order for 10 cases
    create_res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": detergent_id, "quantity_cases": 10, "uom_type": "CASE"}]},
        headers=retailer_h,
    )
    assert create_res.status_code == 201
    order = create_res.json()
    order_id = order["id"]
    line_id = order["items"][0]["id"]

    # 2. Desk lists orders
    desk_list_res = await client.get("/api/v1/desk/orders", headers=desk_h)
    assert desk_list_res.status_code == 200
    assert desk_list_res.json()["total"] >= 1

    # Desk inspects detail
    desk_detail_res = await client.get(f"/api/v1/desk/orders/{order_id}", headers=desk_h)
    assert desk_detail_res.status_code == 200
    assert desk_detail_res.json()["retailer_name"] == "Patel Kirana & General Stores"

    # 3. Desk modifies line quantity from 10 to 8
    patch_line_res = await client.patch(
        f"/api/v1/desk/orders/{order_id}/lines/{line_id}",
        json={"approved_qty": 8, "reason": "Physical damaged cases in warehouse"},
        headers=desk_h,
    )
    assert patch_line_res.status_code == 200
    updated_order = patch_line_res.json()
    assert updated_order["items"][0]["approved_qty"] == 8

    # 4. Desk puts order on hold
    hold_res = await client.post(
        f"/api/v1/desk/orders/{order_id}/hold",
        json={"reason": "Awaiting Cheque clearance"},
        headers=desk_h,
    )
    assert hold_res.status_code == 200
    assert hold_res.json()["status"] == "CREDIT_HOLD"

    # Desk approves order with credit override
    approve_res = await client.post(
        f"/api/v1/desk/orders/{order_id}/approve",
        json={"notes": "Cheque received and verified", "override_credit_hold": True},
        headers=desk_h,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # 5. Desk generates Tally CSV export batch
    export_res = await client.post(
        "/api/v1/desk/exports",
        json={"order_ids": [order_id]},
        headers=desk_h,
    )
    assert export_res.status_code == 201
    batch = export_res.json()
    assert batch["order_count"] >= 1
    assert "download_url" in batch

    # Download Tally CSV file
    dl_res = await client.get(f"/api/v1/desk/exports/{batch['id']}/download", headers=desk_h)
    assert dl_res.status_code == 200
    assert "text/csv" in dl_res.headers["content-type"]
    csv_text = dl_res.text
    assert "Voucher Number,Voucher Date,Party Name" in csv_text
    assert "SKU-DT-1KG" in csv_text


@pytest.mark.asyncio
async def test_order_rejection_releases_inventory(
    client: AsyncClient, retailer_token: str, desk_token: str
):
    """Verify that rejecting an order releases reserved inventory back to available stock."""
    retailer_h = {"Authorization": f"Bearer {retailer_token}"}
    desk_h = {"Authorization": f"Bearer {desk_token}"}

    prod_res = await client.get("/api/v1/products", headers=retailer_h)
    biscuit = next(p for p in prod_res.json()["items"] if p["sku_code"] == "SKU-BS-075")
    biscuit_id = biscuit["id"]

    avail_before = await client.get(f"/api/v1/products/{biscuit_id}/availability", headers=retailer_h)
    stock_before = avail_before.json()["available_cases"]

    # Submit order for 5 cases
    order_res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": biscuit_id, "quantity_cases": 5, "uom_type": "CASE"}]},
        headers=retailer_h,
    )
    order_id = order_res.json()["id"]

    # Check available stock reduced by 5
    avail_during = await client.get(f"/api/v1/products/{biscuit_id}/availability", headers=retailer_h)
    assert avail_during.json()["available_cases"] == stock_before - 5

    # Desk rejects order
    reject_res = await client.post(
        f"/api/v1/desk/orders/{order_id}/reject",
        json={"reason": "Customer cancelled order"},
        headers=desk_h,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"

    # Verify inventory was restored
    avail_after = await client.get(f"/api/v1/products/{biscuit_id}/availability", headers=retailer_h)
    assert avail_after.json()["available_cases"] == stock_before
