# Database Table Usage Map

> **Updated:** 2026-01-13
> **Purpose:** Map frontend views to backend APIs to database tables/views

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                              │
│   /dashboard, /analytics, /orders, /warehouse-inventory, etc.          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ fetch() calls
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                               │
│   /api/v1/orders, /api/v1/sales-analytics, /api/v1/warehouses, etc.    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ SQL queries
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATABASE (PostgreSQL/Supabase)                     │
│                                                                         │
│   TABLES (17):              VIEWS (4 used):        MATERIALIZED VIEW:   │
│   orders                    inventory_planning_facts   sales_facts_mv   │
│   order_items               warehouse_stock_by_lot                      │
│   customers                 v_product_conversion                        │
│   channels                                                              │
│   products                  VIEWS (4 unused):                           │
│   product_catalog           inventory_general                           │
│   sku_mappings              v_low_stock_products                        │
│   warehouses                v_orders_full                               │
│   warehouse_stock           v_sales_by_channel                          │
│   product_inventory_settings                                            │
│   users                     DELETED TABLES (Migration 029):             │
│   api_keys                  customer_channel_rules (→ customers)        │
│   api_credentials           product_variants                            │
│   sync_logs                 channel_equivalents                         │
│   alerts                    inventory_movements                         │
│   orders_audit              dim_date, ml_tokens, etc.                   │
│   manual_corrections                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Summary

### Tables (14 active)

| Category | Tables | Status |
|----------|--------|--------|
| **Core Business** | `orders`, `order_items`, `customers`, `channels`, `products` | ✅ Heavily used |
| **Product Config** | `product_catalog`, `sku_mappings` | ✅ Heavily used |
| **Inventory** | `warehouses`, `warehouse_stock`, `product_inventory_settings` | ✅ Used |
| **Auth/System** | `users`, `api_credentials`, `sync_logs` | ✅ Backend only |
| **Audit Trail** | `orders_audit` | ✅ Trigger-based, compliance |

### Views & Materialized Views

| View | Type | Status | Used By |
|------|------|--------|---------|
| `sales_facts_mv` | Materialized | ✅ USED | Dashboard, Sales Analytics, Orders, Production Planning |
| `inventory_planning_facts` | View | ✅ USED | Production Planning, Warehouse Inventory |
| `warehouse_stock_by_lot` | View | ✅ USED | Warehouse by Lot, Expiration Summary |
| `v_product_conversion` | View | ✅ USED | Conversion Service (backend) |
| `inventory_general` | View | ❌ UNUSED | Delete candidate |
| `v_low_stock_products` | View | ❌ UNUSED | Delete candidate |
| `v_orders_full` | View | ❌ UNUSED | Delete candidate |
| `v_sales_by_channel` | View | ❌ UNUSED | Delete candidate |

### Deleted Tables (Migration 029)

| Table | Replacement |
|-------|-------------|
| `customer_channel_rules` | `customers.assigned_channel_id` |
| `product_variants` | `product_catalog` families |
| `channel_equivalents` | Never used |
| `channel_product_equivalents` | Never used |
| `relbase_product_mappings` | `sku_mappings` |
| `dim_date` | Not needed |
| `ml_tokens` | `api_credentials` |
| `inventory_movements` | No UI, low usage |

### Deleted Tables (Migration 031)

| Table | Reason |
|-------|--------|
| `api_keys` | Incomplete feature - `verify_api_key()` exists but never called |
| `alerts` | Trigger writes but never queried, no UI |
| `manual_corrections` | Zero usage, redundant with `orders_audit` |

---

## Part 1: Frontend Pages → API → Database

### 1. Dashboard (Main)

**URL:** `/dashboard`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/orders/dashboard/executive-kpis` | `sales_facts_mv` |
| `GET /api/v1/sales-analytics?group_by=channel` | `sales_facts_mv` |
| `GET /api/v1/sales-analytics?group_by=category` | `sales_facts_mv` |
| `GET /api/v1/sales-analytics?group_by=customer` | `sales_facts_mv` |
| `GET /api/v1/analytics/quarterly-breakdown` | `sales_facts_mv` |

---

### 2. Analytics

**URL:** `/dashboard/analytics`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/channels` | `channels` |
| `GET /api/v1/product-mapping/catalog` | `product_catalog` |
| `GET /api/v1/orders/` | `orders`, `order_items`, `products` |

---

