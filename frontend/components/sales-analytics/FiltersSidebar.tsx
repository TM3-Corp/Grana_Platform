'use client'

import { useState } from 'react'
import MultiSelect from '@/components/ui/MultiSelect'

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
  selectedSkuPrimarios: string[]
  onSkuPrimariosChange: (skuPrimarios: string[]) => void

  // Grouping and Top X
  groupBy: string
  onGroupByChange: (group: string) => void
  stackBy: string | null
  onStackByChange: (stack: string | null) => void
  topLimit: number
  onTopLimitChange: (limit: number) => void

  // Search
  searchTerm: string
  onSearchChange: (term: string) => void

  // Available options
  availableCategories?: string[]
  availableChannels?: string[]
  availableCustomers?: string[]
  availableFormats?: string[]
  availableSkuPrimarios?: string[]

  // Clear filters
  onClearFilters: () => void
}

export default function FiltersSidebar(props: FiltersSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const categories = props.availableCategories || ['BARRAS', 'CRACKERS', 'GRANOLAS', 'KEEPERS']
  const channels = props.availableChannels || []
  const customers = props.availableCustomers || []
  // Formats and SKU Primarios are now dynamically loaded from the API based on selected categories
  const formats = props.availableFormats || []
  const skuPrimarios = props.availableSkuPrimarios || []

  // Generate years dynamically: current year + 2 previous years
  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: 3 }, (_, i) => String(currentYear - 2 + i))
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
    { value: 'format', label: '📦 Tipo Empaque' },
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

        {/* Search */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span>🔍</span> Buscar
          </h3>
          <div className="relative">
            <input
              type="text"
              value={props.searchTerm}
              onChange={(e) => props.onSearchChange(e.target.value)}
              placeholder="Cliente, Producto, Canal, SKU..."
              className="w-full px-3 py-2 pl-9 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
              🔍
            </span>
            {props.searchTerm && (
              <button
                onClick={() => props.onSearchChange('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                title="Limpiar búsqueda"
              >
                ✕
              </button>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Busca por cliente, producto, canal, SKU o SKU primario
          </p>
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

          {/* Year selection - show for both 'year' and 'month' modes */}
          {(props.dateFilterType === 'year' || props.dateFilterType === 'month') && (
            <div className="mb-3">
              {props.dateFilterType === 'month' && (
                <label className="block text-xs text-gray-600 mb-2">Selecciona año(s):</label>
              )}
              <div className="flex flex-wrap gap-2">
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
            </div>
          )}

          {/* Month selection */}
          {props.dateFilterType === 'month' && (
            <div className="mb-3">
              <label className="block text-xs text-gray-600 mb-2">Selecciona mes(es):</label>
              <div className="grid grid-cols-3 gap-2">
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
            <MultiSelect
              label="📊 Canal"
              options={channels}
              selected={props.selectedChannels}
              onChange={props.onChannelsChange}
              placeholder="Seleccionar canales..."
              searchable={true}
              maxHeight="200px"
            />
          </div>
        )}

        {/* Customers */}
        {customers.length > 0 && (
          <div className="mb-6">
            <MultiSelect
              label="👥 Cliente"
              options={customers}
              selected={props.selectedCustomers}
              onChange={props.onCustomersChange}
              placeholder="Seleccionar clientes..."
              searchable={true}
              maxHeight="250px"
            />
          </div>
        )}

        {/* Formats - dynamically loaded based on selected Familia */}
        {formats.length > 0 && (
          <div className="mb-6">
            <MultiSelect
              label="📦 Formato (Producto)"
              options={formats}
              selected={props.selectedFormats}
              onChange={props.onFormatsChange}
              placeholder="Seleccionar productos..."
              searchable={true}
              maxHeight="300px"
            />
            <p className="text-xs text-gray-500 mt-1">
              {props.selectedCategories.length > 0
                ? `Productos de: ${props.selectedCategories.join(', ')}`
                : 'Selecciona una Familia para filtrar productos'}
            </p>
          </div>
        )}

        {/* SKU Primario - dynamically loaded based on selected Familia */}
        {skuPrimarios.length > 0 && (
          <div className="mb-6">
            <MultiSelect
              label="🏷️ SKU Primario"
              options={skuPrimarios}
              selected={props.selectedSkuPrimarios}
              onChange={props.onSkuPrimariosChange}
              placeholder="Seleccionar SKU Primario..."
              searchable={true}
              maxHeight="250px"
            />
            <p className="text-xs text-gray-500 mt-1">
              {props.selectedCategories.length > 0
                ? `SKUs de: ${props.selectedCategories.join(', ')}`
                : 'Selecciona una Familia para filtrar SKUs'}
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
