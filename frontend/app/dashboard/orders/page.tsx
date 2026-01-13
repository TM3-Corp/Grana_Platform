'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Navigation from '@/components/Navigation'
import Pagination from '@/components/Pagination'
import AuditView from '@/components/AuditView'
import { StatCardsGridSkeleton, TableSkeleton, Skeleton } from '@/components/ui/Skeleton'
import { cn } from '@/lib/utils'

interface OrderItem {
  id: number
  product_sku: string
  product_name: string
  quantity: number
  unit_price: number
  total: number
  subtotal: number
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
  subtotal: number
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

type ViewMode = 'orders' | 'audit';

export default function OrdersPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('orders');
  const [orders, setOrders] = useState<Order[]>([])
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [monthFilter, setMonthFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [totalItems, setTotalItems] = useState(0)

  useEffect(() => {
    if (viewMode === 'orders') {
      const fetchOrders = async () => {
        setLoading(true)
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app'

          const params = new URLSearchParams({
            limit: pageSize.toString(),
            offset: ((currentPage - 1) * pageSize).toString()
          })

          if (sourceFilter) {
            params.append('source', sourceFilter)
          }

          if (searchQuery.trim()) {
            params.append('search', searchQuery.trim())
          }

          if (monthFilter) {
            const year = monthFilter.split('-')[0]
            const month = monthFilter.split('-')[1]
            const fromDate = `${year}-${month}-01`
            const lastDay = new Date(parseInt(year), parseInt(month), 0).getDate()
            const toDate = `${year}-${month}-${lastDay}`

            params.append('from_date', fromDate)
            params.append('to_date', toDate)
          } else {
            // Default to current year
            const currentYear = new Date().getFullYear()
            params.append('from_date', `${currentYear}-01-01`)
            params.append('to_date', `${currentYear}-12-31`)
          }

          const fullUrl = `${apiUrl}/api/v1/orders/?${params}`
          console.log('🔍 [Orders] Fetching from:', fullUrl)

          const response = await fetch(fullUrl)

          if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

          const data: OrdersResponse = await response.json()
          setOrders(data.data)
          setFilteredOrders(data.data)
          setTotalItems(data.total)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Error desconocido')
        } finally {
          setLoading(false)
        }
      }

      fetchOrders()
    }
  }, [currentPage, pageSize, sourceFilter, monthFilter, searchQuery, viewMode])

  // We now handle loading inline instead of returning early
  // This keeps the page structure visible during loading

  if (error && viewMode === 'orders') {
    return (
      <>
        <Navigation />
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
            <h2 className="text-red-800 font-semibold text-lg mb-2">Error</h2>
            <p className="text-red-600">{error}</p>
          </div>
        </div>
      </>
    )
  }

  const sources = ['shopify', 'mercadolibre', 'relbase', 'lokal', 'manual']
  // Generate months dynamically for current year
  const currentYear = new Date().getFullYear()
  const months = Array.from({ length: 12 }, (_, i) =>
    `${currentYear}-${String(i + 1).padStart(2, '0')}`
  )

  const handleFilterChange = (filterType: 'source' | 'month', value: string) => {
    setCurrentPage(1)
    if (filterType === 'source') {
      setSourceFilter(value)
    } else {
      setMonthFilter(value)
    }
  }

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Pedidos
            </h1>
            <p className="text-lg text-gray-600">
              {viewMode === 'orders'
                ? `Gestión completa de órdenes - ${totalItems} pedidos en total`
                : 'Desglose detallado de pedidos con análisis de productos, clientes y canales'
              }
            </p>
          </div>

