'use client'

import { useState } from 'react'

interface FiltersSidebarProps {
  // Date filters
  dateFilterType: 'all' | 'year' | 'month' | 'custom'
  onDateFilterTypeChange: (type: 'all' | 'year' | 'month' | 'custom') => void
  selectedYears: string[]
  onYearsChange: (years: string[]) => void
  selectedMonths: string[]
  onMonthsChange: (months: string[]) => void
  customFromDate: string
  onCustomFromDateChange: (date: string) => void
  customToDate: string
  onCustomToDateChange: (date: string) => void

  // Multi-select filters
  selectedCategories: string[]
  onCategoriesChange: (categories: string[]) => void
  selectedChannels: string[]
  onChannelsChange: (channels: string[]) => void
  selectedCustomers: string[]
  onCustomersChange: (customers: string[]) => void
  selectedFormats: string[]
  onFormatsChange: (formats: string[]) => void

  // Grouping and Top X
  groupBy: string
  onGroupByChange: (group: string) => void
  stackBy: string | null
  onStackByChange: (stack: string | null) => void
  topLimit: number
  onTopLimitChange: (limit: number) => void

  // Available options
  availableCategories?: string[]
  availableChannels?: string[]
  availableCustomers?: string[]
  availableFormats?: string[]

  // Clear filters
  onClearFilters: () => void
}

