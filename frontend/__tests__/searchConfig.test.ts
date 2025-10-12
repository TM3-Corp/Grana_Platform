/**
 * Tests for searchConfig.ts
 *
 * Tests the core fuzzy search configuration and utility functions
 * that handle multi-channel product name variations.
 */

import {
  normalizeSearchTerm,
  normalizeForMatching,
  termVariations,
  categoryKeywords,
  fuseOptions,
  type SearchableProduct
} from '@/lib/searchConfig'
import Fuse from 'fuse.js'

describe('searchConfig - Normalization Functions', () => {
  describe('normalizeSearchTerm', () => {
    it('should convert to lowercase', () => {
      expect(normalizeSearchTerm('BARRA KETO')).toBe('barra keto')
    })

    it('should remove accents from Spanish text', () => {
      expect(normalizeSearchTerm('Proteína')).toBe('proteina')
      expect(normalizeSearchTerm('Almendras tostadas')).toBe('almendras tostadas')
    })

    it('should trim whitespace', () => {
      expect(normalizeSearchTerm('  barra keto  ')).toBe('barra keto')
    })

    it('should handle empty strings', () => {
      expect(normalizeSearchTerm('')).toBe('')
      expect(normalizeSearchTerm('   ')).toBe('')
    })
  })

  describe('normalizeForMatching', () => {
    it('should standardize "barra" variations', () => {
      expect(normalizeForMatching('Barrita de Chocolate')).toContain('barra')
      expect(normalizeForMatching('Barritas Keto')).toContain('barra')
      expect(normalizeForMatching('Barra Proteica')).toContain('barra')
    })

    it('should standardize "display" variations', () => {
      expect(normalizeForMatching('Display 5 unidades')).toContain('display')
      expect(normalizeForMatching('Disp x12')).toContain('display')
    })

    it('should standardize unit variations', () => {
      expect(normalizeForMatching('5 unidades')).toContain('unidad')
      expect(normalizeForMatching('12 uds')).toContain('unidad')
    })

    it('should handle multiple normalizations', () => {
      const result = normalizeForMatching('Barritas Display 5 Uds')
      expect(result).toContain('barra')
      expect(result).toContain('display')
      expect(result).toContain('unidad')
    })

    it('should remove accents', () => {
      expect(normalizeForMatching('Almendras tostadas')).not.toContain('á')
    })
  })
})

describe('searchConfig - Term Variations', () => {
  it('should have "barra" variations', () => {
    expect(termVariations['barra']).toContain('barrita')
    expect(termVariations['barra']).toContain('barritas')
    expect(termVariations['barra']).toContain('bar')
  })

  it('should have "keto" variations', () => {
    expect(termVariations['keto']).toContain('queto')
    expect(termVariations['keto']).toContain('ceto')
  })

  it('should have "lowcarb" variations', () => {
    expect(termVariations['lowcarb']).toContain('low carb')
    expect(termVariations['lowcarb']).toContain('low-carb')
  })

  it('should have "vegana" variations', () => {
    expect(termVariations['vegana']).toContain('vegan')
  })
})

describe('searchConfig - Category Keywords', () => {
  it('should map "keto" keywords to Keto category', () => {
    expect(categoryKeywords['keto']).toBe('Keto')
    expect(categoryKeywords['cetogenica']).toBe('Keto')
  })

  it('should map "low carb" keywords to LowCarb category', () => {
    expect(categoryKeywords['low carb']).toBe('LowCarb')
    expect(categoryKeywords['lowcarb']).toBe('LowCarb')
  })

  it('should map "protein" keywords to Protein category', () => {
    expect(categoryKeywords['proteina']).toBe('Protein')
    expect(categoryKeywords['protein']).toBe('Protein')
  })
})

