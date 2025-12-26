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
  is_mtd?: boolean
  mtd_day?: number
  total_revenue_full_month?: number  // For 2024: full month value when is_mtd=true
  estimated_full_month?: number      // For 2025: estimated full month for incomplete months
  confidence_lower?: number
  confidence_upper?: number
}

interface ExecutiveSalesChartProps {
  sales_2024: MonthData[]
  sales_2025_actual: MonthData[]
  sales_2025_projected: MonthData[]
  sales_2026_projected: MonthData[]
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
  const revenue2024Full = payload.find((p: any) => p.dataKey === 'revenue_2024_full')?.value
  const revenue2025Actual = payload.find((p: any) => p.dataKey === 'revenue_2025_actual')?.value
  const revenue2025Estimated = payload.find((p: any) => p.dataKey === 'revenue_2025_estimated')?.value
  const revenue2025Projected = payload.find((p: any) => p.dataKey === 'revenue_2025_projected')?.value
  const revenue2026Projected = payload.find((p: any) => p.dataKey === 'revenue_2026_projected')?.value

  // Check if this is an MTD month
  const dataPoint = payload[0]?.payload
  const isMtd = dataPoint?.is_mtd
  const mtdDay = dataPoint?.mtd_day

  // Calculate gap between years (2024 vs 2025)
  let gapYearsAmount = 0
  let gapYearsPercent = 0
  if (revenue2024 && revenue2025Actual) {
    gapYearsAmount = revenue2025Actual - revenue2024
    gapYearsPercent = ((revenue2025Actual - revenue2024) / revenue2024) * 100
  }

