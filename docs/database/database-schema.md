# VyapaarSetu — Relational Database Schema Specification
**Engine:** PostgreSQL 15+ ONLY  
**Naming Conventions:** Snake_case for tables and columns; singular nouns for entities; explicit foreign key prefixes.  
**Financial Precision:** `NUMERIC(12, 2)` for currency and rates; `INTEGER` for discrete case/unit counts.

---

## 1. Schema Tables Overview

| Table Name | Description | Cardinality / Scope |
| :--- | :--- | :--- |
| `users` | Unified credentials, phone numbers, roles, and status | Global auth identity |
| `retailers` | Kirana profile, trade name, GSTIN, credit metrics, address | 1:1 with `users` (where role = retailer) |
| `brands` | The 4 distributor brand principals (e.g., Parle, Wheel, Tata Tea) | Core master data |
| `categories` | Hierarchical product taxonomy (Biscuits, Detergents, Tea) | Master taxonomy |
| `products` | Master catalogue SKUs, pack sizes, MRP, base dealer price | Master catalogue |
| `retailer_custom_prices` | Retailer-specific price overrides per SKU | Retailer-product mapping |
| `inventory` | Available warehouse stock in cases and units, reserved buffer | Warehouse real-time stock |
| `product_aliases` | Hindi/Hinglish colloquial aliases for natural language matching | AI match dictionary |
| `schemes` | Trade promotions (Buy X Get Y Free, percentage discounts) | Promotional rules |
| `scheme_products` | Association table linking schemes to eligible/reward products | Scheme mapping |
| `orders` | Header record of retail wholesale orders and lifecycle state | Transactional master |
| `order_items` | Line items including requested vs approved cases, schemes | Transactional details |
| `audit_logs` | Immutable audit log of desk interventions, approvals, credit overrides | Compliance & traceability |

---

## 2. Table Specifications

### 2.1 `users`
Stores login identities for both retailers and internal Company A desk/admin staff.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(15) UNIQUE,                  -- Mandatory for retailers (E.164, e.g. +919876543210)
    email VARCHAR(255) UNIQUE,                 -- Mandatory for desk/admin staff
    hashed_password VARCHAR(255),              -- Nullable for passwordless phone OTP users
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('retailer', 'order_desk', 'admin', 'salesman')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_role ON users(role);
```
- **Primary Key:** `id` (UUID)
- **Unique Constraints:** `phone`, `email`
- **Relationships:**
  - `users.id` -> `retailers.user_id` (1:1)
  - `users.id` -> `audit_logs.performed_by_user_id` (1:N)

---

### 2.2 `retailers`
Distributor-specific profile for each of the ~1,800 kirana shops.

```sql
CREATE TABLE retailers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    store_name VARCHAR(200) NOT NULL,
    owner_name VARCHAR(150) NOT NULL,
    gstin VARCHAR(15),                         -- Optional for small composition retailers
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL DEFAULT 'Jabalpur',
    state VARCHAR(100) NOT NULL DEFAULT 'Madhya Pradesh',
    pincode VARCHAR(10) NOT NULL,
    route_beat VARCHAR(100),                   -- Delivery route / beat identifier in Jabalpur
    credit_limit NUMERIC(12, 2) NOT NULL DEFAULT 25000.00,
    credit_used NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    is_credit_hold BOOLEAN NOT NULL DEFAULT FALSE,
    credit_hold_reason TEXT,
    price_tier VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_credit_values CHECK (credit_limit >= 0 AND credit_used >= 0)
);

CREATE INDEX idx_retailers_city_beat ON retailers(city, route_beat);
CREATE INDEX idx_retailers_credit_hold ON retailers(is_credit_hold);
```
- **Primary Key:** `id` (UUID)
- **Foreign Keys:** `user_id` -> `users(id)`
- **Relationships:**
  - `retailers.id` -> `orders.retailer_id` (1:N)
  - `retailers.id` -> `retailer_custom_prices.retailer_id` (1:N)

---

### 2.3 `brands`
The 4 distributor partner brands represented by Company A.

```sql
CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,          -- e.g., 'PARLE', 'WHEEL', 'TATA_TEA'
    name VARCHAR(150) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```
- **Relationships:** `brands.id` -> `products.brand_id` (1:N)

---

### 2.4 `categories`
Product categorization taxonomy.

```sql
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

### 2.5 `products`
Master catalog items supplied to kirana retailers.

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(50) NOT NULL UNIQUE,           -- e.g., 'SKU-BS-075', 'SKU-DT-1KG'
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,                -- e.g., 'Glucose Biscuit 75g'
    hindi_name VARCHAR(250),                   -- e.g., 'ग्लूकोज बिस्कुट 75 ग्राम'
    description TEXT,
    unit VARCHAR(20) NOT NULL DEFAULT 'case',  -- 'case', 'box', 'piece'
    case_pack INTEGER NOT NULL DEFAULT 1,      -- e.g., 96 units/case for biscuit, 20 for detergent
    mrp NUMERIC(12, 2) NOT NULL,               -- Retail selling price printed on unit
    base_dealer_price NUMERIC(12, 2) NOT NULL, -- Wholesale price (per case or unit basis)
    hsn_code VARCHAR(20),
    gst_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    image_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_positive_pricing CHECK (mrp > 0 AND base_dealer_price > 0 AND case_pack > 0)
);

CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_brand ON products(brand_id);
```

---

### 2.6 `retailer_custom_prices`
Enables custom contract pricing for key retailers.

```sql
CREATE TABLE retailer_custom_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    retailer_id UUID NOT NULL REFERENCES retailers(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    custom_dealer_price NUMERIC(12, 2) NOT NULL,
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_retailer_product_validity UNIQUE (retailer_id, product_id, valid_from),
    CONSTRAINT chk_custom_price_positive CHECK (custom_dealer_price > 0)
);

CREATE INDEX idx_custom_prices_lookup ON retailer_custom_prices(retailer_id, product_id);
```

---

### 2.7 `inventory`
Warehouse stock levels with soft-reservation capability.

```sql
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    stock_cases INTEGER NOT NULL DEFAULT 0,
    stock_units INTEGER NOT NULL DEFAULT 0,
    reserved_cases INTEGER NOT NULL DEFAULT 0,
    min_threshold_cases INTEGER NOT NULL DEFAULT 10,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_stock_non_negative CHECK (stock_cases >= 0 AND reserved_cases >= 0)
);

CREATE INDEX idx_inventory_product ON inventory(product_id);
```

---

### 2.8 `product_aliases`
Colloquial Hindi/Hinglish vocabulary dictionary used for natural language AI matching.

```sql
CREATE TABLE product_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    alias_text VARCHAR(200) NOT NULL,          -- e.g., 'biscuit chhota', 'chhota parle', '5 rupay biscuit'
    normalized_alias VARCHAR(200) NOT NULL,   -- lowercase, trimmed, special chars removed
    language_code VARCHAR(10) NOT NULL DEFAULT 'hi-en',
    confidence_weight NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_product_alias UNIQUE (product_id, normalized_alias)
);

CREATE INDEX idx_aliases_normalized ON product_aliases(normalized_alias);
-- Trigram index for fuzzy search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_aliases_trgm ON product_aliases USING gin(normalized_alias gin_trgm_ops);
```

---

### 2.9 `schemes`
Trade promotional policies active in Company A.

```sql
CREATE TABLE schemes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,          -- e.g., 'SCHEME-BS-10P1', 'SCHEME-DT-5P3'
    name VARCHAR(200) NOT NULL,
    description TEXT,
    scheme_type VARCHAR(30) NOT NULL CHECK (scheme_type IN ('BUY_X_GET_Y_FREE', 'PERCENTAGE_DISCOUNT', 'FLAT_DISCOUNT')),
    min_qty_cases INTEGER NOT NULL DEFAULT 1,
    free_qty_cases INTEGER NOT NULL DEFAULT 0,
    discount_percentage NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_schemes_active ON schemes(is_active, valid_from, valid_to);
```

---

### 2.10 `scheme_products`
Associates schemes to qualifying and reward products.

```sql
CREATE TABLE scheme_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_id UUID NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    is_benefit_product BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE if this is the free item given
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_scheme_product UNIQUE (scheme_id, product_id, is_benefit_product)
);
```

---

### 2.11 `orders`
Transactional header for retail wholesale orders.

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) NOT NULL UNIQUE,  -- e.g., 'VS-2026-1049'
    retailer_id UUID NOT NULL REFERENCES retailers(id) ON DELETE RESTRICT,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_DESK_REVIEW' 
        CHECK (status IN ('PENDING_DESK_REVIEW', 'CREDIT_HOLD', 'APPROVED', 'DISPATCHED', 'EXPORTED_TALLY', 'REJECTED', 'CANCELLED')),
    idempotency_key VARCHAR(100) UNIQUE,
    raw_input_text TEXT,                       -- Stores original WhatsApp / Hinglish text
    input_source VARCHAR(30) NOT NULL DEFAULT 'MANUAL_CART'
        CHECK (input_source IN ('MANUAL_CART', 'AI_TEXT_PARSER', 'VOICE_TRANSCRIPTION', 'SALESMAN_ENTRY')),
    subtotal_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    is_credit_hold BOOLEAN NOT NULL DEFAULT FALSE,
    credit_hold_reason TEXT,
    desk_reviewed_by UUID REFERENCES users(id),
    desk_reviewed_at TIMESTAMPTZ,
    desk_notes TEXT,
    tally_exported_at TIMESTAMPTZ,
    tally_batch_id VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_retailer ON orders(retailer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at DESC);
```

---

### 2.12 `order_items`
Detailed line items for each order.

```sql
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    requested_cases INTEGER NOT NULL,
    approved_cases INTEGER NOT NULL,
    case_price NUMERIC(12, 2) NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL,
    applied_scheme_id UUID REFERENCES schemes(id),
    free_cases INTEGER NOT NULL DEFAULT 0,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    line_total NUMERIC(12, 2) NOT NULL,
    ai_confidence NUMERIC(3, 2),                -- e.g., 0.96 if parsed by AI
    match_source VARCHAR(30),                  -- 'ALIAS_EXACT', 'FUZZY_TOKEN_MATCH', 'MANUAL_SELECTION'
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_positive_quantities CHECK (requested_cases >= 0 AND approved_cases >= 0 AND free_cases >= 0)
);

CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
```

---

### 2.13 `audit_logs`
Immutable record of all state transitions and human interventions.

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name VARCHAR(50) NOT NULL,          -- e.g., 'orders', 'order_items', 'retailers'
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,               -- 'ORDER_APPROVED', 'CREDIT_HOLD_OVERRIDE', 'ITEM_QTY_MODIFIED'
    performed_by_user_id UUID REFERENCES users(id),
    old_values JSONB,
    new_values JSONB,
    reason TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_entity ON audit_logs(entity_name, entity_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
```

