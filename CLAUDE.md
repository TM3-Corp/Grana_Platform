# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

### First-Time Setup (run once after cloning)

```bash
./setup.sh
```

This script will:
- Create backend Python virtual environment
- Install backend dependencies
- Install frontend npm dependencies
- Set up git hooks

### Running the Application

```bash
# Start both frontend and backend (recommended)
./dev.sh

# Stop all services
./stop.sh

# Or run separately:
# Backend (FastAPI)
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Frontend (Next.js)
cd frontend && npm run dev
```

**Local URLs:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Backend Commands

```bash
cd backend
source venv/bin/activate

# Run tests
pytest                                    # All tests
pytest tests/test_api/                    # API tests only
pytest tests/test_services/               # Service tests only
pytest -k "test_conversion"               # Single test by name

# Linting
flake8 app/
black app/ --check                        # Check formatting
black app/                                # Apply formatting
```

### Frontend Commands

```bash
cd frontend

npm run dev       # Development server (Turbopack)
npm run build     # Production build
npm run lint      # ESLint
```

---

## Critical Rule: Session Work vs Production Code

**All session artifacts MUST go in `.claude_sessions/` directory** (gitignored).

### Production Code (commit)
- `backend/app/` - Backend application code
- `backend/tests/` - Proper unit tests (pytest)
- `frontend/` - Frontend application code
- `frontend/__tests__/` - Frontend unit tests
- `backend/scripts/migrations/` - Data migration scripts (versioned)

### Session Work (never commit)
- `.claude_sessions/current/` - Active session work
- `.claude_sessions/tests/` - Temporary test scripts
- `.claude_sessions/debugging/` - Debug scripts
- `.claude_sessions/exploration/` - Code exploration

**Decision tree:** "Will this code run in production?" → YES: production path, NO: `.claude_sessions/`

---

## Critical Rule: Python Virtual Environments

**ALWAYS use virtual environments** - Python 3.12+ prevents system-wide package installation.

```bash
# Create venv for session work
cd /tmp && python3 -m venv session_venv && source session_venv/bin/activate
pip install psycopg2-binary python-dotenv

# Or use project venv
cd backend && source venv/bin/activate
```

---

## Critical Rule: Supabase Database Connections

**MUST use Session Pooler (IPv4, port 6543)** - Direct connection requires IPv6.

```bash
# ALWAYS unset system variable before running DB scripts
unset DATABASE_URL
python3 script.py  # Now reads from backend/.env correctly
```

**For critical scripts, hardcode the Session Pooler URL:**
```python
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
```

---

## Architecture Overview

**Business Intelligence Layer over RelBase** - The backend is an API Integration/ETL layer, not a traditional application backend.

```
External APIs (Relbase, Shopify, MercadoLibre, Chipax, Lokal)
        ↓
Backend (FastAPI on Railway)
  • API Connectors - sync data from external sources
  • Data transformation & enrichment
  • Business rules (channel mapping, SKU conversion)
  • Analytics aggregation
        ↓
Database (Supabase PostgreSQL)
  • orders, customers, products, channels, inventory
        ↓
Frontend (Next.js on Vercel)
  • NextAuth v5 (credentials → Supabase users table)
  • Dashboard views & analytics
```

### Key Backend Structure

```
backend/app/
├── api/              # FastAPI routers
│   ├── audit.py      # Data auditing (largest file)
│   ├── relbase.py    # Relbase API connector
│   ├── shopify.py    # Shopify connector
│   ├── mercadolibre.py
│   ├── sales_analytics.py
│   ├── products.py
│   ├── orders.py
│   └── sync.py
├── connectors/       # External API clients
├── core/             # Config, database, auth, rate limiting
├── domain/           # Business domain models
├── models/           # Database models
├── repositories/     # Data access layer
└── services/         # Business logic
```

### Key Frontend Structure

```
frontend/
├── app/              # Next.js App Router pages
│   ├── dashboard/    # Main dashboard pages
│   ├── api/          # API routes (auth, users)
│   └── login/
├── components/       # React components
│   ├── charts/       # Recharts visualizations
│   ├── dashboard/    # Dashboard-specific components
│   ├── inventory/    # Inventory management
│   ├── sales-analytics/
│   └── ui/           # Shared UI components
└── lib/              # Utilities and auth config
```

---

## Authentication

**Hybrid approach:** NextAuth v5 (frontend) + JWT validation (backend)

- Frontend: NextAuth with Credentials provider → Supabase `users` table
- Backend: Validates JWT tokens using shared `AUTH_SECRET`
- Passwords: bcrypt-hashed in `users.password_hash`

**Environment variables must match:**
```bash
# Both frontend/.env.local and backend/.env need:
AUTH_SECRET=grana_platform_secret_key_2025_production_ready
```

---

## External API Integration

| Service | Purpose | Auth Headers |
|---------|---------|--------------|
| **Relbase** | Invoicing (Chile) | `company` + `authorization` tokens |
| **Shopify** | E-commerce | Basic auth with password |
| **MercadoLibre** | Marketplace | OAuth access token (auto-refresh) |
| **Chipax** | Accounting | App ID + Secret Key |
| **Lokal** | Distribution | API Key + Maker ID |

**Relbase API pattern:**
```python
headers = {
    'company': RELBASE_COMPANY_TOKEN,
    'authorization': RELBASE_USER_TOKEN
}
# Rate limit: ~6 requests/second (use 0.17s delay)
```

---

## Product Data Model

**Product Families** group SKU variants of the same base product:

```
Family: "Barra Low Carb Manzana Canela"
├── BAMC_U04010 (1 unidad)
├── BAMC_U20010 (5 unidades)
└── BAMC_C02810 (caja master)
```

**Source of truth:** `public/Archivos_Compartidos/Códigos_Grana_Final.csv` - maps SKU → family and format.

**SKU fields calculated dynamically in Python** (not stored in DB):
- SKU Primario: `backend/app/api/audit.py` → `get_sku_primario()`
- Unidades: quantity × conversion factor from CSV

---

## Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | https://grana-platform.vercel.app |
| Backend | Railway | https://granaplatform-production.up.railway.app |
| Database | Supabase | sa-east-1 region |

**Vercel:** Root directory = `frontend`, Framework = Next.js

---

## Common Errors & Solutions

**`ModuleNotFoundError: No module named 'psycopg2'`**
```bash
source venv/bin/activate && pip install psycopg2-binary
```

**`connection to server failed: Network unreachable`**
→ Use Session Pooler (port 6543), not direct connection (port 5432)

**`externally-managed-environment`**
→ Use venv: `python3 -m venv venv && source venv/bin/activate`

**Wrong DATABASE_URL being read**
→ `unset DATABASE_URL` before running scripts
