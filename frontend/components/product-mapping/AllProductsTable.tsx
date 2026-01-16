'use client';

import React, { useState, useEffect } from 'react';
import { filterValidProducts, type Product as BaseProduct } from '@/lib/product-utils';

interface Product extends BaseProduct {
  units_per_display: number | null;
  displays_per_box: number | null;
  boxes_per_pallet: number | null;
}

interface ProductsResponse {
  status: string;
  total: number;
  count: number;
  data: Product[];
}

export default function AllProductsTable() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState<string>('');

  useEffect(() => {
    fetchProducts();
  }, [sourceFilter]);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';

      const params = new URLSearchParams({
        limit: '1000',
        offset: '0'
      });

      if (sourceFilter) {
        params.append('source', sourceFilter);
      }

      const fullUrl = `${apiUrl}/api/v1/products/?${params}`;
      const response = await fetch(fullUrl);

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data: ProductsResponse = await response.json();
      // Filter out obsolete ML products
      const validProducts = filterValidProducts(data.data);
      setProducts(validProducts);
      setFilteredProducts(validProducts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  // Client-side search filter
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredProducts(products);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = products.filter(p =>
      p.name.toLowerCase().includes(query) ||
      p.sku.toLowerCase().includes(query) ||
      p.category?.toLowerCase().includes(query) ||
      p.brand?.toLowerCase().includes(query)
    );
    setFilteredProducts(filtered);
  }, [searchQuery, products]);

  const getStockStatus = (product: Product) => {
    if (product.current_stock === null) return { label: 'Sin datos', color: 'gray' };
    if (product.min_stock === null) return { label: 'OK', color: 'green' };
    if (product.current_stock <= product.min_stock) return { label: 'Bajo', color: 'red' };
    if (product.current_stock <= product.min_stock * 1.5) return { label: 'Alerta', color: 'yellow' };
    return { label: 'OK', color: 'green' };
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center p-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">❌ {error}</p>
      </div>
    );
  }

  const sources = ['shopify', 'mercadolibre', 'manual'];

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Total Productos</div>
          <div className="text-2xl font-bold text-gray-900">{products.length}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Shopify</div>
          <div className="text-2xl font-bold text-blue-600">
            {products.filter(p => p.source === 'shopify').length}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">MercadoLibre</div>
          <div className="text-2xl font-bold text-yellow-600">
            {products.filter(p => p.source === 'mercadolibre').length}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-600 mb-1">Stock Bajo</div>
          <div className="text-2xl font-bold text-red-600">
            {products.filter(p => {
              const status = getStockStatus(p);
              return status.color === 'red' || status.color === 'yellow';
            }).length}
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search Bar */}
          <div className="flex-1">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Buscar por nombre, SKU, categoría o marca..."
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Source Filter */}
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
          >
            <option value="">Todas las fuentes</option>
            {sources.map(source => (
              <option key={source} value={source}>
                {source === 'shopify' ? '🛍️ Shopify' :
                 source === 'mercadolibre' ? '🛒 MercadoLibre' :
                 source === 'manual' ? '✏️ Manual' : source}
              </option>
            ))}
          </select>
        </div>

        {/* Search Results Count */}
        {searchQuery && (
          <div className="mt-3 text-sm text-gray-600">
            {filteredProducts.length} resultado{filteredProducts.length !== 1 ? 's' : ''} encontrado{filteredProducts.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Products Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Producto
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Categoría
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Fuente
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Precio
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Stock
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Packaging
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredProducts.map((product) => {
                const stockStatus = getStockStatus(product);
                const hasPackaging = product.units_per_display || product.displays_per_box || product.boxes_per_pallet;

                return (
                  <tr key={product.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <div className="text-sm font-medium text-gray-900">{product.name}</div>
                        <div className="text-xs text-gray-500">{product.sku}</div>
                        {product.brand && (
                          <div className="text-xs text-gray-400 mt-1">Marca: {product.brand}</div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {product.category || 'Sin categoría'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-purple-100 text-purple-800 capitalize">
                        {product.source === 'shopify' ? '🛍️ Shopify' : product.source}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="text-sm font-bold text-green-600">
                        {product.sale_price !== null
                          ? `$${product.sale_price.toLocaleString('es-CL')}`
                          : 'N/A'
                        }
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="text-sm text-gray-900">
                        {product.current_stock !== null ? product.current_stock : 'N/A'}
                      </div>
                      {product.min_stock !== null && (
                        <div className="text-xs text-gray-500">
                          Min: {product.min_stock}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className={`
                        inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${stockStatus.color === 'green' ? 'bg-green-100 text-green-800' :
                          stockStatus.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                          stockStatus.color === 'red' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'}
                      `}>
                        {stockStatus.label}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-xs text-gray-600">
                      {hasPackaging ? (
                        <div className="space-y-1">
                          {product.units_per_display && (
                            <div>{product.units_per_display} u/display</div>
                          )}
                          {product.displays_per_box && (
                            <div>{product.displays_per_box} disp/caja</div>
                          )}
                          {product.boxes_per_pallet && (
                            <div>{product.boxes_per_pallet} cajas/pallet</div>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Empty State */}
      {filteredProducts.length === 0 && !loading && (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No se encontraron productos</h3>
          <p className="mt-1 text-sm text-gray-500">
            {searchQuery ? 'Intenta con otros términos de búsqueda' : 'Intenta con otros filtros'}
          </p>
        </div>
      )}
    </div>
  );
}
