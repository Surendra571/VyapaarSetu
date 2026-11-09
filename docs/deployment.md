# VyapaarSetu — Production Deployment & Reviewer Guide

> **Project Name:** VyapaarSetu  
> **Repository:** https://github.com/Surendra571/VyapaarSetu  
> **Live Frontend Deployment:** https://vyapaar-setu-ashen.vercel.app  
> **Live Backend API:** https://vyapaarsetu-2.onrender.com  
> **Backend Health Endpoint:** https://vyapaarsetu-2.onrender.com/api/v1/health  
> **Interactive Swagger Docs:** https://vyapaarsetu-2.onrender.com/docs  
> **ReDoc Alternative:** https://vyapaarsetu-2.onrender.com/redoc  
> **Date:** November 2026  
> **Version:** 1.0.0 (Production-Verified MVP)

---

## 1. Project Overview

**VyapaarSetu** ("Bridge of Commerce") is a production-grade, AI-powered B2B commerce platform engineered specifically for FMCG wholesale distribution in Jabalpur, Madhya Pradesh, India. It digitizes the high-friction, error-prone ordering workflows between FMCG distributors and neighborhood kirana retail merchants.

Historically, kirana shopkeepers placed replenishment orders through informal WhatsApp voice notes, handwritten paper chits, or fragmented text messages in Hindi and Hinglish. These channels led to severe transcription errors, delayed fulfillment, manual pricing blunders across complex trade schemes, and tedious manual re-entry into accounting software like Tally.

VyapaarSetu bridges this operational gap by combining:
- A responsive, mobile-first **React 18 + TypeScript + Vite** Single Page Application (SPA) with Progressive Web App (PWA) offline queueing.
- A high-concurrency **FastAPI (Python 3.12)** asynchronous backend powered by SQLAlchemy 2.0 with PostgreSQL row-level locks (`SELECT ... FOR UPDATE`).
- A multi-tier **AI Order Capture Engine** (Google Gemini 1.5 Flash + OpenAI GPT-4o fallback + deterministic local regex/heuristic parser) that extracts informal Hindi/Hinglish trade vernacular (e.g., *"5 peti biscuit chhota"*, *"2 peti washing powder 1 kilo"*), matches items to catalog SKUs with confidence scoring, and resolves ambiguous units.
- An automated **Multi-Benefit Trade Promotion Scheme Engine** supporting volume discounts, slab pricing, and free goodsline items snapshot at ₹0.00.
- An **Order Desk Console** with real-time credit limit enforcement, concurrency-safe dispatch approvals, van loading manifest generation, and formula-injection-safe **Tally Prime CSV export**.

### Technology Stack Summary
| Tier | Technology | Version | Purpose |
|---|---|---|---|
| **Frontend Framework** | React | `^18.2.0` | Declarative, component-based user interface |
| **Language & Build** | TypeScript / Vite | `^5.2.2` / `^5.1.6` | Strict type safety and optimized SPA production bundling |
| **Styling & Icons** | Tailwind CSS / Lucide React | `^3.4.1` / `^0.359.0` | Kirana wholesale green design system, responsive mobile layout |
| **Backend Framework** | FastAPI | `>=0.115.0` | Asynchronous high-performance ASGI REST API |
| **Runtime** | Python | `3.12` | Core backend execution runtime |
| **ORM & Database Driver** | SQLAlchemy / asyncpg | `>=2.0.36` / `>=0.30.0` | Non-blocking asynchronous PostgreSQL ORM with connection pooling |
| **Database Engine** | PostgreSQL (Neon Serverless) | `16 / 17` | Relational persistence, UUID keys, row-level locks, ACID compliance |
| **Schema Migrations** | Alembic | `>=1.14.0` | Version-controlled, deterministic database migrations |
| **AI Extraction Providers** | Google Gemini / OpenAI | `gemini-1.5-flash` / `gpt-4o` | Multimodal unstructured text/audio/image parsing |
| **Frontend Hosting** | Vercel Edge Network | Cloud CDN | Global static CDN distribution and SPA routing rewrites |
| **Backend Hosting** | Render Web Services | Cloud PaaS | Managed containerized ASGI process with automatic SSL |

