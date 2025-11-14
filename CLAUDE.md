# 🍃 Grana Platform - Claude Code Development Guidelines

## 🚨 **CRITICAL RULE #1: Session Work vs Production Code**

### **THE PROBLEM WE'RE SOLVING**

Previously, Claude was mixing **session artifacts** with **production code**, causing:
- Debug scripts committed to production
- Temporary exploration code in the codebase
- Session documentation polluting the repo
- Difficulty distinguishing between production code and debugging work

### **THE SOLUTION**

**Session Work ≠ Production Code**

All session artifacts MUST go in `.claude_sessions/` directory (which is .gitignored).

---

## 📂 **Where to Put Your Code**

### ✅ **Production Code** (COMMIT to git)

Goes in standard paths:
- `backend/app/` - Backend application code
- `backend/tests/` - Proper unit tests (pytest, 80% coverage goal)
- `frontend/` - Frontend application code
- `frontend/__tests__/` - Frontend unit tests (jest)
- `backend/alembic/versions/` - Database migrations
- `backend/scripts/migrations/` - Data migration scripts (one-time, but versioned)

**Examples:**
```python
# ✅ CORRECT: Production API endpoint
# File: backend/app/api/products.py
@router.get("/products")
async def get_products():
    return service.get_all_products()
```

```typescript
// ✅ CORRECT: Production frontend component
// File: frontend/components/ProductList.tsx
export default function ProductList() { ... }
```

### ❌ **Session Work** (NEVER commit - use `.claude_sessions/`)

Goes in `.claude_sessions/`:
- `.claude_sessions/current/` - Active session work
- `.claude_sessions/tests/` - Temporary test scripts
- `.claude_sessions/debugging/` - Debug scripts
- `.claude_sessions/exploration/` - Code exploration

**Examples:**
```python
# ✅ CORRECT: Session debugging script
# File: .claude_sessions/current/debug_api_response.py
import requests
response = requests.get("http://localhost:8000/api/products")
print(response.json())
```

```bash
# ✅ CORRECT: Temporary verification script
# File: .claude_sessions/current/test_catalog_endpoints.sh
curl -s "http://localhost:8000/api/v1/catalog" | jq .
```

---

## 🤔 **Decision Tree: Where Does This Code Go?**

Ask yourself:

1. **"Will this code run in production?"**
   - YES → Production path (`backend/app/`, `frontend/`)
   - NO → `.claude_sessions/`

2. **"Is this a proper unit test with assertions?"**
   - YES → Test directory (`backend/tests/`, `frontend/__tests__/`)
   - NO → `.claude_sessions/tests/`

3. **"Is this exploring/debugging the codebase?"**
   - YES → `.claude_sessions/exploration/` or `.claude_sessions/debugging/`

4. **"Is this a one-time data migration that needs versioning?"**
   - YES → `backend/scripts/migrations/` (committed)
   - NO → `.claude_sessions/current/`

---

## 📋 **Session Workflow Example**

### ❌ **WRONG WORKFLOW (Before)**
```bash
# Claude creates debug script directly in backend
$ echo "print('Debug API')" > backend/debug_api.py
$ git add backend/debug_api.py
$ git commit -m "debugging"  # 🔥 Session artifact in production!
```

### ✅ **CORRECT WORKFLOW (Now)**
```bash
# Claude creates debug script in session directory
$ echo "print('Debug API')" > .claude_sessions/current/debug_api.py
$ python3 .claude_sessions/current/debug_api.py
# File is .gitignored, never committed ✅

# When ready, Claude creates PRODUCTION code
$ # Creates proper endpoint in backend/app/api/products.py
$ git add backend/app/api/products.py
$ git commit -m "feat: add products API endpoint"  # ✅ Production code!
```

---

## 🛡️ **Automated Protection: Git Hooks**

### Pre-Commit Hook (Automatically Blocks Session Artifacts)

A git pre-commit hook is installed that **automatically prevents** session artifacts from being committed.

**Installation:**
```bash
# Run once after cloning the repo
./scripts/setup-git-hooks.sh
```

**What it does:**
- ❌ Blocks commits containing files in `.claude_sessions/`
- ❌ Blocks commits matching `session_*.py`, `debug_temp_*`, `exploration_*`
- ⚠️  Warns about files in `backend/scripts/debug/` (asks for confirmation)
- ✅ Allows legitimate production code commits

