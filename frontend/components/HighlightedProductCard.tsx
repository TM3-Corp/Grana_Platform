import React from 'react'
import type Fuse from 'fuse.js'
import { getSourceBadge, type SearchableProduct } from '@/lib/searchConfig'

export interface SearchResult {
  product: SearchableProduct
  score: number
  matches: Fuse.FuseResultMatch[]
}

interface HighlightedProductCardProps {
  result: SearchResult
  onClick?: () => void
}

export default function HighlightedProductCard({ result, onClick }: HighlightedProductCardProps) {
  const { product, score, matches } = result

  // Función para resaltar matches en el texto
  const highlightText = (text: string, key: string): React.ReactNode => {
    const match = matches.find(m => m.key === key)
    if (!match || !match.indices || match.indices.length === 0) {
      return text
    }

    const parts: React.ReactNode[] = []
    let lastIndex = 0

    match.indices.forEach(([start, end], idx) => {
      // Texto antes del match
      if (start > lastIndex) {
        parts.push(
          <span key={`before-${idx}`}>
            {text.substring(lastIndex, start)}
          </span>
        )
      }

      // Texto matched (resaltado)
      parts.push(
        <mark key={`match-${idx}`} className="bg-yellow-200 font-semibold px-0.5 rounded">
          {text.substring(start, end + 1)}
        </mark>
      )

      lastIndex = end + 1
    })

    // Texto después del último match
    if (lastIndex < text.length) {
      parts.push(
        <span key="after">
          {text.substring(lastIndex)}
        </span>
      )
    }

    return <>{parts}</>
  }

  // Score badge - muestra qué tan relevante es el resultado
  const getScoreBadge = () => {
    // Score de Fuse.js: 0 = perfect match, 1 = no match
    // Convertimos a porcentaje: 0 → 100%, 1 → 0%
    const percentage = Math.round((1 - score) * 100)
    let color = 'bg-green-100 text-green-800 border-green-200'

    if (percentage < 70) color = 'bg-yellow-100 text-yellow-800 border-yellow-200'
    if (percentage < 50) color = 'bg-orange-100 text-orange-800 border-orange-200'

    return (
      <div className={`absolute top-3 right-3 px-2 py-1 rounded-full text-xs font-bold border ${color} flex items-center gap-1`}>
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
        {percentage}%
      </div>
    )
  }

  // Badge de origen (Shopify, ML, Manual)
  const sourceBadge = getSourceBadge(product.source)

  return (
    <div
      onClick={onClick}
      className="relative bg-white rounded-lg shadow hover:shadow-xl transition-all p-6 cursor-pointer border-2 border-transparent hover:border-green-500 group"
    >
      {/* Source Badge (canal de origen) */}
      <div className={`absolute top-3 left-3 px-2 py-1 rounded-full text-xs font-semibold flex items-center gap-1 border ${sourceBadge.color}`}>
        <span>{sourceBadge.icon}</span>
        <span>{sourceBadge.label}</span>
      </div>

      {/* Score Badge (relevancia) */}
      {getScoreBadge()}

      {/* Product Info */}
      <div className="mt-8 mb-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
            {product.sku}
          </span>
        </div>

        <h3 className="font-semibold text-gray-900 text-lg leading-snug group-hover:text-green-700 transition-colors">
          {highlightText(product.name, 'name')}
        </h3>
      </div>

      {/* Category and Brand */}
      <div className="flex gap-2 flex-wrap">
        {product.category && (
          <div className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded border border-gray-200">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M17.707 9.293a1 1 0 010 1.414l-7 7a1 1 0 01-1.414 0l-7-7A.997.997 0 012 10V5a3 3 0 013-3h5c.256 0 .512.098.707.293l7 7zM5 6a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
            {highlightText(product.category, 'category')}
          </div>
        )}

        {product.brand && (
          <div className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded border border-blue-200">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
            </svg>
            {product.brand}
          </div>
        )}
      </div>

      {/* Matched fields indicator */}
      {matches.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="text-xs text-gray-500 flex items-center gap-2">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span>
              Coincide en: {matches.map(m => {
                const labels: Record<string, string> = {
                  'name': 'nombre',
                  'sku': 'SKU',
                  'category': 'categoría',
                  'brand': 'marca'
                }
                return labels[m.key || ''] || m.key
              }).join(', ')}
            </span>
          </div>
        </div>
      )}

      {/* Hover indicator */}
      <div className="absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-green-500 to-green-600 opacity-0 group-hover:opacity-100 transition-opacity rounded-b-lg" />
    </div>
  )
}
