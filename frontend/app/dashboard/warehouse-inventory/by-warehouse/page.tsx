'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import Image from 'next/image';
import Navigation from '@/components/Navigation';
import EnhancedWarehouseInventoryTable from '@/components/inventory/EnhancedWarehouseInventoryTable';
import ExpandableProductTable from '@/components/inventory/ExpandableProductTable';
import EnhancedSummaryCard from '@/components/inventory/EnhancedSummaryCard';
import WarehouseCard from '@/components/inventory/WarehouseCard';
import InventoryUploadButton from '@/components/inventory/InventoryUploadButton';

interface Warehouse {
  id: number;
  code: string;
  name: string;
  location: string | null;
  update_method: string;
  is_active: boolean;
}

interface LotInfo {
  lot_number: string;
  quantity: number;
  expiration_date: string | null;
  last_updated: string;
  days_to_expiration?: number | null;
  expiration_status?: 'No Date' | 'Expired' | 'Expiring Soon' | 'Valid';
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

interface WarehouseProduct {
  sku: string;
  name: string;
  category: string | null;
  stock: number;
  lots: LotInfo[];
  percentage_of_warehouse?: number;  // Opcional - solo para vista warehouse-specific
  percentage_of_product?: number;     // Opcional - solo para vista warehouse-specific
  sku_value?: number;  // Unit cost from product_catalog
  valor?: number;      // Total value (stock × sku_value)
}

interface WarehouseSummary {
  total_products: number;
  total_stock: number;
  total_lots: number;
  last_updated: string | null;
  expiration?: ExpirationStats;
  total_valor?: number;
}

interface WarehouseInventoryResponse {
  status: string;
  warehouse: {
    code: string;
    name: string;
    update_method: string;
  };
  data: WarehouseProduct[];
  summary: WarehouseSummary;
}

interface WarehousesResponse {
  status: string;
  data: Warehouse[];
}

export default function WarehouseSpecificInventoryPage() {
  const { data: session, status } = useSession();
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>('');
  const [products, setProducts] = useState<WarehouseProduct[]>([]);
  const [warehouseInfo, setWarehouseInfo] = useState<{ code: string; name: string; update_method: string } | null>(
    null
  );
  const [summary, setSummary] = useState<WarehouseSummary | null>(null);
  const [loading, setLoading] = useState(false); // Don't load by default
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [showOnlyWithStock, setShowOnlyWithStock] = useState(false);

  // Fetch warehouses list
  const fetchWarehouses = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/warehouses`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data: WarehousesResponse = await response.json();
      setWarehouses(data.data);
      // Don't auto-select - user must choose a warehouse
    } catch (err: any) {
      console.error('Error fetching warehouses:', err);
      setError(err.message || 'Error al cargar las bodegas');
    }
  };

  // Fetch warehouse inventory
  const fetchWarehouseInventory = async (showRefreshAnimation = false) => {
    if (!selectedWarehouse) return;

    try {
      if (showRefreshAnimation) setIsRefreshing(true);
      else setLoading(true);

      setError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Build query params
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (showOnlyWithStock) params.append('only_with_stock', 'true');

      // Special case: "amplifica" shows all 4 Amplifica locations in columns
      if (selectedWarehouse === 'amplifica') {
        // Add warehouse_group parameter to filter by Amplifica stock only
        params.append('warehouse_group', 'amplifica');

        const response = await fetch(
          `${apiUrl}/api/v1/warehouse-inventory/general?${params.toString()}`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        setProducts(data.data);
        setWarehouseInfo({ code: 'amplifica', name: 'Amplifica (Todas las sucursales)', update_method: 'manual_upload' });
        setSummary(data.summary);
      } else {
        const response = await fetch(
          `${apiUrl}/api/v1/warehouse-inventory/warehouse/${selectedWarehouse}?${params.toString()}`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: WarehouseInventoryResponse = await response.json();
        setProducts(data.data);
        setWarehouseInfo(data.warehouse);
        setSummary(data.summary);
      }
    } catch (err: any) {
      console.error('Error fetching warehouse inventory:', err);
      setError(err.message || 'Error al cargar el inventario de la bodega');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  // Manual refresh
  const handleRefresh = () => {
    fetchWarehouseInventory(true);
  };

  // Clear all filters
  const handleClearFilters = () => {
    setSearchQuery('');
    setShowOnlyWithStock(false);
  };

  const hasActiveFilters = searchQuery || showOnlyWithStock;

  // Load warehouses on mount
  useEffect(() => {
    if (status === 'authenticated') {
      fetchWarehouses();
    }
  }, [status]);

  // Load inventory when warehouse or filters change
  useEffect(() => {
    if (status === 'authenticated' && selectedWarehouse) {
      fetchWarehouseInventory();
    }
  }, [status, selectedWarehouse, searchQuery, showOnlyWithStock]);

  // Handle auth loading
  if (status === 'loading') {
    return (
      <>
        <Navigation />
        <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando...</p>
        </div>
      </div>
      </>
    );
  }

  if (status === 'unauthenticated') {
    return (
      <>
        <Navigation />
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
      </>
    );
  }

  // Group warehouses by type
  const amplificaWarehouses = warehouses.filter((w) => w.code.startsWith('amplifica'));
  const otherWarehouses = warehouses.filter((w) => !w.code.startsWith('amplifica'));

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-8">
      {/* Header with gradient */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
              <span className="text-4xl">🏢</span>
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                Inventario por Bodega
              </span>
            </h1>
            <p className="text-gray-600 text-lg">Vista específica de stock en cada bodega</p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            {/* Upload Button (only for manual warehouses) */}
            {selectedWarehouse &&
              warehouseInfo &&
              warehouseInfo.update_method === 'manual_upload' &&
              selectedWarehouse !== 'amplifica' && (
                <InventoryUploadButton
                  warehouseCode={selectedWarehouse}
                  warehouseName={warehouseInfo.name}
                  onUploadSuccess={handleRefresh}
                />
              )}

            {/* Refresh Button */}
            <button
              onClick={handleRefresh}
              disabled={isRefreshing || !selectedWarehouse}
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
      </div>

      {/* Compact Warehouse Selector - All warehouses in one row */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <span>Seleccionar Bodega</span>
          </h2>
          {warehouseInfo && (
            <div className="text-xs text-gray-600">
              Mostrando: <span className="font-semibold text-gray-900">{warehouseInfo.name}</span>
            </div>
          )}
        </div>

        {/* All warehouses in a single row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Amplifica group card (consolidated view) */}
          <WarehouseCard
            code="amplifica"
            name="Amplifica"
            location="4 sucursales"
            updateMethod="manual_upload"
            isActive={selectedWarehouse === 'amplifica'}
            onClick={() => setSelectedWarehouse('amplifica')}
          />

          {/* Individual Amplifica warehouses (for manual upload) */}
          {amplificaWarehouses.map((warehouse) => {
            const warehouseStats = summary && selectedWarehouse === warehouse.code
              ? { stockCount: summary.total_stock, productCount: summary.total_products }
              : undefined;

            return (
              <WarehouseCard
                key={warehouse.code}
                code={warehouse.code}
                name={warehouse.name}
                location={warehouse.location}
                updateMethod={warehouse.update_method}
                isActive={selectedWarehouse === warehouse.code}
                onClick={() => setSelectedWarehouse(warehouse.code)}
                stockCount={warehouseStats?.stockCount}
                productCount={warehouseStats?.productCount}
              />
            );
          })}

          {/* Other warehouses */}
          {otherWarehouses.map((warehouse) => {
            const warehouseStats = summary && selectedWarehouse === warehouse.code
              ? { stockCount: summary.total_stock, productCount: summary.total_products }
              : undefined;

            return (
              <WarehouseCard
                key={warehouse.code}
                code={warehouse.code}
                name={warehouse.name}
                location={warehouse.location}
                updateMethod={warehouse.update_method}
                isActive={selectedWarehouse === warehouse.code}
                onClick={() => setSelectedWarehouse(warehouse.code)}
                stockCount={warehouseStats?.stockCount}
                productCount={warehouseStats?.productCount}
              />
            );
          })}
        </div>
      </div>

      {/* Enhanced Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
          <EnhancedSummaryCard
            title="Productos en Bodega"
            value={summary.total_products}
            icon="📦"
            color="purple"
            subtitle="SKUs distintos"
          />
          <EnhancedSummaryCard
            title="Stock Total"
            value={summary.total_stock}
            icon="📊"
            color="blue"
            subtitle="Unidades disponibles"
          />
          <EnhancedSummaryCard
            title="Total Lotes"
            value={summary.total_lots}
            icon="📦"
            color="amber"
            subtitle="Con tracking"
          />
          {summary.total_valor !== undefined && Number(summary.total_valor) > 0 && (
            <EnhancedSummaryCard
              title="Valor Total"
              value={`$${Math.round(Number(summary.total_valor)).toLocaleString('es-CL')}`}
              icon="💰"
              color="green"
              subtitle="Valorización bodega"
            />
          )}
          <EnhancedSummaryCard
            title="Última Actualización"
            value={
              summary.last_updated
                ? new Date(summary.last_updated).toLocaleDateString('es-CL', {
                    day: 'numeric',
                    month: 'short',
                  })
                : 'N/A'
            }
            icon="🕒"
            color="green"
            subtitle={
              summary.last_updated
                ? new Date(summary.last_updated).toLocaleTimeString('es-CL', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : 'No disponible'
            }
          />
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
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6 backdrop-blur-sm bg-opacity-95">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <span>Filtros</span>
          </h2>
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 transition-colors"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Limpiar
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Search */}
          <div className="md:col-span-2">
            <div className="relative">
              <input
                type="text"
                placeholder="Buscar por SKU o nombre..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 pl-9 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              />
              <svg
                className="absolute left-3 top-2.5 w-4 h-4 text-gray-400"
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
                  className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Stock Toggle */}
          <div className="flex items-center">
            <label className="flex items-center gap-2 cursor-pointer bg-gray-50 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors w-full">
              <input
                type="checkbox"
                checked={showOnlyWithStock}
                onChange={(e) => setShowOnlyWithStock(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 transition-all"
              />
              <span className="text-sm font-medium text-gray-700">
                Solo con stock
              </span>
            </label>
          </div>
        </div>

        {/* Active Filters Display */}
        {hasActiveFilters && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-gray-600">Filtros activos:</span>
              {searchQuery && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                  Búsqueda: "{searchQuery}"
                  <button onClick={() => setSearchQuery('')} className="hover:bg-blue-200 rounded-full p-0.5">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              )}
              {showOnlyWithStock && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                  Solo con stock
                  <button onClick={() => setShowOnlyWithStock(false)} className="hover:bg-green-200 rounded-full p-0.5">
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

      {/* Enhanced Inventory Table or empty state */}
      {!selectedWarehouse ? (
        <div className="bg-white rounded-xl border-2 border-dashed border-gray-300 p-12 text-center">
          <div className="text-6xl mb-4">🏢</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Selecciona una bodega</h3>
          <p className="text-gray-600">Elige una bodega arriba para ver su inventario</p>
        </div>
      ) : selectedWarehouse === 'amplifica' ? (
        // Multi-warehouse view: use standard table
        <EnhancedWarehouseInventoryTable
          products={products}
          mode="amplifica"
          loading={loading}
        />
      ) : (
        // Single warehouse view: use expandable table with lot details
        <ExpandableProductTable
          products={products}
          loading={loading}
        />
      )}
    </div>
    </>
  );
}