**Example:**
```bash
$ echo "test" > .claude_sessions/current/debug.py
$ git add -f .claude_sessions/current/debug.py
$ git commit -m "test"

🔍 Checking for session artifacts...
❌ ERROR: Attempting to commit files from .claude_sessions/

Files blocked:
.claude_sessions/current/debug.py

💡 TIP: Session work should stay in .claude_sessions/ and never be committed.
```

**Benefits:**
- 🚀 No need to remember rules manually
- 🛡️ Automatic enforcement for everyone on the team
- 💡 Clear error messages when rules are violated
- 🔒 Defense-in-depth (works with .gitignore)

---

## 🚨 **CRITICAL RULE #2: Python Virtual Environments & Supabase Connections**

### **THE PROBLEM**

WSL2 environment has specific limitations that must be addressed:

1. **Python Externally-Managed Environment**: Python 3.12+ prevents system-wide package installation
2. **IPv4/IPv6 Connectivity**: Supabase direct connection requires IPv6 (not available in WSL2)
3. **Database URL Priority**: System environment variables override `.env` files

### **THE SOLUTION**

**ALWAYS use virtual environments and Session Pooler for Supabase**

---

### **✅ Rule 2.1: Python Commands MUST Use venv**

**WRONG:**
```bash
# ❌ This will FAIL in WSL2 (externally-managed Python)
python3 script.py
pip install package
```

**CORRECT:**
```bash
# ✅ Create temporary venv for session work
cd /tmp
python3 -m venv session_venv
source session_venv/bin/activate
pip install psycopg2-binary python-dotenv
python3 /path/to/script.py

# ✅ Or use project venv if available
cd /home/javier/Proyectos/Grana/Grana_Platform
source venv/bin/activate  # (if exists)
python3 script.py
```

**When to create venv:**
- Running any Python script that imports non-standard packages
- Executing database migrations
- Running tests
- Any operation that requires `psycopg2`, `pandas`, `requests`, etc.

---

### **✅ Rule 2.2: Supabase Connections MUST Use Session Pooler**

**PROBLEM:** Direct Supabase connection requires IPv6 (WSL2 = IPv4 only)

```
Direct Connection (IPv6 - WILL FAIL in WSL2):
postgresql://postgres:[PASSWORD]@db.lypuvibmtxjaxmcmahxr.supabase.co:5432/postgres
❌ Error: Network unreachable

Session Pooler (IPv4 - WORKS in WSL2):
postgresql://postgres.lypuvibmtxjaxmcmahxr:[PASSWORD]@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
✅ Success!
```

**CRITICAL: Backend `.env` already configured correctly**

```bash
# File: backend/.env
DATABASE_URL=postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

**But system environment variable may override!**

**Solution:**
```bash
# ALWAYS unset system variable before running DB scripts
unset DATABASE_URL
python3 script.py  # Now reads from .env file correctly
```

---

### **✅ Rule 2.3: Database Migration Workflow**

**Complete workflow for running migrations:**

```bash
# Step 1: Create temporary venv
cd /tmp
python3 -m venv migration_venv
source migration_venv/bin/activate

# Step 2: Install dependencies
pip install psycopg2-binary python-dotenv -q

# Step 3: Unset system DATABASE_URL (if exists)
unset DATABASE_URL

# Step 4: Run migration script
python3 /path/to/migration_script.py

# Step 5: Verify success
echo $?  # Should be 0
```

**Example from Migration 014:**
```bash
cd /tmp && \
python3 -m venv migration_venv && \
source migration_venv/bin/activate && \
pip install psycopg2-binary -q && \
unset DATABASE_URL && \
python3 /home/javier/Proyectos/Grana/Grana_Platform/.claude_sessions/current/run_migration_014.py
```

---

### **✅ Rule 2.4: Hardcode Pooler URL for Critical Scripts**

For scripts that MUST work regardless of environment variables:

```python
# ✅ CORRECT: Hardcode Session Pooler URL
DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

