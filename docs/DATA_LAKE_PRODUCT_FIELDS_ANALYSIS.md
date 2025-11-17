# Data Lake Product Fields - Comprehensive Analysis

**Date:** 2025-11-10
**Source:** `data/relbase_dtes/all_dtes.json`
**Total DTEs:** 5,422
**Total Products:** 12,087

---

## Executive Summary

This analysis examined product-level fields in all Relbase DTEs to understand how to properly populate the `order_items` table in Supabase.

**Key Findings:**
1. ✅ **price** is the correct unit price (NOT unit_cost)
2. ✅ **real_quantity** equals **quantity** in 99.8% of cases
3. ⚠️ **real_amount_neto** differs from `quantity × price` in **48.8%** of products
4. 🔍 **-16% pattern** dominates (55.6% of discrepancies) - likely **IVA-related**
5. ✅ **discount** field only populated in 2.3% of products
6. ✅ **surcharge** is always NULL (0% usage)

---

## 1. Field Presence Analysis

| Field | Count | % Present | Notes |
|-------|-------|-----------|-------|
| **price** | 12,087 | 100.0% | Always present ✅ |
| **quantity** | 12,087 | 100.0% | Always present ✅ |
| **real_quantity** | 12,087 | 100.0% | Always present ✅ |
| **real_amount_neto** | 12,087 | 100.0% | Always present ✅ |
| **unit_cost** | 12,078 | 99.9% | Almost always present |
| **unit_item** | 5,539 | 45.8% | Only in some products |
| **discount** | 274 | 2.3% | Rarely used ⚠️ |
| **surcharge** | 0 | 0.0% | Never used ❌ |

---

## 2. price vs unit_cost

### Analysis

| Metric | Count | % |
|--------|-------|---|
| unit_cost = 0 | 5,626 | 46.6% |
| unit_cost ≠ 0 | 6,452 | 53.4% |

### Examples of unit_cost ≠ 0:

```
DTE 3950269: ANU-C-P3-299827
  price: $11,800
  unit_cost: $3,600  (30% of price)

DTE 3971723: ANU-ANU-C-GC-963863
  price: $2,900
  unit_cost: $1,200  (41% of price)
```

### Conclusion ✅

**price** is the unit price to use for `order_items.unit_price`.

**unit_cost** appears to be internal cost/margin data, NOT the selling price.

---

## 3. quantity vs real_quantity

### Analysis

| Metric | Count | % |
|--------|-------|---|
| quantity = real_quantity | 12,067 | 99.8% |
| quantity ≠ real_quantity | 20 | 0.2% |

### Examples of Differences:

```
DTE 8637809: ANU-B-UB-617158
  quantity: 16
  real_quantity: 15  (-1 unit)

DTE 21663593: ANU-ALDEA_GRAketo210
  quantity: 6
  real_quantity: 0  (cancelled?)

DTE 32796444: ANU-CRSM_U13510
  quantity: 118
  real_quantity: 0  (large cancellation)
```

### Conclusion ✅

Use **real_quantity** as the authoritative quantity value.

The 20 cases where they differ appear to be:
- Order adjustments (returns, cancellations)
- Inventory corrections

---

## 4. real_amount_neto Calculation (CRITICAL FINDING)

### The Problem

**Expected:** `real_amount_neto = quantity × price`

**Reality:**

| Metric | Count | % |
|--------|-------|---|
| Matches calculation | 6,190 | 51.2% |
| **Differs from calculation** | **5,897** | **48.8%** ⚠️ |

### Analysis of Discrepancies

| Category | Count | % of Discrepancies |
|----------|-------|-------------------|
| **Rounding errors** (< $1) | 53 | 0.9% |
| **Explicit discount field** | 274 | 4.6% |
| **Implicit discounts** | 5,570 | **94.5%** 🔍 |

---

## 5. The -16% Pattern (IVA Hypothesis)

### Discovery

**3,277 products (55.6% of all discrepancies)** have exactly **-16% difference**.

### What is -16%?

In Chile, IVA (VAT) is **19%**:

```
If price includes IVA:
  price_without_iva = price_with_iva / 1.19
  discount = (price_with_iva - price_without_iva) / price_with_iva
  discount = (1 - 1/1.19) = 0.1597 ≈ 16%
```

### Hypothesis

**price** field contains price **WITH IVA** in some cases.
**real_amount_neto** is the **NET amount (without IVA)**.

### Examples:

```
DTE 3725626: ANU-SC-PC-631485 (PACK CHOCOLATOSO)
  price: $19,990 (con IVA)
  quantity: 1
  calculated: $19,990
  real_amount_neto: $16,798  (-16%)
  → $16,798 × 1.19 = $19,990 ✅ (matches!)

DTE 3791513: ANU-PC-PF-62506 (Pack Familia Saludable)
  price: $24,900 (con IVA)
  calculated: $24,900
  real_amount_neto: $20,924  (-16%)
  → $20,924 × 1.19 = $24,900 ✅ (matches!)
```

