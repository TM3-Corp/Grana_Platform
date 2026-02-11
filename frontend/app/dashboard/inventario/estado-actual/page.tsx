'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useSession } from 'next-auth/react';
import Navigation from '@/components/Navigation';
import { formatCurrencyFull } from '@/lib/utils';
import { useSpatialZoom } from '@/lib/use-spatial-zoom';
import SpatialBreadcrumb from '@/components/inventory/SpatialBreadcrumb';
import SpatialWarehouseGrid from '@/components/inventory/SpatialWarehouseGrid';
import SpatialProductList from '@/components/inventory/SpatialProductList';
import SpatialLotDetail from '@/components/inventory/SpatialLotDetail';
import {
  Package,
  DollarSign,
  AlertTriangle,
  RefreshCw,
  Loader2,
  ShieldAlert,
  Boxes,
} from 'lucide-react';

// =============================================================================
// Types
// =============================================================================

interface WarehouseInfo {
  id: number;
  code: string;
  name: string;
  location: string | null;
  update_method: string;
  is_active: boolean;
}

interface LotInfo {
  lot_number: string | null;
  quantity: number;
  expiration_date: string | null;
  last_updated: string;
  days_to_expiration?: number | null;
  expiration_status?: 'No Date' | 'Expired' | 'Expiring Soon' | 'Valid';
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

interface InventoryProduct {
  sku: string;
  name: string;
  category: string | null;
  warehouses: { [code: string]: number };
  stock_total: number;
  lot_count: number;
  last_updated: string | null;
  sku_value?: number;
  valor?: number;
}

interface ExpirationStats {
  expired_lots: number;
  expired_units: number;
  expiring_soon_lots: number;
  expiring_soon_units: number;
  valid_lots: number;
  valid_units: number;
  no_date_lots?: number;
  no_date_units?: number;
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

interface WarehouseExpirationData {
  expired_lots: number;
  expired_units: number;
  expiring_soon_lots: number;
  expiring_soon_units: number;
  valid_lots: number;
  valid_units: number;
  earliest_expiration: string | null;
  days_to_earliest: number | null;
}

interface WarehouseSummary {
  total_products: number;
  total_stock: number;
  total_lots: number;
  last_updated: string | null;
  expiration?: ExpirationStats;
  total_valor?: number;
}

// =============================================================================
// Component
// =============================================================================

export default function EstadoActualPage() {
  const { data: session, status: authStatus } = useSession();
  const { state: zoom, zoomIntoWarehouse, zoomIntoProduct, zoomOut, zoomToLevel, animationClass, breadcrumbs } = useSpatialZoom();

  // Level 0 data
  const [warehouses, setWarehouses] = useState<WarehouseInfo[]>([]);
  const [products, setProducts] = useState<InventoryProduct[]>([]);
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [warehouseExpiration, setWarehouseExpiration] = useState<Record<string, WarehouseExpirationData>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Level 1 data
  const [warehouseProducts, setWarehouseProducts] = useState<WarehouseProduct[]>([]);
  const [warehouseSummary, setWarehouseSummary] = useState<WarehouseSummary | null>(null);
  const [warehouseLoading, setWarehouseLoading] = useState(false);

  // Level 2 — derived from Level 1
  const selectedProduct = useMemo(() => {
    if (zoom.level !== 2 || !zoom.productSku) return null;
    return warehouseProducts.find(p => p.sku === zoom.productSku) ?? null;
  }, [zoom.level, zoom.productSku, warehouseProducts]);

  // ─── Fetchers ─────────────────────────────────────────────────────────────

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchLevel0 = async () => {
    setLoading(true);
    setError(null);
    try {
      const [whRes, expRes, invRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/warehouses`),
        fetch(`${apiUrl}/api/v1/warehouse-inventory/expiration-summary`),
        fetch(`${apiUrl}/api/v1/warehouse-inventory/general?only_with_stock=true`),
      ]);

      if (whRes.ok) {
        const d = await whRes.json();
        setWarehouses(d.data || []);
      }
      if (expRes.ok) {
        const d = await expRes.json();
        setWarehouseExpiration(d.data || {});
      }
      if (!invRes.ok) throw new Error('Error al cargar inventario');
      const invData = await invRes.json();
      setProducts(invData.data || []);
      setSummary(invData.summary || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const fetchLevel1 = async (code: string) => {
    setWarehouseLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/warehouse-inventory/warehouse/${encodeURIComponent(code)}`);
      if (!res.ok) throw new Error('Error al cargar bodega');
      const data = await res.json();
      setWarehouseProducts(data.data || []);
      setWarehouseSummary(data.summary || null);
    } catch (err) {
      console.error('Error fetching warehouse:', err);
      setWarehouseProducts([]);
      setWarehouseSummary(null);
    } finally {
      setWarehouseLoading(false);
    }
  };

  // ─── Effects ──────────────────────────────────────────────────────────────

  useEffect(() => {
    if (authStatus === 'authenticated') {
      fetchLevel0();
    }
  }, [authStatus]);

  useEffect(() => {
    if (zoom.warehouseCode && zoom.level >= 1) {
      fetchLevel1(zoom.warehouseCode);
    }
  }, [zoom.warehouseCode]);

  // ─── Auth guards ──────────────────────────────────────────────────────────

  if (authStatus === 'loading') {
    return (
      <div className="flex justify-center items-center min-h-screen bg-[var(--background)]">
        <Loader2 className="w-12 h-12 animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  if (authStatus === 'unauthenticated') {
    return (
      <div className="p-8">
        <div className="bg-amber-50 border-l-4 border-amber-500 p-6 rounded-lg">
          <div className="flex items-center gap-4">
            <ShieldAlert className="w-8 h-8 text-amber-500" />
            <div>
              <p className="font-semibold">Acceso Restringido</p>
              <p className="text-gray-600">Por favor inicia sesion para ver el inventario.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ─── KPI helpers ──────────────────────────────────────────────────────────

  const alertCount = summary?.expiration
    ? (summary.expiration.expired_lots || 0) + (summary.expiration.expiring_soon_lots || 0)
    : 0;

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-b from-[var(--background)] to-[var(--background-subtle)]">
        <div className="p-6 max-w-[1800px] mx-auto">

          {/* Page Header */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2.5 bg-[var(--primary)] rounded-xl">
                <Boxes className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-[var(--foreground)] tracking-tight">
                  Estado Actual del Inventario
                </h1>
                <p className="text-[var(--foreground-muted)] text-sm">
                  Vista consolidada de stock por bodega con detalle de lotes
                </p>
              </div>
            </div>
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-24">
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-12 h-12 animate-spin text-[var(--primary)]" />
                <p className="text-[var(--foreground-muted)] font-medium">Cargando inventario...</p>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-red-600" />
                <div>
                  <h3 className="font-semibold text-red-800">Error al cargar datos</h3>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
                <button
                  onClick={fetchLevel0}
                  className="ml-auto px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700"
                >
                  Reintentar
                </button>
              </div>
            </div>
          )}

          {/* Main Content */}
          {!loading && summary && (
            <>
              {/* Company-wide KPIs — Level 0 only */}
              {zoom.level === 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-5 shadow-sm">
                    <div className="p-2.5 bg-blue-100 rounded-xl w-fit mb-3">
                      <Package className="w-5 h-5 text-blue-600" />
                    </div>
                    <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1">Productos con Stock</p>
                    <p className="text-2xl font-bold text-[var(--foreground)]">
                      {summary.products_with_stock}
                      <span className="text-base font-normal text-stone-400 ml-1">/ {summary.total_products}</span>
                    </p>
                  </div>

                  <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-5 shadow-sm">
                    <div className="p-2.5 bg-emerald-100 rounded-xl w-fit mb-3">
                      <Boxes className="w-5 h-5 text-emerald-600" />
                    </div>
                    <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1">Stock Total</p>
                    <p className="text-2xl font-bold text-[var(--foreground)]">{summary.total_stock.toLocaleString('es-CL')}</p>
                    <p className="text-xs text-stone-400 mt-1">unidades en {summary.active_warehouses} bodegas</p>
                  </div>

                  <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-5 shadow-sm">
                    <div className="p-2.5 bg-purple-100 rounded-xl w-fit mb-3">
                      <DollarSign className="w-5 h-5 text-purple-600" />
                    </div>
                    <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1">Valor Inventario</p>
                    <p className="text-2xl font-bold text-[var(--foreground)]">{formatCurrencyFull(summary.total_valor || 0)}</p>
                  </div>

                  <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-5 shadow-sm">
                    <div className={`p-2.5 rounded-xl w-fit mb-3 ${alertCount > 0 ? 'bg-red-100' : 'bg-green-100'}`}>
                      <AlertTriangle className={`w-5 h-5 ${alertCount > 0 ? 'text-red-600' : 'text-green-600'}`} />
                    </div>
                    <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1">Alertas de Vencimiento</p>
                    <p className={`text-2xl font-bold ${alertCount > 0 ? 'text-red-600' : 'text-green-600'}`}>{alertCount}</p>
                    {summary.expiration && (
                      <p className="text-xs text-stone-400 mt-1">
                        {summary.expiration.expired_lots} vencidos, {summary.expiration.expiring_soon_lots} por vencer
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Breadcrumb + Refresh */}
              <div className="flex items-center justify-between mb-2">
                <SpatialBreadcrumb
                  breadcrumbs={breadcrumbs}
                  currentLevel={zoom.level}
                  onBack={zoomOut}
                  onNavigate={zoomToLevel}
                />
                {zoom.level === 0 && (
                  <button
                    onClick={fetchLevel0}
                    className="px-4 py-2 bg-[var(--accent)] text-white rounded-lg text-sm font-medium hover:bg-[var(--accent-hover)] flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Actualizar
                  </button>
                )}
              </div>

              {/* Zoom levels */}
              <div key={`${zoom.level}-${zoom.warehouseCode}-${zoom.productSku}`} className={animationClass}>
                {zoom.level === 0 && (
                  <SpatialWarehouseGrid
                    warehouses={warehouses}
                    warehouseExpiration={warehouseExpiration}
                    products={products}
                    onWarehouseClick={zoomIntoWarehouse}
                  />
                )}

                {zoom.level === 1 && (
                  warehouseLoading ? (
                    <div className="flex items-center justify-center py-24">
                      <div className="flex flex-col items-center gap-4">
                        <Loader2 className="w-10 h-10 animate-spin text-[var(--primary)]" />
                        <p className="text-[var(--foreground-muted)] font-medium">Cargando productos...</p>
                      </div>
                    </div>
                  ) : (
                    <SpatialProductList
                      products={warehouseProducts}
                      summary={warehouseSummary}
                      warehouseName={zoom.warehouseName || ''}
                      warehouseUpdateMethod={zoom.warehouseUpdateMethod}
                      onProductClick={zoomIntoProduct}
                    />
                  )
                )}

                {zoom.level === 2 && selectedProduct && (
                  <SpatialLotDetail product={selectedProduct} />
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
