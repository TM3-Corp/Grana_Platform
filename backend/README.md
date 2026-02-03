# 🍃 Grana Platform - Backend API

REST API backend para la plataforma de integración de datos de Grana SpA (healthy snacks company).

**Stack**: FastAPI + PostgreSQL (Supabase) + Python 3.12

## 📁 Estructura del Proyecto

```
backend/
├── app/                      # Core Application
│   ├── api/                  # REST API Endpoints (Controllers)
│   │   ├── conversion.py
│   │   ├── mercadolibre.py
│   │   ├── orders.py         # ⚡ N+1 query optimized
│   │   ├── product_mapping.py
│   │   ├── products.py
│   │   └── shopify.py
│   │
│   ├── services/             # Business Logic Layer
│   │   ├── conversion_service.py
│   │   ├── mercadolibre_sync_service.py
│   │   ├── order_processing_service.py
│   │   └── product_mapping_service.py
│   │
│   ├── connectors/           # External API Clients
│   │   ├── klog_connector.py       # KLOG/INVAS warehouse API
│   │   ├── mercadolibre_connector.py
│   │   └── shopify_connector.py
│   │
│   ├── models/               # SQLAlchemy ORM Models
│   │   └── order.py
│   │
│   ├── core/                 # Core Configuration
│   │   ├── config.py         # Settings
│   │   └── database.py       # Database connections (unified)
│   │
│   └── main.py               # ✅ Production entry point
│
├── tests/                    # All Tests
│   ├── conftest.py           # Pytest fixtures
│   ├── test_api/             # API endpoint tests
│   ├── test_services/        # Business logic tests
│   └── test_integration/     # Integration tests
│
├── scripts/                  # Operational Scripts
│   ├── data_loading/         # One-time data imports
│   ├── sync/                 # Regular sync operations
│   └── debug/                # Debug & inspection tools
│
├── migrations/               # Database Migrations
├── archive/                  # Legacy Code
├── pytest.ini                # Pytest configuration
├── requirements.txt          # Python dependencies
└── runtime.txt              # Python version for Railway

```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL (or Supabase account)
- pip or venv

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/TM3-Corp/Grana_Platform.git
   cd Grana_Platform/backend
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

   Required variables:
   ```
   DATABASE_URL=postgresql://user:password@host:port/database
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your_key
   ```

5. **Run the development server**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   API will be available at: http://localhost:8000

## 📚 API Documentation

When running locally, interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main Endpoints

```
GET  /                              # API info
GET  /api/v1/orders/                # List orders (supports filters)
GET  /api/v1/orders/stats           # Order statistics
GET  /api/v1/orders/analytics       # Analytics data
GET  /api/v1/products/              # List products
GET  /api/v1/product-mapping/       # Product mapping info
```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m api           # API tests only

# Run specific test file
pytest tests/test_api/test_products.py
```

## 📂 Database Access Patterns

This project supports **three ways** to access the database:

### 1. SQLAlchemy ORM (for complex models)
```python
from app.core.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends

@app.get("/items")
def read_items(db: Session = Depends(get_db)):
    return db.query(Order).all()
```

### 2. psycopg2 Direct (for raw SQL)
```python
from app.core.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM orders WHERE total > %s", (1000,))
results = cursor.fetchall()
cursor.close()
conn.close()
```

### 3. Supabase Client (for Supabase features)
```python
from app.core.database import get_supabase

sb = get_supabase()
result = sb.table('orders').select('*').execute()
```

## 🔧 Scripts

Utility scripts are organized in `/scripts`:

### Data Loading (one-time imports)
```bash
python scripts/data_loading/load_shopify_bulk.py
python scripts/data_loading/load_ml_bulk.py
```

### Sync (regular operations)
```bash
python scripts/sync/sync_shopify_data.py
python scripts/sync/sync_mercadolibre_data.py
```

### Debug (inspection & testing)
```bash
python scripts/debug/check_current_data.py
python scripts/debug/inspect_order.py
```

See `scripts/README.md` for detailed documentation.

## 🚢 Deployment

### Railway (Production)

The backend is configured to deploy automatically on Railway when pushing to GitHub `main` branch.

**Procfile** (Railway auto-detects):
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Environment Variables** (configure in Railway dashboard):
```
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...
```

Railway URL: https://granaplatform-production.up.railway.app

### Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🏗️ Architecture

This backend follows **layered architecture**:

1. **API Layer** (`app/api/`): HTTP endpoints, request/response handling
2. **Service Layer** (`app/services/`): Business logic, orchestration
3. **Connector Layer** (`app/connectors/`): External API integrations
4. **Data Layer** (`app/core/database.py`): Database access

### Key Design Principles

- ✅ **Single Responsibility**: Each module has one clear purpose
- ✅ **Dependency Injection**: FastAPI's dependency system
- ✅ **Separation of Concerns**: API ≠ Business Logic ≠ Data Access
- ✅ **Type Safety**: Type hints everywhere
- ✅ **Documentation**: Docstrings in all public functions

## 🔌 External API Connectors

### KLOG/INVAS (Warehouse Management)

KLOG is Grana's 3PL warehouse system. The connector (`app/connectors/klog_connector.py`) provides:

**Authentication:** Dual auth - Bearer token in headers + credentials in request body.

**Key Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| Summary | `consultaInventarioSkuActivo` | Aggregate inventory by SKU |
| Lot-level | `consultaWmsCajaAlmacenadasWS` | Box-level with lot/expiration |

**Lot/Expiration API (added 2026-02-03):**

```python
from app.connectors.klog_connector import KLOGConnector

connector = KLOGConnector()

# Get lot-level inventory with expiration dates
lots = await connector.get_inventory_with_lots(empresa="GRANA")

# Get inventory expiring within 90 days (FEFO alerts)
expiring = await connector.get_expiring_inventory(days_threshold=90)
```

**Response fields:** `lote` (lot number), `fechaVencimiento` (expiration date), `unidadesDisponibles` (available units)

**Site code:** `"KW BOD 7 LAMPA"` (not `"1KW BOD 7 LAMPA"`)

### MercadoLibre

OAuth-based marketplace API. See `app/connectors/mercadolibre_connector.py`.

### Shopify

GraphQL API for e-commerce. See `app/connectors/shopify_connector.py`.

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Test database connection
python tests/test_integration/test_db_connection.py
```

### Import Errors
```bash
# Ensure you're in the backend/ directory
# Ensure venv is activated
source venv/bin/activate
```

### Performance Issues
- Check `/api/v1/orders/` endpoint - it's optimized for N+1 queries
- Use `limit` and `offset` parameters for pagination
- See `app/api/orders.py:104-137` for optimization details

## 📖 Additional Documentation

- **Tests**: See `tests/README.md`
- **Scripts**: See `scripts/README.md`
- **Frontend**: See `../frontend/README.md`

## 👥 Authors

- **TM3 Team** - Development & Architecture
- **Project**: Grana Platform Integration

## 📝 License

Private - Grana SpA © 2025
