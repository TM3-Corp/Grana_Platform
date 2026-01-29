'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import Image from 'next/image';
import Navigation from '@/components/Navigation';
import ExpandableProductTable from '@/components/inventory/ExpandableProductTable';
import EnhancedSummaryCard from '@/components/inventory/EnhancedSummaryCard';
import WarehouseCard from '@/components/inventory/WarehouseCard';
import InventoryUploadButton from '@/components/inventory/InventoryUploadButton';
import {
  Building2,
  RefreshCw,
  Search,
  X,
  Filter,
  Loader2,
  ShieldAlert,
  Package,
  AlertTriangle,
} from 'lucide-react';

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
  percentage_of_warehouse?: number;
  percentage_of_product?: number;
  sku_value?: number;
  valor?: number;
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

interface WarehouseExpirationSummary {
  [warehouseCode: string]: {
    expired_lots: number;
    expired_units: number;
    expiring_soon_lots: number;
    expiring_soon_units: number;
    valid_lots: number;
    valid_units: number;
    earliest_expiration: string | null;
    days_to_earliest: number | null;
  };
}

export default function WarehouseSpecificInventoryPage() {
  const { data: session, status } = useSession();
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>('');
  const [products, setProducts] = useState<WarehouseProduct[]>([]);
  const [warehouseInfo, setWarehouseInfo] = useState<{ code: string; name: string; update_method: string } | null>(null);
  const [summary, setSummary] = useState<WarehouseSummary | null>(null);
  const [expirationSummary, setExpirationSummary] = useState<WarehouseExpirationSummary>({});
  const [loading, setLoading] = useState(false);
  const [warehousesLoading, setWarehousesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [showOnlyWithStock, setShowOnlyWithStock] = useState(false);

  // Fetch warehouses list and expiration summary
  const fetchWarehouses = async () => {
    try {
      setWarehousesLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const [warehousesResponse, expirationResponse] = await Promise.all([
        fetch(`${apiUrl}/api/v1/warehouses`),
        fetch(`${apiUrl}/api/v1/warehouse-inventory/expiration-summary`)
      ]);

      if (!warehousesResponse.ok) {
        throw new Error(`HTTP ${warehousesResponse.status}: ${warehousesResponse.statusText}`);
      }

      const warehousesData: WarehousesResponse = await warehousesResponse.json();
      setWarehouses(warehousesData.data);

      if (expirationResponse.ok) {
        const expirationData = await expirationResponse.json();
        setExpirationSummary(expirationData.data || {});
      }
    } catch (err: any) {
      console.error('Error fetching warehouses:', err);
      setError(err.message || 'Error al cargar las bodegas');
    } finally {
      setWarehousesLoading(false);
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

      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (showOnlyWithStock) params.append('only_with_stock', 'true');

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
    } catch (err: any) {
      console.error('Error fetching warehouse inventory:', err);
      setError(err.message || 'Error al cargar el inventario de la bodega');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleRefresh = () => fetchWarehouseInventory(true);

  const handleClearFilters = () => {
    setSearchQuery('');
    setShowOnlyWithStock(false);
  };

  const hasActiveFilters = searchQuery || showOnlyWithStock;

  useEffect(() => {
    if (status === 'authenticated') {
      fetchWarehouses();
    }
  }, [status]);

  useEffect(() => {
    if (status === 'authenticated' && selectedWarehouse) {
      fetchWarehouseInventory();
    }
  }, [status, selectedWarehouse, searchQuery, showOnlyWithStock]);

  // Auth loading state
  if (status === 'loading') {
    return (
      <>
        <Navigation />
        <div className="flex justify-center items-center min-h-screen bg-[var(--background)]">
          <div className="text-center">
            <Loader2 className="w-12 h-12 animate-spin text-[var(--primary)] mx-auto mb-4" />
            <p className="text-[var(--foreground-muted)] font-medium">Cargando...</p>
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
      </>
    );
  }

  const amplificaWarehouses = warehouses.filter((w) => w.code.startsWith('amplifica'));
  const otherWarehouses = warehouses.filter((w) => !w.code.startsWith('amplifica'));

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-[var(--background)] p-6 lg:p-8">
        {/* Header */}
        <header className="mb-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-3xl lg:text-4xl font-bold text-[var(--foreground)] tracking-tight">
                Inventario por Bodega
              </h1>
              <p className="text-[var(--foreground-muted)] mt-1">
                Vista específica de stock en cada bodega
              </p>
            </div>

            <div className="flex items-center gap-3">
              {/* Upload Button */}
              {selectedWarehouse && warehouseInfo && warehouseInfo.update_method === 'manual_upload' && (
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
                className="flex items-center gap-2 px-4 py-2.5 bg-[var(--surface)] border border-[var(--border)] text-[var(--foreground)] rounded-lg hover:border-[var(--primary)] hover:text-[var(--primary)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-sm"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">{isRefreshing ? 'Actualizando...' : 'Actualizar'}</span>
              </button>
            </div>
          </div>
        </header>

        {/* Warehouse Selector */}
        <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-4 mb-6 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-[var(--foreground)] flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
                <Building2 className="w-4 h-4 text-[var(--primary)]" />
              </div>
              <span>Seleccionar Bodega</span>
            </h2>
            {warehouseInfo && (
              <div className="text-xs text-[var(--foreground-muted)]">
                Activa: <span className="font-semibold text-[var(--foreground)]">{warehouseInfo.name}</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {warehousesLoading && (
              <div className="col-span-full flex items-center justify-center py-8">
                <div className="flex items-center gap-3 text-[var(--foreground-muted)]">
                  <Loader2 className="w-5 h-5 animate-spin text-[var(--primary)]" />
                  <span>Cargando bodegas...</span>
                </div>
              </div>
            )}

            {!warehousesLoading && warehouses.length === 0 && (
              <div className="col-span-full flex flex-col items-center justify-center py-8 text-[var(--foreground-muted)]">
                <Building2 className="w-10 h-10 mb-2 text-stone-300" />
                <span>No hay bodegas disponibles</span>
              </div>
            )}

            {!warehousesLoading && amplificaWarehouses.map((warehouse) => {
              const warehouseStats = summary && selectedWarehouse === warehouse.code
                ? { stockCount: summary.total_stock, productCount: summary.total_products }
                : undefined;
              const expStats = expirationSummary[warehouse.code];

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
                  expirationSummary={expStats ? {
                    expired_lots: expStats.expired_lots,
                    expired_units: expStats.expired_units,
                    expiring_soon_lots: expStats.expiring_soon_lots,
                    expiring_soon_units: expStats.expiring_soon_units,
                    earliest_expiration: expStats.earliest_expiration
                  } : undefined}
                />
              );
            })}

            {!warehousesLoading && otherWarehouses.map((warehouse) => {
              const warehouseStats = summary && selectedWarehouse === warehouse.code
                ? { stockCount: summary.total_stock, productCount: summary.total_products }
                : undefined;
              const expStats = expirationSummary[warehouse.code];

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
                  expirationSummary={expStats ? {
                    expired_lots: expStats.expired_lots,
                    expired_units: expStats.expired_units,
                    expiring_soon_lots: expStats.expiring_soon_lots,
                    expiring_soon_units: expStats.expiring_soon_units,
                    earliest_expiration: expStats.earliest_expiration
                  } : undefined}
                />
              );
            })}
          </div>
        </div>

        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            <EnhancedSummaryCard
              title="Productos"
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
              subtitle="Unidades"
            />
            <EnhancedSummaryCard
              title="Lotes"
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
                subtitle="Valorización"
              />
            )}
            <EnhancedSummaryCard
              title="Actualización"
              value={
                summary.last_updated
                  ? new Date(summary.last_updated).toLocaleDateString('es-CL', {
                      day: 'numeric',
                      month: 'short',
                    })
                  : 'N/A'
              }
              icon="🕒"
              color="gray"
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
                {(summary.expiration.expiring_soon_lots > 0 || summary.expiration.expired_lots > 0) && (
                  <>
                    <EnhancedSummaryCard
                      title="Por Vencer"
                      value={summary.expiration.expiring_soon_lots}
                      icon="⏰"
                      color="amber"
                      subtitle={`${summary.expiration.expiring_soon_units.toLocaleString()} uds (30d)`}
                    />
                    <EnhancedSummaryCard
                      title="Vencidos"
                      value={summary.expiration.expired_lots}
                      icon="❌"
                      color="red"
                      subtitle={`${summary.expiration.expired_units.toLocaleString()} uds`}
                    />
                  </>
                )}
              </>
            )}
          </div>
        )}

        {/* Filters */}
        <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-4 mb-6 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center gap-4">
            {/* Search */}
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

            {/* Stock Toggle */}
            <label className="flex items-center gap-2 cursor-pointer px-3 py-2 rounded-lg hover:bg-[var(--background-subtle)] transition-colors">
              <input
                type="checkbox"
                checked={showOnlyWithStock}
                onChange={(e) => setShowOnlyWithStock(e.target.checked)}
                className="w-4 h-4 rounded border-[var(--border)] text-[var(--primary)] focus:ring-[var(--primary)] cursor-pointer"
              />
              <span className="text-sm font-medium text-[var(--foreground)]">Solo con stock</span>
            </label>

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

          {/* Active Filters */}
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
              {showOnlyWithStock && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--success-light)] text-[var(--success)] rounded-full text-xs font-medium">
                  Con stock
                </span>
              )}
            </div>
          )}
        </div>

        {/* Error */}
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

        {/* Content */}
        {!selectedWarehouse ? (
          <div className="bg-[var(--surface)] rounded-xl border-2 border-dashed border-[var(--border)] p-12 text-center">
            <Building2 className="w-16 h-16 text-stone-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-[var(--foreground)] mb-2">Selecciona una bodega</h3>
            <p className="text-[var(--foreground-muted)]">Elige una bodega arriba para ver su inventario</p>
          </div>
        ) : (
          <ExpandableProductTable
            products={products}
            loading={loading}
          />
        )}
      </div>
    </>
  );
}
