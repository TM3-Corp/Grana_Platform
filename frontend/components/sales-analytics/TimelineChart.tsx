'use client'

import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface TimelineDataPoint {
  period: string
  total_revenue: number
  total_units: number
  total_orders: number
  by_group?: Array<{
    group_value: string
    revenue: number
    units: number
    orders: number
  }>
}

interface TimelineChartProps {
  data: TimelineDataPoint[] | null
  groupBy: string | null
  loading?: boolean
}

type MetricType = 'revenue' | 'units' | 'orders'

export default function TimelineChart({ data, groupBy, loading }: TimelineChartProps) {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('revenue')

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-10">
        <div className="h-80 bg-gray-200 animate-pulse rounded-lg" />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          📈 Evolución de Ventas
        </h2>
        <div className="flex items-center justify-center h-64 text-gray-500">
          No hay datos disponibles para el período seleccionado
        </div>
      </div>
    )
  }

  // Format data for chart - handle day, month, and year formats
  const formattedData = data.map(d => {
    let date: Date
    let label: string

    // Detect format based on period string length and format
    if (d.period.length === 10) {
      // Format: "2025-11-05" (YYYY-MM-DD) - Daily
      date = new Date(d.period)
      label = date.toLocaleDateString('es-CL', {
        day: 'numeric',
        month: 'short'
      })
      // e.g., "5 nov"
    } else if (d.period.length === 7) {
      // Format: "2025-11" (YYYY-MM) - Monthly
      date = new Date(d.period + '-01')
      label = date.toLocaleDateString('es-CL', {
        month: 'short',
        year: '2-digit'
      })
      // e.g., "nov 25"
    } else if (d.period.length === 4) {
      // Format: "2025" (YYYY) - Yearly
      label = d.period
      // e.g., "2025"
    } else {
      // Fallback - use period as-is
      label = d.period
    }

    return {
      period: label,
      total_revenue: d.total_revenue,
      total_units: d.total_units,
      total_orders: d.total_orders,
      by_group: d.by_group
    }
  })

  // Prepare data for grouped view
  const hasGrouping = groupBy && formattedData.some(d => d.by_group && d.by_group.length > 0)

  const getMetricValue = (metricType: MetricType) => {
    switch (metricType) {
      case 'revenue': return 'total_revenue'
      case 'units': return 'total_units'
      case 'orders': return 'total_orders'
    }
  }

  const getMetricLabel = (metricType: MetricType) => {
    switch (metricType) {
      case 'revenue': return 'Ingresos'
      case 'units': return 'Unidades'
      case 'orders': return 'Órdenes'
    }
  }

  const formatYAxis = (value: number) => {
    if (selectedMetric === 'revenue') {
      if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
      if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`
      return `$${value}`
    } else {
      if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
      if (value >= 1000) return `${(value / 1000).toFixed(0)}K`
      return value.toString()
    }
  }

  const formatTooltip = (value: number) => {
    if (selectedMetric === 'revenue') {
      return `$${value.toLocaleString('es-CL')} CLP`
    } else {
      return value.toLocaleString('es-CL')
    }
  }

  // Colors for grouped lines
  const groupColors = [
    '#10B981', // green
    '#3B82F6', // blue
    '#8B5CF6', // purple
    '#F59E0B', // orange
    '#EF4444', // red
    '#06B6D4', // cyan
    '#EC4899', // pink
    '#14B8A6', // teal
  ]

  // Extract unique group values and limit to top 20 by total revenue
  const groupValues = hasGrouping
    ? (() => {
        // Calculate total for each group across all periods
        const groupTotals = new Map<string, number>();

        formattedData.forEach(d => {
          d.by_group?.forEach(g => {
            const value = selectedMetric === 'revenue' ? g.revenue : selectedMetric === 'units' ? g.units : g.orders;
            groupTotals.set(g.group_value, (groupTotals.get(g.group_value) || 0) + value);
          });
        });

        // Sort by total and take top 20
        return Array.from(groupTotals.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, 20)
          .map(([groupValue]) => groupValue);
      })()
    : []

  // Prepare chart data with grouped metrics (only top 20 groups)
  const chartData = hasGrouping
    ? formattedData.map(d => {
        const point: any = {
          period: d.period,
          total: selectedMetric === 'revenue' ? d.total_revenue : selectedMetric === 'units' ? d.total_units : d.total_orders
        }

        // Add each group as a separate line (only if in top 20)
        d.by_group?.forEach(g => {
          if (groupValues.includes(g.group_value)) {
            const value = selectedMetric === 'revenue' ? g.revenue : selectedMetric === 'units' ? g.units : g.orders
            point[g.group_value] = value
          }
        })

        return point
      })
    : formattedData.map(d => ({
        period: d.period,
        total: selectedMetric === 'revenue' ? d.total_revenue : selectedMetric === 'units' ? d.total_units : d.total_orders
      }))

  return (
    <div className="bg-white rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300 p-6 mb-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          📈 Evolución de Ventas
        </h2>

        {/* Metric Toggle */}
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedMetric('revenue')}
            className={`
              px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${selectedMetric === 'revenue'
                ? 'bg-green-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }
            `}
          >
            Ingresos
          </button>
          <button
            onClick={() => setSelectedMetric('units')}
            className={`
              px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${selectedMetric === 'units'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }
            `}
          >
            Unidades
          </button>
          <button
            onClick={() => setSelectedMetric('orders')}
            className={`
              px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${selectedMetric === 'orders'
                ? 'bg-purple-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }
            `}
          >
            Órdenes
          </button>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="period"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            tickFormatter={formatYAxis}
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <Tooltip
            formatter={formatTooltip}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '8px'
            }}
          />
          <Legend />

          {/* Total line (always shown) */}
          <Line
            type="monotone"
            dataKey="total"
            stroke="#1f2937"
            strokeWidth={3}
            name={`Total ${getMetricLabel(selectedMetric)}`}
            dot={{ r: 5, fill: '#1f2937' }}
          />

          {/* Grouped lines (if grouping is active) - Limited to top 20 */}
          {hasGrouping && groupValues.map((groupValue, index) => (
            <Line
              key={groupValue}
              type="monotone"
              dataKey={groupValue}
              stroke={groupColors[index % groupColors.length]}
              strokeWidth={2}
              name={groupValue}
              dot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Note when showing top 20 only */}
      {hasGrouping && groupValues.length === 20 && (
        <div className="mt-4 text-sm text-gray-600 text-center">
          📊 Mostrando los 20 principales por {getMetricLabel(selectedMetric).toLowerCase()}
        </div>
      )}
    </div>
  )
}