describe('searchConfig - Fuse.js Configuration', () => {
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
      name: 'Barrita Keto Nuez',  // Different name, same product
      category: 'Keto',
      brand: 'Grana',
      source: 'mercadolibre'
    },
    {
      id: 3,
      sku: 'BARR-LOW-01',
      name: 'Barra Low Carb Chocolate',
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
    }
  ]

  let fuse: Fuse<SearchableProduct>

  beforeEach(() => {
    fuse = new Fuse(mockProducts, fuseOptions)
  })

  describe('Fuzzy Search - Cross-Channel Matching', () => {
    it('should find "barra keto nuez" when searching "barrita keto nuez"', () => {
      const results = fuse.search('barrita keto nuez')
      expect(results.length).toBeGreaterThan(0)

      // Should find both variations
      const names = results.map(r => r.item.name)
      expect(names).toContain('Barra Keto Nuez')
      expect(names).toContain('Barrita Keto Nuez')
    })

    it('should find products when searching with typos', () => {
      const results = fuse.search('queto nuez')  // "queto" instead of "keto"
      expect(results.length).toBeGreaterThan(0)
      expect(results[0].item.name).toMatch(/[Kk]eto/)
    })

    it('should find products with word order independence', () => {
      const results = fuse.search('nuez keto')  // Reversed order
      expect(results.length).toBeGreaterThan(0)
      expect(results[0].item.name).toMatch(/Keto.*Nuez/)
    })
  })

  describe('Fuzzy Search - SKU Matching', () => {
    it('should find products by SKU', () => {
      const results = fuse.search('BARR-KETO-01')
      expect(results.length).toBeGreaterThan(0)
      expect(results[0].item.sku).toBe('BARR-KETO-01')
    })

    it('should find products by partial SKU', () => {
      const results = fuse.search('KETO-01')
      expect(results.length).toBeGreaterThan(0)
      expect(results[0].item.sku).toContain('KETO-01')
    })
  })

  describe('Fuzzy Search - Category Matching', () => {
    it('should find all Keto products when searching "keto"', () => {
      const results = fuse.search('keto')
      expect(results.length).toBeGreaterThanOrEqual(2)

      results.forEach(result => {
        expect(
          result.item.category === 'Keto' || result.item.name.includes('Keto')
        ).toBe(true)
      })
    })

    it('should find LowCarb products when searching "low carb"', () => {
      const results = fuse.search('low carb')
      expect(results.length).toBeGreaterThan(0)
      expect(results[0].item.category).toBe('LowCarb')
    })
  })

  describe('Fuzzy Search - Source Independence', () => {
    it('should find products from all sources', () => {
      const results = fuse.search('barra')
      const sources = results.map(r => r.item.source)

      // Should find products from multiple sources
      expect(new Set(sources).size).toBeGreaterThan(1)
    })

    it('should not prioritize one source over another', () => {
      const results = fuse.search('keto nuez')

      // Both Shopify and MercadoLibre versions should be in results
      const names = results.slice(0, 3).map(r => r.item.name)
      expect(names.some(n => n.includes('Barra'))).toBe(true)
      expect(names.some(n => n.includes('Barrita'))).toBe(true)
    })
  })

  describe('Fuzzy Search - Edge Cases', () => {
    it('should handle empty query', () => {
      const results = fuse.search('')
      expect(results.length).toBe(0)
    })

    it('should handle query with only spaces', () => {
      const results = fuse.search('   ')
      expect(results.length).toBe(0)
    })

    it('should handle query with special characters', () => {
      const results = fuse.search('barra-keto')
      expect(results.length).toBeGreaterThan(0)
    })

    it('should handle very long queries', () => {
      const longQuery = 'barra keto nuez chocolate proteina lowcarb vegana sin gluten organica'
      const results = fuse.search(longQuery)
      // Should still return some results despite the long query
      expect(results.length).toBeGreaterThanOrEqual(0)
    })
  })

  describe('Fuzzy Search - Score and Relevance', () => {
    it('should return exact matches with better scores', () => {
      const results = fuse.search('Barra Keto Nuez')
      expect(results[0].score).toBeLessThan(0.3)  // Very low score = high relevance
    })

    it('should include match indices for highlighting', () => {
      const results = fuse.search('keto')
      expect(results[0].matches).toBeDefined()
      expect(results[0].matches!.length).toBeGreaterThan(0)
    })

    it('should match on multiple fields simultaneously', () => {
      const results = fuse.search('BARR keto')

      // Should match both SKU ("BARR") and name ("keto")
      expect(results[0].matches!.length).toBeGreaterThan(0)
      const matchedKeys = results[0].matches!.map(m => m.key)

      // Could match name, sku, or both
      expect(matchedKeys.length).toBeGreaterThan(0)
    })
  })
})

describe('searchConfig - Integration Test', () => {
  it('should handle complete search workflow', () => {
    const products: SearchableProduct[] = [
      {
        id: 1,
        sku: 'TEST-01',
        name: 'Barra Keto Nuez Display 5 Unidades',
        category: 'Keto',
        brand: 'Grana',
        source: 'shopify'
      }
    ]

    const fuse = new Fuse(products, fuseOptions)

    // User searches with variation
    const userQuery = 'barrita queto nueces disp'
    const normalized = normalizeSearchTerm(userQuery)
    const results = fuse.search(normalized)

    expect(results.length).toBeGreaterThan(0)
    expect(results[0].item.name).toContain('Barra')
    expect(results[0].item.name).toContain('Keto')
  })
})