  // Calculate gap between 2025 and 2026
  let gap2026Amount = 0
  let gap2026Percent = 0
  if (revenue2025Actual && revenue2026Projected) {
    gap2026Amount = revenue2026Projected - revenue2025Actual
    gap2026Percent = ((revenue2026Projected - revenue2025Actual) / revenue2025Actual) * 100
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-4 min-w-[280px]">
      <p className="font-bold text-gray-900 mb-3 border-b pb-2">
        {label}
        {isMtd && <span className="text-xs text-blue-500 ml-2">(días 1-{mtdDay})</span>}
      </p>

      {/* Values Section */}
      <div className="space-y-2 mb-3">
        {revenue2024 !== undefined && revenue2024 !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-gray-400"></span>
              <span className="text-gray-600">{isMtd ? '2024 (1-' + mtdDay + '):' : '2024 Real:'}</span>
            </span>
            <span className="font-semibold text-gray-800">
              ${revenue2024.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {/* Full 2024 month for MTD months */}
        {revenue2024Full !== undefined && revenue2024Full !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-gray-500" style={{ border: '2px dashed #6B7280' }}></span>
              <span className="text-gray-500 text-xs">2024 Mes completo:</span>
            </span>
            <span className="font-medium text-gray-600 text-sm">
              ${revenue2024Full.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {revenue2025Actual !== undefined && revenue2025Actual !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-teal-600"></span>
              <span className="text-gray-600">{isMtd ? '2025 (1-' + mtdDay + '):' : '2025 Real:'}</span>
            </span>
            <span className="font-semibold text-teal-700">
              ${revenue2025Actual.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {/* Estimated full 2025 month for MTD months */}
        {revenue2025Estimated !== undefined && revenue2025Estimated !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-600" style={{ border: '2px dashed #059669' }}></span>
              <span className="text-gray-500 text-xs">2025 Estimado mes:</span>
            </span>
            <span className="font-medium text-emerald-600 text-sm">
              ${revenue2025Estimated.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {revenue2026Projected !== undefined && revenue2026Projected !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-purple-600"></span>
              <span className="text-gray-600">2026 Proyección:</span>
            </span>
            <span className="font-semibold text-purple-700">
              ${revenue2026Projected.toLocaleString('es-CL')}
            </span>
          </div>
        )}
      </div>

      {/* Diferencia Años (2024 vs 2025 Real) */}
      {revenue2024 && revenue2025Actual && (
        <div className="pt-3 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <span className="text-gray-600 font-medium text-sm">2025 vs 2024:</span>
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

      {/* Diferencia 2026 vs 2025 */}
      {revenue2025Actual && revenue2026Projected && (
        <div className="pt-2 mt-2 border-t border-gray-100">
          <div className="flex justify-between items-center">
            <span className="text-gray-600 font-medium text-sm">2026 vs 2025:</span>
            <div className="text-right">
              <span className={`font-bold ${gap2026Amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {gap2026Amount >= 0 ? '+' : ''}{gap2026Percent.toFixed(1)}%
              </span>
              <p className={`text-xs ${gap2026Amount >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {gap2026Amount >= 0 ? '+' : ''}${Math.round(gap2026Amount).toLocaleString('es-CL')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ExecutiveSalesChart({ sales_2024, sales_2025_actual, sales_2025_projected, sales_2026_projected }: ExecutiveSalesChartProps) {
  // Combine all data for the chart
  // Note: Backend returns MTD-adjusted values as primary for current month (DRY principle)
  const chartData = sales_2024.map(m => ({
    month: m.month_name,
    monthNum: m.month,
    revenue_2024: m.total_revenue,  // Already MTD-adjusted for current month by backend
    revenue_2024_full: m.is_mtd ? (m.total_revenue_full_month ?? null) : null,  // Full month for MTD months (striped gray)
    revenue_2025_actual: null as number | null,
    revenue_2025_estimated: null as number | null,  // Estimated full month for MTD months (striped green)
    revenue_2025_projected: null as number | null,
    revenue_2026_projected: null as number | null,
    confidence_lower_2026: null as number | null,
    confidence_upper_2026: null as number | null,
    gap_years_percent: null as number | null,
    gap_years_amount: null as number | null,
    gap_2026_percent: null as number | null,
    gap_2026_amount: null as number | null,
    is_future: false,
    is_mtd: m.is_mtd ?? false,  // Get MTD flag from 2024 data
    mtd_day: m.mtd_day ?? null
  }))

  // Add 2025 projected data (kept for reference but not displayed prominently)
  sales_2025_projected.forEach(m => {
    const index = m.month - 1
    if (chartData[index]) {
      chartData[index].revenue_2025_projected = m.total_revenue
    }
  })

  // Add 2025 actual data
  // Note: Backend returns MTD-adjusted values as primary for current month (DRY principle)
  sales_2025_actual.forEach(m => {
    const index = m.month - 1
    if (chartData[index]) {
      chartData[index].revenue_2025_actual = m.total_revenue
      chartData[index].is_mtd = m.is_mtd ?? false
      chartData[index].mtd_day = m.mtd_day ?? null

      // For incomplete months, add estimated full month (striped green line)
      if (m.is_mtd && m.estimated_full_month) {
        chartData[index].revenue_2025_estimated = m.estimated_full_month
        // Extend to November using November's ACTUAL value so line connects properly
        if (index > 0 && chartData[index - 1].revenue_2025_actual) {
          chartData[index - 1].revenue_2025_estimated = chartData[index - 1].revenue_2025_actual
        }
      }

      // Calculate gap vs 2024
      // Backend already returns MTD-adjusted 2024 value for current month, so just use revenue_2024
      const rev2024 = chartData[index].revenue_2024
      if (rev2024) {
        chartData[index].gap_years_percent = ((m.total_revenue - rev2024) / rev2024) * 100
        chartData[index].gap_years_amount = m.total_revenue - rev2024
      }
    }
  })

  // Extend 2024 full month values to previous month using November's ACTUAL value
  chartData.forEach((d, index) => {
    if (d.is_mtd && d.revenue_2024_full && index > 0) {
      // Use November's actual 2024 value so line connects from Nov actual to Dec full
      chartData[index - 1].revenue_2024_full = chartData[index - 1].revenue_2024
    }
  })

  // Add 2026 projected data and calculate gaps vs 2025
  sales_2026_projected.forEach(m => {
    const index = m.month - 1
    if (chartData[index]) {
      chartData[index].revenue_2026_projected = m.total_revenue
      chartData[index].confidence_lower_2026 = m.confidence_lower ?? null
      chartData[index].confidence_upper_2026 = m.confidence_upper ?? null

      // Calculate gap vs 2025 actual
      const rev2025 = chartData[index].revenue_2025_actual
      if (rev2025) {
        chartData[index].gap_2026_percent = ((m.total_revenue - rev2025) / rev2025) * 100
        chartData[index].gap_2026_amount = m.total_revenue - rev2025
      }
    }
  })

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          Comparación de Ventas y Proyección 2026
        </h2>
        <p className="text-sm text-gray-600">
          Datos reales de 2024 y 2025, con proyección 2026 basada en crecimiento YoY. Hover sobre cada punto para ver las diferencias.
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

          {/* Confidence interval area for 2026 projections - light purple */}
          <Area
            type="monotone"
            dataKey="confidence_upper_2026"
            stroke="none"
            fill="#9333EA"
            fillOpacity={0.1}
            name="Rango de confianza 2026"
            legendType="none"
          />
          <Area
            type="monotone"
            dataKey="confidence_lower_2026"
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
            dot={{ r: 4, fill: '#9CA3AF', strokeWidth: 1, stroke: '#6B7280' }}
            activeDot={{ r: 7, fill: '#6B7280' }}
          />

          {/* 2025 actual line - TEAL solid */}
          <Line
            type="monotone"
            dataKey="revenue_2025_actual"
            stroke="#0D9488"
            strokeWidth={3}
            name="2025 (Real)"
            dot={{ r: 5, fill: '#0D9488', strokeWidth: 2, stroke: '#115E59' }}
            activeDot={{ r: 8, fill: '#115E59' }}
            label={<CustomLabel color="#0D9488" />}
          />

          {/* 2026 projected line - PURPLE dashed */}
          <Line
            type="monotone"
            dataKey="revenue_2026_projected"
            stroke="#9333EA"
            strokeWidth={3}
            strokeDasharray="8 4"
            name="2026 (Proyección)"
            dot={{ r: 5, fill: '#9333EA', strokeWidth: 2, stroke: '#7C3AED' }}
            activeDot={{ r: 8, fill: '#7C3AED' }}
            label={<CustomLabel color="#9333EA" />}
          />

          {/* Striped gray line for full 2024 month (incomplete months only) */}
          <Line
            type="monotone"
            dataKey="revenue_2024_full"
            stroke="#6B7280"
            strokeWidth={2}
            strokeDasharray="5 5"
            name="2024 Mes completo"
            dot={(props: any) => {
              // Only show dot at December (MTD month), not at November
              if (!props.payload?.is_mtd) return null
              return <circle key={`dot-2024-full-${props.index}`} cx={props.cx} cy={props.cy} r={5} fill="#6B7280" stroke="#4B5563" strokeWidth={2} />
            }}
            connectNulls={false}
            legendType="none"
            label={(props: any) => {
              // Only show label at December (MTD month)
              if (!props.payload?.is_mtd) return null
              return <CustomLabel key={`label-2024-full-${props.index}`} {...props} color="#6B7280" />
            }}
          />

          {/* Striped green line for estimated 2025 full month (incomplete months only) */}
          <Line
            type="monotone"
            dataKey="revenue_2025_estimated"
            stroke="#059669"
            strokeWidth={2}
            strokeDasharray="5 5"
            name="2025 Estimado"
            dot={(props: any) => {
              // Only show dot at December (MTD month), not at November
              if (!props.payload?.is_mtd) return null
              return <circle key={`dot-2025-est-${props.index}`} cx={props.cx} cy={props.cy} r={5} fill="#059669" stroke="#047857" strokeWidth={2} />
            }}
            connectNulls={false}
            legendType="none"
            label={(props: any) => {
              // Only show label at December (MTD month)
              if (!props.payload?.is_mtd) return null
              return <CustomLabel key={`label-2025-est-${props.index}`} {...props} color="#059669" />
            }}
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
            <div className="w-10 h-1 bg-teal-600 rounded"></div>
            <div className="w-3 h-3 rounded-full bg-teal-600 -ml-2"></div>
            <span className="text-gray-700 font-medium">2025 Real</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-1 bg-purple-600 rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #9333EA 0px, #9333EA 6px, transparent 6px, transparent 10px)' }}></div>
            <div className="w-3 h-3 rounded-full bg-purple-600 -ml-2"></div>
            <span className="text-gray-700 font-medium">2026 Proyección</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-4 bg-purple-100 rounded border border-purple-200"></div>
            <span className="text-gray-700 font-medium">Rango de confianza</span>
          </div>
        </div>
        {/* Striped lines legend for incomplete months */}
        {chartData.some(d => d.is_mtd) && (
          <div className="flex flex-wrap items-center justify-center gap-6 text-sm mt-3 pt-3 border-t border-gray-100">
            <span className="text-xs text-gray-500 font-medium">Mes en curso (Diciembre):</span>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #6B7280 0px, #6B7280 4px, transparent 4px, transparent 8px)' }}></div>
              <div className="w-2.5 h-2.5 rounded-full bg-gray-500 -ml-1"></div>
              <span className="text-gray-600 text-xs">2024 Mes completo</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #059669 0px, #059669 4px, transparent 4px, transparent 8px)' }}></div>
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-600 -ml-1"></div>
              <span className="text-gray-600 text-xs">2025 Estimado mes completo</span>
            </div>
          </div>
        )}
      </div>

      {/* Diferencia Años - 2024 vs 2025 Real */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Diferencia Años (2025 Real vs 2024):</h3>
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
                    : d.is_mtd
                      ? 'bg-blue-50 border border-blue-300'
                      : 'bg-teal-50 border border-teal-200'
                }`}
              >
                <div className="font-medium text-gray-600">
                  {d.month.substring(0, 3)}
                  {d.is_mtd && <span className="text-[8px] text-blue-500 block">1-{d.mtd_day}</span>}
                </div>
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

      {/* Diferencia Proyección 2026 - 2026 Proyección vs 2025 Real */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Crecimiento Proyectado 2026 (vs 2025 Real):</h3>
        <div className="grid grid-cols-6 md:grid-cols-12 gap-2 text-xs">
          {chartData.map((d, idx) => {
            const has2025 = d.revenue_2025_actual !== null
            const has2026 = d.revenue_2026_projected !== null
            const hasComparison = has2025 && has2026
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
                    : 'bg-purple-50 border border-purple-200'
                }`}
              >
                <div className="font-medium text-gray-600">{d.month.substring(0, 3)}</div>
                {hasComparison && d.gap_2026_percent !== null && d.gap_2026_amount !== null ? (
                  <>
                    <div className={`font-bold ${d.gap_2026_percent >= 0 ? 'text-purple-600' : 'text-red-600'}`}>
                      {d.gap_2026_percent >= 0 ? '+' : ''}{d.gap_2026_percent.toFixed(0)}%
                    </div>
                    <div className={`text-[10px] ${d.gap_2026_amount >= 0 ? 'text-purple-500' : 'text-red-500'}`}>
                      {formatAmount(d.gap_2026_amount)}
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
            <span className="text-purple-600 font-bold">+%</span>
            <span>Crecimiento proyectado</span>
          </div>
        </div>
      </div>
    </div>
  )
}
