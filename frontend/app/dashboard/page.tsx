'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import Navigation from '@/components/Navigation'
import ExecutiveSalesChart from '@/components/charts/ExecutiveSalesChart'
import DistributionPieCharts from '@/components/charts/DistributionPieCharts'
import QuarterlyAnalytics from '@/components/charts/QuarterlyAnalytics'

interface MonthData {
  month: number
  month_name: string
  year: number
  total_orders: number
  total_revenue: number
  is_actual?: boolean
  is_projection?: boolean
  is_mtd?: boolean
  mtd_day?: number
  total_revenue_full_month?: number  // Full month value when is_mtd=true
  confidence_lower?: number
  confidence_upper?: number
  growth_rate_applied?: number
}

interface ExecutiveData {
  sales_2024: MonthData[]
  sales_2025_actual: MonthData[]
  sales_2025_projected: MonthData[]
  sales_2026_projected: MonthData[]
  kpis: {
    total_revenue_2024: number
    total_revenue_2025_actual: number
    total_revenue_2026_projected: number
    total_orders_2024: number
    total_orders_2025_actual: number
    total_orders_2026_projected: number
    avg_ticket_2024: number
    avg_ticket_2025: number
    revenue_yoy_change: number
    orders_yoy_change: number
    ticket_yoy_change: number
  }
  projection_metadata: {
    avg_growth_rate: number
    avg_growth_rate_2026: number
    std_dev: number
    std_dev_2026: number
    months_projected: number
    current_month: number
    current_year: number
    mtd_day?: number
    is_mtd_comparison?: boolean
    mtd_comparison_info?: string | null
  }
}

const PRODUCT_FAMILIES = [
  { name: 'Todas', value: 'TODAS' },
  { name: 'Barras', value: 'BARRAS' },
  { name: 'Crackers', value: 'CRACKERS' },
  { name: 'Granolas', value: 'GRANOLAS' },
  { name: 'Keepers', value: 'KEEPERS' },
]

// Get greeting based on user name (uses feminine form for Macarena)
function getGreeting(name: string | null | undefined): string {
  if (!name) return 'Bienvenido/a'

  // Female users get "Bienvenida", others get "Bienvenido"
  const femaleNames = ['macarena', 'maria', 'ana', 'carolina', 'francisca', 'constanza', 'valentina', 'camila', 'javiera', 'fernanda', 'catalina', 'paula', 'daniela', 'andrea', 'nicole', 'alejandra', 'natalia', 'claudia', 'patricia', 'lorena', 'sandra']
  const firstName = name.split(' ')[0].toLowerCase()

  if (femaleNames.includes(firstName)) {
    return `Bienvenida, ${name.split(' ')[0]}`
  }
  return `Bienvenido, ${name.split(' ')[0]}`
}

