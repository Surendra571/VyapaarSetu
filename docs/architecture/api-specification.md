# VyapaarSetu — REST API Specification
**Version:** 1.0.0 (Phase 0 Planning)  
**Base URL:** `/api/v1`  
**Authentication Scheme:** HTTP Bearer JWT (`Authorization: Bearer <token>`)

---

## 1. Authentication Endpoints

### 1.1 Request Retailer OTP
- **Method:** `POST`
- **URL:** `/api/v1/auth/request-otp`
- **Auth Required:** None (Public)
- **Role Permission:** Public
- **Description:** Sends a 6-digit one-time password to the registered mobile number.
- **Request Schema:**
```json
{
  "phone": "+919876543210"
}
```
- **Response Schema (`200 OK`):**
```json
{
  "success": true,
  "message": "OTP sent successfully to registered mobile number.",
  "retry_after_seconds": 60
}
```
- **Error Responses:**
  - `400 Bad Request`: Invalid Indian 10-digit phone format.
  - `404 Not Found`: Mobile number not registered with Company A.
  - `429 Too Many Requests`: Rate limit exceeded (max 3 attempts per 15 minutes).

---

### 1.2 Verify Retailer OTP
- **Method:** `POST`
- **URL:** `/api/v1/auth/verify-otp`
- **Auth Required:** None (Public)
- **Role Permission:** Public
- **Description:** Verifies OTP and issues retailer JWT token.
- **Request Schema:**
```json
{
  "phone": "+919876543210",
  "otp": "459012"
}
```
- **Response Schema (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "role": "retailer",
    "retailer_id": "8f80459c-6a1e-42c2-8ffb-8326be8eb5cb",
    "store_name": "Sharma Kirana Store",
    "owner_name": "Ramesh Sharma",
    "city": "Jabalpur",
    "credit_status": {
      "credit_limit": 50000.00,
      "credit_used": 12450.00,
      "available_credit": 37550.00,
      "is_credit_hold": false
    }
  }
}
```
- **Error Responses:**
  - `400 Bad Request`: Malformed payload or expired OTP.
  - `401 Unauthorized`: Incorrect OTP provided.
  - `403 Forbidden`: Retailer account is deactivated or suspended.

---

### 1.3 Staff / Order Desk Login
- **Method:** `POST`
- **URL:** `/api/v1/auth/login-staff`
- **Auth Required:** None (Public)
- **Role Permission:** Public
- **Request Schema:**
```json
{
  "email": "desk.operator@company-a.com",
  "password": "SecureStaffPassword123!"
}
```
- **Response Schema (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 43200,
  "user": {
    "id": "7b134d19-482a-4318-bd2e-50669930811e",
    "role": "order_desk",
    "full_name": "Amit Patel",
    "email": "desk.operator@company-a.com"
  }
}
```
- **Error Responses:**
  - `401 Unauthorized`: Invalid credentials.
  - `403 Forbidden`: User account does not have staff permissions.

---

## 2. Retailer Catalogue & Pricing Endpoints

### 2.1 Get Retailer Products List
- **Method:** `GET`
- **URL:** `/api/v1/retailer/products`
- **Auth Required:** Yes
- **Role Permission:** `retailer`
- **Query Parameters:**
  - `brand_id` (optional, UUID)
  - `category_id` (optional, UUID)
  - `search` (optional, string)
  - `in_stock_only` (optional, boolean, default false)
- **Response Schema (`200 OK`):**
```json
{
  "items": [
    {
      "id": "a1b2c3d4-0001-4000-8000-000000000001",
      "sku": "SKU-BS-075",
      "brand_name": "Parle",
      "name": "Glucose Biscuit 75g",
      "hindi_name": "ग्लूकोज बिस्कुट 75 ग्राम",
      "unit": "case",
      "case_pack": 96,
      "mrp": 10.00,
      "dealer_price": 8.10,
      "stock_status": "IN_STOCK",
      "stock_cases_available": 340,
      "active_schemes": [
        {
          "id": "s1-0001",
          "code": "SCHEME-BS-10P1",
          "name": "Buy 10 Cases, Get 1 Free",
          "scheme_type": "BUY_X_GET_Y_FREE",
          "min_qty": 10,
          "free_qty": 1
        }
      ]
    },
    {
      "id": "a1b2c3d4-0002-4000-8000-000000000002",
      "sku": "SKU-DT-1KG",
      "brand_name": "Wheel",
      "name": "Detergent Powder 1kg",
      "hindi_name": "डिटर्जेंट पाउडर 1 किलो",
      "unit": "case",
      "case_pack": 20,
      "mrp": 120.00,
      "dealer_price": 101.50,
      "stock_status": "IN_STOCK",
      "stock_cases_available": 85,
      "active_schemes": [
        {
          "id": "s2-0002",
          "code": "SCHEME-DT-5P3",
          "name": "3% off on 5 or more cases",
          "scheme_type": "PERCENTAGE_DISCOUNT",
          "min_qty": 5,
          "discount_percentage": 3.00
        }
      ]
    },
    {
      "id": "a1b2c3d4-0003-4000-8000-000000000003",
      "sku": "SKU-TE-250",
      "brand_name": "Tata Tea",
      "name": "Tea Leaf 250g",
      "hindi_name": "चाय पत्ती 250 ग्राम",
      "unit": "case",
      "case_pack": 40,
      "mrp": 140.00,
      "dealer_price": 118.00,
      "stock_status": "OUT_OF_STOCK",
      "stock_cases_available": 0,
      "active_schemes": []
    }
  ],
  "total": 3
}
```
- **Error Responses:**
  - `401 Unauthorized`: Token missing or expired.
  - `403 Forbidden`: Caller lacks retailer role.

