'use client'

import { useMemo } from 'react'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, ComposedChart, Line } from 'recharts'
import { TrendingUp, Calendar, Target, Trophy } from 'lucide-react'

interface DailyData {
  day_of_year: number
  date_previous_year: string | null
  date_current_year: string | null
  cumulative_previous_year: number
  cumulative_current_year: number
  daily_previous_year: number
  daily_current_year: number
  ytd_difference: number
  ytd_difference_percent: number
}

interface YTDSummary {
  ytd_previous_year: number
  ytd_current_year: number
  ytd_difference: number
  ytd_difference_percent: number
  monthly_goal: number
  distance_to_goal: number
  goal_exceeded: boolean
}

interface YTDProgressChartProps {
  dailyData: DailyData[]
  summary: YTDSummary
  previousYear: number
  currentYear: number
  currentMonth: number
  currentDayOfYear: number
  currentDate: string
  loading?: boolean
}

// Custom tooltip
const CustomTooltip = ({ active, payload, previousYear, currentYear }: any) => {
  if (!active || !payload || payload.length === 0) return null

  const data = payload[0]?.payload
  if (!data) return null

  const formatCurrency = (value: number) => `$${Math.round(value).toLocaleString('es-CL')}`
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('es-CL', { day: 'numeric', month: 'short' })
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-4 min-w-[280px]">
      <p className="font-bold text-gray-900 mb-3 border-b pb-2">
        Día {data.day_of_year} del año
      </p>

      <div className="space-y-3">
        {/* Previous year */}
        <div>
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-indigo-500"></span>
              <span className="text-gray-600">{previousYear} YTD:</span>
            </span>
            <span className="font-semibold text-indigo-600">
              {formatCurrency(data.cumulative_previous_year)}
            </span>
          </div>
          <div className="text-xs text-gray-400 ml-5">
            {formatDate(data.date_previous_year)} • +{formatCurrency(data.daily_previous_year)} ese día
          </div>
        </div>

        {/* Current year */}
        <div>
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-teal-600"></span>
              <span className="text-gray-600">{currentYear} YTD:</span>
            </span>
            <span className="font-semibold text-teal-700">
              {formatCurrency(data.cumulative_current_year)}
            </span>
          </div>
          <div className="text-xs text-gray-400 ml-5">
            {formatDate(data.date_current_year)} • +{formatCurrency(data.daily_current_year)} ese día
          </div>
        </div>
      </div>

      {/* Difference */}
      <div className="mt-3 pt-3 border-t border-gray-200">
        <div className="flex justify-between items-center">
          <span className="text-gray-600 font-medium text-sm">Diferencia YTD:</span>
          <div className="text-right">
            <span className={`font-bold ${data.ytd_difference >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {data.ytd_difference >= 0 ? '+' : ''}{data.ytd_difference_percent}%
            </span>
            <p className={`text-xs ${data.ytd_difference >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {data.ytd_difference >= 0 ? '+' : ''}{formatCurrency(data.ytd_difference)}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function YTDProgressChart({
  dailyData,
  summary,
  previousYear,
  currentYear,
  currentMonth,
  currentDayOfYear,
  currentDate,
  loading
}: YTDProgressChartProps) {
  // Get month name in Spanish
  const monthNames = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
  const currentMonthName = monthNames[currentMonth - 1] || ''
  // Sample data for better performance (every 7 days for weekly view)
  const chartData = useMemo(() => {
    if (!dailyData || dailyData.length === 0) return []

    // Show every day if less than 60 days, otherwise sample weekly
    if (dailyData.length <= 60) {
      return dailyData
    }

    // Sample every 7 days + always include the last day
    const sampled = dailyData.filter((d, i) => i % 7 === 0 || i === dailyData.length - 1)
    return sampled
  }, [dailyData])

  // Abbreviated format for chart axis
  const formatCurrencyShort = (value: number): string => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`
    }
    return `$${Math.round(value / 1000)}K`
  }

  // Full number format for summary cards
  const formatCurrencyFull = (value: number): string => {
    return `$${Math.round(value).toLocaleString('es-CL')}`
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="h-80 bg-gray-100 animate-pulse rounded-lg" />
      </div>
    )
  }

  if (!dailyData || dailyData.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Progreso YTD</h2>
        <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
          No hay datos disponibles
        </div>
      </div>
    )
  }

  const isPositive = summary.ytd_difference >= 0

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 border-l-4 border-l-emerald-500 p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-emerald-600" strokeWidth={2} />
            </div>
            Progreso YTD Acumulado
          </h2>
          <p className="text-sm text-gray-500 mt-1 ml-10">
            Comparación día a día: {previousYear} vs {currentYear}
          </p>
        </div>

        {/* Summary badge */}
        <div className={`flex items-center gap-2 px-4 py-2 rounded-xl ${
          isPositive ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          <Calendar className={`w-4 h-4 ${isPositive ? 'text-green-500' : 'text-red-500'}`} strokeWidth={1.75} />
          <div className="text-right">
            <div className={`text-lg font-bold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? '+' : ''}{summary.ytd_difference_percent}%
            </div>
            <div className="text-xs text-gray-500">
              Día {currentDayOfYear}
            </div>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-indigo-50 rounded-xl p-4 border border-indigo-100">
          <div className="text-xs text-indigo-600 font-medium mb-1">{previousYear} YTD</div>
          <div className="text-lg font-bold text-indigo-700">{formatCurrencyFull(summary.ytd_previous_year)}</div>
        </div>
        <div className="bg-teal-50 rounded-xl p-4 border border-teal-100">
          <div className="text-xs text-teal-600 font-medium mb-1">{currentYear} YTD</div>
          <div className="text-lg font-bold text-teal-700">{formatCurrencyFull(summary.ytd_current_year)}</div>
        </div>
        <div className={`rounded-xl p-4 border ${isPositive ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
          <div className={`text-xs font-medium mb-1 ${isPositive ? 'text-green-600' : 'text-red-600'}`}>Diferencia YTD</div>
          <div className={`text-lg font-bold ${isPositive ? 'text-green-700' : 'text-red-700'}`}>
            {isPositive ? '+' : ''}{formatCurrencyFull(summary.ytd_difference)}
          </div>
        </div>
        {/* Distancia a Meta card with progress fill */}
        {(() => {
          const goalProgress = summary.monthly_goal > 0
            ? (summary.ytd_current_year / summary.monthly_goal) * 100
            : 0
          const fillPercent = Math.min(goalProgress, 100) // Cap visual fill at 100%
          const displayPercent = Math.round(goalProgress)

          return (
            <div className={`relative rounded-xl p-4 border overflow-hidden ${
              summary.goal_exceeded
                ? 'border-amber-300'
                : 'border-sky-200'
            }`}>
              {/* Progress fill background */}
              <div
                className={`absolute bottom-0 left-0 right-0 transition-all duration-700 ease-out ${
                  summary.goal_exceeded
                    ? 'bg-gradient-to-t from-amber-200 via-amber-100 to-yellow-50'
                    : 'bg-gradient-to-t from-sky-200 via-sky-100 to-sky-50'
                }`}
                style={{ height: `${fillPercent}%` }}
              />
              {/* Content (above the fill) */}
              <div className="relative z-10">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    {summary.goal_exceeded ? (
                      <Trophy className="w-3.5 h-3.5 text-amber-600" strokeWidth={2} />
                    ) : (
                      <Target className="w-3.5 h-3.5 text-sky-600" strokeWidth={2} />
                    )}
                    <span className={`text-xs font-medium ${summary.goal_exceeded ? 'text-amber-700' : 'text-sky-700'}`}>
                      {summary.goal_exceeded ? 'Meta Superada' : 'Progreso a Meta'}
                    </span>
                  </div>
                  {/* Percentage badge */}
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                    summary.goal_exceeded
                      ? 'bg-amber-500 text-white'
                      : 'bg-sky-500 text-white'
                  }`}>
                    {displayPercent}%
                  </span>
                </div>
                <div className={`text-lg font-bold ${summary.goal_exceeded ? 'text-amber-800' : 'text-sky-800'}`}>
                  {summary.goal_exceeded ? '+' : '-'}{formatCurrencyFull(summary.distance_to_goal)}
                </div>
                <div className={`text-[10px] mt-0.5 ${summary.goal_exceeded ? 'text-amber-600' : 'text-sky-600'}`}>
                  Meta: {formatCurrencyFull(summary.monthly_goal)} ({currentMonthName} {previousYear})
                </div>
              </div>
            </div>
          )
        })()}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={350}>
        <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 10 }}>
          <defs>
            <linearGradient id="gradientPrevYear" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366F1" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradientCurrYear" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0D9488" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#0D9488" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="day_of_year"
            tick={{ fontSize: 11 }}
            stroke="#6B7280"
            tickFormatter={(day) => {
              // Convert day of year to month abbreviation
              const date = new Date(currentYear, 0, day)
              return date.toLocaleDateString('es-CL', { day: 'numeric', month: 'short' })
            }}
            interval={Math.floor(chartData.length / 8)}
          />
          <YAxis
            tickFormatter={formatCurrencyShort}
            tick={{ fontSize: 11 }}
            stroke="#6B7280"
            domain={[0, 'auto']}
          />
          <Tooltip content={<CustomTooltip previousYear={previousYear} currentYear={currentYear} />} />

          {/* Previous year area */}
          <Area
            type="monotone"
            dataKey="cumulative_previous_year"
            stroke="#6366F1"
            strokeWidth={2}
            fill="url(#gradientPrevYear)"
            name={`${previousYear} YTD`}
            dot={false}
          />

          {/* Current year line (on top) */}
          <Line
            type="monotone"
            dataKey="cumulative_current_year"
            stroke="#0D9488"
            strokeWidth={3}
            name={`${currentYear} YTD`}
            dot={false}
            activeDot={{ r: 6, fill: '#0D9488', stroke: '#115E59', strokeWidth: 2 }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-gray-100">
        <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-gray-600">
          <div className="flex items-center gap-2">
            <div className="w-4 h-2 bg-indigo-500 rounded opacity-60"></div>
            <span>{previousYear} YTD acumulado</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-teal-600"></div>
            <div className="w-2 h-2 rounded-full bg-teal-600 -ml-1"></div>
            <span>{currentYear} YTD acumulado</span>
          </div>
        </div>
      </div>
    </div>
  )
}