import psycopg2
conn = psycopg2.connect(DATABASE_URL)
# This will ALWAYS work in WSL2 ✅
```

**When to hardcode:**
- Migration scripts (must be reliable)
- Database tests
- Data population scripts
- Any critical infrastructure script

**When NOT to hardcode:**
- Production backend code (use .env)
- Frontend environment variables
- API integrations (use config)

---

### **📋 Checklist Before Running Any DB Operation**

- [ ] Am I using a venv? (`source venv/bin/activate`)
- [ ] Did I unset DATABASE_URL? (`unset DATABASE_URL`)
- [ ] Is the script using Session Pooler (port 6543)?
- [ ] Do I have psycopg2-binary installed in venv?
- [ ] Is this a session script (in `.claude_sessions/`)?

---

### **🆘 Common Errors & Solutions**

**Error:** `ModuleNotFoundError: No module named 'psycopg2'`
```bash
# Solution: Activate venv and install
source venv/bin/activate
pip install psycopg2-binary
```

**Error:** `connection to server at "db.lypuvibmtxjaxmcmahxr.supabase.co" failed: Network unreachable`
```bash
# Solution: Use Session Pooler (IPv4), not direct connection (IPv6)
# Check DATABASE_URL uses: aws-1-sa-east-1.pooler.supabase.com:6543
```

**Error:** `externally-managed-environment`
```bash
# Solution: Use venv, don't install system-wide
python3 -m venv venv
source venv/bin/activate
pip install package
```

**Error:** Wrong DATABASE_URL being read
```bash
# Solution: Unset system env variable
unset DATABASE_URL
# Now Python will read from .env file
```

---

## 🏗️ **Project Architecture**

### Current Stack
- **Backend:** FastAPI + PostgreSQL/Supabase
- **Frontend:** Next.js 13 (App Router) + TypeScript
- **Database:** PostgreSQL with Supabase
- **Deployment:** Railway (backend) + Vercel (frontend)

### Clean Architecture Pattern
```
Domain Layer     → Pure business logic (app/domain/)
Repository Layer → Data access (app/repositories/)
Service Layer    → Business orchestration (app/services/)
API Layer        → HTTP endpoints (app/api/)
```

---

## 🧪 **Testing Standards**

### Production Tests (COMMIT these)
```python
# ✅ backend/tests/test_products.py
def test_get_all_products():
    """Test retrieving all products"""
    products = service.get_all_products()
    assert len(products) > 0
    assert products[0].sku is not None
```

### Session Tests (DON'T commit)
```python
# ✅ .claude_sessions/tests/quick_product_test.py
from app.services.product_service import ProductService
service = ProductService()
products = service.get_all_products()
print(f"Found {len(products)} products")  # Quick verification
```

---

## 🚀 **Deployment**

- **Backend (Railway):** Auto-deploys from `main` branch
- **Frontend (Vercel):** Auto-deploys from `main` branch
- **Database:** Supabase PostgreSQL

**IMPORTANT:** Only production code should reach Railway/Vercel. Session artifacts in `.claude_sessions/` are .gitignored and never deployed.

---

## 📝 **Checklist Before Committing**

Before running `git commit`, verify:

- [ ] No files from `.claude_sessions/` are staged
- [ ] No `session_*.py` or `debug_temp_*` files
- [ ] Only production code and proper tests are included
- [ ] No temporary exploration or debugging scripts
- [ ] Migration scripts are in proper `scripts/migrations/` if they need versioning

---

## 🆘 **When in Doubt**

**Question:** "Should I commit this file?"

**Ask:**
1. Does it provide value to the production system?
2. Will other developers need this code?
3. Is it a proper test or just a quick verification?

If unsure → Put it in `.claude_sessions/` first. You can always move it to production paths later if needed.

---

**Remember:** Session work in `.claude_sessions/` is your playground. Production code is sacred and should only contain what actually needs to run in production or be maintained long-term.

---

## 🎯 **Platform Vision: Business Intelligence Layer Over RelBase**

### **The Core Problem We're Solving**

Grana uses **RelBase** as their invoicing system (facturador). RelBase has limitations:

1. **Limited reporting capabilities** - Can't do multidimensional analysis
2. **Human classification errors** - $408.8M in invoices without channel_id assigned
3. **No pivot table functionality** - Can't group by format + channel + customer simultaneously
4. **Read-only API** - We can only GET data, cannot modify/correct it in RelBase

**Our Solution:** Build a Business Intelligence platform that reads from RelBase and applies business rules to visualize data correctly, even when source data has errors.

---

## 📊 **RelBase Data Structure (CRITICAL)**

### **How RelBase Stores Data**

**In facturas/boletas JSON:**
```python
{
  "id": 39833042,
  "channel_id": 3906,          # ✅ EXISTS: Number (1448, 1459, 3768, etc.)
  "channel_name": None,        # ❌ ALWAYS NULL - not provided
  "customer_id": 7344922,      # ✅ EXISTS: Number
  "customer_name": None,       # ❌ ALWAYS NULL - not provided
  "amount_total": 77859,
  "created_at": "2025-10-17",
  "products": [...]
}
```

### **Getting Human-Readable Names**

Names come from **separate API calls**:

```python
# 1. Channel names: GET /api/v1/canal_ventas
{
  "data": {
    "channels": [
      {"id": 1448, "name": "ECOMMERCE"},
      {"id": 1459, "name": "RETAIL"},
      {"id": 3768, "name": "CORPORATIVO"},
      {"id": 3906, "name": "DISTRIBUIDOR"},
      {"id": 1544, "name": "EMPORIOS Y CAFETERIAS"}
    ]
  }
}

