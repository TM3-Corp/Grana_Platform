'use client'

import { useState, useEffect, useRef } from 'react'

export interface SearchSuggestion {
  type: 'did_you_mean' | 'category' | 'related_term'
  text: string
  action: () => void
}

interface SmartSearchBarProps {
  value: string
  onChange: (value: string) => void
  suggestions: SearchSuggestion[]
  onSearch?: () => void
  placeholder?: string
  isSearching?: boolean
  className?: string
}

export default function SmartSearchBar({
  value,
  onChange,
  suggestions,
  onSearch,
  placeholder = 'Buscar productos por nombre, SKU, categoría...',
  isSearching = false,
  className = ''
}: SmartSearchBarProps) {
  const [showSuggestions, setShowSuggestions] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Cerrar sugerencias al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(e.target as Node) &&
        !inputRef.current?.contains(e.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Mostrar sugerencias cuando hay texto y sugerencias disponibles
  useEffect(() => {
    if (value.trim() && suggestions.length > 0) {
      setShowSuggestions(true)
    } else if (!value.trim()) {
      setShowSuggestions(false)
    }
  }, [value, suggestions])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSearch?.()
      setShowSuggestions(false)
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
      inputRef.current?.blur()
    }
  }

  const getSuggestionIcon = (type: SearchSuggestion['type']) => {
    switch (type) {
      case 'did_you_mean':
        return '💡'
      case 'category':
        return '🏷️'
      case 'related_term':
        return '🔗'
    }
  }

  const getSuggestionColor = (type: SearchSuggestion['type']) => {
    switch (type) {
      case 'did_you_mean':
        return 'bg-blue-50 hover:bg-blue-100 text-blue-800 border-blue-200'
      case 'category':
        return 'bg-green-50 hover:bg-green-100 text-green-800 border-green-200'
      case 'related_term':
        return 'bg-purple-50 hover:bg-purple-100 text-purple-800 border-purple-200'
    }
  }

  const getSuggestionTitle = (type: SearchSuggestion['type']) => {
    switch (type) {
      case 'did_you_mean':
        return '¿Quisiste decir...?'
      case 'category':
        return 'Filtrar por categoría'
      case 'related_term':
        return 'Términos relacionados'
    }
  }

  return (
    <div className={`relative w-full ${className}`}>
      {/* Search Input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          placeholder={placeholder}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck="false"
          className="w-full px-4 py-3 pl-12 pr-12 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all text-base"
        />

        {/* Search Icon */}
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        {/* Loading/Clear Button */}
        {value && (
          <button
            onClick={() => {
              onChange('')
              setShowSuggestions(false)
              inputRef.current?.focus()
            }}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Limpiar búsqueda"
          >
            {isSearching ? (
              <div className="animate-spin h-5 w-5 border-2 border-green-600 border-t-transparent rounded-full" />
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
          </button>
        )}
      </div>

      {/* Suggestions Dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute z-50 w-full mt-2 bg-white border-2 border-gray-200 rounded-lg shadow-lg max-h-72 overflow-y-auto"
        >
          <div className="p-3 space-y-2">
            {/* Group suggestions by type */}
            {['did_you_mean', 'category', 'related_term'].map(type => {
              const typeSuggestions = suggestions.filter(s => s.type === type)
              if (typeSuggestions.length === 0) return null

              return (
                <div key={type} className="space-y-1">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-2">
                    {getSuggestionTitle(type as SearchSuggestion['type'])}
                  </div>
                  {typeSuggestions.map((suggestion, idx) => (
                    <button
                      key={`${type}-${idx}`}
                      onClick={() => {
                        suggestion.action()
                        setShowSuggestions(false)
                        inputRef.current?.focus()
                      }}
                      className={`w-full text-left px-3 py-2.5 rounded-md transition-all flex items-center gap-2.5 border ${getSuggestionColor(suggestion.type)}`}
                    >
                      <span className="text-lg flex-shrink-0">{getSuggestionIcon(suggestion.type)}</span>
                      <span className="text-sm font-medium flex-1">{suggestion.text}</span>
                      <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  ))}
                </div>
              )
            })}
          </div>

          {/* Footer hint */}
          <div className="px-3 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-600 flex items-center justify-between">
            <span>
              <kbd className="px-1.5 py-0.5 bg-white border border-gray-300 rounded text-xs">Enter</kbd> para buscar
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-white border border-gray-300 rounded text-xs">Esc</kbd> para cerrar
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
