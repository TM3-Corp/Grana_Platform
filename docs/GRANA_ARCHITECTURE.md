# Grana Platform - Architecture Overview

> **Business Intelligence system** for Grana SpA (Chilean food company).
> Consolidates sales data from multiple channels into a single dashboard for analytics and inventory management.

---

## Stack Summary

| Layer | Technology | Version | Hosting |
|-------|------------|---------|---------|
| **Frontend** | Next.js + React + TypeScript | Next 15.5, React 19 | Vercel |
| **Backend** | FastAPI + Python | FastAPI 0.104+, Python 3.10+ | Railway |
| **Database** | PostgreSQL | 17+ | Supabase |
| **Auth** | NextAuth v5 (frontend) + JWT (backend) | Beta 29 | - |
| **Styling** | Tailwind CSS | v4 | - |
| **Charts** | Recharts | 3.2 | - |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                        │
│  ┌──────────┐  ┌────────────┐  ┌─────────┐  ┌────────┐         │
│  │ Relbase  │  │ Shopify    │  │ ML      │  │ Chipax │         │
│  │(Invoices)│  │(E-commerce)│  │(Market) │  │(Acctg) │         │
│  └────┬─────┘  └─────┬──────┘  └────┬────┘  └───┬────┘         │
└───────┼──────────────┼──────────────┼───────────┼───────────────┘
        │              │              │           │
        ▼              ▼              ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI @ Railway)                  │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │ Connectors  │  │   Services   │  │   API Routers    │       │
│  │ (shopify,   │  │ (sync,       │  │ /api/v1/...      │       │
│  │  meli, etc) │  │  catalog,    │  │ - orders         │       │
│  └─────────────┘  │  inventory)  │  │ - products       │       │
│                   └──────────────┘  │ - sales-analytics│       │
│  ┌─────────────┐                    │ - inventory      │       │
│  │    Core     │                    │ - audit          │       │
│  │ (auth, db,  │                    │ - sync           │       │
│  │  rate-limit)│                    └──────────────────┘       │
│  └─────────────┘                                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              DATABASE (PostgreSQL @ Supabase)                   │
│                                                                 │
│  Core Tables:                    OLAP:                         │
│  ├── orders (source of truth)    ├── dim_date                  │
│  ├── order_items                 └── sales_summary_*           │
│  ├── customers                                                 │
│  ├── products                    Inventory:                    │
│  ├── channels                    ├── warehouses                │
│  └── product_catalog             ├── warehouse_stock           │
│                                  └── inventory_movements       │
│  Audit:                                                        │
│  └── orders_audit (trigger-based)                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 FRONTEND (Next.js @ Vercel)                     │
│                                                                 │
│  ┌──────────────────┐  ┌────────────────────────────────┐      │
│  │   Auth Layer     │  │        Dashboard Pages         │      │
│  │  (NextAuth v5)   │  │  /dashboard                    │      │
│  │  - JWT sessions  │  │  /dashboard/sales-analytics    │      │
│  │  - RBAC roles    │  │  /dashboard/orders             │      │
│  └──────────────────┘  │  /dashboard/warehouse-inventory│      │
│                        │  /dashboard/audit              │      │
│  ┌──────────────────┐  │  /dashboard/product-catalog    │      │
│  │   Components     │  │  /dashboard/sku-mappings       │      │
│  │  - charts/       │  └────────────────────────────────┘      │
│  │  - inventory/    │                                          │
│  │  - sales-*       │  ┌────────────────────────────────┐      │
│  └──────────────────┘  │   AI Chat (Claude API)         │      │
│                        │   FloatingChatWidget.tsx       │      │
│                        └────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture (Python/FastAPI)

```
backend/app/
├── main.py                 # FastAPI app, router registration, CORS, middleware
├── api/                    # REST endpoints (21 routers)
│   ├── orders.py           # CRUD for orders
│   ├── products.py         # Product management
│   ├── sales_analytics.py  # OLAP analytics endpoints
│   ├── audit.py            # Data auditing & correction
│   ├── sync.py             # Scheduled sync (UptimeRobot triggers)
│   ├── inventory.py        # Stock queries
│   ├── warehouses.py       # Multi-warehouse management
│   ├── chat.py             # Claude AI chat for inventory queries
│   ├── shopify.py          # Shopify connector endpoints
│   ├── mercadolibre.py     # MercadoLibre connector
│   ├── relbase.py          # Relbase invoicing connector
│   └── ...
├── connectors/             # External API clients
│   ├── shopify_connector.py
│   └── mercadolibre_connector.py
├── services/               # Business logic
│   ├── sync_service.py           # Orchestrates data sync
│   ├── product_catalog_service.py # SKU mappings, families
│   ├── inventory_service.py      # Stock calculations
│   ├── sku_mapping_service.py    # SKU transformation rules
│   └── claude_chat_service.py    # AI-powered queries
├── repositories/           # Data access layer (raw SQL)
│   ├── order_repository.py
│   └── product_repository.py
├── core/                   # Infrastructure
│   ├── config.py           # Pydantic settings (env loading)
│   ├── database.py         # SQLAlchemy + psycopg2 + Supabase client
│   ├── auth.py             # JWT validation, RBAC
│   └── rate_limit.py       # Sliding window rate limiter
├── models/                 # SQLAlchemy ORM models
└── domain/                 # Business domain models
```

### Key Patterns

- **Three DB access tiers**: SQLAlchemy ORM, psycopg2 raw SQL, Supabase client
- **Connection retry logic**: Exponential backoff for SSL failures
- **Rate limiting**: Per-user/IP/API-key sliding window limits

---

## Frontend Architecture (Next.js 15 / React 19)

