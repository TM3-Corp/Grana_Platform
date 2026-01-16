'use client'

import { useState, useEffect } from 'react'

interface MappingStep {
  step: number
  action: string
  matched: boolean
  details: Record<string, unknown>
}

interface MappingResult {
  mapped_sku: string | null
  match_type: string
  quantity: number
  multiplier: number
  conversion_factor: number
  total_units: number
  formula: string
}

interface MappingDebug {
  original_sku: string
  original_quantity: number
  source: string
  steps: MappingStep[]
  final_result: MappingResult
}

interface OrderItem {
  item_id: number
  sku: string
  product_name: string
  quantity: number
  unit_price: number
  subtotal: number
  mapping: MappingDebug
}

interface OrderDebug {
  order: {
    id: number
    external_id: string
    date: string
    customer: string
    channel: string
    total: number
    status: string
  }
  items: OrderItem[]
  summary: {
    total_items: number
    mapped_items: number
    unmapped_items: number
    total_quantity: number
    total_units: number
  }
}

interface UnmappedSku {
  sku: string
  product_name: string
  order_count: number
  total_quantity: number
  total_revenue: number
}

export default function DebugMappingPage() {
  const [activeTab, setActiveTab] = useState<'orders' | 'unmapped' | 'test'>('orders')
  const [orders, setOrders] = useState<OrderDebug[]>([])
  const [unmappedSkus, setUnmappedSkus] = useState<UnmappedSku[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedOrders, setExpandedOrders] = useState<Set<number>>(new Set())
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())

  // Filters
  const [days, setDays] = useState(7)
  const [limit, setLimit] = useState(10)
  const [showUnmappedOnly, setShowUnmappedOnly] = useState(false)

  // Test SKU
  const [testSku, setTestSku] = useState('')
  const [testQuantity, setTestQuantity] = useState(1)
  const [testResult, setTestResult] = useState<MappingDebug | null>(null)

  // Global summary
  const [globalSummary, setGlobalSummary] = useState({
    orders_count: 0,
    total_items: 0,
    mapped_items: 0,
    unmapped_items: 0,
    mapping_coverage: 0
  })

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const fetchOrders = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        days: days.toString(),
        limit: limit.toString(),
        source: 'relbase',
        show_unmapped_only: showUnmappedOnly.toString()
      })
      const response = await fetch(`${apiUrl}/api/v1/debug-mapping/debug/orders?${params}`)
      const data = await response.json()
      if (data.status === 'success') {
        setOrders(data.orders)
        setGlobalSummary(data.global_summary)
      }
    } catch (error) {
      console.error('Error fetching orders:', error)
    }
    setLoading(false)
  }

  const fetchUnmapped = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        days: '30',
        limit: '50',
        source: 'relbase'
      })
      const response = await fetch(`${apiUrl}/api/v1/debug-mapping/debug/unmapped-skus?${params}`)
      const data = await response.json()
      if (data.status === 'success') {
        setUnmappedSkus(data.unmapped_skus)
      }
    } catch (error) {
      console.error('Error fetching unmapped:', error)
    }
    setLoading(false)
  }

  const testSkuMapping = async () => {
    if (!testSku) return
    setLoading(true)
    try {
      const params = new URLSearchParams({
        quantity: testQuantity.toString(),
        source: 'relbase'
      })
      const response = await fetch(`${apiUrl}/api/v1/debug-mapping/debug/sku/${testSku}?${params}`)
      const data = await response.json()
      if (data.status === 'success') {
        setTestResult(data.debug)
      }
    } catch (error) {
      console.error('Error testing SKU:', error)
    }
    setLoading(false)
  }

  useEffect(() => {
    if (activeTab === 'orders') {
      fetchOrders()
    } else if (activeTab === 'unmapped') {
      fetchUnmapped()
    }
  }, [activeTab])

  const toggleOrder = (orderId: number) => {
    const newExpanded = new Set(expandedOrders)
    if (newExpanded.has(orderId)) {
      newExpanded.delete(orderId)
    } else {
      newExpanded.add(orderId)
    }
    setExpandedOrders(newExpanded)
  }

  const toggleItem = (itemKey: string) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(itemKey)) {
      newExpanded.delete(itemKey)
    } else {
      newExpanded.add(itemKey)
    }
    setExpandedItems(newExpanded)
  }

  const getMatchTypeColor = (matchType: string) => {
    if (matchType === 'unmapped' || matchType === 'no_match') return 'bg-red-100 text-red-800 border-red-300'
    if (matchType === 'direct') return 'bg-green-100 text-green-800 border-green-300'
    if (matchType === 'caja_master') return 'bg-purple-100 text-purple-800 border-purple-300'
    if (matchType.includes('sku_mapping')) return 'bg-blue-100 text-blue-800 border-blue-300'
    return 'bg-gray-100 text-gray-800 border-gray-300'
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP' }).format(value)
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Debug Mapeo de SKUs</h1>
        <p className="text-gray-600">Visualiza cómo se mapean los productos y calcula las unidades</p>
      </div>

      {/* Global Summary Cards */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="bg-white p-4 rounded-lg border shadow-sm">
          <div className="text-sm text-gray-500">Pedidos</div>
          <div className="text-2xl font-bold">{globalSummary.orders_count}</div>
        </div>
        <div className="bg-white p-4 rounded-lg border shadow-sm">
          <div className="text-sm text-gray-500">Items Totales</div>
          <div className="text-2xl font-bold">{globalSummary.total_items}</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg border border-green-200 shadow-sm">
          <div className="text-sm text-green-600">Mapeados</div>
          <div className="text-2xl font-bold text-green-700">{globalSummary.mapped_items}</div>
        </div>
        <div className="bg-red-50 p-4 rounded-lg border border-red-200 shadow-sm">
          <div className="text-sm text-red-600">Sin Mapear</div>
          <div className="text-2xl font-bold text-red-700">{globalSummary.unmapped_items}</div>
        </div>
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 shadow-sm">
          <div className="text-sm text-blue-600">Cobertura</div>
          <div className="text-2xl font-bold text-blue-700">{globalSummary.mapping_coverage}%</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b mb-6">
        <div className="flex space-x-4">
          <button
            onClick={() => setActiveTab('orders')}
            className={`py-2 px-4 border-b-2 font-medium ${
              activeTab === 'orders' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'
            }`}
          >
            Pedidos Recientes
          </button>
          <button
            onClick={() => setActiveTab('unmapped')}
            className={`py-2 px-4 border-b-2 font-medium ${
              activeTab === 'unmapped' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'
            }`}
          >
            SKUs Sin Mapear
          </button>
          <button
            onClick={() => setActiveTab('test')}
            className={`py-2 px-4 border-b-2 font-medium ${
              activeTab === 'test' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'
            }`}
          >
            Probar SKU
          </button>
        </div>
      </div>

      {/* Orders Tab */}
      {activeTab === 'orders' && (
        <div>
          {/* Filters */}
          <div className="bg-gray-50 p-4 rounded-lg mb-4 flex items-center gap-4">
            <div>
              <label className="text-sm text-gray-600">Días</label>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="ml-2 border rounded px-2 py-1"
              >
                <option value={3}>3 días</option>
                <option value={7}>7 días</option>
                <option value={14}>14 días</option>
                <option value={30}>30 días</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-600">Límite</label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="ml-2 border rounded px-2 py-1"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="unmappedOnly"
                checked={showUnmappedOnly}
                onChange={(e) => setShowUnmappedOnly(e.target.checked)}
                className="mr-2"
              />
              <label htmlFor="unmappedOnly" className="text-sm text-gray-600">
                Solo sin mapear
              </label>
            </div>
            <button
              onClick={fetchOrders}
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Cargando...' : 'Buscar'}
            </button>
          </div>

          {/* Orders List */}
          <div className="space-y-4">
            {orders.map((orderDebug) => (
              <div key={orderDebug.order.id} className="bg-white border rounded-lg shadow-sm">
                {/* Order Header */}
                <div
                  className="p-4 cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                  onClick={() => toggleOrder(orderDebug.order.id)}
                >
                  <div className="flex items-center gap-4">
                    <span className="text-lg font-mono font-bold text-gray-700">
                      #{orderDebug.order.external_id}
                    </span>
                    <span className="text-gray-500">{orderDebug.order.date?.split('T')[0]}</span>
                    <span className="bg-gray-100 px-2 py-1 rounded text-sm">
                      {orderDebug.order.customer}
                    </span>
                    <span className="text-gray-500">{orderDebug.order.channel}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-sm text-gray-500">
                        {orderDebug.summary.mapped_items}/{orderDebug.summary.total_items} mapeados
                      </div>
                      <div className="text-sm font-medium">
                        {orderDebug.summary.total_quantity} qty → {orderDebug.summary.total_units} uds
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      orderDebug.summary.unmapped_items > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                    }`}>
                      {orderDebug.summary.unmapped_items > 0 ? `${orderDebug.summary.unmapped_items} sin mapear` : 'OK'}
                    </span>
                    <span className="text-gray-400">{expandedOrders.has(orderDebug.order.id) ? '▼' : '▶'}</span>
                  </div>
                </div>

                {/* Order Items */}
                {expandedOrders.has(orderDebug.order.id) && (
                  <div className="border-t">
                    {orderDebug.items.map((item) => {
                      const itemKey = `${orderDebug.order.id}-${item.item_id}`
                      const isExpanded = expandedItems.has(itemKey)
                      const result = item.mapping.final_result

                      return (
                        <div key={item.item_id} className="border-b last:border-b-0">
                          {/* Item Row */}
                          <div
                            className="p-4 cursor-pointer hover:bg-gray-50 flex items-center gap-4"
                            onClick={() => toggleItem(itemKey)}
                          >
                            <span className={`px-2 py-1 rounded text-xs font-mono border ${getMatchTypeColor(result.match_type)}`}>
                              {result.match_type}
                            </span>
                            <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                              {item.sku}
                            </span>
                            {result.mapped_sku && result.mapped_sku !== item.sku && (
                              <>
                                <span className="text-gray-400">→</span>
                                <span className="font-mono text-sm bg-blue-100 px-2 py-1 rounded text-blue-800">
                                  {result.mapped_sku}
                                </span>
                              </>
                            )}
                            <span className="text-gray-600 truncate max-w-xs" title={item.product_name}>
                              {item.product_name}
                            </span>
                            <div className="ml-auto flex items-center gap-4">
                              <div className="text-right">
                                <div className="font-mono text-sm">
                                  <span className="text-gray-500">{item.quantity}</span>
                                  {result.multiplier > 1 && (
                                    <span className="text-blue-600"> ×{result.multiplier}</span>
                                  )}
                                  {result.conversion_factor > 1 && (
                                    <span className="text-purple-600"> ×{result.conversion_factor}</span>
                                  )}
                                  <span className="text-gray-400"> = </span>
                                  <span className="font-bold text-green-700">{result.total_units}</span>
                                  <span className="text-gray-500 text-xs ml-1">uds</span>
                                </div>
                              </div>
                              <span className="text-gray-500">{formatCurrency(item.subtotal)}</span>
                              <span className="text-gray-400">{isExpanded ? '▼' : '▶'}</span>
                            </div>
                          </div>

                          {/* Mapping Debug Details */}
                          {isExpanded && (
                            <div className="bg-gray-50 p-4 border-t">
                              <div className="text-sm font-medium text-gray-700 mb-3">
                                Proceso de Mapeo:
                              </div>
                              <div className="space-y-2">
                                {item.mapping.steps.map((step) => (
                                  <div
                                    key={step.step}
                                    className={`p-3 rounded border ${
                                      step.matched
                                        ? 'bg-green-50 border-green-200'
                                        : 'bg-gray-100 border-gray-200'
                                    }`}
                                  >
                                    <div className="flex items-center gap-2">
                                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                                        step.matched ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                                      }`}>
                                        {step.step}
                                      </span>
                                      <span className="font-mono text-sm font-medium">
                                        {step.action}
                                      </span>
                                      <span className={`px-2 py-0.5 rounded text-xs ${
                                        step.matched ? 'bg-green-200 text-green-800' : 'bg-gray-200 text-gray-600'
                                      }`}>
                                        {step.matched ? 'MATCH' : 'NO MATCH'}
                                      </span>
                                    </div>
                                    {step.matched && step.details && (
                                      <div className="mt-2 pl-8 text-xs text-gray-600 font-mono">
                                        {JSON.stringify(step.details, null, 2)}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                                <div className="font-medium text-blue-800 mb-1">Resultado Final:</div>
                                <div className="font-mono text-sm text-blue-900">
                                  {result.formula}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unmapped Tab */}
      {activeTab === 'unmapped' && (
        <div>
          <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg mb-4">
            <div className="font-medium text-yellow-800">SKUs sin mapear (últimos 30 días)</div>
            <div className="text-sm text-yellow-700">Ordenados por impacto en revenue</div>
          </div>

          <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Pedidos</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cantidad</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Revenue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {unmappedSkus.map((sku, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-sm bg-red-50 text-red-800">{sku.sku}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 truncate max-w-xs">{sku.product_name}</td>
                    <td className="px-4 py-3 text-sm text-right">{sku.order_count}</td>
                    <td className="px-4 py-3 text-sm text-right">{sku.total_quantity}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium">{formatCurrency(sku.total_revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Test SKU Tab */}
      {activeTab === 'test' && (
        <div>
          <div className="bg-white p-6 rounded-lg border shadow-sm mb-6">
            <div className="text-lg font-medium mb-4">Probar Mapeo de SKU</div>
            <div className="flex items-end gap-4">
              <div className="flex-1">
                <label className="block text-sm text-gray-600 mb-1">SKU</label>
                <input
                  type="text"
                  value={testSku}
                  onChange={(e) => setTestSku(e.target.value.toUpperCase())}
                  placeholder="Ej: BAKC_U04010, PACKGRCA_U26010"
                  className="w-full border rounded px-3 py-2 font-mono"
                />
              </div>
              <div className="w-32">
                <label className="block text-sm text-gray-600 mb-1">Cantidad</label>
                <input
                  type="number"
                  value={testQuantity}
                  onChange={(e) => setTestQuantity(Number(e.target.value))}
                  min={1}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <button
                onClick={testSkuMapping}
                disabled={loading || !testSku}
                className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Probar
              </button>
            </div>
          </div>

          {testResult && (
            <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
              {/* Result Header */}
              <div className={`p-4 ${
                testResult.final_result.match_type === 'unmapped'
                  ? 'bg-red-50 border-b border-red-200'
                  : 'bg-green-50 border-b border-green-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-lg">{testResult.original_sku}</span>
                    {testResult.final_result.mapped_sku && (
                      <>
                        <span className="text-gray-400 text-2xl">→</span>
                        <span className="font-mono text-lg text-blue-700">{testResult.final_result.mapped_sku}</span>
                      </>
                    )}
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getMatchTypeColor(testResult.final_result.match_type)}`}>
                    {testResult.final_result.match_type}
                  </span>
                </div>
              </div>

              {/* Conversion Display */}
              <div className="p-6 bg-blue-50 border-b">
                <div className="text-center">
                  <div className="text-4xl font-mono mb-2">
                    <span className="text-gray-600">{testResult.final_result.quantity}</span>
                    {testResult.final_result.multiplier > 1 && (
                      <span className="text-blue-600"> × {testResult.final_result.multiplier}</span>
                    )}
                    {testResult.final_result.conversion_factor > 1 && (
                      <span className="text-purple-600"> × {testResult.final_result.conversion_factor}</span>
                    )}
                    <span className="text-gray-400"> = </span>
                    <span className="text-green-600 font-bold">{testResult.final_result.total_units}</span>
                  </div>
                  <div className="text-sm text-gray-600">{testResult.final_result.formula}</div>
                </div>
              </div>

              {/* Steps */}
              <div className="p-4">
                <div className="text-sm font-medium text-gray-700 mb-3">Pasos del Mapeo:</div>
                <div className="space-y-3">
                  {testResult.steps.map((step) => (
                    <div
                      key={step.step}
                      className={`p-4 rounded-lg border ${
                        step.matched
                          ? 'bg-green-50 border-green-300'
                          : 'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                          step.matched ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                        }`}>
                          {step.step}
                        </div>
                        <div>
                          <div className="font-medium">{step.action}</div>
                          <div className="text-sm text-gray-500">
                            {step.matched ? 'Encontrado' : 'No encontrado'}
                          </div>
                        </div>
                      </div>
                      {step.matched && step.details && (
                        <pre className="mt-3 p-3 bg-white rounded border text-xs overflow-x-auto">
                          {JSON.stringify(step.details, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
