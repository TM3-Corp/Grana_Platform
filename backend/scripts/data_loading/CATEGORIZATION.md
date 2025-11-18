# 🏷️ Product Categorization Scripts

## Overview

These scripts handle automatic categorization of products to ensure data completeness for analytics and filtering.

## Problem Statement

When importing data from external sources (RelBase, CSV exports, etc.), products may not have category assignments. This creates issues:

- **Analytics Impact**: Revenue from uncategorized products is invisible in filtered views
- **User Experience**: Filters don't show complete data
- **Data Quality**: Incomplete product metadata

**Real-world example**: In November 2024, we had 51 uncategorized SKUs representing $230.9M (42.1% of total revenue).

## Scripts

### 1. `investigate_uncategorized_products.py`

**Purpose**: Diagnose data quality issues and analyze uncategorized products.

**Usage**:
```bash
# Text output (human-readable)
python3 scripts/data_loading/investigate_uncategorized_products.py

# JSON output (for automation/CI)
python3 scripts/data_loading/investigate_uncategorized_products.py --output-format json
```

**What it does**:
- Shows total revenue distribution by category
- Identifies products without category assignment
- Calculates revenue impact of missing categories
- Lists top uncategorized SKUs by revenue
- Provides actionable recommendations

**Example output**:
```
⚠️  DATA QUALITY ISSUE DETECTED:
   • 51 SKUs without category
   • $230,928,910 in uncategorized revenue (42.1% of total)

💡 Recommendation: Run auto_categorize_products.py to fix
```

**Exit codes**:
- `0`: All products categorized
- `1`: Uncategorized products found

---

### 2. `auto_categorize_products.py`

**Purpose**: Automatically categorize uncategorized products using intelligent matching.

**Usage**:
```bash
# Dry-run (see what would be done)
python3 scripts/data_loading/auto_categorize_products.py --dry-run --verbose

# Execute categorization
python3 scripts/data_loading/auto_categorize_products.py

# Verbose output (show all details)
python3 scripts/data_loading/auto_categorize_products.py --verbose
```

**Categorization Strategy** (3-step approach):

1. **Method 1: Exact Match in product_catalog**
   - Matches SKU exactly against `product_catalog` table
   - **Confidence**: HIGH
   - Example: `CRPM_U13520` → CRACKERS

2. **Method 2: Match without ANU- prefix**
   - Removes legacy "ANU-" prefix and searches `product_catalog`
   - **Confidence**: HIGH
   - Example: `ANU-BAKC_U04010` → matches `BAKC_U04010` → BARRAS

3. **Method 3: Keyword-based Auto-categorization**
   - Analyzes product name for category keywords
   - **Confidence**: MEDIUM
   - Keyword mapping:
     - "barra", "barrita" → **BARRAS**
     - "cracker" → **CRACKERS**
     - "granola" → **GRANOLAS**
     - "keeper" → **KEEPERS**
     - "caja master" → **CAJA MASTER**
     - "despacho", "pack" → **DESPACHOS**
     - "refacturación", "productos varios" → **OTROS**

**What it does**:
- Queries uncategorized products from database
- Loads product catalog for reference
- Applies 3-step categorization strategy
- Updates `products` table with assigned categories
- Reports automation rate and manual review cases

**Example output**:
```
📋 CATEGORIZATION REPORT
✅ Method 1 - Catalog (exact match):        1 SKUs
✅ Method 2 - Catalog (without ANU- prefix): 18 SKUs
⚠️  Method 3 - Keyword matching:             32 SKUs
❌ Manual review needed:                    0 SKUs

📊 Total automated: 51/51 (100.0%)

🚀 EXECUTING DATABASE UPDATES
✅ Updated: ANU-BAKC_U04010 → BARRAS
✅ Updated: ANU-BACM_U04010 → BARRAS
...
✅ Updates completed: 41 products categorized
```

**Exit codes**:
- `0`: All products categorized successfully
- `1`: Some products need manual review

---

## Workflow: Data Loading + Categorization

### Recommended Workflow

When importing new data (e.g., via GitHub Actions):

```bash
# Step 1: Load data from source
python3 scripts/data_loading/load_complete_2025_data.py

# Step 2: Check for categorization issues
python3 scripts/data_loading/investigate_uncategorized_products.py

# Step 3: Auto-categorize if needed
if [ $? -eq 1 ]; then
  python3 scripts/data_loading/auto_categorize_products.py
fi

# Step 4: Verify success
python3 scripts/data_loading/investigate_uncategorized_products.py
```

### GitHub Actions Integration