### 3. Orders (includes Desglose tab)

**URL:** `/dashboard/orders`

This page has **two tabs**:
- **📦 Pedidos** - Orders table
- **📊 Desglose Pedidos** - Audit/breakdown view (uses AuditView component)

| API Endpoint | Database Tables/Views | Tab |
|--------------|----------------------|-----|
| `GET /api/v1/orders/` | `orders`, `order_items`, `customers`, `channels` | Pedidos |
| `GET /api/v1/orders/stats` | `orders`, `order_items` | Pedidos |
| `GET /api/v1/orders/analytics` | `sales_facts_mv` | Pedidos |
| `GET /api/v1/audit/filters` | `orders`, `customers`, `channels` | Desglose |
| `GET /api/v1/audit/summary` | `orders`, `order_items`, `products`, `product_catalog` | Desglose |
| `GET /api/v1/audit/data` | `orders`, `order_items`, `customers`, `channels`, `sku_mappings`, `product_catalog` | Desglose |

**Note:** The `/dashboard/audit` page exists but is **NOT in navigation** (orphan page).

---

### 4. Product Catalog

**URL:** `/dashboard/product-catalog`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/product-catalog/` | `product_catalog` |
| `GET /api/v1/product-catalog/stats` | `product_catalog` |
| `POST /api/v1/product-catalog/` | `product_catalog` |
| `PATCH /api/v1/product-catalog/{id}` | `product_catalog` |

---

### 5. Product Mapping

**URL:** `/dashboard/product-mapping`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/product-mapping/catalog` | `product_catalog`, `sku_mappings` |
| `GET /api/v1/product-mapping/families/hierarchical` | `product_catalog` |

---

### 6. Production Planning

**URL:** `/dashboard/production-planning`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/inventory-planning/categories` | `product_catalog` |
| `GET /api/v1/inventory-planning/production-recommendations` | `inventory_planning_facts`, `sales_facts_mv`, `warehouse_stock`, `product_inventory_settings` |

---

### 7. Sales Analytics

**URL:** `/dashboard/sales-analytics`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/sales-analytics/filter-options` | `sales_facts_mv` |
| `GET /api/v1/sales-analytics` | `sales_facts_mv` |
| `GET /api/v1/audit/filters` | `orders`, `channels`, `customers` |

---

### 8. SKU Mappings

**URL:** `/dashboard/sku-mappings`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/sku-mappings/` | `sku_mappings`, `product_catalog` |
| `GET /api/v1/sku-mappings/order-skus` | `order_items`, `orders`, `sku_mappings`, `product_catalog` |
| `GET /api/v1/sku-mappings/catalog-skus` | `product_catalog` |
| `POST /api/v1/sku-mappings/` | `sku_mappings` |
| `PATCH /api/v1/sku-mappings/{id}` | `sku_mappings` |

---

### 9. Warehouse Inventory (General)

**URL:** `/dashboard/warehouse-inventory`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/warehouse-inventory/general` | `warehouse_stock`, `products`, `warehouses`, `product_catalog`, `product_inventory_settings`, `sales_facts_mv` |
| `GET /api/v1/products/minimum-stock-suggestions` | `sales_facts_mv` |

---

### 10. Warehouse Inventory (By Lot)

**URL:** `/dashboard/warehouse-inventory/by-warehouse`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/warehouses` | `warehouses` |
| `GET /api/v1/warehouse-inventory/expiration-summary` | `warehouse_stock_by_lot` |
| `GET /api/v1/warehouse-inventory/warehouse/{code}` | `warehouse_stock_by_lot`, `warehouse_stock`, `products` |
| `POST /api/v1/warehouse-inventory/upload` | `warehouse_stock`, `warehouses`, `products` |

---

### 11. Users

**URL:** `/dashboard/users`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/users` | `users` |
| `POST /api/users` | `users` |
| `PATCH /api/users/{id}` | `users` |

---

### 12. Profile

**URL:** `/dashboard/profile`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `POST /api/auth/change-password` | `users` |

---

### 13. Debug Mapping

**URL:** `/dashboard/debug-mapping`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| `GET /api/v1/debug-mapping/debug/sku/{sku}` | `products`, `product_catalog`, `sku_mappings` |
| `GET /api/v1/debug-mapping/debug/orders` | `orders`, `order_items`, `customers`, `channels` |
| `GET /api/v1/debug-mapping/debug/unmapped-skus` | `order_items`, `orders` |

