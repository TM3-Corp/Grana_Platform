'use client'

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Trophy } from 'lucide-react'

interface TopItem {
  group_value: string
  revenue: number
  units: number
  orders: number
  percentage: number
}

interface TopItemsChartProps {
  data: TopItem[] | null
  groupBy: string | null
  topLimit: number
  loading?: boolean
}

export default function TopItemsChart({ data, groupBy, topLimit, loading }: TopItemsChartProps) {
  // Helper function - must be defined before any returns that use it
  const getGroupLabel = (group: string): string => {
    const labels: Record<string, string> = {
      category: 'Familia',
      channel: 'Canal',
      customer: 'Cliente',
      format: 'Formato',
      sku_primario: 'SKU Primario'
    }
    return labels[group] || group
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <div className="h-96 bg-gray-100 animate-pulse rounded-lg" />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Trophy className="w-5 h-5 text-amber-500" strokeWidth={1.75} />
          Top {topLimit} {groupBy ? `por ${getGroupLabel(groupBy)}` : ''}
        </h2>
        <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
          No hay datos disponibles
        </div>
      </div>
    )
  }

  // Format data for chart
  const chartData = data.map(item => ({
    name: item.group_value || 'Sin clasificar',
    revenue: item.revenue,
    percentage: item.percentage,
    fullName: item.group_value || 'Sin clasificar'
  }))

  // Truncate long names for better display
  const truncateName = (name: string, maxLength: number = 20): string => {
    if (name.length <= maxLength) return name
    return name.substring(0, maxLength - 3) + '...'
  }

  const formatCurrency = (value: number): string => {
    return `$${Math.round(value).toLocaleString('es-CL')}`
  }

  // Colors gradient for bars
  const getBarColor = (index: number): string => {
    const colors = [
      '#10B981', // green (top 1)
      '#059669', // darker green (top 2)
      '#3B82F6', // blue (top 3)
      '#2563EB', // darker blue
      '#8B5CF6', // purple
      '#7C3AED', // darker purple
      '#F59E0B', // orange
      '#D97706', // darker orange
      '#6B7280', // gray
      '#4B5563', // darker gray
    ]
    return colors[index % colors.length]
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 border-l-4 border-l-amber-500 p-6 mb-8 hover:shadow-lg hover:border-l-amber-600 transition-all duration-200">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-base font-semibold text-gray-900 mb-1 flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-100 to-orange-100 flex items-center justify-center">
            <Trophy className="w-4 h-4 text-amber-600" strokeWidth={2} />
          </div>
          Top {topLimit} {groupBy ? `por ${getGroupLabel(groupBy)}` : 'Productos'}
        </h2>
        <p className="text-xs text-gray-500 ml-10">
          Ordenado por ingresos totales
        </p>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={Math.max(400, data.length * 50)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={true} vertical={false} />
          <XAxis
            type="number"
            tickFormatter={formatCurrency}
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            tickFormatter={(value) => truncateName(value, 25)}
            width={100}
          />
          <Tooltip
            formatter={(value: number) => formatCurrency(value)}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '8px'
            }}
            labelFormatter={(label) => `${label}`}
          />
          <Bar
            dataKey="revenue"
            name="Ingresos"
            radius={[0, 8, 8, 0]}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(index)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Summary Table */}
      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2 px-3 font-semibold text-gray-700">#</th>
              <th className="text-left py-2 px-3 font-semibold text-gray-700">
                {groupBy ? getGroupLabel(groupBy) : 'Item'}
              </th>
              <th className="text-right py-2 px-3 font-semibold text-gray-700">Ingresos</th>
              <th className="text-right py-2 px-3 font-semibold text-gray-700">% Total</th>
            </tr>
          </thead>
          <tbody>
            {data.map((item, index) => (
              <tr
                key={index}
                className="border-b border-gray-100 hover:bg-amber-50 transition-colors group"
              >
                <td className="py-2 px-3">
                  <span className={`
                    inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold
                    ${index === 0 ? 'bg-gradient-to-br from-amber-400 to-orange-500 text-white' :
                      index === 1 ? 'bg-gradient-to-br from-gray-300 to-gray-400 text-white' :
                      index === 2 ? 'bg-gradient-to-br from-amber-600 to-amber-700 text-white' :
                      'bg-gray-100 text-gray-600'}
                  `}>
                    {index + 1}
                  </span>
                </td>
                <td
                  className="py-2 px-3 text-gray-900 font-medium min-w-48 group-hover:text-amber-700 transition-colors"
                  title={item.group_value || 'Sin clasificar'}
                >
                  {item.group_value || 'Sin clasificar'}
                </td>
                <td className="py-2 px-3 text-right text-gray-900 font-medium">
                  {formatCurrency(item.revenue)}
                </td>
                <td className="py-2 px-3 text-right">
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-green-100 to-emerald-100 text-green-800">
                    {item.percentage.toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