---

## 2. Prerequisites

Before installing and running VyapaarSetu locally, verify that your environment meets the following software requirements:

- **Git:** Version 2.38+ installed.
- **Node.js:** Version 18.x or 20.x LTS installed (`node -v`).
- **npm:** Version 9.x or 10.x installed (`npm -v`).
- **Python:** Version 3.12.x (or 3.11.x) 64-bit installed (`python --version`).
- **pip:** Latest Python package manager (`python -m pip install --upgrade pip`).
- **PostgreSQL:** Local PostgreSQL 16/17 server running, or cloud access to a Neon Serverless PostgreSQL instance with an SSL connection string.

---

## 3. Clone the Repository

Clone the official VyapaarSetu Git repository to your local development machine:

```bash
git clone https://github.com/Surendra571/VyapaarSetu.git
cd VyapaarSetu
```

Confirm that the project contains the `backend` and `frontend` subdirectories.

---

## 4. Backend Setup

### Step 4.1: Create a Python Virtual Environment
Navigate into the `backend` directory and create an isolated virtual environment:

```bash
cd backend
python -m venv .venv
```

### Step 4.2: Activate the Virtual Environment
Activate the environment according to your operating system:

- **Windows PowerShell:**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows Command Prompt (cmd):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### Step 4.3: Install Backend Dependencies
Install all required production and testing packages using `pip`:

```bash
pip install -r requirements.txt
```

### Step 4.4: Configure Backend Environment Variables
Create a local `.env` configuration file in the `backend/` directory by copying the supplied `.env.example`:

```bash
# On Linux / macOS / Git Bash:
cp .env.example .env

# On Windows PowerShell:
Copy-Item .env.example .env
```

Edit `.env` to specify your database connection and secrets. At minimum, configure:
- `DATABASE_URL`: Asynchronous PostgreSQL URI (`postgresql+asyncpg://<user>:<password>@<host>:<port>/<dbname>`).
- `SECRET_KEY`: A secure 64-character random string for signing JWT tokens.
- `CORS_ORIGINS`: Comma-separated allowed frontend origins (e.g. `http://localhost:5173,http://127.0.0.1:5173`).
- `AI_PROVIDER`: Set to `auto`, `gemini`, or `openai`. If API keys are omitted, the system seamlessly uses the verified local regex/heuristic fallback parser.

### Step 4.5: Run Database Migrations
Apply the latest Alembic schema migrations to synchronize the database tables to head revision (`d93a11c7f5a1`):

```bash
alembic upgrade head
```

### Step 4.6: Seed Synthetic Demo Master Data
Populate the database with verified master FMCG products, active schemes, synthetic retailer accounts, custom prices, and SKU aliases:

```bash
python -m app.seeds.demo_data
```

### Step 4.7: Start the FastAPI Server
Launch the ASGI development server with hot-reload enabled:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend server is now running at `http://localhost:8000`.

### Step 4.8: Access API Documentation
Open your web browser and navigate to:
- **Interactive Swagger UI:** `http://localhost:8000/docs`
- **ReDoc API Reference:** `http://localhost:8000/redoc`
- **Health Check Endpoint:** `http://localhost:8000/api/v1/health`

---

## 5. Frontend Setup

### Step 5.1: Install Node Dependencies
Open a new terminal window, navigate to the `frontend` directory, and install dependencies:

```bash
cd frontend
npm install
```

### Step 5.2: Configure Frontend Environment Variables
Create a `.env` file inside the `frontend/` directory:

```bash
# On Windows PowerShell:
New-Item -ItemType File -Name .env -Value "VITE_API_BASE_URL=http://localhost:8000/api/v1`nVITE_APP_TITLE=VyapaarSetu"

# On macOS / Linux:
cat <<EOF > .env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_TITLE=VyapaarSetu
EOF
```

> **Note:** To test against the live cloud backend instead of your local server, set:  
> `VITE_API_BASE_URL=https://vyapaarsetu-2.onrender.com/api/v1`

### Step 5.3: Run the Vite Development Server
Start the frontend development server:

