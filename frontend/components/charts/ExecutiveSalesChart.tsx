'use client'

import { useState, useEffect } from 'react'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, ComposedChart, Line } from 'recharts'

// Type for series visibility
type SeriesKey = 'previousYear' | 'currentYear' | 'projectedCurrentYear' | 'projectedNextYear'

interface SeriesConfig {
  key: SeriesKey
  label: string
  color: string
  defaultEnabled: boolean
}

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
  // Optional MTD comparison info
  mtdComparisonInfo?: string | null
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

// Custom tooltip showing gaps between years AND projection - now receives year values and visibility
const CustomTooltip = ({ active, payload, label, previousYear, currentYear, nextYear, showProjections }: any) => {
  if (!active || !payload || payload.length === 0) return null

  // Check if this is an MTD month - get dataPoint first for raw access
  const dataPoint = payload[0]?.payload
  const isMtd = dataPoint?.is_mtd
  const mtdDay = dataPoint?.mtd_day

  const revenuePrevYear = payload.find((p: any) => p.dataKey === 'revenue_previous_year')?.value
  // Get MTD value directly from dataPoint since there's no Line for it
  const revenuePrevYearMtd = dataPoint?.revenue_previous_year_mtd
  const revenueCurrYearActual = payload.find((p: any) => p.dataKey === 'revenue_current_year_actual')?.value
  const revenueCurrYearEstimated = payload.find((p: any) => p.dataKey === 'revenue_current_year_estimated')?.value
  const revenueCurrYearProjected = payload.find((p: any) => p.dataKey === 'revenue_current_year_projected')?.value
  const revenueNextYearProjected = payload.find((p: any) => p.dataKey === 'revenue_next_year_projected')?.value

  // Calculate gap between years (previous vs current)
  // For MTD months, compare MTD vs MTD for fair comparison
  let gapYearsAmount = 0
  let gapYearsPercent = 0
  const prevYearForComparison = isMtd && revenuePrevYearMtd ? revenuePrevYearMtd : revenuePrevYear
  if (prevYearForComparison && revenueCurrYearActual) {
    gapYearsAmount = revenueCurrYearActual - prevYearForComparison
    gapYearsPercent = ((revenueCurrYearActual - prevYearForComparison) / prevYearForComparison) * 100
  }

  // Calculate gap between current and next year
  // For MTD months, use estimated full month for fair comparison with next year projection
  let gapNextAmount = 0
  let gapNextPercent = 0
  const currYearForNextComparison = isMtd && revenueCurrYearEstimated ? revenueCurrYearEstimated : revenueCurrYearActual
  if (currYearForNextComparison && revenueNextYearProjected) {
    gapNextAmount = revenueNextYearProjected - currYearForNextComparison
    gapNextPercent = ((revenueNextYearProjected - currYearForNextComparison) / currYearForNextComparison) * 100
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-4 min-w-[280px]">
      <p className="font-bold text-gray-900 mb-3 border-b pb-2">
        {label}
        {isMtd && <span className="text-xs text-blue-500 ml-2">(días 1-{mtdDay})</span>}
      </p>

      {/* Values Section */}
      <div className="space-y-2 mb-3">
        {/* MTD comparison for previous year - show FIRST when it's an MTD month (main comparison value) */}
        {isMtd && revenuePrevYearMtd !== undefined && revenuePrevYearMtd !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-indigo-300"></span>
              <span className="text-gray-600">{previousYear} (días 1-{mtdDay}):</span>
            </span>
            <span className="font-semibold text-indigo-400">
              ${revenuePrevYearMtd.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {/* Previous year full month - show smaller when MTD, normal otherwise */}
        {revenuePrevYear !== undefined && revenuePrevYear !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-indigo-500"></span>
              <span className={isMtd ? 'text-gray-500 text-xs' : 'text-gray-600'}>{previousYear} {isMtd ? 'mes' : 'Real'}:</span>
            </span>
            <span className={isMtd ? 'font-medium text-indigo-600 text-sm' : 'font-semibold text-indigo-600'}>
              ${revenuePrevYear.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {revenueCurrYearActual !== undefined && revenueCurrYearActual !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-teal-600"></span>
              <span className="text-gray-600">{isMtd ? `${currentYear} (días 1-${mtdDay}):` : `${currentYear} Real:`}</span>
            </span>
            <span className="font-semibold text-teal-700">
              ${revenueCurrYearActual.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {/* Estimated full current year month for MTD months - only show with projections */}
        {showProjections && revenueCurrYearEstimated !== undefined && revenueCurrYearEstimated !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: '#14B8A6', border: '2px dashed #14B8A6' }}></span>
              <span className="text-gray-500 text-xs">{currentYear} Estimado mes:</span>
            </span>
            <span className="font-medium text-sm" style={{ color: '#14B8A6' }}>
              ${revenueCurrYearEstimated.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {/* Current year projected (remaining months) - hide if MTD month since it's redundant with estimated */}
        {revenueCurrYearProjected !== undefined && revenueCurrYearProjected !== null && !isMtd && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: '#14B8A6', border: '2px dashed #14B8A6' }}></span>
              <span className="text-gray-600">{currentYear} Proyección:</span>
            </span>
            <span className="font-semibold" style={{ color: '#14B8A6' }}>
              ${revenueCurrYearProjected.toLocaleString('es-CL')}
            </span>
          </div>
        )}

        {revenueNextYearProjected !== undefined && revenueNextYearProjected !== null && (
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-violet-500"></span>
              <span className="text-gray-600">{nextYear} Proyección:</span>
            </span>
            <span className="font-semibold text-violet-600">
              ${revenueNextYearProjected.toLocaleString('es-CL')}
            </span>
          </div>
        )}
      </div>

      {/* Gap between previous and current year */}
      {revenuePrevYear && revenueCurrYearActual && (
        <div className="pt-3 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <span className="text-gray-600 font-medium text-sm">{previousYear} vs {currentYear}:</span>
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

// Local storage key for series visibility
const SERIES_STORAGE_KEY = 'executiveChart_seriesVisibility'

export default function ExecutiveSalesChart({
  sales_previous_year,
  sales_current_year,
  sales_current_year_projected,
  sales_next_year_projected,
  previous_year,
  current_year,
  next_year,
  mtdComparisonInfo,
}: ExecutiveSalesChartProps) {
  // Series configuration with dynamic labels - improved colors
  const seriesConfigs: SeriesConfig[] = [
    { key: 'currentYear', label: `${current_year} Real`, color: '#0D9488', defaultEnabled: true },
    { key: 'previousYear', label: `${previous_year} Real`, color: '#6366F1', defaultEnabled: true },
    { key: 'projectedCurrentYear', label: `${current_year} Proy.`, color: '#14B8A6', defaultEnabled: true },
    { key: 'projectedNextYear', label: `${next_year} Proy.`, color: '#8B5CF6', defaultEnabled: false },
  ]

  // Initialize visibility state from localStorage or defaults
  const [visibleSeries, setVisibleSeries] = useState<Record<SeriesKey, boolean>>(() => {
    const defaults: Record<SeriesKey, boolean> = {
      previousYear: true,
      currentYear: true,
      projectedCurrentYear: true,
      projectedNextYear: false,
    }
    if (typeof window === 'undefined') return defaults
    try {
      const stored = localStorage.getItem(SERIES_STORAGE_KEY)
      if (stored) {
        return { ...defaults, ...JSON.parse(stored) }
      }
    } catch {
      // Ignore localStorage errors
    }
    return defaults
  })

  // Persist visibility changes to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(SERIES_STORAGE_KEY, JSON.stringify(visibleSeries))
    } catch {
      // Ignore localStorage errors
    }
  }, [visibleSeries])

  // Toggle series visibility
  const toggleSeries = (key: SeriesKey) => {
    setVisibleSeries(prev => ({ ...prev, [key]: !prev[key] }))
  }

  // Combine all data for the chart with dynamic year labels
  // For previous year: always show FULL month value in line, store MTD-adjusted for tooltip context
  const chartData = sales_previous_year.map(m => ({
    month: m.month_name,
    monthNum: m.month,
    // Use full month value for main line (fallback to total_revenue for non-MTD months)
    revenue_previous_year: m.is_mtd && m.total_revenue_full_month ? m.total_revenue_full_month : m.total_revenue,
    // Store MTD-adjusted value for tooltip comparison (only meaningful for MTD months)
    revenue_previous_year_mtd: m.is_mtd ? m.total_revenue : null,
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
      {/* Header - Title left, MTD badge right */}
      <div className="flex items-start justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900">
          Comparacion de Ventas y Proyecciones
        </h2>
        {mtdComparisonInfo && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg">
            <svg className="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-xs text-amber-700 font-medium">{mtdComparisonInfo}</span>
          </div>
        )}
      </div>

      {/* Year Selector - Elegant toggle buttons */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 font-medium">Mostrar series:</span>
          {seriesConfigs.map((config) => (
            <button
              key={config.key}
              onClick={() => toggleSeries(config.key)}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium
                transition-all duration-200 ease-out
                ${visibleSeries[config.key]
                  ? 'bg-white shadow-[0_2px_4px_rgba(0,0,0,0.12)]'
                  : 'bg-gray-50 text-gray-400 hover:bg-gray-100'
                }
              `}
            >
              <span
                className={`w-2.5 h-2.5 rounded-full transition-all duration-200`}
                style={{ backgroundColor: visibleSeries[config.key] ? config.color : '#D1D5DB' }}
              />
              <span
                className="transition-colors duration-200"
                style={{ color: visibleSeries[config.key] ? config.color : undefined }}
              >
                {config.label}
              </span>
            </button>
          ))}
        </div>
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
          <Tooltip content={<CustomTooltip previousYear={previous_year} currentYear={current_year} nextYear={next_year} showProjections={visibleSeries.projectedCurrentYear} />} />

          {/* Confidence interval area for next year projections - only show when next year projection is visible */}
          {visibleSeries.projectedNextYear && (
            <>
              <Area
                type="monotone"
                dataKey="confidence_upper_next"
                stroke="none"
                fill="#8B5CF6"
                fillOpacity={0.1}
                name={`Rango de confianza ${next_year}`}
                legendType="none"
                dot={false}
                activeDot={false}
              />
              <Area
                type="monotone"
                dataKey="confidence_lower_next"
                stroke="none"
                fill="white"
                fillOpacity={1}
                legendType="none"
                dot={false}
                activeDot={false}
              />
            </>
          )}

          {/* Previous year actual line - INDIGO solid */}
          {visibleSeries.previousYear && (
            <Line
              type="monotone"
              dataKey="revenue_previous_year"
              stroke="#6366F1"
              strokeWidth={2}
              name={`${previous_year} (Real)`}
              dot={{ r: 4, fill: '#6366F1', strokeWidth: 1, stroke: '#4F46E5' }}
              activeDot={{ r: 7, fill: '#4F46E5' }}
            />
          )}

          {/* Current year actual line - TEAL solid */}
          {visibleSeries.currentYear && (
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
          )}

          {/* Current year projected line - TEAL dashed (remaining months) */}
          {visibleSeries.projectedCurrentYear && (
            <Line
              type="monotone"
              dataKey="revenue_current_year_projected"
              stroke="#14B8A6"
              strokeWidth={2}
              strokeDasharray="6 3"
              name={`${current_year} (Proyección)`}
              dot={{ r: 4, fill: '#14B8A6', strokeWidth: 1, stroke: '#0D9488' }}
              activeDot={{ r: 6, fill: '#14B8A6' }}
            />
          )}

          {/* Next year projected line - VIOLET dashed */}
          {visibleSeries.projectedNextYear && (
            <Line
              type="monotone"
              dataKey="revenue_next_year_projected"
              stroke="#8B5CF6"
              strokeWidth={3}
              strokeDasharray="8 4"
              name={`${next_year} (Proyección)`}
              dot={{ r: 5, fill: '#8B5CF6', strokeWidth: 2, stroke: '#7C3AED' }}
              activeDot={{ r: 8, fill: '#7C3AED' }}
              label={<CustomLabel color="#8B5CF6" />}
            />
          )}


          {/* Striped teal line for estimated current year full month (incomplete months only) */}
          {visibleSeries.projectedCurrentYear && (
            <Line
              type="monotone"
              dataKey="revenue_current_year_estimated"
              stroke="#14B8A6"
              strokeWidth={2}
              strokeDasharray="5 5"
              name={`${current_year} Estimado`}
              dot={(props: any) => {
                // Only show dot at MTD month
                if (!props.payload?.is_mtd) return null
                return <circle key={`dot-curr-est-${props.index}`} cx={props.cx} cy={props.cy} r={5} fill="#14B8A6" stroke="#0D9488" strokeWidth={2} />
              }}
              connectNulls={false}
              legendType="none"
              label={(props: any) => {
                // Only show label at MTD month
                if (!props.payload?.is_mtd) return null
                return <CustomLabel key={`label-curr-est-${props.index}`} {...props} color="#14B8A6" />
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend - show when any series is visible */}
      {(visibleSeries.previousYear || visibleSeries.currentYear || visibleSeries.projectedNextYear) && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-gray-600">
            {visibleSeries.previousYear && (
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-0.5 bg-indigo-500"></div>
                <div className="w-2 h-2 rounded-full bg-indigo-500 -ml-1"></div>
                <span>{previous_year} real</span>
              </div>
            )}
            {visibleSeries.currentYear && (
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-0.5 bg-teal-600"></div>
                <div className="w-2 h-2 rounded-full bg-teal-600 -ml-1"></div>
                <span>{current_year} real</span>
              </div>
            )}
            {visibleSeries.projectedCurrentYear && chartData.some(d => d.is_mtd) && (
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-0.5" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #14B8A6 0px, #14B8A6 2px, transparent 2px, transparent 4px)' }}></div>
                <div className="w-2 h-2 rounded-full -ml-1" style={{ backgroundColor: '#14B8A6' }}></div>
                <span>{current_year} estimado</span>
              </div>
            )}
            {visibleSeries.projectedNextYear && (
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-0.5" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #8B5CF6 0px, #8B5CF6 2px, transparent 2px, transparent 4px)' }}></div>
                <div className="w-2 h-2 rounded-full bg-violet-500 -ml-1"></div>
                <span>{next_year} proy.</span>
              </div>
            )}
            {visibleSeries.projectedNextYear && (
              <div className="flex items-center gap-1.5">
                <div className="w-5 h-2.5 bg-violet-100 rounded border border-violet-200"></div>
                <span>Intervalo de Confianza</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Gap between previous and current year - only show when both series are visible */}
      {visibleSeries.previousYear && visibleSeries.currentYear && (
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
      )}

      {/* Gap between current and next year projections - only show when both are visible */}
      {visibleSeries.currentYear && visibleSeries.projectedNextYear && (
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
      )}
    </div>
  )
}
