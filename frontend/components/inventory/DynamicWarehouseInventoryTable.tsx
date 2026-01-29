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
import {
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Pencil,
  RotateCcw,
  BarChart3,
  AlertTriangle,
  CheckCircle,
  Clock,
  Plus,
  Package,
  X,
  Loader2,
  TrendingUp,
  Calendar,
} from 'lucide-react';

// Types
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

interface DynamicInventoryProduct {
  sku: string;
  original_skus?: string[];
  original_skus_detail?: OriginalSkuDetail[];
  name: string;
  category: string | null;
  subfamily: string | null;
  warehouses: {
    [warehouse_code: string]: number;
  };
  stock_total: number;
  lot_count: number;
  last_updated: string | null;
  min_stock?: number;
  recommended_min_stock?: number;
  estimation_months?: number;
  stock_usable?: number;
  stock_expiring_30d?: number;
  stock_expired?: number;
  days_of_coverage?: number;
  production_needed?: number;
  earliest_expiration?: string | null;
  days_to_earliest_expiration?: number | null;
  sku_value?: number;
  valor?: number;
  in_catalog?: boolean;
  is_inventory_active?: boolean;
}

interface DynamicWarehouseInventoryTableProps {
  products: DynamicInventoryProduct[];
  loading?: boolean;
  onDataChanged?: () => void;
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
  const [savingEstimation, setSavingEstimation] = useState<string | null>(null);

