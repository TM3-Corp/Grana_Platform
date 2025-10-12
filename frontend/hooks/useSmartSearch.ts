import { useMemo, useState, useCallback } from 'react'
import Fuse from 'fuse.js'
import {
  fuseOptions,
  normalizeSearchTerm,
  termVariations,
  categoryKeywords,
  type SearchableProduct
} from '@/lib/searchConfig'
import type { SearchSuggestion } from '@/components/SmartSearchBar'

export interface SearchResult {
  product: SearchableProduct
  score: number
  matches: Fuse.FuseResultMatch[]
}

export function useSmartSearch(products: SearchableProduct[]) {
  const [searchQuery, setSearchQuery] = useState('')
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([])

  // Crear índice Fuse con memoización
  const fuse = useMemo(
    () => new Fuse(products, fuseOptions),
    [products]
  )

  // Detectar categorías en el query
  const detectCategories = useCallback((query: string): string[] => {
    const normalized = normalizeSearchTerm(query)
    const detected: string[] = []

    for (const [keyword, category] of Object.entries(categoryKeywords)) {
      if (normalized.includes(keyword)) {
        if (!detected.includes(category)) {
          detected.push(category)
        }
      }
    }

    return detected
  }, [])

  // Extraer palabras clave del query (excluyendo palabras comunes)
  const extractKeywords = useCallback((query: string): string[] => {
    const stopWords = new Set(['de', 'del', 'la', 'el', 'los', 'las', 'con', 'sin', 'para', 'por', 'en', 'y', 'o'])
    const normalized = normalizeSearchTerm(query)
    const words = normalized.split(/\s+/).filter(w => w.length > 2 && !stopWords.has(w))
    return words
  }, [])

  // Encontrar variaciones de un término
  const findTermVariations = useCallback((term: string): string[] => {
    // Buscar directamente en el diccionario
    if (termVariations[term]) {
      return termVariations[term].filter(v => v !== term)
    }

    // Buscar si el término es una variación de alguna clave
    for (const [key, variations] of Object.entries(termVariations)) {
      if (variations.includes(term) && key !== term) {
        return variations.filter(v => v !== term)
      }
    }

    return []
  }, [])

  // Generar sugerencias inteligentes basadas en el query y resultados
  const generateSuggestions = useCallback((query: string, results: SearchResult[]): SearchSuggestion[] => {
    const suggestions: SearchSuggestion[] = []
    const normalized = normalizeSearchTerm(query)
    const keywords = extractKeywords(query)

    // 1. SUGERENCIA: Filtrar por categoría detectada
    const categories = detectCategories(query)
    if (categories.length > 0) {
      categories.slice(0, 2).forEach(cat => {
        suggestions.push({
          type: 'category',
          text: `Filtrar solo productos "${cat}"`,
          action: () => {
            // En el futuro, esto podría aplicar un filtro real
            setSearchQuery(cat.toLowerCase())
          }
        })
      })
    }

    // 2. SUGERENCIA: "¿También buscar...?" para variaciones de términos
    const variationsSuggested = new Set<string>()
    keywords.forEach(word => {
      const variations = findTermVariations(word)
      if (variations.length > 0 && !variationsSuggested.has(word)) {
        variationsSuggested.add(word)
        // Tomar solo las primeras 2 variaciones más comunes
        const topVariations = variations.slice(0, 2)
        suggestions.push({
          type: 'did_you_mean',
          text: `¿También buscar "${topVariations.join('" o "')}"?`,
          action: () => {
            // Agregar la primera variación al query
            const newQuery = query + ' ' + topVariations[0]
            setSearchQuery(newQuery)
          }
        })
      }
    })

    // 3. SUGERENCIA: Términos relacionados si hay pocos resultados
    if (results.length > 0 && results.length < 5) {
      // Extraer términos comunes de los resultados encontrados
      const resultTerms = new Map<string, number>()

      results.forEach(r => {
        const name = normalizeSearchTerm(r.product.name)
        const words = name.split(/\s+/).filter(w => w.length > 3)

        words.forEach(word => {
          // Solo agregar si no está ya en el query
          if (!keywords.includes(word)) {
            resultTerms.set(word, (resultTerms.get(word) || 0) + 1)
          }
        })
      })

      // Ordenar por frecuencia y tomar los top 3
      const topTerms = Array.from(resultTerms.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([term]) => term)

      if (topTerms.length > 0) {
        suggestions.push({
          type: 'related_term',
          text: `Términos relacionados: "${topTerms.join('", "')}"`,
          action: () => {
            // Agregar el primer término relacionado
            setSearchQuery(query + ' ' + topTerms[0])
          }
        })
      }
    }

    // 4. SUGERENCIA: Corrección de typos comunes
    // Si no hay resultados, sugerir variaciones conocidas
    if (results.length === 0 && keywords.length > 0) {
      keywords.forEach(word => {
        // Buscar en termVariations si hay una corrección común
        for (const [correct, variations] of Object.entries(termVariations)) {
          if (variations.includes(word) && correct !== word) {
            suggestions.push({
              type: 'did_you_mean',
              text: `¿Quisiste decir "${correct}"?`,
              action: () => {
                const newQuery = query.replace(new RegExp(`\\b${word}\\b`, 'gi'), correct)
                setSearchQuery(newQuery)
              }
            })
            break
          }
        }
      })
    }

    // Limitar a máximo 5 sugerencias totales para no abrumar al usuario
    return suggestions.slice(0, 5)
  }, [detectCategories, extractKeywords, findTermVariations])

  // Realizar búsqueda
  const search = useCallback((query: string): SearchResult[] => {
    if (!query.trim()) {
      setSuggestions([])
      return []
    }

    const normalized = normalizeSearchTerm(query)

    // Búsqueda con Fuse.js
    const fuseResults = fuse.search(normalized)

    // Convertir a nuestro formato
    const results: SearchResult[] = fuseResults.map(result => ({
      product: result.item,
      score: result.score || 0,
      matches: result.matches || []
    }))

    // Generar sugerencias basadas en el query y resultados
    const newSuggestions = generateSuggestions(query, results)
    setSuggestions(newSuggestions)

    return results
  }, [fuse, generateSuggestions])

  // Función para limpiar búsqueda
  const clearSearch = useCallback(() => {
    setSearchQuery('')
    setSuggestions([])
  }, [])

  // Función para aplicar una categoría como filtro
  const searchByCategory = useCallback((category: string) => {
    setSearchQuery(category)
  }, [])

  return {
    search,
    searchQuery,
    setSearchQuery,
    suggestions,
    clearSearch,
    searchByCategory,
    // Utilidades expuestas
    detectCategories,
    extractKeywords
  }
}