export default function DashboardPage() {
  const { data: session } = useSession()
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
          {/* Welcome Banner */}
          <div className="mb-8">
            <div className="bg-gradient-to-r from-blue-50 via-indigo-50 to-blue-100 rounded-2xl p-6 shadow-sm border border-blue-100/50">
              <div>
                <h1 className="text-2xl font-semibold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                  {getGreeting(session?.user?.name)}
                </h1>
                <p className="text-blue-600/70 mt-1 font-medium">
                  Resumen ejecutivo · {new Date().toLocaleDateString('es-CL', { weekday: 'long', day: 'numeric', month: 'long' })}
                </p>
              </div>
            </div>
          </div>

          {/* Product Family Filters */}
          <div className="mb-8 bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex flex-wrap gap-2">
              {PRODUCT_FAMILIES.map((family) => (
                <button
                  key={family.value}
                  onClick={() => setSelectedFamily(family.value)}
                  className={`
                    px-4 py-2 rounded-lg text-sm font-medium transition-all
                    ${
                      selectedFamily === family.value
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }
                  `}
                >
                  {family.name}
                </button>
              ))}
            </div>
          </div>

          {/* MTD Comparison Info */}
          {data.projection_metadata.is_mtd_comparison && (
            <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm text-blue-700">
                Diciembre: comparando días 1-{data.projection_metadata.mtd_day} de 2024 vs 2025 (mes en curso)
              </span>
            </div>
          )}

          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {/* Revenue KPI */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-500">Ingresos Totales</span>
                {data.kpis.revenue_yoy_change !== 0 && (
                  <span className={`text-sm font-medium ${data.kpis.revenue_yoy_change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {data.kpis.revenue_yoy_change > 0 ? '+' : ''}{data.kpis.revenue_yoy_change.toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="text-2xl font-semibold text-gray-900">${Math.round(data.kpis.total_revenue_2025_actual).toLocaleString('es-CL')}</div>
              <div className="text-xs text-gray-400 mt-1">
                vs ${Math.round(data.kpis.total_revenue_2024).toLocaleString('es-CL')} en 2024
              </div>
            </div>

            {/* Orders KPI */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-500">Total Órdenes</span>
                {data.kpis.orders_yoy_change !== 0 && (
                  <span className={`text-sm font-medium ${data.kpis.orders_yoy_change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {data.kpis.orders_yoy_change > 0 ? '+' : ''}{data.kpis.orders_yoy_change.toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="text-2xl font-semibold text-gray-900">{data.kpis.total_orders_2025_actual.toLocaleString('es-CL')}</div>
              <div className="text-xs text-gray-400 mt-1">
                vs {data.kpis.total_orders_2024.toLocaleString('es-CL')} en 2024
              </div>
            </div>

            {/* Avg Ticket KPI */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-500">Ticket Promedio</span>
                {data.kpis.ticket_yoy_change !== 0 && (
                  <span className={`text-sm font-medium ${data.kpis.ticket_yoy_change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {data.kpis.ticket_yoy_change > 0 ? '+' : ''}{data.kpis.ticket_yoy_change.toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="text-2xl font-semibold text-gray-900">${Math.round(data.kpis.avg_ticket_2025).toLocaleString('es-CL')}</div>
              <div className="text-xs text-gray-400 mt-1">
                vs ${Math.round(data.kpis.avg_ticket_2024).toLocaleString('es-CL')} en 2024
              </div>
            </div>
          </div>

          {/* Executive Sales Chart with Projections */}
          <div className="mb-10">
            <ExecutiveSalesChart
              sales_2024={data.sales_2024}
              sales_2025_actual={data.sales_2025_actual}
              sales_2025_projected={data.sales_2025_projected}
              sales_2026_projected={data.sales_2026_projected}
            />
          </div>

          {/* Projection Metadata - 2026 */}
          {data.sales_2026_projected && data.sales_2026_projected.length > 0 && (
            <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-xl p-5 mb-8">
              <h3 className="text-sm font-medium text-gray-900 mb-2">
                Proyección de Ventas 2026
              </h3>
              <p className="text-sm text-gray-600 mb-3">
                Proyección anual basada en el crecimiento histórico 2024-2025
              </p>
              <div className="flex flex-wrap gap-6 text-sm">
                <div>
                  <span className="text-gray-500">Revenue 2026 Proyectado:</span>
                  <span className="ml-2 font-semibold text-purple-700">
                    ${Math.round(data.kpis.total_revenue_2026_projected).toLocaleString('es-CL')}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Crecimiento aplicado:</span>
                  <span className="ml-2 font-medium text-gray-900">
                    +{data.projection_metadata.avg_growth_rate_2026.toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Variabilidad:</span>
                  <span className="ml-2 font-medium text-gray-900">
                    ±{data.projection_metadata.std_dev_2026.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Distribution Pie Charts - By Channel, Family, and Top Customers */}
          <div className="mb-10">
            <DistributionPieCharts />
          </div>

          {/* Quarterly Analytics - Pie Charts by Product Family, Channel, Top Customers */}
          <QuarterlyAnalytics />
        </div>
      </div>
    </>
  )
}
