'use client'

import { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

// Types
interface QuarterData {
  revenue: number
  units: number
  orders: number
}

interface QuartersBreakdown {
  Q1: QuarterData
  Q2: QuarterData
  Q3: QuarterData
  Q4: QuarterData
}

interface ProductFamily {
  name: string
  icon: string
  quarters: QuartersBreakdown
  totals: QuarterData
}

interface Channel {
  name: string
  icon: string
  quarters: QuartersBreakdown
  totals: QuarterData
}

interface Customer {
  id: number
  name: string
  quarters: QuartersBreakdown
  totals: QuarterData
}

interface QuarterlyData {
  year: number
  available_years: number[]
  product_families: ProductFamily[]
  channels: Channel[]
  top_customers: Customer[]
}

// Quarter colors - consistent across all charts
const QUARTER_COLORS = {
  Q1: '#3B82F6', // Blue
  Q2: '#F97316', // Orange
  Q3: '#22C55E', // Green
  Q4: '#1E40AF', // Dark Blue
}

const QUARTER_LABELS = {
  Q1: '1er trim.',
  Q2: '2º trim.',
  Q3: '3er trim.',
  Q4: '4º trim.',
}

// Format currency
const formatCurrency = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  } else if (value >= 1000) {
    return `$${Math.round(value / 1000)}K`
  }
  return `$${value.toLocaleString('es-CL')}`
}

// Format number
const formatNumber = (value: number): string => {
  return value.toLocaleString('es-CL')
}

// Custom tooltip for pie charts
const CustomTooltip = ({ active, payload, metric }: any) => {
  if (!active || !payload || payload.length === 0) return null

  const data = payload[0]
  const quarter = data.name
  const value = data.value
  const percent = data.payload.percent

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-gray-800 mb-1">{QUARTER_LABELS[quarter as keyof typeof QUARTER_LABELS]}</p>
      <p className="text-gray-600">
        {metric === 'revenue' ? formatCurrency(value) : formatNumber(value)}
      </p>
      <p className="text-gray-500 text-xs">{percent.toFixed(1)}% del total</p>
    </div>
  )
}

// Mini Pie Chart component
interface MiniPieChartProps {
  data: QuartersBreakdown
  metric: 'revenue' | 'units' | 'orders'
  total: number
}

