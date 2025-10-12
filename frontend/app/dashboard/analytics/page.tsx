'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface AnalyticsData {
  totalSearches: number
  searchesLast24h: number
  searchesLast7d: number
  topSearches: Array<{ term: string; count: number }>
  noResultSearches: string[]
  clickThroughRate: number
  avgResultsPerSearch: number
  sourceClickDistribution: Record<string, number>
  uniqueSearchTerms: number
}

export default function SearchAnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await fetch('/api/v1/products/search/track')

        if (!response.ok) {
          throw new Error('Failed to fetch analytics')
        }

        const data = await response.json()
        setAnalytics(data.analytics)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando analytics...</p>
        </div>
      </div>
    )
  }

  if (error || !analytics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 max-w-md">
          <h2 className="text-yellow-800 font-semibold text-lg mb-2">Sin Datos</h2>
          <p className="text-yellow-600">
            No hay datos de búsqueda todavía. Realiza algunas búsquedas en el catálogo de productos para ver analytics.
          </p>
          <Link
            href="/dashboard/products"
            className="mt-4 inline-block px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            Ir al Catálogo
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                📊 Analytics de Búsqueda
              </h1>
              <p className="mt-2 text-gray-600">
                Análisis de comportamiento de búsqueda de productos
              </p>
            </div>
            <Link
              href="/dashboard"
              className="text-gray-600 hover:text-gray-900"
            >
              ← Volver al Dashboard
            </Link>
          </div>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Búsquedas</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {analytics.totalSearches.toLocaleString()}
                </p>
              </div>
              <div className="bg-green-100 rounded-full p-3">
                <svg className="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Últimas 24h: {analytics.searchesLast24h}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Términos Únicos</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {analytics.uniqueSearchTerms}
                </p>
              </div>
              <div className="bg-blue-100 rounded-full p-3">
                <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
                </svg>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Diversidad de búsquedas
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Click-Through Rate</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {analytics.clickThroughRate}%
                </p>
              </div>
              <div className="bg-purple-100 rounded-full p-3">
                <svg className="w-6 h-6 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M6.672 1.911a1 1 0 10-1.932.518l.259.966a1 1 0 001.932-.518l-.26-.966zM2.429 4.74a1 1 0 10-.517 1.932l.966.259a1 1 0 00.517-1.932l-.966-.26zm8.814-.569a1 1 0 00-1.415-1.414l-.707.707a1 1 0 101.415 1.415l.707-.708zm-7.071 7.072l.707-.707A1 1 0 003.465 9.12l-.708.707a1 1 0 001.415 1.415zm3.2-5.171a1 1 0 00-1.3 1.3l4 10a1 1 0 001.823.075l1.38-2.759 3.018 3.02a1 1 0 001.414-1.415l-3.019-3.02 2.76-1.379a1 1 0 00-.076-1.822l-10-4z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              % de búsquedas con click
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Resultados Promedio</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {analytics.avgResultsPerSearch.toFixed(1)}
                </p>
              </div>
              <div className="bg-orange-100 rounded-full p-3">
                <svg className="w-6 h-6 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                </svg>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Por búsqueda
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Top Searches */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              🔥 Búsquedas Más Populares
            </h2>
            <div className="space-y-3">
              {analytics.topSearches.length > 0 ? (
                analytics.topSearches.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-gray-400">#{idx + 1}</span>
                      <span className="font-medium text-gray-900">{item.term}</span>
                    </div>
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold">
                      {item.count} búsquedas
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-sm">No hay datos todavía</p>
              )}
            </div>
          </div>

          {/* No Results Searches */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              ⚠️ Búsquedas Sin Resultados
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              Estas búsquedas no encontraron productos. Considera agregar sinónimos o mejorar el catálogo.
            </p>
            <div className="space-y-2">
              {analytics.noResultSearches.length > 0 ? (
                analytics.noResultSearches.map((term, idx) => (
                  <div key={idx} className="p-2 bg-red-50 rounded text-red-800 text-sm border border-red-200">
                    "{term}"
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-sm">¡Todas las búsquedas encontraron resultados! 🎉</p>
              )}
            </div>
          </div>

          {/* Source Click Distribution */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              📍 Clicks por Fuente
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              Distribución de clicks en productos por canal de venta
            </p>
            <div className="space-y-3">
              {Object.entries(analytics.sourceClickDistribution).length > 0 ? (
                Object.entries(analytics.sourceClickDistribution).map(([source, count]) => {
                  const total = Object.values(analytics.sourceClickDistribution).reduce((a, b) => a + b, 0)
                  const percentage = ((count / total) * 100).toFixed(1)

                  return (
                    <div key={source} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-gray-900 capitalize">
                          {source === 'shopify' ? '🛍️ Shopify' :
                           source === 'mercadolibre' ? '🛒 MercadoLibre' :
                           source === 'manual' ? '✏️ Manual' : source}
                        </span>
                        <span className="text-gray-600">
                          {count} clicks ({percentage}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  )
                })
              ) : (
                <p className="text-gray-500 text-sm">No hay datos de clicks todavía</p>
              )}
            </div>
          </div>

          {/* Weekly Trend */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
              📈 Tendencia Semanal
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div>
                  <p className="text-sm text-blue-800 font-medium">Últimas 24 horas</p>
                  <p className="text-2xl font-bold text-blue-900 mt-1">
                    {analytics.searchesLast24h}
                  </p>
                </div>
                <svg className="w-8 h-8 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                </svg>
              </div>

              <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg border border-green-200">
                <div>
                  <p className="text-sm text-green-800 font-medium">Últimos 7 días</p>
                  <p className="text-2xl font-bold text-green-900 mt-1">
                    {analytics.searchesLast7d}
                  </p>
                </div>
                <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                </svg>
              </div>

              <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div>
                  <p className="text-sm text-purple-800 font-medium">Total histórico</p>
                  <p className="text-2xl font-bold text-purple-900 mt-1">
                    {analytics.totalSearches}
                  </p>
                </div>
                <svg className="w-8 h-8 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Action Links */}
        <div className="mt-8 bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <svg className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h3 className="text-green-900 font-semibold mb-2">Mejora continua</h3>
              <p className="text-green-800 text-sm mb-3">
                Usa estos datos para mejorar tu catálogo y la experiencia de búsqueda.
                Agrega productos para términos populares sin resultados y optimiza los nombres
                de productos basándote en las búsquedas más comunes.
              </p>
              <Link
                href="/dashboard/products"
                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                </svg>
                Ir al Catálogo
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
