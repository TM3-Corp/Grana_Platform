'use client'

import { useEffect, useState, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import Navigation from '@/components/Navigation'
import ExecutiveSalesChart from '@/components/charts/ExecutiveSalesChart'
import YTDProgressChart from '@/components/charts/YTDProgressChart'
import {
  DashboardFilterProvider,
  useDashboardFilters,
  UnifiedFilterBar,
  CollapsibleSection,
} from '@/components/dashboard'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

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
  total_revenue_full_month?: number
  confidence_lower?: number
  confidence_upper?: number
  growth_rate_applied?: number
}

interface ExecutiveData {
  sales_previous_year: MonthData[]
  sales_current_year: MonthData[]
  sales_current_year_projected: MonthData[]
  sales_next_year_projected: MonthData[]
  kpis: {
    total_revenue_previous_year: number
    total_revenue_current_year: number
    total_revenue_next_year_projected: number
    total_orders_previous_year: number
    total_orders_current_year: number
    total_orders_next_year_projected: number
    avg_ticket_previous_year: number
    avg_ticket_current_year: number
    revenue_yoy_change: number
    orders_yoy_change: number
    ticket_yoy_change: number
    // YTD-adjusted values for fair comparison display
    total_revenue_previous_year_ytd: number
    total_orders_previous_year_ytd: number
    avg_ticket_previous_year_ytd: number
  }
  projection_metadata: {
    avg_growth_rate: number | null
    avg_growth_rate_next_year: number | null
    std_dev: number | null
    std_dev_next_year: number | null
    months_projected: number
    current_month: number
    current_month_name?: string
    current_year: number
    previous_year: number
    next_year: number
    mtd_day?: number
    is_mtd_comparison?: boolean
    mtd_comparison_info?: string | null
    // Flag indicating insufficient data for projections (filtered queries with no current year data)
    insufficient_data_for_projection?: boolean
    insufficient_data_message?: string | null
  }
}

interface DistributionItem {
  group_value: string
  revenue: number
  units: number
  orders: number
  percentage: number
}

interface YTDDailyData {
  day_of_year: number
  date_previous_year: string | null
  date_current_year: string | null
  cumulative_previous_year: number
  cumulative_current_year: number
  daily_previous_year: number
  daily_current_year: number
  ytd_difference: number
  ytd_difference_percent: number
}

interface YTDProgressData {
  previous_year: number
  current_year: number
  current_day_of_year: number
  current_date: string
  summary: {
    ytd_previous_year: number
    ytd_current_year: number
    ytd_difference: number
    ytd_difference_percent: number
  }
  daily_data: YTDDailyData[]
}

// Color palettes
const CHANNEL_COLORS = ['#10B981', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444', '#06B6D4', '#EC4899', '#9CA3AF']
const CATEGORY_COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#8B5CF6']
const CUSTOMER_COLORS = [
  '#10B981', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444',
  '#06B6D4', '#EC4899', '#14B8A6', '#F97316', '#84CC16',
  '#22D3EE', '#A855F7', '#FB923C', '#4ADE80', '#38BDF8',
  '#C084FC', '#FBBF24', '#34D399', '#60A5FA', '#9CA3AF',
]

// Spanish month names mapping
const MONTH_NAMES_ES: Record<string, string> = {
  'January': 'Enero',
  'February': 'Febrero',
  'March': 'Marzo',
  'April': 'Abril',
  'May': 'Mayo',
  'June': 'Junio',
  'July': 'Julio',
  'August': 'Agosto',
  'September': 'Septiembre',
  'October': 'Octubre',
  'November': 'Noviembre',
  'December': 'Diciembre',
}

// Get greeting based on user name
function getGreeting(name: string | null | undefined): string {
  if (!name) return 'Bienvenido/a'
  const femaleNames = ['macarena', 'maria', 'ana', 'carolina', 'francisca', 'constanza', 'valentina', 'camila', 'javiera', 'fernanda', 'catalina', 'paula', 'daniela', 'andrea', 'nicole', 'alejandra', 'natalia', 'claudia', 'patricia', 'lorena', 'sandra']
  const firstName = name.split(' ')[0].toLowerCase()
  if (femaleNames.includes(firstName)) {
    return `Bienvenida, ${name.split(' ')[0]}`
  }
  return `Bienvenido, ${name.split(' ')[0]}`
}

// Format currency helper
const formatCurrency = (value: number): string => {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
  if (value >= 1000) return `$${Math.round(value / 1000)}K`
  return `$${value.toLocaleString('es-CL')}`
}

// Custom tooltip for pie charts
const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || payload.length === 0) return null
  const data = payload[0]
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-gray-800 mb-1">{data.name}</p>
      <p className="text-gray-600">{formatCurrency(data.value)}</p>
      <p className="text-gray-500 text-xs">{data.payload.percentage?.toFixed(1)}% del total</p>
    </div>
  )
}