const MiniPieChart = ({ data, metric, total }: MiniPieChartProps) => {
  const chartData = Object.entries(data).map(([quarter, values]) => ({
    name: quarter,
    value: values[metric],
    percent: total > 0 ? (values[metric] / total) * 100 : 0,
  }))

  // Check if we have any data
  const hasData = chartData.some(d => d.value > 0)

  if (!hasData) {
    return (
      <div className="w-16 h-16 flex items-center justify-center text-gray-300 text-xs">
        Sin datos
      </div>
    )
  }

  return (
    <div className="w-16 h-16">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={0}
            outerRadius={28}
            paddingAngle={1}
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={QUARTER_COLORS[entry.name as keyof typeof QUARTER_COLORS]}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip metric={metric} />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

// Section component for each analytics group
interface AnalyticsSectionProps {
  title: string
  icon: string
  year: number
  availableYears: number[]
  onYearChange: (year: number) => void
  children: React.ReactNode
}

const AnalyticsSection = ({ title, icon, year, availableYears, onYearChange, children }: AnalyticsSectionProps) => {
  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <span>{icon}</span>
          {title}
        </h3>
        <select
          value={year}
          onChange={(e) => onYearChange(parseInt(e.target.value))}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          {availableYears.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Column Headers */}
      <div className="grid grid-cols-4 gap-4 mb-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
        <div></div>
        <div className="text-center">Venta Neta</div>
        <div className="text-center">Unidades</div>
        <div className="text-center">Pedidos</div>
      </div>

      {children}

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-center gap-4 text-xs text-gray-600">
        {Object.entries(QUARTER_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: QUARTER_COLORS[key as keyof typeof QUARTER_COLORS] }}
            />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Row component for each item (product family, channel, or customer)
interface AnalyticsRowProps {
  name: string
  icon?: string
  rank?: number
  quarters: QuartersBreakdown
  totals: QuarterData
}

const AnalyticsRow = ({ name, icon, rank, quarters, totals }: AnalyticsRowProps) => {
  return (
    <div className="grid grid-cols-4 gap-4 py-3 border-b border-gray-100 last:border-b-0 hover:bg-gray-50 transition-colors">
      {/* Name Column */}
      <div className="flex items-center gap-2">
        {rank && (
          <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold flex items-center justify-center">
            {rank}
          </span>
        )}
        {icon && <span className="text-lg">{icon}</span>}
        <span className="font-medium text-gray-800 text-sm truncate" title={name}>
          {name.length > 20 ? `${name.substring(0, 20)}...` : name}
        </span>
      </div>

      {/* Revenue Pie + Total */}
      <div className="flex flex-col items-center">
        <MiniPieChart data={quarters} metric="revenue" total={totals.revenue} />
        <span className="text-xs font-semibold text-gray-700 mt-1">
          {formatCurrency(totals.revenue)}
        </span>
      </div>

      {/* Units Pie + Total */}
      <div className="flex flex-col items-center">
        <MiniPieChart data={quarters} metric="units" total={totals.units} />
        <span className="text-xs font-semibold text-gray-700 mt-1">
          {formatNumber(totals.units)}
        </span>
      </div>

      {/* Orders Pie + Total */}
      <div className="flex flex-col items-center">
        <MiniPieChart data={quarters} metric="orders" total={totals.orders} />
        <span className="text-xs font-semibold text-gray-700 mt-1">
          {formatNumber(totals.orders)}
        </span>
      </div>
    </div>
  )
}

// Main component
export default function QuarterlyAnalytics() {
  const [data, setData] = useState<QuarterlyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear())

  const fetchData = async (year: number) => {
    try {
      setLoading(true)
      setError(null)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/analytics/quarterly-breakdown?year=${year}`)

      if (!response.ok) {
        throw new Error(`Error fetching data (${response.status})`)
      }

      const result = await response.json()
      setData(result.data)
      setSelectedYear(result.data.year)
    } catch (err) {
      console.error('Error fetching quarterly data:', err)
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData(selectedYear)
  }, [])

  const handleYearChange = (year: number) => {
    setSelectedYear(year)
    fetchData(year)
  }

  if (loading) {
    return (
      <div className="space-y-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
            <div className="space-y-4">
              {[1, 2, 3].map((j) => (
                <div key={j} className="h-20 bg-gray-100 rounded"></div>
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-red-800 font-semibold">Error cargando análisis trimestral</h3>
        <p className="text-red-600 text-sm mt-1">{error || 'No se pudieron cargar los datos'}</p>
      </div>
    )
  }

  // Filter out product families with zero revenue and limit to main ones
  const mainFamilies = data.product_families.filter(
    pf => pf.totals.revenue > 0 && !['OTROS', 'DESPACHOS', 'ALIANZA', 'CAJA MASTER'].includes(pf.name)
  )

  // Filter out channels with very low revenue
  const mainChannels = data.channels.filter(ch => ch.totals.revenue > 1000000)

  return (
    <div className="space-y-6">
      {/* Product Families Section */}
      <AnalyticsSection
        title="Ventas por Línea de Productos"
        icon="📦"
        year={selectedYear}
        availableYears={data.available_years}
        onYearChange={handleYearChange}
      >
        {mainFamilies.map((family) => (
          <AnalyticsRow
            key={family.name}
            name={family.name}
            icon={family.icon}
            quarters={family.quarters}
            totals={family.totals}
          />
        ))}
      </AnalyticsSection>

      {/* Channels Section */}
      <AnalyticsSection
        title="Ventas por Canal"
        icon="🏪"
        year={selectedYear}
        availableYears={data.available_years}
        onYearChange={handleYearChange}
      >
        {mainChannels.map((channel) => (
          <AnalyticsRow
            key={channel.name}
            name={channel.name}
            icon={channel.icon}
            quarters={channel.quarters}
            totals={channel.totals}
          />
        ))}
      </AnalyticsSection>

      {/* Top Customers Section */}
      <AnalyticsSection
        title="Top 10 Clientes por Ingresos"
        icon="👥"
        year={selectedYear}
        availableYears={data.available_years}
        onYearChange={handleYearChange}
      >
        {data.top_customers.map((customer, index) => (
          <AnalyticsRow
            key={customer.id}
            name={customer.name}
            rank={index + 1}
            quarters={customer.quarters}
            totals={customer.totals}
          />
        ))}
      </AnalyticsSection>
    </div>
  )
}
