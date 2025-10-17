# FASE 2: Clean Architecture Refactor - Implementation Plan

## 📊 Current Architecture Analysis

### What We Have (The Good News!)

Your backend is **already well-structured** with a clear layered architecture:

```
Current Backend Structure:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────────────────────────────────────┐
│  API Layer (Controllers) - app/api/                 │
│  ├── products.py (335 lines) - 6 endpoints          │
│  ├── orders.py (531 lines) - 6 endpoints ⚡N+1 fix  │
│  ├── product_mapping.py (272 lines) - 10 endpoints  │
│  ├── conversion.py                                   │
│  ├── shopify.py                                      │
│  └── mercadolibre.py                                 │
├─────────────────────────────────────────────────────┤
│  Service Layer (Business Logic) - app/services/     │
│  ├── product_mapping_service.py (561 lines)         │
│  ├── order_processing_service.py (439 lines)        │
│  ├── conversion_service.py (332 lines)              │
│  └── mercadolibre_sync_service.py (386 lines)       │
├─────────────────────────────────────────────────────┤
│  Connector Layer (External APIs) - app/connectors/  │
│  ├── shopify_connector.py                           │
│  └── mercadolibre_connector.py                      │
├─────────────────────────────────────────────────────┤
│  Data Layer - app/core/                             │
│  └── database.py (unified access) ✅                │
└─────────────────────────────────────────────────────┘
```

**Total Backend Code**: ~3,000+ lines of well-organized Python

### What's Working Well ✅

1. **Layered Architecture** - Clear separation between API, Services, and Connectors
2. **Performance Optimized** - N+1 query fix in orders endpoint (8x improvement!)
3. **Comprehensive Endpoints** - 20+ well-documented API endpoints
4. **Business Logic Isolated** - Services handle complex operations
5. **External API Abstraction** - Connectors manage Shopify/ML integration
6. **Database Centralized** - All access unified in `app/core/database.py`

### Issues Identified ⚠️

#### 1. **Database Access Inconsistency**
**Problem**: Some API files still create their own `get_db_connection()` instead of importing from `app.core.database`

**Examples**:
- `app/api/products.py:17-22` - Local `get_db_connection()` function
- `app/api/orders.py:18-23` - Duplicate function
- Each file reimplements the same logic

**Impact**: Code duplication, harder to maintain, no centralized connection pooling

---

#### 2. **Missing Domain Models**
**Problem**: No Pydantic models for database entities (Product, Order, Customer, etc.)

**Current State**:
- Database returns raw dictionaries: `{'id': 1, 'sku': 'BAKC_U04010', ...}`
- No type safety for database entities
- Only request/response models exist (e.g., `VariantMappingCreate`)

**Impact**:
- No validation of database data
- Harder to maintain as schema evolves
- No autocomplete for entity fields

---

#### 3. **No Repository Pattern**
**Problem**: Database queries scattered across services and API endpoints

**Current State**:
```python
# In API endpoint (products.py:40-93)
cursor.execute(f"""
    SELECT id, sku, name, ... FROM products
    WHERE {where_clause}
    ORDER BY name LIMIT %s OFFSET %s
""", params + [limit, offset])

# In Service (product_mapping_service.py:79-89)
cursor.execute("""
    SELECT id, sku, name, source
    FROM products
    WHERE id = %s AND is_active = true
""", (product_id,))
```

