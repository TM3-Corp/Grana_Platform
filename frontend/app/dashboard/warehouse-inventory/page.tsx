'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import Navigation from '@/components/Navigation';
import DynamicWarehouseInventoryTable from '@/components/inventory/DynamicWarehouseInventoryTable';
import EnhancedSummaryCard from '@/components/inventory/EnhancedSummaryCard';

interface InventoryProduct {
  sku: string;
  name: string;
  category: string | null;
  subfamily: string | null;
  warehouses: {
    [warehouse_code: string]: number;
  };
  stock_total: number;
  lot_count: number;
  last_updated: string | null;
  sku_value?: number;
  valor?: number;
  min_stock?: number;  // User-editable minimum stock
  recommended_min_stock?: number;  // System-calculated recommendation (based on 6-month sales avg)
}

interface ExpirationStats {
  expired_lots: number;
  expired_units: number;
  expiring_soon_lots: number;
  expiring_soon_units: number;
  valid_lots: number;
  valid_units: number;
  no_date_lots: number;
  no_date_units: number;
}

interface InventorySummary {
  total_products: number;
  total_stock: number;
  products_with_stock: number;
  products_without_stock: number;
  active_warehouses: number;
  expiration?: ExpirationStats;
  total_valor?: number;
}

interface APIResponse {
  status: string;
  data: InventoryProduct[];
  summary: InventorySummary;
}