---

### 14. Login

**URL:** `/login`

| API Endpoint | Database Tables/Views |
|--------------|----------------------|
| NextAuth session | `users` |

---

## Part 2: Backend API Endpoints

### Audit Endpoints (`/api/v1/audit/*`)

**Used by:** Orders page (Desglose tab), Sales Analytics (filters only)

| Endpoint | Tables Used | Notes |
|----------|-------------|-------|
| `GET /audit/filters` | `orders`, `customers`, `channels` | Get filter options |
| `GET /audit/summary` | `orders`, `order_items`, `products`, `product_catalog` | Summary statistics |
| `GET /audit/data` | `orders`, `order_items`, `customers`, `channels`, `sku_mappings`, `product_catalog` | Main data endpoint |
| `GET /audit/export` | Same as data | ❌ NOT USED in frontend |

**Channel Fallback Logic (Fixed 2026-01-13):**
```sql
-- Uses customers.assigned_channel_id for channel fallback
LEFT JOIN channels ch_assigned
    ON ch_assigned.external_id = cust_direct.assigned_channel_id::text
    AND ch_assigned.source = 'relbase'
```

### Sales Analytics Realtime (`/api/v1/sales-analytics-realtime`)

**Used by:** Potentially frontend, same logic as audit

| Endpoint | Tables Used |
|----------|-------------|
| `GET /` | `orders`, `order_items`, `products`, `channels`, `customers` |

---

## Part 3: Database Objects Detail

### Tables by Usage Frequency

| Table | Frontend Pages | Backend Services | Importance |
|-------|---------------|------------------|------------|
| `orders` | 6 pages | sync, audit | Critical |
| `order_items` | 6 pages | sync, audit | Critical |
| `product_catalog` | 6 pages | conversion, mapping | Critical |
| `customers` | 4 pages | sync, audit | High |
| `channels` | 4 pages | sync, audit | High |
| `sku_mappings` | 4 pages | conversion | High |
| `products` | 4 pages | sync | Medium |
| `warehouse_stock` | 2 pages | inventory | Medium |
| `warehouses` | 2 pages | inventory | Medium |
| `product_inventory_settings` | 2 pages | inventory | Medium |
| `users` | 3 pages | auth | Medium |
| `api_credentials` | 0 pages | MercadoLibre OAuth | Backend only |
| `api_keys` | 0 pages | API auth | Backend only |
| `sync_logs` | 0 pages | Sync tracking | Backend only |
| `alerts` | 0 pages | - | ⚠️ No UI |
| `orders_audit` | 0 pages | - | ⚠️ No UI |
| `manual_corrections` | 0 pages | - | ⚠️ No UI |

### Views and Materialized Views

| View | Type | Source Tables | Purpose |
|------|------|---------------|---------|
| `sales_facts_mv` | Materialized | orders, order_items, product_catalog, channels, customers | Pre-aggregated sales for fast analytics |
| `inventory_planning_facts` | View | warehouse_stock, products, warehouses | Inventory planning with expiration |
| `warehouse_stock_by_lot` | View | warehouse_stock, products, warehouses | Lot-level inventory tracking |
| `v_product_conversion` | View | product_catalog | Product conversion factors |

### Views to DELETE (Migration 030)

| View | Reason | Analysis |
|------|--------|----------|
| `inventory_general` | `warehouses.py` uses custom CTEs | Backend: function name only, no view query |
| `v_low_stock_products` | `ProductRepository.find_low_stock()` used | Backend: custom SQL in chat tools |
| `v_orders_full` | `OrderRepository` uses dynamic queries | No usage anywhere |
| `v_sales_by_channel` | Chat tool builds custom SQL with order_items | View lacks order_items joins |

---

