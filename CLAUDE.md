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
