'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Product {
  id: number
  sku: string
  name: string
  category: string
  brand: string
  source: string
  sale_price: number
  current_stock: number
  min_stock: number
  is_active: boolean
  units_per_display: number
  displays_per_box: number
  boxes_per_pallet: number
}

interface ProductsResponse {
  status: string
  total: number
  count: number
  data: Product[]
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState<string>('')

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL
        const response = await fetch(`${apiUrl}/api/v1/products/?limit=100`)

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

        const data: ProductsResponse = await response.json()
        setProducts(data.data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchProducts()
  }, [])

  if (loading) {
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

  // Filter products
  const filteredProducts = products.filter(product => {
    const matchesSearch = product.name.toLowerCase().includes(filter.toLowerCase()) ||
                         product.sku.toLowerCase().includes(filter.toLowerCase())
    const matchesSource = !sourceFilter || product.source === sourceFilter
    return matchesSearch && matchesSource
  })

  // Get unique sources
  const sources = [...new Set(products.map(p => p.source))]

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
                {filteredProducts.length} de {products.length} productos
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
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="Buscar por nombre o SKU..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">Todas las fuentes</option>
              {sources.map(source => (
                <option key={source || 'null'} value={source || ''}>
                  {source === 'shopify' ? '🛍️ Shopify' : source || 'Manual'}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProducts.map((product) => (
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
                    {product.source === 'shopify' ? '🛍️ Shopify' : product.source || 'Manual'}
                  </span>
                </div>
              </div>

              {/* Price and Stock */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-lg font-bold text-green-600">
                    ${product.sale_price.toLocaleString('es-CL')}
                  </span>
                  <div className="text-right">
                    <div className={`text-sm font-medium ${
                      product.current_stock <= 0 ? 'text-red-600' :
                      product.current_stock <= product.min_stock ? 'text-orange-600' :
                      'text-green-600'
                    }`}>
                      Stock: {product.current_stock}
                    </div>
                    <div className="text-xs text-gray-500">
                      Min: {product.min_stock}
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
          ))}
        </div>

        {/* Empty State */}
        {filteredProducts.length === 0 && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No se encontraron productos</h3>
            <p className="mt-1 text-sm text-gray-500">
              Intenta con otros filtros de búsqueda
            </p>
          </div>
        )}

        {/* Stats Footer */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-gray-900">{products.length}</div>
              <div className="text-sm text-gray-600">Total Productos</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {products.filter(p => p.is_active).length}
              </div>
              <div className="text-sm text-gray-600">Activos</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">
                {products.filter(p => p.current_stock <= 0).length}
              </div>
              <div className="text-sm text-gray-600">Agotados</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600">
                {products.filter(p => p.current_stock > 0 && p.current_stock <= p.min_stock).length}
              </div>
              <div className="text-sm text-gray-600">Stock Bajo</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