```bash
npm run dev
```

The Vite dev server will start at `http://localhost:5173`. Open this URL in your web browser.

### Step 5.4: Execute Frontend Production Verification
Validate TypeScript types and build the production bundle:

```bash
npm run build
```

This executes `tsc && vite build`, creating optimized assets in `frontend/dist/` with 0 compilation errors.

---

## 6. Environment Variables

The table below documents every configurable environment variable in the VyapaarSetu application. **Never commit actual secret values, passwords, or private keys to source control.**

| Variable Name | Component | Purpose | Required | Default / Example Setting |
|---|---|---|:---:|---|
| `DATABASE_URL` | Backend | Asynchronous PostgreSQL connection string with `asyncpg` driver prefix | **Yes** | `postgresql+asyncpg://postgres:secret@127.0.0.1:5432/vyapaarsetu_db` |
| `SECRET_KEY` | Backend | Cryptographic secret key used to sign and verify HMAC-SHA256 JWT tokens | **Yes** | 64-char hex string (generate with `openssl rand -hex 32`) |
| `CORS_ORIGINS` | Backend | Comma-separated list of allowed cross-origin web origins | **Yes** | `http://localhost:5173,https://vyapaar-setu-ashen.vercel.app` |
| `ENVIRONMENT` | Backend | Environment flag (`development` or `production`) | No | `development` |
| `DEBUG` | Backend | Enables verbose traceback output and development logging | No | `True` in local, `False` in production |
| `APP_NAME` | Backend | Application title used in health check and metadata | No | `VyapaarSetu` |
| `APP_HOST` | Backend | Host IP binding for ASGI server | No | `0.0.0.0` |
| `APP_PORT` | Backend | Port binding for ASGI server | No | `8000` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | Lifetime of authenticated JWT Bearer tokens | No | `1440` (24 hours) |
| `ALGORITHM` | Backend | JWT digital signing algorithm | No | `HS256` |
| `AI_PROVIDER` | Backend | AI processing provider (`auto`, `gemini`, or `openai`) | No | `auto` |
| `GEMINI_API_KEY` | Backend | Google Gemini API key for structured multimodal extraction | Optional | Empty / User API Key (uses regex fallback if absent) |
| `GEMINI_MODEL` | Backend | Google Gemini LLM model identifier | No | `gemini-1.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Backend | HTTP timeout for Gemini API calls before fallback | No | `20` |
| `OPENAI_API_KEY` | Backend | OpenAI API key for secondary LLM structured extraction | Optional | Empty / User API Key (uses regex fallback if absent) |
| `OPENAI_MODEL` | Backend | OpenAI LLM model identifier | No | `gpt-4o` |
| `OPENAI_TIMEOUT_SECONDS` | Backend | HTTP timeout for OpenAI API calls before fallback | No | `15` |
| `ALLOW_SCHEME_STACKING` | Backend | Whether multiple promotional trade schemes can stack on the same line | No | `False` |
| `SCHEME_STACKING_POLICY` | Backend | Conflict governance (`FLAG_CONFLICT_FOR_REVIEW`, `BEST_VALUE`) | No | `FLAG_CONFLICT_FOR_REVIEW` |
| `STRICT_CREDIT_HOLD` | Backend | Whether exceeding available credit automatically locks orders to `CREDIT_HOLD` | No | `True` |
| `INSUFFICIENT_STOCK_POLICY` | Backend | Behavior when requested stock is unavailable (`REJECT_ORDER` vs partial) | No | `REJECT_ORDER` |
| `VITE_API_BASE_URL` | Frontend | Base URL of the FastAPI REST API `/api/v1` router | **Yes** | `http://localhost:8000/api/v1` or `https://vyapaarsetu-2.onrender.com/api/v1` |
| `VITE_APP_TITLE` | Frontend | HTML document title displayed in browser tab | No | `VyapaarSetu` |

---

## 7. Database Setup

### Step 7.1: PostgreSQL Connection Formatting
VyapaarSetu's backend uses SQLAlchemy 2.0 with the asynchronous `asyncpg` engine.

