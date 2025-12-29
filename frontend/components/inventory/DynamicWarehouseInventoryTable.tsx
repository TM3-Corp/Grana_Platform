'use client';

import { useState, useMemo, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { toTitleCase } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

// Types for sales timeline data
interface TimelineDataPoint {
  month: string;
  month_name: string;
  units_sold: number;
  revenue: number;
}

interface TimelineStats {
  min_units: number;
  max_units: number;
  avg_units: number;
  stddev_units: number;
  total_units: number;
  total_revenue: number;
  months_with_sales: number;
}

interface TimelineData {
  timeline: TimelineDataPoint[];
  stats: TimelineStats;
}

// Types for SKU mapping detail
interface OriginalSkuDetail {
  sku: string;
  name: string;
  is_mapped: boolean;
  target_sku: string | null;
  multiplier: number | null;
  rule_name: string | null;
  raw_quantity: number;
  adjusted_quantity: number;
}

// Types for dynamic warehouse structure
interface DynamicInventoryProduct {
  sku: string;
  original_skus?: string[]; // Source SKUs that were consolidated into this row
  original_skus_detail?: OriginalSkuDetail[]; // Detailed mapping info for each source SKU
  name: string;
  category: string | null;
  subfamily: string | null;
  warehouses: {
    [warehouse_code: string]: number;
  };
  stock_total: number;
  lot_count: number;
  last_updated: string | null;
  min_stock?: number; // User-editable minimum stock level
  recommended_min_stock?: number; // System-calculated recommendation (based on configurable estimation period)
  estimation_months?: number; // Estimation period: 1, 3, or 6 months (default 6)
  stock_usable?: number; // Stock excluding expired and expiring soon
  stock_expiring_30d?: number; // Stock expiring within 30 days
  stock_expired?: number; // Already expired stock
  days_of_coverage?: number; // Days of stock remaining at current sales rate
  production_needed?: number; // Units needed to produce to meet target
  earliest_expiration?: string | null; // Earliest expiration date
  days_to_earliest_expiration?: number | null; // Days to earliest expiration
  sku_value?: number; // Unit cost from product_catalog
  valor?: number; // Total value (stock_total × sku_value)
  in_catalog?: boolean; // Whether SKU is in product_catalog (false = show warning)
  is_inventory_active?: boolean; // Whether product is active for inventory tracking
}

interface DynamicWarehouseInventoryTableProps {
  products: DynamicInventoryProduct[];
  loading?: boolean;
  onDataChanged?: () => void;  // Callback to refresh data after edits
}

type SortDirection = 'asc' | 'desc';

export default function DynamicWarehouseInventoryTable({
  products,
  loading = false,
  onDataChanged,
}: DynamicWarehouseInventoryTableProps) {
  const [sortField, setSortField] = useState<string>('category');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Inline editing state
  const [editingSku, setEditingSku] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<number>(0);
  const [saving, setSaving] = useState(false);
  const [savingEstimation, setSavingEstimation] = useState<string | null>(null); // SKU being updated

  // Hover tooltip state for SKU consolidation details
  const [hoveredSku, setHoveredSku] = useState<string | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ top: number; left: number } | null>(null);
  const [hoveredSkuDetail, setHoveredSkuDetail] = useState<OriginalSkuDetail[] | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  // Sales timeline modal state
  const [timelineModalSku, setTimelineModalSku] = useState<string | null>(null);
  const [timelineModalName, setTimelineModalName] = useState<string>('');
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);

  // Track if component is mounted for portal rendering
  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  // Extract unique warehouse codes from products
  const warehouseCodes = useMemo(() => {
    const codes = new Set<string>();
    products.forEach((product) => {
      if (product.warehouses) {
        Object.keys(product.warehouses).forEach((code) => codes.add(code));
      }
    });
    return Array.from(codes).sort();
  }, [products]);

  // Format warehouse name for display
  const formatWarehouseName = (code: string): string => {
    return code
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Sorting handler
  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Inline editing handlers
  const startEditing = (sku: string, currentValue: number) => {
    setEditingSku(sku);
    // If value is 0, start with empty string so user can type fresh
    setEditingValue(currentValue || 0);
  };

  // Track if input was just focused (to select all text)
  const handleInputFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    e.target.select(); // Select all text on focus so typing replaces it
  };

  const cancelEditing = () => {
    setEditingSku(null);
    setEditingValue(0);
  };

  const saveMinStock = async (sku: string, newValue: number) => {
    if (newValue < 0) {
      alert('El stock mínimo no puede ser negativo');
      return;
    }

    setSaving(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/products/${sku}/min-stock`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ min_stock: newValue }),
      });

      if (!response.ok) {
        throw new Error('Failed to update minimum stock');
      }

      setEditingSku(null);
      setEditingValue(0);

      // Trigger parent to refetch data so new value is displayed
      if (onDataChanged) {
        onDataChanged();
      }
    } catch (error) {
      console.error('Error updating min stock:', error);
      alert('Error al actualizar el stock mínimo');
    } finally {
      setSaving(false);
    }
  };

  // Update estimation period for a SKU
  const updateEstimationPeriod = async (sku: string, estimationMonths: number) => {
    setSavingEstimation(sku);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/products/${sku}/estimation-method`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ estimation_months: estimationMonths }),
      });

      if (!response.ok) {
        throw new Error('Failed to update estimation period');
      }

      // Trigger parent to refetch data so new value is displayed
      if (onDataChanged) {
        onDataChanged();
      }
    } catch (error) {
      console.error('Error updating estimation period:', error);
      alert('Error al actualizar el período de estimación');
    } finally {
      setSavingEstimation(null);
    }
  };

  // Open sales timeline modal for a SKU
  const openTimelineModal = async (sku: string, name: string) => {
    setTimelineModalSku(sku);
    setTimelineModalName(name);
    setTimelineLoading(true);
    setTimelineData(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/api/v1/sales-analytics/sku-timeline/${encodeURIComponent(sku)}?months=12`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch timeline data');
      }

      const result = await response.json();
      setTimelineData(result.data);
    } catch (error) {
      console.error('Error fetching timeline:', error);
      setTimelineData({ timeline: [], stats: { min_units: 0, max_units: 0, avg_units: 0, stddev_units: 0, total_units: 0, total_revenue: 0, months_with_sales: 0 } });
    } finally {
      setTimelineLoading(false);
    }
  };

  const closeTimelineModal = () => {
    setTimelineModalSku(null);
    setTimelineData(null);
  };

  // Sorted products
  const sortedProducts = useMemo(() => {
    return [...products].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      if (sortField === 'sku') {
        aVal = a.sku;
        bVal = b.sku;
      } else if (sortField === 'name') {
        aVal = a.name;
        bVal = b.name;
      } else if (sortField === 'category') {
        aVal = a.category || '';
        bVal = b.category || '';
      } else if (sortField === 'stock_total') {
        // Ensure numeric sorting (values may come as strings from API)
        aVal = Number(a.stock_total) || 0;
        bVal = Number(b.stock_total) || 0;
      } else if (sortField === 'lot_count') {
        aVal = Number(a.lot_count) || 0;
        bVal = Number(b.lot_count) || 0;
      } else if (sortField === 'min_stock') {
        aVal = Number(a.min_stock) || 0;
        bVal = Number(b.min_stock) || 0;
      } else if (sortField === 'valor') {
        aVal = Number(a.valor) || 0;
        bVal = Number(b.valor) || 0;
      } else if (sortField === 'days_of_coverage') {
        aVal = Number(a.days_of_coverage) || 999;
        bVal = Number(b.days_of_coverage) || 999;
      } else if (sortField === 'production_needed') {
        aVal = Number(a.production_needed) || 0;
        bVal = Number(b.production_needed) || 0;
      } else if (sortField === 'earliest_expiration') {
        // Sort by days to expiration (null values at the end)
        aVal = a.days_to_earliest_expiration ?? 9999;
        bVal = b.days_to_earliest_expiration ?? 9999;
      } else if (sortField === 'stock_status') {
        // Sort by stock status: over-stocked first (most urgent), then balanced, then ok
        const getStatusPriority = (p: DynamicInventoryProduct) => {
          const coverage = Number(p.days_of_coverage) || 999;
          const daysToExp = p.days_to_earliest_expiration;
          if (!daysToExp) return 3; // No expiration - lowest priority
          if (coverage > daysToExp) return 0; // Over-stocked (expires before selling) - highest priority
          if (coverage >= daysToExp * 0.8) return 1; // At risk
          return 2; // OK
        };
        aVal = getStatusPriority(a);
        bVal = getStatusPriority(b);
      } else if (warehouseCodes.includes(sortField)) {
        // Warehouse stock values - ensure numeric sorting
        aVal = Number(a.warehouses?.[sortField]) || 0;
        bVal = Number(b.warehouses?.[sortField]) || 0;
      } else {
        return 0;
      }

      if (typeof aVal === 'string') {
        const comparison = aVal.localeCompare(bVal);
        return sortDirection === 'asc' ? comparison : -comparison;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [products, sortField, sortDirection, warehouseCodes]);

  // Sort indicator
  const SortIndicator = ({ field }: { field: string }) => {
    if (sortField !== field) {
      return (
        <svg className="w-4 h-4 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return (
      <svg
        className={`w-4 h-4 text-blue-600 transition-transform duration-200 ${
          sortDirection === 'desc' ? 'rotate-180' : ''
        }`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    );
  };

  // Header cell - clean executive style
  const HeaderCell = ({ label, field, sticky = false }: { label: string; field: string; sticky?: boolean }) => (
    <th
      onClick={() => handleSort(field)}
      className={`${
        sticky ? 'sticky left-0 z-10 bg-gray-50' : 'bg-gray-50'
      } px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide cursor-pointer hover:bg-gray-100 transition-colors group border-b border-gray-200`}
    >
      <div className="flex items-center gap-1.5">
        <span>{label}</span>
        <SortIndicator field={field} />
      </div>
    </th>
  );

  // Loading skeleton
  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
        <div className="p-8 flex flex-col items-center justify-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-600 border-t-transparent mb-4"></div>
          <p className="text-gray-600 font-medium">Cargando inventario...</p>
        </div>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="bg-white rounded-2xl border-2 border-dashed border-gray-300 p-12 text-center shadow-sm">
        <div className="text-6xl mb-4">📦</div>
        <h3 className="text-xl font-semibold text-gray-900 mb-2">No hay productos en inventario</h3>
        <p className="text-gray-600">No se encontraron productos con las bodegas activas de Relbase.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              {/* Consolidated Producto column (SKU + Name + Category) */}
              <HeaderCell label="Producto" field="name" sticky />

              {/* Dynamic warehouse columns */}
              {warehouseCodes.map((code) => (
                <HeaderCell key={code} label={formatWarehouseName(code)} field={code} />
              ))}

              <HeaderCell label="Stock" field="stock_total" />
              <HeaderCell label="Valor" field="valor" />
              <HeaderCell label="Stock Mínimo" field="min_stock" />
              <HeaderCell label="Cobertura" field="days_of_coverage" />
              <HeaderCell label="Vence" field="earliest_expiration" />
              <HeaderCell label="Estado" field="stock_status" />
              <HeaderCell label="Producir" field="production_needed" />
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {sortedProducts.map((product, index) => (
              <tr key={product.sku} className="hover:bg-blue-50/50 transition-colors duration-150">
                {/* Consolidated Producto column: SKU + Name + Category */}
                <td className="sticky left-0 z-20 bg-white px-4 py-3 border-r border-gray-100 min-w-[280px] max-w-[360px]">
                  <div className="flex flex-col gap-0.5">
                    {/* Row 1: SKU code + Category badge */}
                    <div className="flex items-center gap-2">
                      <code className="text-xs font-mono font-medium text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                        {product.sku}
                      </code>
                      {product.category && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                          {toTitleCase(product.category)}
                        </span>
                      )}
                      {product.in_catalog === false && (
                        <span
                          title="SKU no está en catálogo"
                          className="text-amber-500 cursor-help text-sm"
                        >
                          ⚠️
                        </span>
                      )}
                      {/* Expiration warning badge */}
                      {Number(product.stock_expiring_30d) > 0 && (
                        <span
                          title={`${Number(product.stock_expiring_30d).toLocaleString()} unidades vencen en los próximos 30 días`}
                          className="text-xs text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded cursor-help"
                        >
                          {Number(product.stock_expiring_30d).toLocaleString()} venciendo
                        </span>
                      )}
                    </div>
                    {/* Row 2: Product name */}
                    <span className="text-sm font-medium text-gray-900 truncate" title={toTitleCase(product.name)}>
                      {toTitleCase(product.name)}
                    </span>
                    {/* Row 3: Consolidated SKUs info (if applicable) */}
                    {product.original_skus && product.original_skus.length > 1 && (
                      <span
                        className="text-xs text-blue-600 cursor-pointer hover:text-blue-800 hover:underline"
                        onMouseEnter={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          setTooltipPosition({ top: rect.bottom + 4, left: rect.left });
                          setHoveredSku(product.sku);
                          setHoveredSkuDetail(product.original_skus_detail || null);
                        }}
                        onMouseLeave={() => setHoveredSku(null)}
                      >
                        {product.original_skus.length} SKUs consolidados
                      </span>
                    )}
                  </div>
                </td>

                {/* Dynamic warehouse stock columns - cleaner numeric display */}
                {warehouseCodes.map((code) => {
                  const stock = product.warehouses?.[code] || 0;
                  return (
                    <td key={code} className="px-3 py-3 whitespace-nowrap text-sm text-right tabular-nums">
                      {stock > 0 ? (
                        <span className="text-gray-900 font-medium">{stock.toLocaleString()}</span>
                      ) : (
                        <span className="text-gray-300">-</span>
                      )}
                    </td>
                  );
                })}

                {/* Total stock - prominent display */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  <div className="flex flex-col items-end">
                    <span className="text-base font-bold text-gray-900 tabular-nums">
                      {product.stock_total.toLocaleString()}
                    </span>
                    {product.lot_count > 0 && (
                      <span className="text-xs text-gray-500">
                        {product.lot_count} {product.lot_count === 1 ? 'lote' : 'lotes'}
                      </span>
                    )}
                  </div>
                </td>

                {/* Valor - compact currency display */}
                <td className="px-3 py-3 whitespace-nowrap text-right tabular-nums">
                  {product.valor && Number(product.valor) > 0 ? (
                    <span className="text-sm font-medium text-emerald-700">
                      ${Math.round(Number(product.valor)).toLocaleString('es-CL')}
                    </span>
                  ) : (
                    <span className="text-gray-300">-</span>
                  )}
                </td>

                {/* Minimum stock - professional editable field design */}
                <td className="px-3 py-2.5 whitespace-nowrap">
                  <div className="flex flex-col gap-2">
                    {/* Editable field with proper visual affordance */}
                    {editingSku === product.sku ? (
                      /* Edit mode: focused input */
                      <div className="relative">
                        <input
                          type="number"
                          min="0"
                          value={editingValue || ''}
                          onChange={(e) => setEditingValue(parseInt(e.target.value) || 0)}
                          onFocus={handleInputFocus}
                          onBlur={() => saveMinStock(product.sku, editingValue)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              saveMinStock(product.sku, editingValue);
                            } else if (e.key === 'Escape') {
                              cancelEditing();
                            }
                          }}
                          disabled={saving}
                          autoFocus
                          className="w-full px-3 py-2 text-sm text-right tabular-nums border-2 border-blue-500 rounded-lg bg-white focus:ring-2 focus:ring-blue-200 focus:outline-none shadow-sm"
                        />
                        <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
                          {saving && (
                            <svg className="w-4 h-4 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                          )}
                        </div>
                      </div>
                    ) : (
                      /* View mode: styled editable field */
                      <button
                        onClick={() => startEditing(product.sku, Number(product.min_stock) || Number(product.recommended_min_stock) || 0)}
                        className={`group relative flex items-center justify-between gap-2 w-full px-3 py-2 rounded-lg border transition-all ${
                          Number(product.stock_total) < (Number(product.min_stock) || Number(product.recommended_min_stock) || 0)
                            ? 'bg-red-50 border-red-200 hover:border-red-400 hover:bg-red-100'
                            : 'bg-gray-50 border-gray-200 hover:border-blue-400 hover:bg-blue-50'
                        }`}
                        title="Click para editar stock mínimo"
                      >
                        <span className={`text-sm font-semibold tabular-nums ${
                          Number(product.stock_total) < (Number(product.min_stock) || Number(product.recommended_min_stock) || 0)
                            ? 'text-red-700'
                            : 'text-gray-700'
                        }`}>
                          {Number(product.min_stock) > 0
                            ? Number(product.min_stock).toLocaleString()
                            : (Number(product.recommended_min_stock) > 0
                                ? Number(product.recommended_min_stock).toLocaleString()
                                : '—')}
                        </span>
                        {/* Edit icon - appears on hover */}
                        <svg
                          className="w-4 h-4 text-gray-400 group-hover:text-blue-500 transition-colors"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                      </button>
                    )}

                    {/* Action buttons row - properly styled */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {/* Estimation period dropdown */}
                      <div className="relative">
                        <select
                          value={product.estimation_months || 6}
                          onChange={(e) => updateEstimationPeriod(product.sku, parseInt(e.target.value))}
                          disabled={savingEstimation === product.sku}
                          className={`text-xs px-2 py-1 rounded border bg-white cursor-pointer transition-colors ${
                            savingEstimation === product.sku
                              ? 'opacity-50 cursor-wait'
                              : 'border-gray-200 hover:border-blue-400'
                          }`}
                          title="Período de estimación para cálculo de stock mínimo"
                        >
                          <option value={1}>Último Mes</option>
                          <option value={3}>Últimos 3 Meses</option>
                          <option value={6}>Últimos 6 Meses</option>
                        </select>
                        {savingEstimation === product.sku && (
                          <div className="absolute right-1 top-1/2 -translate-y-1/2">
                            <svg className="w-3 h-3 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                          </div>
                        )}
                      </div>

                      {/* Recommended value button - shows when user has custom value different from recommended */}
                      {Number(product.recommended_min_stock) > 0 &&
                       Number(product.min_stock) > 0 &&
                       Number(product.min_stock) !== Number(product.recommended_min_stock) && (
                        <button
                          onClick={() => saveMinStock(product.sku, Number(product.recommended_min_stock))}
                          disabled={saving}
                          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 rounded-md transition-colors disabled:opacity-50"
                          title={`Restablecer al valor recomendado: ${Number(product.recommended_min_stock).toLocaleString()}`}
                        >
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                          <span>{Number(product.recommended_min_stock).toLocaleString()}</span>
                        </button>
                      )}

                      {/* Sales history button */}
                      <button
                        onClick={() => openTimelineModal(product.sku, product.name)}
                        className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 rounded-md transition-colors"
                        title="Ver historial de ventas (últimos 12 meses)"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        <span>Ventas</span>
                      </button>
                    </div>
                  </div>
                </td>

                {/* Days of Coverage (Cobertura) - color coded */}
                <td className="px-3 py-3 whitespace-nowrap text-center">
                  {Number(product.days_of_coverage) >= 0 && Number(product.days_of_coverage) < 999 ? (
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-full text-sm font-semibold ${
                        Number(product.days_of_coverage) < 15
                          ? 'bg-red-100 text-red-800'
                          : Number(product.days_of_coverage) < 30
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-green-100 text-green-800'
                      }`}
                      title={`${Number(product.days_of_coverage)} días de cobertura basado en ventas promedio`}
                    >
                      {Number(product.days_of_coverage)}d
                    </span>
                  ) : (
                    <span className="text-gray-400 text-sm" title="Sin ventas registradas">
                      —
                    </span>
                  )}
                </td>

                {/* Earliest Expiration (Vence) - DD/MM/YYYY format, sorted by days numerically */}
                <td className="px-3 py-3 whitespace-nowrap text-center">
                  {product.earliest_expiration ? (
                    <div className="flex flex-col items-center">
                      <span className={`text-sm font-medium ${
                        (product.days_to_earliest_expiration ?? 999) < 30
                          ? 'text-red-700'
                          : (product.days_to_earliest_expiration ?? 999) < 60
                          ? 'text-amber-700'
                          : 'text-gray-700'
                      }`}>
                        {new Date(product.earliest_expiration).toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                      </span>
                      <span className="text-xs text-gray-500">
                        ({product.days_to_earliest_expiration}d)
                      </span>
                    </div>
                  ) : (
                    <span className="text-gray-400 text-sm" title="Sin fecha de vencimiento">—</span>
                  )}
                </td>

                {/* Stock Status (Estado) - Over-stocked vs OK */}
                <td className="px-3 py-3 whitespace-nowrap text-center">
                  {(() => {
                    const coverage = Number(product.days_of_coverage) || 999;
                    const daysToExp = product.days_to_earliest_expiration;

                    if (!daysToExp || coverage >= 999) {
                      return <span className="text-gray-400 text-sm">—</span>;
                    }

                    // Over-stocked: coverage > days to expiration (will expire before selling)
                    if (coverage > daysToExp) {
                      const excessDays = coverage - daysToExp;
                      return (
                        <span
                          className="inline-flex items-center px-2 py-1 rounded-lg bg-red-100 text-red-800 text-xs font-semibold"
                          title={`Stock excede vencimiento por ${excessDays} días. Riesgo de merma.`}
                        >
                          <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          Exceso
                        </span>
                      );
                    }

                    // At risk: coverage is close to expiration (within 20%)
                    if (coverage >= daysToExp * 0.8) {
                      return (
                        <span
                          className="inline-flex items-center px-2 py-1 rounded-lg bg-amber-100 text-amber-800 text-xs font-semibold"
                          title={`Stock se venderá ${daysToExp - coverage} días antes del vencimiento. Monitorear.`}
                        >
                          <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          Ajustado
                        </span>
                      );
                    }

                    // OK: coverage < 80% of expiration (will sell well before expiration)
                    return (
                      <span
                        className="inline-flex items-center px-2 py-1 rounded-lg bg-green-100 text-green-800 text-xs font-semibold"
                        title={`Stock se venderá ${daysToExp - coverage} días antes del vencimiento. OK.`}
                      >
                        <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        OK
                      </span>
                    );
                  })()}
                </td>

                {/* Production Needed (Producir) */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  {Number(product.production_needed) > 0 ? (
                    <span
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-100 text-blue-800 font-semibold text-sm"
                      title={`Producir ${Number(product.production_needed).toLocaleString()} unidades para alcanzar stock objetivo`}
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                      {Number(product.production_needed).toLocaleString()}
                    </span>
                  ) : (
                    <span className="text-gray-400 text-sm">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="bg-gradient-to-r from-gray-50 to-blue-50 px-6 py-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 font-medium">
            Mostrando {sortedProducts.length} {sortedProducts.length === 1 ? 'producto' : 'productos'}
          </span>
          <span className="text-gray-600">
            Total de bodegas: <span className="font-semibold text-blue-600">{warehouseCodes.length}</span>
          </span>
        </div>
      </div>

      {/* Hover tooltip - rendered via portal to escape table stacking context */}
      {isMounted && hoveredSku && hoveredSkuDetail && tooltipPosition &&
        createPortal(
          <div
            className="fixed bg-white border border-gray-200 rounded-lg shadow-2xl p-3 min-w-[320px] max-w-[400px]"
            style={{
              top: tooltipPosition.top,
              left: tooltipPosition.left,
              zIndex: 99999,
            }}
            onMouseEnter={() => {/* Keep tooltip visible */}}
            onMouseLeave={() => setHoveredSku(null)}
          >
            <div className="text-xs font-semibold text-gray-700 mb-2 border-b pb-1">
              SKUs consolidados en {hoveredSku}
            </div>
            <div className="space-y-2">
              {hoveredSkuDetail.map((detail) => (
                <div
                  key={detail.sku}
                  className={`text-xs p-2 rounded ${
                    detail.is_mapped
                      ? 'bg-blue-50 border border-blue-200'
                      : 'bg-gray-50 border border-gray-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-semibold text-gray-800">
                      {detail.sku}
                    </span>
                    <span className="text-gray-600">
                      {detail.raw_quantity.toLocaleString()} uds
                    </span>
                  </div>
                  {detail.is_mapped ? (
                    <div className="mt-1 flex items-center gap-1 text-blue-700">
                      <span>→</span>
                      <span className="font-mono">{detail.target_sku}</span>
                      {detail.multiplier && detail.multiplier > 1 && (
                        <span className="bg-blue-200 text-blue-800 px-1.5 py-0.5 rounded font-semibold">
                          ×{detail.multiplier}
                        </span>
                      )}
                      <span className="text-gray-500 ml-1">
                        = {detail.adjusted_quantity.toLocaleString()} uds
                      </span>
                    </div>
                  ) : (
                    <div className="mt-1 text-gray-500 italic">
                      (SKU principal - sin mapeo)
                    </div>
                  )}
                  {detail.rule_name && (
                    <div className="mt-1 text-gray-500">
                      Regla: {detail.rule_name}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>,
          document.body
        )
      }

      {/* Sales Timeline Modal */}
      {isMounted && timelineModalSku &&
        createPortal(
          <div
            className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50"
            onClick={closeTimelineModal}
          >
            <div
              className="bg-white rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4 rounded-t-xl">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold">📈 Historial de Ventas</h2>
                    <p className="text-blue-100 text-sm mt-1">{timelineModalSku} - {timelineModalName}</p>
                  </div>
                  <button
                    onClick={closeTimelineModal}
                    className="text-white/80 hover:text-white text-2xl font-bold"
                  >
                    ×
                  </button>
                </div>
              </div>

              {/* Modal Content */}
              <div className="p-6">
                {timelineLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                    <span className="ml-4 text-gray-600">Cargando datos...</span>
                  </div>
                ) : timelineData && timelineData.timeline.length > 0 ? (
                  <>
                    {/* Statistics Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-blue-50 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-blue-700">
                          {timelineData.stats.avg_units.toLocaleString()}
                        </div>
                        <div className="text-sm text-blue-600">Promedio Mensual</div>
                      </div>
                      <div className="bg-green-50 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-green-700">
                          {timelineData.stats.max_units.toLocaleString()}
                        </div>
                        <div className="text-sm text-green-600">Máximo</div>
                      </div>
                      <div className="bg-amber-50 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-amber-700">
                          {timelineData.stats.min_units.toLocaleString()}
                        </div>
                        <div className="text-sm text-amber-600">Mínimo</div>
                      </div>
                      <div className="bg-purple-50 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-purple-700">
                          {timelineData.stats.stddev_units.toLocaleString()}
                        </div>
                        <div className="text-sm text-purple-600">Desv. Estándar</div>
                      </div>
                    </div>

                    {/* Chart */}
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h3 className="text-sm font-semibold text-gray-700 mb-4">
                        Unidades Vendidas - Últimos 12 Meses
                      </h3>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={timelineData.timeline}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis
                              dataKey="month_name"
                              tick={{ fontSize: 11 }}
                              angle={-45}
                              textAnchor="end"
                              height={60}
                            />
                            <YAxis
                              tick={{ fontSize: 11 }}
                              tickFormatter={(value) => value.toLocaleString()}
                            />
                            <Tooltip
                              formatter={(value: number) => [value.toLocaleString(), 'Unidades']}
                              labelFormatter={(label) => `Mes: ${label}`}
                            />
                            {/* Average reference line */}
                            <ReferenceLine
                              y={timelineData.stats.avg_units}
                              stroke="#3b82f6"
                              strokeDasharray="5 5"
                              label={{ value: `Prom: ${timelineData.stats.avg_units.toLocaleString()}`, fill: '#3b82f6', fontSize: 11 }}
                            />
                            <Line
                              type="monotone"
                              dataKey="units_sold"
                              stroke="#2563eb"
                              strokeWidth={2}
                              dot={{ fill: '#2563eb', strokeWidth: 2, r: 4 }}
                              activeDot={{ r: 6, stroke: '#1d4ed8', strokeWidth: 2 }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Summary */}
                    <div className="mt-4 p-4 bg-gray-100 rounded-lg">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">
                          Total vendido en {timelineData.stats.months_with_sales} meses: <strong>{timelineData.stats.total_units.toLocaleString()} unidades</strong>
                        </span>
                        <span className="text-gray-600">
                          Ingresos: <strong>${(timelineData.stats.total_revenue / 1000000).toFixed(1)}M</strong>
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        💡 El stock mínimo recomendado se basa en el promedio mensual de los últimos 6 meses.
                        Use esta información para ajustar según estacionalidad.
                      </p>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <div className="text-5xl mb-4">📊</div>
                    <p className="text-lg font-medium">No hay datos de ventas</p>
                    <p className="text-sm">Este producto no tiene ventas registradas en los últimos 12 meses.</p>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="bg-gray-50 px-6 py-4 rounded-b-xl border-t flex justify-end">
                <button
                  onClick={closeTimelineModal}
                  className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg font-medium transition-colors"
                >
                  Cerrar
                </button>
              </div>
            </div>
          </div>,
          document.body
        )
      }
    </div>
  );
}
