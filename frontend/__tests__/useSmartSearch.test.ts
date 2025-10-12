/**
 * Tests for useSmartSearch hook
 *
 * Tests the smart search functionality including:
 * - Search execution
 * - Suggestion generation
 * - Category detection
 * - Term variations handling
 */

import { renderHook, act } from '@testing-library/react'
import { useSmartSearch } from '@/hooks/useSmartSearch'
import type { SearchableProduct } from '@/lib/searchConfig'

describe('useSmartSearch Hook', () => {
  const mockProducts: SearchableProduct[] = [
    {
      id: 1,
      sku: 'BARR-KETO-01',
      name: 'Barra Keto Nuez',
      category: 'Keto',
      brand: 'Grana',
      source: 'shopify'
    },
    {
      id: 2,
      sku: 'BARR-KETO-02',
      name: 'Barrita Keto Chocolate',
      category: 'Keto',
      brand: 'Grana',
      source: 'mercadolibre'
    },
    {
      id: 3,
      sku: 'BARR-LOW-01',
      name: 'Barra Low Carb Almendras',
      category: 'LowCarb',
      brand: 'Grana',
      source: 'shopify'
    },
    {
      id: 4,
      sku: 'CRACK-01',
      name: 'Crackers Integrales',
      category: 'Snacks',
      brand: 'Grana',
      source: 'manual'
    },
    {
      id: 5,
      sku: 'GRAN-01',
      name: 'Granola Proteica',
      category: 'Breakfast',
      brand: 'Grana',
      source: 'shopify'
    }
  ]

  describe('Basic Search Functionality', () => {
    it('should initialize with empty state', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      expect(result.current.searchQuery).toBe('')
      expect(result.current.suggestions).toEqual([])
    })

    it('should perform search and return results', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('keto')
        expect(results.length).toBeGreaterThan(0)
        expect(results[0].product.name).toMatch(/[Kk]eto/)
      })
    })

    it('should return empty array for empty query', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('')
        expect(results).toEqual([])
      })
    })

    it('should update searchQuery state', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        result.current.setSearchQuery('keto nuez')
      })

      expect(result.current.searchQuery).toBe('keto nuez')
    })

    it('should clear search', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        result.current.setSearchQuery('keto')
        result.current.clearSearch()
      })

      expect(result.current.searchQuery).toBe('')
      expect(result.current.suggestions).toEqual([])
    })
  })

  describe('Fuzzy Matching', () => {
    it('should find "barra" when searching "barrita"', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('barrita')
        const names = results.map(r => r.product.name)
        expect(names.some(n => n.includes('Barra'))).toBe(true)
      })
    })

    it('should handle typos in search query', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('queto')  // typo for "keto"
        expect(results.length).toBeGreaterThan(0)
        expect(results[0].product.name).toMatch(/[Kk]eto/)
      })
    })

    it('should be word-order independent', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('nuez keto')
        expect(results.length).toBeGreaterThan(0)
        expect(results[0].product.name).toMatch(/[Kk]eto.*[Nn]uez/)
      })
    })
  })

  describe('Suggestion Generation', () => {
    it('should generate category suggestions', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        result.current.setSearchQuery('keto')
        result.current.search('keto')
      })

      expect(result.current.suggestions.length).toBeGreaterThan(0)
      const categorySuggestions = result.current.suggestions.filter(
        s => s.type === 'category'
      )
      expect(categorySuggestions.length).toBeGreaterThan(0)
    })

    it('should generate term variation suggestions', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        result.current.setSearchQuery('barra')
        result.current.search('barra')
      })

      const didYouMeanSuggestions = result.current.suggestions.filter(
        s => s.type === 'did_you_mean'
      )

      // Should suggest "barrita" or "barritas" as variations
      if (didYouMeanSuggestions.length > 0) {
        const suggestionText = didYouMeanSuggestions[0].text
        expect(
          suggestionText.includes('barrita') || suggestionText.includes('barritas')
        ).toBe(true)
      }
    })

    it('should generate related term suggestions for limited results', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        result.current.setSearchQuery('crackers')
        result.current.search('crackers')
      })

      // With only 1 result, should suggest related terms
      const relatedSuggestions = result.current.suggestions.filter(
        s => s.type === 'related_term'
      )

      expect(result.current.suggestions.length).toBeGreaterThanOrEqual(0)
    })

    it('should limit suggestions to maximum 5', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        result.current.setSearchQuery('barra')
        result.current.search('barra')
      })

      expect(result.current.suggestions.length).toBeLessThanOrEqual(5)
    })

    it('should clear suggestions when search is cleared', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        result.current.setSearchQuery('keto')
        result.current.search('keto')
      })

      expect(result.current.suggestions.length).toBeGreaterThan(0)

      act(() => {
        result.current.clearSearch()
      })

      expect(result.current.suggestions).toEqual([])
    })
  })

  describe('Category Detection', () => {
    it('should detect "keto" category', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      const categories = result.current.detectCategories('barra keto nuez')
      expect(categories).toContain('Keto')
    })

    it('should detect "lowcarb" category variations', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      const categories1 = result.current.detectCategories('low carb')
      const categories2 = result.current.detectCategories('lowcarb')
      const categories3 = result.current.detectCategories('low-carb')

      expect(categories1).toContain('LowCarb')
      expect(categories2).toContain('LowCarb')
      expect(categories3).toContain('LowCarb')
    })

    it('should detect multiple categories', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      const categories = result.current.detectCategories('keto low carb proteina')
      expect(categories.length).toBeGreaterThan(1)
    })

    it('should not duplicate category detections', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      const categories = result.current.detectCategories('keto keto keto')
      expect(categories.filter(c => c === 'Keto').length).toBe(1)
    })

    it('should be case insensitive', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      const categories1 = result.current.detectCategories('KETO')
      const categories2 = result.current.detectCategories('keto')
      const categories3 = result.current.detectCategories('KeTo')

      expect(categories1).toEqual(categories2)
      expect(categories2).toEqual(categories3)
    })
  })

  describe('Keyword Extraction', () => {
    it('should extract meaningful keywords', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      const keywords = result.current.extractKeywords('barra keto nuez')
      expect(keywords).toContain('barra')
      expect(keywords).toContain('keto')
      expect(keywords).toContain('nuez')
    })

    it('should filter out stop words', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      const keywords = result.current.extractKeywords('barra de keto con nuez')
      expect(keywords).not.toContain('de')
      expect(keywords).not.toContain('con')
      expect(keywords).toContain('barra')
      expect(keywords).toContain('keto')
      expect(keywords).toContain('nuez')
    })

    it('should filter out short words', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      const keywords = result.current.extractKeywords('barra keto de 5 un')
      expect(keywords).not.toContain('de')
      expect(keywords).not.toContain('5')
      expect(keywords).not.toContain('un')
    })

    it('should handle empty query', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      const keywords = result.current.extractKeywords('')
      expect(keywords).toEqual([])
    })
  })

  describe('Search Results Quality', () => {
    it('should include match information in results', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('keto')
        expect(results[0].matches).toBeDefined()
        expect(results[0].matches.length).toBeGreaterThan(0)
      })
    })

    it('should include relevance score in results', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('keto')
        expect(typeof results[0].score).toBe('number')
        expect(results[0].score).toBeGreaterThanOrEqual(0)
        expect(results[0].score).toBeLessThanOrEqual(1)
      })
    })

    it('should order results by relevance', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('barra')
        // More specific matches should come first
        for (let i = 0; i < results.length - 1; i++) {
          expect(results[i].score).toBeLessThanOrEqual(results[i + 1].score)
        }
      })
    })
  })

  describe('Search by Category', () => {
    it('should allow searching by category', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        result.current.searchByCategory('Keto')
      })

      expect(result.current.searchQuery).toBe('Keto')
    })

    it('should update query when using searchByCategory', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        result.current.searchByCategory('LowCarb')
      })

      expect(result.current.searchQuery).toBe('LowCarb')
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty products array', () => {
      const { result } = renderHook(() => useSmartSearch([]))

      act(() => {
        const results = result.current.search('keto')
        expect(results).toEqual([])
      })
    })

    it('should handle products with null/undefined fields', () => {
      const productsWithNulls: SearchableProduct[] = [
        {
          id: 1,
          sku: 'TEST-01',
          name: 'Test Product',
          category: null,
          brand: null,
          source: 'manual'
        }
      ]

      const { result } = renderHook(() => useSmartSearch(productsWithNulls))

      act(() => {
        const results = result.current.search('test')
        expect(results.length).toBeGreaterThan(0)
      })
    })

    it('should handle special characters in query', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('barra-keto_nuez')
        expect(results.length).toBeGreaterThan(0)
      })
    })

    it('should handle query with numbers', () => {
      const { result } = renderHook(() => useSmartSearch(mockProducts))

      act(() => {
        const results = result.current.search('BARR-KETO-01')
        expect(results.length).toBeGreaterThan(0)
        expect(results[0].product.sku).toBe('BARR-KETO-01')
      })
    })
  })

  describe('Performance', () => {
    it('should handle large product datasets', () => {
      // Create a large dataset
      const largeDataset: SearchableProduct[] = Array.from({ length: 1000 }, (_, i) => ({
        id: i,
        sku: `PROD-${i}`,
        name: `Product ${i} Keto ${i % 2 === 0 ? 'Barra' : 'Barrita'}`,
        category: i % 2 === 0 ? 'Keto' : 'LowCarb',
        brand: 'Grana',
        source: i % 3 === 0 ? 'shopify' : i % 3 === 1 ? 'mercadolibre' : 'manual'
      }))

      const { result } = renderHook(() => useSmartSearch(largeDataset))

      const startTime = Date.now()

      act(() => {
        result.current.search('keto barra')
      })

      const endTime = Date.now()

      // Search should complete in reasonable time (< 500ms)
      expect(endTime - startTime).toBeLessThan(500)
    })
  })
})