## Part 4: Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL APIs                                 │
│              (Relbase, Shopify, MercadoLibre, Chipax, Lokal)           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ sync_service.py
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         OLTP TABLES (Transactional)                     │
│                                                                         │
│   ┌──────────┐    ┌─────────────┐    ┌──────────┐    ┌───────────┐    │
│   │ customers│◄───│   orders    │───►│ channels │    │ products  │    │
│   │  + assigned    └──────┬──────┘    └──────────┘    └─────┬─────┘    │
│   │  _channel_id │        │                                  │          │
│   └──────────┘            ▼                                  │          │
│                    ┌─────────────┐                          │          │
│                    │ order_items │◄─────────────────────────┘          │
│                    └─────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ JOIN + Enrichment
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CONFIG TABLES (Source of Truth)                    │
│                                                                         │
│        ┌─────────────────┐              ┌──────────────┐               │
│        │ product_catalog │◄────────────►│ sku_mappings │               │
│        │  (SKUs, conv.)  │              │   (rules)    │               │
│        └─────────────────┘              └──────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Materialization
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         OLAP LAYER (Analytics)                          │
│                                                                         │
│                      ┌────────────────┐                                 │
│                      │ sales_facts_mv │  ◄── Pre-computed, fast        │
│                      └────────────────┘                                 │
│                              │                                          │
│              ┌───────────────┼───────────────┐                         │
│              ▼               ▼               ▼                         │
│        ┌──────────┐   ┌───────────┐   ┌──────────────┐                │
│        │Dashboard │   │  Sales    │   │  Production  │                │
│        │  KPIs    │   │ Analytics │   │  Planning    │                │
│        └──────────┘   └───────────┘   └──────────────┘                │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      INVENTORY LAYER (Separate)                         │
│                                                                         │
│   ┌────────────┐    ┌─────────────────┐    ┌────────────────────┐     │
│   │ warehouses │───►│ warehouse_stock │───►│warehouse_stock_by_ │     │
│   └────────────┘    └─────────────────┘    │      lot (VIEW)    │     │
│                              │              └────────────────────┘     │
│                              ▼                                         │
│                     ┌────────────────────┐                            │
│                     │inventory_planning_ │                            │
│                     │   facts (VIEW)     │                            │
│                     └────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 5: Matrix - Frontend Page ↔ Table

| Table | Dashboard | Analytics | Orders | Product Catalog | Product Mapping | Production Planning | Sales Analytics | SKU Mappings | Warehouse Inv | Users |
|-------|:---------:|:---------:|:------:|:---------------:|:---------------:|:------------------:|:---------------:|:------------:|:-------------:|:-----:|
| `orders` | via MV | ✓ | ✓ | - | - | - | via MV | - | - | - |
| `order_items` | via MV | ✓ | ✓ | - | - | - | via MV | ✓ | - | - |
| `customers` | via MV | - | ✓ | - | - | - | via MV | - | - | - |
| `channels` | via MV | ✓ | ✓ | - | - | - | via MV | - | - | - |
| `products` | - | ✓ | - | - | ✓ | - | - | - | ✓ | - |
| `product_catalog` | via MV | ✓ | ✓ | ✓ | ✓ | ✓ | via MV | ✓ | ✓ | - |
| `sku_mappings` | via MV | - | ✓ | - | ✓ | - | via MV | ✓ | - | - |
| `warehouses` | - | - | - | - | - | - | - | - | ✓ | - |
| `warehouse_stock` | - | - | - | - | - | ✓ | - | - | ✓ | - |
| `product_inventory_settings` | - | - | - | - | - | ✓ | - | - | ✓ | - |
| `users` | - | - | - | - | - | - | - | - | - | ✓ |
| `sales_facts_mv` | ✓ | - | ✓ | - | - | ✓ | ✓ | - | ✓ | - |

**Legend:**
- ✓ = Direct table access
- via MV = Access through `sales_facts_mv`
- `-` = Not used

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-13 | Created migration 031 to delete api_keys, alerts, manual_corrections tables |
| 2026-01-13 | Multi-agent analysis: api_credentials KEEP (OAuth), sync_logs KEEP (active), orders_audit KEEP (compliance) |
| 2026-01-13 | Removed ManualCorrection ORM model and updated test_connection.py |
| 2026-01-13 | Updated load-remote-data.sh to exclude deleted tables (now 14 tables) |
| 2026-01-13 | Created migration 030 to delete 4 unused views (inventory_general, v_low_stock_products, v_orders_full, v_sales_by_channel) |
| 2026-01-13 | Deep multi-agent analysis confirmed all 4 views are safe to delete |
| 2026-01-13 | Fixed audit.py and sales_analytics_realtime.py - removed customer_channel_rules |
| 2026-01-13 | Added migration step to move customer_channel_rules → customers.assigned_channel_id |
| 2026-01-13 | Added complete frontend → API → database mapping |
| 2026-01-13 | Identified 4 unused views for deletion |
| 2026-01-12 | Initial document created |
