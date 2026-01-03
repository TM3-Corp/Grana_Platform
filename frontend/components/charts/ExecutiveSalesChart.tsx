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
  total_revenue_full_month?: number  // For previous year: full month value when is_mtd=true
  estimated_full_month?: number      // For current year: estimated full month for incomplete months
  confidence_lower?: number
  confidence_upper?: number
}

interface ExecutiveSalesChartProps {
  // Dynamic year-based props
  sales_previous_year: MonthData[]
  sales_current_year: MonthData[]
  sales_current_year_projected: MonthData[]
  sales_next_year_projected: MonthData[]
  // Actual year values for labels
  previous_year: number
  current_year: number
  next_year: number
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

// Custom tooltip showing gaps between years AND projection - now receives year values
const CustomTooltip = ({ active, payload, label, previousYear, currentYear, nextYear }: any) => {
  if (!active || !payload || payload.length === 0) return null

  const revenuePrevYear = payload.find((p: any) => p.dataKey === 'revenue_previous_year')?.value
  const revenuePrevYearFull = payload.find((p: any) => p.dataKey === 'revenue_previous_year_full')?.value
  const revenueCurrYearActual = payload.find((p: any) => p.dataKey === 'revenue_current_year_actual')?.value
  const revenueCurrYearEstimated = payload.find((p: any) => p.dataKey === 'revenue_current_year_estimated')?.value
  const revenueNextYearProjected = payload.find((p: any) => p.dataKey === 'revenue_next_year_projected')?.value

  // Check if this is an MTD month
  const dataPoint = payload[0]?.payload
  const isMtd = dataPoint?.is_mtd
  const mtdDay = dataPoint?.mtd_day

  // Calculate gap between years (previous vs current)
  let gapYearsAmount = 0
  let gapYearsPercent = 0
  if (revenuePrevYear && revenueCurrYearActual) {
    gapYearsAmount = revenueCurrYearActual - revenuePrevYear
    gapYearsPercent = ((revenueCurrYearActual - revenuePrevYear) / revenuePrevYear) * 100
  }

  // Calculate gap between current and next year
  let gapNextAmount = 0
  let gapNextPercent = 0
  if (revenueCurrYearActual && revenueNextYearProjected) {
    gapNextAmount = revenueNextYearProjected - revenueCurrYearActual
    gapNextPercent = ((revenueNextYearProjected - revenueCurrYearActual) / revenueCurrYearActual) * 100
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-4 min-w-[280px]">
      <p className="font-bold text-gray-900 mb-3 border-b pb-2">
        {label}
        {isMtd && <span className="text-xs text-blue-500 ml-2">(días 1-{mtdDay})</span>}
      </p>

      {/* Values Section */}
      <div className="space-y-2 mb-3">
        {revenuePrevYear !== undefined && revenuePrevYear !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-gray-400"></span>
              <span className="text-gray-600">{isMtd ? `${previousYear} (1-${mtdDay}):` : `${previousYear} Real:`}</span>
            </span>
            <span className="font-semibold text-gray-800">
              ${revenuePrevYear.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {/* Full previous year month for MTD months */}
        {revenuePrevYearFull !== undefined && revenuePrevYearFull !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-gray-500" style={{ border: '2px dashed #6B7280' }}></span>
              <span className="text-gray-500 text-xs">{previousYear} Mes completo:</span>
            </span>
            <span className="font-medium text-gray-600 text-sm">
              ${revenuePrevYearFull.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {revenueCurrYearActual !== undefined && revenueCurrYearActual !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-teal-600"></span>
              <span className="text-gray-600">{isMtd ? `${currentYear} (1-${mtdDay}):` : `${currentYear} Real:`}</span>
            </span>
            <span className="font-semibold text-teal-700">
              ${revenueCurrYearActual.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {/* Estimated full current year month for MTD months */}
        {revenueCurrYearEstimated !== undefined && revenueCurrYearEstimated !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-600" style={{ border: '2px dashed #059669' }}></span>
              <span className="text-gray-500 text-xs">{currentYear} Estimado mes:</span>
            </span>
            <span className="font-medium text-emerald-600 text-sm">
              ${revenueCurrYearEstimated.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {revenueNextYearProjected !== undefined && revenueNextYearProjected !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-purple-600"></span>
              <span className="text-gray-600">{nextYear} Proyección:</span>
            </span>
            <span className="font-semibold text-purple-700">
              ${revenueNextYearProjected.toLocaleString('es-CL')}
            </span>
          </div>
        )}
      </div>

      {/* Gap between previous and current year */}
      {revenuePrevYear && revenueCurrYearActual && (
        <div className="pt-3 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <span className="text-gray-600 font-medium text-sm">{currentYear} vs {previousYear}:</span>
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

      {/* Gap between current and next year */}
      {revenueCurrYearActual && revenueNextYearProjected && (
        <div className="pt-2 mt-2 border-t border-gray-100">
          <div className="flex justify-between items-center">
            <span className="text-gray-600 font-medium text-sm">{nextYear} vs {currentYear}:</span>
            <div className="text-right">
              <span className={`font-bold ${gapNextAmount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {gapNextAmount >= 0 ? '+' : ''}{gapNextPercent.toFixed(1)}%
              </span>
              <p className={`text-xs ${gapNextAmount >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {gapNextAmount >= 0 ? '+' : ''}${Math.round(gapNextAmount).toLocaleString('es-CL')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ExecutiveSalesChart({
  sales_previous_year,
  sales_current_year,
  sales_current_year_projected,
  sales_next_year_projected,
  previous_year,
  current_year,
  next_year
}: ExecutiveSalesChartProps) {
  // Combine all data for the chart with dynamic year labels
  // Note: Backend returns MTD-adjusted values as primary for current month (DRY principle)
  const chartData = sales_previous_year.map(m => ({
    month: m.month_name,
    monthNum: m.month,
    revenue_previous_year: m.total_revenue,  // Already MTD-adjusted for current month by backend
    revenue_previous_year_full: m.is_mtd ? (m.total_revenue_full_month ?? null) : null,  // Full month for MTD months (striped gray)
    revenue_current_year_actual: null as number | null,
    revenue_current_year_estimated: null as number | null,  // Estimated full month for MTD months (striped green)
    revenue_current_year_projected: null as number | null,
    revenue_next_year_projected: null as number | null,
    confidence_lower_next: null as number | null,
    confidence_upper_next: null as number | null,
    gap_years_percent: null as number | null,
    gap_years_amount: null as number | null,
    gap_next_percent: null as number | null,
    gap_next_amount: null as number | null,
    is_future: false,
    is_mtd: m.is_mtd ?? false,  // Get MTD flag from previous year data
    mtd_day: m.mtd_day ?? null
  }))

  // Add current year projected data (kept for reference but not displayed prominently)
  sales_current_year_projected.forEach(m => {
    const index = m.month - 1
    if (chartData[index]) {
      chartData[index].revenue_current_year_projected = m.total_revenue
    }
  })

  // Add current year actual data
  // Note: Backend returns MTD-adjusted values as primary for current month (DRY principle)
  sales_current_year.forEach(m => {
    const index = m.month - 1
    if (chartData[index]) {
      chartData[index].revenue_current_year_actual = m.total_revenue
      chartData[index].is_mtd = m.is_mtd ?? false
      chartData[index].mtd_day = m.mtd_day ?? null

      // For incomplete months, add estimated full month (striped green line)
      if (m.is_mtd && m.estimated_full_month) {
        chartData[index].revenue_current_year_estimated = m.estimated_full_month
        // Extend to previous month using that month's ACTUAL value so line connects properly
        if (index > 0 && chartData[index - 1].revenue_current_year_actual) {
          chartData[index - 1].revenue_current_year_estimated = chartData[index - 1].revenue_current_year_actual
        }
      }

      // Calculate gap vs previous year
      // Backend already returns MTD-adjusted previous year value for current month
      const revPrev = chartData[index].revenue_previous_year
      if (revPrev) {
        chartData[index].gap_years_percent = ((m.total_revenue - revPrev) / revPrev) * 100
        chartData[index].gap_years_amount = m.total_revenue - revPrev
      }
    }
  })

  // Extend previous year full month values to prior month using that month's ACTUAL value
  chartData.forEach((d, index) => {
    if (d.is_mtd && d.revenue_previous_year_full && index > 0) {
      // Use prior month's actual previous year value so line connects properly
      chartData[index - 1].revenue_previous_year_full = chartData[index - 1].revenue_previous_year
    }
  })

  // Add next year projected data and calculate gaps vs current year
  sales_next_year_projected.forEach(m => {
    const index = m.month - 1
    if (chartData[index]) {
      chartData[index].revenue_next_year_projected = m.total_revenue
      chartData[index].confidence_lower_next = m.confidence_lower ?? null
      chartData[index].confidence_upper_next = m.confidence_upper ?? null

      // Calculate gap vs current year actual
      const revCurr = chartData[index].revenue_current_year_actual
      if (revCurr) {
        chartData[index].gap_next_percent = ((m.total_revenue - revCurr) / revCurr) * 100
        chartData[index].gap_next_amount = m.total_revenue - revCurr
      }
    }
  })

  // Get current month name for dynamic labels
  const currentMonthName = chartData.find(d => d.is_mtd)?.month || 'Mes actual'

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          Comparación de Ventas y Proyección {next_year}
        </h2>
        <p className="text-sm text-gray-600">
          Datos reales de {previous_year} y {current_year}, con proyección {next_year} basada en crecimiento YoY. Hover sobre cada punto para ver las diferencias.
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
          <Tooltip content={<CustomTooltip previousYear={previous_year} currentYear={current_year} nextYear={next_year} />} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />

          {/* Confidence interval area for next year projections - light purple */}
          <Area
            type="monotone"
            dataKey="confidence_upper_next"
            stroke="none"
            fill="#9333EA"
            fillOpacity={0.1}
            name={`Rango de confianza ${next_year}`}
            legendType="none"
          />
          <Area
            type="monotone"
            dataKey="confidence_lower_next"
            stroke="none"
            fill="white"
            fillOpacity={1}
            legendType="none"
          />

          {/* Previous year actual line - GRAY solid */}
          <Line
            type="monotone"
            dataKey="revenue_previous_year"
            stroke="#9CA3AF"
            strokeWidth={2}
            name={`${previous_year} (Real)`}
            dot={{ r: 4, fill: '#9CA3AF', strokeWidth: 1, stroke: '#6B7280' }}
            activeDot={{ r: 7, fill: '#6B7280' }}
          />

          {/* Current year actual line - TEAL solid */}
          <Line
            type="monotone"
            dataKey="revenue_current_year_actual"
            stroke="#0D9488"
            strokeWidth={3}
            name={`${current_year} (Real)`}
            dot={{ r: 5, fill: '#0D9488', strokeWidth: 2, stroke: '#115E59' }}
            activeDot={{ r: 8, fill: '#115E59' }}
            label={<CustomLabel color="#0D9488" />}
          />

          {/* Next year projected line - PURPLE dashed */}
          <Line
            type="monotone"
            dataKey="revenue_next_year_projected"
            stroke="#9333EA"
            strokeWidth={3}
            strokeDasharray="8 4"
            name={`${next_year} (Proyección)`}
            dot={{ r: 5, fill: '#9333EA', strokeWidth: 2, stroke: '#7C3AED' }}
            activeDot={{ r: 8, fill: '#7C3AED' }}
            label={<CustomLabel color="#9333EA" />}
          />

          {/* Striped gray line for full previous year month (incomplete months only) */}
          <Line
            type="monotone"
            dataKey="revenue_previous_year_full"
            stroke="#6B7280"
            strokeWidth={2}
            strokeDasharray="5 5"
            name={`${previous_year} Mes completo`}
            dot={(props: any) => {
              // Only show dot at MTD month
              if (!props.payload?.is_mtd) return null
              return <circle key={`dot-prev-full-${props.index}`} cx={props.cx} cy={props.cy} r={5} fill="#6B7280" stroke="#4B5563" strokeWidth={2} />
            }}
            connectNulls={false}
            legendType="none"
            label={(props: any) => {
              // Only show label at MTD month
              if (!props.payload?.is_mtd) return null
              return <CustomLabel key={`label-prev-full-${props.index}`} {...props} color="#6B7280" />
            }}
          />

          {/* Striped green line for estimated current year full month (incomplete months only) */}
          <Line
            type="monotone"
            dataKey="revenue_current_year_estimated"
            stroke="#059669"
            strokeWidth={2}
            strokeDasharray="5 5"
            name={`${current_year} Estimado`}
            dot={(props: any) => {
              // Only show dot at MTD month
              if (!props.payload?.is_mtd) return null
              return <circle key={`dot-curr-est-${props.index}`} cx={props.cx} cy={props.cy} r={5} fill="#059669" stroke="#047857" strokeWidth={2} />
            }}
            connectNulls={false}
            legendType="none"
            label={(props: any) => {
              // Only show label at MTD month
              if (!props.payload?.is_mtd) return null
              return <CustomLabel key={`label-curr-est-${props.index}`} {...props} color="#059669" />
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
            <span className="text-gray-700 font-medium">{previous_year} Real</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-1 bg-teal-600 rounded"></div>
            <div className="w-3 h-3 rounded-full bg-teal-600 -ml-2"></div>
            <span className="text-gray-700 font-medium">{current_year} Real</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-1 bg-purple-600 rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #9333EA 0px, #9333EA 6px, transparent 6px, transparent 10px)' }}></div>
            <div className="w-3 h-3 rounded-full bg-purple-600 -ml-2"></div>
            <span className="text-gray-700 font-medium">{next_year} Proyección</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-4 bg-purple-100 rounded border border-purple-200"></div>
            <span className="text-gray-700 font-medium">Rango de confianza</span>
          </div>
        </div>
        {/* Striped lines legend for incomplete months */}
        {chartData.some(d => d.is_mtd) && (
          <div className="flex flex-wrap items-center justify-center gap-6 text-sm mt-3 pt-3 border-t border-gray-100">
            <span className="text-xs text-gray-500 font-medium">Mes en curso ({currentMonthName}):</span>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #6B7280 0px, #6B7280 4px, transparent 4px, transparent 8px)' }}></div>
              <div className="w-2.5 h-2.5 rounded-full bg-gray-500 -ml-1"></div>
              <span className="text-gray-600 text-xs">{previous_year} Mes completo</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #059669 0px, #059669 4px, transparent 4px, transparent 8px)' }}></div>
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-600 -ml-1"></div>
              <span className="text-gray-600 text-xs">{current_year} Estimado mes completo</span>
            </div>
          </div>
        )}
      </div>

      {/* Gap between previous and current year */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Diferencia Años ({current_year} Real vs {previous_year}):</h3>
        <div className="grid grid-cols-6 md:grid-cols-12 gap-2 text-xs">
          {chartData.map((d, idx) => {
            const hasData = d.revenue_current_year_actual !== null
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

      {/* Gap between current and next year projections */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Crecimiento Proyectado {next_year} (vs {current_year} Real):</h3>
        <div className="grid grid-cols-6 md:grid-cols-12 gap-2 text-xs">
          {chartData.map((d, idx) => {
            const hasCurr = d.revenue_current_year_actual !== null
            const hasNext = d.revenue_next_year_projected !== null
            const hasComparison = hasCurr && hasNext
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
                {hasComparison && d.gap_next_percent !== null && d.gap_next_amount !== null ? (
                  <>
                    <div className={`font-bold ${d.gap_next_percent >= 0 ? 'text-purple-600' : 'text-red-600'}`}>
                      {d.gap_next_percent >= 0 ? '+' : ''}{d.gap_next_percent.toFixed(0)}%
                    </div>
                    <div className={`text-[10px] ${d.gap_next_amount >= 0 ? 'text-purple-500' : 'text-red-500'}`}>
                      {formatAmount(d.gap_next_amount)}
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
