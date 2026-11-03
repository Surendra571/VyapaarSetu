# VyapaarSetu — Architecture Decision Records (ADRs)
**Status:** Approved  
**Date:** 2026-11-03  

---

## ADR-001: Selection of PostgreSQL 15+ and SQLAlchemy 2.0 Async over MongoDB/NoSQL

### Context
Wholesale B2B distribution involves complex relational integrity: orders tie to order lines, which tie to products, inventory tiers, custom retailer price lists, and active promotional schemes. Inaccurate financial calculations or orphaned inventory reservations directly impact commercial revenue and partner trust.

### Decision
We standardize strictly on **PostgreSQL 15+** managed instance using **SQLAlchemy 2.0** with the `asyncpg` async driver and Alembic for declarative schema migrations. MongoDB or unstructured NoSQL document databases are explicitly prohibited for core application state.

### Consequences
- **Positive:**
  - True ACID transactions across multi-item order placement, credit checks, and inventory status updates.
  - Strict foreign key constraints and database-level `CHECK` constraints prevent negative quantities or invalid statuses.
  - Advanced relational features (`pg_trgm` for fuzzy Hindi/English alias matching, `JSONB` for raw AI telemetry, and window functions for analytics).
- **Negative:**
  - Requires explicit relational migration scripts (Alembic) for schema evolution.

---

## ADR-002: OpenAI Structured Outputs Paired with Server-Side Deterministic SKU Matching

### Context
Kirana retailers communicate orders informally in Hinglish and Hindi (e.g., *"bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo"*). Large Language Models (LLMs) can hallucinate plausible product names, invent prices, or miscalculate quantities if given open-ended generative prompts.

### Decision
We adopt a **two-stage hybrid AI pipeline**:
1. **Stage 1 (Cognitive Extraction):** OpenAI Structured Outputs (`response_format` with Pydantic JSON Schema) extracts *only* raw entity fragments: raw text query string, numerical quantity, and raw unit string. The LLM is strictly prohibited from returning SKUs, prices, totals, or stock statuses.
2. **Stage 2 (Deterministic Matcher):** A Python matching service resolves the extracted text query against the PostgreSQL database:
   - Level 1: Exact match on `product_aliases` (e.g., "biscuit chhota" -> `SKU-BS-075`).
   - Level 2: Trigram similarity and token sort ratio matching (`rapidfuzz` and `pg_trgm`).
   - Output: Top matched SKU with a confidence score (0.00 to 1.00) plus up to 2 alternative candidates.
3. **Stage 3 (Human-in-the-Loop):** Extracted items are presented to the user for review. No order is ever placed without retailer or desk confirmation.

### Consequences
- **Positive:**
  - Zero hallucinated products or inventory numbers.
  - Transparent confidence metrics visible to retailers and desk staff.
  - Continuous learning loop: whenever an operator corrects an AI match, the alias can be saved to `product_aliases`.
- **Negative:**
  - Unrecognized colloquial terms require initial alias seeding or manual retailer selection.

---

## ADR-003: Fixed-Point Arithmetic (Decimal / NUMERIC(12,2)) for Financials & Scheme Calculations

### Context
In B2B wholesale, line items are ordered in cases of dozens or hundreds of units. Floating point calculations (`float` in Python or `number` in JavaScript) suffer from binary IEEE-754 precision issues (e.g., `0.1 + 0.2 = 0.30000000000000004`), resulting in rounding discrepancies during invoicing and Tally ledger reconciliation.

### Decision
All financial prices, subtotals, discount deductions, tax calculations, and credits MUST use:
- Python: `decimal.Decimal` with explicit `ROUND_HALF_UP` rounding.
- PostgreSQL: `NUMERIC(12, 2)` columns.
- API Transports: Returned as decimal strings or two-decimal fixed numbers in Pydantic schemas.

### Consequences
- **Positive:**
  - 100% mathematical parity with Tally ERP ledger balances and invoice totals.
  - Clean audit trails without fractional cent drift.
- **Negative:**
  - Requires explicit serialization/deserialization between string and Decimal in API schemas.

---

## ADR-004: Dual-Path Authentication Architecture

### Context
The platform has two distinct user personas with vastly different digital literacy and access environments:
1. Kirana retailers accessing via budget mobile devices on mobile networks.
2. Order Desk operators accessing via desktop browsers inside Company A's office.

### Decision
Implement a single unified JWT token specification with dual login flows:
- **Retailer Flow:** Passwordless authentication using registered mobile phone number + 6-digit OTP (One Time Password). Short-lived session with rolling refresh tokens.
- **Order Desk / Admin Flow:** Email + strong password + bcrypt hashing, with session duration aligned with desktop working shifts.
- Both flows return standard JWT access tokens containing user claims (`sub`, `retailer_id`, `role`, `exp`).

### Consequences
- **Positive:**
  - Frictionless access for Kirana store owners who do not remember passwords.
  - Enterprise security hygiene for corporate staff handling invoices and credit overrides.
- **Negative:**
  - Requires maintaining an OTP delivery provider abstraction (with a deterministic development mock for testing).

---

## ADR-005: Decoupled Scheme Calculation Engine

### Context
Company A operates promotional schemes (e.g., Scheme A: *"Buy 10 cases of Glucose Biscuit, get 1 free case"*; Scheme B: *"3% discount on 5 or more cases of Detergent"*). These schemes change frequently based on manufacturer trade promotions. Hardcoding scheme logic inside cart controllers creates technical debt and makes unit testing difficult.

### Decision
Implement an isolated, pure-function `SchemeEngine` service:
- Accepts an immutable list of cart items and active scheme definitions.
- Evaluates eligibility rules deterministically.
- Returns an annotated `CalculationResult` containing line-level discounts, free item line additions, and an itemized breakdown.
- Operates identically on the retailer preview and the backend order finalization transaction.

### Consequences
- **Positive:**
  - High testability with 100% branch coverage via parameterized Pytest suites.
  - Transparent display of applied schemes to the retailer before checkout.
- **Negative:**
  - Scheme rules must be modeled cleanly in the relational schema.

---

## ADR-006: Distributed Idempotency Mechanism for Order Submissions

### Context
Retailers in Jabalpur often face spotty mobile network coverage. If a user taps "Confirm Order" and the connection drops before the HTTP response returns, the user may tap again, creating accidental duplicate wholesale orders worth thousands of rupees.

### Decision
Require an `Idempotency-Key` header (UUIDv4) on `POST /api/v1/orders`. The backend validates this key within a PostgreSQL transaction or temporary table. If an order with the same key was already received within the last 24 hours, the existing order record is returned without re-executing stock reservations or line creation.

### Consequences
- **Positive:**
  - Guaranteed zero duplicate orders from network retries or double clicks.
- **Negative:**
  - Client PWA must generate and retain an idempotency key per checkout attempt.

---

## ADR-007: Vercel Frontend + Render Backend + Managed PostgreSQL Deployment Topology

### Context
Company A requires high availability and minimal maintenance overhead without dedicating a full-time DevOps engineer to server infrastructure.

### Decision
- **Frontend:** Hosted on **Vercel** with automatic edge CDN caching, instant rollbacks, and fast static asset delivery.
- **Backend:** Containerized FastAPI service hosted on **Render** (or AWS ECS container) with automated health checks and horizontal autoscaling.
- **Database:** Managed **PostgreSQL** instance with automated daily snapshots, connection pooling (PgBouncer), and continuous WAL archiving.

### Consequences
- **Positive:**
  - Zero server patching overhead.
  - Separation of static asset delivery from compute-intensive backend requests.
  - Production parity easily reproducible locally via `docker-compose`.

