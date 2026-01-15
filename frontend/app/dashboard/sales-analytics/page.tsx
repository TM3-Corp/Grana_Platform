'use client'

import { useState, useEffect } from 'react'
import Navigation from '@/components/Navigation'
import KPICards from '@/components/sales-analytics/KPICards'
import TimelineChart from '@/components/sales-analytics/TimelineChart'
import TopItemsChart from '@/components/sales-analytics/TopItemsChart'
import GroupedDataTable from '@/components/sales-analytics/GroupedDataTable'
import FiltersSidebar from '@/components/sales-analytics/FiltersSidebar'

interface SalesAnalyticsData {
  summary: {
    total_revenue: number
    total_units: number
    total_orders: number
    avg_ticket: number
    growth_rate: number
  }
  timeline: Array<{
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
  }>
  top_items: Array<{
    group_value: string
    revenue: number
    units: number
    orders: number
    percentage: number
  }>
  grouped_data: Array<{
    group_value: string
    revenue: number
    units: number
    orders: number
    avg_ticket: number
  }>
  pagination: {
    current_page: number
    total_pages: number
    total_items: number
    page_size: number
  }
  filters: {
    from_date: string | null
    to_date: string | null
    sources: string[]
    channels: string[] | null
    customers: string[] | null
    categories: string[] | null
    formats: string[] | null
    group_by: string | null
    top_limit: number
  }
}

