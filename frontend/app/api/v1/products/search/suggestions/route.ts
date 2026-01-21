import { NextRequest, NextResponse } from 'next/server'

/**
 * GET /api/v1/products/search/suggestions
 *
 * Returns intelligent search suggestions based on:
 * - Popular search terms
 * - Recent searches
 * - Product catalog analysis
 * - Cross-channel variations (Shopify/ML/Manual)
 *
 * Query params:
 * - q: partial search query
 * - limit: max number of suggestions (default: 5)
 */

// In-memory storage for popular terms (in production, use Redis or DB)
let popularSearches: Map<string, number> = new Map()
const productTermsCache: Set<string> = new Set()

// Common Chilean food product terms and variations
const commonTerms = new Set([
  'barra',
  'barrita',
  'barritas',
  'keto',
  'lowcarb',
  'low carb',
  'proteina',
  'protein',
  'nuez',
  'nueces',
  'almendra',
  'almendras',
  'chocolate',
  'cacao',
  'vegana',
  'vegan',
  'sin gluten',
  'gluten free',
  'organico',
  'organica',
  'natural',
  'saludable',
  'snack',
  'colacion',
  'display',
  'unidad',
  'unidades',
  'caja'
])

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const query = searchParams.get('q') || ''
    const limit = parseInt(searchParams.get('limit') || '5')

    if (!query.trim()) {
      // Return popular terms when no query
      const popular = getTopPopularTerms(limit)
      return NextResponse.json({
        suggestions: popular,
        type: 'popular'
      })
    }

    // Generate suggestions based on query
    const suggestions = generateSuggestions(query, limit)

    return NextResponse.json({
      suggestions,
      type: 'matches',
      query
    })
  } catch (error) {
    console.error('Error generating suggestions:', error)
    return NextResponse.json(
      { error: 'Failed to generate suggestions' },
      { status: 500 }
    )
  }
}

/**
 * POST /api/v1/products/search/suggestions
 *
 * Initialize or update the product terms cache
 * This should be called when product catalog changes
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { products } = body

    if (!Array.isArray(products)) {
      return NextResponse.json(
        { error: 'Invalid products array' },
        { status: 400 }
      )
    }

    // Extract terms from product names
    products.forEach(product => {
      if (product.name) {
        const terms = extractTerms(product.name)
        terms.forEach(term => productTermsCache.add(term))
      }
    })

    return NextResponse.json({
      success: true,
      termsCount: productTermsCache.size
    })
  } catch (error) {
    console.error('Error updating product terms:', error)
    return NextResponse.json(
      { error: 'Failed to update product terms' },
      { status: 500 }
    )
  }
}

/**
 * Helper: Generate suggestions based on query
 */
function generateSuggestions(query: string, limit: number): string[] {
  const normalized = query.toLowerCase().trim()
  const suggestions = new Set<string>()

  // 1. Match against common terms
  for (const term of commonTerms) {
    if (term.startsWith(normalized) && term !== normalized) {
      suggestions.add(term)
    }
  }

  // 2. Match against product terms cache
  for (const term of productTermsCache) {
    if (term.startsWith(normalized) && term !== normalized) {
      suggestions.add(term)
    }
  }

  // 3. Match against popular searches
  for (const [term] of popularSearches) {
    if (term.includes(normalized) && term !== normalized) {
      suggestions.add(term)
    }
  }

  // Convert to array and sort by popularity
  const sorted = Array.from(suggestions).sort((a, b) => {
    const aCount = popularSearches.get(a) || 0
    const bCount = popularSearches.get(b) || 0
    return bCount - aCount
  })

  return sorted.slice(0, limit)
}

/**
 * Helper: Get top popular terms
 */
function getTopPopularTerms(limit: number): string[] {
  const sorted = Array.from(popularSearches.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([term]) => term)

  return sorted.slice(0, limit)
}

/**
 * Helper: Extract searchable terms from product name
 */
function extractTerms(name: string): string[] {
  const normalized = name
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // Remove accents

  // Split by spaces and special characters
  const words = normalized.split(/[\s\-_,\.]+/)

  // Filter out short words and numbers
  return words.filter(word => word.length > 2 && !/^\d+$/.test(word))
}

/**
 * Helper: Update popular searches from analytics
 * This can be called periodically or triggered by analytics endpoint
 */
export function updatePopularSearches(term: string, count: number = 1): void {
  const current = popularSearches.get(term) || 0
  popularSearches.set(term, current + count)

  // Keep only top 1000 to prevent memory bloat
  if (popularSearches.size > 1000) {
    const sorted = Array.from(popularSearches.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 1000)
    popularSearches = new Map(sorted)
  }
}