**Impact**:
- SQL queries not reusable
- Hard to test (can't mock database)
- Difficult to change database schema

---

#### 4. **Frontend Business Logic Duplication** 🔴 CRITICAL
**Problem**: 625 lines of product mapping logic duplicated between frontend and backend

**Frontend Files**:
- `/frontend/lib/product-catalog.ts` (168 lines) - Official product catalog
- `/frontend/lib/product-mapping-ml.ts` (203 lines) - ML → Catalog mapping
- `/frontend/lib/product-utils.ts` (254 lines) - Product utilities

**Backend File**:
- `/backend/app/services/product_mapping_service.py` (560 lines)

**Why This Is Bad**:
- Same logic in 2 places = 2x maintenance
- Changes must be made twice
- Frontend has business logic (should only have UI)
- No single source of truth

---

#### 5. **Missing Comprehensive Tests**
**Problem**: Test directory was empty before FASE 1

**Current State**:
- 11 test files exist (moved in FASE 1)
- Most are connection tests
- No business logic tests
- No API endpoint tests

**Impact**:
- Hard to refactor safely
- No confidence in changes
- Bugs discovered in production

---

#### 6. **Inconsistent Error Handling**
**Problem**: Each endpoint handles errors differently

**Examples**:
```python
# Some use try/except with HTTPException
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Others just let exceptions bubble up
# No logging
# No error context
```

---

## 🎯 FASE 2: Proposed Refactoring

### Goals
1. **Eliminate code duplication** (especially frontend business logic)
2. **Implement Repository Pattern** for clean data access
3. **Add Domain Models** with Pydantic for type safety
4. **Standardize database access** across all files
5. **Add comprehensive tests** for all layers
6. **Improve error handling** with proper logging

### New Architecture (Clean Architecture)

```
Target Backend Structure:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────────────────────────────────────┐
│  API Layer (Controllers) - app/api/                 │
│  - Handle HTTP requests/responses                   │
│  - Validate input with Pydantic                     │
│  - Call service layer                               │
│  - Return formatted responses                       │
├─────────────────────────────────────────────────────┤
│  Service Layer (Business Logic) - app/services/     │
│  - Orchestrate business operations                  │
│  - Use repositories for data access                 │
│  - Implement business rules                         │
│  - Return domain models                             │
├─────────────────────────────────────────────────────┤
│  Repository Layer - app/repositories/ ✨ NEW        │
│  - All database queries                             │
│  - CRUD operations                                  │
│  - Query builders                                   │
│  - Return domain models                             │
├─────────────────────────────────────────────────────┤
│  Domain Layer - app/domain/ ✨ NEW                  │
│  - Business entities (Product, Order, Customer)     │
│  - Pydantic models                                  │
│  - Business rules and validations                   │
│  - Official product catalog ✨                      │
├─────────────────────────────────────────────────────┤
│  Connector Layer - app/connectors/                  │
│  - External API integrations                        │
│  - Shopify, MercadoLibre                           │
├─────────────────────────────────────────────────────┤
│  Core Layer - app/core/                             │
│  - database.py (unified access)                     │
│  - config.py (settings)                             │
│  - logging.py ✨ NEW                                │
└─────────────────────────────────────────────────────┘
```

### Implementation Steps

#### Step 1: Create Domain Models (app/domain/)
```python
# app/domain/product.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Product(BaseModel):
    """Product domain model - represents a product in our system"""
    id: int
    external_id: Optional[str]
    source: str
    sku: str
    name: str
    description: Optional[str]
    category: Optional[str]
    brand: Optional[str]
    unit: Optional[str]

    # Conversion info
    units_per_display: Optional[int]
    displays_per_box: Optional[int]
    boxes_per_pallet: Optional[int]

    # Pricing and stock
    cost_price: Optional[float]
    sale_price: Optional[float]
    current_stock: int = 0
    min_stock: int = 0

    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True  # Allow creation from ORM objects

# Similar models for:
# - Order
# - Customer
# - OrderItem
# - Channel
# - ProductVariant
# - ChannelEquivalent
```

#### Step 2: Create Repository Layer (app/repositories/)
```python
# app/repositories/product_repository.py
from typing import List, Optional
from app.domain.product import Product
from app.core.database import get_db_connection_dict

class ProductRepository:
    """Repository for Product data access"""

    def find_by_id(self, product_id: int) -> Optional[Product]:
        """Find product by ID"""
        conn = get_db_connection_dict()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM products WHERE id = %s
        """, (product_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        return Product(**row) if row else None

    def find_by_sku(self, sku: str) -> Optional[Product]:
        """Find product by SKU"""
        # Implementation
        pass

    def find_all(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Product]:
        """Find products with filters"""
        # Implementation
        pass

    def count(self, **filters) -> int:
        """Count products matching filters"""
        pass

    def create(self, product: Product) -> Product:
        """Create new product"""
        pass

    def update(self, product: Product) -> Product:
        """Update existing product"""
        pass

# Similar repositories for:
# - OrderRepository
# - CustomerRepository
# - ProductMappingRepository
```

#### Step 3: Refactor Services to Use Repositories
```python
# app/services/product_mapping_service.py (refactored)
from app.repositories.product_repository import ProductRepository
from app.repositories.product_mapping_repository import ProductMappingRepository
from app.domain.product import Product

class ProductMappingService:
    def __init__(self):
        self.product_repo = ProductRepository()
        self.mapping_repo = ProductMappingRepository()

    def detect_packaging_variants(self, product_id: int) -> List[ProductVariant]:
        """Detect potential packaging variants"""
        # Get product from repository
        product = self.product_repo.find_by_id(product_id)
        if not product or product.source != 'shopify':
            return []

        # Business logic here
        parsed = self.parse_shopify_sku(product.sku)
        if not parsed or not parsed['is_base']:
            return []

        # Find variants using repository
        variants = self.product_repo.find_variants(
            base_code=parsed['base_code'],
            type_code=parsed['type_code']
        )

        # Process and return
        return self._calculate_variant_confidence(product, variants)
```

#### Step 4: Refactor API Endpoints
```python
# app/api/products.py (refactored)
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from app.domain.product import Product
from app.services.product_service import ProductService
from app.api.schemas.product import ProductListResponse, ProductResponse

router = APIRouter()

def get_product_service() -> ProductService:
    """Dependency injection for ProductService"""
    return ProductService()

@router.get("/", response_model=ProductListResponse)
async def get_products(
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    service: ProductService = Depends(get_product_service)
):
    """Get products with filters - NO database queries here!"""

    # Call service layer (which uses repository)
    products = service.get_products(
        source=source,
        category=category,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset
    )

    total = service.count_products(
        source=source,
        category=category,
        is_active=is_active,
        search=search
    )

    return ProductListResponse(
        status="success",
        total=total,
        limit=limit,
        offset=offset,
        count=len(products),
        data=products
    )
```

#### Step 5: Move Product Catalog to Backend Domain
```python
# app/domain/catalog.py ✨ NEW
"""
Official Grana Product Catalog
Single Source of Truth for all product mappings
"""
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class OfficialProduct:
    """Official product definition from Grana"""
    sku: str
    name: str
    category: str
    unit_description: str
    units_per_display: int
    displays_per_box: int
    boxes_per_pallet: int

    @property
    def units_per_box(self) -> int:
        return self.units_per_display * self.displays_per_box

    @property
    def units_per_pallet(self) -> int:
        return self.units_per_box * self.boxes_per_pallet

# Official catalog (moved from frontend)
OFFICIAL_CATALOG: Dict[str, OfficialProduct] = {
    "BAKC_U04010": OfficialProduct(
        sku="BAKC_U04010",
        name="Barra Keto Cacao",
        category="BARRAS",
        unit_description="1 unidad",
        units_per_display=12,
        displays_per_box=12,
        boxes_per_pallet=20
    ),
    # ... all other products
}

# Expose as API endpoint
@router.get("/api/v1/catalog")
async def get_official_catalog():
    """Get official product catalog"""
    return [
        {
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "unit_description": p.unit_description,
            "conversions": {
                "units_per_display": p.units_per_display,
                "displays_per_box": p.displays_per_box,
                "boxes_per_pallet": p.boxes_per_pallet,
                "units_per_box": p.units_per_box,
                "units_per_pallet": p.units_per_pallet
            }
        }
        for p in OFFICIAL_CATALOG.values()
    ]
```

#### Step 6: Simplify Frontend (Remove Duplication)
```typescript
// frontend/lib/api/catalog.ts ✨ NEW
import { api } from './client'

export interface OfficialProduct {
  sku: string
  name: string
  category: string
  unit_description: string
  conversions: {
    units_per_display: number
    displays_per_box: number
    boxes_per_pallet: number
    units_per_box: number
    units_per_pallet: number
  }
}

export async function getOfficialCatalog(): Promise<OfficialProduct[]> {
  const response = await api.get('/catalog')
  return response.data
}

// DELETE: frontend/lib/product-catalog.ts (168 lines)
// DELETE: frontend/lib/product-mapping-ml.ts (203 lines)
// SIMPLIFY: frontend/lib/product-utils.ts (keep only UI utilities)
```

#### Step 7: Add Comprehensive Tests
```python
# tests/test_repositories/test_product_repository.py
import pytest
from app.repositories.product_repository import ProductRepository
from app.domain.product import Product

def test_find_by_id_existing_product(db_connection):
    """Test finding an existing product by ID"""
    repo = ProductRepository()
    product = repo.find_by_id(1)

    assert product is not None
    assert isinstance(product, Product)
    assert product.id == 1
    assert product.sku is not None

def test_find_by_sku(db_connection):
    """Test finding product by SKU"""
    repo = ProductRepository()
    product = repo.find_by_sku("BAKC_U04010")

    assert product is not None
    assert product.sku == "BAKC_U04010"

# tests/test_services/test_product_service.py
def test_get_products_with_filters(mock_product_repo):
    """Test product service with filters"""
    service = ProductService(product_repo=mock_product_repo)

    mock_product_repo.find_all.return_value = [
        Product(id=1, sku="BAKC_U04010", name="Test", ...)
    ]

    products = service.get_products(source="shopify")

    assert len(products) == 1
    assert products[0].source == "shopify"
    mock_product_repo.find_all.assert_called_once()
```

#### Step 8: Add Logging and Error Handling
```python
# app/core/logging.py ✨ NEW
import logging
from functools import wraps

logger = logging.getLogger("grana_api")

def log_errors(func):
    """Decorator to log exceptions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise
    return wrapper

# Use in API endpoints
@router.get("/products")
@log_errors
async def get_products(...):
    # Implementation
    pass
```

---

## 📈 Expected Benefits

### Code Quality
- ✅ **50% less code** by removing frontend duplication (625 lines → 0 lines frontend business logic)
- ✅ **Single source of truth** for product catalog and mappings
- ✅ **Type safety** with Pydantic domain models
- ✅ **Testable** with repository pattern (easy to mock)

### Maintainability
- ✅ **Easy to change database** (only update repositories)
- ✅ **Easy to add features** (clear layers)
- ✅ **Easy to find code** (organized structure)
- ✅ **Easy to onboard** (clear architecture)

### Performance
- ✅ **Reusable queries** (no duplication)
- ✅ **Optimized queries** (centralized in repositories)
- ✅ **Better caching** (can cache repository results)

### Testing
- ✅ **100% test coverage** possible
- ✅ **Fast tests** (mock repositories)
- ✅ **Confidence in refactoring**

---

## 🚀 Implementation Plan

### Phase 1: Foundation (Days 1-2)
1. Create `app/domain/` with all domain models
2. Create `app/repositories/` structure
3. Implement ProductRepository
4. Add logging infrastructure

### Phase 2: Refactor Core (Days 3-5)
5. Refactor ProductService to use repositories
6. Refactor Product API endpoints
7. Add comprehensive tests
8. Update imports across all files

### Phase 3: Expand (Days 6-8)
9. Implement OrderRepository
10. Refactor OrderService and OrderProcessingService
11. Refactor Order API endpoints
12. Add order tests

### Phase 4: Product Mapping (Days 9-10)
13. Implement ProductMappingRepository
14. Refactor ProductMappingService
15. Move official catalog to backend (app/domain/catalog.py)
16. Create `/api/v1/catalog` endpoint
17. Add product mapping tests

### Phase 5: Frontend Cleanup (Days 11-12)
18. Update frontend to use `/api/v1/catalog` endpoint
19. Delete `product-catalog.ts` (168 lines)
20. Delete `product-mapping-ml.ts` (203 lines)
21. Simplify `product-utils.ts` (keep only UI utilities)
22. Test frontend still works

### Phase 6: Polish (Days 13-14)
23. Add error logging to all endpoints
24. Update API documentation
25. Performance testing
26. Deploy to Railway

---

## ✅ Success Criteria

1. **Zero frontend business logic** - All moved to backend APIs
2. **Repository pattern implemented** - All database access through repositories
3. **Domain models exist** - Pydantic models for all entities
4. **80%+ test coverage** - Comprehensive tests for all layers
5. **No duplicate code** - Database access unified
6. **Documentation complete** - All APIs documented

---

## 🤔 Questions for You

Before I start implementing FASE 2:

1. **Priority**: Which layer should I start with?
   - [ ] Domain models first (foundations)
   - [ ] Repository pattern first (data access)
   - [ ] Frontend cleanup first (visible impact)

2. **Scope**: Should I refactor all at once or one module at a time?
   - [ ] All modules in parallel (faster but riskier)
   - [ ] Products module first, then Orders, then Mapping (safer)

3. **Testing**: How much test coverage do you want?
   - [ ] Basic tests (main happy paths)
   - [ ] Comprehensive tests (80%+ coverage)

4. **Frontend**: When should I clean up the frontend duplication?
   - [ ] After backend refactor is complete
   - [ ] In parallel with backend work

5. **Breaking changes**: Are you okay with me changing the API response format for consistency?
   - [ ] Yes, consistency is more important
   - [ ] No, maintain exact compatibility

**Ready to proceed with FASE 2?** Let me know your preferences and I'll start implementing! 🚀
