'use client'

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

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
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-10">
        <div className="h-96 bg-gray-200 animate-pulse rounded-lg" />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          🏆 Top {topLimit} {groupBy ? `por ${getGroupLabel(groupBy)}` : ''}
        </h2>
        <div className="flex items-center justify-center h-64 text-gray-500">
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
    <div className="bg-white rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300 p-6 mb-10">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          🏆 Top {topLimit} {groupBy ? `por ${getGroupLabel(groupBy)}` : 'Productos'}
        </h2>
        <p className="text-sm text-gray-600">
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
                className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
              >
                <td className="py-2 px-3 text-gray-600">
                  {index + 1}
                </td>
                <td className="py-2 px-3 text-gray-900 font-medium">
                  {item.group_value || 'Sin clasificar'}
                </td>
                <td className="py-2 px-3 text-right text-gray-900 font-medium">
                  {formatCurrency(item.revenue)}
                </td>
                <td className="py-2 px-3 text-right">
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
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
