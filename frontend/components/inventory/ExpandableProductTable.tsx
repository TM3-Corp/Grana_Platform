'use client';

import { useState, useMemo } from 'react';

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
}

interface ExpandableProductTableProps {
  products: WarehouseProduct[];
  loading?: boolean;
}

type SortField = 'sku' | 'name' | 'category' | 'stock' | 'lot_count' | 'next_expiration';
type SortDirection = 'asc' | 'desc';

// Helper function to get expiration status badge
const ExpirationBadge = ({ status }: { status?: string }) => {
  if (!status) return null;

  const badges = {
    'Valid': { icon: '✅', text: 'Válido', color: 'bg-green-100 text-green-700 border-green-200' },
    'Expiring Soon': { icon: '⏰', text: 'Próximo a vencer', color: 'bg-amber-100 text-amber-700 border-amber-200' },
    'Expired': { icon: '❌', text: 'Vencido', color: 'bg-red-100 text-red-700 border-red-200' },
    'No Date': { icon: '⚠️', text: 'Sin fecha', color: 'bg-gray-100 text-gray-700 border-gray-200' },
  };

  const badge = badges[status as keyof typeof badges];
  if (!badge) return null;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border rounded ${badge.color}`}>
      <span>{badge.icon}</span>
      <span>{badge.text}</span>
    </span>
  );
};

// Format date helper
const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('es-CL', { day: 'numeric', month: 'short', year: 'numeric' });
};

// Expandable Product Row
const ExpandableProductRow = ({ product, index }: { product: WarehouseProduct; index: number }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Get priority status (most urgent expiration)
  const getPriorityStatus = () => {
    if (!product.lots || product.lots.length === 0) return 'No Date';
    const statuses = product.lots.map(l => l.expiration_status).filter(Boolean);
    if (statuses.includes('Expired')) return 'Expired';
    if (statuses.includes('Expiring Soon')) return 'Expiring Soon';
    if (statuses.includes('Valid')) return 'Valid';
    return 'No Date';
  };

  // Get next expiration date
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
  const bgColor = index % 2 === 0 ? 'bg-white' : 'bg-gray-50';

  return (
    <>
      {/* Main Row */}
      <tr
        className={`${bgColor} hover:bg-blue-50 transition-colors cursor-pointer group`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Expand Icon */}
        <td className="px-4 py-3">
          <button className="text-gray-600 hover:text-blue-600 transition-colors">
            <svg
              className={`w-5 h-5 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </td>

        {/* SKU */}
        <td className="px-4 py-3">
          <div className="text-sm font-mono text-gray-900">{product.sku}</div>
        </td>

        {/* Product Name */}
        <td className="px-4 py-3">
          <div className="text-sm font-medium text-gray-900">{product.name}</div>
          {product.category && (
            <div className="text-xs text-gray-500 mt-0.5">{product.category}</div>
          )}
        </td>

        {/* Stock */}
        <td className="px-4 py-3 text-center">
          <div className="text-sm font-semibold text-gray-900">
            {product.stock !== undefined && product.stock !== null ? product.stock.toLocaleString() : '0'} u.
          </div>
          {product.percentage_of_warehouse !== undefined && product.percentage_of_product !== undefined ? (
            <div className="text-xs text-gray-600 mt-1">
              <span className="font-medium">Bodega:</span> {product.percentage_of_warehouse}%
              <span className="text-gray-400 mx-1">|</span>
              <span className="font-medium">Producto:</span> {product.percentage_of_product}%
            </div>
          ) : null}
        </td>

        {/* Lot Count */}
        <td className="px-4 py-3 text-center">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            {product.lots?.length || 0} {(product.lots?.length || 0) === 1 ? 'lote' : 'lotes'}
          </span>
        </td>

        {/* Next Expiration */}
        <td className="px-4 py-3 text-center">
          {nextExpiration ? (
            <div>
              <div className="text-sm font-medium text-gray-900">
                {nextExpiration.days_to_expiration}d
              </div>
              <div className="text-xs text-gray-500">{formatDate(nextExpiration.expiration_date)}</div>
            </div>
          ) : (
            <div className="text-xs text-gray-500">-</div>
          )}
        </td>

        {/* Status */}
        <td className="px-4 py-3">
          <ExpirationBadge status={priorityStatus} />
        </td>
      </tr>

      {/* Expanded Details */}
      {isExpanded && (
        <tr className={bgColor}>
          <td colSpan={7} className="px-4 py-4">
            <div className="ml-8 bg-gray-50 border border-gray-200 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <span>📦</span>
                <span>Detalles de Lotes ({product.lots?.length || 0})</span>
              </h4>

              {!product.lots || product.lots.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p className="text-sm">No hay información de lotes disponible para este producto.</p>
                </div>
              ) : (
                <div className="overflow-hidden rounded-lg border border-gray-200">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                          Lote
                        </th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                          Cantidad
                        </th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">
                          Vencimiento
                        </th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">
                          Días Restantes
                        </th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">
                          Estado
                        </th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">
                          % del Producto
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {product.lots.map((lot, idx) => {
                      const lotPercent = ((lot.quantity / product.stock) * 100).toFixed(1);
                      const isUrgent = lot.expiration_status === 'Expired' || lot.expiration_status === 'Expiring Soon';

                      return (
                        <tr key={idx} className={`${isUrgent ? 'bg-amber-50' : ''} hover:bg-gray-50`}>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            <span className="font-mono text-gray-900">
                              {lot.lot_number || <span className="text-gray-400 italic">Sin número</span>}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-right font-semibold text-gray-900">
                            {lot.quantity.toLocaleString()} u.
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-center text-gray-700">
                            {formatDate(lot.expiration_date)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                            {lot.days_to_expiration !== null && lot.days_to_expiration !== undefined ? (
                              <span className={`font-medium ${
                                lot.days_to_expiration < 0 ? 'text-red-600' :
                                lot.days_to_expiration < 30 ? 'text-amber-600' :
                                'text-green-600'
                              }`}>
                                {lot.days_to_expiration}d
                              </span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                            <ExpirationBadge status={lot.expiration_status} />
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                            <div className="flex items-center justify-center gap-2">
                              <div className="w-16 bg-gray-200 rounded-full h-2">
                                <div
                                  className="bg-blue-600 h-2 rounded-full"
                                  style={{ width: `${lotPercent}%` }}
                                ></div>
                              </div>
                              <span className="text-xs font-medium text-gray-600">{lotPercent}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                      })}
                    </tbody>
                    <tfoot className="bg-gray-50">
                      <tr>
                        <td className="px-4 py-2 text-sm font-semibold text-gray-700">
                          TOTAL
                        </td>
                        <td className="px-4 py-2 text-sm font-bold text-right text-gray-900">
                          {product.stock.toLocaleString()} u.
                        </td>
                        <td colSpan={4} className="px-4 py-2 text-sm text-gray-500 text-center">
                          {product.lots?.length || 0} {(product.lots?.length || 0) === 1 ? 'lote' : 'lotes'} en bodega
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}

              {/* Last Updated */}
              <div className="mt-3 text-xs text-gray-500 flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>
                  Última actualización: {formatDate(product.lots[0]?.last_updated)}
                </span>
              </div>
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

  // Sorting handler
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Sorted products
  const sortedProducts = useMemo(() => {
    const sorted = [...products].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      if (sortField === 'lot_count') {
        aVal = a.lots.length;
        bVal = b.lots.length;
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

    return sorted;
  }, [products, sortField, sortDirection]);

  // Sort indicator
  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return (
        <svg className="w-4 h-4 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return (
      <svg
        className={`w-4 h-4 text-blue-600 transition-transform duration-200 ${sortDirection === 'desc' ? 'rotate-180' : ''}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    );
  };

  // Loading state
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Cargando productos...</span>
        </div>
      </div>
    );
  }

  // Empty state
  if (products.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="text-center text-gray-500">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <p className="mt-2 text-sm">No se encontraron productos</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
            <tr>
              <th className="px-4 py-3 w-12"></th>

              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-200 transition-colors group"
                onClick={() => handleSort('sku')}
              >
                <div className="flex items-center gap-2">
                  <span>SKU</span>
                  <SortIndicator field="sku" />
                </div>
              </th>

              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-200 transition-colors group"
                onClick={() => handleSort('name')}
              >
                <div className="flex items-center gap-2">
                  <span>Producto</span>
                  <SortIndicator field="name" />
                </div>
              </th>

              <th
                className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-200 transition-colors group"
                onClick={() => handleSort('stock')}
              >
                <div className="flex items-center justify-center gap-2">
                  <span>Stock</span>
                  <SortIndicator field="stock" />
                </div>
              </th>

              <th
                className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-200 transition-colors group"
                onClick={() => handleSort('lot_count')}
              >
                <div className="flex items-center justify-center gap-2">
                  <span>Lotes</span>
                  <SortIndicator field="lot_count" />
                </div>
              </th>

              <th
                className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-200 transition-colors group"
                onClick={() => handleSort('next_expiration')}
              >
                <div className="flex items-center justify-center gap-2">
                  <span>Próximo Vencimiento</span>
                  <SortIndicator field="next_expiration" />
                </div>
              </th>

              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">
                Estado
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sortedProducts.map((product, index) => (
              <ExpandableProductRow key={product.sku} product={product} index={index} />
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
        <div className="text-sm text-gray-600 flex items-center justify-between">
          <span>Total: {products.length} productos</span>
          <span className="text-xs text-gray-500">Click en una fila para ver detalles de lotes</span>
        </div>
      </div>
    </div>
  );
}