// Detail Modal for pie charts - minimalist table
function PieDetailModal({
  isOpen,
  onClose,
  title,
  icon,
  data,
  total,
}: {
  isOpen: boolean
  onClose: () => void
  title: string
  icon: string
  data: { name: string; value: number; percentage: number; color: string }[]
  total: number
}) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full max-h-[70vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <span>{icon}</span> {title}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Table */}
        <div className="overflow-y-auto max-h-[55vh]">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0">
              <tr className="text-left text-gray-500 text-xs uppercase">
                <th className="px-4 py-2 font-medium">Nombre</th>
                <th className="px-4 py-2 font-medium text-right">Ingresos</th>
                <th className="px-4 py-2 font-medium text-right w-20">%</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((item, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ backgroundColor: item.color }} />
                      <span className="text-gray-800">{item.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-right text-gray-600">{formatCurrency(item.value)}</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className="font-bold" style={{ color: item.color }}>{item.percentage.toFixed(1)}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t bg-gray-50 flex justify-between text-sm">
          <span className="text-gray-500">Total</span>
          <span className="font-semibold text-gray-900">{formatCurrency(total)}</span>
        </div>
      </div>
    </div>
  )
}

// Single Pie Chart component
function SinglePieChart({
  title,
  icon,
  data,
  colors,
  loading,
}: {
  title: string
  icon: string
  data: DistributionItem[]
  colors: string[]
  loading: boolean
}) {
  const [showModal, setShowModal] = useState(false)

  const chartData = useMemo(() => {
    return data.map((item, index) => ({
      name: item.group_value || 'Sin Asignar',
      value: item.revenue,
      percentage: item.percentage,
      color: colors[index % colors.length],
    }))
  }, [data, colors])

  const total = useMemo(() => data.reduce((sum, item) => sum + item.revenue, 0), [data])

  if (loading) {
    return (
      <div className="bg-gray-50 rounded-xl p-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/2 mb-4" />
        <div className="h-48 bg-gray-200 rounded" />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <span>{icon}</span> {title}
        </h3>
        <div className="h-48 flex items-center justify-center text-gray-400">
          No hay datos disponibles
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <span>{icon}</span> {title}
        </h3>

        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={70}
                dataKey="value"
                labelLine={false}
                stroke="none"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend */}
        <div className="mt-3 space-y-1.5 text-xs">
          {chartData.slice(0, 6).map((item, index) => (
            <div key={index} className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: item.color }} />
              <span className="truncate flex-1 text-gray-700" title={item.name}>{item.name}</span>
              <span className="font-semibold" style={{ color: item.color }}>{item.percentage.toFixed(0)}%</span>
            </div>
          ))}
          {chartData.length > 6 && (
            <button
              onClick={() => setShowModal(true)}
              className="w-full text-center text-green-600 hover:text-green-700 font-medium pt-1"
            >
              +{chartData.length - 6} más
            </button>
          )}
        </div>
      </div>

      <PieDetailModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={title}
        icon={icon}
        data={chartData}
        total={total}
      />
    </>
  )
}