# 2. Customer names: GET /api/v1/clientes/{customer_id}
{
  "data": {
    "id": 596810,
    "name": "CENCOSUD RETAIL S.A.",  # ← Here's the name
    "rut": "81201000-K"
  }
}
```

**Key Insight:** RelBase invoices only have IDs. We must query the API separately to get names.

---

## 🏗️ **Business Intelligence Architecture**

### **Data Flow**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. RelBase (Source of Truth - Read Only)                   │
│    • Facturas/Boletas with channel_id + customer_id        │
│    • Has errors: 345 invoices ($408.8M) without channel    │
│    • Limited reporting: can't pivot/group effectively      │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ GET /api/v1/* (read-only)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Our Platform (Business Intelligence Layer)              │
│    • Reads data from RelBase API                           │
│    • Applies business rules to correct classifications     │
│    • Maps: customer_id → correct channel_id                │
│    • Groups products into families                         │
│    • Enables multidimensional analysis                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ Frontend displays corrected data
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Visualizations (Executive Dashboard)                    │
│    • Pivot tables by: format × channel × customer × date   │
│    • Hierarchical product view (families → SKUs)           │
│    • Corrected channel assignments (even if RelBase wrong) │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌳 **Product Families & Hierarchical Analysis**

### **The Problem**

RelBase shows SKU-level sales:
```
Top Products in RelBase:
1. BAMC_U04010 (Barra Low Carb Manzana Canela x1) - 50,000 units
2. BAMC_U20010 (Barra Low Carb Manzana Canela x5) - 10,000 units
3. BAMC_C02810 (Barra Low Carb Manzana Canela caja master) - 500 units
```

**Question:** "What's our best-selling product?"
**Wrong Answer:** "BAMC_U04010"
**Right Answer:** "Barra Low Carb Manzana Canela" (across all formats)

### **Product Family Concept**

A **Product Family** groups all SKU variants of the same base product:

```
Family: "Barra Low Carb Manzana Canela"
├── BAMC_U04010 (1 unidad)    → 50,000 units
├── BAMC_U20010 (5 unidades)  → 10,000 units
└── BAMC_C02810 (caja master) → 500 units
────────────────────────────────────────────
TOTAL FAMILY                  → 60,500 units
```

**Source of Truth:** `/public/Archivos_Compartidos/Códigos_Grana_Final.csv`
- Maps SKU → Product Family
- Maps SKU → Format (1U, 5U, caja master)

### **Analysis Hierarchy**

Our platform enables analysis at multiple levels:

```
Level 1: PRODUCT FAMILY
│  "Barra Low Carb Manzana Canela" - $X total revenue
│
├─ Level 2: BY FORMAT
│  ├─ 1 unidad (BAMC_U04010) - $Y
│  ├─ 5 unidades (BAMC_U20010) - $Z
│  └─ Caja master (BAMC_C02810) - $W
│
├─ Level 3: BY CHANNEL
│  ├─ E-commerce - $A
│  ├─ Retail - $B
│  ├─ Corporativo - $C
│  └─ Distribuidor - $D
│
└─ Level 4: BY CUSTOMER
   ├─ Shopify - $E
   ├─ Walmart - $F
   ├─ Cencosud - $G
   └─ Newrest - $H