export default function FiltersSidebar(props: FiltersSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const categories = props.availableCategories || ['BARRAS', 'CRACKERS', 'GRANOLAS', 'KEEPERS', 'CAJA MASTER', 'DESPACHOS', 'ALIANZA', 'OTROS']
  const channels = props.availableChannels || []
  const customers = props.availableCustomers || []
  const formats = props.availableFormats || ['X1', 'X5', 'X16', 'Caja Master']

  const years = ['2023', '2024', '2025']
  const months = [
    { value: '1', label: 'Enero' },
    { value: '2', label: 'Febrero' },
    { value: '3', label: 'Marzo' },
    { value: '4', label: 'Abril' },
    { value: '5', label: 'Mayo' },
    { value: '6', label: 'Junio' },
    { value: '7', label: 'Julio' },
    { value: '8', label: 'Agosto' },
    { value: '9', label: 'Septiembre' },
    { value: '10', label: 'Octubre' },
    { value: '11', label: 'Noviembre' },
    { value: '12', label: 'Diciembre' },
  ]

  const groupByOptions = [
    { value: '', label: 'Sin agrupación' },
    { value: 'category', label: 'Familia' },
    { value: 'channel', label: 'Canal' },
    { value: 'customer', label: 'Cliente' },
    { value: 'format', label: 'Formato' },
    { value: 'sku_primario', label: 'SKU Primario' },
  ]

  const topLimitOptions = [5, 10, 15, 20, 25, 30]

  const toggleCategory = (category: string) => {
    if (props.selectedCategories.includes(category)) {
      props.onCategoriesChange(props.selectedCategories.filter(c => c !== category))
    } else {
      props.onCategoriesChange([...props.selectedCategories, category])
    }
  }

  const toggleYear = (year: string) => {
    if (props.selectedYears.includes(year)) {
      props.onYearsChange(props.selectedYears.filter(y => y !== year))
    } else {
      props.onYearsChange([...props.selectedYears, year])
    }
  }

  const toggleMonth = (month: string) => {
    if (props.selectedMonths.includes(month)) {
      props.onMonthsChange(props.selectedMonths.filter(m => m !== month))
    } else {
      props.onMonthsChange([...props.selectedMonths, month])
    }
  }

  const categoryIcons: Record<string, string> = {
    'BARRAS': '🍫',
    'CRACKERS': '🍘',
    'GRANOLAS': '🥣',
    'KEEPERS': '🍬',
    'CAJA MASTER': '📦',
    'DESPACHOS': '🚚',
    'ALIANZA': '🤝',
    'OTROS': '📦'
  }

  if (isCollapsed) {
    return (
      <div className="fixed left-0 top-20 z-40">
        <button
          onClick={() => setIsCollapsed(false)}
          className="bg-white shadow-lg rounded-r-lg p-3 hover:bg-gray-50 transition-colors"
          title="Mostrar filtros"
        >
          <span className="text-xl">→</span>
        </button>
      </div>
    )
  }

  return (
    <div className="fixed left-0 top-20 bottom-0 w-80 bg-white shadow-lg overflow-y-auto z-40 border-r border-gray-200">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">
            🎛️ Filtros
          </h2>
          <button
            onClick={() => setIsCollapsed(true)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            title="Ocultar filtros"
          >
            <span className="text-xl">←</span>
          </button>
        </div>

        {/* Date Filters */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span>📅</span> Filtros Temporales
          </h3>

          {/* Date filter type */}
          <div className="space-y-2 mb-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={props.dateFilterType === 'all'}
                onChange={() => props.onDateFilterTypeChange('all')}
                className="text-green-500"
              />
              <span className="text-sm text-gray-700">Todos los períodos</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={props.dateFilterType === 'year'}
                onChange={() => props.onDateFilterTypeChange('year')}
                className="text-green-500"
              />
              <span className="text-sm text-gray-700">Por año</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={props.dateFilterType === 'month'}
                onChange={() => props.onDateFilterTypeChange('month')}
                className="text-green-500"
              />
              <span className="text-sm text-gray-700">Por mes</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={props.dateFilterType === 'custom'}
                onChange={() => props.onDateFilterTypeChange('custom')}
                className="text-green-500"
              />
              <span className="text-sm text-gray-700">Rango personalizado</span>
            </label>
          </div>

          {/* Year selection */}
          {props.dateFilterType === 'year' && (
            <div className="flex flex-wrap gap-2 mb-3">
              {years.map(year => (
                <button
                  key={year}
                  onClick={() => toggleYear(year)}
                  className={`
                    px-3 py-1 rounded-lg text-sm font-medium transition-colors
                    ${props.selectedYears.includes(year)
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }
                  `}
                >
                  {year}
                </button>
              ))}
            </div>
          )}

          {/* Month selection */}
          {props.dateFilterType === 'month' && (
            <div className="grid grid-cols-3 gap-2 mb-3">
              {months.map(month => (
                <button
                  key={month.value}
                  onClick={() => toggleMonth(month.value)}
                  className={`
                    px-2 py-1 rounded text-xs font-medium transition-colors
                    ${props.selectedMonths.includes(month.value)
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }
                  `}
                >
                  {month.label}
                </button>
              ))}
            </div>
          )}

          {/* Custom date range */}
          {props.dateFilterType === 'custom' && (
            <div className="space-y-2">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Desde</label>
                <input
                  type="date"
                  value={props.customFromDate}
                  onChange={(e) => props.onCustomFromDateChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Hasta</label>
                <input
                  type="date"
                  value={props.customToDate}
                  onChange={(e) => props.onCustomToDateChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
            </div>
          )}
        </div>

        {/* Product Family (Category) */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span>🏷️</span> Familia de Producto
          </h3>
          <div className="flex flex-wrap gap-2">
            {categories.map(category => (
              <button
                key={category}
                onClick={() => toggleCategory(category)}
                className={`
                  px-3 py-2 rounded-lg text-sm font-medium transition-all
                  ${props.selectedCategories.includes(category)
                    ? 'bg-gradient-to-r from-green-500 to-green-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                <span className="mr-1">{categoryIcons[category] || '📦'}</span>
                {category}
              </button>
            ))}
          </div>
        </div>

        {/* Channels */}
        {channels.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <span>📊</span> Canal
            </h3>
            <select
              multiple
              value={props.selectedChannels}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, option => option.value)
                props.onChannelsChange(selected)
              }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm min-h-[100px]"
            >
              {channels.map(channel => (
                <option key={channel} value={channel}>
                  {channel}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Mantén Ctrl/Cmd para seleccionar varios
            </p>
          </div>
        )}

        {/* Customers */}
        {customers.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <span>👥</span> Cliente
            </h3>
            <select
              multiple
              value={props.selectedCustomers}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, option => option.value)
                props.onCustomersChange(selected)
              }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm min-h-[100px]"
            >
              {customers.map(customer => (
                <option key={customer} value={customer}>
                  {customer}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Mantén Ctrl/Cmd para seleccionar varios
            </p>
          </div>
        )}

        {/* Formats */}
        {formats.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <span>📦</span> Formato
            </h3>
            <select
              multiple
              value={props.selectedFormats}
              onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, option => option.value)
                props.onFormatsChange(selected)
              }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm min-h-[100px]"
            >
              {formats.map(format => (
                <option key={format} value={format}>
                  {format}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Mantén Ctrl/Cmd para seleccionar varios
            </p>
          </div>
        )}

        {/* Grouping */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span>🎯</span> Agrupación
          </h3>
          <select
            value={props.groupBy}
            onChange={(e) => props.onGroupByChange(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {groupByOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Stack By (always visible) */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span>📊</span> Apilar por
          </h3>
          <select
            value={props.stackBy || ''}
            onChange={(e) => props.onStackByChange(e.target.value || null)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">Sin apilación</option>
            {props.groupBy !== 'category' && <option value="category">Familia</option>}
            {props.groupBy !== 'channel' && <option value="channel">Canal</option>}
            {props.groupBy !== 'format' && <option value="format">Formato</option>}
            {props.groupBy !== 'customer' && <option value="customer">Cliente</option>}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {props.stackBy ? 'Barras apiladas por dimensión seleccionada' : 'Gráfico de líneas'}
          </p>
        </div>

        {/* Top X */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span>🔧</span> Top X
          </h3>
          <div className="flex flex-wrap gap-2">
            {topLimitOptions.map(limit => (
              <button
                key={limit}
                onClick={() => props.onTopLimitChange(limit)}
                className={`
                  px-3 py-1 rounded-lg text-sm font-medium transition-colors
                  ${props.topLimit === limit
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                {limit}
              </button>
            ))}
          </div>
        </div>

        {/* Clear Filters */}
        <button
          onClick={props.onClearFilters}
          className="w-full px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors text-sm font-medium"
        >
          Limpiar Filtros
        </button>
      </div>
    </div>
  )
}
