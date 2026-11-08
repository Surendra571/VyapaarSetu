# VyapaarSetu Project Documentation

## Phase 1: Architecture & Setup Overview

VyapaarSetu is a B2B FMCG Ordering Platform designed for distributors and kirana store retailers in Jabalpur, India.

### Directory Structure
```
vyapaarsetu/
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── api/              # API routers and endpoints
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   └── health.py
│   │   │       └── router.py
│   │   ├── core/             # Configuration, database engine & settings
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   └── main.py           # Application entrypoint & CORS setup
│   ├── tests/                # Automated pytest suite
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                 # React + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── api/              # API client and TanStack query hooks
│   │   ├── components/       # Shared UI components
│   │   ├── layouts/          # Responsive App shell and navigation
│   │   ├── pages/            # View pages (Dashboard, Health, etc.)
│   │   ├── types/            # TypeScript interfaces
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── vite.config.ts
├── docs/                     # Technical specifications & documentation
├── .env.example              # Environment variables template
├── .gitignore
├── docker-compose.yml        # PostgreSQL container configuration
└── README.md                 # Setup & running instructions
```

### Technology Matrix
- **Backend Framework:** FastAPI 0.115+
- **ASGI Server:** Uvicorn
- **ORM & Database Driver:** SQLAlchemy 2.0+ with `asyncpg`
- **Settings & Validation:** Pydantic v2 & `pydantic-settings`
- **Frontend Framework:** React 18 / 19 with Vite
- **Language:** TypeScript
- **Styling:** Tailwind CSS with PostCSS
- **Routing:** React Router v6
- **Server State Management:** TanStack React Query v5
- **Containerization:** Docker Compose (PostgreSQL 16)

