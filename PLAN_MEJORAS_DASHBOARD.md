# 🎯 PLAN ULTRA-DETALLADO: MEJORAS DASHBOARD GRANA

**Fecha:** 12 Octubre 2025
**Proyecto:** Grana Platform
**Objetivo:** Mejorar visualización de datos para Macarena Vicuña
**Modo:** Ultrathink Planning

---

## 📊 CONTEXTO ACTUAL

### Data Cargada (100% completa 2025)
- **1,505 órdenes** (Shopify: 1,241 | MercadoLibre: 261 | Manual: 3)
- **$44,391,148 CLP** en ventas totales
- **93 productos** (Shopify: 53 | MercadoLibre: 34 | Sin fuente: 6)
- **1,090 clientes únicos**
- **Período:** Enero 2025 - Octubre 2025

### Stack Técnico
```
Frontend: Next.js 15.5.4 + TypeScript + Tailwind CSS
Backend:  FastAPI + Python 3.12
Database: Supabase (PostgreSQL)
Current:  http://localhost:3000/dashboard
```

### Páginas Existentes
```
/dashboard           → Vista general (básica)
/dashboard/orders    → Lista de órdenes (filtros: mes, fuente)
/dashboard/products  → Lista de productos (filtro: fuente)
```

---

## 🎯 MEJORAS A IMPLEMENTAR

### 1. 📄 PAGINACIÓN ESCALABLE
**Problema:** Actualmente carga todas las órdenes de una vez (limit=2000)
**Solución:** Paginación server-side con UI amigable
**Impacto:** Preparación para crecimiento futuro

### 2. 🔍 BÚSQUEDA INTELIGENTE CON SUGERENCIAS
**Problema:** Sin forma de buscar productos específicos rápidamente
**Solución:** Búsqueda fuzzy con sugerencias en tiempo real
**Impacto:** Mejora UX y productividad de Macarena

### 3. 📊 GRÁFICOS DE VENTAS
**Problema:** Sin visualización de tendencias ni análisis temporal
**Solución:** Dashboard con múltiples gráficos interactivos
**Impacto:** Toma de decisiones basada en data visual

---

## 📐 ARQUITECTURA GENERAL

```
┌─────────────────────────────────────────────────────┐
│              FRONTEND (Next.js)                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  /dashboard                                         │
│    ├─ KPI Cards                                    │
│    ├─ SalesLineChart (📈 Recharts)                │
│    ├─ SourcePieChart (📊 Recharts)                │
│    └─ MonthlyBarChart (📊 Recharts)               │
│                                                     │
│  /dashboard/orders                                  │
│    ├─ SearchBar (🔍 con debounce)                 │
│    ├─ Filters (mes, fuente)                       │
│    ├─ OrdersList                                   │
│    └─ Pagination Component                         │
│                                                     │
│  /dashboard/products                                │
│    ├─ SmartSearch (🔍 Fuse.js)                    │
│    ├─ SearchSuggestions                            │
│    ├─ ProductsGrid                                 │
│    └─ Pagination Component                         │
│                                                     │
└─────────────────────────────────────────────────────┘
                         ↓
         ┌───────────────────────────────┐
         │      API (FastAPI)            │
         ├───────────────────────────────┤
         │  GET /api/v1/orders           │
         │    ?limit=50&offset=0         │
         │    &source=&month=            │
         │                               │
         │  GET /api/v1/orders/analytics │
         │    ?start_date=&end_date=     │
         │    &group_by=month            │
         │                               │
         │  GET /api/v1/products/search  │
         │    ?q=bara&limit=10           │
         └───────────────────────────────┘
                         ↓
              ┌─────────────────┐
              │  SUPABASE (DB)  │
              ├─────────────────┤
              │  orders         │
              │  products       │
              │  customers      │
              │  order_items    │
              └─────────────────┘
```

---

## 🔧 PARTE 1: PAGINACIÓN ESCALABLE

### 📋 Análisis Detallado

**¿Por qué paginación?**
- **Actualmente:** 1,505 órdenes cargadas de una vez (funcionable pero no escalable)
- **Futuro:** Si Grana crece a 5,000+ órdenes, el navegador se ralentizará
- **Performance:** Reducir carga inicial de ~2MB a ~200KB por página

**Estrategias evaluadas:**

| Estrategia              | Pros                      | Contras                    | Decisión |
|-------------------------|---------------------------|----------------------------|----------|
| Client-Side Pagination  | Simple, sin API changes   | Carga todo igual           | ❌       |
| Offset-based (SQL)      | Simple, API ya lo tiene   | Lento con offsets grandes  | ✅       |
| Cursor-based (SQL)      | Muy eficiente             | Complejo de implementar    | 🔮 Futuro|

**Decisión:** Implementar Offset-based ahora (el API ya lo soporta)

### 🎨 Diseño de UI

```
┌──────────────────────────────────────────────────────┐
│  📦 ÓRDENES (1,505)                      🔍 [Search] │
├──────────────────────────────────────────────────────┤
│                                                       │
│  [Filtro Fuente ▾]  [Filtro Mes ▾]                  │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │ #GRANA-1505  │ Shopify  │ $45,000 │ Oct 10  │   │
│  │ #GRANA-1504  │ ML       │ $12,500 │ Oct 10  │   │
│  │ ...          │ ...      │ ...     │ ...     │   │
│  │ #GRANA-1456  │ Shopify  │ $32,100 │ Oct 9   │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  📄 Mostrando 1-50 de 1,505 órdenes                 │
│                                                       │
│  [Mostrar: 25▾ 50▾ 100▾]  [Ir a pág: __]           │
│                                                       │
│  [ ◄◄ Primera ] [ ◄ Anterior ] [1] 2 3 ... 31      │
│  [ Siguiente ► ] [ Última ►► ]                      │
└──────────────────────────────────────────────────────┘
```

