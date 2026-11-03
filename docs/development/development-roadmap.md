# VyapaarSetu — 7-Day Phase-Wise Development Roadmap
**Version:** 1.0.0 (Phase 0 Planning)  
**Execution Standard:** Strictly incremental phases. After every phase: explain changes, list files, execute automated tests, report real test results, identify remaining issues, and suggest next phase.

---

## 1. Roadmap Overview & Timeline

```mermaid
flowchart LR
    P0["Day 0:<br/>Architecture & Planning"] --> P1["Day 1:<br/>Data Model & Seed DB"]
    P1 --> P2["Day 2:<br/>Auth & Master APIs"]
    P2 --> P3["Day 3:<br/>Schemes & Cart Engine"]
    P3 --> P4["Day 4:<br/>AI Order Parser & Matching"]
    P4 --> P5["Day 5:<br/>Retailer Mobile PWA"]
    P5 --> P6["Day 6:<br/>Order Desk & Tally Export"]
    P6 --> P7["Day 7:<br/>E2E Testing & Staging Deploy"]
```

---

## 2. Daily Phase Breakdown

### Day 0 (Current): Master Architecture & Product Planning
- **Focus:** System design, technical decisions, OpenAPI contracts, relational ERD, design system, screen specifications, assumptions register, and testing strategy.
- **Deliverables:** Complete planning documents under `docs/`, root docker-compose, and clean directory structure.
- **Verification:** Inspection of architectural documentation completeness and alignment with fixed technology choices.

---

### Day 1: Database Setup, Alembic Migrations & Business Seed Data
- **Focus:** PostgreSQL schema implementation using SQLAlchemy 2.0 and Alembic.
- **Key Tasks:**
  - Setup async SQLAlchemy session engine and base models.
  - Create declarative models for `users`, `retailers`, `brands`, `products`, `inventory`, `schemes`, `orders`, and `audit_logs`.
  - Generate and run Alembic baseline migration.
  - Implement seed data script importing Company A sample business data:
    - 4 Brands (Parle, Wheel, Tata Tea, etc.).
    - `SKU-BS-075` (Glucose Biscuit 75g, ₹8.10, 340 cases stock).
    - `SKU-DT-1KG` (Detergent Powder 1kg, ₹101.50, 85 cases stock).
    - `SKU-TE-250` (Tea Leaf 250g, ₹118.00, 0 cases stock).
    - Scheme A (Buy 10 biscuit cases get 1 free) & Scheme B (3% off >= 5 detergent cases).
    - Hindi colloquial aliases in `product_aliases`.
- **Exit Verification:** Pytest database connection test & seed verification passing against live PostgreSQL.

---

### Day 2: Authentication & Master Product Catalogue APIs
- **Focus:** Phone OTP authentication flow, staff JWT login, and retailer catalog endpoints.
- **Key Tasks:**
  - Implement JWT token generation, verification, and role-based dependencies.
  - Implement mock OTP service for development/testing (+919876543210 -> OTP 459012).
  - Build `GET /api/v1/retailer/products` with brand filters, search, custom pricing resolution, and real-time stock levels.
  - Build `GET /api/v1/retailer/schemes` active promotional rules endpoint.
- **Exit Verification:** Pytest integration tests for auth login, invalid OTP rejection, and role-scoped catalogue responses.

---

### Day 3: Deterministic Scheme Engine & Cart Validation
- **Focus:** Mathematical core for trade promotions and Decimal financial calculations.
- **Key Tasks:**
  - Implement isolated `SchemeCalculationService` using Python `Decimal`.
  - Encode Scheme A (Buy 10 Biscuit Cases -> 1 Free Case; e.g. 19 cases = 1 free, 20 cases = 2 free).
  - Encode Scheme B (Detergent Cases >= 5 -> 3% discount on detergent line total).
  - Implement `POST /api/v1/cart/calculate` endpoint returning gross amount, line item breakdown, applied schemes, and net payable.
  - Enforce stock threshold validations (rejecting items with 0 stock).
- **Exit Verification:** Comprehensive Pytest parameterized matrix covering 100% branch conditions of Scheme A and Scheme B.

---

### Day 4: AI Order Extraction & Deterministic SKU Matching Engine
- **Focus:** Natural language processing for Hinglish kirana orders.
- **Key Tasks:**
  - Implement OpenAI Structured Outputs extractor with strict Pydantic JSON schema.
  - Build server-side deterministic SKU matcher resolving extracted terms against:
    - Level 1: `product_aliases` exact match.
    - Level 2: Trigram similarity & token set ratio (`rapidfuzz`).
  - Calculate confidence scores and identify top 2 alternatives for ambiguous queries.
  - Handle out-of-stock flagging (e.g., `SKU-TE-250` flagged as out of stock).
  - Implement `POST /api/v1/ai/parse-order`.
- **Exit Verification:** Unit tests verifying sample message: *"bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti"* correctly extracts and matches all 3 items with expected confidence and out-of-stock warning.

---

### Day 5: Retailer Mobile PWA Implementation
- **Focus:** High-speed, responsive frontend for Kirana store owners.
- **Key Tasks:**
  - Setup Vite + React 18 + Tailwind CSS with design tokens (`#123B35`, `#187A65`, `#E8A33B`, `#F5F6F2`).
  - Build Phone OTP login screen (`SCR-RET-01`).
  - Build Catalogue & Scheme browsing screen with bottom navigation (`SCR-RET-02`).
  - Build AI Natural Language Order text capture & voice recorder UI (`SCR-RET-03`).
  - Build AI Candidate Review & Correction interface (`SCR-RET-04`).
  - Build Cart preview & Order confirmation flow (`SCR-RET-05` & `SCR-RET-06`).
  - Integrate `Idempotency-Key` header on order submission.
- **Exit Verification:** Vitest component tests and responsive viewport verification on mobile dimensions (360x640 to 414x896).

---

### Day 6: Order Desk Console & Tally CSV Export Engine
- **Focus:** Operations console for Company A staff in Jabalpur.
- **Key Tasks:**
  - Build Order Desk login and dashboard with segmented tabs (`SCR-DSK-01` & `SCR-DSK-02`).
  - Build split-screen order inspection and inline quantity adjustment panel (`SCR-DSK-03`).
  - Implement credit check rules and credit hold override with mandatory note logging.
  - Build Tally CSV export generator endpoint (`GET /api/v1/desk/orders/export/tally`) mapping orders to Tally Sales Voucher format.
  - Create Tally Export Console view (`SCR-DSK-04`).
- **Exit Verification:** Pytest verifying Tally CSV format against exact Tally import structure; Playwright test simulating desk operator reviewing and approving an order.

---

### Day 7: End-to-End Testing, Hardening & Staging Deployment
- **Focus:** Complete system integration, automated regression test runs, and cloud staging.
- **Key Tasks:**
  - Execute full Playwright E2E test suite: Retailer logs in -> pastes Hinglish order -> reviews matched SKUs -> places order -> Order Desk inspects order -> approves order -> exports Tally CSV.
  - Perform security audit: Verify retailer tenant isolation (cannot read other retailer's pricing or orders).
  - Configure production container builds (Backend Dockerfile, Frontend Dockerfile).
  - Deploy to Vercel (Frontend) and Render (Backend) with managed PostgreSQL.
- **Exit Verification:** Zero failing tests; documented test execution logs; live staging URLs verified.

