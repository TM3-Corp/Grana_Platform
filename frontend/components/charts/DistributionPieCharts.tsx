'use client'

import { useState, useEffect, useMemo } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

// Types
interface DistributionItem {
  group_value: string
  revenue: number
  units: number
  orders: number
  percentage: number
}

interface DistributionData {
  channels: DistributionItem[]
  categories: DistributionItem[]
  customers: DistributionItem[]
}

// Color palettes for each chart type
const CHANNEL_COLORS = [
  '#10B981', // Corporativo - green
  '#3B82F6', // Retail - blue
  '#8B5CF6', // E-commerce - purple
  '#F59E0B', // Distribuidor - orange
  '#EF4444', // Emporios - red
  '#06B6D4', // cyan
  '#EC4899', // pink
  '#9CA3AF', // gray (Sin Canal)
]

const CATEGORY_COLORS = [
  '#10B981', // BARRAS - green
  '#3B82F6', // CRACKERS - blue
  '#F59E0B', // GRANOLAS - orange
  '#8B5CF6', // KEEPERS - purple
]

const CUSTOMER_COLORS = [
  '#10B981', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444',
  '#06B6D4', '#EC4899', '#14B8A6', '#F97316', '#84CC16',
  '#22D3EE', '#A855F7', '#FB923C', '#4ADE80', '#38BDF8',
  '#C084FC', '#FBBF24', '#34D399', '#60A5FA', '#9CA3AF',
]

const CATEGORY_ICONS: Record<string, string> = {
  'BARRAS': '🍫',
  'CRACKERS': '🍘',
  'GRANOLAS': '🥣',
  'KEEPERS': '🍬',
}

// Date presets
interface DatePreset {
  id: string
  label: string
  getRange: () => { from: string; to: string }
}

const getDatePresets = (): DatePreset[] => {
  const today = new Date()
  const currentYear = today.getFullYear()
  const currentMonth = today.getMonth() + 1
  const currentQuarter = Math.ceil(currentMonth / 3)

  return [
    {
      id: 'ytd',
      label: 'YTD',
      getRange: () => ({
        from: `${currentYear}-01-01`,
        to: today.toISOString().split('T')[0],
      }),
    },
    {
      id: 'current_month',
      label: 'Mes Actual',
      getRange: () => {
        const firstDay = `${currentYear}-${currentMonth.toString().padStart(2, '0')}-01`
        return { from: firstDay, to: today.toISOString().split('T')[0] }
      },
    },
    {
      id: 'last_month',
      label: 'Mes Anterior',
      getRange: () => {
        const lastMonth = currentMonth === 1 ? 12 : currentMonth - 1
        const year = currentMonth === 1 ? currentYear - 1 : currentYear
        const lastDay = new Date(year, lastMonth, 0).getDate()
        return {
          from: `${year}-${lastMonth.toString().padStart(2, '0')}-01`,
          to: `${year}-${lastMonth.toString().padStart(2, '0')}-${lastDay}`,
        }
      },
    },
    {
      id: 'current_quarter',
      label: `Q${currentQuarter} ${currentYear}`,
      getRange: () => {
        const startMonth = (currentQuarter - 1) * 3 + 1
        return {
          from: `${currentYear}-${startMonth.toString().padStart(2, '0')}-01`,
          to: today.toISOString().split('T')[0],
        }
      },
    },
    {
      id: 'last_quarter',
      label: `Q${currentQuarter === 1 ? 4 : currentQuarter - 1} ${currentQuarter === 1 ? currentYear - 1 : currentYear}`,
      getRange: () => {
        const lastQ = currentQuarter === 1 ? 4 : currentQuarter - 1
        const year = currentQuarter === 1 ? currentYear - 1 : currentYear
        const startMonth = (lastQ - 1) * 3 + 1
        const endMonth = lastQ * 3
        const lastDay = new Date(year, endMonth, 0).getDate()
        return {
          from: `${year}-${startMonth.toString().padStart(2, '0')}-01`,
          to: `${year}-${endMonth.toString().padStart(2, '0')}-${lastDay}`,
        }
      },
    },
    {
      id: 'last_12_months',
      label: 'Últimos 12 meses',
      getRange: () => {
        const past = new Date(today)
        past.setFullYear(past.getFullYear() - 1)
        return {
          from: past.toISOString().split('T')[0],
          to: today.toISOString().split('T')[0],
        }
      },
    },
  ]
}

