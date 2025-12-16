'use client'

import { useEffect, useState } from 'react'
import Navigation from '@/components/Navigation'
import ExecutiveSalesChart from '@/components/charts/ExecutiveSalesChart'
import QuarterlyAnalytics from '@/components/charts/QuarterlyAnalytics'

interface MonthData {
  month: number
  month_name: string
  year: number
  total_orders: number
  total_revenue: number
  is_actual?: boolean
  is_projection?: boolean
  confidence_lower?: number
  confidence_upper?: number
  growth_rate_applied?: number
}

interface ExecutiveData {
  sales_2024: MonthData[]
  sales_2025_actual: MonthData[]
  sales_2025_projected: MonthData[]
  kpis: {
    total_revenue_2024: number
    total_revenue_2025_actual: number
    total_orders_2024: number
    total_orders_2025_actual: number
    avg_ticket_2024: number
    avg_ticket_2025: number
    revenue_yoy_change: number
    orders_yoy_change: number
    ticket_yoy_change: number
  }
  projection_metadata: {
    avg_growth_rate: number
    std_dev: number
    months_projected: number
    current_month: number
    current_year: number
  }
}

const PRODUCT_FAMILIES = [
  { name: 'Todas', icon: '🎯', value: 'TODAS' },
  { name: 'Barras', icon: '🍫', value: 'BARRAS' },
  { name: 'Crackers', icon: '🍘', value: 'CRACKERS' },
  { name: 'Granolas', icon: '🥣', value: 'GRANOLAS' },
  { name: 'Keepers', icon: '🍪', value: 'KEEPERS' },
]

