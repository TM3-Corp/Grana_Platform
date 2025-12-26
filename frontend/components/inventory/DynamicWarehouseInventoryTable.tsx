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
  recommended_min_stock?: number; // System-calculated recommendation (based on 6-month sales avg)
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

  // Header cell
  const HeaderCell = ({ label, field, sticky = false }: { label: string; field: string; sticky?: boolean }) => (
    <th
      onClick={() => handleSort(field)}
      className={`${
        sticky ? 'sticky left-0 z-10 bg-gradient-to-r from-gray-100 to-gray-50' : 'bg-gradient-to-br from-gray-50 to-blue-50'
      } px-4 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-blue-100 transition-colors duration-200 group border-b border-gray-200`}
    >
      <div className="flex items-center gap-2">
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
              <HeaderCell label="SKU" field="sku" sticky />
              <HeaderCell label="Producto" field="name" />
              <HeaderCell label="Familia" field="category" />

              {/* Dynamic warehouse columns */}
              {warehouseCodes.map((code) => (
                <HeaderCell key={code} label={formatWarehouseName(code)} field={code} />
              ))}

              <HeaderCell label="Lotes" field="lot_count" />
              <HeaderCell label="Total" field="stock_total" />
              <HeaderCell label="Valor" field="valor" />
              <HeaderCell label="Stock Mínimo" field="min_stock" />
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {sortedProducts.map((product, index) => (
              <tr key={product.sku} className="hover:bg-blue-50 transition-colors duration-150">
                {/* Sticky SKU column with warning indicator and consolidation info */}
                <td className="sticky left-0 z-20 bg-white px-4 py-3 whitespace-nowrap border-r border-gray-200">
                  <div className="flex flex-col relative">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono font-semibold text-blue-600">
                        {product.sku}
                      </span>
                      {product.in_catalog === false && (
                        <span
                          title="Este SKU no está en el catálogo de productos. Agregar mapeo en SKU Mappings."
                          className="text-amber-500 cursor-help"
                        >
                          ⚠️
                        </span>
                      )}
                    </div>
                    {product.original_skus && product.original_skus.length > 1 && (
                      <div className="relative inline-block">
                        <span
                          className="text-xs text-blue-600 mt-0.5 cursor-pointer hover:text-blue-800 hover:underline"
                          onMouseEnter={(e) => {
                            const rect = e.currentTarget.getBoundingClientRect();
                            setTooltipPosition({ top: rect.bottom + 4, left: rect.left });
                            setHoveredSku(product.sku);
                            setHoveredSkuDetail(product.original_skus_detail || null);
                          }}
                          onMouseLeave={() => setHoveredSku(null)}
                        >
                          ({product.original_skus.length} SKUs consolidados)
                        </span>
                      </div>
                    )}
                  </div>
                </td>

                {/* Product name */}
                <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate" title={toTitleCase(product.name)}>
                  {toTitleCase(product.name)}
                </td>

                {/* Category */}
                <td className="px-4 py-3 whitespace-nowrap">
                  {product.category && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                      {toTitleCase(product.category)}
                    </span>
                  )}
                </td>

                {/* Dynamic warehouse stock columns */}
                {warehouseCodes.map((code) => {
                  const stock = product.warehouses?.[code] || 0;
                  return (
                    <td key={code} className="px-4 py-3 whitespace-nowrap text-sm text-center">
                      <span
                        className={`inline-flex items-center justify-center min-w-[60px] px-3 py-1 rounded-md font-semibold ${
                          stock > 0
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-400'
                        }`}
                      >
                        {stock.toLocaleString()}
                      </span>
                    </td>
                  );
                })}

                {/* Lot count */}
                <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                  {product.lot_count > 0 ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {product.lot_count} {product.lot_count === 1 ? 'lote' : 'lotes'}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>

                {/* Total stock */}
                <td className="px-4 py-3 whitespace-nowrap text-sm font-bold text-right">
                  <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent text-base">
                    {product.stock_total.toLocaleString()}
                  </span>
                </td>

                {/* Valor (value) */}
                <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                  {product.valor && Number(product.valor) > 0 ? (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800">
                      ${Math.round(Number(product.valor)).toLocaleString('es-CL')}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>

                {/* Minimum stock (editable) with recommended value */}
                <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                  <div className="flex flex-col items-center gap-1">
                    {editingSku === product.sku ? (
                      // Editing mode: show input
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
                        className="w-24 px-2 py-1 text-center border-2 border-blue-400 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      />
                    ) : (
                      // View mode: show clickable span with current value
                      <span
                        onClick={() => startEditing(product.sku, Number(product.min_stock) || Number(product.recommended_min_stock) || 0)}
                        className={`inline-flex items-center justify-center min-w-[80px] px-3 py-1 rounded-md font-medium cursor-pointer transition-all hover:ring-2 hover:ring-blue-400 ${
                          Number(product.stock_total) < (Number(product.min_stock) || Number(product.recommended_min_stock) || 0)
                            ? 'bg-red-100 text-red-800 ring-2 ring-red-300'
                            : Number(product.min_stock) > 0
                              ? 'bg-blue-100 text-blue-800'  // User-edited value
                              : 'bg-gray-100 text-gray-700'
                        }`}
                        title={`Click para editar.${Number(product.min_stock) > 0 ? ` Valor actual: ${Number(product.min_stock).toLocaleString()}` : ''} Recomendado: ${Number(product.recommended_min_stock || 0).toLocaleString()}`}
                      >
                        {Number(product.min_stock) > 0
                          ? Number(product.min_stock).toLocaleString()
                          : (Number(product.recommended_min_stock) > 0
                              ? Number(product.recommended_min_stock).toLocaleString()
                              : '-')}
                      </span>
                    )}
                    {/* Show recommended value below ONLY if user edited to a different value AND recommended > 0 */}
                    {Number(product.recommended_min_stock) > 0 &&
                     Number(product.min_stock) > 0 &&
                     Number(product.min_stock) !== Number(product.recommended_min_stock) && (
                      <button
                        onClick={() => saveMinStock(product.sku, Number(product.recommended_min_stock))}
                        className="text-xs text-amber-600 hover:text-amber-800 font-medium hover:underline cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        title={`Click para usar ${Number(product.recommended_min_stock).toLocaleString()} como stock mínimo (basado en promedio de ventas de 6 meses)`}
                        disabled={saving}
                      >
                        📊 Rec: {Number(product.recommended_min_stock).toLocaleString()}
                      </button>
                    )}
                    {/* Detalles button to show sales timeline */}
                    <button
                      onClick={() => openTimelineModal(product.sku, product.name)}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium hover:underline mt-1"
                      title="Ver historial de ventas de los últimos 12 meses"
                    >
                      📈 Detalles
                    </button>
                  </div>
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
