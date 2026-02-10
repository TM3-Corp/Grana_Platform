# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

### First-Time Setup

```bash
./setup.sh
```

### Running the Application

```bash
npx supabase start           # Start local Supabase Docker
npx supabase db reset        # Apply migrations (from supabase/migrations/)
./dev.sh                     # Start frontend + backend
./stop.sh                    # Stop app (Supabase keeps running)
npx supabase stop            # Stop Supabase Docker
```

**Local URLs:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Supabase Studio: http://127.0.0.1:54323

**Logs (when running via dev.sh):**
- Backend: `tail -f /tmp/grana_backend.log`
- Frontend: `tail -f /tmp/grana_frontend.log`

### Backend Commands

```bash
cd backend && source venv/bin/activate

# Tests
pytest                                    # All tests
pytest tests/test_api/                    # API tests
pytest tests/test_services/               # Service tests
pytest tests/test_integration/            # Integration tests (DB, Shopify)
pytest tests/test_repositories/           # Repository tests
pytest -k "test_conversion"               # Single test by name

# Linting
flake8 app/
black app/ --check
black app/
```

### Frontend Commands

```bash
cd frontend
npm run dev       # Development server
npm run lint      # ESLint
npx tsc --noEmit  # Type check (use this instead of npm run build)
```

---

## Critical Rules

### 1. Development vs Production Environment

**Default is DEVELOPMENT** — uses local Supabase Docker, never production.

| File | Environment | Tracked |
|------|-------------|---------|
| `backend/.env.development` | Development | Yes |
| `frontend/.env.development` | Development | Yes |
| `backend/.env.production` | Production | No |
| `frontend/.env.production` | Production | No |

- `APP_ENV=development` (default) → loads `.env.development`
- `./dev.sh` automatically sets `APP_ENV=development`

**Claude Code hooks** (`.claude/hooks/`) automatically block dangerous commands:
- `supabase link` / `supabase push` / `supabase db pull` → Touches production
- `npm run build` → May connect to remote

### 2. Session Work vs Production Code

**All session artifacts MUST go in `.claude_sessions/`** (gitignored).

| Path | Commit? | Purpose |
|------|---------|---------|
| `backend/app/`, `frontend/` | Yes | Production code |
| `backend/tests/` | Yes | Proper unit tests |
| `.claude_sessions/` | No | Debug scripts, exploration, temp tests |

### 3. Python Virtual Environments

**ALWAYS activate venv** before running Python:

```bash
cd backend && source venv/bin/activate
```

### 4. Database Connections

**Production MUST use Session Pooler (port 6543)** — Direct connection requires IPv6.

```bash
# ALWAYS unset before running DB scripts
unset DATABASE_URL
python3 script.py
```

**Database access patterns** in `core/database.py`:

| Function | Returns | Use Case |
|----------|---------|----------|
| `get_db()` | SQLAlchemy Session | FastAPI dependency, ORM models |
| `get_db_connection()` | psycopg2 conn (tuples) | Raw SQL, bulk operations |
| `get_db_connection_dict()` | psycopg2 conn (dicts) | API responses, JSON serialization |
| `get_db_connection_with_retry()` | psycopg2 conn + retry | Production resilience (SSL failures) |
| `get_supabase()` | Supabase Client | Supabase-specific features |

For production code, prefer `_with_retry` variants for resilience against Supabase SSL connection drops.

---

## Architecture Overview

**Business Intelligence Layer** — ETL/API integration layer, not traditional backend.

```
External APIs (Relbase, Shopify, MercadoLibre, Chipax, Lokal)
        ↓
Backend (FastAPI on Railway)
  • API Connectors, data transformation, business rules
        ↓
Database (Supabase PostgreSQL)
        ↓
Frontend (Next.js on Vercel)
  • NextAuth v5, Dashboard views
```

### Key Services

| Service | Location | Purpose |
|---------|----------|---------|
| `ProductCatalogService` | `services/product_catalog_service.py` | Product families, SKU mappings, conversion factors |
| `SKUMappingService` | `services/sku_mapping_service.py` | Database-driven SKU transformation rules |
| `SyncService` | `services/sync_service.py` | Orchestrates external API sync with transactional rollback |
| `InventoryService` | `services/inventory_service.py` | Stock level management across warehouses |

