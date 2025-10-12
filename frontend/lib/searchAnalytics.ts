/**
 * Search Analytics System
 *
 * Tracks user search behavior to improve search suggestions and understand usage patterns.
 * This data helps identify:
 * - Most searched products
 * - Common typos and variations
 * - Search patterns across different channels (Shopify/ML/Manual)
 * - Popular product categories
 */

import { useCallback } from 'react'

export interface SearchEvent {
  query: string
  resultsCount: number
  timestamp: number
  selectedProductId?: string
  selectedProductSource?: string
  sessionId: string
}

export interface SearchAnalytics {
  searches: SearchEvent[]
  popularTerms: Map<string, number>
  recentSearches: string[]
}

class SearchAnalyticsManager {
  private static instance: SearchAnalyticsManager
  private sessionId: string
  private storageKey = 'grana_search_analytics'
  private maxRecentSearches = 10
  private maxStoredSearches = 100

  private constructor() {
    // Generate or retrieve session ID
    this.sessionId = this.getOrCreateSessionId()
  }

  static getInstance(): SearchAnalyticsManager {
    if (!SearchAnalyticsManager.instance) {
      SearchAnalyticsManager.instance = new SearchAnalyticsManager()
    }
    return SearchAnalyticsManager.instance
  }

  private getOrCreateSessionId(): string {
    if (typeof window === 'undefined') return 'server-session'

    let sessionId = sessionStorage.getItem('grana_session_id')
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      sessionStorage.setItem('grana_session_id', sessionId)
    }
    return sessionId
  }

  /**
   * Track a search query
   */
  trackSearch(query: string, resultsCount: number): void {
    if (typeof window === 'undefined') return
    if (!query.trim()) return

    const event: SearchEvent = {
      query: query.trim().toLowerCase(),
      resultsCount,
      timestamp: Date.now(),
      sessionId: this.sessionId
    }

    this.storeEvent(event)
    this.updateRecentSearches(event.query)
  }

  /**
   * Track when a user clicks on a search result
   */
  trackResultClick(query: string, productId: string, productSource: string): void {
    if (typeof window === 'undefined') return

    const event: SearchEvent = {
      query: query.trim().toLowerCase(),
      resultsCount: -1, // Not relevant for click events
      timestamp: Date.now(),
      selectedProductId: productId,
      selectedProductSource: productSource,
      sessionId: this.sessionId
    }

    this.storeEvent(event)

    // Send to backend for aggregation
    this.sendToBackend(event)
  }

  /**
   * Get recent search queries for autocomplete
   */
  getRecentSearches(): string[] {
    if (typeof window === 'undefined') return []

    try {
      const data = localStorage.getItem(`${this.storageKey}_recent`)
      return data ? JSON.parse(data) : []
    } catch (error) {
      console.error('Error loading recent searches:', error)
      return []
    }
  }

  /**
   * Get popular search terms from local storage
   */
  getPopularTerms(): Map<string, number> {
    if (typeof window === 'undefined') return new Map()

    try {
      const data = localStorage.getItem(`${this.storageKey}_popular`)
      const obj = data ? JSON.parse(data) : {}
      return new Map(Object.entries(obj))
    } catch (error) {
      console.error('Error loading popular terms:', error)
      return new Map()
    }
  }

  /**
   * Get search analytics data
   */
  getAnalytics(): SearchAnalytics {
    if (typeof window === 'undefined') {
      return { searches: [], popularTerms: new Map(), recentSearches: [] }
    }

    try {
      const data = localStorage.getItem(this.storageKey)
      const searches: SearchEvent[] = data ? JSON.parse(data) : []

      return {
        searches,
        popularTerms: this.getPopularTerms(),
        recentSearches: this.getRecentSearches()
      }
    } catch (error) {
      console.error('Error loading analytics:', error)
      return { searches: [], popularTerms: new Map(), recentSearches: [] }
    }
  }

  /**
   * Clear all analytics data
   */
  clearAnalytics(): void {
    if (typeof window === 'undefined') return

    localStorage.removeItem(this.storageKey)
    localStorage.removeItem(`${this.storageKey}_recent`)
    localStorage.removeItem(`${this.storageKey}_popular`)
  }

  /**
   * Export analytics data (for debugging or sending to backend)
   */
  exportAnalytics(): string {
    const analytics = this.getAnalytics()
    return JSON.stringify({
      ...analytics,
      popularTerms: Array.from(analytics.popularTerms.entries())
    }, null, 2)
  }

  private storeEvent(event: SearchEvent): void {
    try {
      const data = localStorage.getItem(this.storageKey)
      const searches: SearchEvent[] = data ? JSON.parse(data) : []

      searches.push(event)

      // Keep only last N searches to prevent storage bloat
      if (searches.length > this.maxStoredSearches) {
        searches.shift()
      }

      localStorage.setItem(this.storageKey, JSON.stringify(searches))

      // Update popular terms
      this.updatePopularTerms(event.query)
    } catch (error) {
      console.error('Error storing search event:', error)
    }
  }

  private updateRecentSearches(query: string): void {
    try {
      let recent = this.getRecentSearches()

      // Remove duplicates
      recent = recent.filter(q => q !== query)

      // Add to front
      recent.unshift(query)

      // Keep only last N
      if (recent.length > this.maxRecentSearches) {
        recent = recent.slice(0, this.maxRecentSearches)
      }

      localStorage.setItem(`${this.storageKey}_recent`, JSON.stringify(recent))
    } catch (error) {
      console.error('Error updating recent searches:', error)
    }
  }

  private updatePopularTerms(query: string): void {
    try {
      const popular = this.getPopularTerms()
      const count = popular.get(query) || 0
      popular.set(query, count + 1)

      // Convert Map to object for storage
      const obj = Object.fromEntries(popular)
      localStorage.setItem(`${this.storageKey}_popular`, JSON.stringify(obj))
    } catch (error) {
      console.error('Error updating popular terms:', error)
    }
  }

  private async sendToBackend(event: SearchEvent): Promise<void> {
    try {
      await fetch('/api/v1/products/search/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event)
      })
    } catch (error) {
      // Silent fail - analytics shouldn't break user experience
      console.debug('Analytics backend error:', error)
    }
  }
}

// Export singleton instance
export const searchAnalytics = SearchAnalyticsManager.getInstance()

/**
 * React hook for using search analytics
 */
export function useSearchAnalytics() {
  const trackSearch = useCallback((query: string, resultsCount: number) => {
    searchAnalytics.trackSearch(query, resultsCount)
  }, [])

  const trackResultClick = useCallback((query: string, productId: string, productSource: string) => {
    searchAnalytics.trackResultClick(query, productId, productSource)
  }, [])

  const getRecentSearches = useCallback(() => {
    return searchAnalytics.getRecentSearches()
  }, [])

  const getPopularTerms = useCallback(() => {
    return searchAnalytics.getPopularTerms()
  }, [])

  const clearAnalytics = useCallback(() => {
    searchAnalytics.clearAnalytics()
  }, [])

  return {
    trackSearch,
    trackResultClick,
    getRecentSearches,
    getPopularTerms,
    clearAnalytics
  }
}
