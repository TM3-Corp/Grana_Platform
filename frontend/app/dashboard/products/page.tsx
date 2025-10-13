'use client'

import { useEffect, useState, useMemo } from 'react'
import Link from 'next/link'
import Pagination from '@/components/Pagination'
import SmartSearchBar from '@/components/SmartSearchBar'
import HighlightedProductCard from '@/components/HighlightedProductCard'
import { useSmartSearch } from '@/hooks/useSmartSearch'
import { useSearchAnalytics } from '@/lib/searchAnalytics'
import type { SearchableProduct } from '@/lib/searchConfig'

interface Product {
  id: number
  sku: string
  name: string
  category: string | null
  brand: string | null
  source: string
  sale_price: number | null
  current_stock: number | null
  min_stock: number | null
  is_active: boolean
  units_per_display: number | null
  displays_per_box: number | null
  boxes_per_pallet: number | null
}

interface ProductsResponse {
  status: string
  total: number
  count: number
  data: Product[]
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [allProducts, setAllProducts] = useState<Product[]>([]) // For fuzzy search
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sourceFilter, setSourceFilter] = useState<string>('')

  // Pagination states (solo para modo navegación normal)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [totalItems, setTotalItems] = useState(0)

  // Preparar productos para búsqueda fuzzy
  const searchableProducts: SearchableProduct[] = useMemo(() => {
    return allProducts.map(p => ({
      id: p.id,
      sku: p.sku,
      name: p.name,
      category: p.category,
      brand: p.brand,
      source: p.source
    }))
  }, [allProducts])

  // Smart search hook
  const { search, searchQuery, setSearchQuery, suggestions, clearSearch } = useSmartSearch(searchableProducts)

  // Analytics hook
  const { trackSearch, trackResultClick } = useSearchAnalytics()

  // Resultados de búsqueda fuzzy
  const [searchResults, setSearchResults] = useState<ReturnType<typeof search>>([])
  const [isSearchActive, setIsSearchActive] = useState(false)

  // Cargar TODOS los productos una vez para fuzzy search
  useEffect(() => {
    const fetchAllProducts = async () => {
      try {
        // Get API URL with fallback to Railway production URL
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app'
        // Cargar todos los productos (sin paginación)
        const fullUrl = `${apiUrl}/api/v1/products/?limit=1000`
        console.log('🔍 [Products - All] Fetching from:', fullUrl)

        const response = await fetch(fullUrl)

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

        const data: ProductsResponse = await response.json()
        setAllProducts(data.data)
      } catch (err) {
        console.error('Error loading all products:', err)
      }
    }

    fetchAllProducts()
  }, [])

  // Búsqueda fuzzy en tiempo real
  useEffect(() => {
    if (searchQuery.trim()) {
      const results = search(searchQuery)
      setSearchResults(results)
      setIsSearchActive(true)

      // Track search analytics
      trackSearch(searchQuery, results.length)
    } else {
      setSearchResults([])
      setIsSearchActive(false)
    }
  }, [searchQuery, search, trackSearch])

  // Fetch paginado (solo cuando NO hay búsqueda activa)
  useEffect(() => {
    if (isSearchActive) {
      // En modo búsqueda, no fetch paginado
      return
    }

    const fetchProducts = async () => {
      setLoading(true)
      try {
        // Get API URL with fallback to Railway production URL
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app'

        // Build query params for server-side filtering and pagination
        const params = new URLSearchParams({
          limit: pageSize.toString(),
          offset: ((currentPage - 1) * pageSize).toString()
        })

        if (sourceFilter) {
          params.append('source', sourceFilter)
        }

        const fullUrl = `${apiUrl}/api/v1/products/?${params}`
        console.log('🔍 [Products - Paginated] Fetching from:', fullUrl)

        const response = await fetch(fullUrl)

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

        const data: ProductsResponse = await response.json()
        setProducts(data.data)
        setTotalItems(data.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchProducts()
  }, [currentPage, pageSize, sourceFilter, isSearchActive])

  if (loading && !isSearchActive) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando productos...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 font-semibold text-lg mb-2">Error</h2>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    )
  }

  // Available sources (hardcoded since we know them)
  const sources = ['shopify', 'mercadolibre', 'manual']

  // Reset to page 1 when source filter changes
  const handleSourceFilterChange = (value: string) => {
    setCurrentPage(1)
    setSourceFilter(value)
  }

  // Obtener productos a mostrar según el modo
  const displayedProducts = isSearchActive
    ? searchResults
        .map(r => allProducts.find(p => p.id === r.product.id))
        .filter((p): p is Product => p !== undefined)
    : products

  // Calcular estadísticas según el modo
  const statsProducts = isSearchActive ? displayedProducts : products

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                📦 Catálogo de Productos
              </h1>
              <p className="mt-2 text-gray-600">
                {isSearchActive ? (
                  <>
                    {searchResults.length} resultado{searchResults.length !== 1 ? 's' : ''} para "{searchQuery}"
                  </>
                ) : (
                  <>
                    Mostrando {products.length} de {totalItems} productos
                  </>
                )}
              </p>
            </div>
            <Link
              href="/dashboard"
              className="text-gray-600 hover:text-gray-900"
            >
              ← Volver al Dashboard
            </Link>
          </div>

          {/* Filters */}
          <div className="flex gap-4 flex-wrap">
            {/* Smart Search Bar */}
            <div className="flex-1 min-w-[300px]">
              <SmartSearchBar
                value={searchQuery}
                onChange={setSearchQuery}
                suggestions={suggestions}
                placeholder="Busca por nombre, SKU, categoría... (ej: barra keto nuez)"
                isSearching={false}
              />
            </div>

            {/* Source Filter - Solo visible en modo normal */}
            {!isSearchActive && (
              <select
                value={sourceFilter}
                onChange={(e) => handleSourceFilterChange(e.target.value)}
                className="px-4 py-2 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                <option value="">Todas las fuentes</option>
                {sources.map(source => (
                  <option key={source} value={source}>
                    {source === 'shopify' ? '🛍️ Shopify' :
                     source === 'mercadolibre' ? '🛒 MercadoLibre' :
                     source === 'manual' ? '✏️ Manual' : source}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Search mode indicator */}
          {isSearchActive && (
            <div className="mt-4 flex items-center gap-2 text-sm">
              <div className="px-3 py-1.5 bg-green-100 text-green-800 rounded-full font-medium flex items-center gap-2">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                </svg>
                Búsqueda inteligente activa
              </div>
              <button
                onClick={clearSearch}
                className="text-gray-600 hover:text-gray-900 underline"
              >
                Limpiar búsqueda
              </button>
            </div>
          )}
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isSearchActive ? (
            // Modo búsqueda: Mostrar resultados con highlights
            searchResults.map((result) => (
              <HighlightedProductCard
                key={result.product.id}
                result={result}
                onClick={() => {
                  // Track click analytics
                  trackResultClick(
                    searchQuery,
                    result.product.id.toString(),
                    result.product.source
                  )
                  // TODO: Ver detalle del producto en el futuro
                }}
              />
            ))
          ) : (
            // Modo normal: Mostrar productos con paginación
            products.map((product) => (
              <div
                key={product.id}
                className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6"
              >
                {/* Product Header */}
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-gray-500">{product.sku}</span>
                      {!product.is_active && (
                        <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                          Inactivo
                        </span>
                      )}
                    </div>
                    <h3 className="font-semibold text-gray-900 line-clamp-2">
                      {product.name}
                    </h3>
                  </div>
                </div>

                {/* Product Details */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Categoría:</span>
                    <span className="font-medium text-gray-900">{product.category || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Marca:</span>
                    <span className="font-medium text-gray-900">{product.brand || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Fuente:</span>
                    <span className="font-medium text-gray-900 capitalize">
                      {product.source === 'shopify' ? '🛍️ Shopify' :
                       product.source === 'mercadolibre' ? '🛒 ML' :
                       product.source === 'manual' ? '✏️ Manual' : product.source}
                    </span>
                  </div>
                </div>

                {/* Price and Stock */}
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-lg font-bold text-green-600">
                      {product.sale_price !== null
                        ? `$${product.sale_price.toLocaleString('es-CL')}`
                        : 'Precio no disponible'}
                    </span>
                    <div className="text-right">
                      <div className={`text-sm font-medium ${
                        (product.current_stock ?? 0) <= 0 ? 'text-red-600' :
                        (product.current_stock ?? 0) <= (product.min_stock ?? 0) ? 'text-orange-600' :
                        'text-green-600'
                      }`}>
                        Stock: {product.current_stock ?? 'N/A'}
                      </div>
                      <div className="text-xs text-gray-500">
                        Min: {product.min_stock ?? 'N/A'}
                      </div>
                    </div>
                  </div>

                  {/* Conversions */}
                  {product.units_per_display && product.displays_per_box && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <div className="text-xs text-gray-600 space-y-1">
                        <div className="flex justify-between">
                          <span>Unidades/Display:</span>
                          <span className="font-medium">{product.units_per_display}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Displays/Caja:</span>
                          <span className="font-medium">{product.displays_per_box}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Unidades/Caja:</span>
                          <span className="font-medium text-green-600">
                            {product.units_per_display * product.displays_per_box}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination - Solo en modo normal */}
        {!isSearchActive && products.length > 0 && (
          <Pagination
            currentPage={currentPage}
            totalItems={totalItems}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={setPageSize}
          />
        )}

        {/* Empty State */}
        {displayedProducts.length === 0 && !loading && (
          <div className="bg-white rounded-lg shadow p-12 text-center mt-6">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              {isSearchActive ? `No se encontraron productos para "${searchQuery}"` : 'No hay productos'}
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              {isSearchActive ? 'Intenta con otros términos de búsqueda' : 'Intenta con otros filtros'}
            </p>
            {isSearchActive && (
              <div className="mt-4 flex gap-2 justify-center flex-wrap">
                {['keto', 'low carb', 'crackers', 'granola', 'barra'].map(term => (
                  <button
                    key={term}
                    onClick={() => setSearchQuery(term)}
                    className="px-4 py-2 bg-green-100 text-green-800 rounded-full hover:bg-green-200 transition-colors text-sm font-medium"
                  >
                    {term}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Stats Footer */}
        {statsProducts.length > 0 && (
          <div className="mt-8 bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              {isSearchActive ? 'Estadísticas de resultados' : 'Estadísticas de esta página'}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-gray-900">{statsProducts.length}</div>
                <div className="text-sm text-gray-600">Productos</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {statsProducts.filter(p => p.is_active).length}
                </div>
                <div className="text-sm text-gray-600">Activos</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-red-600">
                  {statsProducts.filter(p => (p.current_stock ?? 0) <= 0).length}
                </div>
                <div className="text-sm text-gray-600">Agotados</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-orange-600">
                  {statsProducts.filter(p => (p.current_stock ?? 0) > 0 && (p.current_stock ?? 0) <= (p.min_stock ?? 0)).length}
                </div>
                <div className="text-sm text-gray-600">Stock Bajo</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
