import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, ComposedChart } from 'recharts'

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
}

interface ExecutiveSalesChartProps {
  sales_2024: MonthData[]
  sales_2025_actual: MonthData[]
  sales_2025_projected: MonthData[]
}

export default function ExecutiveSalesChart({ sales_2024, sales_2025_actual, sales_2025_projected }: ExecutiveSalesChartProps) {
  // Combine all data for the chart
  // 2024 data for all 12 months
  const chartData = sales_2024.map(m => ({
    month: m.month_name,
    revenue_2024: m.total_revenue,
    revenue_2025_actual: null,
    revenue_2025_projected: null,
    confidence_lower: null,
    confidence_upper: null
  }))

  // Add 2025 actual data (overlay on the months that have it)
  sales_2025_actual.forEach(m => {
    const index = m.month - 1 // month is 1-indexed
    if (chartData[index]) {
      chartData[index].revenue_2025_actual = m.total_revenue
    }
  })

  // Add 2025 projected data
  sales_2025_projected.forEach(m => {
    const index = m.month - 1
    if (chartData[index]) {
      chartData[index].revenue_2025_projected = m.total_revenue
      chartData[index].confidence_lower = m.confidence_lower
      chartData[index].confidence_upper = m.confidence_upper
    }
  })

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          📈 Comparación de Ventas 2024 vs 2025
        </h2>
        <p className="text-sm text-gray-600">
          Datos reales de 2024 y 2025, con proyecciones para el resto del año
        </p>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12 }}
            stroke="#6B7280"
          />
          <YAxis
            tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
            tick={{ fontSize: 12 }}
            stroke="#6B7280"
          />
          <Tooltip
            formatter={(value: number) => `$${value.toLocaleString('es-CL')} CLP`}
            labelStyle={{ color: '#111827', fontWeight: 600 }}
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
          />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />

          {/* Confidence interval area for projections */}
          <Area
            type="monotone"
            dataKey="confidence_upper"
            stroke="none"
            fill="#10B981"
            fillOpacity={0.1}
            name="Rango de confianza"
          />
          <Area
            type="monotone"
            dataKey="confidence_lower"
            stroke="none"
            fill="#10B981"
            fillOpacity={0.1}
          />

          {/* 2024 actual line - solid */}
          <Line
            type="monotone"
            dataKey="revenue_2024"
            stroke="#9CA3AF"
            strokeWidth={2}
            name="2024 (Real)"
            dot={{ r: 4, fill: '#9CA3AF' }}
            activeDot={{ r: 6 }}
          />

          {/* 2025 actual line - solid, vibrant green */}
          <Line
            type="monotone"
            dataKey="revenue_2025_actual"
            stroke="#10B981"
            strokeWidth={3}
            name="2025 (Real)"
            dot={{ r: 5, fill: '#10B981' }}
            activeDot={{ r: 7 }}
          />

          {/* 2025 projected line - dashed green with blue dots */}
          <Line
            type="monotone"
            dataKey="revenue_2025_projected"
            stroke="#10B981"
            strokeWidth={3}
            strokeDasharray="5 5"
            name="2025 (Proyectado)"
            dot={{ r: 5, fill: '#3B82F6', strokeDasharray: '0' }}
            activeDot={{ r: 7, fill: '#3B82F6' }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend explanation */}
      <div className="mt-6 flex items-center justify-center gap-8 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-gray-400"></div>
          <span className="text-gray-600">2024 Real</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-green-600"></div>
          <span className="text-gray-600">2025 Real</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-green-600 border-dashed border-t-2 border-green-600"></div>
          <span className="text-gray-600">2025 Proyección</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-4 bg-green-100 rounded"></div>
          <span className="text-gray-600">Rango de confianza</span>
        </div>
      </div>
    </div>
  )
}