### 🔨 Implementación

#### Backend Changes (Mínimos - API ya listo)

```python
# app/api/orders.py - YA EXISTE ✅
@router.get("/orders/")
async def get_orders(
    source: Optional[str] = None,
    limit: int = Query(50, ge=1, le=5000),  # ✅ Ya aumentado
    offset: int = Query(0, ge=0)            # ✅ Ya existe
):
    # ... query logic

    # MEJORAR: Agregar total count en response
    cursor.execute("SELECT COUNT(*) FROM orders WHERE ...")
    total_count = cursor.fetchone()[0]

    return {
        "status": "success",
        "total": total_count,      # ← AGREGAR ESTO
        "count": len(orders),
        "limit": limit,            # ← AGREGAR ESTO
        "offset": offset,          # ← AGREGAR ESTO
        "data": orders
    }
```

**Cambios necesarios en backend:**
1. ✅ Agregar `total` count en response de `/orders`
2. ✅ Agregar `total` count en response de `/products`
3. ✅ Incluir `limit` y `offset` en response para que frontend sepa el estado

#### Frontend - Componente Pagination

```typescript
// components/Pagination.tsx (NUEVO)
interface PaginationProps {
  currentPage: number
  totalItems: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
}

export default function Pagination({
  currentPage,
  totalItems,
  pageSize,
  onPageChange,
  onPageSizeChange
}: PaginationProps) {
  const totalPages = Math.ceil(totalItems / pageSize)
  const startItem = (currentPage - 1) * pageSize + 1
  const endItem = Math.min(currentPage * pageSize, totalItems)

  // Calcular páginas a mostrar (ej: 1 ... 5 6 [7] 8 9 ... 31)
  const getPageNumbers = () => {
    const pages: (number | string)[] = []
    const showPages = 5 // Mostrar 5 números de página

    if (totalPages <= showPages + 2) {
      // Pocas páginas, mostrar todas
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }

    // Siempre mostrar primera página
    pages.push(1)

    // Calcular rango alrededor de página actual
    let startPage = Math.max(2, currentPage - 1)
    let endPage = Math.min(totalPages - 1, currentPage + 1)

    // Agregar "..." si hay gap
    if (startPage > 2) pages.push('...')

    // Páginas del medio
    for (let i = startPage; i <= endPage; i++) {
      pages.push(i)
    }

    // Agregar "..." si hay gap al final
    if (endPage < totalPages - 1) pages.push('...')

    // Siempre mostrar última página
    pages.push(totalPages)

    return pages
  }

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-white border-t">
      {/* Info texto */}
      <div className="text-sm text-gray-600">
        Mostrando <span className="font-medium">{startItem}-{endItem}</span> de{' '}
        <span className="font-medium">{totalItems}</span> resultados
      </div>

      {/* Controles */}
      <div className="flex items-center gap-4">
        {/* Page size selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">Mostrar:</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
        </div>

        {/* Botones de navegación */}
        <div className="flex gap-1">
          <button
            onClick={() => onPageChange(1)}
            disabled={currentPage === 1}
            className="px-3 py-1 border rounded text-sm disabled:opacity-50"
          >
            ◄◄
          </button>

          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-3 py-1 border rounded text-sm disabled:opacity-50"
          >
            ◄
          </button>

          {/* Números de página */}
          {getPageNumbers().map((page, idx) => (
            page === '...' ? (
              <span key={`ellipsis-${idx}`} className="px-2 py-1">...</span>
            ) : (
              <button
                key={page}
                onClick={() => onPageChange(page as number)}
                className={`px-3 py-1 border rounded text-sm ${
                  currentPage === page
                    ? 'bg-green-600 text-white border-green-600'
                    : 'hover:bg-gray-100'
                }`}
              >
                {page}
              </button>
            )
          ))}

          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-3 py-1 border rounded text-sm disabled:opacity-50"
          >
            ►
          </button>

          <button
            onClick={() => onPageChange(totalPages)}
            disabled={currentPage === totalPages}
            className="px-3 py-1 border rounded text-sm disabled:opacity-50"
          >
            ►►
          </button>
        </div>
      </div>
    </div>
  )
}
```

#### Integración en OrdersPage

```typescript
// app/dashboard/orders/page.tsx - MODIFICAR

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)

  // AGREGAR estados de paginación
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [totalOrders, setTotalOrders] = useState(0)

  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [monthFilter, setMonthFilter] = useState<string>('')

  // MODIFICAR useEffect para usar paginación
  useEffect(() => {
    const fetchOrders = async () => {
      setLoading(true)
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL
        const offset = (currentPage - 1) * pageSize

        // Construir query params
        const params = new URLSearchParams({
          limit: pageSize.toString(),
          offset: offset.toString(),
          ...(sourceFilter && { source: sourceFilter }),
          ...(monthFilter && { month: monthFilter })
        })

        const response = await fetch(`${apiUrl}/api/v1/orders/?${params}`)
        const data: OrdersResponse = await response.json()

        setOrders(data.data)
        setTotalOrders(data.total)  // ← del backend

      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchOrders()
  }, [currentPage, pageSize, sourceFilter, monthFilter])  // ← dependencies

  // Handler para cambio de página
  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    window.scrollTo({ top: 0, behavior: 'smooth' })  // Scroll to top
  }

  // Handler para cambio de page size
  const handlePageSizeChange = (size: number) => {
    setPageSize(size)
    setCurrentPage(1)  // Reset a página 1
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      {/* ... header y filtros ... */}

      {/* Lista de órdenes */}
      <div className="bg-white rounded-lg shadow">
        {orders.map(order => (
          // ... render orden ...
        ))}
      </div>

      {/* AGREGAR componente de paginación */}
      <Pagination
        currentPage={currentPage}
        totalItems={totalOrders}
        pageSize={pageSize}
        onPageChange={handlePageChange}
        onPageSizeChange={handlePageSizeChange}
      />
    </div>
  )
}
```