```

**Time Filters:** Last 30 days, Last 90 days, Month, Quarter, Year

---

## 🔧 **Business Rules Layer**

### **Correcting RelBase Classification Errors**

**Problem Identified:**
- 345 invoices ($408.8M) have `channel_id = null` in RelBase
- Top 3 customers account for 96% of uncategorized sales:
  - Customer 1997707 (NEWREST) - $186M → Should be **CORPORATIVO**
  - Customer 596810 (CENCOSUD) - $160M → Should be **RETAIL**
  - Customer 2358971 (Walmart) - $45.9M → Should be **RETAIL**

**Solution: Customer → Channel Mapping Table**

We create a mapping in our platform:

```sql
-- Table: customer_channel_rules
CREATE TABLE customer_channel_rules (
  customer_id INTEGER,
  channel_id INTEGER,
  channel_name TEXT,
  rule_reason TEXT,
  created_at TIMESTAMP
);

-- Example rules:
INSERT INTO customer_channel_rules VALUES
  (1997707, 3768, 'CORPORATIVO', 'Newrest is airline catering = corporate'),
  (596810, 1459, 'RETAIL', 'Cencosud is supermarket chain = retail'),
  (2358971, 1459, 'RETAIL', 'Walmart is supermarket chain = retail');
```

**Application Logic:**

```python
# When displaying data:
if order.channel_id is None:
    # Apply business rule
    mapped_channel = customer_channel_rules.get(order.customer_id)
    if mapped_channel:
        display_channel = mapped_channel.channel_name
    else:
        display_channel = "SIN CLASIFICAR"  # Show as uncategorized
else:
    # Use RelBase channel
    display_channel = channels.get(order.channel_id)
```

This allows us to:
- ✅ Display data correctly in dashboards
- ✅ Apply executive-level business logic
- ✅ NOT modify source data in RelBase (read-only)
- ✅ Maintain audit trail of our classification rules

---

## 📈 **Example Use Cases**

### **Use Case 1: Executive wants to know top product by channel**

**In RelBase:** Can only see "BAMC_U04010 sold 50k units in 2025"

**In Our Platform:**
```
Family: Barra Low Carb Manzana Canela
Total: 60,500 units | $2.1M revenue

By Channel:
├─ E-commerce: 35,000 units (58%) | $1.2M
├─ Retail: 20,000 units (33%) | $700K
└─ Corporativo: 5,500 units (9%) | $200K

By Format (E-commerce only):
├─ 1 unidad: 30,000 units
└─ 5 unidades: 5,000 units

Top Customer (E-commerce): Shopify - $950K
```

### **Use Case 2: Analyze Walmart sales by product family**

**Query:** "Show me what Walmart bought in Q1 2025, grouped by product family"

**Our Platform:**
```
Walmart Chile S.A. (Customer 2358971)
Channel: RETAIL (auto-assigned by our rules)
Period: Q1 2025
Total: $45.9M

Top Families:
1. Barra Low Carb Manzana Canela - $12M
   ├─ Caja master (BAMC_C02810) - $10M
   └─ 1 unidad (BAMC_U04010) - $2M

2. Barra Low Carb Cranberry - $8M
   └─ Caja master - $8M

3. Keeper Mix - $6M
```

---

## 🎯 **Platform Goals**

1. **Provide executive insights** RelBase can't deliver
2. **Correct classification errors** through business rules
3. **Enable multidimensional analysis** (product family × format × channel × customer × time)
4. **Maintain data integrity** by not modifying source (RelBase)
5. **Serve as single source of truth** for visualizations and reporting

---

**Remember:** We're building a **Business Intelligence layer**, not just a data viewer. We apply business logic to make sense of imperfect source data.

---

## 🗄️ **Data Integrity Migration (November 6, 2025)**

### **Context: From CSV to Database-Driven Architecture**

Previously, the platform relied on CSV files for product mapping. We migrated to a database-driven architecture with proper `external_id` tracking across all tables.

### **Migration Completed**

#### **Phase 1: Schema Migrations ✅**

Added `external_id` and `source` columns to enable multi-source data tracking:

**Channels Table:**
```sql
ALTER TABLE channels
  ADD COLUMN external_id VARCHAR(255),
  ADD COLUMN source VARCHAR(50);

