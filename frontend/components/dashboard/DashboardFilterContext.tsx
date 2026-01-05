'use client'

import { createContext, useContext, useState, useCallback, useMemo, ReactNode } from 'react'

// Period type options
export type PeriodType = 'ytd' | 'current_month' | 'last_month' | 'current_quarter' | 'last_quarter' | 'last_12' | 'custom'

// Time period (granularity) options for charts
export type TimePeriod = 'auto' | 'day' | 'week' | 'month'

// Filter state interface
export interface DashboardFilters {
  periodType: PeriodType
  customFromDate: string | null
  customToDate: string | null
  family: string | null // BARRAS, CRACKERS, GRANOLAS, KEEPERS, or null for ALL
  channel: string | null // Channel name or null for ALL
  timePeriod: TimePeriod // Granularity for charts: day, week, month, or auto
}

// Computed date range (for API calls)
export interface DateRange {
  from: string
  to: string
}

// Context value interface
interface DashboardContextValue {
  filters: DashboardFilters
  dateRange: DateRange
  setFilters: (updates: Partial<DashboardFilters>) => void
  resetFilters: () => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
}

// Default filters
const defaultFilters: DashboardFilters = {
  periodType: 'ytd',
  customFromDate: null,
  customToDate: null,
  family: null,
  channel: null,
  timePeriod: 'auto',
}

// Create context
const DashboardFilterContext = createContext<DashboardContextValue | null>(null)

// Date range calculation helper
function computeDateRange(filters: DashboardFilters): DateRange {
  const today = new Date()
  const currentYear = today.getFullYear()
  const currentMonth = today.getMonth() + 1
  const currentQuarter = Math.ceil(currentMonth / 3)
  const todayStr = today.toISOString().split('T')[0]

  switch (filters.periodType) {
    case 'ytd':
      return {
        from: `${currentYear}-01-01`,
        to: todayStr,
      }

    case 'current_month':
      return {
        from: `${currentYear}-${currentMonth.toString().padStart(2, '0')}-01`,
        to: todayStr,
      }

    case 'last_month': {
      const lastMonth = currentMonth === 1 ? 12 : currentMonth - 1
      const year = currentMonth === 1 ? currentYear - 1 : currentYear
      const lastDay = new Date(year, lastMonth, 0).getDate()
      return {
        from: `${year}-${lastMonth.toString().padStart(2, '0')}-01`,
        to: `${year}-${lastMonth.toString().padStart(2, '0')}-${lastDay}`,
      }
    }

    case 'current_quarter': {
      const startMonth = (currentQuarter - 1) * 3 + 1
      return {
        from: `${currentYear}-${startMonth.toString().padStart(2, '0')}-01`,
        to: todayStr,
      }
    }

    case 'last_quarter': {
      const lastQ = currentQuarter === 1 ? 4 : currentQuarter - 1
      const year = currentQuarter === 1 ? currentYear - 1 : currentYear
      const startMonth = (lastQ - 1) * 3 + 1
      const endMonth = lastQ * 3
      const lastDay = new Date(year, endMonth, 0).getDate()
      return {
        from: `${year}-${startMonth.toString().padStart(2, '0')}-01`,
        to: `${year}-${endMonth.toString().padStart(2, '0')}-${lastDay}`,
      }
    }

    case 'last_12': {
      const past = new Date(today)
      past.setFullYear(past.getFullYear() - 1)
      return {
        from: past.toISOString().split('T')[0],
        to: todayStr,
      }
    }

    case 'custom':
      return {
        from: filters.customFromDate || `${currentYear}-01-01`,
        to: filters.customToDate || todayStr,
      }

    default:
      return {
        from: `${currentYear}-01-01`,
        to: todayStr,
      }
  }
}

// Period labels for display
export const PERIOD_LABELS: Record<PeriodType, string> = {
  ytd: 'YTD',
  current_month: 'Mes Actual',
  last_month: 'Mes Anterior',
  current_quarter: 'Trimestre Actual',
  last_quarter: 'Trimestre Anterior',
  last_12: 'Ultimos 12 meses',
  custom: 'Personalizado',
}

// Time period (granularity) labels for display
export const TIME_PERIOD_LABELS: Record<TimePeriod, string> = {
  auto: 'Auto',
  day: 'Diario',
  week: 'Semanal',
  month: 'Mensual',
}

// Family options
export const FAMILY_OPTIONS = [
  { label: 'Todas', value: null },
  { label: 'Barras', value: 'BARRAS' },
  { label: 'Crackers', value: 'CRACKERS' },
  { label: 'Granolas', value: 'GRANOLAS' },
  { label: 'Keepers', value: 'KEEPERS' },
]

// Provider component
interface DashboardFilterProviderProps {
  children: ReactNode
}

export function DashboardFilterProvider({ children }: DashboardFilterProviderProps) {
  const [filters, setFiltersState] = useState<DashboardFilters>(defaultFilters)
  const [isLoading, setIsLoading] = useState(false)

  // Compute date range from filters
  const dateRange = useMemo(() => computeDateRange(filters), [filters])

  // Update filters (partial update)
  const setFilters = useCallback((updates: Partial<DashboardFilters>) => {
    setFiltersState(prev => ({ ...prev, ...updates }))
  }, [])

  // Reset to defaults
  const resetFilters = useCallback(() => {
    setFiltersState(defaultFilters)
  }, [])

  const contextValue = useMemo<DashboardContextValue>(() => ({
    filters,
    dateRange,
    setFilters,
    resetFilters,
    isLoading,
    setIsLoading,
  }), [filters, dateRange, setFilters, resetFilters, isLoading])

  return (
    <DashboardFilterContext.Provider value={contextValue}>
      {children}
    </DashboardFilterContext.Provider>
  )
}

// Hook to use the filter context
export function useDashboardFilters() {
  const context = useContext(DashboardFilterContext)
  if (!context) {
    throw new Error('useDashboardFilters must be used within a DashboardFilterProvider')
  }
  return context
}

// Export the context for advanced use cases
export { DashboardFilterContext }