### ✅ Testing Plan

**Test Cases:**
1. ✅ Navegar a página 2, 3, última
2. ✅ Cambiar page size (25, 50, 100)
3. ✅ Aplicar filtro y verificar que resetea a página 1
4. ✅ Verificar conteo correcto en todas las páginas
5. ✅ Verificar botones disabled en primera/última página
6. ✅ Verificar scroll to top al cambiar página
7. ✅ Verificar responsiveness en móvil

### 📊 Métricas de Éxito
- ⏱️ Tiempo de carga inicial reducido de ~2s a ~0.5s
- 💾 Payload reducido de ~2MB a ~200KB por request
- 🎯 UX mejorada con navegación intuitiva

---

## 🔧 PARTE 2: BÚSQUEDA INTELIGENTE CON SUGERENCIAS

### 📋 Análisis Detallado

**¿Por qué búsqueda inteligente?**
- **Problema actual:** 93 productos, sin forma rápida de encontrar uno específico
- **Caso de uso real:** Macarena quiere buscar "barrita chocolate" pero el nombre exacto es "Barra Cereal Grana Chocolate Dark"
- **Solución:** Fuzzy search que tolera errores de tipeo y nombres parciales

**Ejemplos de búsquedas:**
```
Usuario escribe:      Debe encontrar:
"bara"              → "Barra Cereal...", "Barrita de Chía"
"chocolat"          → "Chocolate Dark", "Chocolate Milk"
"chia"              → "Barrita de Chía", "Chía Protein"
"souber"            → "Sour Berries" (tolera typo)
"MLC163"            → Producto con SKU MLC1630337051
```

### 🎨 Diseño de UI

```
┌──────────────────────────────────────────────────────┐
│  🔍 Buscar productos...                              │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ↓ (mientras escribe "bara")                         │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │ ✨ 8 resultados encontrados                      │ │
│  ├─────────────────────────────────────────────────┤ │
│  │ 📦 Barra Cereal Grana Chocolate Dark            │ │
│  │    SKU: SHOPIFY-12345 | $2,500                  │ │
│  │                                                  │ │
│  │ 📦 Barra Cereal Grana Sour Berries              │ │
│  │    SKU: SHOPIFY-12346 | $2,500                  │ │
│  │                                                  │ │
│  │ 📦 Barrita de Chía                              │ │
│  │    SKU: BARR-CHIA-01 | $1,800                   │ │
│  │                                                  │ │
│  │ 📦 Barrita Coco con Chocolate                   │ │
│  │    SKU: MLC1630337051 | $2,200                  │ │
│  │                                                  │ │
│  │ ... 4 más                                       │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 🔨 Implementación

#### Instalar Fuse.js (Fuzzy Search Library)

```bash
cd frontend
npm install fuse.js
```

**¿Por qué Fuse.js?**
- ✅ 4.3kB gzipped (muy ligero)
- ✅ Búsqueda fuzzy con scoring
- ✅ Búsqueda en múltiples campos
- ✅ Highlight de matches
- ✅ Sin dependencias

#### Backend - Endpoint de Búsqueda

```python
# app/api/products.py - AGREGAR

