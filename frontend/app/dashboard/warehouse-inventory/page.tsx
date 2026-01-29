'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import Navigation from '@/components/Navigation';
import DynamicWarehouseInventoryTable from '@/components/inventory/DynamicWarehouseInventoryTable';
import {
  Package,
  BarChart3,
  DollarSign,
  AlertTriangle,
  RefreshCw,
  Search,
  X,
  Filter,
  ChevronDown,
  Loader2,
  ShieldAlert,
  Clock,
} from 'lucide-react';

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
  min_stock?: number;
  recommended_min_stock?: number;
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
  const [showOnlyWithStock, setShowOnlyWithStock] = useState(true);
  const [showLowStockOnly, setShowLowStockOnly] = useState(false);
  const [minStockSuggestions, setMinStockSuggestions] = useState<Record<string, number>>({});

  // Get unique categories
  const categories = [...new Set(products.map((p) => p.category).filter(Boolean))].sort() as string[];

  // Enrich products with min stock data
  const enrichedProducts = products.map(product => ({
    ...product,
    min_stock: product.min_stock || 0,
    recommended_min_stock: product.recommended_min_stock || minStockSuggestions[product.sku] || 0
  }));

  // Apply client-side filters
  const filteredProducts = enrichedProducts.filter(product => {
    if (showLowStockOnly) {
      const effectiveMinStock = product.min_stock > 0 ? product.min_stock : product.recommended_min_stock;
      return product.stock_total > 0 && effectiveMinStock > 0 && product.stock_total < effectiveMinStock;
    }
    return true;
  });

  // Fetch minimum stock suggestions
  const fetchMinStockSuggestions = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/products/minimum-stock-suggestions`);
      if (!response.ok) return;
      const data = await response.json();
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

  useEffect(() => {
    if (status === 'authenticated') {
      fetchMinStockSuggestions();
    }
  }, [status]);

  useEffect(() => {
    if (status === 'authenticated') {
      fetchInventory();
    }
  }, [status, searchQuery, selectedCategory, showOnlyWithStock]);

  const handleRefresh = () => fetchInventory(true);

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('');
    setShowOnlyWithStock(true);
    setShowLowStockOnly(false);
  };

  const hasActiveFilters = searchQuery || selectedCategory || !showOnlyWithStock || showLowStockOnly;

  // Auth loading state
  if (status === 'loading') {
    return (
      <div className="flex justify-center items-center min-h-screen bg-[var(--background)]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-[var(--primary)] mx-auto mb-4" />
          <p className="text-[var(--foreground-muted)] font-medium">Cargando...</p>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return (
      <div className="p-8">
        <div className="bg-[var(--warning-light)] border-l-4 border-[var(--warning)] p-6 rounded-lg">
          <div className="flex items-center gap-4">
            <ShieldAlert className="w-8 h-8 text-[var(--warning)]" />
            <div>
              <p className="text-lg font-semibold text-[var(--foreground)]">Acceso Restringido</p>
              <p className="text-[var(--foreground-muted)] mt-1">Por favor inicia sesión para ver el inventario.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Calculate alert count
  const alertCount = summary?.expiration
    ? summary.expiration.expired_lots + summary.expiration.expiring_soon_lots
    : 0;

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-[var(--background)] p-6 lg:p-8">
        {/* Header */}
        <header className="mb-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-3xl lg:text-4xl font-bold text-[var(--foreground)] tracking-tight">
                Inventario General
              </h1>
              <p className="text-[var(--foreground-muted)] mt-1">
                Vista consolidada de stock en todas las bodegas
              </p>
            </div>

            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-2 px-4 py-2.5 bg-[var(--surface)] border border-[var(--border)] text-[var(--foreground)] rounded-lg hover:border-[var(--primary)] hover:text-[var(--primary)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-sm"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{isRefreshing ? 'Actualizando...' : 'Actualizar'}</span>
            </button>
          </div>
        </header>

        {/* Metrics Grid - Asymmetric layout with primary metric larger */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-12 gap-4 mb-6">
            {/* Primary Metric - Products with Stock (larger) */}
            <div className="col-span-2 lg:col-span-3 metric-card bg-gradient-to-br from-[var(--surface)] to-[var(--background-subtle)]">
              <div className="flex items-start justify-between">
                <div>
                  <p className="metric-card-label">Productos con Stock</p>
                  <p className="metric-card-value text-3xl mt-1">
                    {summary.products_with_stock.toLocaleString()}
                  </p>
                  {summary.products_without_stock > 0 && (
                    <p className="text-xs text-[var(--warning)] mt-2 font-medium">
                      {summary.products_without_stock} sin stock
                    </p>
                  )}
                </div>
                <div className="w-12 h-12 rounded-xl bg-[var(--primary-light)] flex items-center justify-center">
                  <Package className="w-6 h-6 text-[var(--primary)]" />
                </div>
              </div>
            </div>

            {/* Stock Total */}
            <div className="lg:col-span-3 metric-card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="metric-card-label">Stock Total</p>
                  <p className="metric-card-value mt-1">
                    {summary.total_stock.toLocaleString()}
                  </p>
                  <p className="text-xs text-[var(--foreground-muted)] mt-2">
                    {summary.active_warehouses} {summary.active_warehouses === 1 ? 'bodega' : 'bodegas'}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-[var(--secondary-light)] flex items-center justify-center">
                  <BarChart3 className="w-5 h-5 text-[var(--secondary)]" />
                </div>
              </div>
            </div>

            {/* Inventory Value */}
            <div className="lg:col-span-3 metric-card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="metric-card-label">Valor Inventario</p>
                  <p className="metric-card-value mt-1 text-[var(--success)]">
                    {summary.total_valor && Number(summary.total_valor) > 0
                      ? `$${(Number(summary.total_valor) / 1000000).toFixed(1)}M`
                      : '—'}
                  </p>
                  <p className="text-xs text-[var(--foreground-muted)] mt-2">
                    {summary.total_valor && Number(summary.total_valor) > 0
                      ? `$${Math.round(Number(summary.total_valor)).toLocaleString('es-CL')} CLP`
                      : 'Sin valorizar'}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-[var(--success-light)] flex items-center justify-center">
                  <DollarSign className="w-5 h-5 text-[var(--success)]" />
                </div>
              </div>
            </div>

            {/* Alerts */}
            <div className="lg:col-span-3 metric-card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="metric-card-label">Alertas</p>
                  <p className={`metric-card-value mt-1 ${alertCount > 0 ? 'text-[var(--danger)]' : 'text-[var(--success)]'}`}>
                    {alertCount}
                  </p>
                  <div className="text-xs mt-2 space-y-0.5">
                    {summary.expiration && summary.expiration.expired_lots > 0 && (
                      <p className="text-[var(--danger)] font-medium">{summary.expiration.expired_lots} vencidos</p>
                    )}
                    {summary.expiration && summary.expiration.expiring_soon_lots > 0 && (
                      <p className="text-[var(--warning)] font-medium">{summary.expiration.expiring_soon_lots} por vencer</p>
                    )}
                    {alertCount === 0 && (
                      <p className="text-[var(--success)] font-medium">Sin alertas</p>
                    )}
                  </div>
                </div>
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  alertCount > 0 ? 'bg-[var(--danger-light)]' : 'bg-[var(--success-light)]'
                }`}>
                  {alertCount > 0 ? (
                    <AlertTriangle className="w-5 h-5 text-[var(--danger)]" />
                  ) : (
                    <Clock className="w-5 h-5 text-[var(--success)]" />
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Compact Filter Bar */}
        <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-4 mb-6 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center gap-4">
            {/* Search Input */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--foreground-muted)]" />
              <input
                type="text"
                placeholder="Buscar por SKU o nombre..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-10 py-2.5 text-sm border border-[var(--border)] rounded-lg bg-[var(--surface)] focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary-light)] transition-all outline-none"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--foreground-muted)] hover:text-[var(--foreground)]"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Category Select */}
            <div className="relative min-w-[180px]">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-[var(--border)] rounded-lg bg-[var(--surface)] appearance-none cursor-pointer focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary-light)] transition-all outline-none pr-10"
              >
                <option value="">Todas las familias</option>
                {categories.map((category) => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--foreground-muted)] pointer-events-none" />
            </div>

            {/* Toggle Filters */}
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer px-3 py-2 rounded-lg hover:bg-[var(--background-subtle)] transition-colors">
                <input
                  type="checkbox"
                  checked={showOnlyWithStock}
                  onChange={(e) => setShowOnlyWithStock(e.target.checked)}
                  className="w-4 h-4 rounded border-[var(--border)] text-[var(--primary)] focus:ring-[var(--primary)] cursor-pointer"
                />
                <span className="text-sm font-medium text-[var(--foreground)]">Con stock</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer px-3 py-2 rounded-lg bg-[var(--warning-light)] hover:bg-amber-100 transition-colors">
                <input
                  type="checkbox"
                  checked={showLowStockOnly}
                  onChange={(e) => setShowLowStockOnly(e.target.checked)}
                  className="w-4 h-4 rounded border-amber-300 text-[var(--warning)] focus:ring-[var(--warning)] cursor-pointer"
                />
                <span className="text-sm font-medium text-amber-900">Stock bajo</span>
              </label>
            </div>

            {/* Clear Filters */}
            {hasActiveFilters && (
              <button
                onClick={handleClearFilters}
                className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-[var(--primary)] hover:bg-[var(--primary-light)] rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
                Limpiar
              </button>
            )}
          </div>

          {/* Active Filters Pills */}
          {hasActiveFilters && (
            <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-[var(--border)]">
              <Filter className="w-4 h-4 text-[var(--foreground-muted)]" />
              {searchQuery && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--primary-light)] text-[var(--primary)] rounded-full text-xs font-medium">
                  "{searchQuery}"
                  <button onClick={() => setSearchQuery('')} className="hover:bg-[var(--primary)] hover:text-white rounded-full p-0.5 transition-colors">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )}
              {selectedCategory && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--secondary-light)] text-[var(--secondary)] rounded-full text-xs font-medium">
                  {selectedCategory}
                  <button onClick={() => setSelectedCategory('')} className="hover:bg-[var(--secondary)] hover:text-white rounded-full p-0.5 transition-colors">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )}
              {showOnlyWithStock && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--success-light)] text-[var(--success)] rounded-full text-xs font-medium">
                  Con stock
                </span>
              )}
              {showLowStockOnly && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--warning-light)] text-amber-800 rounded-full text-xs font-medium">
                  Stock bajo
                </span>
              )}
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-[var(--danger-light)] border-l-4 border-[var(--danger)] p-4 mb-6 rounded-lg">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-[var(--danger)]" />
              <div>
                <p className="font-semibold text-[var(--danger)]">Error al cargar datos</p>
                <p className="text-sm text-red-700 mt-0.5">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Inventory Table */}
        <DynamicWarehouseInventoryTable
          products={filteredProducts}
          loading={loading}
          onDataChanged={() => fetchInventory(true)}
        />
      </div>
    </>
  );
}