**Service Patterns:**
- Services use in-memory caching (`_catalog_cache`) with `reload_catalog()` for invalidation
- Singletons accessed via factory functions (e.g., `get_sku_mapping_service()`)

### Authentication

**Hybrid:** NextAuth v5 (frontend) + JWT validation (backend)

- `AUTH_SECRET` must match between frontend and backend
- RBAC: admin (3) > user (2) > viewer (1)
- Protected endpoints use `get_current_user` dependency from `core/auth.py`
- Role-based decorators: `require_admin`, `require_user`, `require_viewer`

**Frontend:** Uses App Router (`app/` directory) with `middleware.ts` for route protection.

### External API Integration

| Service | Purpose | Auth |
|---------|---------|------|
| **Relbase** | Invoicing (Chile) | `company` + `authorization` headers |
| **Shopify** | E-commerce | Basic auth |
| **MercadoLibre** | Marketplace | OAuth (auto-refresh) |
| **Chipax** | Accounting | App ID + Secret Key |
| **Lokal** | Distribution | API Key + Maker ID |

### RelBase Inventory Sync Patterns

**CRITICAL:** When syncing inventory from RelBase, always fetch the list of active products from the RelBase API first, NOT from the local `products` table.

```python
# ❌ WRONG: Using local products table (may include legacy/inactive products)
cursor.execute("SELECT id, external_id FROM products WHERE source = 'relbase'")

# ✅ CORRECT: Fetch active products from RelBase API first
products = self._fetch_relbase_active_products()  # GET /api/v1/productos
```

**Why this matters:**
- The `/api/v1/productos` endpoint returns ONLY active products in RelBase
- Legacy products (e.g., SKU prefix `ANU-`) return 401/403 errors when querying lot/serial data
- The local `products` table may contain stale records for inactive products
- This pattern prevents sync failures and 401 Unauthorized errors

**Endpoints:**
| Endpoint | Purpose | Notes |
|----------|---------|-------|
| `GET /api/v1/productos` | List active products | Use this for inventory sync |
| `GET /api/v1/productos/{id}/lotes_series/{warehouse_id}` | Get lot/serial stock | Only works for active products |
| `GET /api/v1/bodegas` | List warehouses | Returns all enabled warehouses |

### Product Data Model

**Product Families** group SKU variants:

```
Family: "Barra Low Carb Manzana Canela"
├── BAMC_U04010 (1 unidad)
├── BAMC_U20010 (5 unidades)
└── BAMC_C02810 (caja master - 20 units)
```

SKU fields calculated dynamically via `ProductCatalogService` (not stored in orders).

---

## Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | https://grana-platform.vercel.app |
| Backend | Railway | https://granaplatform-production.up.railway.app |
| Database | Supabase | sa-east-1 region |

---

## Known Critical Issues

> **Full analysis:** `docs/CRITICAL_ISSUES_ANALYSIS.md`

| Issue | Status | Impact |
|-------|--------|--------|
| `sales_facts_mv.units_sold` missing conversion factors | ✅ Resolved | Fixed via migration (CORP-162) |
| Audit totals ignore category/channel filters | ✅ Resolved | Fixed (CORP-155) |
| Three SKU mapping systems with different coverage | 🔴 Open | SKUs mapped in audit, unmapped in analytics |
| Sales sync silent failure (5 chained bugs) | ✅ Resolved | Feb 2026 data recovered ($5.4M→$11M) |
| Inventory velocity using `original_sku` not `catalog_sku` | ✅ Resolved | Variant sales now included in velocity calc |

**Warning:** `REFRESH MATERIALIZED VIEW CONCURRENTLY` is not supported on `sales_facts_mv` (no unique index). The sync uses non-concurrent refresh as fallback.

---

## Common Errors

**`ModuleNotFoundError: psycopg2`** → `source venv/bin/activate && pip install psycopg2-binary`

**`connection to server failed: Network unreachable`** → Use Session Pooler (port 6543)

**`externally-managed-environment`** → Use venv

**Wrong DATABASE_URL** → `unset DATABASE_URL` before running scripts