@router.get("/products/search")
async def search_products(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Búsqueda inteligente de productos
    Busca en: name, SKU, category, brand
    """
    if not q or len(q) < 2:
        return {
            "status": "error",
            "message": "Query must be at least 2 characters",
            "data": []
        }

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # PostgreSQL Full-Text Search con similitud
        query_lower = q.lower()

        cursor.execute("""
            SELECT
                id, sku, name, category, brand, source,
                sale_price, current_stock, min_stock, is_active,
                units_per_display, displays_per_box,
                -- Calcular relevancia
                CASE
                    WHEN LOWER(name) = %s THEN 100
                    WHEN LOWER(name) LIKE %s THEN 90
                    WHEN LOWER(sku) = %s THEN 85
                    WHEN LOWER(name) LIKE %s THEN 70
                    WHEN LOWER(sku) LIKE %s THEN 60
                    WHEN LOWER(category) LIKE %s THEN 50
                    WHEN LOWER(brand) LIKE %s THEN 40
                    ELSE 0
                END as relevance_score
            FROM products
            WHERE
                LOWER(name) LIKE %s
                OR LOWER(sku) LIKE %s
                OR LOWER(category) LIKE %s
                OR LOWER(brand) LIKE %s
            ORDER BY relevance_score DESC, name ASC
            LIMIT %s
        """, (
            query_lower,                    # exact name match
            f'{query_lower}%',              # name starts with
            query_lower,                    # exact SKU match
            f'%{query_lower}%',             # name contains
            f'%{query_lower}%',             # SKU contains
            f'%{query_lower}%',             # category contains
            f'%{query_lower}%',             # brand contains
            f'%{query_lower}%',             # WHERE name
            f'%{query_lower}%',             # WHERE sku
            f'%{query_lower}%',             # WHERE category
            f'%{query_lower}%',             # WHERE brand
            limit
        ))

        results = cursor.fetchall()

        return {
            "status": "success",
            "query": q,
            "count": len(results),
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
```

#### Frontend - Componente SearchBar

```typescript
// components/SearchBar.tsx (NUEVO)

import { useState, useEffect, useRef } from 'react'
import Fuse from 'fuse.js'

interface SearchBarProps {
  placeholder?: string
  onSearch: (query: string) => void
  onSelect?: (item: any) => void
  data: any[]
  searchKeys: string[]  // campos a buscar
  displayKey: string    // campo a mostrar
}

export default function SearchBar({
  placeholder = "Buscar...",
  onSearch,
  onSelect,
  data,
  searchKeys,
  displayKey
}: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)

  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Configurar Fuse.js
  const fuse = new Fuse(data, {
    keys: searchKeys,
    threshold: 0.4,           // 0 = exact, 1 = match anything
    distance: 100,            // max distance for fuzzy match
    includeScore: true,
    includeMatches: true,     // para highlighting
    minMatchCharLength: 2,
    ignoreLocation: true
  })

  // Debounced search
  useEffect(() => {
    if (query.length < 2) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    const timer = setTimeout(() => {
      const results = fuse.search(query)
      setSuggestions(results.slice(0, 8).map(r => r.item))
      setShowSuggestions(true)
      onSearch(query)
    }, 300)  // 300ms debounce

    return () => clearTimeout(timer)
  }, [query])

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightedIndex(prev =>
        Math.min(prev + 1, suggestions.length - 1)
      )
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightedIndex(prev => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter' && highlightedIndex >= 0) {
      handleSelect(suggestions[highlightedIndex])
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
      setHighlightedIndex(-1)
    }
  }

  const handleSelect = (item: any) => {
    setQuery('')
    setSuggestions([])
    setShowSuggestions(false)
    setHighlightedIndex(-1)
    onSelect?.(item)
  }

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="relative w-full">
      {/* Input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
        />
        <div className="absolute left-3 top-2.5 text-gray-400">
          🔍
        </div>
        {query && (
          <button
            onClick={() => setQuery('')}
            className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        )}
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto"
        >
          <div className="p-2 text-xs text-gray-500 bg-gray-50 border-b">
            ✨ {suggestions.length} resultado{suggestions.length !== 1 ? 's' : ''} encontrado{suggestions.length !== 1 ? 's' : ''}
          </div>

          {suggestions.map((item, idx) => (
            <div
              key={item.id}
              onClick={() => handleSelect(item)}
              className={`p-3 cursor-pointer border-b last:border-b-0 hover:bg-green-50 ${
                idx === highlightedIndex ? 'bg-green-50' : ''
              }`}
            >
              <div className="font-medium text-gray-900">
                📦 {item[displayKey]}
              </div>
              {item.sku && (
                <div className="text-xs text-gray-500 mt-1">
                  SKU: {item.sku}
                  {item.sale_price && ` | $${item.sale_price.toLocaleString('es-CL')}`}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* No results */}
      {showSuggestions && query.length >= 2 && suggestions.length === 0 && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg p-4 text-center text-gray-500">
          No se encontraron productos similares a "<span className="font-medium">{query}</span>"
        </div>
      )}
    </div>
  )
}
```

#### Integración en ProductsPage

```typescript
// app/dashboard/products/page.tsx - MODIFICAR

import SearchBar from '@/components/SearchBar'

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [allProducts, setAllProducts] = useState<Product[]>([])  // ← mantener copia completa
  const [searchActive, setSearchActive] = useState(false)

  useEffect(() => {
    const fetchProducts = async () => {
      // ... fetch logic ...
      setProducts(sortedProducts)
      setAllProducts(sortedProducts)  // ← guardar copia
    }
    fetchProducts()
  }, [])

  const handleSearch = (query: string) => {
    setSearchActive(query.length >= 2)
    // El SearchBar ya filtra con Fuse.js
  }

  const handleSelectProduct = (product: Product) => {
    // Navegar al producto seleccionado
    // O mostrar modal con detalles
    console.log('Producto seleccionado:', product)
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Productos</h1>

          {/* AGREGAR Search Bar */}
          <div className="mt-4">
            <SearchBar
              placeholder="Buscar productos por nombre, SKU, categoría..."
              onSearch={handleSearch}
              onSelect={handleSelectProduct}
              data={allProducts}
              searchKeys={['name', 'sku', 'category', 'brand']}
              displayKey="name"
            />
          </div>

          {/* Filtros existentes */}
          <div className="mt-4 flex gap-4">
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="px-4 py-2 border rounded-lg"
            >
              <option value="">Todas las fuentes</option>
              {/* ... */}
            </select>
          </div>
        </div>

        {/* Grid de productos */}
        {/* ... */}
      </div>
    </div>
  )
}
```

### ✅ Testing Plan

**Test Cases:**
1. ✅ Buscar producto por nombre exacto
2. ✅ Buscar con typo ("chocolat" → "chocolate")
3. ✅ Buscar por SKU parcial
4. ✅ Buscar sin resultados
5. ✅ Navegación con teclado (↑↓ Enter Escape)
6. ✅ Click fuera del dropdown para cerrar
7. ✅ Debounce funciona (no busca en cada tecla)
8. ✅ Seleccionar producto con mouse/teclado

### 📊 Métricas de Éxito
- ⏱️ Tiempo para encontrar un producto: de ~30s a ~3s
- 🎯 Precisión de búsqueda: >95% con nombres parciales
- 💡 UX: Sugerencias instantáneas (<300ms)

---

## 🔧 PARTE 3: GRÁFICOS DE VENTAS POR MES/FUENTE

### 📋 Análisis Detallado

**¿Por qué gráficos?**
- **Problema actual:** Macarena no puede ver tendencias de un vistazo
- **Data disponible:** 10 meses de ventas (Ene-Oct 2025) en 3 fuentes
- **Value:** Identificar picos, caídas, fuentes más rentables

**Gráficos necesarios:**

| Gráfico            | Tipo         | Propósito                          | Prioridad |
|--------------------|--------------|------------------------------------|-----------|
| Ventas por mes     | Line Chart   | Ver tendencia temporal             | 🔥 Alta   |
| Ventas por fuente  | Pie Chart    | Ver distribución de revenue        | 🔥 Alta   |
| Órdenes por mes    | Bar Chart    | Comparar volumen de pedidos        | ⭐ Media  |
| Top 5 productos    | Bar Chart    | Identificar best sellers           | ⭐ Media  |
| Ticket promedio    | Line Chart   | Ver evolución de ticket            | ⏳ Baja   |

### 🎨 Diseño de Dashboard

```
┌──────────────────────────────────────────────────────────────┐
│  📊 GRANA DASHBOARD 2025                                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ 💰 INGRESOS│  │ 📦 ÓRDENES │  │ 🎫 TICKET  │            │
│  │ $44.4M CLP │  │   1,505    │  │  $29.5K    │            │
│  │  ↑ 8.2%    │  │  ↑ 12.5%  │  │  ↓ 3.1%   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  📈 VENTAS POR MES (Enero - Octubre 2025)                   │
│                                                               │
│  12M ┤                                                       │
│  10M ┤                                     ●────●            │
│   8M ┤                           ●────●    │                │
│   6M ┤                     ●────●          │                │
│   4M ┤           ●────●    │               │                │
│   2M ┤   ●──●────│         │               │                │
│   0  ┴────┴─────┴─────────┴───────────────┴────────────────│
│      ENE FEB MAR ABR MAY JUN JUL AGO SEP OCT               │
│                                                               │
│   ─── Total    ─── Shopify    ─── MercadoLibre             │
│                                                               │
├─────────────────────────┬────────────────────────────────────┤
│                         │                                    │
│  📊 DISTRIBUCIÓN POR    │  🏆 TOP 5 PRODUCTOS               │
│      FUENTE             │                                    │
│                         │  ████████ Barra Chocolate $4.2M   │
│      92.3%              │  ██████ Barra Sour Berries $3.1M  │
│   ■ Shopify             │  ████ Barrita Chía $2.8M          │
│       ($40.9M)          │  ███ Mix Nuts $2.3M               │
│                         │  ██ Granola Bar $1.9M             │
│   6.7% ■ ML ($2.9M)     │                                    │
│   1.0% ■ Manual         │                                    │
│                         │                                    │
└─────────────────────────┴────────────────────────────────────┘
```

### 🔨 Implementación

#### Instalar Recharts

```bash
cd frontend
npm install recharts
```

**¿Por qué Recharts?**
- ✅ Componentes React nativos
- ✅ API declarativa y simple
- ✅ Responsive por defecto
- ✅ Bien documentado
- ✅ Animaciones suaves
- ✅ Tooltips interactivos

#### Backend - Endpoint de Analytics

```python
# app/api/orders.py - AGREGAR

@router.get("/orders/analytics")
async def get_analytics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    group_by: str = Query('month', enum=['day', 'week', 'month'])
):
    """
    Obtener analytics de ventas con diferentes agregaciones
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Filtros de fecha
        date_filter = ""
        params = []

        if start_date:
            date_filter += " AND order_date >= %s"
            params.append(start_date)
        if end_date:
            date_filter += " AND order_date <= %s"
            params.append(end_date)

        # 1. Ventas por período y fuente
        date_format = {
            'day': 'YYYY-MM-DD',
            'week': 'IYYY-IW',  # ISO week
            'month': 'YYYY-MM'
        }[group_by]

        cursor.execute(f"""
            SELECT
                TO_CHAR(order_date, %s) as period,
                source,
                COUNT(*) as order_count,
                SUM(total) as revenue,
                AVG(total) as avg_ticket
            FROM orders
            WHERE 1=1 {date_filter}
            GROUP BY period, source
            ORDER BY period, source
        """, [date_format] + params)

        sales_by_period_source = cursor.fetchall()

        # Transformar a estructura pivoteada
        periods = {}
        for row in sales_by_period_source:
            period = row['period']
            if period not in periods:
                periods[period] = {
                    'period': period,
                    'total_revenue': 0,
                    'total_orders': 0
                }

            periods[period][f"{row['source']}_revenue"] = float(row['revenue'])
            periods[period][f"{row['source']}_orders"] = row['order_count']
            periods[period]['total_revenue'] += float(row['revenue'])
            periods[period]['total_orders'] += row['order_count']

        sales_by_period = list(periods.values())

        # 2. Distribución por fuente (total)
        cursor.execute(f"""
            SELECT
                source,
                COUNT(*) as order_count,
                SUM(total) as revenue,
                AVG(total) as avg_ticket
            FROM orders
            WHERE 1=1 {date_filter}
            GROUP BY source
            ORDER BY revenue DESC
        """, params)

        source_distribution = cursor.fetchall()

        # 3. Top productos
        cursor.execute(f"""
            SELECT
                p.name,
                p.sku,
                COUNT(DISTINCT o.id) as order_count,
                SUM(oi.quantity) as units_sold,
                SUM(oi.total) as revenue
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            JOIN products p ON p.id = oi.product_id
            WHERE 1=1 {date_filter}
            GROUP BY p.id, p.name, p.sku
            ORDER BY revenue DESC
            LIMIT 5
        """, params)

        top_products = cursor.fetchall()

        # 4. KPIs generales
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_orders,
                SUM(total) as total_revenue,
                AVG(total) as avg_ticket,
                MIN(order_date) as first_order,
                MAX(order_date) as last_order
            FROM orders
            WHERE 1=1 {date_filter}
        """, params)

        kpis = cursor.fetchone()

        # 5. Crecimiento mes a mes (solo si group_by='month')
        growth_rates = []
        if group_by == 'month' and len(sales_by_period) > 1:
            for i in range(1, len(sales_by_period)):
                prev = sales_by_period[i-1]['total_revenue']
                curr = sales_by_period[i]['total_revenue']
                growth = ((curr - prev) / prev * 100) if prev > 0 else 0
                growth_rates.append({
                    'period': sales_by_period[i]['period'],
                    'growth_rate': round(growth, 2)
                })

        return {
            "status": "success",
            "data": {
                "sales_by_period": sales_by_period,
                "source_distribution": source_distribution,
                "top_products": top_products,
                "kpis": {
                    "total_orders": kpis['total_orders'],
                    "total_revenue": float(kpis['total_revenue']),
                    "avg_ticket": float(kpis['avg_ticket']),
                    "first_order": kpis['first_order'].isoformat() if kpis['first_order'] else None,
                    "last_order": kpis['last_order'].isoformat() if kpis['last_order'] else None
                },
                "growth_rates": growth_rates
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
```

#### Frontend - Componente KPI Card

```typescript
// components/charts/KPICard.tsx (NUEVO)

interface KPICardProps {
  title: string
  value: string | number
  change?: number  // % change
  icon: string
  trend?: 'up' | 'down' | 'neutral'
}

export default function KPICard({
  title,
  value,
  change,
  icon,
  trend = 'neutral'
}: KPICardProps) {
  const trendColors = {
    up: 'text-green-600 bg-green-50',
    down: 'text-red-600 bg-red-50',
    neutral: 'text-gray-600 bg-gray-50'
  }

  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→'
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{icon}</span>
        {change !== undefined && (
          <span className={`text-sm px-2 py-1 rounded ${trendColors[trend]}`}>
            {trendIcons[trend]} {Math.abs(change).toFixed(1)}%
          </span>
        )}
      </div>

      <h3 className="text-sm text-gray-600 mb-1">{title}</h3>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </div>
  )
}
```

#### Frontend - Componente Sales Line Chart

```typescript
// components/charts/SalesLineChart.tsx (NUEVO)

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface SalesLineChartProps {
  data: Array<{
    period: string
    shopify_revenue?: number
    mercadolibre_revenue?: number
    manual_revenue?: number
    total_revenue: number
  }>
}

export default function SalesLineChart({ data }: SalesLineChartProps) {
  // Formatear data para español
  const formattedData = data.map(d => ({
    ...d,
    mes: new Date(d.period + '-01').toLocaleDateString('es-CL', { month: 'short', year: '2-digit' })
  }))

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        📈 Ventas por Mes (2025)
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="mes" />
          <YAxis
            tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
          />
          <Tooltip
            formatter={(value: number) => `$${value.toLocaleString('es-CL')} CLP`}
            labelStyle={{ color: '#000' }}
          />
          <Legend />

          <Line
            type="monotone"
            dataKey="total_revenue"
            stroke="#10B981"
            strokeWidth={3}
            name="Total"
            dot={{ r: 5 }}
          />
          <Line
            type="monotone"
            dataKey="shopify_revenue"
            stroke="#50E3C2"
            strokeWidth={2}
            name="Shopify"
            dot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="mercadolibre_revenue"
            stroke="#F5A623"
            strokeWidth={2}
            name="MercadoLibre"
            dot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

#### Frontend - Componente Source Pie Chart

```typescript
// components/charts/SourcePieChart.tsx (NUEVO)

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

interface SourcePieChartProps {
  data: Array<{
    source: string
    revenue: number
  }>
}

const COLORS = {
  shopify: '#50E3C2',
  mercadolibre: '#F5A623',
  manual: '#7B68EE'
}

const NAMES = {
  shopify: 'Shopify',
  mercadolibre: 'MercadoLibre',
  manual: 'Manual'
}

export default function SourcePieChart({ data }: SourcePieChartProps) {
  const total = data.reduce((sum, item) => sum + item.revenue, 0)

  const chartData = data.map(item => ({
    name: NAMES[item.source as keyof typeof NAMES] || item.source,
    value: item.revenue,
    percentage: ((item.revenue / total) * 100).toFixed(1)
  }))

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        📊 Distribución por Fuente
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percentage }) => `${name}: ${percentage}%`}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => {
              const source = data[index].source
              return (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[source as keyof typeof COLORS] || '#888'}
                />
              )
            })}
          </Pie>
          <Tooltip
            formatter={(value: number) => `$${value.toLocaleString('es-CL')} CLP`}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Leyenda customizada */}
      <div className="mt-4 space-y-2">
        {chartData.map((item, idx) => {
          const source = data[idx].source
          return (
            <div key={idx} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-4 h-4 rounded"
                  style={{ backgroundColor: COLORS[source as keyof typeof COLORS] }}
                />
                <span className="text-sm text-gray-700">{item.name}</span>
              </div>
              <span className="text-sm font-medium">
                ${(item.value / 1000000).toFixed(1)}M ({item.percentage}%)
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

#### Frontend - Componente Top Products Bar

```typescript
// components/charts/TopProductsBar.tsx (NUEVO)

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface TopProductsBarProps {
  data: Array<{
    name: string
    revenue: number
    units_sold: number
  }>
}

export default function TopProductsBar({ data }: TopProductsBarProps) {
  // Formatear nombres (truncar si son muy largos)
  const formattedData = data.map(item => ({
    ...item,
    shortName: item.name.length > 30 ? item.name.substring(0, 27) + '...' : item.name
  }))

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        🏆 Top 5 Productos
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={formattedData} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            type="number"
            tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
          />
          <YAxis
            type="category"
            dataKey="shortName"
            width={150}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === 'revenue') return [`$${value.toLocaleString('es-CL')} CLP`, 'Ingresos']
              return [value, 'Unidades']
            }}
          />
          <Bar dataKey="revenue" fill="#10B981" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
```

#### Dashboard Principal - Integración

```typescript
// app/dashboard/page.tsx - REESCRIBIR COMPLETO

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import KPICard from '@/components/charts/KPICard'
import SalesLineChart from '@/components/charts/SalesLineChart'
import SourcePieChart from '@/components/charts/SourcePieChart'
import TopProductsBar from '@/components/charts/TopProductsBar'

interface AnalyticsData {
  sales_by_period: any[]
  source_distribution: any[]
  top_products: any[]
  kpis: {
    total_orders: number
    total_revenue: number
    avg_ticket: number
  }
  growth_rates: any[]
}

export default function DashboardPage() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL
        const response = await fetch(`${apiUrl}/api/v1/orders/analytics?group_by=month`)

        if (!response.ok) throw new Error('Error fetching analytics')

        const result = await response.json()
        setData(result.data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando dashboard...</p>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-800 font-semibold text-lg mb-2">Error</h2>
          <p className="text-red-600">{error || 'No se pudieron cargar los datos'}</p>
        </div>
      </div>
    )
  }

  // Calcular crecimiento promedio
  const avgGrowth = data.growth_rates.length > 0
    ? data.growth_rates.reduce((sum, g) => sum + g.growth_rate, 0) / data.growth_rates.length
    : 0

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard Grana 2025</h1>
          <p className="mt-2 text-gray-600">
            Vista general de ventas, productos y tendencias
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <KPICard
            icon="💰"
            title="Ingresos Totales"
            value={`$${(data.kpis.total_revenue / 1000000).toFixed(1)}M CLP`}
            change={avgGrowth}
            trend={avgGrowth > 0 ? 'up' : avgGrowth < 0 ? 'down' : 'neutral'}
          />

          <KPICard
            icon="📦"
            title="Total Órdenes"
            value={data.kpis.total_orders.toLocaleString('es-CL')}
          />

          <KPICard
            icon="🎫"
            title="Ticket Promedio"
            value={`$${Math.round(data.kpis.avg_ticket).toLocaleString('es-CL')}`}
          />
        </div>

        {/* Main Chart */}
        <div className="mb-8">
          <SalesLineChart data={data.sales_by_period} />
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <SourcePieChart data={data.source_distribution} />
          <TopProductsBar data={data.top_products} />
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Acciones Rápidas
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              href="/dashboard/orders"
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
            >
              <span className="text-2xl">📦</span>
              <div>
                <div className="font-medium">Ver Órdenes</div>
                <div className="text-sm text-gray-600">
                  {data.kpis.total_orders} órdenes
                </div>
              </div>
            </Link>

            <Link
              href="/dashboard/products"
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
            >
              <span className="text-2xl">🏷️</span>
              <div>
                <div className="font-medium">Ver Productos</div>
                <div className="text-sm text-gray-600">
                  Gestionar inventario
                </div>
              </div>
            </Link>

            <button
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
              onClick={() => window.location.reload()}
            >
              <span className="text-2xl">🔄</span>
              <div>
                <div className="font-medium">Actualizar</div>
                <div className="text-sm text-gray-600">
                  Recargar datos
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

### ✅ Testing Plan

**Test Cases:**
1. ✅ Verificar datos del endpoint `/orders/analytics`
2. ✅ Line chart muestra todas las líneas correctamente
3. ✅ Pie chart suma 100%
4. ✅ Top products muestra los 5 más vendidos
5. ✅ KPI cards muestran cifras correctas
6. ✅ Tooltips funcionan en hover
7. ✅ Gráficos son responsive (mobile/desktop)
8. ✅ Colores consistentes entre gráficos

### 📊 Métricas de Éxito
- 📈 Tiempo para entender tendencias: de 5 minutos a 30 segundos
- 🎯 Identificación de mejores productos: instantánea
- 💡 Decisiones basadas en data: mejoradas por visualización clara

---

## 📅 CRONOGRAMA DE IMPLEMENTACIÓN

### SPRINT 1: GRÁFICOS (Día 1-2) - 🔥 PRIORIDAD ALTA
**Duración:** 4-5 horas

**Día 1 (2.5h):**
- ✅ Instalar Recharts
- ✅ Crear endpoint `/orders/analytics`
- ✅ Crear componente KPICard
- ✅ Crear componente SalesLineChart
- ✅ Testing inicial

**Día 2 (2h):**
- ✅ Crear SourcePieChart
- ✅ Crear TopProductsBar
- ✅ Integrar en dashboard principal
- ✅ Styling y responsiveness
- ✅ Testing completo

### SPRINT 2: BÚSQUEDA (Día 3) - ⭐ PRIORIDAD MEDIA
**Duración:** 3-4 horas

**Día 3 (3.5h):**
- ✅ Instalar Fuse.js
- ✅ Crear endpoint `/products/search`
- ✅ Crear componente SearchBar
- ✅ Integrar en ProductsPage
- ✅ Agregar keyboard navigation
- ✅ Testing de casos edge

### SPRINT 3: PAGINACIÓN (Día 4) - ⏳ PRIORIDAD BAJA
**Duración:** 2-3 horas

**Día 4 (2.5h):**
- ✅ Actualizar responses del API (agregar total)
- ✅ Crear componente Pagination
- ✅ Integrar en OrdersPage
- ✅ Integrar en ProductsPage
- ✅ Testing de navegación

---

## 📝 RESUMEN EJECUTIVO

### 🎯 Objetivos
Transformar el dashboard de Grana de una lista simple a una herramienta de análisis potente que ayude a Macarena a:
1. **Visualizar tendencias** de ventas con gráficos
2. **Encontrar productos** rápidamente con búsqueda inteligente
3. **Navegar datos** eficientemente con paginación

### 💰 Valor de Negocio
- **Ahorro de tiempo:** 15-20 min/día en análisis manual
- **Mejor toma de decisiones:** Identificar productos/meses rentables
- **Escalabilidad:** Preparado para 10x crecimiento

### ⚡ Quick Wins (orden recomendado)
1. **GRÁFICOS** → Mayor impacto visual, datos ya disponibles
2. **BÚSQUEDA** → Mejora UX inmediata, fácil de usar
3. **PAGINACIÓN** → Preparación futura, menor urgencia

### 📊 Métricas de Éxito
| Métrica                    | Antes    | Después   | Mejora   |
|----------------------------|----------|-----------|----------|
| Tiempo análisis tendencias | 5 min    | 30 seg    | 90%      |
| Tiempo encontrar producto  | 30 seg   | 3 seg     | 90%      |
| Tiempo carga página        | 2 seg    | 0.5 seg   | 75%      |
| Satisfacción usuario       | ?        | ⭐⭐⭐⭐⭐     | +100%    |

### 🛠️ Stack Técnico
```
Frontend:  Next.js + TypeScript + Tailwind
Charts:    Recharts (line, pie, bar charts)
Search:    Fuse.js (fuzzy search)
Backend:   FastAPI + Python
Database:  Supabase (PostgreSQL)
```

### 👥 Stakeholder
**Macarena Vicuña** - Owner de Grana
Necesita dashboard para:
- Ver cuánto vende por mes
- Identificar productos estrella
- Comparar Shopify vs MercadoLibre
- Tomar decisiones de inventario

---

## 🚀 PRÓXIMOS PASOS INMEDIATOS

1. **Confirmar prioridades** con usuario
2. **Empezar con GRÁFICOS** (mayor impacto)
3. **Iterar rápido** con feedback visual
4. **Deploy incremental** (feature by feature)

---

## 📎 ANEXOS

### A. Ejemplo de Data del Analytics Endpoint

```json
{
  "status": "success",
  "data": {
    "sales_by_period": [
      {
        "period": "2025-01",
        "shopify_revenue": 800430,
        "mercadolibre_revenue": 206000,
        "total_revenue": 1006430,
        "shopify_orders": 27,
        "mercadolibre_orders": 5,
        "total_orders": 32
      },
      {
        "period": "2025-08",
        "shopify_revenue": 9773038,
        "mercadolibre_revenue": 1000000,
        "total_revenue": 10773038,
        "shopify_orders": 387,
        "mercadolibre_orders": 30,
        "total_orders": 417
      }
    ],
    "source_distribution": [
      {
        "source": "shopify",
        "order_count": 1241,
        "revenue": 40976808,
        "avg_ticket": 33013
      },
      {
        "source": "mercadolibre",
        "order_count": 261,
        "revenue": 2964340,
        "avg_ticket": 11357
      }
    ],
    "top_products": [
      {
        "name": "Barra Cereal Grana Chocolate Dark",
        "sku": "SHOPIFY-12345",
        "order_count": 245,
        "units_sold": 1823,
        "revenue": 4200000
      }
    ],
    "kpis": {
      "total_orders": 1505,
      "total_revenue": 44391148,
      "avg_ticket": 29496
    },
    "growth_rates": [
      {"period": "2025-02", "growth_rate": -17.3},
      {"period": "2025-03", "growth_rate": 89.5}
    ]
  }
}
```

### B. Colores del Brand

```css
/* Grana Color Palette */
:root {
  --color-primary: #10B981;      /* Green (main brand) */
  --color-shopify: #50E3C2;      /* Teal */
  --color-ml: #F5A623;           /* Orange */
  --color-manual: #7B68EE;       /* Purple */
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
}
```

### C. Librerías y Versiones

```json
{
  "dependencies": {
    "recharts": "^2.12.0",
    "fuse.js": "^7.0.0"
  }
}
```

---

**FIN DEL PLAN ULTRA-DETALLADO** 🎉

¿Procedemos con la implementación? Recomiendo empezar con los **GRÁFICOS** para dar el mayor impacto visual inmediato.
