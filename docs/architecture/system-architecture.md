# VyapaarSetu — System Architecture Document
**Version:** 1.0.0 (Phase 0 Planning)  
**Author:** Principal Software Architect & Technical Lead  
**Client:** Company A, Jabalpur, Madhya Pradesh  

---

## 1. System Context & Overview

VyapaarSetu (व्यापार सेतु) is a B2B wholesale ordering platform connecting Company A (a distributor of 4 packaged food and home-care FMCG brands in Jabalpur, MP) with ~1,800 kirana retailers.

### Problem Context
The current ordering process relies heavily on unstructured communication channels:
- WhatsApp Hinglish messages (e.g., *"bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti"*).
- Hindi audio voice notes sent over WhatsApp.
- Handwritten order slips photographed and sent via smartphone cameras.
- Direct phone calls to sales reps and order desk clerks.

Manual re-keying into Tally ERP results in human errors, delayed dispatches, unapplied retailer schemes, and inventory misalignment.

### Architectural Solution
VyapaarSetu resolves this via an intelligent hybrid architecture:
1. **Edge-Delivered Mobile-First Web PWA (Retailer Portal):** Built with React 18, Vite, TypeScript, and Tailwind CSS.
2. **Deterministic High-Throughput REST API (Backend Core):** Built with Python 3.11, FastAPI, SQLAlchemy 2.0 (async), and Pydantic v2.
3. **Relational ACID Core (Database):** Hosted on managed PostgreSQL 15+ (strictly relational; no document stores).
4. **AI Parsing & Server-Side Deterministic SKU Matching:** OpenAI Structured Outputs API extracting candidate entities, routed through a server-side fuzzy & alias-matching engine with human-in-the-loop review.
5. **Operational Order Desk & ERP Gateway:** Role-based desk interface with credit-limit guardrails and deterministic Tally ERP CSV/XML export.

---

## 2. Mermaid System Architecture Diagram

```mermaid
flowchart TD
    subgraph Clients["Frontend Presentation Layer (Vercel)"]
        A["📱 Retailer Mobile PWA<br/>(React + Vite + Tailwind)"]
        B["💻 Order Desk Console<br/>(React + Vite + Desktop Layout)"]
    end

    subgraph Gateway["Edge & Routing Layer"]
        C["Cloudflare Edge CDN / SSL"]
    end

    subgraph Backend["Core Application Services (Render)"]
        D["FastAPI Application Server<br/>(Uvicorn ASGI async)"]
        
        subgraph Modules["Modular Internal Subsystems"]
            M1["Auth & RBAC Module<br/>(JWT + OTP Validator)"]
            M2["Catalogue & Pricing Engine<br/>(Retailer Tier & Custom Rates)"]
            M3["Scheme Engine<br/>(Deterministic Decimal Arithmetic)"]
            M4["AI Order Parser Engine<br/>(Structured Extraction + Alias Resolver)"]
            M5["Order Desk & Approval Engine<br/>(Credit Holds & Auditing)"]
            M6["Tally ERP Export Gateway<br/>(Sales Order CSV/XML Generator)"]
        end
    end

    subgraph AI["External Cognitive Services"]
        E["OpenAI API<br/>(Structured Outputs / json_schema)"]
    end

    subgraph Data["Persistence Layer"]
        F[("PostgreSQL 15+<br/>(Managed ACID Database)<br/>- Products & Inventory<br/>- Retailers & Custom Pricing<br/>- Schemes & Orders<br/>- Audit Logs")]
    end

    subgraph ERP["Distributor Local Infrastructure"]
        G["🏢 Company A Local Tally ERP<br/>(Jabalpur Head Office)"]
    end

    %% Client to Edge
    A -->|HTTPS / REST| C
    B -->|HTTPS / REST| C
    C -->|Reverse Proxy| D

    %% Backend internal connections
    D --> M1
    D --> M2
    D --> M3
    D --> M4
    D --> M5
    D --> M6

    %% External & Persistence integrations
    M4 <-->|"Extract Entities (JSON Schema)"| E
    M1 <-->|"Users / Sessions"| F
    M2 <-->|"Products / Stock / Prices"| F
    M3 <-->|"Schemes / Eligibility"| F
    M4 <-->|"Catalog Match / Aliases"| F
    M5 <-->|"Order State / Credit Limits"| F
    M6 <-->|"Export Final Orders"| F

    %% Export to Tally
    M6 -.->|"Download Tally CSV/XML"| B
    B -->|"Import Sales Vouchers"| G
```

---

## 3. End-to-End Core Data Flows

### Flow 1: AI Natural Language Order Capture to Confirmed Cart
```mermaid
sequenceDiagram
    autonumber
    actor Retailer as Retailer (Kirana Owner)
    participant UI as Retailer PWA (React)
    participant API as FastAPI Backend (/ai/parse-order)
    participant LLM as OpenAI (Structured Outputs)
    participant Matcher as Python SKU Matcher Service
    participant DB as PostgreSQL 15+

    Retailer->>UI: Types: "bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo"
    UI->>API: POST /api/v1/ai/parse-order (raw_text, retailer_id)
    API->>LLM: Prompt with JSON Schema (extract product_query, quantity, raw_unit)
    LLM-->>API: Structured JSON: [{query: "biscuit chhota", qty: 5, unit: "peti"}, ...]
    API->>Matcher: Resolve extracted queries against DB product aliases & catalog
    Matcher->>DB: Query exact aliases, trigram text matching (pg_trgm), active SKUs & stock
    DB-->>Matcher: SKU-BS-075 (Confidence: 0.96), SKU-DT-1KG (Confidence: 0.94)
    Matcher-->>API: Match results with primary SKU, confidence score, alternatives
    API-->>UI: Return reviewable items payload (no silent order placement)
    UI->>Retailer: Render AI Review Screen with editable quantities & SKU alternatives
    Retailer->>UI: Adjusts or confirms items -> "Add to Cart"
    UI->>API: POST /api/v1/cart/calculate (items, retailer_id)
    API-->>UI: Return priced cart with schemes applied (Free biscuit cases + 3% detergent discount)
```

