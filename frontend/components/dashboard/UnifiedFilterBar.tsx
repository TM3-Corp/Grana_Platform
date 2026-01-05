'use client'

import { useState } from 'react'
import { useDashboardFilters, FAMILY_OPTIONS } from './DashboardFilterContext'

export default function UnifiedFilterBar() {
  const { filters, dateRange, setFilters } = useDashboardFilters()
  const [showFamilyDropdown, setShowFamilyDropdown] = useState(false)

  // Format date for display
  const formatDateRange = () => {
    const from = new Date(dateRange.from + 'T00:00:00')
    const to = new Date(dateRange.to + 'T00:00:00')
    return `${from.toLocaleDateString('es-CL')} - ${to.toLocaleDateString('es-CL')}`
  }

  // Get current family label
  const currentFamilyLabel = FAMILY_OPTIONS.find(f => f.value === filters.family)?.label || 'Todas las Familias'

  return (
    <div className="sticky top-16 z-40 bg-white/95 backdrop-blur-sm border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex flex-wrap items-center gap-4">
          {/* Dashboard Title */}
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span className="text-sm font-semibold text-gray-700">Proyecciones de Ventas</span>
          </div>

          {/* Separator */}
          <div className="h-6 w-px bg-gray-200" />

          {/* Family Filter */}
          <div className="relative">
            <button
              onClick={() => setShowFamilyDropdown(!showFamilyDropdown)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors"
            >
              <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span className="text-sm font-medium text-gray-700">
                {currentFamilyLabel}
              </span>
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showFamilyDropdown && (
              <div className="absolute top-full left-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                {FAMILY_OPTIONS.map((option) => (
                  <button
                    key={option.value || 'all'}
                    onClick={() => {
                      setFilters({ family: option.value })
                      setShowFamilyDropdown(false)
                    }}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 transition-colors ${
                      filters.family === option.value ? 'bg-green-50 text-green-700 font-medium' : 'text-gray-700'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Date Range Display (YTD context) */}
          <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span>YTD: {formatDateRange()}</span>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Reset Button (only show if family filter is applied) */}
          {filters.family !== null && (
            <button
              onClick={() => setFilters({ family: null })}
              className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Limpiar filtro
            </button>
          )}
        </div>
      </div>

      {/* Click outside handler */}
      {showFamilyDropdown && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowFamilyDropdown(false)}
        />
      )}
    </div>
  )
}