- **For local PostgreSQL:**
  ```ini
  DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/vyapaarsetu_db
  ```
- **For Neon Serverless PostgreSQL / Cloud Hosted Services:**
  Neon enforces TLS/SSL. Ensure the URL ends with `?ssl=require` (or `?sslmode=require` which `config.py` automatically normalizes to `ssl=require`):
  ```ini
  DATABASE_URL=postgresql+asyncpg://[username]:[password]@[neon-hostname]/neondb?ssl=require
  ```

### Step 7.2: Database Migration Commands
The database schema is fully versioned using Alembic in `backend/alembic/`.

- **Apply all migrations:**
  ```bash
  alembic upgrade head
  ```
- **Check current revision:**
  ```bash
  alembic current
  ```
  *Expected current head:* `d93a11c7f5a1 (head)`
- **Roll back the latest migration (if ever needed):**
  ```bash
  alembic downgrade -1
  ```

### Step 7.3: Database Seed Scripts
- **Seed Master FMCG Data:**  
  Executes `backend/app/seeds/demo_data.py`. Creates 3 core products, 3 synthetic retailers, 2 trade schemes, inventory ledgers, custom prices, and regional trade aliases:
  ```bash
  python -m app.seeds.demo_data
  ```
- **Clear Orders (Reset Queue):**  
  Executes `backend/app/seeds/clear_orders.py`. Safely purges active orders and resets inventory reservations without modifying products or retailers:
  ```bash
  python -m app.seeds.clear_orders
  ```

---

## 8. Deployment Architecture

VyapaarSetu is live in production across a cloud-native, decoupled multi-cloud architecture:

```
[ Retailers / PWA Mobile ]    [ Order Desk Operators / Desktop ]
            │                                 │
            └───────────────┬─────────────────┘
                            │ (HTTPS)
                            ▼
              [ Vercel Global Edge CDN ]
              - Single Page Application (SPA)
              - Assets: HTML, JS bundles, CSS, sw.js
              - Client-Side Routing via vercel.json
                            │
                            │ (Direct HTTPS REST Calls with Bearer JWT)
                            ▼
           [ Render Web Service (Python 3.12) ]
              - FastAPI ASGI Application (uvicorn)
              - Scheme Engine, Concurrency Locking
              - AI Extraction & Heuristic Fallback
                            │
              ┌─────────────┴─────────────┐
              │ (asyncpg SSL)             │ (REST / HTTPS)
              ▼                           ▼
  [ Neon PostgreSQL 16 ]     [ Google Gemini / OpenAI ]
  - Serverless PostgreSQL     - Structured WhatsApp parsing
  - Row-Level Locks           - Fallback to local regex
  - PgBouncer Pooler
```

### Frontend: Vercel
- **Production URL:** `https://vyapaar-setu-ashen.vercel.app`
- **Framework Preset:** Vite
- **Root Directory:** `frontend`
- **Build Command:** `npm run build` (`tsc && vite build`)
- **Output Directory:** `dist`
- **Environment Variable:** `VITE_API_BASE_URL=https://vyapaarsetu-2.onrender.com/api/v1`
- **SPA Rewrites (`vercel.json`):**
  ```json
  {
    "rewrites": [
      {
        "source": "/(.*)",
        "destination": "/index.html"
      }
    ]
  }
  ```

### Backend: Render
- **Production URL:** `https://vyapaarsetu-2.onrender.com`
- **Health Check Path:** `/api/v1/health`
- **Runtime:** Python 3 (Python 3.12)
- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Database Connection:** Connected to Neon AWS US-East-2 instance with SSL.

> [!NOTE]
> **Render Free Tier Cold-Start Disclosure:**  
> When the backend is hosted on Render's free tier, the container enters sleep mode after 15 minutes of inactivity. The initial request to `https://vyapaarsetu-2.onrender.com/api/v1/health` may require **30 to 45 seconds** to spin up. All subsequent requests respond with sub-second latency.

---

## 9. Demo Login Credentials

The live deployment incorporates a synthetic **Mock OTP Authentication Mode** designed to allow reviewers and evaluators to test all role-based experiences immediately without requiring real SMS delivery.

