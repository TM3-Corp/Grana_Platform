import { NextRequest, NextResponse } from 'next/server'
import { updatePopularSearches } from '../suggestions/route'

/**
 * POST /api/v1/products/search/track
 *
 * Tracks search events from the frontend to build analytics and improve suggestions.
 * This data helps us understand:
 * - What products users are looking for
 * - Common search patterns across channels (Shopify/ML/Manual)
 * - Which results users actually click on
 * - Search effectiveness (results found vs. no results)
 */

interface SearchEvent {
  query: string
  resultsCount: number
  timestamp: number
  selectedProductId?: string
  selectedProductSource?: string
  sessionId: string
}

// In-memory storage (in production, use a database or analytics service)
const searchEvents: SearchEvent[] = []
const maxStoredEvents = 10000

export async function POST(request: NextRequest) {
  try {
    const event: SearchEvent = await request.json()

    // Validate event data
    if (!event.query || typeof event.resultsCount !== 'number') {
      return NextResponse.json(
        { error: 'Invalid event data' },
        { status: 400 }
      )
    }

    // Store the event
    storeEvent(event)

    // Update popular searches for suggestions
    updatePopularSearches(event.query.toLowerCase().trim())

    // Log for debugging (remove in production)
    console.log('[Search Analytics]', {
      query: event.query,
      results: event.resultsCount,
      clicked: event.selectedProductId ? 'yes' : 'no',
      source: event.selectedProductSource
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error tracking search event:', error)
    return NextResponse.json(
      { error: 'Failed to track event' },
      { status: 500 }
    )
  }
}

/**
 * GET /api/v1/products/search/track
 *
 * Get analytics data (for admin dashboard)
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const limit = parseInt(searchParams.get('limit') || '100')

    // Get recent events
    const recentEvents = searchEvents.slice(-limit)

    // Calculate analytics
    const analytics = calculateAnalytics(searchEvents)

    return NextResponse.json({
      events: recentEvents,
      analytics,
      totalEvents: searchEvents.length
    })
  } catch (error) {
    console.error('Error fetching analytics:', error)
    return NextResponse.json(
      { error: 'Failed to fetch analytics' },
      { status: 500 }
    )
  }
}

/**
 * Store search event
 */
function storeEvent(event: SearchEvent): void {
  searchEvents.push(event)

  // Keep only last N events to prevent memory bloat
  if (searchEvents.length > maxStoredEvents) {
    searchEvents.shift()
  }
}

/**
 * Calculate analytics from events
 */
function calculateAnalytics(events: SearchEvent[]) {
  const now = Date.now()
  const last24h = events.filter(e => now - e.timestamp < 24 * 60 * 60 * 1000)
  const last7d = events.filter(e => now - e.timestamp < 7 * 24 * 60 * 60 * 1000)

  // Most searched terms
  const termCounts = new Map<string, number>()
  events.forEach(e => {
    const term = e.query.toLowerCase().trim()
    termCounts.set(term, (termCounts.get(term) || 0) + 1)
  })
  const topSearches = Array.from(termCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([term, count]) => ({ term, count }))

  // Searches with no results (potential issues)
  const noResultSearches = events
    .filter(e => e.resultsCount === 0)
    .map(e => e.query)
    .slice(-20) // Last 20

  // Click-through rate (searches that led to product click)
  const searchesWithClicks = events.filter(e => e.selectedProductId).length
  const clickThroughRate = events.length > 0
    ? (searchesWithClicks / events.length) * 100
    : 0

  // Product source distribution (where users click)
  const sourceClicks = new Map<string, number>()
  events.forEach(e => {
    if (e.selectedProductSource) {
      sourceClicks.set(
        e.selectedProductSource,
        (sourceClicks.get(e.selectedProductSource) || 0) + 1
      )
    }
  })

  // Average results per search
  const avgResults = events.length > 0
    ? events.reduce((sum, e) => sum + e.resultsCount, 0) / events.length
    : 0

  return {
    totalSearches: events.length,
    searchesLast24h: last24h.length,
    searchesLast7d: last7d.length,
    topSearches,
    noResultSearches: Array.from(new Set(noResultSearches)).slice(0, 10),
    clickThroughRate: Math.round(clickThroughRate * 100) / 100,
    avgResultsPerSearch: Math.round(avgResults * 100) / 100,
    sourceClickDistribution: Object.fromEntries(sourceClicks),
    uniqueSearchTerms: termCounts.size
  }
}
