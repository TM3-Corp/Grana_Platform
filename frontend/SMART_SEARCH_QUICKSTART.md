# 🚀 Smart Search - Quick Start Guide

## What Is It?

Intelligent fuzzy product search that finds products across all your sales channels (Shopify, MercadoLibre, Manual) even when they have different names.

**Example**: Search "barrita keto" and find both:
- Shopify: "Barra Keto Nuez"
- MercadoLibre: "Barrita Keto Nuez 5 Unidades"

---

## For End Users

### How to Use

1. **Go to Products Page**: `/dashboard/products`

2. **Type your search**: Examples:
   - `keto nuez` - Find keto products with nuts
   - `barrita` - Find all bar products
   - `BARR-KETO-01` - Search by SKU
   - `low carb chocolate` - Multi-word search

3. **Use Suggestions**: Click on suggestion chips that appear:
   - 💡 **Did you mean**: Try similar terms
   - 🏷️ **Filter**: Show only one category
   - 🔗 **Related**: Discover related products

4. **Click Results**: Yellow highlights show where your search matched

5. **Clear Search**: Click "Limpiar búsqueda" to return to normal view

### Tips

✅ **Spelling doesn't matter**: "queto" finds "keto"
✅ **Word order doesn't matter**: "nuez keto" = "keto nuez"
✅ **Variations work**: "barra", "barrita", "barritas" all work
✅ **Try suggestions**: They're designed to help you find what you need

---

## For Administrators

### View Analytics

Go to: `/dashboard/analytics`

**What You'll See**:
- How many searches per day
- Most popular search terms
- Searches with no results (products to add!)
- Which channels users prefer (Shopify/ML/Manual)
- Click-through rates

**Use This Data To**:
- Add products users are searching for
- Improve product names for discoverability
- Understand customer preferences

---

## For Developers

### Files Overview

```
Core Search Logic:
  lib/searchConfig.ts         - Fuzzy search configuration
  hooks/useSmartSearch.ts     - React hook with search logic

UI Components:
  components/SmartSearchBar.tsx           - Search input
  components/HighlightedProductCard.tsx   - Result cards

Analytics:
  lib/searchAnalytics.ts                  - Client-side tracking
  app/api/v1/products/search/track/*      - Server endpoints

Analytics Dashboard:
  app/dashboard/analytics/page.tsx        - View search stats

Integration:
  app/dashboard/products/page.tsx         - Products page with search
```

### Quick Implementation

```typescript
import { useSmartSearch } from '@/hooks/useSmartSearch'
import SmartSearchBar from '@/components/SmartSearchBar'

function MyPage({ products }) {
  const { search, searchQuery, setSearchQuery, suggestions } = useSmartSearch(products)
  const results = search(searchQuery)

  return (
    <>
      <SmartSearchBar
        value={searchQuery}
        onChange={setSearchQuery}
        suggestions={suggestions}
      />
      {results.map(r => <div key={r.product.id}>{r.product.name}</div>)}
    </>
  )
}
```

### Run Tests

```bash
# Setup (first time only)
npm install --save-dev jest @testing-library/react @testing-library/jest-dom

# Run tests
npm test

# See test documentation
cat __tests__/README.md
```

### Customize Search

**Add new term variations** (`lib/searchConfig.ts`):
```typescript
export const termVariations = {
  // Add your variations
  'energia': ['energia', 'energetica', 'energético'],
}
```

**Adjust sensitivity** (`lib/searchConfig.ts`):
```typescript
export const fuseOptions = {
  threshold: 0.5,  // Lower = more strict, Higher = more lenient
  distance: 150,   // Max characters to search
}
```

---

## Common Issues

### "No results found"

**If searching for existing product**:
1. Check product is loaded: Open browser console, check Network tab
2. Try variations: "barra" instead of "barrita"
3. Check spelling: "keto" not "queto" (though typos should work)

**If product really doesn't exist**:
- This is expected behavior
- Check Analytics dashboard for common "no results" searches
- Consider adding those products to catalog

### "Search is slow"

**If >500 products**:
- Consider server-side search
- See `SMART_SEARCH_GUIDE.md` for scaling recommendations

**If <500 products**:
- Check browser DevTools Performance tab
- Look for other performance issues on page
- Ensure products are memoized: `useMemo(() => products, [products])`

### "Analytics not updating"

**Check**:
1. Analytics tracking is called: `useSearchAnalytics()`
2. LocalStorage enabled: Check browser settings
3. API endpoints working: `/api/v1/products/search/track`

---

## Key Features

### ✅ Fuzzy Matching
Finds products even with typos, variations, or different word order

### ✅ Cross-Channel
Shows products from Shopify, MercadoLibre, and Manual entries

### ✅ Intelligent Suggestions
Offers category filters, term variations, and related terms

### ✅ Visual Highlighting
Yellow highlights show exactly where matches occurred

### ✅ Real-Time Analytics
Tracks searches, clicks, and user behavior

### ✅ Mobile Responsive
Works great on phones and tablets

### ✅ Performance Optimized
Searches 100+ products in <100ms

---

## Next Steps

1. **Read Full Guide**: `SMART_SEARCH_GUIDE.md` for complete documentation
2. **Check Tests**: `__tests__/README.md` for testing guide
3. **View Analytics**: Go to `/dashboard/analytics`
4. **Customize**: Edit `lib/searchConfig.ts` for your needs

---

## Support

- **Full Documentation**: `SMART_SEARCH_GUIDE.md`
- **Test Documentation**: `__tests__/README.md`
- **Issues**: Report to development team

---

## Version

**v1.0.0** - Released 2025-10-12

Features:
- Fuzzy search with Fuse.js
- Multi-channel product matching
- 3 types of intelligent suggestions
- Analytics tracking + dashboard
- Comprehensive test suite
- Mobile responsive UI

---

*Happy searching! 🔍*
