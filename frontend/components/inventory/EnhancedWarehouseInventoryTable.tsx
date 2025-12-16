'use client';

import { useState, useMemo } from 'react';
import { toTitleCase } from '@/lib/utils';

// Types
interface WarehouseStock {
  stock_amplifica_centro: number;
  stock_amplifica_lareina: number;
  stock_amplifica_lobarnechea: number;
  stock_amplifica_quilicura: number;
  stock_packner: number;
  stock_orinoco: number;
  stock_mercadolibre: number;
  stock_total: number;
}

interface InventoryProduct extends WarehouseStock {
  sku: string;
  name: string;
  category: string | null;
  subfamily: string | null;
  last_updated: string | null;
}

interface WarehouseSpecificProduct {
  sku: string;
  name: string;
  category: string | null;
  stock: number;
  percentage_of_total: number;
}

interface EnhancedWarehouseInventoryTableProps {
  products: InventoryProduct[] | WarehouseSpecificProduct[];
  mode: 'general' | 'warehouse' | 'amplifica';
  loading?: boolean;
}

type SortField = 'sku' | 'name' | 'category' | 'stock_total' | 'stock' | keyof WarehouseStock;
type SortDirection = 'asc' | 'desc';

export default function EnhancedWarehouseInventoryTable({
  products,
  mode,
  loading = false,
}: EnhancedWarehouseInventoryTableProps) {
  const [sortField, setSortField] = useState<SortField>('category');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [hoveredSegment, setHoveredSegment] = useState<{ row: number; location: string; count: number; pct: number } | null>(null);

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
      let aVal: any = a[sortField as keyof typeof a];
      let bVal: any = b[sortField as keyof typeof b];

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

  // Sort indicator with animation
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

  // Table header cell with sorting
  const SortableHeader = ({ field, label, align = 'left' }: { field: SortField; label: string; align?: 'left' | 'right' | 'center' }) => (
    <th
      className={`px-3 py-3 text-xs font-semibold text-gray-700 uppercase tracking-tight cursor-pointer
        hover:bg-gray-100 transition-colors group bg-gray-50 backdrop-blur-sm
        ${align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'}
      `}
      onClick={() => handleSort(field)}
    >
      <div className={`flex items-center gap-1 ${align === 'right' ? 'justify-end' : align === 'center' ? 'justify-center' : ''}`}>
        <span className="whitespace-nowrap">{label}</span>
        <SortIndicator field={field} />
      </div>
    </th>
  );

  // Calculate max stock per familia for context-aware coloring
  const maxStockByFamilia = useMemo(() => {
    const familiaMaxMap = new Map<string, number>();

    products.forEach((product) => {
      const familia = product.category || 'Sin Familia';
      const stockValue =
        mode === 'general'
          ? (product as InventoryProduct).stock_total
          : mode === 'amplifica'
          ? (product as InventoryProduct).stock_amplifica_centro +
            (product as InventoryProduct).stock_amplifica_lareina +
            (product as InventoryProduct).stock_amplifica_lobarnechea +
            (product as InventoryProduct).stock_amplifica_quilicura
          : (product as WarehouseSpecificProduct).stock;

      const currentMax = familiaMaxMap.get(familia) || 0;
      if (stockValue > currentMax) {
        familiaMaxMap.set(familia, stockValue);
      }
    });

    return familiaMaxMap;
  }, [products, mode]);

  // Stock cell with color-coded numbers based on familia max
  const EnhancedStockCell = ({
    value,
    familia,
  }: {
    value: number | undefined;
    familia: string;
  }) => {
    const safeValue = value ?? 0;
    const maxInFamilia = maxStockByFamilia.get(familia || 'Sin Familia') || 1;

    // Color based on percentage of max in familia
    const percentage = (safeValue / maxInFamilia) * 100;

    const colorClass =
      safeValue === 0
        ? 'text-gray-400'
        : percentage >= 70
        ? 'text-green-600 font-semibold'
        : percentage >= 30
        ? 'text-amber-600 font-medium'
        : 'text-red-600 font-medium';

    return (
      <span className={`${colorClass} text-sm tabular-nums`}>
        {safeValue.toLocaleString()}
      </span>
    );
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="animate-pulse flex space-x-4 bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex-1 space-y-3">
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
              <div className="h-3 bg-gray-200 rounded w-3/4"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Empty state
  if (products.length === 0) {
    return (
      <div className="text-center py-16 bg-white rounded-xl border-2 border-dashed border-gray-300">
        <div className="text-6xl mb-4">📦</div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No hay productos en el inventario</h3>
        <p className="text-sm text-gray-500">Intenta ajustar los filtros o agrega productos al sistema</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Table Container with max height for scrolling */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm bg-white max-h-[calc(100vh-320px)] overflow-y-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="sticky top-0 z-20 bg-gray-50 shadow-md">
            {/* Legend row for Amplifica mode - Full coverage, no gaps */}
            {mode === 'amplifica' && (
              <tr className="bg-gradient-to-r from-blue-50 to-indigo-50">
                <th colSpan={100} className="px-4 py-2 text-left border-b border-gray-200">
                  <div className="flex items-center gap-6 flex-wrap">
                    <span className="text-xs font-semibold text-gray-700">Leyenda:</span>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded bg-blue-500 shadow-sm"></div>
                      <span className="text-xs text-gray-700 font-medium">Centro</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded bg-green-500 shadow-sm"></div>
                      <span className="text-xs text-gray-700 font-medium">La Reina</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded bg-purple-500 shadow-sm"></div>
                      <span className="text-xs text-gray-700 font-medium">Lo Barnechea</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded bg-orange-500 shadow-sm"></div>
                      <span className="text-xs text-gray-700 font-medium">Quilicura</span>
                    </div>
                  </div>
                </th>
              </tr>
            )}
            {/* Column headers row */}
            <tr>
              <SortableHeader field="sku" label="SKU" />
              <SortableHeader field="name" label="Producto" />
              <SortableHeader field="category" label="Familia" />

              {mode === 'general' ? (
                <>
                  <SortableHeader field="stock_amplifica_centro" label="Centro" align="right" />
                  <SortableHeader field="stock_amplifica_lareina" label="L. Reina" align="right" />
                  <SortableHeader field="stock_amplifica_lobarnechea" label="L. Barn." align="right" />
                  <SortableHeader field="stock_amplifica_quilicura" label="Quilicura" align="right" />
                  <SortableHeader field="stock_packner" label="Packner" align="right" />
                  <SortableHeader field="stock_orinoco" label="Orinoco" align="right" />
                  <SortableHeader field="stock_mercadolibre" label="ML" align="right" />
                  <SortableHeader field="stock_total" label="Total" align="right" />
                </>
              ) : mode === 'amplifica' ? (
                <>
                  <SortableHeader field="stock_amplifica_centro" label="Centro" align="right" />
                  <SortableHeader field="stock_amplifica_lareina" label="L. Reina" align="right" />
                  <SortableHeader field="stock_amplifica_lobarnechea" label="L. Barn." align="right" />
                  <SortableHeader field="stock_amplifica_quilicura" label="Quilicura" align="right" />
                  <SortableHeader field="stock_total" label="Total" align="right" />
                  <th className="px-3 py-3 text-xs font-semibold text-gray-700 uppercase tracking-tight bg-gray-50">
                    Distribución
                  </th>
                </>
              ) : (
                <>
                  <SortableHeader field="stock" label="Stock" align="right" />
                </>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sortedProducts.map((product, index) => (
              <tr
                key={`${product.sku}-${index}`}
                className={`
                  transition-all duration-150 hover:bg-blue-50
                  ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                `}
              >
                <td className="px-3 py-3 whitespace-nowrap">
                  <div className="text-xs font-mono font-medium text-gray-900">{product.sku}</div>
                </td>
                <td className="px-3 py-3 max-w-[180px]">
                  <div className="text-xs text-gray-900 line-clamp-2 leading-tight" title={toTitleCase(product.name)}>
                    {toTitleCase(product.name)}
                  </div>
                  {(product as InventoryProduct).subfamily && (
                    <div className="text-xs text-gray-400 mt-0.5 truncate">
                      {toTitleCase((product as InventoryProduct).subfamily)}
                    </div>
                  )}
                </td>
                <td className="px-3 py-3 whitespace-nowrap">
                  {product.category && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {toTitleCase(product.category)}
                    </span>
                  )}
                </td>

                {mode === 'general' ? (
                  <>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_amplifica_centro}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_amplifica_lareina}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_amplifica_lobarnechea}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_amplifica_quilicura}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_packner}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_orinoco}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_mercadolibre}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <span className="text-sm font-bold text-blue-600 tabular-nums">
                        {(product as InventoryProduct).stock_total.toLocaleString()}
                      </span>
                    </td>
                  </>
                ) : mode === 'amplifica' ? (
                  <>
                    {/* Amplifica mode: Show only 4 Amplifica columns + stacked bar */}
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_amplifica_centro}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_amplifica_lareina}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_amplifica_lobarnechea}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as InventoryProduct).stock_amplifica_quilicura}
                        
                      />
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-3">
                        <span className="text-sm font-bold text-blue-600">
                          {(
                            ((product as InventoryProduct).stock_amplifica_centro ?? 0) +
                            ((product as InventoryProduct).stock_amplifica_lareina ?? 0) +
                            ((product as InventoryProduct).stock_amplifica_lobarnechea ?? 0) +
                            ((product as InventoryProduct).stock_amplifica_quilicura ?? 0)
                          ).toLocaleString()}
                        </span>
                      </div>
                    </td>
                    <td className="px-2 py-3">
                      {/* Stacked horizontal bar showing distribution */}
                      {(() => {
                        const centro = (product as InventoryProduct).stock_amplifica_centro ?? 0;
                        const lareina = (product as InventoryProduct).stock_amplifica_lareina ?? 0;
                        const lobarnechea = (product as InventoryProduct).stock_amplifica_lobarnechea ?? 0;
                        const quilicura = (product as InventoryProduct).stock_amplifica_quilicura ?? 0;
                        const total = centro + lareina + lobarnechea + quilicura;

                        if (total === 0) return <span className="text-xs text-gray-400">Sin stock</span>;

                        const centroPct = (centro / total) * 100;
                        const lareinaPct = (lareina / total) * 100;
                        const lobarnecheaPct = (lobarnechea / total) * 100;
                        const quilicuraPct = (quilicura / total) * 100;

                        return (
                          <div className="w-full max-w-[150px] relative">
                            <div className="h-6 flex rounded-lg overflow-hidden shadow-sm">
                              {centro > 0 && (
                                <div
                                  className="bg-blue-500 hover:bg-blue-600 transition-colors cursor-pointer relative"
                                  style={{ width: `${centroPct}%` }}
                                  onMouseEnter={() => setHoveredSegment({ row: index, location: 'Centro', count: centro, pct: centroPct })}
                                  onMouseLeave={() => setHoveredSegment(null)}
                                />
                              )}
                              {lareina > 0 && (
                                <div
                                  className="bg-green-500 hover:bg-green-600 transition-colors cursor-pointer relative"
                                  style={{ width: `${lareinaPct}%` }}
                                  onMouseEnter={() => setHoveredSegment({ row: index, location: 'La Reina', count: lareina, pct: lareinaPct })}
                                  onMouseLeave={() => setHoveredSegment(null)}
                                />
                              )}
                              {lobarnechea > 0 && (
                                <div
                                  className="bg-purple-500 hover:bg-purple-600 transition-colors cursor-pointer relative"
                                  style={{ width: `${lobarnecheaPct}%` }}
                                  onMouseEnter={() => setHoveredSegment({ row: index, location: 'Lo Barnechea', count: lobarnechea, pct: lobarnecheaPct })}
                                  onMouseLeave={() => setHoveredSegment(null)}
                                />
                              )}
                              {quilicura > 0 && (
                                <div
                                  className="bg-orange-500 hover:bg-orange-600 transition-colors cursor-pointer relative"
                                  style={{ width: `${quilicuraPct}%` }}
                                  onMouseEnter={() => setHoveredSegment({ row: index, location: 'Quilicura', count: quilicura, pct: quilicuraPct })}
                                  onMouseLeave={() => setHoveredSegment(null)}
                                />
                              )}
                            </div>

                            {/* Custom tooltip */}
                            {hoveredSegment && hoveredSegment.row === index && (
                              <div className="absolute left-0 -top-16 z-30 bg-gray-900 text-white px-3 py-2 rounded-lg shadow-xl text-xs whitespace-nowrap animate-fadeIn">
                                <div className="font-semibold text-blue-200 mb-1">{hoveredSegment.location}</div>
                                <div className="flex items-center gap-2">
                                  <span className="text-gray-300">Stock:</span>
                                  <span className="font-bold">{hoveredSegment.count.toLocaleString()}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-gray-300">Porcentaje:</span>
                                  <span className="font-bold text-green-400">{hoveredSegment.pct.toFixed(1)}%</span>
                                </div>
                                {/* Arrow pointing down */}
                                <div className="absolute left-6 -bottom-1 w-2 h-2 bg-gray-900 transform rotate-45"></div>
                              </div>
                            )}
                          </div>
                        );
                      })()}
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-2 py-3 whitespace-nowrap text-right">
                      <EnhancedStockCell familia={product.category || 'Sin Familia'}
                        value={(product as WarehouseSpecificProduct).stock}

                      />
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Enhanced Summary Footer */}
      <div className="flex items-center justify-between bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl p-6 border border-gray-200">
        <div className="flex items-center gap-6">
          <div>
            <div className="text-sm text-gray-600">Productos Mostrados</div>
            <div className="text-2xl font-bold text-gray-900">{sortedProducts.length.toLocaleString()}</div>
          </div>
          {mode === 'general' && (
            <>
              <div className="w-px h-12 bg-gray-300" />
              <div>
                <div className="text-sm text-gray-600">Stock Total</div>
                <div className="text-2xl font-bold text-blue-600">
                  {sortedProducts
                    .reduce((sum, p) => sum + (p as InventoryProduct).stock_total, 0)
                    .toLocaleString()}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Quick Stats */}
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs text-gray-500">Con Stock</div>
            <div className="text-lg font-semibold text-green-600">
              {mode === 'general'
                ? sortedProducts.filter((p) => (p as InventoryProduct).stock_total > 0).length
                : sortedProducts.filter((p) => (p as WarehouseSpecificProduct).stock > 0).length}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-500">Sin Stock</div>
            <div className="text-lg font-semibold text-gray-400">
              {mode === 'general'
                ? sortedProducts.filter((p) => (p as InventoryProduct).stock_total === 0).length
                : sortedProducts.filter((p) => (p as WarehouseSpecificProduct).stock === 0).length}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