### Verified Demo Accounts
| Role | User Name & Kirana Store | Phone Number | Demo OTP | Default Landing Page | Credit Limit & Profile |
|---|---|---|:---:|---|---|
| **Retailer (Gold Tier)** | Ramesh Patel<br>*(Patel Kirana & General Stores)* | `9826011111` | `123456` | `/catalogue` | Limit: ₹50,000.00<br>Available: ₹31,600.00<br>Custom price: Parle-G @ ₹7.90 |
| **Retailer (Silver Tier)** | Mohan Lal Agrawal<br>*(Agrawal Provision Store)* | `9826022222` | `123456` | `/catalogue` | Limit: ₹100,000.00<br>Available: ₹7,500.00<br>Low available credit for hold testing |
| **Retailer (Locked)** | Sunil Jain<br>*(Mahaveer Daily Needs)* | `9826033333` | `123456` | `/catalogue` | Limit: ₹25,000.00<br>Available: ₹0.00<br>Strict credit hold flag active |
| **Order Desk Supervisor**| Sanjay Sharma<br>*(FMCG Wholesale Desk)* | `9826000000` | `123456` | `/desk` | Full desk access: Approve/reject, Van manifest, Inactivity, Tally export |

### How to Sign In
1. Open `https://vyapaar-setu-ashen.vercel.app/login` in your web browser.
2. Click one of the **Quick Demo Switcher** pills (**"Retailer Demo (9826011111)"** or **"Order Desk Demo (9826000000)"**), or manually enter the phone number.
3. Click **"Send Verification OTP"**.
4. In the OTP field, enter the verified evaluation code: `123456`.
5. Click **"Verify & Enter Portal"**. The system validates the token and redirects to the role-specific dashboard.

---

## 10. How to Test the Application (Reviewer Walkthrough)

Follow this 9-step test protocol to evaluate the complete end-to-end functionality:

