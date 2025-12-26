
 Diagnosis Complete

  I've created a comprehensive diagnosis document at:
  .claude_sessions/current/DATA_DISCREPANCY_DIAGNOSIS.md

  Summary of Root Cause

  The discrepancy is $117M+ in CAJA MASTER sales being misclassified.

  | View                       | Join Method    | CAJA MASTER | CRACKERS |
  |----------------------------|----------------|-------------|----------|
  | /dashboard/sales-analytics | BY product_id  | $7M         | $91M     |
  | /dashboard & /orders       | BY product_sku | $124M       | $34M     |

  The Two Problems

  1. Wrong product_id values in order_items:
    - CRSM_C01010 (CAJA MASTER) has product_id=26 pointing to CRSM_U13510 (CRACKERS)
    - The SKU-to-ID mapping is broken for CAJA MASTER variants
    - $117M of revenue is misclassified
  2. 2,176 items with NULL product_id:
    - These are completely invisible to the materialized view
    - The SKU-based join finds them correctly

  The Technical Cause

  The sales_facts_mv materialized view joins by product_id:
  LEFT JOIN products p ON oi.product_id = p.id  -- WRONG ID = WRONG CATEGORY

  While audit.py and analytics.py jon by SKU:
  LEFT JOIN products p ON UPPER(p.sku) = UPPER(oi.product_sku)  -- CORRECT

  Three Fix Options

  | Option | What                                 | Pros                               | Cons                           |
  |--------|--------------------------------------|------------------------------------|--------------------------------|
  | A      | Update MV to join by SKU             | Quick, consistent with other views | Doesn't fix underlying data    |
  | B      | Fix product_id values in order_items | Fixes root cause                   | Complex, requires data cleanup |
  | C      | Both A + B                           | Complete fix                       | Most work                      |

  ---
  Questions for you before proceeding:

  1. Is it okay to change the materialized view to join by SKU instead of product_id?
  2. Should CAJA MASTER remain a separate category, or should those items be grouped under their product family (BARRAS, CRACKERS, GRANOLAS)?
  3. Do we need to fix the historical product_id data, or is fixing forward sufficient?

# Data Discrepancy Diagnosis Report
## Product Family Numbers Across Dashboard Views
**Date:** 2025-12-14
**Status:** ROOT CAUSE IDENTIFIED

---

## Executive Summary

There are significant data discrepancies between three dashboard views when filtering/grouping by Product Family:

| View | BARRAS | CRACKERS | GRANOLAS | KEEPERS | CAJA MASTER |
|------|--------|----------|----------|---------|-------------|
| `/dashboard` (QuarterlyAnalytics) | $223M | $34M | $18M | $14M | $124M |
| `/dashboard/sales-analytics` | $228M | $91M | $45M | $10M | $7M |
| `/dashboard/orders` (Audit) | $223M | $34M | $18M | $14M | $124M |

**The discrepancy is $117M+ in CAJA MASTER alone!**

---

## Root Cause Analysis

### The Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     order_items TABLE                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ id | product_sku    | product_id | product_name | subtotal   │   │
│  │ 1  | CRSM_C01010    | 26         | Cracker box  | $500,000   │   │
│  │ 2  | CRRO_C01010    | 28         | Cracker box  | $400,000   │   │
│  │ 3  | BAKC_U04010    | NULL       | Barra unit   | $100,000   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                    │                               │
                    │                               │
    ┌───────────────┴──────────┐    ┌──────────────┴──────────────┐
    │  JOIN by product_id       │    │  JOIN by product_sku        │
    │  (sales_facts_mv)         │    │  (audit.py / analytics.py)  │
    └───────────────┬──────────┘    └──────────────┬──────────────┘
                    │                               │
                    ▼                               ▼
    ┌───────────────────────────┐    ┌───────────────────────────────┐
    │  products TABLE           │    │  products TABLE               │
    │  id=26 → CRSM_U13510     │    │  sku=CRSM_C01010             │
    │        → category=CRACKERS│    │        → category=CAJA MASTER │
    └───────────────────────────┘    └───────────────────────────────┘
