'use client'

import { useState } from 'react'
import MultiSelect from '@/components/ui/MultiSelect'
import {
  SlidersHorizontal,
  Search,
  Calendar,
  Tag,
  Store,
  Users,
  Package,
  Hash,
  Layers,
  BarChart3,
  Settings2,
  X,
  ChevronRight,
  ChevronLeft,
  RotateCcw
} from 'lucide-react'

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

  // Collapse state callback
  onCollapseChange?: (collapsed: boolean) => void
}

export default function FiltersSidebar(props: FiltersSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const handleCollapseToggle = (collapsed: boolean) => {
    setIsCollapsed(collapsed)
    props.onCollapseChange?.(collapsed)
  }

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
    { value: 'format', label: 'Tipo Empaque' },
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

  if (isCollapsed) {
    return (
      <div className="fixed left-0 top-20 z-40">
        <button
          onClick={() => handleCollapseToggle(false)}
          className="bg-white shadow-lg rounded-r-lg p-3 hover:bg-gray-50 transition-colors border border-l-0 border-gray-200"
          title="Mostrar filtros"
        >
          <ChevronRight className="w-5 h-5 text-gray-600" strokeWidth={1.75} />
        </button>
      </div>
    )
  }

  return (
    <div className="fixed left-0 top-20 bottom-0 w-80 bg-white shadow-lg overflow-y-auto z-40 border-r border-gray-200">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
            <SlidersHorizontal className="w-5 h-5 text-gray-700" strokeWidth={1.75} />
            Filtros
          </h2>
          <button
            onClick={() => handleCollapseToggle(true)}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded hover:bg-gray-100"
            title="Ocultar filtros"
          >
            <ChevronLeft className="w-5 h-5" strokeWidth={1.75} />
          </button>
        </div>

        {/* Search */}
        <div className="mb-6">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
            <Search className="w-3.5 h-3.5" strokeWidth={2} />
            Buscar
          </h3>
          <div className="relative">
            <input
              type="text"
              value={props.searchTerm}
              onChange={(e) => props.onSearchChange(e.target.value)}
              placeholder="Cliente, Producto, Canal, SKU..."
              className="w-full px-3 py-2 pl-9 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" strokeWidth={1.75} />
            {props.searchTerm && (
              <button
                onClick={() => props.onSearchChange('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-0.5 rounded hover:bg-gray-100"
                title="Limpiar búsqueda"
              >
                <X className="w-4 h-4" strokeWidth={1.75} />
              </button>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-1.5">
            Busca por cliente, producto, canal, SKU o SKU primario
          </p>
        </div>

        {/* Date Filters */}
        <div className="mb-6">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5" strokeWidth={2} />
            Período
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
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
            <Tag className="w-3.5 h-3.5" strokeWidth={2} />
            Familia de Producto
          </h3>
          <div className="flex flex-wrap gap-2">
            {categories.map(category => (
              <button
                key={category}
                onClick={() => toggleCategory(category)}
                className={`
                  px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                  ${props.selectedCategories.includes(category)
                    ? 'bg-green-500 text-white shadow-sm'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                {category}
              </button>
            ))}
          </div>
        </div>

        {/* Channels */}
        {channels.length > 0 && (
          <div className="mb-6">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
              <Store className="w-3.5 h-3.5" strokeWidth={2} />
              Canal
            </h3>
            <MultiSelect
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
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
              <Users className="w-3.5 h-3.5" strokeWidth={2} />
              Cliente
            </h3>
            <MultiSelect
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
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
              <Package className="w-3.5 h-3.5" strokeWidth={2} />
              Formato (Producto)
            </h3>
            <MultiSelect
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
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
              <Hash className="w-3.5 h-3.5" strokeWidth={2} />
              SKU Primario
            </h3>
            <MultiSelect
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
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
            <Layers className="w-3.5 h-3.5" strokeWidth={2} />
            Agrupación
          </h3>
          <select
            value={props.groupBy}
            onChange={(e) => props.onGroupByChange(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
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
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
            <BarChart3 className="w-3.5 h-3.5" strokeWidth={2} />
            Apilar por
          </h3>
          <select
            value={props.stackBy || ''}
            onChange={(e) => props.onStackByChange(e.target.value || null)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
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
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
            <Settings2 className="w-3.5 h-3.5" strokeWidth={2} />
            Top X
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
          className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-red-50 hover:text-red-600 transition-colors text-sm font-medium flex items-center justify-center gap-2 border border-gray-200 hover:border-red-200"
        >
          <RotateCcw className="w-4 h-4" strokeWidth={1.75} />
          Limpiar Filtros
        </button>
      </div>
    </div>
  )
}