---

## 3. AI Order Capture & Matching Endpoints

### 3.1 Parse Natural Language Order Text
- **Method:** `POST`
- **URL:** `/api/v1/ai/parse-order`
- **Auth Required:** Yes
- **Role Permission:** `retailer`, `order_desk`
- **Description:** Ingests raw Hinglish/Hindi text (or transcribed voice note), extracts product intent via OpenAI structured outputs, matches against active catalog SKUs, and returns candidate line items with confidence scores.
- **Request Schema:**
```json
{
  "raw_text": "bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti"
}
```
- **Response Schema (`200 OK`):**
```json
{
  "original_text": "bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti",
  "parsed_items": [
    {
      "query_term": "biscuit chhota",
      "requested_qty": 5,
      "raw_unit": "peti",
      "matched_sku": "SKU-BS-075",
      "product_name": "Glucose Biscuit 75g",
      "unit": "case",
      "case_pack": 96,
      "dealer_price": 8.10,
      "confidence": 0.96,
      "match_source": "ALIAS_EXACT",
      "stock_status": "IN_STOCK",
      "stock_available": 340,
      "alternatives": []
    },
    {
      "query_term": "washing powder 1 kilo",
      "requested_qty": 2,
      "raw_unit": "peti",
      "matched_sku": "SKU-DT-1KG",
      "product_name": "Detergent Powder 1kg",
      "unit": "case",
      "case_pack": 20,
      "dealer_price": 101.50,
      "confidence": 0.93,
      "match_source": "FUZZY_TOKEN_MATCH",
      "stock_status": "IN_STOCK",
      "stock_available": 85,
      "alternatives": []
    },
    {
      "query_term": "chai patti 250 wala",
      "requested_qty": 1,
      "raw_unit": "peti",
      "matched_sku": "SKU-TE-250",
      "product_name": "Tea Leaf 250g",
      "unit": "case",
      "case_pack": 40,
      "dealer_price": 118.00,
      "confidence": 0.91,
      "match_source": "ALIAS_EXACT",
      "stock_status": "OUT_OF_STOCK",
      "stock_available": 0,
      "warning": "Item is currently out of stock",
      "alternatives": []
    }
  ],
  "unmatched_terms": []
}
```
- **Error Responses:**
  - `400 Bad Request`: Empty or excessively long (> 1000 chars) input text.
  - `422 Unprocessable Entity`: Structured output failed validation.
  - `503 Service Unavailable`: External AI API unreachable (graceful fallback prompt provided).

---

## 4. Cart & Scheme Calculation Endpoints

### 4.1 Calculate Cart Totals & Evaluate Schemes
- **Method:** `POST`
- **URL:** `/api/v1/cart/calculate`
- **Auth Required:** Yes
- **Role Permission:** `retailer`, `order_desk`
- **Description:** Deterministic pure-calculation endpoint that applies retailer-specific prices and promotional schemes.
- **Request Schema:**
```json
{
  "items": [
    {
      "product_id": "a1b2c3d4-0001-4000-8000-000000000001",
      "quantity_cases": 10
    },
    {
      "product_id": "a1b2c3d4-0002-4000-8000-000000000002",
      "quantity_cases": 5
    }
  ]
}
```
- **Response Schema (`200 OK`):**
```json
{
  "line_items": [
    {
      "product_id": "a1b2c3d4-0001-4000-8000-000000000001",
      "sku": "SKU-BS-075",
      "name": "Glucose Biscuit 75g",
      "ordered_cases": 10,
      "case_price": 777.60,
      "subtotal": 7776.00,
      "applied_scheme": {
        "scheme_id": "s1-0001",
        "scheme_code": "SCHEME-BS-10P1",
        "name": "Buy 10 Cases, Get 1 Free",
        "free_cases_added": 1,
        "discount_amount": 0.00
      },
      "line_total": 7776.00
    },
    {
      "product_id": "a1b2c3d4-0002-4000-8000-000000000002",
      "sku": "SKU-DT-1KG",
      "name": "Detergent Powder 1kg",
      "ordered_cases": 5,
      "case_price": 2030.00,
      "subtotal": 10150.00,
      "applied_scheme": {
        "scheme_id": "s2-0002",
        "scheme_code": "SCHEME-DT-5P3",
        "name": "3% off on 5 or more cases",
        "free_cases_added": 0,
        "discount_amount": 304.50
      },
      "line_total": 9845.50
    }
  ],
  "free_items_summary": [
    {
      "product_id": "a1b2c3d4-0001-4000-8000-000000000001",
      "sku": "SKU-BS-075",
      "name": "Glucose Biscuit 75g (Scheme Free Case)",
      "free_cases": 1
    }
  ],
  "gross_amount": 17926.00,
  "total_scheme_discount": 304.50,
  "taxable_amount": 17621.50,
  "estimated_gst": 0.00,
  "net_payable_amount": 17621.50
}
```

