'use client'

import { useState, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface MultiSelectProps {
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  label?: string
  searchable?: boolean
  maxHeight?: string
  emptyMessage?: string
  className?: string
  disabled?: boolean
}

export default function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = 'Seleccionar...',
  label,
  searchable = true,
  maxHeight = '200px',
  emptyMessage = 'No hay opciones disponibles',
  className,
  disabled = false,
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Filter options based on search
  const filteredOptions = options.filter(option =>
    option.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const toggleOption = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter(item => item !== option))
    } else {
      onChange([...selected, option])
    }
  }

  const removeOption = (option: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(selected.filter(item => item !== option))
  }

  const selectAll = () => {
    onChange([...options])
  }

  const clearAll = () => {
    onChange([])
    setSearchQuery('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false)
      setSearchQuery('')
    }
  }

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          {label}
        </label>
      )}

      {/* Trigger button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={cn(
          'w-full min-h-[42px] px-3 py-2 text-left',
          'bg-white border border-gray-300 rounded-lg',
          'focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
          'transition-all duration-200',
          disabled ? 'opacity-50 cursor-not-allowed bg-gray-50' : 'hover:border-gray-400',
          isOpen && 'ring-2 ring-green-500 border-transparent'
        )}
      >
        <div className="flex flex-wrap gap-1.5 items-center">
          {selected.length === 0 ? (
            <span className="text-gray-400 text-sm">{placeholder}</span>
          ) : selected.length <= 3 ? (
            selected.map(item => (
              <span
                key={item}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-800 text-xs font-medium rounded-full"
              >
                {item}
                <button
                  type="button"
                  onClick={(e) => removeOption(item, e)}
                  className="hover:bg-green-200 rounded-full p-0.5 transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </span>
            ))
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-800 text-xs font-medium rounded-full">
              {selected.length} seleccionados
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  clearAll()
                }}
                className="hover:bg-green-200 rounded-full p-0.5 transition-colors"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </span>
          )}
        </div>

        {/* Dropdown icon */}
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
          <svg
            className={cn('w-4 h-4 transition-transform duration-200', isOpen && 'rotate-180')}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden"
          onKeyDown={handleKeyDown}
        >
          {/* Search input */}
          {searchable && (
            <div className="p-2 border-b border-gray-200">
              <div className="relative">
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  ref={inputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Buscar..."
                  className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  autoFocus
                />
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
            <button
              type="button"
              onClick={selectAll}
              className="text-xs text-green-600 hover:text-green-800 font-medium transition-colors"
            >
              Seleccionar todos
            </button>
            {selected.length > 0 && (
              <button
                type="button"
                onClick={clearAll}
                className="text-xs text-red-600 hover:text-red-800 font-medium transition-colors"
              >
                Limpiar ({selected.length})
              </button>
            )}
          </div>

          {/* Options list */}
          <div className="overflow-y-auto" style={{ maxHeight }}>
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-gray-500">
                {searchQuery ? `No se encontró "${searchQuery}"` : emptyMessage}
              </div>
            ) : (
              filteredOptions.map(option => (
                <button
                  key={option}
                  type="button"
                  onClick={() => toggleOption(option)}
                  className={cn(
                    'w-full px-3 py-2 text-left text-sm flex items-center gap-2 transition-colors',
                    selected.includes(option)
                      ? 'bg-green-50 text-green-900'
                      : 'hover:bg-gray-50 text-gray-700'
                  )}
                >
                  {/* Checkbox indicator */}
                  <span
                    className={cn(
                      'w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-all',
                      selected.includes(option)
                        ? 'bg-green-500 border-green-500'
                        : 'border-gray-300'
                    )}
                  >
                    {selected.includes(option) && (
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </span>
                  <span className="truncate">{option}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