### Flow 2: Order Review, Credit Hold, Approval, and Tally Export
```mermaid
sequenceDiagram
    autonumber
    actor Retailer as Retailer
    actor Desk as Order Desk Staff (Company A)
    participant UI as Order Desk Console
    participant API as FastAPI Backend
    participant Engine as Scheme & Credit Engine
    participant DB as PostgreSQL 15+
    participant Tally as Tally ERP (Company A)

    Retailer->>API: POST /api/v1/orders (Idempotency-Key)
    API->>Engine: Validate stock availability & Retailer Credit Status
    alt Credit Limit Exceeded
        Engine-->>API: Flag Order as Status: "CREDIT_HOLD"
    else Credit OK
        Engine-->>API: Flag Order as Status: "PENDING_DESK_REVIEW"
    end
    API->>DB: Persist order & order_items in single ACID transaction
    API-->>Retailer: Order confirmation message with Order # & status

    Desk->>UI: Open Desk Operations Dashboard
    UI->>API: GET /api/v1/desk/orders?status=PENDING_DESK_REVIEW,CREDIT_HOLD
    API-->>UI: List of incoming orders
    Desk->>UI: Inspect Order #VS-1049 (Raw input text vs parsed lines)
    alt Credit Hold Resolution
        Desk->>UI: Enter Credit Override Note & Click "Release Hold & Approve"
    else Standard Approval
        Desk->>UI: Click "Approve Order"
    end
    UI->>API: POST /api/v1/desk/orders/{id}/approve
    API->>DB: Update status to "APPROVED", record audit log, reserve hard inventory
    API-->>UI: 200 OK (Status Updated)
    Desk->>UI: Select Batch -> Click "Export to Tally CSV"
    UI->>API: GET /api/v1/desk/orders/export/tally?batch_id=...
    API-->>UI: Stream CSV formatted to Tally Sales Voucher spec
    Desk->>Tally: Import CSV into Company A Tally Company Data
```

---

## 4. Subsystem Component Breakdown

### 4.1 Frontend Presentation Layer (React 18 + Vite + Tailwind CSS)
- **Retailer Experience (Mobile First):** Optimized for low-end Android devices on 3G/4G cellular connections. Sticky bottom navigation, high contrast typography (Inter + Noto Sans Devanagari), 48px+ tap targets, local cart persistence, and single-click AI Hinglish ordering.
- **Order Desk Experience (Desktop First):** High-density tabular layout, keyboard shortcuts, split-screen raw text vs structured SKU verification, inline quantity adjustments, and batch Tally export actions.

### 4.2 Backend API Core (FastAPI + SQLAlchemy 2.0 Async)
- **Strict Role-Based Access Control (RBAC):** JWT tokens with claims differentiating `retailer`, `order_desk`, and `admin`. Retailer requests are strictly scoped to their own `retailer_id`.
- **Decimal Financial Engine:** All monetary values (dealer prices, line totals, discounts, taxes) use Python's `Decimal` type to prevent binary floating-point roundoff errors.
- **Idempotency Protection:** Order creation endpoints require a unique client-generated `Idempotency-Key` header, preventing duplicate order placement during poor network reconnects.

### 4.3 Database Persistence Layer (Managed PostgreSQL 15+)
- Strictly relational schema.
- Foreign key constraints, unique indexes, and check constraints enforce data integrity at the database engine level.
- `JSONB` audit trails preserve exact raw AI inputs and state transitions without losing schema structure.
- Trigram similarity indexing (`pg_trgm`) accelerates server-side SKU and alias lookups.

### 4.4 External Cognitive Services (OpenAI API)
- Utilizes OpenAI's **Structured Outputs** (`response_format: { type: "json_object" }` or Pydantic JSON schema mode).
- Extracts only entities: product name query, quantity number, and raw unit.
- **Strict Rule:** The LLM is never permitted to determine prices, calculate subtotals, or verify stock availability. These are executed deterministically by Python services.

---

## 5. Security & Isolation Architecture

1. **Retailer Data Isolation:** Every query on retailer-specific resources enforces a mandatory `WHERE retailer_id = :current_user_retailer_id` clause extracted directly from the verified JWT payload. No retailer can access another retailer's pricing, cart, or order history.
2. **Deterministic Fallbacks:** If the OpenAI API is unreachable or experiences rate limits, the frontend gracefully falls back to direct catalogue browsing and search without crashing the ordering pipeline.
3. **Audit Trail Logging:** All changes to order line items, quantity modifications by desk operators, credit hold overrides, and approvals are written immutably to the `audit_logs` table.
4. **Environment Isolation:** Zero credentials or API keys stored in source control. All configuration parameters are strictly validated via Pydantic `BaseSettings` reading from environment variables.

