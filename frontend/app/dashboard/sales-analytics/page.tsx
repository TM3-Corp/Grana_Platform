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

  const [timePeriod, setTimePeriod] = useState<'auto' | 'day' | 'week' | 'month' | 'quarter' | 'year'>('auto')
  const [groupBy, setGroupBy] = useState<string>('category')
  const [stackBy, setStackBy] = useState<string | null>('channel')
  const [topLimit, setTopLimit] = useState<number>(10)
  const [currentPage, setCurrentPage] = useState<number>(1)

  // Available options (fetched from API or data)
  const [availableChannels, setAvailableChannels] = useState<string[]>([])
  const [availableCustomers, setAvailableCustomers] = useState<string[]>([])
  const [availableFormats, setAvailableFormats] = useState<string[]>([])

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
    groupBy,
    stackBy,
    topLimit,
    currentPage
  ])

  // Fetch available filter options on mount
  useEffect(() => {
    fetchFilterOptions()
  }, [])

  const fetchFilterOptions = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app'

      // Fetch channels - only Relbase channels with 2025 data
      const channelsRes = await fetch(`${apiUrl}/api/v1/channels`)
      if (channelsRes.ok) {
        const channelsData = await channelsRes.json()
        if (channelsData.data) {
          // Channels with no 2025 data (exclude from filters)
          const excludedChannels = ['EXPORTACIÓN', 'HORECA', 'MARKETPLACES']

          // Filter only Relbase channels with 2025 data
          const relbaseChannels = channelsData.data
            .filter((ch: any) =>
              ch.code?.startsWith('RB_') &&
              ch.is_active &&
              !excludedChannels.includes(ch.name)
            )
            .map((ch: any) => ch.name)
            .sort()

          // "Sin Canal Asignado" is already in the DB with code RB_SIN_CANAL
          setAvailableChannels(relbaseChannels)
        }
      }

      // Note: We would also fetch customers and formats here if we had dedicated endpoints
      // For now, they'll be populated from the audit/filters endpoint or remain empty

    } catch (err) {
      console.error('Error fetching filter options:', err)
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
      } else if (dateFilterType === 'month' && selectedYears.length > 0 && selectedMonths.length > 0) {
        // Build date range from selected years and months
        const yearMonths = selectedYears.flatMap(year =>
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

      // Time period
      params.append('time_period', timePeriod)

      // Grouping and top limit
      params.append('group_by', groupBy)
      if (stackBy && (groupBy === 'category' || groupBy === 'format')) {
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

      if (result.success && result.data) {
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
    setGroupBy('category')
    setStackBy('channel')
    setTopLimit(10)
    setCurrentPage(1)
  }

  const handleExportCSV = () => {
    if (!data || !data.grouped_data) return

    // Build CSV content
    const headers = ['Categoría', 'Ingresos', 'Unidades', 'Órdenes', 'Ticket Promedio']
    const rows = data.grouped_data.map(row => [
      row.group_value,
      row.revenue,
      row.units,
      row.orders,
      row.avg_ticket
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `sales_analytics_${new Date().toISOString().split('T')[0]}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
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
        groupBy={groupBy}
        onGroupByChange={setGroupBy}
        stackBy={stackBy}
        onStackByChange={setStackBy}
        topLimit={topLimit}
        onTopLimitChange={setTopLimit}
        availableChannels={availableChannels}
        availableCustomers={availableCustomers}
        availableFormats={availableFormats}
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