// Main Dashboard Content (uses filter context)
function DashboardContent() {
  const { data: session } = useSession()
  const { filters, dateRange } = useDashboardFilters()

  const [executiveData, setExecutiveData] = useState<ExecutiveData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Distribution data
  const [distributionData, setDistributionData] = useState<{
    channels: DistributionItem[]
    categories: DistributionItem[]
    customers: DistributionItem[]
  }>({ channels: [], categories: [], customers: [] })
  const [distributionLoading, setDistributionLoading] = useState(true)

  // YTD Progress data
  const [ytdData, setYtdData] = useState<YTDProgressData | null>(null)
  const [ytdLoading, setYtdLoading] = useState(true)

  // Fetch executive KPIs
  useEffect(() => {
    const fetchExecutiveData = async () => {
      try {
        setLoading(true)
        setError(null)

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const params = new URLSearchParams()
        if (filters.family) {
          params.append('product_family', filters.family)
        }

        const response = await fetch(`${apiUrl}/api/v1/orders/dashboard/executive-kpis?${params}`)
        if (!response.ok) throw new Error(`Error fetching executive data (${response.status})`)

        const result = await response.json()
        setExecutiveData(result.data)
      } catch (err) {
        console.error('Error:', err)
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchExecutiveData()
  }, [filters.family])

  // Fetch YTD Progress data
  useEffect(() => {
    const fetchYTDData = async () => {
      try {
        setYtdLoading(true)
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const params = new URLSearchParams()
        if (filters.family) {
          params.append('product_family', filters.family)
        }

        const response = await fetch(`${apiUrl}/api/v1/orders/executive/ytd-progress?${params}`)
        if (!response.ok) throw new Error(`Error fetching YTD data (${response.status})`)

        const result = await response.json()
        setYtdData(result)
      } catch (err) {
        console.error('Error fetching YTD progress:', err)
      } finally {
        setYtdLoading(false)
      }
    }

    fetchYTDData()
  }, [filters.family])

  // Fetch distribution data (YTD)
  useEffect(() => {
    const fetchDistributionData = async () => {
      try {
        setDistributionLoading(true)
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

        // Build category filter if family is selected
        const categoryParam = filters.family ? `&categories=${filters.family}` : ''

        const [channelsRes, categoriesRes, customersRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/sales-analytics?from_date=${dateRange.from}&to_date=${dateRange.to}&group_by=channel&top_limit=10${categoryParam}`),
          fetch(`${apiUrl}/api/v1/sales-analytics?from_date=${dateRange.from}&to_date=${dateRange.to}&group_by=category&top_limit=10${categoryParam}`),
          fetch(`${apiUrl}/api/v1/sales-analytics?from_date=${dateRange.from}&to_date=${dateRange.to}&group_by=customer&top_limit=20${categoryParam}`),
        ])

        const [channelsData, categoriesData, customersData] = await Promise.all([
          channelsRes.json(),
          categoriesRes.json(),
          customersRes.json(),
        ])

        setDistributionData({
          channels: channelsData.data?.top_items || [],
          categories: categoriesData.data?.top_items || [],
          customers: customersData.data?.top_items || [],
        })
      } catch (err) {
        console.error('Error fetching distribution data:', err)
      } finally {
        setDistributionLoading(false)
      }
    }

    fetchDistributionData()
  }, [dateRange, filters.family])

  // Calculate projected total for current year (actual YTD + projected remaining)
  const projectedCurrentYearTotal = useMemo(() => {
    if (!executiveData) return 0
    const actualRevenue = executiveData.kpis.total_revenue_current_year
    const projectedRemaining = executiveData.sales_current_year_projected
      .reduce((sum, m) => sum + m.total_revenue, 0)
    return actualRevenue + projectedRemaining
  }, [executiveData])

  // Calculate YoY change for projected total vs previous year full
  const projectedYoYChange = useMemo(() => {
    if (!executiveData || executiveData.kpis.total_revenue_previous_year === 0) return 0
    return ((projectedCurrentYearTotal - executiveData.kpis.total_revenue_previous_year) /
            executiveData.kpis.total_revenue_previous_year * 100)
  }, [executiveData, projectedCurrentYearTotal])

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

  if (error || !executiveData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-800 font-semibold text-lg mb-2">Error</h2>
          <p className="text-red-600">{error || 'No se pudieron cargar los datos'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Unified Filter Bar */}
      <UnifiedFilterBar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Welcome Header - Clean floating style */}
        <div className="mb-6 pt-2">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            👋 {getGreeting(session?.user?.name)}
          </h1>
          <p className="text-sm text-gray-500">
            Datos <strong className="text-gray-700">YTD</strong> desde el 1 de enero hasta el {new Date().getDate()} de {new Date().toLocaleDateString('es-CL', { month: 'long' })}
          </p>
        </div>

        {/* KPI Cards - 4 cards including Projected Revenue */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {/* Revenue YTD KPI */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-500">Ingresos YTD</span>
              {executiveData.kpis.revenue_yoy_change !== 0 && (
                <span className={`text-sm font-medium ${executiveData.kpis.revenue_yoy_change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {executiveData.kpis.revenue_yoy_change > 0 ? '+' : ''}{executiveData.kpis.revenue_yoy_change.toFixed(1)}%
                </span>
              )}
            </div>
            <div className="text-2xl font-semibold text-gray-900">${Math.round(executiveData.kpis.total_revenue_current_year).toLocaleString('es-CL')}</div>
            <div className="text-sm text-gray-400 mt-2">
              vs ${Math.round(executiveData.kpis.total_revenue_previous_year_ytd).toLocaleString('es-CL')} en {executiveData.projection_metadata.previous_year}
            </div>
          </div>

          {/* Projected Revenue KPI */}
          <div className="bg-teal-50 rounded-xl border border-teal-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-teal-600">Proyectado {executiveData.projection_metadata.current_year}</span>
              {!executiveData.projection_metadata.insufficient_data_for_projection && projectedYoYChange !== 0 && (
                <span className={`text-sm font-medium ${projectedYoYChange > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {projectedYoYChange > 0 ? '+' : ''}{projectedYoYChange.toFixed(1)}%
                </span>
              )}
            </div>
            {executiveData.projection_metadata.insufficient_data_for_projection ? (
              <>
                <div className="text-base font-medium text-teal-700">Sin datos suficientes</div>
                <div className="text-sm text-teal-500">{executiveData.projection_metadata.insufficient_data_message || 'No hay datos del año actual'}</div>
              </>
            ) : (
              <>
                <div className="text-2xl font-semibold text-teal-700">${Math.round(projectedCurrentYearTotal).toLocaleString('es-CL')}</div>
                <div className="text-sm text-teal-400 mt-2">
                  vs ${Math.round(executiveData.kpis.total_revenue_previous_year).toLocaleString('es-CL')} en {executiveData.projection_metadata.previous_year}
                </div>
              </>
            )}
          </div>

          {/* Orders KPI */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-500">Total Órdenes</span>
              {executiveData.kpis.orders_yoy_change !== 0 && (
                <span className={`text-sm font-medium ${executiveData.kpis.orders_yoy_change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {executiveData.kpis.orders_yoy_change > 0 ? '+' : ''}{executiveData.kpis.orders_yoy_change.toFixed(1)}%
                </span>
              )}
            </div>
            <div className="text-2xl font-semibold text-gray-900">{executiveData.kpis.total_orders_current_year.toLocaleString('es-CL')}</div>
            <div className="text-sm text-gray-400 mt-2">
              vs {executiveData.kpis.total_orders_previous_year_ytd.toLocaleString('es-CL')} en {executiveData.projection_metadata.previous_year}
            </div>
          </div>

          {/* Avg Ticket KPI */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-500">Ticket Promedio</span>
              {executiveData.kpis.ticket_yoy_change !== 0 && (
                <span className={`text-sm font-medium ${executiveData.kpis.ticket_yoy_change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {executiveData.kpis.ticket_yoy_change > 0 ? '+' : ''}{executiveData.kpis.ticket_yoy_change.toFixed(1)}%
                </span>
              )}
            </div>
            <div className="text-2xl font-semibold text-gray-900">${Math.round(executiveData.kpis.avg_ticket_current_year).toLocaleString('es-CL')}</div>
            <div className="text-sm text-gray-400 mt-2">
              vs ${Math.round(executiveData.kpis.avg_ticket_previous_year_ytd).toLocaleString('es-CL')} en {executiveData.projection_metadata.previous_year}
            </div>
          </div>
        </div>

        {/* Executive Sales Chart with Projections */}
        <div className="mb-10">
          <ExecutiveSalesChart
            sales_previous_year={executiveData.sales_previous_year}
            sales_current_year={executiveData.sales_current_year}
            sales_current_year_projected={executiveData.sales_current_year_projected}
            sales_next_year_projected={executiveData.sales_next_year_projected}
            previous_year={executiveData.projection_metadata.previous_year}
            current_year={executiveData.projection_metadata.current_year}
            next_year={executiveData.projection_metadata.next_year}
            mtdComparisonInfo={executiveData.projection_metadata.is_mtd_comparison
              ? `${MONTH_NAMES_ES[executiveData.projection_metadata.current_month_name || ''] || executiveData.projection_metadata.current_month_name}: comparando dias 1-${executiveData.projection_metadata.mtd_day} de ${executiveData.projection_metadata.previous_year} vs ${executiveData.projection_metadata.current_year}`
              : null
            }
          />
        </div>

        {/* YTD Progress Chart */}
        <div className="mb-10">
          {ytdLoading ? (
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
              <div className="h-80 bg-gray-100 animate-pulse rounded-lg" />
            </div>
          ) : ytdData && ytdData.daily_data && ytdData.daily_data.length > 0 ? (
            <YTDProgressChart
              dailyData={ytdData.daily_data}
              summary={ytdData.summary}
              previousYear={ytdData.previous_year}
              currentYear={ytdData.current_year}
              currentDayOfYear={ytdData.current_day_of_year}
              currentDate={ytdData.current_date}
            />
          ) : null}
        </div>

        {/* Projection Summary Card */}
        {executiveData.sales_next_year_projected && executiveData.sales_next_year_projected.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-10">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-4">
              <span>📈</span> Resumen de Proyecciones
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 2026 Estimated - Teal */}
              <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-3 h-3 rounded-full bg-teal-500"></div>
                  <span className="text-sm font-medium text-teal-700">Estimado {executiveData.projection_metadata.current_year}</span>
                </div>
                <span className="text-2xl font-bold text-teal-600">${Math.round(projectedCurrentYearTotal).toLocaleString('es-CL')}</span>
                <span className="text-xs text-teal-600/70 block mt-1">YTD real + {executiveData.projection_metadata.months_projected} meses proyectados</span>
              </div>

              {/* 2027 Projection - Violet */}
              <div className="bg-violet-50 border border-violet-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-3 h-3 rounded-full bg-violet-500"></div>
                  <span className="text-sm font-medium text-violet-700">Proyección {executiveData.projection_metadata.next_year}</span>
                </div>
                <span className="text-2xl font-bold text-violet-600">${Math.round(executiveData.kpis.total_revenue_next_year_projected).toLocaleString('es-CL')}</span>
                <span className="text-xs text-violet-600/70 block mt-1">+{executiveData.projection_metadata.avg_growth_rate_next_year.toFixed(1)}% crecimiento estimado</span>
              </div>

              {/* Variability - General metric */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm font-medium text-gray-600">Variabilidad histórica</span>
                </div>
                <span className="text-2xl font-bold text-gray-700">±{executiveData.projection_metadata.std_dev_next_year.toFixed(1)}%</span>
                <span className="text-xs text-gray-500 block mt-1">
                  Desviación estándar del crecimiento interanual ({executiveData.projection_metadata.previous_year}-{executiveData.projection_metadata.current_year})
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Distribution Section - Collapsible */}
        <CollapsibleSection
          title="Distribuciones YTD"
          icon="📊"
          defaultExpanded={true}
          storageKey="dashboard_distributions"
        >
          {/* Charts Grid - Always show all 3 */}
          <div className="grid gap-6 grid-cols-1 md:grid-cols-3">
            <SinglePieChart
              title="Distribucion por Canal"
              icon="🏪"
              data={distributionData.channels}
              colors={CHANNEL_COLORS}
              loading={distributionLoading}
            />
            <SinglePieChart
              title="Distribucion por Familia"
              icon="📦"
              data={distributionData.categories}
              colors={CATEGORY_COLORS}
              loading={distributionLoading}
            />
            <SinglePieChart
              title="Top 20 Clientes"
              icon="👥"
              data={distributionData.customers}
              colors={CUSTOMER_COLORS}
              loading={distributionLoading}
            />
          </div>
        </CollapsibleSection>
      </div>
    </div>
  )
}

// Main page component - wraps with providers
export default function DashboardPage() {
  return (
    <>
      <Navigation />
      <DashboardFilterProvider>
        <DashboardContent />
      </DashboardFilterProvider>
    </>
  )
}
