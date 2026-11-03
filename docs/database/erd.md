# VyapaarSetu — Entity Relationship Diagram (ERD)
**Version:** 1.0.0 (Phase 0 Planning)  
**Database Engine:** PostgreSQL 15+

---

## 1. Mermaid Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o| RETAILERS : "has profile (1:1)"
    USERS ||--o{ AUDIT_LOGS : "performs"
    USERS ||--o{ ORDERS : "desk reviews"
    
    BRANDS ||--o{ PRODUCTS : "produces"
    CATEGORIES ||--o{ PRODUCTS : "categorizes"
    CATEGORIES ||--o{ CATEGORIES : "parent category"
    
    PRODUCTS ||--|| INVENTORY : "tracks stock"
    PRODUCTS ||--o{ PRODUCT_ALIASES : "has colloquials"
    PRODUCTS ||--o{ RETAILER_CUSTOM_PRICES : "custom priced"
    RETAILERS ||--o{ RETAILER_CUSTOM_PRICES : "receives"
    
    SCHEMES ||--o{ SCHEME_PRODUCTS : "specifies rules"
    PRODUCTS ||--o{ SCHEME_PRODUCTS : "included in"
    
    RETAILERS ||--o{ ORDERS : "places"
    ORDERS ||--|{ ORDER_ITEMS : "contains"
    PRODUCTS ||--o{ ORDER_ITEMS : "ordered as"
    SCHEMES ||--o{ ORDER_ITEMS : "rewards"

    USERS {
        uuid id PK
        string phone UK
        string email UK
        string hashed_password
        string full_name
        string role
        boolean is_active
        timestamp created_at
    }

    RETAILERS {
        uuid id PK
        uuid user_id FK,UK
        string store_name
        string owner_name
        string gstin
        string city
        string route_beat
        numeric credit_limit
        numeric credit_used
        boolean is_credit_hold
        string price_tier
    }

    BRANDS {
        uuid id PK
        string code UK
        string name
        boolean is_active
    }

    CATEGORIES {
        uuid id PK
        uuid parent_id FK
        string name
        string slug UK
    }

    PRODUCTS {
        uuid id PK
        string sku UK
        uuid brand_id FK
        uuid category_id FK
        string name
        string hindi_name
        string unit
        integer case_pack
        numeric mrp
        numeric base_dealer_price
        boolean is_active
    }

    INVENTORY {
        uuid id PK
        uuid product_id FK,UK
        integer stock_cases
        integer reserved_cases
        integer min_threshold_cases
        timestamp updated_at
    }

    PRODUCT_ALIASES {
        uuid id PK
        uuid product_id FK
        string alias_text
        string normalized_alias
        string language_code
        numeric confidence_weight
    }

    RETAILER_CUSTOM_PRICES {
        uuid id PK
        uuid retailer_id FK
        uuid product_id FK
        numeric custom_dealer_price
        date valid_from
        date valid_to
    }

    SCHEMES {
        uuid id PK
        string code UK
        string name
        string scheme_type
        integer min_qty_cases
        integer free_qty_cases
        numeric discount_percentage
        boolean is_active
    }

    SCHEME_PRODUCTS {
        uuid id PK
        uuid scheme_id FK
        uuid product_id FK
        boolean is_benefit_product
    }

    ORDERS {
        uuid id PK
        string order_number UK
        uuid retailer_id FK
        string status
        string idempotency_key UK
        text raw_input_text
        string input_source
        numeric subtotal_amount
        numeric discount_amount
        numeric total_amount
        boolean is_credit_hold
        uuid desk_reviewed_by FK
        timestamp tally_exported_at
        timestamp created_at
    }

    ORDER_ITEMS {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        integer requested_cases
        integer approved_cases
        numeric case_price
        uuid applied_scheme_id FK
        integer free_cases
        numeric discount_amount
        numeric line_total
        numeric ai_confidence
        string match_source
    }

    AUDIT_LOGS {
        uuid id PK
        string entity_name
        uuid entity_id
        string action
        uuid performed_by_user_id FK
        jsonb old_values
        jsonb new_values
        string ip_address
        timestamp created_at
    }
```

---

## 2. Cardinality & Foreign Key Cascade Rules

1. **`users` -> `retailers` (1:1):**
   - Deleting a user cascade-deletes the retailer record (`ON DELETE CASCADE`).
2. **`brands` -> `products` (1:N):**
   - Deleting a brand is strictly prohibited if active products reference it (`ON DELETE RESTRICT`).
3. **`products` -> `inventory` (1:1):**
   - Inventory is an automatic child record of product creation (`ON DELETE CASCADE`).
4. **`orders` -> `order_items` (1:N):**
   - Cascade delete only allowed if an order is cancelled before desk review (`ON DELETE CASCADE`).
5. **`retailers` -> `orders` (1:N):**
   - Retailer records with existing orders cannot be deleted; they can only be marked inactive (`ON DELETE RESTRICT`).

