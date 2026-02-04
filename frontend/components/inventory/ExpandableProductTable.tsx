'use client';

import { useState, useMemo } from 'react';
import { toTitleCase } from '@/lib/utils';
import {
  ChevronRight,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Package,
  CheckCircle,
  Clock,
  AlertTriangle,
  XCircle,
  Loader2,
  Boxes,
} from 'lucide-react';

// Types
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

interface ExpandableProductTableProps {
  products: WarehouseProduct[];
  loading?: boolean;
}

type SortField = 'sku' | 'name' | 'category' | 'stock' | 'valor' | 'lot_count' | 'next_expiration';
type SortDirection = 'asc' | 'desc';

// Helper function to get expiration status badge
const ExpirationBadge = ({ status }: { status?: string }) => {
  if (!status) return null;

  const badges = {
    'Valid': { icon: <CheckCircle className="w-3 h-3" />, text: 'Válido', classes: 'bg-[var(--success-light)] text-[var(--success)] border-emerald-200' },
    'Expiring Soon': { icon: <Clock className="w-3 h-3" />, text: 'Por vencer', classes: 'bg-[var(--warning-light)] text-amber-700 border-amber-200' },
    'Expired': { icon: <XCircle className="w-3 h-3" />, text: 'Vencido', classes: 'bg-[var(--danger-light)] text-[var(--danger)] border-red-200' },
    'No Date': { icon: <AlertTriangle className="w-3 h-3" />, text: 'Sin fecha', classes: 'bg-stone-100 text-stone-600 border-stone-200' },
  };

  const badge = badges[status as keyof typeof badges];
  if (!badge) return null;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border rounded-md ${badge.classes}`}>
      {badge.icon}
      <span>{badge.text}</span>
    </span>
  );
};

// Format date helper
const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: '2-digit' });
};

// Expandable Product Row
const ExpandableProductRow = ({ product, index }: { product: WarehouseProduct; index: number }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getPriorityStatus = () => {
    if (!product.lots || product.lots.length === 0) return 'No Date';
    const statuses = product.lots.map(l => l.expiration_status).filter(Boolean);
    if (statuses.includes('Expired')) return 'Expired';
    if (statuses.includes('Expiring Soon')) return 'Expiring Soon';
    if (statuses.includes('Valid')) return 'Valid';
    return 'No Date';
  };

  const getNextExpiration = () => {
    if (!product.lots || product.lots.length === 0) return null;
    const datesWithExpiration = product.lots
      .filter(l => l.days_to_expiration !== null && l.days_to_expiration !== undefined)
      .sort((a, b) => (a.days_to_expiration || 0) - (b.days_to_expiration || 0));

    if (datesWithExpiration.length === 0) return null;
    return datesWithExpiration[0];
  };

  const priorityStatus = getPriorityStatus();
  const nextExpiration = getNextExpiration();

  return (
    <>
      {/* Main Row */}
      <tr
        className="hover:bg-amber-50/50 transition-colors cursor-pointer group"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Expand Icon */}
        <td className="px-3 py-3">
          <button className="text-stone-400 group-hover:text-[var(--primary)] transition-colors">
            <ChevronRight
              className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
            />
          </button>
        </td>

        {/* SKU */}
        <td className="px-3 py-3">
          <code className="text-xs font-mono font-medium text-stone-600 bg-stone-100 px-1.5 py-0.5 rounded">
            {product.sku}
          </code>
        </td>

        {/* Product Name */}
        <td className="px-3 py-3">
          <div className="text-sm font-medium text-[var(--foreground)]">{toTitleCase(product.name)}</div>
          {product.category && (
            <span className="inline-flex items-center px-1.5 py-0.5 mt-1 rounded text-[10px] font-semibold bg-teal-100 text-teal-700 uppercase tracking-wide">
              {toTitleCase(product.category)}
            </span>
          )}
        </td>

        {/* Stock */}
        <td className="px-3 py-3 text-right">
          <div className="text-base font-bold text-[var(--foreground)] font-mono">
            {product.stock !== undefined && product.stock !== null ? product.stock.toLocaleString() : '0'}
          </div>
          {product.percentage_of_warehouse !== undefined && product.percentage_of_product !== undefined && (
            <div className="text-[10px] text-[var(--foreground-muted)] mt-0.5 font-mono">
              {product.percentage_of_warehouse}% bodega · {product.percentage_of_product}% prod
            </div>
          )}
        </td>

        {/* Valor */}
        <td className="px-3 py-3 text-right">
          {product.valor && Number(product.valor) > 0 ? (
            <span className="text-sm font-medium text-[var(--success)] font-mono">
              ${Math.round(Number(product.valor)).toLocaleString('es-CL')}
            </span>
          ) : (
            <span className="text-stone-300">—</span>
          )}
        </td>

        {/* Lot Count */}
        <td className="px-3 py-3 text-center">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-[var(--secondary-light)] text-[var(--secondary)] font-mono">
            {product.lots?.length || 0}
          </span>
        </td>

        {/* Next Expiration */}
        <td className="px-3 py-3 text-center">
          {nextExpiration ? (
            <div>
              <div className={`text-sm font-semibold font-mono ${
                (nextExpiration.days_to_expiration || 0) < 30
                  ? 'text-[var(--danger)]'
                  : (nextExpiration.days_to_expiration || 0) < 60
                  ? 'text-amber-700'
                  : 'text-[var(--foreground)]'
              }`}>
                {nextExpiration.days_to_expiration}d
              </div>
              <div className="text-[10px] text-[var(--foreground-muted)] font-mono">
                {formatDate(nextExpiration.expiration_date)}
              </div>
            </div>
          ) : (
            <span className="text-stone-300">—</span>
          )}
        </td>

        {/* Status */}
        <td className="px-3 py-3">
          <ExpirationBadge status={priorityStatus} />
        </td>
      </tr>

      {/* Expanded Details */}
      {isExpanded && (
        <tr>
          <td colSpan={8} className="px-3 py-4 bg-stone-50">
            <div className="ml-6 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4">
              <h4 className="text-sm font-semibold text-[var(--foreground)] mb-3 flex items-center gap-2">
                <Boxes className="w-4 h-4 text-[var(--secondary)]" />
                <span>Detalles de Lotes ({product.lots?.length || 0})</span>
              </h4>

              {!product.lots || product.lots.length === 0 ? (
                <div className="text-center py-6 text-[var(--foreground-muted)]">
                  <Package className="w-8 h-8 mx-auto mb-2 text-stone-300" />
                  <p className="text-sm">No hay información de lotes disponible.</p>
                </div>
              ) : (
                <div className="overflow-hidden rounded-lg border border-[var(--border)]">
                  <table className="min-w-full">
                    <thead className="bg-stone-100">
                      <tr>
                        <th className="px-3 py-2 text-left text-[10px] font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">
                          Lote
                        </th>
                        <th className="px-3 py-2 text-right text-[10px] font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">
                          Cantidad
                        </th>
                        <th className="px-3 py-2 text-center text-[10px] font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">
                          Vencimiento
                        </th>
                        <th className="px-3 py-2 text-center text-[10px] font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">
                          Días
                        </th>
                        <th className="px-3 py-2 text-center text-[10px] font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">
                          Estado
                        </th>
                        <th className="px-3 py-2 text-center text-[10px] font-semibold text-[var(--foreground-muted)] uppercase tracking-wider">
                          % Producto
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-stone-100">
                      {product.lots.map((lot, idx) => {
                        const lotPercent = ((lot.quantity / product.stock) * 100).toFixed(1);
                        const isUrgent = lot.expiration_status === 'Expired' || lot.expiration_status === 'Expiring Soon';

                        return (
                          <tr key={idx} className={`${isUrgent ? 'bg-amber-50/50' : ''} hover:bg-[var(--primary-lighter)]`}>
                            <td className="px-3 py-2.5 whitespace-nowrap text-sm">
                              <code className="font-mono text-stone-700 bg-stone-100 px-1.5 py-0.5 rounded text-xs">
                                {lot.lot_number || <span className="text-stone-400 italic">Sin número</span>}
                              </code>
                            </td>
                            <td className="px-3 py-2.5 whitespace-nowrap text-sm text-right font-bold text-[var(--foreground)] font-mono">
                              {lot.quantity.toLocaleString()}
                            </td>
                            <td className="px-3 py-2.5 whitespace-nowrap text-sm text-center text-[var(--foreground-muted)] font-mono">
                              {formatDate(lot.expiration_date)}
                            </td>
                            <td className="px-3 py-2.5 whitespace-nowrap text-sm text-center">
                              {lot.days_to_expiration !== null && lot.days_to_expiration !== undefined ? (
                                <span className={`font-semibold font-mono ${
                                  lot.days_to_expiration < 0 ? 'text-[var(--danger)]' :
                                  lot.days_to_expiration < 30 ? 'text-amber-700' :
                                  'text-[var(--success)]'
                                }`}>
                                  {lot.days_to_expiration}d
                                </span>
                              ) : (
                                <span className="text-stone-300">—</span>
                              )}
                            </td>
                            <td className="px-3 py-2.5 whitespace-nowrap text-center">
                              <ExpirationBadge status={lot.expiration_status} />
                            </td>
                            <td className="px-3 py-2.5 whitespace-nowrap">
                              <div className="flex items-center justify-center gap-2">
                                <div className="w-16 bg-stone-200 rounded-full h-1.5">
                                  <div
                                    className="bg-[var(--primary)] h-1.5 rounded-full"
                                    style={{ width: `${Math.min(100, parseFloat(lotPercent))}%` }}
                                  />
                                </div>
                                <span className="text-xs font-medium text-[var(--foreground-muted)] font-mono w-10 text-right">
                                  {lotPercent}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot className="bg-stone-50">
                      <tr>
                        <td className="px-3 py-2 text-xs font-semibold text-[var(--foreground-muted)] uppercase">
                          Total
                        </td>
                        <td className="px-3 py-2 text-sm font-bold text-right text-[var(--foreground)] font-mono">
                          {product.stock.toLocaleString()}
                        </td>
                        <td colSpan={4} className="px-3 py-2 text-xs text-[var(--foreground-muted)] text-center">
                          {product.lots?.length || 0} lotes en bodega
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
};

// Main Table Component
export default function ExpandableProductTable({
  products,
  loading = false,
}: ExpandableProductTableProps) {
  const [sortField, setSortField] = useState<SortField>('category');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const sortedProducts = useMemo(() => {
    return [...products].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      if (sortField === 'lot_count') {
        aVal = a.lots.length;
        bVal = b.lots.length;
      } else if (sortField === 'valor') {
        aVal = Number(a.valor) || 0;
        bVal = Number(b.valor) || 0;
      } else if (sortField === 'next_expiration') {
        const aLot = a.lots.find(l => l.days_to_expiration !== null);
        const bLot = b.lots.find(l => l.days_to_expiration !== null);
        aVal = aLot?.days_to_expiration ?? 9999;
        bVal = bLot?.days_to_expiration ?? 9999;
      } else {
        aVal = a[sortField as keyof typeof a];
        bVal = b[sortField as keyof typeof b];
      }

      if (aVal === null) aVal = '';
      if (bVal === null) bVal = '';

      if (typeof aVal === 'string') {
        const comparison = aVal.localeCompare(bVal);
        return sortDirection === 'asc' ? comparison : -comparison;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [products, sortField, sortDirection]);

  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="w-3.5 h-3.5 text-stone-300 opacity-0 group-hover:opacity-100 transition-opacity" />;
    }
    return sortDirection === 'asc' ? (
      <ChevronUp className="w-3.5 h-3.5 text-[var(--primary)]" />
    ) : (
      <ChevronDown className="w-3.5 h-3.5 text-[var(--primary)]" />
    );
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

  if (loading) {
    return (
      <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden">
        <div className="p-12 flex flex-col items-center justify-center">
          <Loader2 className="w-10 h-10 animate-spin text-[var(--primary)] mb-4" />
          <p className="text-[var(--foreground-muted)] font-medium">Cargando productos...</p>
        </div>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="bg-[var(--surface)] rounded-xl border-2 border-dashed border-[var(--border)] p-12 text-center">
        <Package className="w-12 h-12 text-stone-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-[var(--foreground)] mb-2">No se encontraron productos</h3>
        <p className="text-[var(--foreground-muted)]">No hay productos que coincidan con los filtros.</p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead>
            <tr>
              <th className="px-3 py-3 w-10 bg-stone-50 border-b border-stone-200"></th>
              <HeaderCell label="SKU" field="sku" />
              <HeaderCell label="Producto" field="name" />
              <HeaderCell label="Stock" field="stock" align="right" />
              <HeaderCell label="Valor" field="valor" align="right" />
              <HeaderCell label="Lotes" field="lot_count" align="center" />
              <HeaderCell label="Próx. Venc." field="next_expiration" align="center" />
              <th className="px-3 py-3 text-center text-[11px] font-semibold text-stone-500 uppercase tracking-wider bg-stone-50 border-b border-stone-200">
                Estado
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {sortedProducts.map((product, index) => (
              <ExpandableProductRow key={product.sku} product={product} index={index} />
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="bg-stone-50 px-6 py-4 border-t border-stone-200">
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--foreground-muted)] font-medium">
            Total: <span className="text-[var(--foreground)] font-semibold">{products.length}</span> productos
          </span>
          <span className="text-[10px] text-[var(--foreground-muted)]">
            Click en fila para ver lotes
          </span>
        </div>
      </div>
    </div>
  );
}
