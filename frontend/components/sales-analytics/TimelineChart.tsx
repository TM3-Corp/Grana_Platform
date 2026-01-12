'use client'

import { useState } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface TimelineDataPoint {
  period: string
  total_revenue: number
  total_units: number
  total_items: number
  total_orders: number
  by_group?: Array<{
    group_value: string
    revenue: number
    units: number
    items: number
    orders: number
    by_stack?: Array<{
      stack_value: string
      revenue: number
      units: number
      items: number
      orders: number
    }>
  }>
}

interface TimelineChartProps {
  data: TimelineDataPoint[] | null
  groupBy: string | null
  stackBy: string | null
  timePeriod: 'auto' | 'day' | 'week' | 'month' | 'quarter' | 'year'
  onTimePeriodChange: (period: 'auto' | 'day' | 'week' | 'month' | 'quarter' | 'year') => void
  loading?: boolean
}

type MetricType = 'revenue' | 'units' | 'items' | 'orders'

export default function TimelineChart({ data, groupBy, stackBy, timePeriod, onTimePeriodChange, loading }: TimelineChartProps) {
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

  // Format data for chart - handle all period formats
  const formattedData = data.map(d => {
    let date: Date
    let label: string

    // Detect format based on period string pattern
    if (d.period.includes('-W')) {
      // Format: "2025-W45" - Weekly
      const [year, week] = d.period.split('-W')
      label = `S${week} '${year.slice(2)}`
      // e.g., "S45 '25"
    } else if (d.period.includes('-Q')) {
      // Format: "2025-Q4" - Quarterly
      const [year, quarter] = d.period.split('-Q')
      label = `Q${quarter} '${year.slice(2)}`
      // e.g., "Q4 '25"
    } else if (d.period.length === 10) {
      // Format: "2025-11-05" (YYYY-MM-DD) - Daily
      // Parse date components directly to avoid timezone conversion issues
      const [year, month, day] = d.period.split('-').map(Number)
      date = new Date(year, month - 1, day)
      label = date.toLocaleDateString('es-CL', {
        day: 'numeric',
        month: 'short'
      })
      // e.g., "5 nov"
    } else if (d.period.length === 7) {
      // Format: "2025-11" (YYYY-MM) - Monthly
      // Parse date components directly to avoid timezone conversion issues
      const [year, month] = d.period.split('-').map(Number)
      date = new Date(year, month - 1, 1)  // Use local timezone, not UTC
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
      total_items: d.total_items,
      total_orders: d.total_orders,
      by_group: d.by_group
    }
  })

  // Prepare data for grouped view
  const hasGrouping = groupBy && formattedData.some(d => d.by_group && d.by_group.length > 0)

  // Detect if we have stacked data
  const hasStacking = stackBy && formattedData.some(d =>
    d.by_group?.some(g => g.by_stack && g.by_stack.length > 0)
  )

  // Detect if we want simple stacking (bar chart instead of line chart)
  const useStackedBars = stackBy !== null && hasStacking

  const getMetricValue = (metricType: MetricType) => {
    switch (metricType) {
      case 'revenue': return 'total_revenue'
      case 'units': return 'total_units'
      case 'items': return 'total_items'
      case 'orders': return 'total_orders'
    }
  }

  const getMetricLabel = (metricType: MetricType) => {
    switch (metricType) {
      case 'revenue': return 'Ingresos'
      case 'units': return 'Unidades'
      case 'items': return 'Items'
      case 'orders': return 'Órdenes'
    }
  }

  const formatYAxis = (value: number) => {
    if (selectedMetric === 'revenue') {
      return `$${Math.round(value).toLocaleString('es-CL')}`
    } else {
      return Math.round(value).toLocaleString('es-CL')
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

  // Colors for stack values (consistent across all groups)
  const stackColors: Record<string, string> = {
    'Corporativo': '#10B981',      // green
    'Retail': '#3B82F6',            // blue
    'E-commerce': '#8B5CF6',        // purple
    'Distribuidor': '#F59E0B',      // orange
    'Emporios y Cafeterías': '#EF4444', // red
    'Sin Canal Asignado': '#9CA3AF', // gray
  }

  // Get color for a stack value (with fallback)
  const getStackColor = (stackValue: string, index: number) => {
    return stackColors[stackValue] || groupColors[index % groupColors.length]
  }

  // Extract unique group values and limit to top 20 by total revenue
  // IMPORTANT: Filter out null/empty group values
  const groupValues = hasGrouping
    ? (() => {
        // Calculate total for each group across all periods
        const groupTotals = new Map<string, number>();

        formattedData.forEach(d => {
          d.by_group?.forEach(g => {
            // Skip null/empty group values
            if (!g.group_value || g.group_value.trim() === '') return;

            const value = selectedMetric === 'revenue' ? g.revenue : selectedMetric === 'units' ? g.units : selectedMetric === 'items' ? g.items : g.orders;
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

  // === DATA TRANSFORMATION FOR STACKED BARS ===
  // Extract all unique stack values for simple stacked bars
  // IMPORTANT: Filter out null/empty values to prevent chart rendering issues
  const simpleStackValues = new Set<string>()

  if (useStackedBars) {
    formattedData.forEach(d => {
      d.by_group?.forEach(g => {
        g.by_stack?.forEach(s => {
          // Only add valid, non-empty stack values
          if (s.stack_value && s.stack_value.trim() !== '') {
            simpleStackValues.add(s.stack_value)
          }
        })
      })
    })
  }

  // Legacy: Extract all unique combinations of (group_value, stack_value) for grouped stacked bars
  // IMPORTANT: Filter out null/empty values
  const stackCombinations: Array<{ group: string; stack: string }> = []
  const uniqueStackValues = new Set<string>()

  if (hasStacking && !useStackedBars) {
    formattedData.forEach(d => {
      d.by_group?.forEach(g => {
        if (g.group_value && groupValues.includes(g.group_value)) {
          g.by_stack?.forEach(s => {
            // Skip null/empty stack values
            if (!s.stack_value || s.stack_value.trim() === '') return

            const key = `${g.group_value}_${s.stack_value}`
            if (!stackCombinations.find(c => c.group === g.group_value && c.stack === s.stack_value)) {
              stackCombinations.push({ group: g.group_value, stack: s.stack_value })
              uniqueStackValues.add(s.stack_value)
            }
          })
        }
      })
    })
  }

  // Prepare chart data (different structure for stacked bars)
  // IMPORTANT: Filter out null/empty values to prevent chart bugs like "$ago 25 CLP"
  const chartData = useStackedBars
    ? formattedData.map(d => {
        const point: any = {
          period: d.period,
        }

        // For simple stacked bars: sum all groups for each stack value
        const stackTotals = new Map<string, number>()

        d.by_group?.forEach(g => {
          g.by_stack?.forEach(s => {
            // Skip null/empty stack values
            if (!s.stack_value || s.stack_value.trim() === '') return

            const value = selectedMetric === 'revenue' ? s.revenue : selectedMetric === 'units' ? s.units : selectedMetric === 'items' ? s.items : s.orders
            stackTotals.set(s.stack_value, (stackTotals.get(s.stack_value) || 0) + value)
          })
        })

        // Add each stack value as a field
        stackTotals.forEach((value, stackValue) => {
          point[stackValue] = value
        })

        return point
      })
    : hasStacking
    ? formattedData.map(d => {
        const point: any = {
          period: d.period,
        }

        // For each group, add all its stack values as separate fields
        d.by_group?.forEach(g => {
          // Skip null/empty group values
          if (!g.group_value || !groupValues.includes(g.group_value)) return

          g.by_stack?.forEach(s => {
            // Skip null/empty stack values
            if (!s.stack_value || s.stack_value.trim() === '') return

            const key = `${g.group_value}_${s.stack_value}`
            const value = selectedMetric === 'revenue' ? s.revenue : selectedMetric === 'units' ? s.units : selectedMetric === 'items' ? s.items : s.orders
            point[key] = value
          })
        })

        return point
      })
    : hasGrouping
    ? formattedData.map(d => {
        const point: any = {
          period: d.period,
          total: selectedMetric === 'revenue' ? d.total_revenue : selectedMetric === 'units' ? d.total_units : selectedMetric === 'items' ? d.total_items : d.total_orders
        }

        // Add each group as a separate line (only if in top 20)
        d.by_group?.forEach(g => {
          // Skip null/empty group values
          if (!g.group_value || !groupValues.includes(g.group_value)) return

          const value = selectedMetric === 'revenue' ? g.revenue : selectedMetric === 'units' ? g.units : selectedMetric === 'items' ? g.items : g.orders
          point[g.group_value] = value
        })

        return point
      })
    : formattedData.map(d => ({
        period: d.period,
        total: selectedMetric === 'revenue' ? d.total_revenue : selectedMetric === 'units' ? d.total_units : selectedMetric === 'items' ? d.total_items : d.total_orders
      }))

  return (
    <div className="bg-white rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300 p-6 mb-10">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
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
              onClick={() => setSelectedMetric('items')}
              className={`
                px-4 py-2 rounded-lg text-sm font-medium transition-colors
                ${selectedMetric === 'items'
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }
              `}
            >
              Items
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

        {/* Time Period Selector */}
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700">⏱️ Agrupación:</span>
          <div className="flex gap-1">
            {['auto', 'day', 'week', 'month', 'quarter', 'year'].map((period) => (
              <button
                key={period}
                onClick={() => onTimePeriodChange(period as any)}
                className={`
                  px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                  ${timePeriod === period
                    ? 'bg-gray-800 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }
                `}
              >
                {period === 'auto' ? 'Auto' :
                 period === 'day' ? 'Diario' :
                 period === 'week' ? 'Semanal' :
                 period === 'month' ? 'Mensual' :
                 period === 'quarter' ? 'Trimestral' : 'Anual'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart - Conditional rendering based on stacking */}
      <ResponsiveContainer width="100%" height={400}>
        {useStackedBars ? (
          /* SIMPLE STACKED BAR CHART */
          <BarChart data={chartData}>
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

            {/* Create one Bar per stack value - all stacked together */}
            {Array.from(simpleStackValues).map((stackValue, index) => (
              <Bar
                key={stackValue}
                dataKey={stackValue}
                stackId="total"  // All bars stack on same ID
                fill={getStackColor(stackValue, index)}
                name={stackValue}
              />
            ))}
          </BarChart>
        ) : hasStacking ? (
          /* GROUPED STACKED BAR CHART (Legacy - rarely used) */
          <BarChart data={chartData}>
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

            {/* Create one Bar per (group × stack) combination */}
            {stackCombinations.map((combo, index) => (
              <Bar
                key={`${combo.group}_${combo.stack}`}
                dataKey={`${combo.group}_${combo.stack}`}
                stackId={combo.group}  // Stack bars by group
                fill={getStackColor(combo.stack, index)}
                name={`${combo.group} - ${combo.stack}`}
              />
            ))}
          </BarChart>
        ) : (
          /* LINE CHART (existing behavior) */
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
        )}
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