```yaml
name: Load and Categorize Data

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  load-data:
    runs-on: ubuntu-latest
    steps:
      - name: Load data from RelBase
        run: python3 scripts/data_loading/load_complete_2025_data.py

      - name: Check categorization
        id: check
        run: |
          python3 scripts/data_loading/investigate_uncategorized_products.py --output-format json > uncategorized.json
          echo "has_issues=$(jq '.products_with_null_category.skus_with_null_category > 0' uncategorized.json)" >> $GITHUB_OUTPUT

      - name: Auto-categorize products
        if: steps.check.outputs.has_issues == 'true'
        run: python3 scripts/data_loading/auto_categorize_products.py

      - name: Verify categorization
        run: python3 scripts/data_loading/investigate_uncategorized_products.py
```

---

## Database Schema Requirements

### Tables Used

**`products`** (updated by auto_categorize_products.py):
- `id`: Product ID
- `sku`: Product SKU (unique identifier)
- `category`: Product category (BARRAS, CRACKERS, etc.)
- `name`: Product name
- `updated_at`: Last update timestamp

**`product_catalog`** (reference for categorization):
- `sku`: Product SKU
- `category`: Product category
- `product_name`: Product name

**`orders` + `order_items`** (analyzed for uncategorized revenue):
- Used to calculate revenue impact
- Joined with `products` on `sku`

---

## Categories

Standard product categories:

| Category | Spanish | Examples |
|----------|---------|----------|
| BARRAS | Barras/Barritas | Barra Keto Cacao, Barra Low Carb |
| CRACKERS | Crackers | Crackers Sal de Mar, Crackers Romero |
| GRANOLAS | Granolas | Granola Almendras, Granola Cacao |
| KEEPERS | Keepers | Keeper Mix |
| CAJA MASTER | Cajas Master | Caja Master Crackers |
| DESPACHOS | Despachos/Packs | Pack Dieciochero |
| ALIANZA | Alianzas | Productos de alianzas comerciales |
| OTROS | Otros | Refacturaciones, productos varios |

---

## Configuration

### Environment Variables

Scripts use standard database configuration from `.env`:

```env
# Uses Transaction Pooler (IPv4 compatible for WSL2)
DATABASE_URL=postgresql://postgres.lypuvibmtxjaxmcmahxr:[PASSWORD]@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

**Important**: Uses **Transaction Pooler** (port 6543) for IPv4 compatibility on free Supabase plan.

---

## Troubleshooting

### Issue: "Network is unreachable"

**Problem**: Trying to use Direct Connection (IPv6) instead of Transaction Pooler (IPv4).

**Solution**: Scripts automatically load `.env` with `override=True` to ensure correct DATABASE_URL.

If still failing:
```bash
# Check which DATABASE_URL is being used
python3 -c "from dotenv import load_dotenv; load_dotenv(override=True); import os; print(os.getenv('DATABASE_URL'))"
```

### Issue: "All products are categorized" but dashboard shows missing data

**Problem**: Frontend cache or API response cache.

**Solution**: Restart backend or clear frontend cache.

### Issue: Some products still need manual review

**Problem**: Product name doesn't match any keyword pattern.

**Solution**:
1. Check product name with investigation script
2. Either:
   - Add product to `product_catalog` table, OR
   - Add keyword pattern to `auto_categorize_by_keywords()` function, OR
   - Manually UPDATE the product category in database

---

## Performance Notes

- **Investigation script**: ~2 seconds for 1,600 orders
- **Auto-categorization**: ~5 seconds for 51 SKUs
- **Database impact**: Minimal (simple UPDATE queries)

---

## Historical Data

### November 2024 Categorization

**Problem**: 51 uncategorized SKUs, $230.9M uncategorized revenue (42.1% of total)

**Solution**: Ran `auto_categorize_products.py`

**Results**:
- Method 1 (exact match): 1 SKU
- Method 2 (without ANU- prefix): 18 SKUs
- Method 3 (keywords): 32 SKUs
- **Total automated**: 51/51 (100%)
- **Manual review needed**: 0

**Impact**:
- BARRAS: +$137M (+77%)
- CRACKERS: +$48M (+445%)
- GRANOLAS: +$32M (+616%)

---

## Maintenance

### Adding New Categories

To add a new category:

1. Update `auto_categorize_by_keywords()` in `auto_categorize_products.py`:
```python
elif 'new_keyword' in name_lower:
    return 'NEW_CATEGORY'
```

2. Update category list in this documentation

3. Test with dry-run:
```bash
python3 scripts/data_loading/auto_categorize_products.py --dry-run --verbose
```

### Updating product_catalog

Preferred approach: Keep `product_catalog` table updated with all active products.

This ensures Method 1 and Method 2 (highest confidence) can categorize most products automatically.

---

**Last Updated**: 2025-11-18
**Author**: Claude Code
