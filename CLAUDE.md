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
