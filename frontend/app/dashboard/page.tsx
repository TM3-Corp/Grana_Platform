'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface ProductStats {
  totals: {
    all: number
    active: number
    with_conversions: number
  }
  by_source: Array<{ source: string; count: number }>
  stock_levels: {
    out_of_stock: number
    low_stock: number
    in_stock: number
  }
}

interface OrderStats {
  totals: {
    total_orders: number
    total_revenue: number
    average_order_value: number
    recent_orders_7d: number
  }
  by_source: Array<{ source: string; count: number; revenue: number }>
  by_status: Array<{ status: string; count: number }>
}

export default function DashboardPage() {
  const [productStats, setProductStats] = useState<ProductStats | null>(null)
  const [orderStats, setOrderStats] = useState<OrderStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL

        // Fetch product stats
        const productsRes = await fetch(`${apiUrl}/api/v1/products/stats`)
        if (!productsRes.ok) throw new Error(`Products API error: ${productsRes.status}`)
        const productsData = await productsRes.json()
        setProductStats(productsData.data)

        // Fetch order stats
        const ordersRes = await fetch(`${apiUrl}/api/v1/orders/stats`)
        if (!ordersRes.ok) throw new Error(`Orders API error: ${ordersRes.status}`)
        const ordersData = await ordersRes.json()
        setOrderStats(ordersData.data)

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
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

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 font-semibold text-lg mb-2">Error</h2>
          <p className="text-red-600">{error}</p>
          <p className="text-sm text-red-500 mt-2">
            API URL: {process.env.NEXT_PUBLIC_API_URL}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                🍃 Dashboard - Grana Platform
              </h1>
              <p className="mt-2 text-gray-600">
                Resumen de ventas y productos
              </p>
            </div>
            <Link
              href="/"
              className="text-gray-600 hover:text-gray-900"
            >
              ← Volver
            </Link>
          </div>
        </div>

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Orders */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Pedidos</p>
                <p className="text-3xl font-bold text-gray-900">
                  {orderStats?.totals.total_orders || 0}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {orderStats?.totals.recent_orders_7d || 0} últimos 7 días
                </p>
              </div>
              <div className="bg-blue-100 rounded-full p-3">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Total Revenue */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Ingresos Totales</p>
                <p className="text-3xl font-bold text-green-600">
                  ${(orderStats?.totals.total_revenue || 0).toLocaleString('es-CL')}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Promedio: ${(orderStats?.totals.average_order_value || 0).toLocaleString('es-CL')}
                </p>
              </div>
              <div className="bg-green-100 rounded-full p-3">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Total Products */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Productos Activos</p>
                <p className="text-3xl font-bold text-gray-900">
                  {productStats?.totals.active || 0}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {productStats?.totals.all || 0} total
                </p>
              </div>
              <div className="bg-purple-100 rounded-full p-3">
                <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </div>
            </div>
          </div>

          {/* Stock Alerts */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Stock Bajo</p>
                <p className="text-3xl font-bold text-orange-600">
                  {(productStats?.stock_levels.low_stock || 0) + (productStats?.stock_levels.out_of_stock || 0)}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {productStats?.stock_levels.out_of_stock || 0} agotados
                </p>
              </div>
              <div className="bg-orange-100 rounded-full p-3">
                <svg className="w-8 h-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Orders by Source */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              📊 Pedidos por Fuente
            </h2>
            <div className="space-y-3">
              {orderStats?.by_source.map((source) => (
                <div key={source.source} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-24 text-sm font-medium text-gray-700 capitalize">
                      {source.source === 'shopify' ? '🛍️ Shopify' : source.source}
                    </div>
                    <div className="flex-1 bg-gray-200 rounded-full h-2 min-w-[200px]">
                      <div
                        className="bg-green-600 h-2 rounded-full"
                        style={{
                          width: `${(source.count / (orderStats?.totals.total_orders || 1)) * 100}%`
                        }}
                      ></div>
                    </div>
                  </div>
                  <div className="text-sm text-gray-600 ml-4">
                    {source.count} pedidos (${source.revenue.toLocaleString('es-CL')})
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Products by Source */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              📦 Productos por Fuente
            </h2>
            <div className="space-y-3">
              {productStats?.by_source.map((source) => (
                <div key={source.source || 'manual'} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-24 text-sm font-medium text-gray-700 capitalize">
                      {source.source === 'shopify' ? '🛍️ Shopify' : source.source || 'Manual'}
                    </div>
                    <div className="flex-1 bg-gray-200 rounded-full h-2 min-w-[200px]">
                      <div
                        className="bg-purple-600 h-2 rounded-full"
                        style={{
                          width: `${(source.count / (productStats?.totals.all || 1)) * 100}%`
                        }}
                      ></div>
                    </div>
                  </div>
                  <div className="text-sm text-gray-600 ml-4">
                    {source.count} productos
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            href="/dashboard/orders"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Ver Pedidos</h3>
                <p className="text-sm text-gray-600 mt-1">Lista completa de pedidos</p>
              </div>
              <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </Link>

          <Link
            href="/dashboard/products"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Ver Productos</h3>
                <p className="text-sm text-gray-600 mt-1">Catálogo de productos</p>
              </div>
              <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </Link>

          <a
            href={`${process.env.NEXT_PUBLIC_API_URL}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">API Docs</h3>
                <p className="text-sm text-gray-600 mt-1">Documentación de API</p>
              </div>
              <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </div>
          </a>
        </div>

        {/* API Info */}
        <div className="mt-8 bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-800">
            <span className="font-semibold">✅ Conectado a:</span> {process.env.NEXT_PUBLIC_API_URL}
          </p>
        </div>
      </div>
    </div>
  )
}