export default function DashboardPage() {
  const [data, setData] = useState<ExecutiveData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFamily, setSelectedFamily] = useState('TODAS')

  const fetchExecutiveData = async (family: string) => {
    try {
      setLoading(true)
      setError(null)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const params = family !== 'TODAS' ? `?product_family=${family}` : ''
      const fullUrl = `${apiUrl}/api/v1/orders/dashboard/executive-kpis${params}`

      const response = await fetch(fullUrl)

      if (!response.ok) {
        throw new Error(`Error fetching executive data (${response.status})`)
      }

      const result = await response.json()
      setData(result.data)
    } catch (err) {
      console.error('Error:', err)
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchExecutiveData(selectedFamily)
  }, [selectedFamily])

  if (loading) {
    return (
      <>
        <Navigation />
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Cargando dashboard...</p>
          </div>
        </div>
      </>
    )
  }

  if (error || !data) {
    return (
      <>
        <Navigation />
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-red-800 font-semibold text-lg mb-2">Error</h2>
            <p className="text-red-600">{error || 'No se pudieron cargar los datos'}</p>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
                  <span className="text-4xl">📊</span>
                  <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                    Dashboard Ejecutivo
                  </span>
                </h1>
                <p className="text-lg text-gray-600">
                  Vista consolidada de métricas clave y proyecciones de ventas
                </p>
              </div>
              <button
                onClick={() => fetchExecutiveData(selectedFamily)}
                className="flex items-center gap-2 px-6 py-3 bg-white hover:bg-gray-50 border border-gray-200 rounded-xl transition-all shadow-sm hover:shadow-md"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span className="font-medium text-gray-900">Actualizar</span>
              </button>
            </div>
          </div>

          {/* Product Family Filters */}
          <div className="mb-8 bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Filtrar por Familia de Producto</h3>
            <div className="flex flex-wrap gap-3">
              {PRODUCT_FAMILIES.map((family) => (
                <button
                  key={family.value}
                  onClick={() => setSelectedFamily(family.value)}
                  className={`
                    flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all
                    ${
                      selectedFamily === family.value
                        ? 'bg-gradient-to-r from-green-500 to-green-600 text-white shadow-lg scale-105'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }
                  `}
                >
                  <span className="text-xl">{family.icon}</span>
                  <span>{family.name}</span>
                </button>
              ))}
            </div>
            {selectedFamily !== 'TODAS' && (
              <p className="mt-4 text-sm text-gray-600">
                Mostrando datos solo para: <span className="font-semibold">{PRODUCT_FAMILIES.find(f => f.value === selectedFamily)?.name}</span>
              </p>
            )}
          </div>

          {/* KPI Cards with YoY Comparison */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            {/* Revenue KPI */}
            <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all transform hover:scale-105">
              <div className="flex items-center justify-between mb-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <span className="text-3xl">💰</span>
                </div>
                {data.kpis.revenue_yoy_change !== 0 && (
                  <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${
                    data.kpis.revenue_yoy_change > 0 ? 'bg-green-400/30' : 'bg-red-400/30'
                  }`}>
                    <svg className={`w-4 h-4 ${data.kpis.revenue_yoy_change > 0 ? '' : 'transform rotate-180'}`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L6.707 7.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm font-medium">{data.kpis.revenue_yoy_change.toFixed(1)}%</span>
                  </div>
                )}
              </div>
              <div className="text-sm opacity-90 mb-1">Ingresos Totales</div>
              <div className="text-2xl font-bold">${Math.round(data.kpis.total_revenue_2025_actual).toLocaleString('es-CL')}</div>
              <div className="text-xs opacity-75 mt-2">
                YTD 2025 vs 2024: ${Math.round(data.kpis.total_revenue_2024).toLocaleString('es-CL')}
              </div>
            </div>

            {/* Orders KPI */}
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all transform hover:scale-105">
              <div className="flex items-center justify-between mb-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <span className="text-3xl">📦</span>
                </div>
                {data.kpis.orders_yoy_change !== 0 && (
                  <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${
                    data.kpis.orders_yoy_change > 0 ? 'bg-blue-400/30' : 'bg-red-400/30'
                  }`}>
                    <svg className={`w-4 h-4 ${data.kpis.orders_yoy_change > 0 ? '' : 'transform rotate-180'}`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L6.707 7.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm font-medium">{data.kpis.orders_yoy_change.toFixed(1)}%</span>
                  </div>
                )}
              </div>
              <div className="text-sm opacity-90 mb-1">Total Órdenes</div>
              <div className="text-3xl font-bold">{data.kpis.total_orders_2025_actual.toLocaleString('es-CL')}</div>
              <div className="text-xs opacity-75 mt-2">
                YTD 2025 vs 2024: {data.kpis.total_orders_2024.toLocaleString('es-CL')}
              </div>
            </div>

            {/* Avg Ticket KPI */}
            <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all transform hover:scale-105">
              <div className="flex items-center justify-between mb-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <span className="text-3xl">🎫</span>
                </div>
                {data.kpis.ticket_yoy_change !== 0 && (
                  <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${
                    data.kpis.ticket_yoy_change > 0 ? 'bg-purple-400/30' : 'bg-red-400/30'
                  }`}>
                    <svg className={`w-4 h-4 ${data.kpis.ticket_yoy_change > 0 ? '' : 'transform rotate-180'}`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L6.707 7.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm font-medium">{data.kpis.ticket_yoy_change.toFixed(1)}%</span>
                  </div>
                )}
              </div>
              <div className="text-sm opacity-90 mb-1">Ticket Promedio</div>
              <div className="text-2xl font-bold">${Math.round(data.kpis.avg_ticket_2025).toLocaleString('es-CL')}</div>
              <div className="text-xs opacity-75 mt-2">
                2025: ${Math.round(data.kpis.avg_ticket_2024).toLocaleString('es-CL')} en 2024
              </div>
            </div>
          </div>

          {/* Executive Sales Chart with Projections */}
          <div className="mb-10">
            <ExecutiveSalesChart
              sales_2024={data.sales_2024}
              sales_2025_actual={data.sales_2025_actual}
              sales_2025_projected={data.sales_2025_projected}
            />
          </div>

          {/* Projection Metadata */}
          {data.projection_metadata.months_projected > 0 && (
            <div className="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-6 mb-10">
              <div className="flex items-start gap-4">
                <div className="text-4xl">📊</div>
                <div>
                  <h3 className="text-lg font-semibold text-blue-900 mb-2">
                    Proyección de Ventas 2025
                  </h3>
                  <p className="text-blue-800 mb-3">
                    Proyectando <span className="font-semibold">{data.projection_metadata.months_projected} meses restantes</span> basado en datos históricos de 2024 y tendencias YTD 2025.
                  </p>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-blue-700">Tasa de crecimiento promedio:</span>
                      <span className="ml-2 font-semibold text-blue-900">
                        {data.projection_metadata.avg_growth_rate.toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-blue-700">Variabilidad:</span>
                      <span className="ml-2 font-semibold text-blue-900">
                        ±{data.projection_metadata.std_dev.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-blue-700 mt-3">
                    Las proyecciones utilizan suavizado exponencial con ajuste estacional basado en el mismo mes del año anterior.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Quarterly Analytics - Pie Charts by Product Family, Channel, Top Customers */}
          <QuarterlyAnalytics />
        </div>
      </div>
    </>
  )
}
