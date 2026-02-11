'use client';

import { useState, useMemo } from 'react';
import { toTitleCase, formatCurrencyFull } from '@/lib/utils';
import {
  Search,
  X,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Package,
  Boxes,
  DollarSign,
  AlertTriangle,
  Upload,
  CheckCircle,
  Clock,
  XCircle,
} from 'lucide-react';

// Types matching the /warehouse/{code} response
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

interface WarehouseSummary {
  total_products: number;
  total_stock: number;
  total_lots: number;
  last_updated: string | null;
  expiration?: ExpirationStats;
  total_valor?: number;
}

interface SpatialProductListProps {
  products: WarehouseProduct[];
  summary: WarehouseSummary | null;
  warehouseName: string;
  warehouseUpdateMethod: string | null;
  onProductClick: (sku: string, name: string) => void;
}

type SortField = 'sku' | 'name' | 'category' | 'stock' | 'valor' | 'lot_count' | 'next_expiration';
type SortDirection = 'asc' | 'desc';

const ExpirationBadge = ({ status }: { status?: string }) => {
  if (!status) return null;
  const badges: Record<string, { icon: React.ReactNode; text: string; classes: string }> = {
    'Valid': { icon: <CheckCircle className="w-3 h-3" />, text: 'Valido', classes: 'bg-[var(--success-light)] text-[var(--success)] border-emerald-200' },
    'Expiring Soon': { icon: <Clock className="w-3 h-3" />, text: 'Por vencer', classes: 'bg-[var(--warning-light)] text-amber-700 border-amber-200' },
    'Expired': { icon: <XCircle className="w-3 h-3" />, text: 'Vencido', classes: 'bg-[var(--danger-light)] text-[var(--danger)] border-red-200' },
    'No Date': { icon: <AlertTriangle className="w-3 h-3" />, text: 'Sin fecha', classes: 'bg-stone-100 text-stone-600 border-stone-200' },
  };
  const badge = badges[status];
  if (!badge) return null;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border rounded-md ${badge.classes}`}>
      {badge.icon}
      <span>{badge.text}</span>
    </span>
  );
};

export default function SpatialProductList({
  products,
  summary,
  warehouseName,
  warehouseUpdateMethod,
  onProductClick,
}: SpatialProductListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortField, setSortField] = useState<SortField>('stock');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const categories = useMemo(() => {
    const cats = new Set(products.map(p => p.category).filter(Boolean));
    return Array.from(cats).sort() as string[];
  }, [products]);

  const filteredProducts = useMemo(() => {
    let filtered = [...products];
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        p.sku.toLowerCase().includes(q) || p.name.toLowerCase().includes(q)
      );
    }
    if (categoryFilter) {
      filtered = filtered.filter(p => p.category === categoryFilter);
    }
    return filtered;
  }, [products, searchQuery, categoryFilter]);

  const sortedProducts = useMemo(() => {
    return [...filteredProducts].sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      if (sortField === 'lot_count') {
        aVal = a.lots?.length ?? 0;
        bVal = b.lots?.length ?? 0;
      } else if (sortField === 'valor') {
        aVal = Number(a.valor) || 0;
        bVal = Number(b.valor) || 0;
      } else if (sortField === 'next_expiration') {
        const aLot = a.lots?.find(l => l.days_to_expiration != null);
        const bLot = b.lots?.find(l => l.days_to_expiration != null);
        aVal = aLot?.days_to_expiration ?? 9999;
        bVal = bLot?.days_to_expiration ?? 9999;
      } else {
        aVal = (a[sortField as keyof WarehouseProduct] as string | number) ?? '';
        bVal = (b[sortField as keyof WarehouseProduct] as string | number) ?? '';
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        const cmp = aVal.localeCompare(bVal);
        return sortDirection === 'asc' ? cmp : -cmp;
      }
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredProducts, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getPriorityStatus = (product: WarehouseProduct): string => {
    if (!product.lots || product.lots.length === 0) return 'No Date';
    const statuses = product.lots.map(l => l.expiration_status).filter(Boolean);
    if (statuses.includes('Expired')) return 'Expired';
    if (statuses.includes('Expiring Soon')) return 'Expiring Soon';
    if (statuses.includes('Valid')) return 'Valid';
    return 'No Date';
  };

  const getNextExpiration = (product: WarehouseProduct) => {
    if (!product.lots || product.lots.length === 0) return null;
    const withDays = product.lots
      .filter(l => l.days_to_expiration != null)
      .sort((a, b) => (a.days_to_expiration || 0) - (b.days_to_expiration || 0));
    return withDays[0] ?? null;
  };

  const alertCount = summary?.expiration
    ? (summary.expiration.expired_lots || 0) + (summary.expiration.expiring_soon_lots || 0)
    : 0;

  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="w-3.5 h-3.5 text-stone-300 opacity-0 group-hover:opacity-100 transition-opacity" />;
    }
    return sortDirection === 'asc'
      ? <ChevronUp className="w-3.5 h-3.5 text-[var(--primary)]" />
      : <ChevronDown className="w-3.5 h-3.5 text-[var(--primary)]" />;
  };

  const HeaderCell = ({ label, field, align = 'left' }: { label: string; field: SortField; align?: 'left' | 'center' | 'right' }) => (
    <th
      className={`px-3 py-3 text-${align} text-[11px] font-semibold text-stone-500 uppercase tracking-wider cursor-pointer hover:bg-stone-100 transition-colors group border-b border-stone-200 bg-stone-50`}
      onClick={() => handleSort(field)}
    >
      <div className={`flex items-center gap-1 ${align === 'center' ? 'justify-center' : align === 'right' ? 'justify-end' : ''}`}>
        <span>{label}</span>
        <SortIndicator field={field} />
      </div>
    </th>
  );

  return (
    <div className="space-y-4">
      {/* Warehouse KPI summary */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 scope-item-stagger" style={{ '--item-index': 0 } as React.CSSProperties}>
          <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-4">
            <div className="flex items-center gap-2 mb-1">
              <Package className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Productos</span>
            </div>
            <p className="text-xl font-bold text-[var(--foreground)] font-mono">{summary.total_products}</p>
          </div>
          <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-4">
            <div className="flex items-center gap-2 mb-1">
              <Boxes className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Stock</span>
            </div>
            <p className="text-xl font-bold text-[var(--foreground)] font-mono">{summary.total_stock.toLocaleString('es-CL')}</p>
          </div>
          <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-4">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-4 h-4 text-purple-600" />
              <span className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Valor</span>
            </div>
            <p className="text-xl font-bold text-[var(--foreground)] font-mono">{formatCurrencyFull(summary.total_valor || 0)}</p>
          </div>
          <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-4">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className={`w-4 h-4 ${alertCount > 0 ? 'text-red-600' : 'text-green-600'}`} />
              <span className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Alertas</span>
            </div>
            <p className={`text-xl font-bold font-mono ${alertCount > 0 ? 'text-red-600' : 'text-green-600'}`}>{alertCount}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-4 scope-item-stagger" style={{ '--item-index': 1 } as React.CSSProperties}>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" />
              <input
                type="text"
                placeholder="Buscar por SKU o nombre..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-[var(--border)] rounded-lg text-sm focus:ring-2 focus:ring-[var(--primary)] focus:border-[var(--primary)]"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                  <X className="w-4 h-4 text-stone-400 hover:text-stone-600" />
                </button>
              )}
            </div>
          </div>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:ring-2 focus:ring-[var(--primary)] focus:border-[var(--primary)]"
          >
            <option value="">Todas las Categorias</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{toTitleCase(cat)}</option>
            ))}
          </select>

          {warehouseUpdateMethod === 'manual_upload' && (
            <button className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg text-sm font-medium hover:bg-[var(--primary-hover)] flex items-center gap-2">
              <Upload className="w-4 h-4" />
              Subir Excel
            </button>
          )}
        </div>
      </div>

      {/* Product Table */}
      <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden shadow-sm scope-item-stagger" style={{ '--item-index': 2 } as React.CSSProperties}>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr>
                <th className="px-3 py-3 w-10 bg-stone-50 border-b border-stone-200" />
                <HeaderCell label="SKU" field="sku" />
                <HeaderCell label="Producto" field="name" />
                <HeaderCell label="Stock" field="stock" align="right" />
                <HeaderCell label="Valor" field="valor" align="right" />
                <HeaderCell label="Lotes" field="lot_count" align="center" />
                <HeaderCell label="Prox. Venc." field="next_expiration" align="center" />
                <th className="px-3 py-3 text-center text-[11px] font-semibold text-stone-500 uppercase tracking-wider bg-stone-50 border-b border-stone-200">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {sortedProducts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center">
                    <div className="flex flex-col items-center text-stone-400">
                      <Package className="w-12 h-12 mb-3" />
                      <p className="font-medium">No hay productos que coincidan</p>
                      <p className="text-sm">Ajusta los filtros para ver resultados</p>
                    </div>
                  </td>
                </tr>
              ) : (
                sortedProducts.map((product, index) => {
                  const priorityStatus = getPriorityStatus(product);
                  const nextExp = getNextExpiration(product);
                  const staggerIdx = Math.min(index, 14);

                  return (
                    <tr
                      key={product.sku}
                      className="hover:bg-amber-50/50 transition-colors cursor-pointer group scope-item-stagger"
                      style={{ '--item-index': staggerIdx + 3 } as React.CSSProperties}
                      onClick={() => onProductClick(product.sku, product.name)}
                    >
                      <td className="px-3 py-3">
                        <span className="text-stone-400 group-hover:text-[var(--primary)] transition-colors">
                          <ChevronDown className="w-4 h-4 rotate-[-90deg]" />
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <code className="text-xs font-mono font-medium text-stone-600 bg-stone-100 px-1.5 py-0.5 rounded">
                          {product.sku}
                        </code>
                      </td>
                      <td className="px-3 py-3">
                        <div className="text-sm font-medium text-[var(--foreground)]">{toTitleCase(product.name)}</div>
                        {product.category && (
                          <span className="inline-flex items-center px-1.5 py-0.5 mt-1 rounded text-[10px] font-semibold bg-teal-100 text-teal-700 uppercase tracking-wide">
                            {toTitleCase(product.category)}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-right">
                        <div className="text-base font-bold text-[var(--foreground)] font-mono">
                          {product.stock.toLocaleString('es-CL')}
                        </div>
                        {product.percentage_of_warehouse !== undefined && (
                          <div className="text-[10px] text-[var(--foreground-muted)] mt-0.5 font-mono">
                            {product.percentage_of_warehouse}% bodega
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-3 text-right">
                        {product.valor && Number(product.valor) > 0 ? (
                          <span className="text-sm font-medium text-[var(--success)] font-mono">
                            ${Math.round(Number(product.valor)).toLocaleString('es-CL')}
                          </span>
                        ) : (
                          <span className="text-stone-300">&mdash;</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-center">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-[var(--secondary-light)] text-[var(--secondary)] font-mono">
                          {product.lots?.length || 0}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center">
                        {nextExp ? (
                          <div>
                            <div className={`text-sm font-semibold font-mono ${
                              (nextExp.days_to_expiration || 0) < 30
                                ? 'text-[var(--danger)]'
                                : (nextExp.days_to_expiration || 0) < 60
                                  ? 'text-amber-700'
                                  : 'text-[var(--foreground)]'
                            }`}>
                              {nextExp.days_to_expiration}d
                            </div>
                            <div className="text-[10px] text-[var(--foreground-muted)] font-mono">
                              {nextExp.expiration_date
                                ? new Date(nextExp.expiration_date).toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: '2-digit' })
                                : '—'}
                            </div>
                          </div>
                        ) : (
                          <span className="text-stone-300">&mdash;</span>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <ExpirationBadge status={priorityStatus} />
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="bg-stone-50 px-4 py-3 border-t border-stone-200">
          <div className="flex items-center justify-between text-sm text-[var(--foreground-muted)]">
            <span>
              Mostrando <strong>{sortedProducts.length}</strong> de <strong>{products.length}</strong> productos
            </span>
            {summary && (
              <span>
                Stock: <strong className="text-[var(--primary)]">{summary.total_stock.toLocaleString('es-CL')} uds</strong>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