-- Mapped Relbase channels:
-- 1448 = ECOMMERCE
-- 1459 = RETAIL
-- 1544 = EMPORIOS Y CAFETERIAS
-- 3768 = CORPORATIVO
-- 3906 = DISTRIBUIDOR
```

**Products Table:** Already had `external_id` and `source` columns.

**Customers Table:** Already had `external_id` and `source` columns (2,869 customers with 99.96% coverage).

#### **Phase 2: Product Enrichment from Relbase API ✅**

**Script:** `.claude_sessions/current/enrich_products_from_relbase_api.py`

**Approach:** Fetched products from `relbase_product_mappings` table and enriched via Relbase API.

**Results:**
- Processed 341 products from `relbase_product_mappings`
- Successfully fetched 92 products from API (27%)
- Created 48 new products
- Updated 44 existing products
- 249 ANU- legacy codes not found (expected - historical references only)

#### **Phase 3: Product Enrichment from Orders ✅ (IN PROGRESS)**

**The Better Approach:** Instead of using `relbase_product_mappings`, extract products directly from existing orders.

**Why This Works Better:**
- We have 5,422 Relbase orders already in database (from 2021-2025)
- Orders contain actual sold products (relevant data only)
- Avoids ANU- legacy codes (they don't appear in real orders)
- Gets complete product data from Relbase API

**Script:** `.claude_sessions/current/enrich_products_from_orders.py`

**How It Works:**
```python
# Step 1: Get all orders with source='relbase'
orders = get_relbase_orders()  # 5,422 orders

# Step 2: For each order, fetch DTE from API
for order in orders:
    dte = api.get(f"/api/v1/dtes/{order.external_id}")
    # Extract products array from DTE
    for product in dte['products']:
        product_ids.add(product['product_id'])

# Step 3: Fetch complete product details
for product_id in unique_product_ids:
    product_data = api.get(f"/api/v1/productos/{product_id}")
    # Store in products table with:
    # - external_id = product_id_relbase
    # - source = 'relbase'
    # - sku = product_data['code']
    # - name, description, prices, category, etc.
```

**Phase 1 Results (Extract Products from Orders):**
- Orders processed: 5,422 (100%)
- Orders successfully fetched: 4,982 (91.9%)
- Orders timeout/not found: 440 (8.1% - old 2021 orders)
- **Unique product IDs extracted: 388 products** 🎯

**Phase 2 Status (Enrich Products):**
- **FAILED at product 70/388** due to schema mismatch
- Error: Tried to use `barcode` and `image_url` columns that don't exist
- **NEEDS FIX:** Update script to match actual products table schema

### **Current Database State**

**Products Table Schema (Actual):**
```sql
-- Core fields
id, external_id, source, sku, name, description, category

-- Pricing
cost_price, sale_price

-- Inventory
current_stock, min_stock, is_active

-- Product hierarchy (Grana-specific)
brand, unit, units_per_box, subfamily, format, package_type
units_per_display, displays_per_box, boxes_per_pallet
master_box_sku, master_box_name, items_per_master_box

-- Timestamps
created_at, updated_at
```

**What's Missing (that script tried to use):**
- ❌ `barcode` column
- ❌ `image_url` column

### **Next Steps**

**Immediate Task:** Fix and re-run Phase 2 of order enrichment

1. **Update script** to remove references to `barcode` and `image_url`
2. **Re-run Phase 2 only** - we already have the 388 unique product IDs
3. **Should take:** ~10-15 minutes to enrich 388 products

**Script location:** `.claude_sessions/current/enrich_products_from_orders.py`

**What needs fixing:**
```python
# REMOVE these fields from create_product() and update_product():
'barcode': product_api_data.get('barcode'),
'image_url': product_api_data.get('url_image')
```

### **Data Integrity Workflow Summary**

**The Complete Picture:**

```
┌─────────────────────────────────────────────┐
│ Step 1: Orders (Already in Database)       │
│ • 5,422 Relbase orders (source='relbase')  │
│ • From 2021-2025                           │
│ • Each has external_id = DTE ID            │
└────────────┬────────────────────────────────┘
             │
             │ Extract products
             ▼
