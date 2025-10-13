'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Pagination from '@/components/Pagination'

interface OrderItem {
  id: number
  product_sku: string
  product_name: string
  quantity: number
  unit_price: number
  total: number
}

interface Order {
  id: number
  order_number: string
  source: string
  customer_name: string
  customer_email: string
  customer_city: string
  channel_name: string
  total: number
  status: string
  payment_status: string
  fulfillment_status: string
  order_date: string
  items: OrderItem[]
}

interface OrdersResponse {
  status: string
  total: number
  count: number
  data: Order[]
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [monthFilter, setMonthFilter] = useState<string>('')

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(50) // Default: 50 items per page
  const [totalItems, setTotalItems] = useState(0)

  useEffect(() => {
    const fetchOrders = async () => {
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

        if (monthFilter) {
          // Convert month filter (YYYY-MM) to date range
          const year = monthFilter.split('-')[0]
          const month = monthFilter.split('-')[1]
          const fromDate = `${year}-${month}-01`

          // Calculate last day of month
          const lastDay = new Date(parseInt(year), parseInt(month), 0).getDate()
          const toDate = `${year}-${month}-${lastDay}`

          params.append('from_date', fromDate)
          params.append('to_date', toDate)
        } else {
          // Default: only show 2025 data
          params.append('from_date', '2025-01-01')
          params.append('to_date', '2025-12-31')
        }

        const fullUrl = `${apiUrl}/api/v1/orders/?${params}`
        console.log('🔍 [Orders] Fetching from:', fullUrl)

        const response = await fetch(fullUrl)

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

        const data: OrdersResponse = await response.json()
        setOrders(data.data)
        setTotalItems(data.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchOrders()
  }, [currentPage, pageSize, sourceFilter, monthFilter])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando pedidos...</p>
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

  // Generate months for 2025
  const months = [
    '2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06',
    '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12'
  ]

  // Reset to page 1 when filters change
  const handleFilterChange = (filterType: 'source' | 'month', value: string) => {
    setCurrentPage(1)
    if (filterType === 'source') {
      setSourceFilter(value)
    } else {
      setMonthFilter(value)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                🛒 Pedidos
              </h1>
              <p className="mt-2 text-gray-600">
                Mostrando {orders.length} de {totalItems} pedidos
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
            <select
              value={sourceFilter}
              onChange={(e) => handleFilterChange('source', e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
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

            <select
              value={monthFilter}
              onChange={(e) => handleFilterChange('month', e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">Todos los meses (2025)</option>
              {months.map(month => {
                const date = new Date(month + '-01')
                const monthName = date.toLocaleDateString('es-CL', { month: 'long', year: 'numeric' })
                return (
                  <option key={month} value={month}>
                    {monthName.charAt(0).toUpperCase() + monthName.slice(1)}
                  </option>
                )
              })}
            </select>
          </div>
        </div>

        {/* Orders Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Pedido
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cliente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fuente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fecha
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {orders.map((order) => (
                <tr key={order.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{order.order_number}</div>
                    <div className="text-xs text-gray-500">{order.channel_name}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{order.customer_name || 'Sin cliente'}</div>
                    <div className="text-xs text-gray-500">{order.customer_email}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 capitalize">
                      {order.source === 'shopify' ? '🛍️ Shopify' : order.source}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-bold text-green-600">
                      ${order.total.toLocaleString('es-CL')}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="space-y-1">
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                        order.status === 'completed' ? 'bg-green-100 text-green-800' :
                        order.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {order.status}
                      </span>
                      {order.payment_status && (
                        <div className="text-xs text-gray-600">
                          💳 {order.payment_status}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(order.order_date).toLocaleDateString('es-CL')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => setSelectedOrder(order)}
                      className="text-green-600 hover:text-green-900"
                    >
                      Ver detalles
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <Pagination
          currentPage={currentPage}
          totalItems={totalItems}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
        />

        {/* Empty State */}
        {orders.length === 0 && !loading && (
          <div className="bg-white rounded-lg shadow p-12 text-center mt-6">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No se encontraron pedidos</h3>
            <p className="mt-1 text-sm text-gray-500">
              Intenta con otros filtros
            </p>
          </div>
        )}

        {/* Stats Summary - Current page stats */}
        {orders.length > 0 && (
          <div className="mt-8 bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Estadísticas de esta página
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-gray-900">{orders.length}</div>
                <div className="text-sm text-gray-600">Pedidos en página</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  ${orders.reduce((sum, o) => sum + o.total, 0).toLocaleString('es-CL')}
                </div>
                <div className="text-sm text-gray-600">Ingresos en página</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {orders.filter(o => o.status === 'completed').length}
                </div>
                <div className="text-sm text-gray-600">Completados</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-yellow-600">
                  {orders.filter(o => o.status === 'pending').length}
                </div>
                <div className="text-sm text-gray-600">Pendientes</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Order Details Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
              <h2 className="text-xl font-semibold text-gray-900">
                Pedido {selectedOrder.order_number}
              </h2>
              <button
                onClick={() => setSelectedOrder(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Customer Info */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Cliente</h3>
                <div className="bg-gray-50 rounded-lg p-4 space-y-1">
                  <div className="text-sm"><span className="font-medium">Nombre:</span> {selectedOrder.customer_name}</div>
                  <div className="text-sm"><span className="font-medium">Email:</span> {selectedOrder.customer_email}</div>
                  {selectedOrder.customer_city && (
                    <div className="text-sm"><span className="font-medium">Ciudad:</span> {selectedOrder.customer_city}</div>
                  )}
                </div>
              </div>

              {/* Order Info */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Información del Pedido</h3>
                <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Fuente:</span>
                    <span className="capitalize">{selectedOrder.source === 'shopify' ? '🛍️ Shopify' : selectedOrder.source}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Canal:</span>
                    <span>{selectedOrder.channel_name}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Estado:</span>
                    <span className="capitalize">{selectedOrder.status}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Pago:</span>
                    <span className="capitalize">{selectedOrder.payment_status || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Fecha:</span>
                    <span>{new Date(selectedOrder.order_date).toLocaleString('es-CL')}</span>
                  </div>
                </div>
              </div>

              {/* Order Items */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Productos ({selectedOrder.items.length})</h3>
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Producto</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">SKU</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Cant.</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Precio</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {selectedOrder.items.map((item) => (
                        <tr key={item.id}>
                          <td className="px-4 py-2 text-sm">{item.product_name}</td>
                          <td className="px-4 py-2 text-sm text-gray-500">{item.product_sku}</td>
                          <td className="px-4 py-2 text-sm text-right">{item.quantity}</td>
                          <td className="px-4 py-2 text-sm text-right">${item.unit_price.toLocaleString('es-CL')}</td>
                          <td className="px-4 py-2 text-sm text-right font-medium">${item.total.toLocaleString('es-CL')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Total */}
              <div className="border-t border-gray-200 pt-4">
                <div className="flex justify-between items-center">
                  <span className="text-lg font-semibold text-gray-900">Total:</span>
                  <span className="text-2xl font-bold text-green-600">
                    ${selectedOrder.total.toLocaleString('es-CL')}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