### Other Discount Patterns

| Discount % | Count | % of Discrepancies | Possible Reason |
|------------|-------|-------------------|-----------------|
| -16% | 3,277 | 55.6% | **IVA removal** |
| -24% | 792 | 13.4% | Commercial discount? |
| -20% | 329 | 5.6% | Commercial discount (Cencosud) |
| -22% | 296 | 5.0% | Commercial discount? |
| -23% | 213 | 3.6% | Commercial discount? |
| -30% | 137 | 2.3% | Large discount |

---

## 6. Explicit discount Field

### Usage

| Value | Count | % |
|-------|-------|---|
| NULL | 11,813 | 97.7% |
| = 0 | 0 | 0.0% |
| ≠ 0 | 274 | 2.3% |

### Customer Patterns

**Customer 596810 (Cencosud):**
- 266 products with explicit 20% discount
- Always registered in discount field

**Customer 596841:**
- 6 products with 15% discount

### Conclusion

When **discount** field is populated, it accurately reflects the percentage discount applied. However, it's only used in **2.3%** of products.

**Most discounts (94.5%) are implicit** - reflected in `real_amount_neto` but NOT in discount field.

---

## 7. surcharge Field

**Status:** Always NULL (0 occurrences)

**Conclusion:** Not used by Relbase system. Can be ignored.

---

## 8. unit_item Field

**Present in:** 45.8% of products

**Values found:**
- "UNID": 10 products

**Conclusion:** Low usage, not critical for order_items population.

---

## 📌 FINAL RECOMMENDATIONS FOR order_items TABLE

### Field Mapping

```python
order_items.unit_price = product["price"]  # ✅ Selling price (may include IVA)

order_items.quantity = product["real_quantity"]  # ✅ If exists, else "quantity"

order_items.subtotal = product["real_amount_neto"]  # ✅ CRITICAL: Use actual invoiced amount

# Optional: Calculate discount amount
calculated_amount = product["price"] * product["real_quantity"]
if abs(calculated_amount - product["real_amount_neto"]) > 1:
    order_items.discount_amount = calculated_amount - product["real_amount_neto"]
else:
    order_items.discount_amount = 0
```

### Why use real_amount_neto?

1. **It's the ACTUAL invoiced amount** - this is what the customer paid
2. **It includes ALL discounts** (explicit and implicit)
3. **It handles IVA correctly** (net amount without tax)
4. **94.5% of discounts are implicit** - only real_amount_neto captures them

### Tax Consideration

**IVA (19%) is added at DTE level**, not product level:
- `product.price` may be WITH or WITHOUT IVA
- `product.real_amount_neto` is always NET (without IVA)
- DTE totals include IVA separately

---

## 9. Data Quality Issues Found

### 1. Inconsistent IVA Treatment

- Some products have price WITH IVA (-16% pattern)
- Others have price WITHOUT IVA (matches real_amount_neto)
- **No reliable flag to distinguish**

### 2. Missing Discount Field

- 5,570 products have implicit discounts
- discount field is NULL
- **Can't distinguish between IVA and commercial discounts**

### 3. Rare Quantity Adjustments

- 20 cases where quantity ≠ real_quantity
- Likely returns or cancellations
- **real_quantity is authoritative**

---

## 10. Customer-Specific Patterns

### Cencosud (Customer 596810)

- 266 products with explicit 20% discount
- discount field always populated
- Largest client with negotiated discounts

### Web Orders (Channel 1448)

- Many products with -16% pattern
- Suggests web orders have different pricing structure
- Possible B2C (with IVA) vs B2B (without IVA) pricing

---

## 📊 Summary Statistics

```
Total Products Analyzed:    12,087
Total DTEs:                  5,422

Field Completeness:
  price:                    100.0% ✅
  quantity:                 100.0% ✅
  real_quantity:            100.0% ✅
  real_amount_neto:         100.0% ✅
  unit_cost:                 99.9% ✅
  discount:                   2.3% ⚠️
  surcharge:                  0.0% ❌

Amount Discrepancies:
  Matches calculation:      51.2%
  Differs:                  48.8%
    - Rounding (<$1):        0.9%
    - Explicit discount:     4.6%
    - Implicit discount:    94.5% 🔍

Top Discount Patterns:
  -16% (IVA):              3,277 products (55.6%)
  -24%:                      792 products (13.4%)
  -20% (Cencosud):           329 products (5.6%)
```

---

## 🎯 Action Items

1. ✅ **Use real_amount_neto for subtotal** (captures all discounts)
2. ✅ **Use real_quantity for quantity** (handles adjustments)
3. ✅ **Use price for unit_price** (selling price)
4. ⚠️ **Consider IVA implications** when analyzing pricing
5. 📊 **Monitor -16% pattern** - may indicate IVA handling issues in source data

---

**Analysis completed:** 2025-11-10
**Scripts used:**
- `eda_product_fields.py`
- `deep_dive_amount_discrepancies.py`

**Next step:** Populate order_items table with confidence using these mappings.
