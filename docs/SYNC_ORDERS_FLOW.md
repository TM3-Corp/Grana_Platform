# Sync Orders Flow - Deep Technical Documentation

> Complete documentation of how orders are synced from Relbase to the Grana Platform database.

---

## Table of Contents

1. [Flow Overview](#flow-overview)
2. [Step-by-Step Flow with Tables](#step-by-step-flow-with-tables)
3. [Known Issues & Questions](#known-issues--questions)
4. [What is sales_facts_mv?](#what-is-sales_facts_mv)
5. [Next Flows After Sync](#next-flows-after-sync)

---

## Flow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYNC ORDERS FLOW                             │
│                                                                 │
│  UptimeRobot (every 15 min)                                     │
│        │                                                        │
│        ▼                                                        │
│  POST /api/v1/sync/all                                          │
│        │                                                        │
│        ▼                                                        │
│  sync_sales_from_relbase()                                      │
│        │                                                        │
│        ├──► Step 1: Determine date range (orders table)         │
│        ├──► Step 2: Pre-fetch channels (Relbase API)            │
│        ├──► Step 3: Fetch DTE list (Relbase API, paginated)     │
│        │                                                        │
│        │    FOR EACH DTE:                                       │
│        ├──► Step 4: Check if exists (orders table)              │
│        ├──► Step 5: Fetch DTE detail (Relbase API)              │
│        ├──► Step 6: Resolve channel (channels table)            │
│        ├──► Step 7: Resolve customer (customers table)          │
│        ├──► Step 8: INSERT order (orders table)                 │
│        ├──► Step 9: INSERT order_items (order_items table)      │
│        │                                                        │
│        ├──► Step 10: Cleanup missing references                 │
│        ├──► Step 11: COMMIT transaction                         │
│        ├──► Step 12: REFRESH sales_facts_mv                     │
│        └──► Step 13: Log to sync_logs                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Flow with Tables

### Step 1: Determine Date Range

**Table:** `orders`
**Operation:** SELECT

```sql
SELECT MAX(order_date) FROM orders WHERE source = 'relbase'
```

**Logic:**
- If explicit override → use `date_from_override`, `date_to_override`
- If `force_full=true` → Jan 1 of current year to today
- If orders exist → `(last_order_date - days_back)` to today
- If no orders → `(today - 30 days)` to today

---

### Step 2: Pre-fetch Channels

**Table:** None (API call, cached in memory)
**API:** `GET https://api.relbase.cl/api/v1/canal_ventas`

**Response cached as:**
```python
relbase_channels_cache = {
    3768: "CORPORATIVO",
    1448: "ECOMMERCE",
    2013: "MERCADO LIBRE",
    ...
}
```

---

### Step 3: Fetch DTE List (Paginated)

**Table:** None (API call)
**API:** `GET https://api.relbase.cl/api/v1/dtes`

**Parameters:**
- `type_document`: 33 (Factura) or 39 (Boleta)
- `start_date`, `end_date`: Date range
- `page`, `per_page`: Pagination (100 per page)

**Rate limit:** 0.17s delay between pages

---

### Step 4: Check If Order Exists

**Table:** `orders`
**Operation:** SELECT

```sql
SELECT id FROM orders
WHERE external_id = '{dte_id}' AND source = 'relbase'
```

**Decision:**
- If EXISTS → `orders_updated++` → SKIP to next DTE
- If NOT EXISTS → Continue to Step 5

---

### Step 5: Fetch DTE Detail

**Table:** None (API call)
**API:** `GET https://api.relbase.cl/api/v1/dtes/{dte_id}`

**Key fields extracted:**
- `folio` → order_number
- `customer_id` → used to resolve customer
- `channel_id` → used to resolve channel
- `amount_total`, `amount_neto`, `amount_iva` → totals
- `sii_status` → invoice_status
- `products[]` → line items

**Rate limit:** 0.17s delay after each detail fetch

---

### Step 6: Resolve Channel (4 Paths)

**Tables:** `channels`, `customer_channel_rules`

#### Path A: Check database
```sql
SELECT id FROM channels
WHERE external_id = '{channel_id_relbase}' AND source = 'relbase'
```
If found → use `channel_id` → DONE

#### Path B: Create from cache
```sql
INSERT INTO channels (code, name, external_id, source, is_active, created_at)
VALUES ('{code}', '{name}', '{external_id}', 'relbase', true, NOW())
ON CONFLICT (code) DO UPDATE SET ...
RETURNING id
```

#### Path C: Apply customer_channel_rule
```sql
SELECT c.id, ccr.channel_name
FROM customer_channel_rules ccr
JOIN channels c ON c.external_id = ccr.channel_external_id::text
WHERE ccr.customer_external_id = '{customer_id_relbase}'
  AND ccr.is_active = true
```

#### Path D: No channel found → `channel_id = NULL`

---

### Step 7: Resolve Customer (2 Paths)

**Tables:** `customers`

#### Path A: Check database
```sql
SELECT id FROM customers
WHERE external_id = '{customer_id_relbase}' AND source = 'relbase'
```

#### Path B: Fetch from API & Create
**API:** `GET https://api.relbase.cl/api/v1/clientes/{customer_id}`

```sql
INSERT INTO customers
(external_id, source, name, rut, email, phone, address, created_at)
VALUES ('{id}', 'relbase', '{name}', '{rut}', '{email}', '{phone}', '{address}', NOW())
RETURNING id
```

**Rate limit:** 0.15s delay before API call, 3 retries with backoff

---

### Step 8: INSERT Order

**Table:** `orders`
**Operation:** INSERT

```sql
INSERT INTO orders
(external_id, order_number, source, channel_id, customer_id,
 subtotal, tax_amount, total, status, payment_status,
 invoice_status, order_date, invoice_number, invoice_type, invoice_date,
 customer_notes, created_at)
VALUES (
    '{dte_id}',           -- external_id
    '{folio}',            -- order_number
    'relbase',            -- source (always)
    {channel_id},         -- resolved or NULL
    {customer_id},        -- resolved or NULL
    {amount_neto},        -- subtotal
    {amount_iva},         -- tax_amount
    {amount_total},       -- total
    'completed',          -- status (always for DTEs)
    'paid',               -- payment_status (always for DTEs)
    '{sii_status}',       -- invoice_status
    '{order_date}',
    '{folio}',            -- invoice_number
    'factura'/'boleta',   -- invoice_type
    '{order_date}',       -- invoice_date
    '{JSON with relbase IDs}',  -- customer_notes
    NOW()
)
RETURNING id
```

**customer_notes JSON:**
```json
{
  "relbase_id": 123456,
  "customer_id_relbase": 789,
  "channel_id_relbase": 3768
}
```

---

### Step 9: INSERT Order Items

**Table:** `order_items`
**Operation:** INSERT (for each product in DTE)

```sql
INSERT INTO order_items
(order_id, product_id, product_sku, product_name,
 quantity, unit_price, subtotal, total, created_at)
VALUES (
    {order_id},           -- from Step 8
    NULL,                 -- product_id NOT MAPPED
    '{product_code}',     -- RAW Relbase code
    '{product_name}',
    {quantity},
    {price},
    {subtotal},
    {subtotal},
    NOW()
)
```

**CRITICAL DESIGN DECISION:**
- `product_id = NULL` - Products are NOT linked to products table at sync time
- `product_sku` stores the RAW Relbase code (e.g., `ANU-GRLC_D26010`)
- SKU mapping happens at DISPLAY TIME via `ProductCatalogService`

---

### Step 10: Cleanup Missing References

**Tables:** `orders`, `customers`
**Operations:** SELECT, INSERT, UPDATE

Finds and fixes orders where customer/channel creation failed during sync.

```sql
-- Find orders with missing customer_id
SELECT o.id, o.external_id,
       (o.customer_notes::jsonb->>'customer_id_relbase')::int
FROM orders o
WHERE o.source = 'relbase'
  AND o.customer_id IS NULL
  AND o.customer_notes::jsonb ? 'customer_id_relbase'
```

Then for each: create customer if needed, UPDATE order with customer_id.

---

### Step 11: COMMIT Transaction

```python
conn.commit()
```

**What this does:** Persists ALL changes from Steps 4-10 to the database.

Without COMMIT, nothing is saved - the transaction would rollback on connection close.

---

### Step 12: REFRESH Materialized View

**View:** `sales_facts_mv`
**Operation:** REFRESH

```sql
REFRESH MATERIALIZED VIEW sales_facts_mv
```

**Only runs if:** `orders_created > 0`
**Non-blocking:** If refresh fails, sync still succeeds (logs warning)

---

### Step 13: Log Sync Results

**Table:** `sync_logs`
**Operation:** INSERT

```sql
INSERT INTO sync_logs
(source, sync_type, status, records_processed, records_failed, details, started_at, completed_at)
VALUES ('relbase', 'orders', 'success'/'partial', {count}, {errors}, '{JSON}', {start}, NOW())
```

---

## Known Issues & Questions

### Q1: Is Step 6 (customer_channel_rules) really working?

**ANSWER: YES, but it's a FALLBACK mechanism with limited use.**

The `customer_channel_rules` table has only ~4 rows because:
1. It's Path C in a 4-path resolution - only used when Paths A and B fail
2. It's for **business exceptions** - specific customers who should ALWAYS go to a certain channel regardless of what Relbase says
3. Most orders resolve their channel via Path A (already in DB) or Path B (create from API cache)

**When it's used:**
- When `channel_id_relbase` is NULL or not found in Relbase API
- AND the customer has a specific rule defined

**Example use case:**
> "Customer 12345 (Walmart) should ALWAYS be DISTRIBUIDOR channel even if Relbase says otherwise"

**The table is working correctly - it's just not needed for most orders.**

---

### Q2: What's the problem with Step 9 (product_id = NULL)?

**ANSWER: It's a DESIGN DECISION, not a problem.**

**Why product_id is intentionally NULL:**

1. **SKU codes from Relbase are messy:**
   - `ANU-GRLC_D26010` (has ANU- prefix)
   - `GRLC_D26010_WEB` (has _WEB suffix)
   - `GRLC_D26010` (clean)

2. **Mapping rules evolve over time:**
   - New rules added, old rules modified
   - If we mapped at sync time, we'd need to re-sync everything when rules change

3. **Raw data preserved for audit:**
   - We can always see exactly what Relbase sent
   - Debugging is easier

4. **Mapping done at DISPLAY TIME:**
   - `ProductCatalogService` uses 13 smart rules to transform SKUs
   - Rules include: exact match, ANU- prefix removal, _WEB suffix removal, etc.

**This is NOT a bug - it's intentional deferred mapping.**

---

### Q3: Is Step 10 necessary? Is it duplicated code?

**ANSWER: YES it's necessary. It's a SAFETY NET, not duplication.**

**Why cleanup exists:**

1. **Rate limiting failures:**
   - Relbase API can return 429 (rate limited)
   - Customer/channel creation might fail mid-sync
   - Without cleanup, orders would have NULL customer_id

2. **Transient API errors:**
   - Network timeouts
   - Relbase API downtime
   - These can cause customer fetch to fail

3. **Order of operations:**
   - Customer A appears in DTE 1 (fails to create)
   - Customer A appears in DTE 2 (succeeds)
   - Cleanup links DTE 1's order to Customer A

**It's NOT duplicated code because:**
- Steps 7-8 try to create customer/channel DURING sync
- Step 10 fixes orders where creation FAILED

**Could be refactored?** Yes, but the safety net approach is robust.

---

### Q4: What is COMMIT (Step 11)?

**ANSWER: It's how database transactions work.**

**Without COMMIT:**
- All INSERTs/UPDATEs are in a "pending" state
- If connection closes, everything rolls back
- Other processes can't see the changes

**With COMMIT:**
- Changes are permanently saved to disk
- Other processes can now see the new orders
- Transaction is complete

**It's standard database behavior, not Grana-specific.**

```python
# Pseudocode
conn = connect_to_database()
cursor = conn.cursor()

cursor.execute("INSERT INTO orders ...")  # Pending
cursor.execute("INSERT INTO order_items ...")  # Pending

conn.commit()  # NOW saved permanently

# If we did conn.rollback() instead, nothing would be saved
```

---

## What is sales_facts_mv?

### Definition

`sales_facts_mv` is a **Materialized View** - a pre-computed table that stores the results of a complex query.

### Purpose

It pre-aggregates sales data with SKU mapping for **fast OLAP analytics**.

### What it contains

| Column | Description |
|--------|-------------|
| `date_id` | YYYYMMDD integer for date dimension joins |
| `order_date` | Original order date |
| `channel_id`, `channel_name` | Sales channel info |
| `customer_id` | Customer reference |
| `original_sku` | Raw SKU from order_items |
| `catalog_sku` | Mapped SKU from product_catalog |
| `sku_primario` | Primary SKU for product families |
| `product_name` | Resolved product name |
| `category`, `brand` | Product attributes |
| `match_type` | How SKU was matched (direct/caja_master/sku_mapping/unmapped) |
| `quantity`, `unit_price`, `total` | Order amounts |
| `units_sold` | Converted to base units |

### SKU Matching Logic (4 Paths)

```sql
COALESCE(
    pc_direct.sku,          -- 1. Direct match on product_catalog.sku
    pc_master.sku,          -- 2. Match on product_catalog.sku_master (CAJA MASTER)
    pc_mapped.sku,          -- 3. Via sku_mappings → product_catalog.sku
    pc_mapped_master.sku    -- 4. Via sku_mappings → product_catalog.sku_master
) AS catalog_sku
```

### Why Materialized View?

**Regular View:** Re-runs the complex JOIN query every time you query it (slow)

**Materialized View:** Pre-computes and stores the result (fast reads)

**Trade-off:** Must be refreshed to see new data

### When it's refreshed

```sql
-- After sync (if orders were created)
REFRESH MATERIALIZED VIEW sales_facts_mv;
```

The sync service does this automatically in Step 12.

---

## Next Flows After Sync

After orders are synced and saved, these flows consume the data:

### 1. AUTOMATIC: Database Trigger (orders_audit)

**When:** Any UPDATE to `orders` table (not INSERT)

**What:** Automatically logs field changes to `orders_audit`

**Fields tracked:**
- `channel_id` changes
- `total` changes
- `customer_id` changes

```sql
-- Trigger function
IF (OLD.channel_id IS DISTINCT FROM NEW.channel_id) THEN
    INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, ...)
    VALUES (NEW.id, 'channel_id', OLD.channel_id, NEW.channel_id, ...);
END IF;
```

**Note:** INSERT does NOT trigger audit - only UPDATEs do.

---

### 2. SKU Mapping Flow (Display Time)

**File:** `backend/app/api/audit.py`
**Service:** `ProductCatalogService`

**When:** Frontend requests order data for display

**What:** Transforms raw `product_sku` → official catalog SKU

**13 Smart Rules:**
1. Exact match on product_catalog.sku
2. Remove `ANU-` prefix and match
3. Remove `_WEB` suffix and match
4. Match on sku_master (CAJA MASTER)
5. Via sku_mappings table rules
6. ... and more

**Tables used:**
- `product_catalog` - Official SKU catalog
- `sku_mappings` - Database-driven mapping rules

---

### 3. Sales Analytics Flow

**File:** `backend/app/api/sales_analytics_realtime.py`

**When:** Frontend requests dashboard data

**What:** Aggregates orders by channel, date, product for charts

**Tables used:**
- `sales_facts_mv` - Pre-aggregated data (fast)
- `orders` + `order_items` - Real-time queries
- `channels` - Channel names
- `dim_date` - Date dimension for OLAP

---

### 4. Order Audit Flow

**File:** `backend/app/api/audit.py`

**When:** User views order history or audit trail

**What:** Shows all changes made to an order

**Tables used:**
- `orders_audit` - Change history
- `orders` - Current order state
- `manual_corrections` - Manual fix records

---

### 5. Manual Correction Flow

**File:** `backend/app/api/audit.py`

**When:** User manually corrects order data

**What:**
1. Updates order fields
2. Triggers `orders_audit`
3. Records in `manual_corrections`

**Tables used:**
- `orders` - UPDATE
- `orders_audit` - AUTO via trigger
- `manual_corrections` - INSERT

---

### 6. Export Flow

**File:** `backend/app/api/audit.py`

**When:** User exports orders to Excel

**What:** Generates Excel file with mapped SKUs and all order details

**Tables used:**
- `orders` + `order_items`
- `ProductCatalogService` for SKU mapping
- `customers`, `channels` for details

---

## Flow Diagram: After Sync

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AFTER SYNC - DATA CONSUMPTION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        orders table                                  │   │
│  │                   (synced from Relbase)                              │   │
│  └───────────────────────────┬─────────────────────────────────────────┘   │
│                              │                                              │
│         ┌────────────────────┼────────────────────┐                        │
│         │                    │                    │                        │
│         ▼                    ▼                    ▼                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ UPDATE order │    │ sales_facts  │    │ Frontend     │                  │
│  │ (manual fix) │    │ _mv (REFRESH)│    │ requests     │                  │
│  └──────┬───────┘    └──────────────┘    └──────┬───────┘                  │
│         │                                       │                          │
│         ▼                                       │                          │
│  ┌──────────────┐                              │                          │
│  │ orders_audit │◄── TRIGGER (auto)            │                          │
│  │ (change log) │                              │                          │
│  └──────────────┘                              │                          │
│                                                 │                          │
│         ┌───────────────────────────────────────┤                          │
│         │                                       │                          │
│         ▼                                       ▼                          │
│  ┌──────────────────────┐             ┌──────────────────────┐            │
│  │ SKU Mapping Flow     │             │ Sales Analytics      │            │
│  │                      │             │                      │            │
│  │ audit.py             │             │ sales_analytics_     │            │
│  │ ProductCatalogService│             │ realtime.py          │            │
│  │                      │             │                      │            │
│  │ Tables:              │             │ Tables:              │            │
│  │ • product_catalog    │             │ • sales_facts_mv     │            │
│  │ • sku_mappings       │             │ • orders/order_items │            │
│  │                      │             │ • dim_date           │            │
│  └──────────────────────┘             └──────────────────────┘            │
│                                                                             │
│  ┌──────────────────────┐             ┌──────────────────────┐            │
│  │ Order Audit Flow     │             │ Export Flow          │            │
│  │                      │             │                      │            │
│  │ Tables:              │             │ Generates Excel      │            │
│  │ • orders_audit       │             │ with mapped SKUs     │            │
│  │ • manual_corrections │             │                      │            │
│  └──────────────────────┘             └──────────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deep Dive: orders_audit Trigger Flow

### Overview

The `orders_audit` flow is **automatic** - it's triggered by a database trigger whenever the `orders` table is UPDATED.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    orders_audit TRIGGER FLOW                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                ANY UPDATE ON orders TABLE                            │   │
│  │                                                                      │   │
│  │  Sources of UPDATEs:                                                 │   │
│  │  • sync_service.py (Step 10 cleanup - fix NULL customer/channel)    │   │
│  │  • Future: Manual correction UI (not implemented yet)               │   │
│  │  • Future: API endpoints for order modification                     │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │           TRIGGER: audit_order_changes_trigger                       │   │
│  │           (AFTER UPDATE ON orders FOR EACH ROW)                      │   │
│  │                                                                      │   │
│  │  Function: audit_order_changes()                                     │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │           TRACKED FIELDS (only these trigger audit)                  │   │
│  │                                                                      │   │
│  │  IF (OLD.channel_id IS DISTINCT FROM NEW.channel_id)                │   │
│  │     → INSERT INTO orders_audit (field_changed='channel_id')          │   │
│  │                                                                      │   │
│  │  IF (OLD.total IS DISTINCT FROM NEW.total)                          │   │
│  │     → INSERT INTO orders_audit (field_changed='total')               │   │
│  │                                                                      │   │
│  │  IF (OLD.customer_id IS DISTINCT FROM NEW.customer_id)              │   │
│  │     → INSERT INTO orders_audit (field_changed='customer_id')         │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │           orders_audit TABLE                                         │   │
│  │                                                                      │   │
│  │  id | order_id | field_changed | old_value | new_value | changed_by │   │
│  │  ───┼──────────┼───────────────┼───────────┼───────────┼─────────── │   │
│  │  1  │ 12345    │ channel_id    │ NULL      │ 5         │ system     │   │
│  │  2  │ 12345    │ customer_id   │ NULL      │ 789       │ system     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Trigger Definition (SQL)

**File:** `supabase/migrations/20260109143335_remote_schema.sql:55-83`

```sql
CREATE OR REPLACE FUNCTION "public"."audit_order_changes"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Solo auditar si hay cambios reales
    IF (OLD.channel_id IS DISTINCT FROM NEW.channel_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'channel_id', OLD.channel_id::text, NEW.channel_id::text,
                COALESCE(NEW.corrected_by, 'system'),
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    IF (OLD.total IS DISTINCT FROM NEW.total) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'total', OLD.total::text, NEW.total::text,
                COALESCE(NEW.corrected_by, 'system'),
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    IF (OLD.customer_id IS DISTINCT FROM NEW.customer_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'customer_id', OLD.customer_id::text, NEW.customer_id::text,
                COALESCE(NEW.corrected_by, 'system'),
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    RETURN NEW;
END;
$$;
```

### Trigger Attachment

```sql
CREATE OR REPLACE TRIGGER "audit_order_changes_trigger"
    AFTER UPDATE ON "public"."orders"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."audit_order_changes"();
```

### orders_audit Table Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer | Primary key (auto-increment) |
| `order_id` | integer | FK to orders.id |
| `field_changed` | varchar(100) | `channel_id`, `total`, or `customer_id` |
| `old_value` | text | Value before change |
| `new_value` | text | Value after change |
| `changed_by` | varchar(100) | `system` or username |
| `changed_at` | timestamp | Auto-generated (NOW()) |
| `change_type` | varchar(50) | `system_update` or `manual_correction` |
| `reason` | text | Optional explanation |
| `ip_address` | varchar(50) | For manual corrections (future) |
| `user_agent` | text | For manual corrections (future) |

### What Triggers the Audit?

| Source | When | change_type | changed_by |
|--------|------|-------------|------------|
| **Sync Service (Step 10)** | Cleanup fixes NULL customer/channel | `system_update` | `system` |
| **Future: Manual Correction UI** | User edits order in dashboard | `manual_correction` | `username` |
| **Future: API Update** | External API modifies order | `system_update` | `api_key` |

### Important: INSERT Does NOT Trigger Audit

The audit trigger only fires on **UPDATE**, not on **INSERT**.

When a new order is created during sync (Step 8), no audit record is created.
Audit records are only created when an **existing** order is modified.

### Frontend Entry Point (Currently None)

There is **no frontend UI** that directly triggers order UPDATEs currently.

The `/dashboard/audit` page (`frontend/app/dashboard/audit/page.tsx`) is **read-only** - it displays orders with SKU mapping but does not allow editing.

Future implementation would add:
- Edit button on order rows
- Modal for changing channel/customer
- API call to `PUT /api/v1/orders/{id}` (not implemented)
- Sets `is_corrected = true`, `corrected_by = username`
- Triggers audit automatically

---

## Deep Dive: SKU Mapping Flow

### Overview

SKU mapping happens **at display time**, not during sync. This is a key design decision.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SKU MAPPING FLOW                                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                FRONTEND TRIGGERS                                     │   │
│  │                                                                      │   │
│  │  /dashboard/audit (Desglose de Pedidos)                             │   │
│  │       │                                                              │   │
│  │       ├── Page Load → fetchData()                                    │   │
│  │       ├── Filter Change → fetchData()                               │   │
│  │       └── Pagination → fetchData()                                  │   │
│  │                                                                      │   │
│  │  /dashboard/sales-analytics (Sales Analytics)                       │   │
│  │       │                                                              │   │
│  │       └── Uses sales_facts_mv (pre-computed, not live mapping)      │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │           GET /api/v1/audit/data                                     │   │
│  │           File: backend/app/api/audit.py:315                        │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │           FETCH RAW DATA FROM DATABASE                               │   │
│  │                                                                      │   │
│  │  SELECT orders, order_items, customers, channels                     │   │
│  │  WHERE filters applied...                                            │   │
│  │                                                                      │   │
│  │  order_items.product_sku = RAW SKU (e.g., 'ANU-BAKC_U04010')        │   │
│  │  order_items.product_id = NULL (not linked at sync time)            │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │           FOR EACH ROW: map_sku_with_quantity()                      │   │
│  │           File: backend/app/api/audit.py:181-313                    │   │
│  │                                                                      │   │
│  │  Priority order:                                                     │   │
│  │  1. Direct catalog match (exact SKU exists)                         │   │
│  │  2. CAJA MASTER match (sku_master lookup)                           │   │
│  │  3. Database mappings (sku_mappings table via SKUMappingService)    │   │
│  │  4. Programmatic fallbacks (regex transformations)                   │   │
│  │  5. No match → return NULL                                          │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│         ┌────────────────────────────┼────────────────────────────────┐    │
│         │                            │                                │    │
│         ▼                            ▼                                ▼    │
│  ┌──────────────┐          ┌──────────────────┐         ┌──────────────┐  │
│  │ STEP 1-2     │          │ STEP 3           │         │ STEP 4       │  │
│  │ Direct Match │          │ Database Mapping │         │ Programmatic │  │
│  │              │          │                  │         │              │  │
│  │ product_     │          │ sku_mappings     │         │ Regex rules  │  │
│  │ catalog      │          │ table            │         │ (hardcoded)  │  │
│  │              │          │                  │         │              │  │
│  │ Confidence:  │          │ Confidence:      │         │ Confidence:  │  │
│  │ 100%         │          │ 90-100%          │         │ 85-90%       │  │
│  └──────────────┘          └──────────────────┘         └──────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │           ENRICHMENT: ProductCatalogService                          │   │
│  │           File: backend/app/services/product_catalog_service.py     │   │
│  │                                                                      │   │
│  │  get_sku_primario(official_sku)     → SKU Primario (family base)    │   │
│  │  calculate_units(sku, quantity)     → Converted units               │   │
│  │  get_product_name_for_sku_primario() → Product name (Title Case)    │   │
│  │  get_peso_display_total()           → Weight calculation            │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │           RETURN ENRICHED DATA TO FRONTEND                           │   │
│  │                                                                      │   │
│  │  {                                                                   │   │
│  │    "sku": "ANU-BAKC_U04010",           // Original (from DB)        │   │
│  │    "sku_primario": "BAKC_U04010",      // Mapped (computed)         │   │
│  │    "match_type": "db_prefix",          // How it was matched        │   │
│  │    "confidence": 95,                   // Match confidence %        │   │
│  │    "unidades": 50,                     // Calculated units          │   │
│  │    "in_catalog": true,                 // SKU exists in catalog     │   │
│  │    "conversion_factor": 5              // Units per display         │   │
│  │  }                                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Frontend Entry Points

#### 1. /dashboard/audit (Desglose de Pedidos)

**File:** `frontend/app/dashboard/audit/page.tsx`

**Triggers SKU Mapping:**
```typescript
// On page load and filter changes
const fetchData = async () => {
  const response = await fetch(`${API_URL}/api/v1/audit/data?${params}`);
  // Response already contains mapped SKUs
  setData(result.data);
};
```

**Backend endpoint:**
```
GET /api/v1/audit/data
    ?limit=100
    &offset=0
    &source=relbase
    &channel=CORPORATIVO
    &from_date=2025-01-01
    &to_date=2025-12-31
```

#### 2. /dashboard/sales-analytics

**File:** `frontend/app/dashboard/sales-analytics/page.tsx`

**Does NOT trigger live SKU mapping** - uses `sales_facts_mv` materialized view which has pre-computed SKU mappings.

### SKU Mapping Rules (Priority Order)

#### Step 1-2: Direct Catalog Match (Confidence: 100%)

```python
# Rule 1: Exact match in normal SKU
if sku in catalog_skus:
    return sku, 'exact_match', 1, product_map[sku], 100

# Rule 2: Exact match in CAJA MÁSTER
if sku in catalog_master_skus:
    return sku, 'caja_master', 1, product_map[sku], 100
```

#### Step 3: Database-Driven Mappings (Confidence: varies)

**File:** `backend/app/services/sku_mapping_service.py`

**Table:** `sku_mappings`

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer | Primary key |
| `source_pattern` | text | Pattern to match (e.g., `ANU-`, `MLC1630337051`) |
| `pattern_type` | varchar | `exact`, `prefix`, `suffix`, `contains`, `regex` |
| `source_filter` | varchar | Filter by source (e.g., `mercadolibre`) |
| `target_sku` | text | Official catalog SKU to map to |
| `quantity_multiplier` | integer | Multiply quantity (for PACK SKUs) |
| `confidence` | integer | Mapping confidence % |
| `priority` | integer | Higher = evaluated first |

**Examples in database:**

| source_pattern | pattern_type | target_sku | quantity_multiplier |
|----------------|--------------|------------|---------------------|
| `ANU-` | prefix | (strips prefix) | 1 |
| `_WEB` | suffix | (strips suffix) | 1 |
| `KEEPERPACK` | exact | `KSMC_U03010` | 5 |
| `MLC1630337051` | exact | `BABE_U20010` | 1 |

#### Step 4: Programmatic Fallbacks (Confidence: 85-90%)

For complex transformations that can't be expressed in database rules:

```python
# Trailing "20" → "10" pattern
if sku.endswith('20') and not sku.endswith('010'):
    clean_sku = sku[:-2] + '10'
    if clean_sku in catalog_skus:
        return clean_sku, 'trailing_20_to_10', 1, product_map[clean_sku], 90

# Extra digits pattern (e.g., BABE_C028220 → BABE_C02810)
extra_digit_match = re.match(r'^(.+)([0-9]{3})([0-9]{2})0$', sku)

# Cracker "1UES" variants (e.g., CRAA1UES → CRAA_U13510)
cracker_match = re.match(r'^CR([A-Z]{2})1UES$', sku)

# General substring matching (85% confidence)
for catalog_sku in sorted(catalog_skus, key=len, reverse=True):
    if len(catalog_sku) >= 8 and catalog_sku in sku:
        return catalog_sku, 'substring_match_unitary', 1, product_map[catalog_sku], 85
```

### Unit Conversion Flow

**File:** `backend/app/services/product_catalog_service.py:220-296`

```python
def calculate_units(self, sku: str, quantity: int, source: str = None) -> int:
    """
    Formula: Units = Quantity × SKU Mapping Multiplier × Target SKU Conversion Factor

    Examples:
        - BAKC_U04010 (X1): 10 × 1 = 10 bars
        - BAKC_U20010 (X5): 10 × 5 = 50 bars
        - BAKC_C02810 (CM): 2 × 140 = 280 bars
        - KEEPERPACK (mapped ×5): 7 × 5 × 1 = 35 keepers
    """
    # Step 1: Check sku_mappings for quantity_multiplier
    mapping_result = mapping_service.map_sku(sku, source)
    if mapping_result:
        multiplier = mapping_result.quantity_multiplier
        target_sku = mapping_result.target_sku
        target_conversion = catalog[target_sku].get('units_per_display', 1)
        return quantity * multiplier * target_conversion

    # Step 2: Direct catalog lookup
    if sku in catalog:
        conversion_factor = catalog[sku].get('units_per_display', 1)
        return quantity * conversion_factor

    # Step 3: Master box lookup
    if sku in master_sku_lookup:
        conversion_factor = master_sku_lookup[sku].get('items_per_master_box', 1)
        return quantity * conversion_factor

    # Step 4: Unknown SKU - return quantity as units
    return quantity * 1
```

### Tables Used in SKU Mapping

| Table | Purpose | Query Location |
|-------|---------|----------------|
| `product_catalog` | Official SKU catalog with conversion factors | `ProductCatalogService._load_catalog_from_database()` |
| `sku_mappings` | Database-driven transformation rules | `SKUMappingService.map_sku()` |
| `order_items` | Raw SKUs from orders | `audit.py` main query |

### Why Mapping at Display Time?

**Advantages:**
1. **Rules evolve:** New mappings can be added without re-syncing all orders
2. **Raw data preserved:** Original Relbase codes stored for audit trail
3. **Debugging:** Can see exactly what Relbase sent vs what we mapped it to
4. **Performance:** Only map what's being displayed, not entire database

**Disadvantages:**
1. **Latency:** Small overhead on each API call
2. **Inconsistency risk:** If rules change, historical displays change too
3. **Caching needed:** `ProductCatalogService` and `SKUMappingService` cache data (5 min TTL)

### Match Types Displayed in Frontend

| match_type | Description | UI Display |
|------------|-------------|------------|
| `exact_match` | Direct catalog match | (none) |
| `caja_master` | Master box SKU | "Caja Master" |
| `db_prefix` | Database prefix rule (e.g., ANU-) | "ANU-" |
| `db_exact` | Database exact match | (rule name) |
| `trailing_20_to_10` | Programmatic 20→10 | "20→10" |
| `substring_match_unitary` | Substring found in catalog | (none) |
| `no_match` | Could not map | Shown in yellow |

---

## Summary: Tables Used in Sync Flow

| Step | Table | Operation | Purpose |
|------|-------|-----------|---------|
| 1 | `orders` | SELECT | Get MAX(order_date) for date range |
| 4 | `orders` | SELECT | Check if DTE already exists |
| 6A | `channels` | SELECT | Find channel by external_id |
| 6B | `channels` | INSERT | Create channel from API cache |
| 6C | `customer_channel_rules` | SELECT | Apply business rule (fallback) |
| 7A | `customers` | SELECT | Find customer by external_id |
| 7B | `customers` | INSERT | Create customer from API |
| 8 | `orders` | INSERT | Create order record |
| 9 | `order_items` | INSERT | Create line items (RAW SKU) |
| 10 | `orders` | UPDATE | Fix missing customer/channel |
| 10 | `customers` | INSERT | Create missing customers |
| 12 | `sales_facts_mv` | REFRESH | Update analytics cache |
| 13 | `sync_logs` | INSERT | Log sync results |

---

## Obsolete Tables (Not Used in Sync)

| Table | Status | Evidence |
|-------|--------|----------|
| `channel_product_equivalents` | **OBSOLETE** | Zero references in code |
| `relbase_product_mappings` | **DEPRECATED** | Only used for stats visualization |

See `GRANA_ARCHITECTURE.md` for full obsolete table analysis.
