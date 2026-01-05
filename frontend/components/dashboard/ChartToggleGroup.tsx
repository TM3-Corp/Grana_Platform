'use client'

import { useState, useEffect } from 'react'

export type ChartType = 'channel' | 'family' | 'customers'

interface ChartOption {
  id: ChartType
  label: string
  icon: string
}

const CHART_OPTIONS: ChartOption[] = [
  { id: 'channel', label: 'Canal', icon: '🏪' },
  { id: 'family', label: 'Familia', icon: '📦' },
  { id: 'customers', label: 'Clientes', icon: '👥' },
]

interface ChartToggleGroupProps {
  selectedCharts: ChartType[]
  onChange: (selected: ChartType[]) => void
  maxSelections?: number
  storageKey?: string
}

export default function ChartToggleGroup({
  selectedCharts,
  onChange,
  maxSelections = 2,
  storageKey,
}: ChartToggleGroupProps) {
  // Load persisted selection on mount
  useEffect(() => {
    if (storageKey && typeof window !== 'undefined') {
      const saved = localStorage.getItem(`chart_selection_${storageKey}`)
      if (saved) {
        try {
          const parsed = JSON.parse(saved) as ChartType[]
          if (Array.isArray(parsed) && parsed.length > 0) {
            onChange(parsed)
          }
        } catch (e) {
          // Ignore parsing errors
        }
      }
    }
  }, [storageKey])

  // Handle toggle
  const handleToggle = (chartId: ChartType) => {
    let newSelection: ChartType[]

    if (selectedCharts.includes(chartId)) {
      // Deselect - but keep at least one selected
      if (selectedCharts.length > 1) {
        newSelection = selectedCharts.filter(id => id !== chartId)
      } else {
        return // Can't deselect the only selected chart
      }
    } else {
      // Select - respect max selections
      if (selectedCharts.length >= maxSelections) {
        // Replace the first selected with new selection
        newSelection = [...selectedCharts.slice(1), chartId]
      } else {
        newSelection = [...selectedCharts, chartId]
      }
    }

    onChange(newSelection)

    // Persist selection
    if (storageKey && typeof window !== 'undefined') {
      localStorage.setItem(`chart_selection_${storageKey}`, JSON.stringify(newSelection))
    }
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-500 mr-2">Ver:</span>
      {CHART_OPTIONS.map((option) => {
        const isSelected = selectedCharts.includes(option.id)
        return (
          <button
            key={option.id}
            onClick={() => handleToggle(option.id)}
            className={`
              flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium
              transition-all duration-200
              ${isSelected
                ? 'bg-green-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }
            `}
          >
            <span>{option.icon}</span>
            <span>{option.label}</span>
          </button>
        )
      })}
      <span className="text-xs text-gray-400 ml-2">
        (max {maxSelections})
      </span>
    </div>
  )
}

// Export chart options for use in other components
export { CHART_OPTIONS }