```

### The Problem Has TWO Parts

#### Problem 1: Incorrect `product_id` Population

The `order_items.product_id` field was populated incorrectly during data sync. CAJA MASTER SKUs were assigned the `product_id` of their unit variants:

| order_items.product_sku | order_items.product_id | Points to product... | Category |
|-------------------------|------------------------|----------------------|----------|
| `CRSM_C01010` (CAJA MASTER) | 26 | `CRSM_U13510` | **CRACKERS** (WRONG!) |
| `CRRO_C01010` (CAJA MASTER) | 28 | `CRRO_U13510` | **CRACKERS** (WRONG!) |
| `CRAA_C01010` (CAJA MASTER) | 30 | `CRAA_U13510` | **CRACKERS** (WRONG!) |
| `BAKC_C02810` (CAJA MASTER) | 12 | `BAKC_U20010` | **BARRAS** (WRONG!) |
| `GRCA_C02010` (CAJA MASTER) | 23 | `GRCA_U26010` | **GRANOLAS** (WRONG!) |

**Pattern:** The `_C` suffix SKUs (CAJA MASTER variants) have `product_id` pointing to `_U` suffix products (unit variants).

**Impact:** $117M of CAJA MASTER sales classified incorrectly.

#### Problem 2: Missing `product_id` for Many Items

2,176 order_items have `product_id = NULL`:

| Total order_items | With product_id | With product_sku | SKU only (no ID) |
|-------------------|-----------------|------------------|------------------|
| 17,505 | 15,329 | 17,505 | **2,176** |

**Impact:** These 2,176 items are completely invisible to the materialized view (which joins by product_id).

---

## How Each View Gets Its Data

### View 1: `/dashboard` (QuarterlyAnalytics)
**File:** `backend/app/api/analytics.py`
**Join Method:** `LEFT JOIN products p ON UPPER(p.sku) = UPPER(oi.product_sku)`

```sql
SELECT
    COALESCE(UPPER(p.category), 'OTROS') as product_family,
    ...
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
LEFT JOIN products p ON UPPER(p.sku) = UPPER(oi.product_sku)  -- JOIN BY SKU
WHERE o.source = 'relbase'
AND o.invoice_status IN ('accepted', 'accepted_objection')
```

**Result:** CAJA MASTER = $124M (CORRECT)

---

### View 2: `/dashboard/sales-analytics`
**File:** `backend/app/api/sales_analytics.py` (uses `sales_facts_mv`)
**Join Method:** `LEFT JOIN products p ON oi.product_id = p.id` (inside the MV)

```sql
-- sales_facts_mv is pre-computed with:
LEFT JOIN products p ON oi.product_id = p.id  -- JOIN BY product_id
```

**Result:** CAJA MASTER = $7M (INCORRECT - $117M missing!)

---

### View 3: `/dashboard/orders` (Audit)
**File:** `backend/app/api/audit.py`
**Join Method:** `LEFT JOIN products p ON p.sku = oi.product_sku`

```sql
LEFT JOIN products p ON p.sku = oi.product_sku  -- JOIN BY SKU
```

**Result:** CAJA MASTER = $124M (CORRECT)

---

## Detailed Evidence

### Query 1: Category Comparison (2025 Data)

**Join by product_id (what sales_facts_mv does):**
```
BARRAS:         1,801 items | $227,984,309
CRACKERS:       1,242 items | $90,928,069
GRANOLAS:         679 items | $45,168,914
NULL/UNMATCHED: 1,083 items | $35,552,879
OTROS:             12 items | $12,379,785
KEEPERS:          640 items | $10,301,618
CAJA MASTER:       16 items | $7,195,800      ← WRONG! Should be $124M
```

**Join by product_sku (what audit.py/analytics.py do):**
```
BARRAS:         2,134 items | $223,278,111
CAJA MASTER:      260 items | $124,213,820    ← CORRECT!
CRACKERS:       1,455 items | $33,603,265
GRANOLAS:         744 items | $17,587,561
KEEPERS:          857 items | $14,074,928
OTROS:             12 items | $12,379,785
NULL/UNMATCHED:     9 items | $4,363,904
```

### Query 2: Top Misclassified Items

| SKU in order | product_id | Category by ID | Category by SKU | Revenue |
|--------------|------------|----------------|-----------------|---------|
| CRSM_C01010 | 26 | CRACKERS | CAJA MASTER | $24,308,400 |
| CRRO_C01010 | 28 | CRACKERS | CAJA MASTER | $16,327,800 |
| CRAA_C01010 | 30 | CRACKERS | CAJA MASTER | $15,030,600 |
| BAKC_C02810 | 12 | BARRAS | CAJA MASTER | $13,844,400 |
| GRCA_C02010 | 23 | GRANOLAS | CAJA MASTER | $12,249,740 |
| GRBE_C02010 | 41 | GRANOLAS | CAJA MASTER | $8,300,460 |
| GRAL_C02010 | 53 | GRANOLAS | CAJA MASTER | $8,149,100 |
| BAMC_C02810 | 20 | BARRAS | CAJA MASTER | $4,921,560 |

**Total misclassified:** $117,018,060

---

## Why This Happened

### The Sync Process

When orders are synced from RelBase, the system populates `order_items.product_id` by looking up the product in the database. The lookup logic likely used a fuzzy match or partial match that found the wrong product:

1. Order comes from RelBase with SKU `CRSM_C01010`
2. Sync process searches for a matching product
3. Instead of finding product with `sku = 'CRSM_C01010'` (CAJA MASTER)
4. It found product with `sku = 'CRSM_U13510'` (CRACKERS) - probably because:
   - The product with SKU `CRSM_C01010` didn't exist yet
   - OR a partial match algorithm matched on `CRSM` prefix

---

## Impact Assessment

### Financial Impact
- **$117M** of CAJA MASTER sales are incorrectly showing as CRACKERS/BARRAS/GRANOLAS in `/dashboard/sales-analytics`
- This represents ~27% of total 2025 revenue being misclassified

### Business Impact
- Executive decisions based on CRACKERS performance are inflated by 3x ($91M vs $34M actual)
- CAJA MASTER appears as a small category ($7M) when it's actually the 2nd largest ($124M)

---

## Recommended Fix Options

### Option A: Fix the Materialized View (Quick Fix)
**What:** Change `sales_facts_mv` to join by `product_sku` instead of `product_id`
**Pros:**
- Quick to implement (1 SQL migration)
- No data corruption to clean up
- Immediately consistent with other views
**Cons:**
- Doesn't fix the underlying `product_id` data problem

### Option B: Fix the Source Data (Thorough Fix)
**What:** Correct `order_items.product_id` values to point to correct products
**Pros:**
- Fixes the root cause
- All joins work correctly
**Cons:**
- More complex
- Requires careful analysis to ensure correct mappings
- May need to update sync process to prevent recurrence

### Option C: Both (Recommended)
1. First apply Option A to immediately fix the dashboard discrepancy
2. Then investigate and fix the sync process (prevent future issues)
3. Optionally clean up existing `product_id` values

---

## Files Involved

| Component | File | Join Method | Status |
|-----------|------|-------------|--------|
| QuarterlyAnalytics API | `backend/app/api/analytics.py` | BY SKU | CORRECT |
| Audit API | `backend/app/api/audit.py` | BY SKU | CORRECT |
| Sales Analytics | `backend/app/api/sales_analytics.py` | Uses MV | INCORRECT |
| Materialized View | `backend/migrations/017_*.sql` | BY product_id | **NEEDS FIX** |
| Sync Service | `backend/app/services/sync_service.py` | Populates product_id | **NEEDS REVIEW** |

---

## Next Steps (Recommended Order)

1. **Review this diagnosis** and confirm understanding
2. **Decide on fix approach** (Option A, B, or C)
3. **Implement the fix** with proper testing
4. **Verify all three views show consistent numbers**
5. **Document the fix** in CLAUDE.md

---

## Additional Evidence: Products Table Analysis

### CAJA MASTER Products DO Exist

The products table correctly has CAJA MASTER products with the right category:

| SKU | Product ID | Category |
|-----|------------|----------|
| CRSM_C01010 | **248** | CAJA MASTER |
| CRRO_C01010 | **250** | CAJA MASTER |
| CRAA_C01010 | **252** | CAJA MASTER |
| BAKC_C02810 | **251** | CAJA MASTER |
| GRCA_C02010 | **247** | CAJA MASTER |

### Unit Variants Also Exist

| SKU | Product ID | Category |
|-----|------------|----------|
| CRSM_U13510 | **26** | CRACKERS |
| CRRO_U13510 | **28** | CRACKERS |
| CRAA_U13510 | **30** | CRACKERS |
| BAKC_U20010 | **12** | BARRAS |
| GRCA_U26010 | **23** | GRANOLAS |

### The Bug: Wrong product_id Assignment

In `order_items`, the product_id points to the WRONG product:

| order_items.product_sku | order_items.product_id | Should Point To | Actually Points To |
|-------------------------|------------------------|-----------------|-------------------|
| CRSM_C01010 | 26 | ID 248 (CAJA MASTER) | ID 26 (CRACKERS) |
| CRRO_C01010 | 28 | ID 250 (CAJA MASTER) | ID 28 (CRACKERS) |
| CRAA_C01010 | 30 | ID 252 (CAJA MASTER) | ID 30 (CRACKERS) |
| BAKC_C02810 | 12 | ID 251 (CAJA MASTER) | ID 12 (BARRAS) |
| GRCA_C02010 | 23 | ID 247 (CAJA MASTER) | ID 23 (GRANOLAS) |

---

## Sync Process Analysis

### Current Sync Behavior (sync_service.py, line 557)

```python
cursor.execute("""
    INSERT INTO order_items
    (order_id, product_id, product_sku, product_name,
     quantity, unit_price, subtotal, total, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
""", (
    order_id,
    None,  # product_id not used - mapping done at display time
    product_code,  # Store raw RelBase code
    ...
))
```

The current sync sets `product_id = NULL`, which is correct behavior. The incorrect `product_id` values must have come from a **previous version of the sync** or a **different import process**.

### Alternative Sync (order_processing_service.py)

This service DOES populate `product_id`:

```python
our_sku = self.map_sku(item['product_sku'], order_data['source'], conn)

product_id = None
if our_sku:
    cursor.execute("""
        SELECT id FROM products WHERE sku = %s
    """, (our_sku,))
    product = cursor.fetchone()
    if product:
        product_id = product['id']
```

If `map_sku()` returned the wrong SKU (e.g., mapped CRSM_C01010 to CRSM_U13510), then the lookup would get the wrong product_id.

---

## Questions to Clarify

1. Do you want to preserve the current `order_items.product_id` data or is it okay to deprecate/ignore it?
2. Should we investigate why the sync process assigned wrong product_ids, or just fix forward?
3. Is CAJA MASTER intended to be a separate category, or should these items be grouped with their product families (BARRAS, CRACKERS, GRANOLAS)?
