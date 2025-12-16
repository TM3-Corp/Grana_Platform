import { XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, ComposedChart, Line } from 'recharts'

interface MonthData {
  month: number
  month_name: string
  year: number
  total_orders: number
  total_revenue: number
  is_actual?: boolean
  is_projection?: boolean
  is_future?: boolean
  confidence_lower?: number
  confidence_upper?: number
}

interface ExecutiveSalesChartProps {
  sales_2024: MonthData[]
  sales_2025_actual: MonthData[]
  sales_2025_projected: MonthData[]
}

// Custom label component for data points
const CustomLabel = ({ x, y, value, color }: { x?: number; y?: number; value?: number; color: string }) => {
  if (!value || value === 0 || x === undefined || y === undefined) return null
  const formattedValue = `$${(value / 1000000).toFixed(1)}M`
  return (
    <text x={x} y={y - 12} fill={color} fontSize={10} textAnchor="middle" fontWeight="600">
      {formattedValue}
    </text>
  )
}

// Custom tooltip showing gaps between years AND projection
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || payload.length === 0) return null

  const revenue2024 = payload.find((p: any) => p.dataKey === 'revenue_2024')?.value
  const revenue2025Actual = payload.find((p: any) => p.dataKey === 'revenue_2025_actual')?.value
  const revenue2025Projected = payload.find((p: any) => p.dataKey === 'revenue_2025_projected')?.value

  // Calculate gap between years (2024 vs 2025)
  let gapYearsAmount = 0
  let gapYearsPercent = 0
  if (revenue2024 && revenue2025Actual) {
    gapYearsAmount = revenue2025Actual - revenue2024
    gapYearsPercent = ((revenue2025Actual - revenue2024) / revenue2024) * 100
  }

  // Calculate gap between projection and actual (2025 Real vs 2025 Proyección)
  let gapProjectionAmount = 0
  let gapProjectionPercent = 0
  if (revenue2025Actual && revenue2025Projected) {
    gapProjectionAmount = revenue2025Actual - revenue2025Projected
    gapProjectionPercent = ((revenue2025Actual - revenue2025Projected) / revenue2025Projected) * 100
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-4 min-w-[280px]">
      <p className="font-bold text-gray-900 mb-3 border-b pb-2">{label}</p>

      {/* Values Section */}
      <div className="space-y-2 mb-3">
        {revenue2024 !== undefined && revenue2024 !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-gray-400"></span>
              <span className="text-gray-600">2024 Real:</span>
            </span>
            <span className="font-semibold text-gray-800">
              ${revenue2024.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {revenue2025Projected !== undefined && revenue2025Projected !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-orange-500"></span>
              <span className="text-gray-600">2025 Proyección:</span>
            </span>
            <span className="font-semibold text-orange-600">
              ${revenue2025Projected.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {revenue2025Actual !== undefined && revenue2025Actual !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-teal-600"></span>
              <span className="text-gray-600">2025 Real:</span>
            </span>
            <span className="font-semibold text-teal-700">
              ${revenue2025Actual.toLocaleString('es-CL')}
            </span>
          </div>
        )}
      </div>

      {/* Diferencia Años (2024 vs 2025 Real) */}
      {revenue2024 && revenue2025Actual && (
        <div className="pt-3 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <span className="text-gray-600 font-medium text-sm">Dif. Años (vs 2024):</span>
            <div className="text-right">
              <span className={`font-bold ${gapYearsAmount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {gapYearsAmount >= 0 ? '+' : ''}{gapYearsPercent.toFixed(1)}%
              </span>
              <p className={`text-xs ${gapYearsAmount >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {gapYearsAmount >= 0 ? '+' : ''}${Math.round(gapYearsAmount).toLocaleString('es-CL')}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Diferencia Proyección (2025 Real vs 2025 Proyección) */}
      {revenue2025Actual && revenue2025Projected && (
        <div className="pt-2 mt-2 border-t border-gray-100">
          <div className="flex justify-between items-center">
            <span className="text-gray-600 font-medium text-sm">Dif. Proyección:</span>
            <div className="text-right">
              <span className={`font-bold ${gapProjectionAmount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {gapProjectionAmount >= 0 ? '+' : ''}{gapProjectionPercent.toFixed(1)}%
              </span>
              <p className={`text-xs ${gapProjectionAmount >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {gapProjectionAmount >= 0 ? '+' : ''}${Math.round(gapProjectionAmount).toLocaleString('es-CL')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ExecutiveSalesChart({ sales_2024, sales_2025_actual, sales_2025_projected }: ExecutiveSalesChartProps) {
  // Combine all data for the chart
  const chartData = sales_2024.map(m => ({
    month: m.month_name,
    monthNum: m.month,
    revenue_2024: m.total_revenue,
    revenue_2025_actual: null as number | null,
    revenue_2025_projected: null as number | null,
    confidence_lower: null as number | null,
    confidence_upper: null as number | null,
    gap_years_percent: null as number | null,
    gap_years_amount: null as number | null,
    gap_projection_percent: null as number | null,
    gap_projection_amount: null as number | null,
    is_future: false
  }))

  // Add 2025 projected data for ALL months (this now comes for all 12 months from backend)
  sales_2025_projected.forEach(m => {
    const index = m.month - 1
    if (chartData[index]) {
      chartData[index].revenue_2025_projected = m.total_revenue
      chartData[index].confidence_lower = m.confidence_lower ?? null
      chartData[index].confidence_upper = m.confidence_upper ?? null
      chartData[index].is_future = m.is_future ?? false
    }
  })

  // Add 2025 actual data and calculate gaps
  sales_2025_actual.forEach(m => {
    const index = m.month - 1
    if (chartData[index]) {
      chartData[index].revenue_2025_actual = m.total_revenue

      // Calculate gap vs 2024
      const rev2024 = chartData[index].revenue_2024
      if (rev2024) {
        chartData[index].gap_years_percent = ((m.total_revenue - rev2024) / rev2024) * 100
        chartData[index].gap_years_amount = m.total_revenue - rev2024
      }

      // Calculate gap vs projection
      const revProjected = chartData[index].revenue_2025_projected
      if (revProjected) {
        chartData[index].gap_projection_percent = ((m.total_revenue - revProjected) / revProjected) * 100
        chartData[index].gap_projection_amount = m.total_revenue - revProjected
      }
    }
  })

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          📈 Comparación de Ventas 2024 vs 2025
        </h2>
        <p className="text-sm text-gray-600">
          Datos reales de 2024 y 2025, con proyecciones basadas en crecimiento YoY. Hover sobre cada punto para ver las diferencias.
        </p>
      </div>

      <ResponsiveContainer width="100%" height={450}>
        <ComposedChart data={chartData} margin={{ top: 30, right: 30, left: 20, bottom: 10 }}>
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
            domain={['auto', 'auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />

          {/* Confidence interval area for projections - light orange */}
          <Area
            type="monotone"
            dataKey="confidence_upper"
            stroke="none"
            fill="#F97316"
            fillOpacity={0.1}
            name="Rango de confianza"
            legendType="none"
          />
          <Area
            type="monotone"
            dataKey="confidence_lower"
            stroke="none"
            fill="white"
            fillOpacity={1}
            legendType="none"
          />

          {/* 2024 actual line - GRAY solid */}
          <Line
            type="monotone"
            dataKey="revenue_2024"
            stroke="#9CA3AF"
            strokeWidth={2}
            name="2024 (Real)"
            dot={{ r: 5, fill: '#9CA3AF', strokeWidth: 2, stroke: '#6B7280' }}
            activeDot={{ r: 8, fill: '#6B7280' }}
            label={<CustomLabel color="#6B7280" />}
          />

          {/* 2025 projected line - ORANGE dashed (for entire year) */}
          <Line
            type="monotone"
            dataKey="revenue_2025_projected"
            stroke="#F97316"
            strokeWidth={2}
            strokeDasharray="8 4"
            name="2025 (Proyección)"
            dot={{ r: 4, fill: '#F97316', strokeWidth: 1, stroke: '#EA580C' }}
            activeDot={{ r: 7, fill: '#EA580C' }}
          />

          {/* 2025 actual line - TEAL solid (very distinct from gray) */}
          <Line
            type="monotone"
            dataKey="revenue_2025_actual"
            stroke="#0D9488"
            strokeWidth={3}
            name="2025 (Real)"
            dot={{ r: 6, fill: '#0D9488', strokeWidth: 2, stroke: '#115E59' }}
            activeDot={{ r: 9, fill: '#115E59' }}
            label={<CustomLabel color="#0D9488" />}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Clear Legend explanation with color samples */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex flex-wrap items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-10 h-1 bg-gray-400 rounded"></div>
            <div className="w-3 h-3 rounded-full bg-gray-400 -ml-2"></div>
            <span className="text-gray-700 font-medium">2024 Real</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-1 bg-orange-500 rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #F97316 0px, #F97316 6px, transparent 6px, transparent 10px)' }}></div>
            <div className="w-3 h-3 rounded-full bg-orange-500 -ml-2"></div>
            <span className="text-gray-700 font-medium">2025 Proyección</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-1 bg-teal-600 rounded"></div>
            <div className="w-3 h-3 rounded-full bg-teal-600 -ml-2"></div>
            <span className="text-gray-700 font-medium">2025 Real</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-4 bg-orange-100 rounded border border-orange-200"></div>
            <span className="text-gray-700 font-medium">Rango de confianza</span>
          </div>
        </div>
      </div>

      {/* Diferencia Años - 2024 vs 2025 Real */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">📊 Diferencia Años (2025 Real vs 2024):</h3>
        <div className="grid grid-cols-6 md:grid-cols-12 gap-2 text-xs">
          {chartData.map((d, idx) => {
            const hasData = d.revenue_2025_actual !== null
            const formatAmount = (amount: number) => {
              const absAmount = Math.abs(amount)
              if (absAmount >= 1000000) {
                return `${amount >= 0 ? '+' : '-'}$${(absAmount / 1000000).toFixed(1)}M`
              }
              return `${amount >= 0 ? '+' : '-'}$${Math.round(absAmount / 1000)}K`
            }
            return (
              <div
                key={idx}
                className={`text-center p-2 rounded ${
                  !hasData
                    ? 'bg-gray-50 text-gray-400'
                    : 'bg-teal-50 border border-teal-200'
                }`}
              >
                <div className="font-medium text-gray-600">{d.month.substring(0, 3)}</div>
                {hasData && d.gap_years_percent !== null && d.gap_years_amount !== null ? (
                  <>
                    <div className={`font-bold ${d.gap_years_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {d.gap_years_percent >= 0 ? '+' : ''}{d.gap_years_percent.toFixed(0)}%
                    </div>
                    <div className={`text-[10px] ${d.gap_years_amount >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatAmount(d.gap_years_amount)}
                    </div>
                  </>
                ) : (
                  <div className="text-gray-300">-</div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Diferencia Proyección - 2025 Real vs 2025 Proyección */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">🎯 Diferencia Proyección (2025 Real vs 2025 Proyección):</h3>
        <div className="grid grid-cols-6 md:grid-cols-12 gap-2 text-xs">
          {chartData.map((d, idx) => {
            const hasActual = d.revenue_2025_actual !== null
            const hasProjection = d.revenue_2025_projected !== null
            const hasComparison = hasActual && hasProjection
            const formatAmount = (amount: number) => {
              const absAmount = Math.abs(amount)
              if (absAmount >= 1000000) {
                return `${amount >= 0 ? '+' : '-'}$${(absAmount / 1000000).toFixed(1)}M`
              }
              return `${amount >= 0 ? '+' : '-'}$${Math.round(absAmount / 1000)}K`
            }
            return (
              <div
                key={idx}
                className={`text-center p-2 rounded ${
                  !hasComparison
                    ? 'bg-gray-50 text-gray-400'
                    : 'bg-orange-50 border border-orange-200'
                }`}
              >
                <div className="font-medium text-gray-600">{d.month.substring(0, 3)}</div>
                {hasComparison && d.gap_projection_percent !== null && d.gap_projection_amount !== null ? (
                  <>
                    <div className={`font-bold ${d.gap_projection_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {d.gap_projection_percent >= 0 ? '+' : ''}{d.gap_projection_percent.toFixed(0)}%
                    </div>
                    <div className={`text-[10px] ${d.gap_projection_amount >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatAmount(d.gap_projection_amount)}
                    </div>
                  </>
                ) : (
                  <div className="text-gray-300">-</div>
                )}
              </div>
            )
          })}
        </div>
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <span className="text-green-600 font-bold">+%</span>
            <span>Superaste la proyección</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-red-600 font-bold">-%</span>
            <span>Por debajo de la proyección</span>
          </div>
        </div>
      </div>
    </div>
  )
}