// Format currency
const formatCurrency = (value: number): string => {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
  if (value >= 1000) return `$${Math.round(value / 1000)}K`
  return `$${value.toLocaleString('es-CL')}`
}

// Custom tooltip
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

// Custom label for pie chart
const renderCustomLabel = ({ name, percentage }: any) => {
  if (percentage < 5) return null // Don't show labels for small slices
  return `${percentage.toFixed(0)}%`
}

// Detail Modal component
interface DetailModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  icon: string
  data: { name: string; value: number; percentage: number; color: string }[]
  total: number
}

const DetailModal = ({ isOpen, onClose, title, icon, data, total }: DetailModalProps) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-lg w-full mx-4 max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <span>{icon}</span> {title}
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          <div className="text-sm text-gray-500 mb-4">
            Total: <span className="font-semibold text-gray-900">{formatCurrency(total)}</span>
          </div>

          <div className="space-y-2">
            {data.map((item, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div
                  className="w-4 h-4 rounded flex-shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="flex-1 font-medium text-gray-800">
                  {item.name}
                </span>
                <span className="text-gray-600">
                  {formatCurrency(item.value)}
                </span>
                <span className="text-gray-400 text-sm w-12 text-right">
                  {item.percentage.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// Single Pie Chart component
interface SinglePieChartProps {
  title: string
  icon: string
  data: DistributionItem[]
  colors: string[]
  loading: boolean
}

const SinglePieChart = ({ title, icon, data, colors, loading }: SinglePieChartProps) => {
  const [showModal, setShowModal] = useState(false)

  const chartData = useMemo(() => {
    return data.map((item, index) => ({
      name: item.group_value || 'Sin Asignar',
      value: item.revenue,
      percentage: item.percentage,
      color: colors[index % colors.length],
    }))
  }, [data, colors])

  const total = useMemo(() => {
    return data.reduce((sum, item) => sum + item.revenue, 0)
  }, [data])

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="h-6 bg-gray-200 rounded w-1/2 mb-4 animate-pulse" />
        <div className="h-64 bg-gray-100 rounded animate-pulse" />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <span>{icon}</span> {title}
        </h3>
        <div className="h-64 flex items-center justify-center text-gray-400">
          No hay datos disponibles
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <span>{icon}</span> {title}
          </h3>
          <span className="text-sm text-gray-500">
            Total: {formatCurrency(total)}
          </span>
        </div>

        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                dataKey="value"
                label={renderCustomLabel}
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
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
          {chartData.slice(0, 8).map((item, index) => (
            <div key={index} className="flex items-center gap-2 truncate">
              <div
                className="w-3 h-3 rounded-sm flex-shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <span className="truncate" title={item.name}>
                {item.name}
              </span>
              <span className="text-gray-400 ml-auto">
                {item.percentage.toFixed(0)}%
              </span>
            </div>
          ))}
          {chartData.length > 8 && (
            <button
              onClick={() => setShowModal(true)}
              className="text-green-600 hover:text-green-700 col-span-2 text-center font-medium hover:underline cursor-pointer"
            >
              +{chartData.length - 8} más →
            </button>
          )}
        </div>

        {/* View All Button */}
        <button
          onClick={() => setShowModal(true)}
          className="mt-3 w-full py-2 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
        >
          Ver detalle completo
        </button>
      </div>

      {/* Detail Modal */}
      <DetailModal
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

// Main component
export default function DistributionPieCharts() {
  const [data, setData] = useState<DistributionData>({
    channels: [],
    categories: [],
    customers: [],
  })
  const [loading, setLoading] = useState(true)
  const [selectedPreset, setSelectedPreset] = useState('ytd')
  const [customFromDate, setCustomFromDate] = useState('')
  const [customToDate, setCustomToDate] = useState('')
  const [showCustom, setShowCustom] = useState(false)

  const datePresets = useMemo(() => getDatePresets(), [])

  // Get current date range
  const getDateRange = () => {
    if (showCustom && customFromDate && customToDate) {
      return { from: customFromDate, to: customToDate }
    }
    const preset = datePresets.find(p => p.id === selectedPreset)
    return preset ? preset.getRange() : datePresets[0].getRange()
  }

  // Fetch distribution data
  const fetchData = async () => {
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const { from, to } = getDateRange()

      // Fetch all three distributions in parallel
      const [channelsRes, categoriesRes, customersRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/sales-analytics?from_date=${from}&to_date=${to}&group_by=channel&top_limit=10`),
        fetch(`${apiUrl}/api/v1/sales-analytics?from_date=${from}&to_date=${to}&group_by=category&top_limit=10`),
        fetch(`${apiUrl}/api/v1/sales-analytics?from_date=${from}&to_date=${to}&group_by=customer&top_limit=20`),
      ])

      const [channelsData, categoriesData, customersData] = await Promise.all([
        channelsRes.json(),
        categoriesRes.json(),
        customersRes.json(),
      ])

      setData({
        channels: channelsData.data?.top_items || [],
        categories: categoriesData.data?.top_items || [],
        customers: customersData.data?.top_items || [],
      })
    } catch (err) {
      console.error('Error fetching distribution data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [selectedPreset, customFromDate, customToDate, showCustom])

  return (
    <div className="space-y-6">
      {/* Date Filter Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-gray-700">📅 Período:</span>

          {/* Preset buttons */}
          <div className="flex flex-wrap gap-2">
            {datePresets.map((preset) => (
              <button
                key={preset.id}
                onClick={() => {
                  setSelectedPreset(preset.id)
                  setShowCustom(false)
                }}
                className={`
                  px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                  ${selectedPreset === preset.id && !showCustom
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                {preset.label}
              </button>
            ))}
            <button
              onClick={() => setShowCustom(!showCustom)}
              className={`
                px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                ${showCustom
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }
              `}
            >
              Personalizado
            </button>
          </div>

          {/* Custom date inputs */}
          {showCustom && (
            <div className="flex items-center gap-2 ml-auto">
              <input
                type="date"
                value={customFromDate}
                onChange={(e) => setCustomFromDate(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
              />
              <span className="text-gray-400">→</span>
              <input
                type="date"
                value={customToDate}
                onChange={(e) => setCustomToDate(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
              />
            </div>
          )}
        </div>

        {/* Current selection display */}
        <div className="mt-2 text-xs text-gray-500">
          {(() => {
            const { from, to } = getDateRange()
            const fromDate = new Date(from + 'T00:00:00')
            const toDate = new Date(to + 'T00:00:00')
            return `${fromDate.toLocaleDateString('es-CL')} - ${toDate.toLocaleDateString('es-CL')}`
          })()}
        </div>
      </div>

      {/* Pie Charts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <SinglePieChart
          title="Distribución por Canal"
          icon="🏪"
          data={data.channels}
          colors={CHANNEL_COLORS}
          loading={loading}
        />
        <SinglePieChart
          title="Distribución por Familia"
          icon="📦"
          data={data.categories}
          colors={CATEGORY_COLORS}
          loading={loading}
        />
        <SinglePieChart
          title="Top 20 Clientes"
          icon="👥"
          data={data.customers}
          colors={CUSTOMER_COLORS}
          loading={loading}
        />
      </div>
    </div>
  )
}
