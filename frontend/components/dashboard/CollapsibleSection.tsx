'use client'

import { useState, useEffect, ReactNode } from 'react'

interface CollapsibleSectionProps {
  title: string
  icon?: string
  defaultExpanded?: boolean
  children: ReactNode
  badge?: string
  storageKey?: string // For persisting state to localStorage
}

export default function CollapsibleSection({
  title,
  icon,
  defaultExpanded = true,
  children,
  badge,
  storageKey,
}: CollapsibleSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const [isAnimating, setIsAnimating] = useState(false)

  // Load persisted state on mount
  useEffect(() => {
    if (storageKey && typeof window !== 'undefined') {
      const savedState = localStorage.getItem(`collapsible_${storageKey}`)
      if (savedState !== null) {
        setIsExpanded(savedState === 'true')
      }
    }
  }, [storageKey])

  // Handle toggle with animation
  const handleToggle = () => {
    setIsAnimating(true)
    setIsExpanded(!isExpanded)

    // Persist state if storageKey provided
    if (storageKey && typeof window !== 'undefined') {
      localStorage.setItem(`collapsible_${storageKey}`, (!isExpanded).toString())
    }

    // Clear animation state after transition
    setTimeout(() => setIsAnimating(false), 300)
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header - Always visible */}
      <button
        onClick={handleToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {icon && <span className="text-xl">{icon}</span>}
          <h3 className="font-semibold text-gray-900">{title}</h3>
          {badge && (
            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs font-medium">
              {badge}
            </span>
          )}
        </div>

        {/* Chevron icon */}
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Content - Collapsible */}
      <div
        className={`transition-all duration-300 ease-in-out overflow-hidden ${
          isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className={`px-6 pb-6 ${isAnimating ? '' : ''}`}>
          {children}
        </div>
      </div>
    </div>
  )
}