---

## 5. Order Management Endpoints

### 5.1 Submit Order
- **Method:** `POST`
- **URL:** `/api/v1/orders`
- **Auth Required:** Yes
- **Role Permission:** `retailer`
- **Headers:** `Idempotency-Key: <UUIDv4>`
- **Request Schema:**
```json
{
  "raw_input_text": "bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo",
  "input_source": "AI_TEXT_PARSER",
  "notes": "Please deliver before 1 PM",
  "items": [
    {
      "product_id": "a1b2c3d4-0001-4000-8000-000000000001",
      "quantity_cases": 10,
      "ai_confidence": 0.96
    },
    {
      "product_id": "a1b2c3d4-0002-4000-8000-000000000002",
      "quantity_cases": 5,
      "ai_confidence": 0.93
    }
  ]
}
```
- **Response Schema (`201 Created`):**
```json
{
  "id": "e9b21f37-1234-4567-89ab-cdef01234567",
  "order_number": "VS-2026-1049",
  "status": "PENDING_DESK_REVIEW",
  "created_at": "2026-11-03T16:45:00Z",
  "total_cases": 15,
  "total_free_cases": 1,
  "net_payable_amount": 17621.50,
  "is_credit_hold": false,
  "message": "Order placed successfully. Sent to Company A Order Desk for review."
}
```
- **Error Responses:**
  - `400 Bad Request`: Out of stock item requested or empty cart.
  - `409 Conflict`: Duplicate `Idempotency-Key` submitted with different payload.
  - `422 Unprocessable Entity`: Validation failure on product IDs or quantities.

---

## 6. Order Desk Operations Endpoints

### 6.1 List Incoming Orders
- **Method:** `GET`
- **URL:** `/api/v1/desk/orders`
- **Auth Required:** Yes
- **Role Permission:** `order_desk`, `admin`
- **Query Parameters:**
  - `status` (`PENDING_DESK_REVIEW`, `CREDIT_HOLD`, `APPROVED`, `EXPORTED`, `REJECTED`)
  - `search` (store name, order number, retailer phone)
  - `page` (default 1)
  - `limit` (default 25)
- **Response Schema (`200 OK`):**
```json
{
  "items": [
    {
      "id": "e9b21f37-1234-4567-89ab-cdef01234567",
      "order_number": "VS-2026-1049",
      "retailer": {
        "id": "8f80459c-6a1e-42c2-8ffb-8326be8eb5cb",
        "store_name": "Sharma Kirana Store",
        "owner_name": "Ramesh Sharma",
        "phone": "+919876543210",
        "city": "Jabalpur"
      },
      "status": "PENDING_DESK_REVIEW",
      "raw_input_text": "bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo",
      "total_cases": 15,
      "total_amount": 17621.50,
      "is_credit_hold": false,
      "created_at": "2026-11-03T16:45:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 25
}
```

---

### 6.2 Approve Order
- **Method:** `POST`
- **URL:** `/api/v1/desk/orders/{order_id}/approve`
- **Auth Required:** Yes
- **Role Permission:** `order_desk`, `admin`
- **Request Schema:**
```json
{
  "approval_note": "Verified with Ramesh ji over phone. Dispatched in Route 2."
}
```
- **Response Schema (`200 OK`):**
```json
{
  "id": "e9b21f37-1234-4567-89ab-cdef01234567",
  "order_number": "VS-2026-1049",
  "status": "APPROVED",
  "approved_by": "Amit Patel",
  "approved_at": "2026-11-03T17:05:12Z",
  "message": "Order successfully approved and queued for Tally export."
}
```
- **Error Responses:**
  - `400 Bad Request`: Cannot approve order currently under active credit hold without explicit override flag.
  - `404 Not Found`: Order ID does not exist.

---

### 6.3 Export Orders to Tally CSV
- **Method:** `GET`
- **URL:** `/api/v1/desk/orders/export/tally`
- **Auth Required:** Yes
- **Role Permission:** `order_desk`, `admin`
- **Query Parameters:**
  - `order_ids` (comma-separated UUIDs)
  - `date` (YYYY-MM-DD)
- **Response Headers:**
  - `Content-Type: text/csv; charset=utf-8`
  - `Content-Disposition: attachment; filename="tally_sales_orders_20261103.csv"`
- **Response Body Format (CSV):**
```csv
VoucherType,VoucherNumber,Date,PartyLedgerName,ItemName,QuantityCases,Rate,DiscountPercent,FreeCases,Narration
Sales Order,VS-2026-1049,03-11-2026,Sharma Kirana Store,Glucose Biscuit 75g,10,777.60,0.00,1,VyapaarSetu App Order
Sales Order,VS-2026-1049,03-11-2026,Sharma Kirana Store,Detergent Powder 1kg,5,2030.00,3.00,0,VyapaarSetu App Order
```