          {/* View Tabs */}
          <div className="flex gap-2 mb-8 border-b">
            <button
              onClick={() => setViewMode('orders')}
              className={`px-6 py-3 font-medium transition-colors ${
                viewMode === 'orders'
                  ? 'text-green-600 border-b-2 border-green-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              📦 Pedidos
            </button>
            <button
              onClick={() => setViewMode('audit')}
              className={`px-6 py-3 font-medium transition-colors ${
                viewMode === 'audit'
                  ? 'text-green-600 border-b-2 border-green-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              📊 Desglose Pedidos
            </button>
          </div>

          {/* Content */}
          {viewMode === 'orders' ? (
            <>
              {/* Filters and Search */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Search Bar */}
                  <div className="md:col-span-1">
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                      </div>
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Buscar por N° orden, cliente, email..."
                        className="block w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                      />
                      {searchQuery && (
                        <button
                          onClick={() => setSearchQuery('')}
                          className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600"
                        >
                          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Source Filter */}
                  <select
                    value={sourceFilter}
                    onChange={(e) => handleFilterChange('source', e.target.value)}
                    className="px-6 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white"
                  >
                    <option value="">Todas las fuentes</option>
                    {sources.map(source => (
                      <option key={source} value={source}>
                        {source === 'shopify' ? '🛒 Shopify' :
                         source === 'mercadolibre' ? '🏪 MercadoLibre' :
                         source === 'relbase' ? '🧾 Relbase' :
                         source === 'lokal' ? '🏬 LOKAL' :
                         source === 'manual' ? '✏️ Manual' : source}
                      </option>
                    ))}
                  </select>

                  {/* Month Filter */}
                  <select
                    value={monthFilter}
                    onChange={(e) => handleFilterChange('month', e.target.value)}
                    className="px-6 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white"
                  >
                    <option value="">Todos los meses ({currentYear})</option>
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

                {/* Search Results Count */}
                {searchQuery && (
                  <div className="mt-4 text-sm text-gray-600">
                    {filteredOrders.length} resultado{filteredOrders.length !== 1 ? 's' : ''} encontrado{filteredOrders.length !== 1 ? 's' : ''}
                  </div>
                )}
              </div>

              {/* Orders Table */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                {loading ? (
                  <div className="p-6">
                    <div className="flex items-center justify-center gap-3 py-8 mb-4">
                      <div className="relative">
                        <div className="w-10 h-10 border-4 border-gray-200 rounded-full"></div>
                        <div className="w-10 h-10 border-4 border-green-500 rounded-full animate-spin border-t-transparent absolute top-0 left-0"></div>
                      </div>
                      <div className="text-gray-600">
                        <p className="font-medium">Cargando pedidos...</p>
                        <p className="text-xs text-gray-400">Esto puede tomar unos segundos</p>
                      </div>
                    </div>
                    <TableSkeleton rows={8} columns={6} />
                  </div>
                ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        Pedido
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        Cliente
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        Total
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        Estado
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        Fecha
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                        Acciones
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredOrders.map((order) => (
                      <tr key={order.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{order.order_number}</div>
                          <div className="text-xs text-gray-500">{order.channel_name}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900">{order.customer_name || 'Sin cliente'}</div>
                          <div className="text-xs text-gray-500">{order.customer_email}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-bold text-green-600">
                            ${order.total.toLocaleString('es-CL')}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="space-y-1">
                            <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full ${
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
                            className="text-green-600 hover:text-green-900 font-medium"
                          >
                            Ver detalles
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                )}
              </div>

              {/* Pagination */}
              {!searchQuery && (
                <div className="mt-6">
                  <Pagination
                    currentPage={currentPage}
                    totalItems={totalItems}
                    pageSize={pageSize}
                    onPageChange={setCurrentPage}
                    onPageSizeChange={setPageSize}
                  />
                </div>
              )}

              {/* Empty State */}
              {filteredOrders.length === 0 && !loading && (
                <div className="bg-white rounded-xl shadow-sm p-12 text-center mt-6">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No se encontraron pedidos</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {searchQuery ? 'Intenta con otros términos de búsqueda' : 'Intenta con otros filtros'}
                  </p>
                </div>
              )}

              {/* Stats Summary - Current page stats */}
              <div className="mt-8 bg-gradient-to-r from-green-50 to-blue-50 rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Estadísticas de esta página
                </h3>
                {loading ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                    {[1, 2, 3, 4].map(i => (
                      <div key={i} className="bg-white rounded-lg p-4 animate-pulse">
                        <Skeleton className="h-8 w-16 mx-auto mb-2" />
                        <Skeleton className="h-4 w-20 mx-auto" />
                      </div>
                    ))}
                  </div>
                ) : filteredOrders.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                    <div className="bg-white rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="text-2xl font-bold text-gray-900">{filteredOrders.length}</div>
                      <div className="text-sm text-gray-600">Pedidos</div>
                    </div>
                    <div className="bg-white rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="text-2xl font-bold text-green-600">
                        ${filteredOrders.reduce((sum, o) => sum + o.total, 0).toLocaleString('es-CL')}
                      </div>
                      <div className="text-sm text-gray-600">Ingresos</div>
                    </div>
                    <div className="bg-white rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="text-2xl font-bold text-blue-600">
                        {filteredOrders.filter(o => o.status === 'completed').length}
                      </div>
                      <div className="text-sm text-gray-600">Completados</div>
                    </div>
                    <div className="bg-white rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="text-2xl font-bold text-yellow-600">
                        {filteredOrders.filter(o => o.status === 'pending').length}
                      </div>
                      <div className="text-sm text-gray-600">Pendientes</div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-4">
                    No hay datos para mostrar estadísticas
                  </div>
                )}
              </div>
            </>
          ) : (
            <AuditView />
          )}
        </div>

        {/* Order Details Modal */}
        {selectedOrder && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center rounded-t-2xl">
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
                  <div className="bg-gray-50 rounded-xl p-4 space-y-1">
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
                  <div className="bg-gray-50 rounded-xl p-4 space-y-2">
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
                  <div className="border border-gray-200 rounded-xl overflow-hidden">
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
                            <td className="px-4 py-2 text-sm text-right">${(item.subtotal / item.quantity).toLocaleString('es-CL', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                            <td className="px-4 py-2 text-sm text-right font-medium">${item.subtotal.toLocaleString('es-CL')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Total */}
                <div className="border-t border-gray-200 pt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-semibold text-gray-900">Total (neto):</span>
                    <span className="text-2xl font-bold text-green-600">
                      ${selectedOrder.subtotal.toLocaleString('es-CL')}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