┌─────────────────────────────────────────────┐
│ Step 2: Extract Product IDs from DTEs      │
│ • GET /api/v1/dtes/{external_id}           │
│ • Extract product_id from products array   │
│ • Result: 388 unique product IDs           │
└────────────┬────────────────────────────────┘
             │
             │ Enrich with complete data
             ▼
┌─────────────────────────────────────────────┐
│ Step 3: Fetch Full Product Details        │
│ • GET /api/v1/productos/{product_id}       │
│ • Get: code, name, price, category, etc.   │
│ • Store in products table                  │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│ Final Result: Complete Product Catalog    │
│ • All products that were sold (relevant)   │
│ • With external_id → Relbase product_id    │
│ • Ready for order analysis                 │
└─────────────────────────────────────────────┘
```

### **Files Created (Session Work)**

All in `.claude_sessions/current/`:

1. **DATABASE_MIGRATION_PLAN.md** - Initial planning
2. **migration_011_add_channels_external_id.sql** - Channels schema migration
3. **enrich_products_from_relbase_api.py** - First enrichment approach (from mappings table)
4. **ENRICHMENT_TEST_RESULTS.md** - Dry-run test results
5. **MIGRATION_EXECUTION_REPORT.md** - Phase 1 & 2 report
6. **populate_channels_external_id.sql** - Channels external_id population
7. **enrich_products_from_orders.py** - Second enrichment approach (from orders) ⬅️ **CURRENT**
8. **orders_enrichment_execution.log** - Execution log (Phase 1 complete, Phase 2 failed)
9. **DATA_INTEGRITY_MIGRATION_COMPLETE.md** - Full documentation

### **Key Learnings**

1. **Orders-based approach is superior** - Gets only products that were actually sold
2. **Old orders timeout frequently** - 2021 DTEs have poor API response times (8.1% failure rate)
3. **Database schema must match exactly** - Script failed because it assumed columns that don't exist
4. **388 unique products from 5,422 orders** - Shows product reuse across many orders
5. **Customers table already complete** - No work needed (99.96% coverage)

### **Relbase API Endpoints Reference**

```python
# Get DTE (order) with products
GET /api/v1/dtes/{dte_id}
# Returns: order info + products array with product_id, code, name, price

# Get complete product details
GET /api/v1/productos/{product_id}
# Returns: full product data including barcode, category, images, inventory

# Get customer details
GET /api/v1/clientes/{customer_id}
# Returns: name, RUT, contact info

# Get all channels
GET /api/v1/canal_ventas
# Returns: list of all channels with id and name
```

**Authentication:**
```python
headers = {
    'company': RELBASE_COMPANY_TOKEN,
    'authorization': RELBASE_USER_TOKEN
}
```

**Rate Limiting:** ~6 requests/second (enforced by script with 0.17s delay)

---

## 📊 **Vista de Auditoría - Mapeo de Columnas a Tablas**

### **Contexto**

La vista 🔍 Auditoría en http://localhost:3000/dashboard/orders muestra datos integrados de múltiples tablas de Supabase. Es importante entender qué tabla alimenta cada columna para saber qué poblar.

### **Endpoint Backend**

- **URL**: `/api/v1/audit/data`
- **Archivo**: `backend/app/api/audit.py` (línea 586+)
- **Componente Frontend**: `frontend/components/AuditView.tsx`

### **Mapeo Completo de Columnas**

| **Columna en Auditoría** | **Campo SQL** | **Tabla de Origen** | **Notas** |
|--------------------------|---------------|---------------------|-----------|
| **Pedido** | `o.external_id` | **`orders`** | Número de pedido externo (ej: DTE ID de Relbase) |
| **Fecha** | `o.order_date` | **`orders`** | Fecha del pedido |
| **Cliente** | `COALESCE(cust_direct.name, cust_channel.name, 'SIN NOMBRE')` | **`customers`** | **Dos fuentes posibles:**<br>1️⃣ `cust_direct`: Join directo vía `orders.customer_id`<br>2️⃣ `cust_channel`: Join vía `customer_channel_rules` (mapeo de canal → cliente) |
| **RUT** | `COALESCE(cust_direct.rut, cust_channel.rut)` | **`customers`** | Campo `rut` de la tabla customers |
| **Canal** | `COALESCE(ch.name, 'SIN CANAL')` | **`channels`** | Join: `channels.id = orders.channel_id` |
| **SKU Original** | `oi.product_sku` | **`order_items`** | SKU original como aparece en el pedido |
| **SKU Primario** | *(calculado)* | **CSV** `Códigos_Grana_Final.csv` | 🔧 **Post-procesamiento Python** (línea 736)<br>Función: `get_sku_primario()`<br>No está en DB, se calcula dinámicamente |
| **Familia** | `p.category` | **`products`** | Join: `products.sku = order_items.product_sku`<br>Ej: BARRAS, CRACKERS, GRANOLAS |
| **Producto** | `oi.product_name` | **`order_items`** | Nombre del producto |
| **Cantidad** | `oi.quantity` | **`order_items`** | Cantidad pedida (ej: 2 cajas) |
| **Unidades** | *(calculado)* | **CSV** `Códigos_Grana_Final.csv` | 🔧 **Post-procesamiento Python** (línea 739)<br>Función: `calculate_units()`<br>Ej: 2 cajas × 144 = 288 unidades |
| **Precio** | `ROUND(oi.subtotal / oi.quantity, 2)` | **`order_items`** | Precio unitario calculado |
| **Total** | `oi.subtotal` | **`order_items`** | Total del line item |

### **Joins del Query SQL**

```sql
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.id
LEFT JOIN products p ON p.sku = oi.product_sku
LEFT JOIN channels ch ON ch.id = o.channel_id