export default function SalesAnalyticsPage() {
  const [data, setData] = useState<SalesAnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filter states
  const [dateFilterType, setDateFilterType] = useState<'all' | 'year' | 'month' | 'custom'>('all')
  const [selectedYears, setSelectedYears] = useState<string[]>([])
  const [selectedMonths, setSelectedMonths] = useState<string[]>([])
  const [customFromDate, setCustomFromDate] = useState<string>('')
  const [customToDate, setCustomToDate] = useState<string>('')

  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [selectedChannels, setSelectedChannels] = useState<string[]>([])
  const [selectedCustomers, setSelectedCustomers] = useState<string[]>([])
  const [selectedFormats, setSelectedFormats] = useState<string[]>([])
  const [selectedSkuPrimarios, setSelectedSkuPrimarios] = useState<string[]>([])

  // Search state
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [debouncedSearch, setDebouncedSearch] = useState<string>('')

  const [timePeriod, setTimePeriod] = useState<'auto' | 'day' | 'week' | 'month' | 'quarter' | 'year'>('auto')
  const [groupBy, setGroupBy] = useState<string>('')
  const [stackBy, setStackBy] = useState<string | null>(null)
  const [topLimit, setTopLimit] = useState<number>(10)
  const [currentPage, setCurrentPage] = useState<number>(1)

  // Available options (fetched from API or data)
  const [availableChannels, setAvailableChannels] = useState<string[]>([])
  const [availableCustomers, setAvailableCustomers] = useState<string[]>([])
  const [availableFormats, setAvailableFormats] = useState<string[]>([])
  const [availableSkuPrimarios, setAvailableSkuPrimarios] = useState<string[]>([])

  // Helper function to format the current date range display
  const getDateRangeDisplay = (): string => {
    const currentYear = new Date().getFullYear()

    if (dateFilterType === 'all') {
      return `Año actual: ${currentYear}`
    } else if (dateFilterType === 'year' && selectedYears.length > 0) {
      return `Años: ${selectedYears.sort().join(', ')}`
    } else if (dateFilterType === 'month' && selectedMonths.length > 0) {
      // Parse months (format: "2025-01") and display as "Enero 2025, Febrero 2025"
      const monthNames: { [key: string]: string } = {
        '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
        '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
        '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
      }
      const formatted = selectedMonths.sort().map(m => {
        const [year, month] = m.split('-')
        return `${monthNames[month] || month} ${year}`
      })
      return `Meses: ${formatted.join(', ')}`
    } else if (dateFilterType === 'custom' && customFromDate && customToDate) {
      const from = new Date(customFromDate + 'T00:00:00')
      const to = new Date(customToDate + 'T00:00:00')
      const formatDate = (d: Date) => d.toLocaleDateString('es-CL')
      return `Período: ${formatDate(from)} - ${formatDate(to)}`
    }
    return `Año actual: ${currentYear}`
  }

  // Debounce search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm)
      setCurrentPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchTerm])

  // Fetch data
  useEffect(() => {
    fetchSalesAnalytics()
  }, [
    dateFilterType,
    selectedYears,
    selectedMonths,
    customFromDate,
    customToDate,
    timePeriod,
    selectedCategories,
    selectedChannels,
    selectedCustomers,
    selectedFormats,
    selectedSkuPrimarios,
    groupBy,
    stackBy,
    topLimit,
    currentPage,
    debouncedSearch
  ])

  // Fetch available filter options on mount
  useEffect(() => {
    fetchFilterOptions()
  }, [])

  // Fetch Formato options when Familia (category) selection changes
  useEffect(() => {
    fetchFormatoOptions()
  }, [selectedCategories])

  const fetchFilterOptions = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app'

      // Fetch filter options from audit/filters endpoint
      // This returns channels, customers, and SKUs with 2025 data
      const filtersRes = await fetch(`${apiUrl}/api/v1/audit/filters`)
      if (filtersRes.ok) {
        const filtersData = await filtersRes.json()
        if (filtersData.data) {
          // Set channels (already filtered in backend)
          if (filtersData.data.channels) {
            setAvailableChannels(filtersData.data.channels)
          }

          // Set customers (top 100 by order count)
          if (filtersData.data.customers) {
            setAvailableCustomers(filtersData.data.customers)
          }
        }
      }
    } catch (err) {
      console.error('Error fetching filter options:', err)
    }
  }

  // Fetch Formato and SKU Primario options dynamically based on selected categories
  const fetchFormatoOptions = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app'

      // Build query parameters for categories
      const params = new URLSearchParams()
      selectedCategories.forEach(cat => params.append('categories', cat))

      const response = await fetch(`${apiUrl}/api/v1/sales-analytics/filter-options?${params}`)
      if (response.ok) {
        const result = await response.json()
        if (result.status === 'success' && result.data) {
          // Set Formato options
          if (result.data.formats) {
            setAvailableFormats(result.data.formats)

            // Clear selected formats that are no longer available
            if (selectedCategories.length > 0) {
              setSelectedFormats(prev =>
                prev.filter(fmt => result.data.formats.includes(fmt))
              )
            }
          }

          // Set SKU Primario options
          if (result.data.sku_primarios) {
            setAvailableSkuPrimarios(result.data.sku_primarios)

            // Clear selected SKU Primarios that are no longer available
            if (selectedCategories.length > 0) {
              setSelectedSkuPrimarios(prev =>
                prev.filter(sku => result.data.sku_primarios.includes(sku))
              )
            }
          }
        }
      }
    } catch (err) {
      console.error('Error fetching formato options:', err)
    }
  }

  const fetchSalesAnalytics = async () => {
    setLoading(true)
    setError(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app'

      // Build query parameters
      const params = new URLSearchParams()

      // Date filters
      if (dateFilterType === 'year' && selectedYears.length > 0) {
        const years = selectedYears.map(y => parseInt(y)).sort()
        params.append('from_date', `${years[0]}-01-01`)
        params.append('to_date', `${years[years.length - 1]}-12-31`)
      } else if (dateFilterType === 'month' && selectedMonths.length > 0) {
        // Default to current year if no year selected
        const yearsToUse = selectedYears.length > 0
          ? selectedYears
          : [new Date().getFullYear().toString()]

        // Build date range from selected years and months
        const yearMonths = yearsToUse.flatMap(year =>
          selectedMonths.map(month => ({ year: parseInt(year), month: parseInt(month) }))
        ).sort((a, b) => {
          if (a.year !== b.year) return a.year - b.year
          return a.month - b.month
        })

        const first = yearMonths[0]
        const last = yearMonths[yearMonths.length - 1]
        const lastDay = new Date(last.year, last.month, 0).getDate()

        params.append('from_date', `${first.year}-${first.month.toString().padStart(2, '0')}-01`)
        params.append('to_date', `${last.year}-${last.month.toString().padStart(2, '0')}-${lastDay}`)
      } else if (dateFilterType === 'custom' && customFromDate && customToDate) {
        params.append('from_date', customFromDate)
        params.append('to_date', customToDate)
      }

      // Sources (default to relbase only)
      params.append('sources', 'relbase')

      // Multi-select filters
      selectedCategories.forEach(cat => params.append('categories', cat))
      selectedChannels.forEach(ch => params.append('channels', ch))
      selectedCustomers.forEach(cust => params.append('customers', cust))
      selectedFormats.forEach(fmt => params.append('formats', fmt))
      selectedSkuPrimarios.forEach(sku => params.append('sku_primarios', sku))

      // Search filter
      if (debouncedSearch) {
        params.append('search', debouncedSearch)
      }

      // Time period
      params.append('time_period', timePeriod)

      // Grouping and top limit
      if (groupBy) {
        params.append('group_by', groupBy)
      }
      if (stackBy) {
        params.append('stack_by', stackBy)
      }
      params.append('top_limit', topLimit.toString())

      // Pagination
      params.append('page', currentPage.toString())
      params.append('page_size', '50')

      const fullUrl = `${apiUrl}/api/v1/sales-analytics?${params.toString()}`

      const response = await fetch(fullUrl)

      if (!response.ok) {
        throw new Error(`Error fetching sales analytics (${response.status})`)
      }

      const result = await response.json()

      if (result.status === 'success' && result.data) {
        setData(result.data)
      } else {
        throw new Error('Invalid response format')
      }

    } catch (err) {
      console.error('Error:', err)
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  const handleClearFilters = () => {
    setDateFilterType('all')
    setSelectedYears([])
    setSelectedMonths([])
    setCustomFromDate('')
    setCustomToDate('')
    setSelectedCategories([])
    setSelectedChannels([])
    setSelectedCustomers([])
    setSelectedFormats([])
    setSelectedSkuPrimarios([])
    setSearchTerm('')
    setGroupBy('')
    setStackBy(null)
    setTopLimit(10)
    setCurrentPage(1)
  }

  const handleExportCSV = async () => {
    if (!data) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app'

      // Build query parameters (same as fetchSalesAnalytics)
      const params = new URLSearchParams()

      // Date filters
      if (dateFilterType === 'year' && selectedYears.length > 0) {
        const years = selectedYears.map(y => parseInt(y)).sort()
        params.append('from_date', `${years[0]}-01-01`)
        params.append('to_date', `${years[years.length - 1]}-12-31`)
      } else if (dateFilterType === 'month' && selectedMonths.length > 0) {
        const yearsToUse = selectedYears.length > 0
          ? selectedYears
          : [new Date().getFullYear().toString()]

        const yearMonths = yearsToUse.flatMap(year =>
          selectedMonths.map(month => ({ year: parseInt(year), month: parseInt(month) }))
        ).sort((a, b) => {
          if (a.year !== b.year) return a.year - b.year
          return a.month - b.month
        })

        const first = yearMonths[0]
        const last = yearMonths[yearMonths.length - 1]
        const lastDay = new Date(last.year, last.month, 0).getDate()

        params.append('from_date', `${first.year}-${first.month.toString().padStart(2, '0')}-01`)
        params.append('to_date', `${last.year}-${last.month.toString().padStart(2, '0')}-${lastDay}`)
      } else if (dateFilterType === 'custom' && customFromDate && customToDate) {
        params.append('from_date', customFromDate)
        params.append('to_date', customToDate)
      }

      // Multi-select filters
      selectedCategories.forEach(cat => params.append('categories', cat))
      selectedChannels.forEach(ch => params.append('channels', ch))
      selectedCustomers.forEach(cust => params.append('customers', cust))
      selectedFormats.forEach(fmt => params.append('formats', fmt))
      selectedSkuPrimarios.forEach(sku => params.append('sku_primarios', sku))

      // Grouping
      if (groupBy) {
        params.append('group_by', groupBy)
      }

      // Fetch Excel file from backend
      const response = await fetch(`${apiUrl}/api/v1/sales-analytics/export?${params.toString()}`)

      if (!response.ok) {
        throw new Error(`Export failed (${response.status})`)
      }

      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition')
      const filenameMatch = contentDisposition?.match(/filename=(.+)/)
      const filename = filenameMatch ? filenameMatch[1] : `ventas_${groupBy || 'categoria'}_${new Date().toISOString().split('T')[0]}.xlsx`

      // Download the file
      const blob = await response.blob()
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

    } catch (err) {
      console.error('Export error:', err)
      alert('Error al exportar. Por favor intenta nuevamente.')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <Navigation />

      {/* Filters Sidebar */}
      <FiltersSidebar
        dateFilterType={dateFilterType}
        onDateFilterTypeChange={setDateFilterType}
        selectedYears={selectedYears}
        onYearsChange={setSelectedYears}
        selectedMonths={selectedMonths}
        onMonthsChange={setSelectedMonths}
        customFromDate={customFromDate}
        onCustomFromDateChange={setCustomFromDate}
        customToDate={customToDate}
        onCustomToDateChange={setCustomToDate}
        selectedCategories={selectedCategories}
        onCategoriesChange={setSelectedCategories}
        selectedChannels={selectedChannels}
        onChannelsChange={setSelectedChannels}
        selectedCustomers={selectedCustomers}
        onCustomersChange={setSelectedCustomers}
        selectedFormats={selectedFormats}
        onFormatsChange={setSelectedFormats}
        selectedSkuPrimarios={selectedSkuPrimarios}
        onSkuPrimariosChange={setSelectedSkuPrimarios}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        groupBy={groupBy}
        onGroupByChange={setGroupBy}
        stackBy={stackBy}
        onStackByChange={setStackBy}
        topLimit={topLimit}
        onTopLimitChange={setTopLimit}
        availableChannels={availableChannels}
        availableCustomers={availableCustomers}
        availableFormats={availableFormats}
        availableSkuPrimarios={availableSkuPrimarios}
        onClearFilters={handleClearFilters}
      />

      {/* Main Content (offset for sidebar) */}
      <div className="ml-80 p-8">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            📊 Análisis Dinámico de Ventas
          </h1>
          <p className="text-gray-600 text-lg">
            Visualiza patrones de ventas con filtros y agrupaciones dinámicas
          </p>
          {/* Date Range Display */}
          <div className="mt-4 flex items-center gap-2 text-sm text-gray-600 bg-blue-50 px-4 py-2 rounded-lg border border-blue-100 w-fit">
            <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span className="font-medium">{getDateRangeDisplay()}</span>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-10">
            <p className="text-red-800">Error: {error}</p>
          </div>
        )}

        {/* KPI Cards */}
        <KPICards data={data?.summary || null} loading={loading} />

        {/* Timeline Chart */}
        <TimelineChart
          data={data?.timeline || null}
          groupBy={groupBy}
          stackBy={stackBy}
          timePeriod={timePeriod}
          onTimePeriodChange={setTimePeriod}
          loading={loading}
        />

        {/* Top Items Chart */}
        <TopItemsChart
          data={data?.top_items || null}
          groupBy={groupBy}
          topLimit={topLimit}
          loading={loading}
        />

        {/* Grouped Data Table */}
        <GroupedDataTable
          data={data?.grouped_data || null}
          groupBy={groupBy}
          pagination={data?.pagination || null}
          onPageChange={setCurrentPage}
          onExportCSV={handleExportCSV}
          loading={loading}
        />
      </div>
    </div>
  )
}
