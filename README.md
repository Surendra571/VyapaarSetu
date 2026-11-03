# VyapaarSetu (व्यापार सेतु)
> **Connecting retailers and distributors intelligently.**

[![Architecture](https://img.shields.io/badge/Architecture-Phase%200%20Complete-123B35.svg)](#)
[![Stack](https://img.shields.io/badge/Backend-FastAPI%20%7C%20SQLAlchemy%202%20%7C%20PostgreSQL-187A65.svg)](#)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%7C%20TypeScript%20%7C%20Vite%20%7C%20Tailwind-E8A33B.svg)](#)

---

## 1. Project Overview

**VyapaarSetu** is a B2B wholesale ordering platform built specifically for Indian FMCG & packaged goods distribution. Designed for **Company A** in Jabalpur, Madhya Pradesh, it modernizes operations for a distributor serving ~1,800 kirana retailers across four primary packaged food and home-care brands.

### Problem Statement
Currently, kirana retailers submit daily replenishment orders via informal WhatsApp text messages, voice notes in Hindi, handwritten notebook photos, and phone calls. Order desk operators manually decode these messages, verify prices, check paper scheme charts, and re-key them into Tally ERP. This creates significant delays, order inaccuracies, missed scheme benefits, and inventory stockout miscommunications.

### Solution
VyapaarSetu provides:
1. **Mobile-First Retailer Portal:** Personalized product catalogue, real-time stock levels, live scheme calculation, and single-tap reordering.
2. **AI Order Capture Engine:** Natural language understanding for Hinglish and colloquial Hindi Kirana terminology (e.g., *"bhaiya 5 peti biscuit chhota"*), mapping unstructured messages directly to catalog SKUs with confidence metrics.
3. **Deterministic Order Desk:** An operations console allowing human-in-the-loop review, automated credit limit checks, and one-click Tally ERP-compatible CSV/XML exports.

---

## 2. Technology Stack

| Layer | Technologies | Selection Rationale |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide React, shadcn/ui primitives | Mobile-first responsiveness, ultra-fast bundle delivery, strict type safety, predictable design token styling. |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic | Async high-concurrency throughput, robust SQL ORM transactions, strict data validation. |
| **Database** | PostgreSQL 15+ ONLY (Strictly relational) | ACID compliance, financial decimal integrity, JSONB support for raw AI payloads, full text and fuzzy indexing. |
| **AI / NLP** | OpenAI Structured Outputs API + Server-side Deterministic Matcher | Strict JSON schema extraction paired with deterministic Python catalog validation to prevent hallucinated SKUs. |
| **Deployment** | Vercel (Frontend), Render (Backend), Managed PostgreSQL (Neon / Supabase) | Global edge caching, serverless zero-config frontend, managed containerized backend with autoscaling. |

---

## 3. Directory Structure

```text
VyapaarSetu/
├── backend/
│   ├── api/                 # API routes versioned under v1
│   │   └── v1/
│   │       ├── auth.py      # Phone OTP & staff authentication
│   │       ├── products.py  # Catalogue & custom price resolution
│   │       ├── cart.py      # Cart validation & scheme engine
│   │       ├── ai.py        # Natural language order parsing & SKU matching
│   │       ├── orders.py    # Order placement & history
│   │       └── desk.py      # Operations desk, approval & Tally export
│   ├── core/                # Application configuration, settings & logging
│   ├── db/                  # Database session, base model & engine setup
│   ├── models/              # SQLAlchemy 2.0 ORM models
│   ├── schemas/             # Pydantic v2 validation models
│   ├── security/            # JWT authentication, password hashing & RBAC
│   ├── services/            # Pure business logic (Schemes, AI parser, Tally export)
│   ├── tests/               # Backend unit and integration test suite
│   ├── .env.example         # Backend environment variables template
│   ├── alembic.ini          # Database migration tool configuration
│   ├── Dockerfile           # Backend production container specification
│   └── requirements.txt     # Python production and test dependencies
├── frontend/
│   ├── public/              # Static public assets (brand icons, manifest)
│   ├── src/
│   │   ├── components/      # Reusable UI components & shadcn primitives
│   │   ├── pages/           # Retailer and Order Desk route views
│   │   ├── services/        # Axios/Fetch API client wrappers
│   │   ├── types/           # TypeScript interfaces and API response contracts
│   │   ├── hooks/           # Custom React hooks (cart, auth, media query)
│   │   ├── App.tsx          # Root routing and application state providers
│   │   ├── main.tsx         # Application entry point
│   │   └── index.css        # Tailwind styles and CSS variables
│   ├── tests/               # Frontend component and Playwright E2E tests
│   ├── .env.example         # Frontend environment variables template
│   ├── package.json         # Node scripts and dependencies
│   ├── tsconfig.json        # TypeScript configuration
│   ├── vite.config.ts       # Vite bundler configuration
│   └── tailwind.config.js   # Tailwind design tokens and theme settings
├── docs/
│   ├── architecture/        # System architecture, ADRs & API specifications
│   ├── database/            # Relational schema specification & Mermaid ERD
│   ├── design/              # Design tokens, typography & screen specifications
│   ├── development/         # 7-day development roadmap & phase plan
│   ├── testing/             # Testing strategy, test matrix & verification rules
│   ├── progress/            # Phase-wise completion reports
│   └── assumptions.md       # Documented domain and business assumptions
├── docker-compose.yml       # Local development multi-container orchestration
├── .gitignore               # Unified git ignore rules
└── README.md                # Project README and master guide
```

---

## 4. Quick Start (Development)

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (LTS) & npm
- Python 3.11+

### Running with Docker Compose
```bash
# 1. Clone the repository
git clone <repo-url>
cd VyapaarSetu

# 2. Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Start PostgreSQL, Backend, and Frontend containers
docker-compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API Docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

---

## 5. Phase 0 Deliverables & Documentation Index

All master planning deliverables are accessible under [`docs/`](file:///d:/BACKEND-2026/VyapaarSetu/docs):

1. **System Architecture:** [`docs/architecture/system-architecture.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/architecture/system-architecture.md)
2. **Technical Decision Records:** [`docs/architecture/technical-decisions.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/architecture/technical-decisions.md)
3. **API Specification:** [`docs/architecture/api-specification.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/architecture/api-specification.md)
4. **Database Schema:** [`docs/database/database-schema.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/database/database-schema.md)
5. **Entity Relationship Diagram (ERD):** [`docs/database/erd.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/database/erd.md)
6. **Design System & Tokens:** [`docs/design/design-system.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/design/design-system.md)
7. **Screen Specifications:** [`docs/design/screen-specifications.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/design/screen-specifications.md)
8. **Assumptions Register:** [`docs/assumptions.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/assumptions.md)
9. **Development Roadmap:** [`docs/development/development-roadmap.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/development/development-roadmap.md)
10. **Testing Strategy:** [`docs/testing/test-strategy.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/testing/test-strategy.md)
11. **Phase 0 Progress Report:** [`docs/progress/phase-0-report.md`](file:///d:/BACKEND-2026/VyapaarSetu/docs/progress/phase-0-report.md)

---

## 6. Development Workflow Rules
- **Phase-Wise Execution:** Code is implemented in strict incremental phases with real test execution and verification.
- **Zero Mock Claiming:** No test or feature is marked complete unless verified against live automated test runs.
- **Financial Precision:** Floating-point arithmetic is strictly prohibited; all prices and calculations use Python `Decimal` and PostgreSQL `NUMERIC(12,2)`.
- **Relational Integrity:** PostgreSQL is the single source of truth. MongoDB or unindexed document stores are strictly prohibited.