export default function WarehouseInventoryPage() {
  const { data: session, status } = useSession();
  const [products, setProducts] = useState<InventoryProduct[]>([]);
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [showOnlyWithStock, setShowOnlyWithStock] = useState(true); // ✅ Default to true
  const [showLowStockOnly, setShowLowStockOnly] = useState(false);
  const [minStockSuggestions, setMinStockSuggestions] = useState<Record<string, number>>({});

  // Get unique categories
  const categories = [...new Set(products.map((p) => p.category).filter(Boolean))].sort() as string[];

  // Products now come from API with min_stock and recommended_min_stock
  // Use minStockSuggestions as fallback for recommended_min_stock if not in DB
  const enrichedProducts = products.map(product => ({
    ...product,
    min_stock: product.min_stock || 0,
    recommended_min_stock: product.recommended_min_stock || minStockSuggestions[product.sku] || 0
  }));

  // Apply client-side filters for low stock
  const filteredProducts = enrichedProducts.filter(product => {
    if (showLowStockOnly) {
      // Show products where current stock is below their minimum stock
      // Use user-set min_stock, or fall back to recommended_min_stock
      const effectiveMinStock = product.min_stock > 0 ? product.min_stock : product.recommended_min_stock;
      return product.stock_total > 0 && effectiveMinStock > 0 && product.stock_total < effectiveMinStock;
    }
    return true;
  });

  // Fetch minimum stock suggestions from backend
  const fetchMinStockSuggestions = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/products/minimum-stock-suggestions`);

      if (!response.ok) {
        console.error('Failed to fetch min stock suggestions');
        return;
      }

      const data = await response.json();

      // Convert API response to { SKU: suggested_min_stock } mapping
      const suggestions: Record<string, number> = {};
      Object.keys(data.data).forEach(sku => {
        suggestions[sku] = data.data[sku].suggested_min_stock;
      });

      setMinStockSuggestions(suggestions);
    } catch (err) {
      console.error('Error fetching min stock suggestions:', err);
    }
  };

  // Fetch inventory data
  const fetchInventory = async (showRefreshAnimation = false) => {
    try {
      if (showRefreshAnimation) setIsRefreshing(true);
      else setLoading(true);

      setError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (selectedCategory) params.append('category', selectedCategory);
      if (showOnlyWithStock) params.append('only_with_stock', 'true');

      const response = await fetch(`${apiUrl}/api/v1/warehouse-inventory/general?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: APIResponse = await response.json();
      setProducts(data.data);
      setSummary(data.summary);
    } catch (err: any) {
      console.error('Error fetching inventory:', err);
      setError(err.message || 'Error al cargar el inventario');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  // Fetch minimum stock suggestions once on mount
  useEffect(() => {
    if (status === 'authenticated') {
      fetchMinStockSuggestions();
    }
  }, [status]);

  // Load data on mount and when filters change
  useEffect(() => {
    if (status === 'authenticated') {
      fetchInventory();
    }
  }, [status, searchQuery, selectedCategory, showOnlyWithStock]);

  // Manual refresh
  const handleRefresh = () => {
    fetchInventory(true);
  };

  // Clear all filters
  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('');
    setShowOnlyWithStock(true); // Reset to default (true)
    setShowLowStockOnly(false);
  };

  const hasActiveFilters = searchQuery || selectedCategory || !showOnlyWithStock || showLowStockOnly;

  // Handle auth loading
  if (status === 'loading') {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando...</p>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return (
      <div className="p-8">
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-6 rounded-lg shadow-sm">
          <div className="flex items-center">
            <div className="text-4xl mr-4">⚠️</div>
            <div>
              <p className="text-lg font-semibold text-yellow-800">Acceso Restringido</p>
              <p className="text-yellow-700 mt-1">Por favor inicia sesión para ver el inventario.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-8">
      {/* Header with gradient */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
              <span className="text-4xl">📦</span>
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                Inventario General
              </span>
            </h1>
            <p className="text-gray-600 text-lg">Vista consolidada de stock en todas las bodegas</p>
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-6 py-3 bg-white border-2 border-blue-500 text-blue-600 rounded-xl hover:bg-blue-50 transition-all duration-300 shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            <svg
              className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>{isRefreshing ? 'Actualizando...' : 'Actualizar'}</span>
          </button>
        </div>
      </div>

      {/* Enhanced Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-6 mb-8">
          <EnhancedSummaryCard
            title="Bodegas Activas"
            value={summary.active_warehouses}
            icon="🏢"
            color="blue"
            subtitle="De Relbase"
          />
          <EnhancedSummaryCard
            title="Total Productos"
            value={summary.total_products}
            icon="📦"
            color="purple"
            subtitle="En el sistema"
          />
          <EnhancedSummaryCard
            title="Stock Total"
            value={summary.total_stock}
            icon="📊"
            color="amber"
            subtitle="Unidades disponibles"
          />
          <EnhancedSummaryCard
            title="Con Stock"
            value={summary.products_with_stock}
            icon="✅"
            color="green"
            subtitle={`${summary.total_products > 0 ? ((summary.products_with_stock / summary.total_products) * 100).toFixed(1) : 0}% del total`}
          />
          <EnhancedSummaryCard
            title="Sin Stock"
            value={summary.products_without_stock}
            icon="⚠️"
            color="gray"
            subtitle={`${summary.total_products > 0 ? ((summary.products_without_stock / summary.total_products) * 100).toFixed(1) : 0}% del total`}
          />
          {summary.total_valor !== undefined && Number(summary.total_valor) > 0 && (
            <EnhancedSummaryCard
              title="Valor Total Inventario"
              value={`$${Math.round(Number(summary.total_valor)).toLocaleString('es-CL')}`}
              icon="💰"
              color="green"
              subtitle="Valorización total"
            />
          )}
          {summary.expiration && (
            <>
              <EnhancedSummaryCard
                title="Próximos a Vencer"
                value={summary.expiration.expiring_soon_lots}
                icon="⏰"
                color="amber"
                subtitle={`${summary.expiration.expiring_soon_units.toLocaleString()} unidades (30 días)`}
              />
              <EnhancedSummaryCard
                title="Vencidos"
                value={summary.expiration.expired_lots}
                icon="❌"
                color="red"
                subtitle={`${summary.expiration.expired_units.toLocaleString()} unidades`}
              />
            </>
          )}
        </div>
      )}

      {/* Enhanced Filters */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 mb-8 backdrop-blur-sm bg-opacity-95">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-md">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <span>Filtros</span>
          </h2>
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Limpiar todo
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Search */}
          <div className="lg:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Buscar Producto
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="SKU o nombre del producto..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-3 pl-10 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              />
              <svg
                className="absolute left-3 top-3.5 w-5 h-5 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-3.5 text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Category Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Familia
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all appearance-none bg-white"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
                backgroundPosition: 'right 0.5rem center',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '1.5em 1.5em',
              }}
            >
              <option value="">Todas las familias</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>

          {/* Stock Toggle */}
          <div className="flex items-end">
            <label className="flex items-center gap-3 cursor-pointer bg-gray-50 px-4 py-3 rounded-xl hover:bg-gray-100 transition-colors w-full">
              <input
                type="checkbox"
                checked={showOnlyWithStock}
                onChange={(e) => setShowOnlyWithStock(e.target.checked)}
                className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 transition-all"
              />
              <span className="text-sm font-medium text-gray-700">
                Solo con stock
              </span>
            </label>
          </div>
        </div>

        {/* Second Row - Low Stock Filter */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
          {/* Low Stock Toggle */}
          <div className="flex items-center">
            <label className="flex items-center gap-3 cursor-pointer bg-amber-50 px-4 py-3 rounded-xl hover:bg-amber-100 transition-colors w-full border-2 border-amber-200">
              <input
                type="checkbox"
                checked={showLowStockOnly}
                onChange={(e) => setShowLowStockOnly(e.target.checked)}
                className="w-5 h-5 text-amber-600 border-amber-300 rounded focus:ring-amber-500 transition-all"
              />
              <span className="text-sm font-medium text-amber-900 flex items-center gap-2">
                <span>⚠️</span>
                <span>Stock bajo (por producto)</span>
              </span>
            </label>
          </div>
        </div>

        {/* Active Filters Display */}
        {hasActiveFilters && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-gray-600">Filtros activos:</span>
              {searchQuery && (
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                  Búsqueda: "{searchQuery}"
                  <button onClick={() => setSearchQuery('')} className="hover:bg-blue-200 rounded-full p-0.5">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              )}
              {selectedCategory && (
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                  Familia: {selectedCategory}
                  <button onClick={() => setSelectedCategory('')} className="hover:bg-purple-200 rounded-full p-0.5">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              )}
              {showOnlyWithStock && (
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                  Solo con stock
                  <button onClick={() => setShowOnlyWithStock(false)} className="hover:bg-green-200 rounded-full p-0.5">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              )}
              {showLowStockOnly && (
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-amber-100 text-amber-700 rounded-full text-sm font-medium">
                  ⚠️ Stock bajo
                  <button onClick={() => setShowLowStockOnly(false)} className="hover:bg-amber-200 rounded-full p-0.5">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-6 mb-8 rounded-lg shadow-sm">
          <div className="flex items-center">
            <div className="text-4xl mr-4">❌</div>
            <div>
              <p className="text-lg font-semibold text-red-800">Error al cargar datos</p>
              <p className="text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Dynamic Inventory Table (Relbase Warehouses) */}
      <DynamicWarehouseInventoryTable
        products={filteredProducts}
        loading={loading}
        onDataChanged={() => fetchInventory(true)}
      />
    </div>
    </>
  );
}