-- Customer Joins (Direct)
LEFT JOIN customers cust_direct
    ON cust_direct.id = o.customer_id
    AND cust_direct.source = o.source

-- Customer Joins (Channel-based mapping)
LEFT JOIN LATERAL (
    SELECT customer_external_id
    FROM customer_channel_rules ccr
    WHERE ccr.channel_external_id::text = (
        -- Extracts channel_id_relbase from JSON in customer_notes
        o.customer_notes::json->>'channel_id_relbase'
    )
    AND ccr.is_active = TRUE
) ccr_match ON true

LEFT JOIN customers cust_channel
    ON cust_channel.external_id = ccr_match.customer_external_id
    AND cust_channel.source = 'relbase'
```

### **Tablas Críticas para Poblar**

Para que la vista de Auditoría funcione completamente, necesitas poblar:

1. **`orders`** ✅ - Ya poblada (5,422 órdenes de Relbase)
   - `external_id` (DTE ID)
   - `order_date`
   - `customer_id` (si disponible)
   - `channel_id` (si disponible)
   - `source` = 'relbase'

2. **`order_items`** ⚠️ - **CRÍTICA - Necesita población**
   - `order_id` (FK a orders)
   - `product_sku` (SKU original del pedido)
   - `product_name`
   - `quantity`
   - `unit_price`
   - `subtotal`

3. **`customers`** ✅ - Ya poblada (2,869 clientes)
   - `external_id` (customer_id de Relbase)
   - `name`
   - `rut`
   - `source` = 'relbase'

4. **`channels`** ✅ - Ya poblada con `external_id`
   - `external_id` (channel_id de Relbase)
   - `name`
   - `source` = 'relbase'

5. **`products`** 🔄 - **En proceso de enriquecimiento**
   - `sku` (debe coincidir con `order_items.product_sku`)
   - `category` (Familia: BARRAS, CRACKERS, etc.)
   - `name`
   - `source` = 'relbase'

### **Datos Calculados (No en DB)**

Estas columnas **NO se pueden poblar directamente** porque se calculan en Python:

- **SKU Primario**: Se obtiene del CSV `Códigos_Grana_Final.csv` usando mapeo de SKU
- **Unidades**: Se calcula multiplicando `quantity` × factor de conversión del CSV

**Ubicación del cálculo:**
- Archivo: `backend/app/api/audit.py`
- Función SKU Primario: `get_sku_primario()` (línea ~736)
- Función Unidades: `calculate_units()` (línea ~739)

### **Próximos Pasos para Completar Auditoría**

1. ✅ **Orders** - Completo
2. ❌ **Order Items** - **PENDIENTE** - Extraer de DTEs de Relbase
3. ✅ **Customers** - Completo
4. ✅ **Channels** - Completo
5. 🔄 **Products** - En progreso (enriquecimiento activo)

**Script prioritario:** Crear `populate_order_items_from_relbase.py` para extraer los line items de cada DTE y poblar `order_items`.

---