  // Hover tooltip state
  const [hoveredSku, setHoveredSku] = useState<string | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ top: number; left: number } | null>(null);
  const [hoveredSkuDetail, setHoveredSkuDetail] = useState<OriginalSkuDetail[] | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  // Sales timeline modal state
  const [timelineModalSku, setTimelineModalSku] = useState<string | null>(null);
  const [timelineModalName, setTimelineModalName] = useState<string>('');
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);

  // Extract unique warehouse codes
  const warehouseCodes = useMemo(() => {
    const codes = new Set<string>();
    products.forEach((product) => {
      if (product.warehouses) {
        Object.keys(product.warehouses).forEach((code) => codes.add(code));
      }
    });
    return Array.from(codes).sort();
  }, [products]);

  const formatWarehouseName = (code: string): string => {
    return code.split('_').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

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
    setEditingValue(currentValue || 0);
  };

  const handleInputFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    e.target.select();
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ min_stock: newValue }),
      });

      if (!response.ok) throw new Error('Failed to update minimum stock');

      setEditingSku(null);
      setEditingValue(0);
      if (onDataChanged) onDataChanged();
    } catch (error) {
      console.error('Error updating min stock:', error);
      alert('Error al actualizar el stock mínimo');
    } finally {
      setSaving(false);
    }
  };

  const updateEstimationPeriod = async (sku: string, estimationMonths: number) => {
    setSavingEstimation(sku);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/products/${sku}/estimation-method`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ estimation_months: estimationMonths }),
      });

      if (!response.ok) throw new Error('Failed to update estimation period');
      if (onDataChanged) onDataChanged();
    } catch (error) {
      console.error('Error updating estimation period:', error);
      alert('Error al actualizar el período de estimación');
    } finally {
      setSavingEstimation(null);
    }
  };

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

      if (!response.ok) throw new Error('Failed to fetch timeline data');

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
        aVal = a.days_to_earliest_expiration ?? 9999;
        bVal = b.days_to_earliest_expiration ?? 9999;
      } else if (sortField === 'stock_status') {
        const getStatusPriority = (p: DynamicInventoryProduct) => {
          const coverage = Number(p.days_of_coverage) || 999;
          const daysToExp = p.days_to_earliest_expiration;
          if (!daysToExp) return 3;
          if (coverage > daysToExp) return 0;
          if (coverage >= daysToExp * 0.8) return 1;
          return 2;
        };
        aVal = getStatusPriority(a);
        bVal = getStatusPriority(b);
      } else if (warehouseCodes.includes(sortField)) {
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

  // Sort indicator component
  const SortIndicator = ({ field }: { field: string }) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="w-3.5 h-3.5 text-stone-300 opacity-0 group-hover:opacity-100 transition-opacity" />;
    }
    return sortDirection === 'asc' ? (
      <ChevronUp className="w-3.5 h-3.5 text-[var(--primary)]" />
    ) : (
      <ChevronDown className="w-3.5 h-3.5 text-[var(--primary)]" />
    );
  };

  // Header cell component
  const HeaderCell = ({ label, field, sticky = false }: { label: string; field: string; sticky?: boolean }) => (
    <th
      onClick={() => handleSort(field)}
      className={`${
        sticky ? 'sticky left-0 z-10' : ''
      } bg-stone-50 px-3 py-3 text-left text-[11px] font-semibold text-stone-500 uppercase tracking-wider cursor-pointer hover:bg-stone-100 transition-colors group border-b border-stone-200`}
    >
      <div className="flex items-center gap-1">
        <span>{label}</span>
        <SortIndicator field={field} />
      </div>
    </th>
  );

  // Loading state
  if (loading) {
    return (
      <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden">
        <div className="p-12 flex flex-col items-center justify-center">
          <Loader2 className="w-10 h-10 animate-spin text-[var(--primary)] mb-4" />
          <p className="text-[var(--foreground-muted)] font-medium">Cargando inventario...</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (products.length === 0) {
    return (
      <div className="bg-[var(--surface)] rounded-xl border-2 border-dashed border-[var(--border)] p-12 text-center">
        <Package className="w-12 h-12 text-stone-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-[var(--foreground)] mb-2">No hay productos en inventario</h3>
        <p className="text-[var(--foreground-muted)]">No se encontraron productos con las bodegas activas de Relbase.</p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-stone-200">
          <thead>
            <tr>
              <HeaderCell label="Producto" field="name" sticky />
              {warehouseCodes.map((code) => (
                <HeaderCell key={code} label={formatWarehouseName(code)} field={code} />
              ))}
              <HeaderCell label="Stock" field="stock_total" />
              <HeaderCell label="Valor" field="valor" />
              <HeaderCell label="Stock Mín" field="min_stock" />
              <HeaderCell label="Cobertura" field="days_of_coverage" />
              <HeaderCell label="Vence" field="earliest_expiration" />
              <HeaderCell label="Estado" field="stock_status" />
              <HeaderCell label="Producir" field="production_needed" />
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-stone-100">
            {sortedProducts.map((product) => (
              <tr key={product.sku} className="hover:bg-amber-50/50 transition-colors duration-100">
                {/* Product Info Cell */}
                <td className="sticky left-0 z-20 bg-white px-4 py-3 border-r border-stone-100 min-w-[280px] max-w-[360px]">
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <code className="text-xs font-mono font-medium text-stone-500 bg-stone-100 px-1.5 py-0.5 rounded">
                        {product.sku}
                      </code>
                      {product.category && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-teal-100 text-teal-700 uppercase tracking-wide">
                          {toTitleCase(product.category)}
                        </span>
                      )}
                      {product.in_catalog === false && (
                        <span title="SKU no está en catálogo" className="text-amber-500 cursor-help">
                          <AlertTriangle className="w-3.5 h-3.5" />
                        </span>
                      )}
                      {Number(product.stock_expiring_30d) > 0 && (
                        <span
                          title={`${Number(product.stock_expiring_30d).toLocaleString()} unidades vencen en 30 días`}
                          className="text-[10px] text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded cursor-help font-medium"
                        >
                          {Number(product.stock_expiring_30d).toLocaleString()} venciendo
                        </span>
                      )}
                    </div>
                    <span className="text-sm font-medium text-[var(--foreground)] truncate" title={toTitleCase(product.name)}>
                      {toTitleCase(product.name)}
                    </span>
                    {product.original_skus && product.original_skus.length > 1 && (
                      <span
                        className="text-xs text-[var(--secondary)] cursor-pointer hover:underline font-medium"
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

                {/* Warehouse stock columns */}
                {warehouseCodes.map((code) => {
                  const stock = product.warehouses?.[code] || 0;
                  return (
                    <td key={code} className="px-3 py-3 whitespace-nowrap text-sm text-right font-mono">
                      {stock > 0 ? (
                        <span className="text-[var(--foreground)] font-medium">{stock.toLocaleString()}</span>
                      ) : (
                        <span className="text-stone-300">—</span>
                      )}
                    </td>
                  );
                })}

                {/* Total stock */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  <div className="flex flex-col items-end">
                    <span className="text-base font-bold text-[var(--foreground)] font-mono">
                      {product.stock_total.toLocaleString()}
                    </span>
                    {product.lot_count > 0 && (
                      <span className="text-[10px] text-stone-500">
                        {product.lot_count} {product.lot_count === 1 ? 'lote' : 'lotes'}
                      </span>
                    )}
                  </div>
                </td>

                {/* Value */}
                <td className="px-3 py-3 whitespace-nowrap text-right font-mono">
                  {product.valor && Number(product.valor) > 0 ? (
                    <span className="text-sm font-medium text-[var(--success)]">
                      ${Math.round(Number(product.valor)).toLocaleString('es-CL')}
                    </span>
                  ) : (
                    <span className="text-stone-300">—</span>
                  )}
                </td>

                {/* Minimum stock - editable */}
                <td className="px-3 py-2.5 whitespace-nowrap">
                  <div className="flex flex-col gap-2">
                    {editingSku === product.sku ? (
                      <div className="relative">
                        <input
                          type="number"
                          min="0"
                          value={editingValue || ''}
                          onChange={(e) => setEditingValue(parseInt(e.target.value) || 0)}
                          onFocus={handleInputFocus}
                          onBlur={() => saveMinStock(product.sku, editingValue)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveMinStock(product.sku, editingValue);
                            else if (e.key === 'Escape') cancelEditing();
                          }}
                          disabled={saving}
                          autoFocus
                          className="w-full px-3 py-2 text-sm text-right font-mono border-2 border-[var(--primary)] rounded-lg bg-white focus:ring-2 focus:ring-[var(--primary-light)] focus:outline-none"
                        />
                        {saving && (
                          <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-[var(--primary)]" />
                        )}
                      </div>
                    ) : (
                      <button
                        onClick={() => startEditing(product.sku, Number(product.min_stock) || Number(product.recommended_min_stock) || 0)}
                        className={`group relative flex items-center justify-between gap-2 w-full px-3 py-2 rounded-lg border transition-all ${
                          Number(product.stock_total) < (Number(product.min_stock) || Number(product.recommended_min_stock) || 0)
                            ? 'bg-red-50 border-red-200 hover:border-red-400'
                            : 'bg-stone-50 border-stone-200 hover:border-[var(--primary)]'
                        }`}
                        title="Click para editar"
                      >
                        <span className={`text-sm font-semibold font-mono ${
                          Number(product.stock_total) < (Number(product.min_stock) || Number(product.recommended_min_stock) || 0)
                            ? 'text-[var(--danger)]'
                            : 'text-[var(--foreground)]'
                        }`}>
                          {Number(product.min_stock) > 0
                            ? Number(product.min_stock).toLocaleString()
                            : (Number(product.recommended_min_stock) > 0
                                ? Number(product.recommended_min_stock).toLocaleString()
                                : '—')}
                        </span>
                        <Pencil className="w-3.5 h-3.5 text-stone-400 group-hover:text-[var(--primary)] transition-colors" />
                      </button>
                    )}

                    <div className="flex items-center gap-1.5 flex-wrap">
                      <select
                        value={product.estimation_months || 6}
                        onChange={(e) => updateEstimationPeriod(product.sku, parseInt(e.target.value))}
                        disabled={savingEstimation === product.sku}
                        className={`text-[10px] px-2 py-1 rounded border bg-white cursor-pointer transition-colors ${
                          savingEstimation === product.sku ? 'opacity-50 cursor-wait' : 'border-stone-200 hover:border-[var(--primary)]'
                        }`}
                        title="Período de estimación"
                      >
                        <option value={1}>1M</option>
                        <option value={3}>3M</option>
                        <option value={6}>6M</option>
                      </select>

                      {Number(product.recommended_min_stock) > 0 &&
                       Number(product.min_stock) > 0 &&
                       Number(product.min_stock) !== Number(product.recommended_min_stock) && (
                        <button
                          onClick={() => saveMinStock(product.sku, Number(product.recommended_min_stock))}
                          disabled={saving}
                          className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 rounded transition-colors disabled:opacity-50"
                          title={`Restablecer: ${Number(product.recommended_min_stock).toLocaleString()}`}
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>{Number(product.recommended_min_stock).toLocaleString()}</span>
                        </button>
                      )}

                      <button
                        onClick={() => openTimelineModal(product.sku, product.name)}
                        className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-[var(--secondary)] bg-[var(--secondary-light)] hover:bg-teal-100 rounded transition-colors"
                        title="Ver historial de ventas"
                      >
                        <BarChart3 className="w-3 h-3" />
                        <span>Ventas</span>
                      </button>
                    </div>
                  </div>
                </td>

                {/* Days of Coverage */}
                <td className="px-3 py-3 whitespace-nowrap text-center">
                  {Number(product.days_of_coverage) >= 0 && Number(product.days_of_coverage) < 999 ? (
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold font-mono ${
                        Number(product.days_of_coverage) < 15
                          ? 'bg-red-100 text-red-800'
                          : Number(product.days_of_coverage) < 30
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-green-100 text-green-800'
                      }`}
                      title={`${Number(product.days_of_coverage)} días de cobertura`}
                    >
                      {Number(product.days_of_coverage)}d
                    </span>
                  ) : (
                    <span className="text-stone-300 text-sm" title="Sin ventas registradas">—</span>
                  )}
                </td>

                {/* Earliest Expiration */}
                <td className="px-3 py-3 whitespace-nowrap text-center">
                  {product.earliest_expiration ? (
                    <div className="flex flex-col items-center">
                      <span className={`text-sm font-medium font-mono ${
                        (product.days_to_earliest_expiration ?? 999) < 30
                          ? 'text-[var(--danger)]'
                          : (product.days_to_earliest_expiration ?? 999) < 60
                          ? 'text-amber-700'
                          : 'text-stone-700'
                      }`}>
                        {new Date(product.earliest_expiration).toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: '2-digit' })}
                      </span>
                      <span className="text-[10px] text-stone-500 font-mono">
                        ({product.days_to_earliest_expiration}d)
                      </span>
                    </div>
                  ) : (
                    <span className="text-stone-300 text-sm" title="Sin fecha">—</span>
                  )}
                </td>

                {/* Stock Status */}
                <td className="px-3 py-3 whitespace-nowrap text-center">
                  {(() => {
                    const coverage = Number(product.days_of_coverage) || 999;
                    const daysToExp = product.days_to_earliest_expiration;

                    if (!daysToExp || coverage >= 999) {
                      return <span className="text-stone-300 text-sm">—</span>;
                    }

                    if (coverage > daysToExp) {
                      return (
                        <span
                          className="status-badge status-badge-danger"
                          title={`Stock excede vencimiento por ${coverage - daysToExp} días`}
                        >
                          <AlertTriangle className="w-3 h-3" />
                          Exceso
                        </span>
                      );
                    }

                    if (coverage >= daysToExp * 0.8) {
                      return (
                        <span
                          className="status-badge status-badge-warning"
                          title={`Se venderá ${daysToExp - coverage} días antes del vencimiento`}
                        >
                          <Clock className="w-3 h-3" />
                          Ajustado
                        </span>
                      );
                    }

                    return (
                      <span
                        className="status-badge status-badge-success"
                        title={`Se venderá ${daysToExp - coverage} días antes del vencimiento`}
                      >
                        <CheckCircle className="w-3 h-3" />
                        OK
                      </span>
                    );
                  })()}
                </td>

                {/* Production Needed */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  {Number(product.production_needed) > 0 ? (
                    <span
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[var(--info-light)] text-[var(--info)] font-semibold text-sm font-mono"
                      title={`Producir ${Number(product.production_needed).toLocaleString()} unidades`}
                    >
                      <Plus className="w-3.5 h-3.5" />
                      {Number(product.production_needed).toLocaleString()}
                    </span>
                  ) : (
                    <span className="text-stone-300 text-sm">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="bg-stone-50 px-6 py-4 border-t border-stone-200">
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--foreground-muted)] font-medium">
            Mostrando <span className="text-[var(--foreground)] font-semibold">{sortedProducts.length}</span> {sortedProducts.length === 1 ? 'producto' : 'productos'}
          </span>
          <span className="text-[var(--foreground-muted)]">
            <span className="font-semibold text-[var(--primary)]">{warehouseCodes.length}</span> {warehouseCodes.length === 1 ? 'bodega' : 'bodegas'}
          </span>
        </div>
      </div>

      {/* Hover tooltip - portal */}
      {isMounted && hoveredSku && hoveredSkuDetail && tooltipPosition &&
        createPortal(
          <div
            className="fixed bg-white border border-stone-200 rounded-xl shadow-xl p-4 min-w-[320px] max-w-[400px] animate-fade-in"
            style={{
              top: tooltipPosition.top,
              left: tooltipPosition.left,
              zIndex: 99999,
            }}
            onMouseEnter={() => {}}
            onMouseLeave={() => setHoveredSku(null)}
          >
            <div className="text-xs font-semibold text-[var(--foreground)] mb-3 pb-2 border-b border-stone-200">
              SKUs consolidados en <code className="bg-stone-100 px-1.5 py-0.5 rounded font-mono">{hoveredSku}</code>
            </div>
            <div className="space-y-2">
              {hoveredSkuDetail.map((detail) => (
                <div
                  key={detail.sku}
                  className={`text-xs p-2.5 rounded-lg ${
                    detail.is_mapped
                      ? 'bg-[var(--secondary-lighter)] border border-[var(--secondary-light)]'
                      : 'bg-stone-50 border border-stone-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-semibold text-[var(--foreground)]">{detail.sku}</span>
                    <span className="text-[var(--foreground-muted)] font-mono">{detail.raw_quantity.toLocaleString()} uds</span>
                  </div>
                  {detail.is_mapped ? (
                    <div className="mt-1.5 flex items-center gap-1.5 text-[var(--secondary)]">
                      <span>→</span>
                      <span className="font-mono">{detail.target_sku}</span>
                      {detail.multiplier && detail.multiplier > 1 && (
                        <span className="bg-[var(--secondary)] text-white px-1.5 py-0.5 rounded font-semibold text-[10px]">
                          ×{detail.multiplier}
                        </span>
                      )}
                      <span className="text-stone-500 ml-1 font-mono">= {detail.adjusted_quantity.toLocaleString()} uds</span>
                    </div>
                  ) : (
                    <div className="mt-1 text-stone-500 italic">SKU principal</div>
                  )}
                </div>
              ))}
            </div>
          </div>,
          document.body
        )
      }

      {/* Sales Timeline Modal - portal */}
      {isMounted && timelineModalSku &&
        createPortal(
          <div
            className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-sm"
            onClick={closeTimelineModal}
          >
            <div
              className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-auto animate-fade-in"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="bg-gradient-to-r from-[var(--primary)] to-amber-500 text-white px-6 py-5 rounded-t-2xl">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold flex items-center gap-2">
                      <TrendingUp className="w-5 h-5" />
                      Historial de Ventas
                    </h2>
                    <p className="text-amber-100 text-sm mt-1 font-mono">{timelineModalSku}</p>
                    <p className="text-white/90 text-sm">{timelineModalName}</p>
                  </div>
                  <button
                    onClick={closeTimelineModal}
                    className="text-white/80 hover:text-white p-2 rounded-lg hover:bg-white/10 transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>
              </div>

              {/* Modal Content */}
              <div className="p-6">
                {timelineLoading ? (
                  <div className="flex items-center justify-center py-16">
                    <Loader2 className="w-10 h-10 animate-spin text-[var(--primary)] mr-4" />
                    <span className="text-[var(--foreground-muted)] font-medium">Cargando datos...</span>
                  </div>
                ) : timelineData && timelineData.timeline.length > 0 ? (
                  <>
                    {/* Statistics Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="metric-card">
                        <p className="metric-card-label">Promedio Mensual</p>
                        <p className="metric-card-value text-[var(--primary)]">
                          {timelineData.stats.avg_units.toLocaleString()}
                        </p>
                      </div>
                      <div className="metric-card">
                        <p className="metric-card-label">Máximo</p>
                        <p className="metric-card-value text-[var(--success)]">
                          {timelineData.stats.max_units.toLocaleString()}
                        </p>
                      </div>
                      <div className="metric-card">
                        <p className="metric-card-label">Mínimo</p>
                        <p className="metric-card-value text-[var(--warning)]">
                          {timelineData.stats.min_units.toLocaleString()}
                        </p>
                      </div>
                      <div className="metric-card">
                        <p className="metric-card-label">Desv. Estándar</p>
                        <p className="metric-card-value text-[var(--secondary)]">
                          {timelineData.stats.stddev_units.toLocaleString()}
                        </p>
                      </div>
                    </div>

                    {/* Chart */}
                    <div className="bg-stone-50 rounded-xl p-4 border border-stone-200">
                      <h3 className="text-sm font-semibold text-[var(--foreground)] mb-4 flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-[var(--foreground-muted)]" />
                        Unidades Vendidas — Últimos 12 Meses
                      </h3>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={timelineData.timeline}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
                            <XAxis
                              dataKey="month_name"
                              tick={{ fontSize: 11, fill: '#57534e' }}
                              angle={-45}
                              textAnchor="end"
                              height={60}
                            />
                            <YAxis
                              tick={{ fontSize: 11, fill: '#57534e' }}
                              tickFormatter={(value) => value.toLocaleString()}
                            />
                            <Tooltip
                              formatter={(value: number) => [value.toLocaleString(), 'Unidades']}
                              labelFormatter={(label) => `Mes: ${label}`}
                              contentStyle={{
                                backgroundColor: '#fff',
                                border: '1px solid #e7e5e4',
                                borderRadius: '8px',
                                boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                              }}
                            />
                            <ReferenceLine
                              y={timelineData.stats.avg_units}
                              stroke="#d97706"
                              strokeDasharray="5 5"
                              label={{ value: `Prom: ${timelineData.stats.avg_units.toLocaleString()}`, fill: '#d97706', fontSize: 11 }}
                            />
                            <Line
                              type="monotone"
                              dataKey="units_sold"
                              stroke="#d97706"
                              strokeWidth={2}
                              dot={{ fill: '#d97706', strokeWidth: 2, r: 4 }}
                              activeDot={{ r: 6, stroke: '#b45309', strokeWidth: 2 }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Summary */}
                    <div className="mt-4 p-4 bg-stone-100 rounded-xl">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[var(--foreground-muted)]">
                          Total vendido en {timelineData.stats.months_with_sales} meses: <strong className="text-[var(--foreground)]">{timelineData.stats.total_units.toLocaleString()} unidades</strong>
                        </span>
                        <span className="text-[var(--foreground-muted)]">
                          Ingresos: <strong className="text-[var(--success)]">${(timelineData.stats.total_revenue / 1000000).toFixed(1)}M</strong>
                        </span>
                      </div>
                      <p className="text-xs text-[var(--foreground-muted)] mt-2">
                        El stock mínimo recomendado se basa en el promedio mensual. Ajuste según estacionalidad.
                      </p>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-16">
                    <BarChart3 className="w-12 h-12 text-stone-300 mx-auto mb-4" />
                    <p className="text-lg font-medium text-[var(--foreground)]">No hay datos de ventas</p>
                    <p className="text-sm text-[var(--foreground-muted)]">Este producto no tiene ventas en los últimos 12 meses.</p>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="bg-stone-50 px-6 py-4 rounded-b-2xl border-t border-stone-200 flex justify-end">
                <button
                  onClick={closeTimelineModal}
                  className="px-4 py-2 bg-stone-200 hover:bg-stone-300 text-[var(--foreground)] rounded-lg font-medium transition-colors"
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
