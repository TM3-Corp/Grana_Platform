'use client';

import React, { useState } from 'react';
import Navigation from '@/components/Navigation';
import ConsolidatedInventoryTable from '@/components/product-mapping/ConsolidatedInventoryTable';
import ProductFamilyView from '@/components/product-mapping/ProductFamilyView';
import ChannelEquivalentsView from '@/components/product-mapping/ChannelEquivalentsView';
import AllProductsTable from '@/components/product-mapping/AllProductsTable';
import InventoryUpdater from '@/components/inventory/InventoryUpdater';
import { ProductProvider } from '@/contexts/ProductContext';

type ViewMode = 'consolidated' | 'families' | 'channel-equivalents' | 'all-products' | 'updater';

export default function ProductMappingPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('consolidated');

  return (
    <>
      <Navigation />
      <ProductProvider>
        <div className="min-h-screen bg-gray-50 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Mapeo de Productos</h1>
            <p className="text-gray-600">
              Inventario consolidado y familias de productos con mapeo de variantes
            </p>
          </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex items-start gap-3">
          <span className="text-2xl">💡</span>
          <div>
            <h3 className="font-semibold text-blue-900 mb-1">Sistema de Mapeo de Productos</h3>
            <p className="text-sm text-blue-700">
              Este sistema consolida el inventario real considerando todas las variantes de packaging
              (displays de 5, 16 unidades, etc.) y equivalencias entre canales (Shopify ↔ MercadoLibre).
            </p>
          </div>
        </div>
      </div>

      {/* View Selector */}
      <div className="flex gap-2 mb-6 border-b">
        <button
          onClick={() => setViewMode('consolidated')}
          className={`px-6 py-3 font-medium transition-colors ${
            viewMode === 'consolidated'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          📊 Inventario Consolidado
        </button>
        <button
          onClick={() => setViewMode('families')}
          className={`px-6 py-3 font-medium transition-colors ${
            viewMode === 'families'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          🏠 Familias de Productos
        </button>
        <button
          onClick={() => setViewMode('channel-equivalents')}
          className={`px-6 py-3 font-medium transition-colors ${
            viewMode === 'channel-equivalents'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          🔄 Equivalencias Cross-Canal
        </button>
        <button
          onClick={() => setViewMode('all-products')}
          className={`px-6 py-3 font-medium transition-colors ${
            viewMode === 'all-products'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          🏷️ Productos
        </button>
        <button
          onClick={() => setViewMode('updater')}
          className={`px-6 py-3 font-medium transition-colors ${
            viewMode === 'updater'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          🔄 Actualización
        </button>
      </div>

      {/* Content */}
      <div>
        {viewMode === 'consolidated' && (
          <div>
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-gray-900 mb-1">Inventario Consolidado</h2>
              <p className="text-sm text-gray-600">
                Stock real en unidades base, considerando todas las variantes de packaging
              </p>
            </div>
            <ConsolidatedInventoryTable />
          </div>
        )}

        {viewMode === 'families' && (
          <div>
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-gray-900 mb-1">Familias de Productos</h2>
              <p className="text-sm text-gray-600">
                Visualiza las relaciones de packaging y descuentos por volumen
              </p>
            </div>
            <ProductFamilyView />
          </div>
        )}

        {viewMode === 'channel-equivalents' && (
          <div>
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-gray-900 mb-1">Equivalencias Cross-Canal</h2>
              <p className="text-sm text-gray-600">
                Mismo producto en Shopify y MercadoLibre - Compara precios y stock entre canales
              </p>
            </div>
            <ChannelEquivalentsView />
          </div>
        )}

        {viewMode === 'all-products' && (
          <div>
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-gray-900 mb-1">Todos los Productos</h2>
              <p className="text-sm text-gray-600">
                Catálogo completo del inventario - Todas las variantes y productos individuales
              </p>
            </div>
            <AllProductsTable />
          </div>
        )}

        {viewMode === 'updater' && (
          <div>
            <InventoryUpdater />
          </div>
        )}
      </div>

      {/* Help Section */}
      <div className="mt-8 bg-gray-50 border rounded-lg p-6">
        <h3 className="font-semibold text-gray-900 mb-3">📚 Cómo funciona el sistema</h3>
        <div className="grid md:grid-cols-3 gap-6 text-sm text-gray-700">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Inventario Consolidado</h4>
            <ul className="space-y-1 list-disc list-inside">
              <li>
                <strong>Stock Directo:</strong> Unidades individuales en inventario
              </li>
              <li>
                <strong>Stock Variantes:</strong> Unidades convertidas desde displays/packs
              </li>
              <li>
                <strong>Total Real:</strong> Suma de ambos = inventario real disponible
              </li>
              <li>
                <strong className="text-red-600">Sobreventa:</strong> Total negativo = más ventas que stock
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Familias de Productos</h4>
            <ul className="space-y-1 list-disc list-inside">
              <li>
                <strong>Producto Base:</strong> Unidad individual (1 unidad)
              </li>
              <li>
                <strong>Variantes:</strong> Displays de 5, 16 unidades, packs, etc.
              </li>
              <li>
                <strong>Equivalencia:</strong> Cuántas unidades base tiene cada variante
              </li>
              <li>
                <strong>Descuento:</strong> Ahorro al comprar variante vs unidades sueltas
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Equivalencias Cross-Canal</h4>
            <ul className="space-y-1 list-disc list-inside">
              <li>
                <strong>Mismo Producto:</strong> En Shopify y MercadoLibre
              </li>
              <li>
                <strong>Comparación de Precios:</strong> Detecta diferencias entre canales
              </li>
              <li>
                <strong>Stock Total:</strong> Suma el stock de ambos canales
              </li>
              <li>
                <strong>Confianza:</strong> Score automático de la equivalencia
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded">
          <h4 className="font-medium text-yellow-900 mb-2">⚠️ Ejemplo de Problema Detectado</h4>
          <p className="text-sm text-yellow-700">
            <strong>BAKC (Keto Nuez):</strong> Stock directo 343 unidades + Display 5 (50×5=250 unidades) -
            Display 16 (-56×16=-896 unidades) = <strong className="text-red-600">-303 unidades SOBREVENDIDAS</strong>
          </p>
          <p className="text-xs text-yellow-600 mt-2">
            Este sistema te alerta sobre estos casos para tomar acción inmediata.
          </p>
        </div>
      </div>
          </div>
        </div>
      </ProductProvider>
    </>
  );
}
