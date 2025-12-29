# Sales Analytics Alignment with Desglose Pedidos

**Date**: 2025-12-24
**Session Goal**: Align `/dashboard/sales-analytics` with `/dashboard/orders` (Desglose Pedidos tab)

## Problem Statement

The Sales Analytics page had multiple inconsistencies with the Desglose Pedidos reference implementation:

1. **Categories**: Showed 8 categories vs Desglose's 4
2. **Temporal Filters**: "Por mes" didn't work (required both year AND month)
3. **Grouping**: "Cliente" option crashed with large datasets, "Formato" showed legacy values
4. **Search**: No search functionality (Desglose has multi-field search)
5. **Units**: Needed verification that calculations matched

## Changes Made

### Phase 1: Product Categories

**File**: `frontend/components/sales-analytics/FiltersSidebar.tsx`

```typescript
// BEFORE (line 49)
const categories = props.availableCategories || ['BARRAS', 'CRACKERS', 'GRANOLAS', 'KEEPERS', 'CAJA MASTER', 'DESPACHOS', 'ALIANZA', 'OTROS']

// AFTER
const categories = props.availableCategories || ['BARRAS', 'CRACKERS', 'GRANOLAS', 'KEEPERS']
```

Also removed unused category icons for CAJA MASTER, DESPACHOS, ALIANZA, OTROS.

---

### Phase 2: Temporal Filters

**Files**:
- `frontend/components/sales-analytics/FiltersSidebar.tsx`
- `frontend/app/dashboard/sales-analytics/page.tsx`

**Problem**: When user selected "Por mes", they had to also select a year - but the UI only showed month buttons.

**Solution**:
1. Show year selection buttons when "Por mes" is selected
2. Default to current year if no year is selected

```typescript
// FiltersSidebar.tsx - Show years for both 'year' and 'month' modes
{(props.dateFilterType === 'year' || props.dateFilterType === 'month') && (
  <div className="mb-3">
    {props.dateFilterType === 'month' && (
      <label className="block text-xs text-gray-600 mb-2">Selecciona año(s):</label>
    )}
    <div className="flex flex-wrap gap-2">
      {years.map(year => (...))}
    </div>
  </div>
)}

// page.tsx - Default to current year
} else if (dateFilterType === 'month' && selectedMonths.length > 0) {
  const yearsToUse = selectedYears.length > 0
    ? selectedYears
    : [new Date().getFullYear().toString()]
  // ... rest of logic
}
```

---

### Phase 3: Grouping Options

**File**: `frontend/components/sales-analytics/FiltersSidebar.tsx`

**Changes**:
1. Removed "Cliente" from groupByOptions (crashed with large datasets)
2. Removed "Cliente" from stackBy options
3. Fixed format values to match database schema

```typescript
// BEFORE
const groupByOptions = [
  { value: '', label: 'Sin agrupación' },
  { value: 'category', label: 'Familia' },
  { value: 'channel', label: 'Canal' },
  { value: 'customer', label: 'Cliente' },  // REMOVED
  { value: 'format', label: 'Formato' },
  { value: 'sku_primario', label: 'SKU Primario' },
]

// Format values - BEFORE
const formats = props.availableFormats || ['X1', 'X5', 'X16', 'Caja Master']

// Format values - AFTER (matches database package_type)
const formats = props.availableFormats || ['DISPLAY', 'GRANEL', 'DOYPACK', 'SACHET', 'BANDEJA', 'UNIDAD']
```

---

### Phase 4: Search Functionality

**Files**:
- `frontend/app/dashboard/sales-analytics/page.tsx` - State management
- `frontend/components/sales-analytics/FiltersSidebar.tsx` - UI + props
- `backend/app/api/sales_analytics.py` - Backend filtering

**Frontend Changes**:

```typescript
// page.tsx - Added state
const [searchTerm, setSearchTerm] = useState<string>('')
const [debouncedSearch, setDebouncedSearch] = useState<string>('')

// Debounce effect
useEffect(() => {
  const timer = setTimeout(() => {
    setDebouncedSearch(searchTerm)
    setCurrentPage(1)
  }, 300)
  return () => clearTimeout(timer)
}, [searchTerm])

// Added to API call
if (debouncedSearch) {
  params.append('search', debouncedSearch)
}
```

**Backend Changes**:

```python
# sales_analytics.py - Added parameter
search: Optional[str] = Query(None, description="Search across customer, channel, category, SKU primario"),

# Added filter logic
if search and search.strip():
    search_term = f"%{search.strip()}%"
    search_conditions = """(
        mv.customer_name ILIKE %s OR
        mv.channel_name ILIKE %s OR
        mv.category ILIKE %s OR
        mv.sku_primario ILIKE %s OR
        mv.product_name ILIKE %s
    )"""
    where_clauses.append(search_conditions)
    params.extend([search_term] * 5)
```

---

### Phase 5: Unit Calculations Verification

**Result**: Already aligned via migration 023

The materialized view `sales_facts_mv` applies:
1. `quantity_multiplier` from sku_mappings → `units_sold`
2. `units_per_display` for regular products
3. `items_per_master_box` for caja master products

Sales Analytics query:
```sql
SUM(
    CASE
        WHEN mv.is_caja_master THEN mv.units_sold * COALESCE(mv.items_per_master_box, 1)
        ELSE mv.units_sold * COALESCE(mv.units_per_display, 1)
    END
) as total_units
```

This is equivalent to audit.py's `ProductCatalogService.calculate_units()` logic.

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/components/sales-analytics/FiltersSidebar.tsx` | Categories, grouping, formats, search UI |
| `frontend/app/dashboard/sales-analytics/page.tsx` | Temporal filters, search state, debounce |
| `backend/app/api/sales_analytics.py` | Search parameter and filter logic |

## Testing Checklist

- [ ] Categories show only 4 options (BARRAS, CRACKERS, GRANOLAS, KEEPERS)
- [ ] "Por mes" shows year + month selection
- [ ] "Por mes" defaults to current year when no year selected
- [ ] Grouping options don't include "Cliente"
- [ ] Format filter shows: DISPLAY, GRANEL, DOYPACK, SACHET, BANDEJA, UNIDAD
- [ ] Search filters results across multiple fields
- [ ] Search has 300ms debounce (doesn't trigger on every keystroke)
- [ ] Unit totals match between Sales Analytics and Desglose Pedidos

## Reference Files

- **Desglose Pedidos Frontend**: `frontend/components/AuditView.tsx`
- **Desglose Pedidos Backend**: `backend/app/api/audit.py`
- **Sales Analytics Frontend**: `frontend/app/dashboard/sales-analytics/page.tsx`
- **Sales Analytics Backend**: `backend/app/api/sales_analytics.py`
- **Materialized View**: `backend/migrations/023_add_quantity_multiplier_to_sales_mv.sql`
