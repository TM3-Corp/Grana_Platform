# Inventory Architecture Decision Required

**Date:** December 4, 2025
**Status:** Pending Decision
**Priority:** High

## Problem Summary

The current inventory system has an architectural issue that causes **44 SKUs with stock to show no valuation** (displaying "-" instead of a price).

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CURRENT DATA FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐         ┌─────────────────┐         ┌───────────────┐│
│   │    products     │         │ warehouse_stock │         │product_catalog││
│   │  (532 active)   │◄────────│  (FK: product_  │         │  (81 active)  ││
│   │                 │         │       id)       │         │               ││
│   │ Legacy SKUs     │         │                 │         │ Real SKUs     ││
│   │ Typos           │         │ Quantities per  │         │ with prices   ││
│   │ PACK variants   │         │ warehouse/lot   │         │ (sku_value)   ││
│   └────────┬────────┘         └─────────────────┘         └───────┬───────┘│
│            │                                                      │        │
│            └──────────────── JOIN ON sku ─────────────────────────┘        │
│                                   │                                        │
│                          Only 53 SKUs match!                               │
│                          44 SKUs have NO price!                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## The Numbers

| Table | Active Records | Description |
|-------|----------------|-------------|
| `products` | 532 | Accumulated from orders (includes legacy/typos) |
| `product_catalog` | 81 | Official SKUs with prices (source of truth) |
| **Matching SKUs** | **53** | SKUs that exist in both tables |
| **Orphan SKUs in inventory** | **44** | Have stock but no price |

## Root Cause

1. **`warehouse_stock`** table has a foreign key to `products.id`
2. **`products`** table accumulates SKUs from historical orders (RelBase sync)
3. **`product_catalog`** is the source of truth with correct SKUs and prices
4. When we JOIN to get prices: `products.sku = product_catalog.sku`
5. **Many SKUs don't match** because:
   - English variants: `CRPR_U02520` vs `CRPR_U02510` (suffix 20 vs 10)
   - PACK products: `PACKBAKC_U20010` (not in catalog)
   - Typos/legacy codes

## Examples of Orphan SKUs

```
SKU in products (has stock)     Should map to (in product_catalog)
─────────────────────────────   ──────────────────────────────────
CRPR_U02520 (English)           CRPR_U02510 (Spanish) - $282
CRSM_U02520 (English)           CRSM_U02510 (Spanish) - $282
PACKBAKC_U20010                  ??? (no equivalent)
PACKBASURTIDA                    ??? (bundle, no single price)
```

## Proposed Solutions

### Option A: Change FK to product_catalog (Recommended)

**Change:** `warehouse_stock.product_id` → references `product_catalog.id`

```
┌─────────────────┐         ┌─────────────────┐
│ warehouse_stock │────────►│ product_catalog │
│                 │   FK    │ (source of truth│
│ quantity, lot,  │         │  with prices)   │
│ expiration      │         │                 │
└─────────────────┘         └─────────────────┘
```

**Pros:**
- Clean architecture
- Single source of truth
- No JOIN mismatch issues
- Prices always available for inventory

**Cons:**
- Requires database migration
- Need to map existing warehouse_stock records to product_catalog IDs
- May need to handle SKUs not in product_catalog (create entries or reject)

**Migration Steps:**
1. Add `product_catalog_id` column to `warehouse_stock`
2. Populate by matching SKU via `products.sku` → `product_catalog.sku`
3. Handle unmatched records (add to catalog or mark as legacy)
4. Update backend queries to use new FK
5. Eventually drop `product_id` column

### Option B: Keep products, add product_catalog_id

**Change:** Add `product_catalog_id` FK to `products` table

```
┌─────────────────┐         ┌─────────────────┐         ┌───────────────┐
│ warehouse_stock │────────►│    products     │────────►│product_catalog│
│                 │   FK    │                 │   FK    │               │
└─────────────────┘         │ +product_       │         │ (prices)      │
                            │  catalog_id     │         │               │
                            └─────────────────┘         └───────────────┘
```

**Pros:**
- Less invasive change
- Keeps historical data intact
- Can be done incrementally

**Cons:**
- Maintains complexity (two product tables)
- Still need to handle unmapped products
- JOIN chain is longer

### Option C: Sync products with product_catalog (Quick Fix)

**Change:** Add missing SKUs to `product_catalog` with derived prices

**This is what we're doing as a temporary fix:**
- Add English SKUs with same price as Spanish equivalents
- Add PACK products with estimated prices

**Pros:**
- Fastest to implement
- No schema changes
- Solves immediate display issue

**Cons:**
- Doesn't fix root architecture issue
- product_catalog grows with "fake" entries
- Maintenance burden increases

## Recommendation

**Long-term:** Option A (warehouse_stock → product_catalog directly)

**Short-term:** Option C (add missing SKUs to product_catalog) - **Currently implementing**

## Questions to Discuss

1. Should `product_catalog` be the ONLY source of truth for inventory?
2. What do we do with PACK products? Create catalog entries or exclude from valuation?
3. Should English variants have the same price as Spanish?
4. Do we need `products` table at all for inventory, or only for historical sales?

## Current Quick Fix (Implemented)

Adding English variant prices to `product_catalog` using Spanish equivalents:
- `CRPR_U02520` gets price from `CRPR_U02510`
- `CRSM_U02520` gets price from `CRSM_U02510`
- etc.

This resolves the "-" display issue but doesn't fix the architecture.

---

**Document Author:** Claude (AI Assistant)
**To Discuss With:** [Colleague Name]
**Decision Deadline:** [TBD]