### Step 1: Open the Live Application
Navigate to [https://vyapaar-setu-ashen.vercel.app](https://vyapaar-setu-ashen.vercel.app). Ensure the green VyapaarSetu navigation bar renders cleanly with zero console errors.

### Step 2: Sign In as Kirana Retailer
Sign in with phone number `9826011111` and OTP `123456`. Verify that the top navigation header displays **"Patel Kirana & General Stores"** with available credit ₹31,600.00.

### Step 3: Browse the Product Catalogue
On the `/catalogue` screen, review the 3 FMCG items:
- **Glucose Biscuit 75g (Parle-G):** Notice the contracted dealer rate of ₹7.90/case (discounted for Ramesh Patel from the base ₹8.10/case).
- **Detergent Powder 1kg (Surf Excel):** Contracted dealer rate ₹99.00/case.
- **Tea Leaf 250g (Tata Tea):** Notice the **"Out of Stock"** status badge (0 cases available).

### Step 4: Create a Cart Order & Review Trade Schemes
1. On the Parle-G Biscuit card, enter **10 cases** and click **Add to Cart**.
2. Navigate to `/cart`.
3. Verify that the **Scheme Engine** automatically calculates the promotion:
   - Primary item: 10 cases of Glucose Biscuit 75g = ₹79.00 (Excl. GST).
   - Bonus line: **1 free case of Glucose Biscuit 75g** displayed as a distinct free goods line item with rate **₹0.00**.
4. Verify credit exposure: Order total ₹79.00 is well within available credit ₹31,600.00.
5. Click **"Place Order"**. The order enters `PENDING_DESK_APPROVAL` status with a unique order number (e.g. `ORD-202611...`).

### Step 5: Test AI Order Capture & Dialect Extraction
1. Click **"AI order capture"** in the navigation bar (`/ai`).
2. Paste the following informal Hindi/Hinglish trade message into the text box:
   ```text
   bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo
   ```
3. Click **"Parse Order with AI"**.
4. Observe the structured extraction:
   - Line 1: *"5 peti biscuit chhota"* $\rightarrow$ Extracted: 5 cases, matched to `SKU-BS-075` with high confidence (0.92).
   - Line 2: *"2 peti washing powder 1 kilo"* $\rightarrow$ Extracted: 2 cases, matched to `SKU-DT-1KG` with high confidence (0.92).
5. Notice that if an ambiguous item is entered (e.g., *"biscuit 5"* without specifying whether peti or packet), the system sets `unit_clarification_needed = true` and prompts the user to select between Case or Piece before confirming.
6. Click **"Add Confirmed Items to Cart"** to seamlessly transfer parsed items to checkout.

### Step 6: Log Out & Sign In as Order Desk Supervisor
1. Click **"Account"** $\rightarrow$ **"Sign Out"**.
2. Sign in with phone number `9826000000` and OTP `123456`.
3. The dashboard routes directly to the **Order Desk** console (`/desk`).

### Step 7: Order Desk Workflow & Quantity Adjustment
1. Locate the pending order submitted in Step 4.
2. Click **"Review Order"**.
3. Inspect the line items, credit health, and applied scheme rules.
4. Test quantity adjustment: Change the ordered quantity from 10 to 12 cases.
5. Observe that the Scheme Engine recalculates in real time (free goods remains 1 case; subtotal updates to ₹94.80).
6. Click **"Approve Order"**. The backend acquires an exclusive row-level lock (`SELECT ... FOR UPDATE`), deducts inventory atomically, and transitions the order status to `APPROVED`.

### Step 8: Inspect Van Loading Manifest
1. Navigate to `/van` in the navigation header.
2. Inspect the aggregate delivery loading list.
3. Verify that approved quantities are grouped by SKU and store destination, keeping purchased stock cleanly separated from free promotional goods for the van driver.

### Step 9: Test Tally Prime CSV Export
1. Navigate to `/exports` (`/tally`).
2. Select the approved orders and click **"Generate Tally Export Batch"**.
3. Click **"Download CSV"**.
4. Open the downloaded CSV file in Excel, Notepad, or VS Code:
   - Verify the required Tally columns: `Voucher Number`, `Voucher Date`, `Party Name`, `Party Code`, `Item SKU`, `Item Name`, `Billed Qty (Cases)`, `Free Qty (Cases)`, `Rate Per Unit (Excl. GST)`, `Line Amount (Excl. GST)`.
   - Verify formula injection defense: Any field starting with `=`, `+`, `-`, or `@` has been prepended with a single quote (`'`).

---

## 11. Troubleshooting

| Symptom | Probable Cause | Verified Resolution |
|---|---|---|
| **Render API responds with 502 / timeout on first request** | Render free tier instance sleep mode | Wait 30–45 seconds for container cold-start wake-up. Subsequent calls respond in sub-second time. |
| **CORS Preflight Error in browser console** | Frontend origin missing from `CORS_ORIGINS` | In Render environment settings, add your frontend origin to `CORS_ORIGINS` (e.g., `https://vyapaar-setu-ashen.vercel.app`). Do not use wildcard `*` with credentials. |
| **`asyncpg.exceptions.InvalidAuthorizationSpecificationError`** | Neon PostgreSQL requires SSL encryption | Verify that `DATABASE_URL` contains `?ssl=require` rather than standard unencrypted PostgreSQL parameters. |
| **`sqlalchemy.exc.MissingGreenlet` during database operations** | Asynchronous ORM boundary violation | Ensure all relationship loading uses eager loading options (`selectinload()`) rather than lazy query attributes. |
| **AI Order Capture returns fallback parser message** | Missing or rate-limited external AI API key | This is by design: VyapaarSetu automatically activates its deterministic local regex/heuristic parser when Gemini/OpenAI are unavailable. No disruption occurs. |
| **Login rejected with "Invalid verification code"** | Incorrect OTP entered | In demo mode, use the verified universal evaluation code: `123456`. |
| **Order placement rejected with "Credit Limit Exceeded"** | Retailer credit limit exhausted | Expected behavior for credit-locked accounts (`9826033333`). Desk operators can review and override credit holds in `/desk`. |
| **Alembic migration error "Target database is not up to date"** | Unapplied schema revisions | Execute `alembic upgrade head` in the backend virtual environment to align schema with latest head `d93a11c7f5a1`. |