```
frontend/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # Root layout + Providers
│   ├── page.tsx                # Landing → redirects to /dashboard
│   ├── login/page.tsx          # Login form
│   └── dashboard/              # Protected routes
│       ├── page.tsx            # Main dashboard
│       ├── sales-analytics/    # Sales charts & tables
│       ├── orders/             # Order management
│       ├── warehouse-inventory/# Stock by warehouse
│       ├── audit/              # Data correction audit trail
│       ├── product-catalog/    # Product CRUD
│       ├── sku-mappings/       # SKU transformation rules
│       ├── production-planning/# Inventory recommendations
│       └── users/              # User management (admin)
├── components/
│   ├── charts/                 # Recharts visualizations
│   │   ├── ExecutiveSalesChart.tsx
│   │   ├── TopProductsBar.tsx
│   │   └── QuarterlyAnalytics.tsx
│   ├── inventory/              # Stock management UI
│   │   ├── WarehouseInventoryTable.tsx
│   │   └── StockLevelIndicator.tsx
│   ├── sales-analytics/        # Analytics components
│   ├── dashboard/              # Shared dashboard components
│   │   ├── UnifiedFilterBar.tsx
│   │   └── DashboardFilterContext.tsx
│   └── ui/                     # Generic UI (Skeleton, MultiSelect)
├── lib/
│   ├── auth.ts                 # NextAuth config (Credentials provider)
│   ├── catalog-api.ts          # Backend API calls
│   └── utils.ts                # Helpers
└── middleware.ts               # Auth middleware (protects /dashboard)
```

### Key Patterns

- **App Router** with server/client components
- **NextAuth v5** with Credentials provider → queries Supabase `users` table
- **JWT sessions** with role stored in token
- **Turbopack** for fast dev builds

---

## Database Schema (Key Tables)

| Table | Purpose |
|-------|---------|
| `orders` | **Source of truth** for all sales (editable, auditable) |
| `order_items` | Line items per order with SKU mapping |
| `customers` | Customer master data with channel assignment |
| `products` | Product catalog with packaging hierarchy |
| `channels` | Sales channels (Relbase, Shopify, MercadoLibre, etc.) |
| `warehouses` | Warehouse definitions |
| `warehouse_stock` | Stock per product per warehouse (lot tracking) |
| `orders_audit` | Trigger-based audit log of all order changes |
| `product_catalog` | Official SKU catalog with conversion factors |
| `sku_mappings` | Rules to transform channel SKUs → canonical SKUs |
| `dim_date` | OLAP date dimension (2020-2030) |
| `users` | Application users with bcrypt passwords |
| `api_keys` | API key authentication for integrations |

---

## Data Flow

### 1. Sync (ETL)

Triggered by UptimeRobot cron → `POST /api/v1/sync/full`

```
External APIs → Connectors → Transform (SKU mapping) → Upsert DB → Audit trigger
```

- Fetches data from Relbase, Shopify, MercadoLibre APIs
- Transforms SKUs using `sku_mappings` rules
- Upserts into `orders`, `order_items`, `customers`
- Database trigger populates `orders_audit` on changes

### 2. Analytics

```
Frontend → /api/v1/sales-analytics/* → OLAP query (dim_date + orders) → JSON response
```

- Backend runs aggregated queries against date dimension
- Returns data formatted for Recharts visualizations

### 3. Inventory

```
Excel Upload / API Sync → warehouse_stock → Claude Chat queries via Anthropic API
```

- Manual Excel upload or Relbase API sync updates `warehouse_stock`
- AI chat provides natural language inventory queries

---

## Authentication Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Browser   │ ──▶  │  NextAuth   │ ──▶  │  Supabase   │
│  (Login)    │      │  (verify)   │      │  (users)    │
└─────────────┘      └──────┬──────┘      └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  JWT Token  │
                     │  (session)  │
                     └──────┬──────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   Frontend            Backend API         Protected
   (session)           (validates JWT)     Routes
```

- **Frontend**: NextAuth Credentials provider, bcrypt password verification
- **Backend**: Validates JWT using shared `AUTH_SECRET`
- **RBAC**: admin (3) > user (2) > viewer (1)

---

## External API Integrations

| Service | Purpose | Auth Method |
|---------|---------|-------------|
| **Relbase** | Invoicing (Chile) | `company` + `authorization` headers |
| **Shopify** | E-commerce orders | Basic auth |
| **MercadoLibre** | Marketplace orders | OAuth2 (auto-refresh) |
| **Chipax** | Accounting | App ID + Secret Key |
| **Lokal** | Distribution | API Key + Maker ID |
| **Anthropic** | Claude AI chat | API Key |

---

## Key Dependencies

### Backend (Python)

| Package | Purpose |
|---------|---------|
| `fastapi`, `uvicorn` | Web framework |
| `sqlalchemy`, `psycopg2-binary` | Database ORM & driver |
| `supabase` | Supabase client |
| `httpx`, `requests` | External API calls |
| `pandas` | Data processing |
| `anthropic` | Claude AI integration |
| `python-jose`, `passlib` | JWT & password hashing |

### Frontend (Node)

| Package | Purpose |
|---------|---------|
| `next` 15.5, `react` 19 | Framework |
| `next-auth` v5 | Authentication |
| `recharts` | Charts |
| `tailwindcss` v4 | Styling |
| `fuse.js` | Fuzzy search |
| `bcryptjs` | Password hashing |

---

## Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | https://grana-platform.vercel.app |
| Backend | Railway | https://granaplatform-production.up.railway.app |
| Database | Supabase | sa-east-1 region |

### Environment Separation

- **Development**: Local Supabase Docker (`127.0.0.1:54321`)
- **Production**: Remote Supabase (Session Pooler, port 6543)

See `CLAUDE.md` for development setup instructions.
