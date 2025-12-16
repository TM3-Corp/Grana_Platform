'use client';

import { useState, useMemo } from 'react';
import { toTitleCase } from '@/lib/utils';

// Types for dynamic warehouse structure
interface DynamicInventoryProduct {
  sku: string;
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
        aVal = a.stock_total;
        bVal = b.stock_total;
      } else if (sortField === 'lot_count') {
        aVal = a.lot_count;
        bVal = b.lot_count;
      } else if (sortField === 'min_stock') {
        aVal = a.min_stock || 0;
        bVal = b.min_stock || 0;
      } else if (sortField === 'valor') {
        aVal = a.valor || 0;
        bVal = b.valor || 0;
      } else if (warehouseCodes.includes(sortField)) {
        aVal = a.warehouses?.[sortField] || 0;
        bVal = b.warehouses?.[sortField] || 0;
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
                {/* Sticky SKU column */}
                <td className="sticky left-0 z-10 bg-white px-4 py-3 whitespace-nowrap text-sm font-mono font-semibold text-blue-600 border-r border-gray-200">
                  {product.sku}
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
                        onClick={() => startEditing(product.sku, product.min_stock || product.recommended_min_stock || 0)}
                        className={`inline-flex items-center justify-center min-w-[80px] px-3 py-1 rounded-md font-medium cursor-pointer transition-all hover:ring-2 hover:ring-blue-400 ${
                          product.stock_total < (product.min_stock || product.recommended_min_stock || 0)
                            ? 'bg-red-100 text-red-800 ring-2 ring-red-300'
                            : product.min_stock && product.min_stock > 0
                              ? 'bg-blue-100 text-blue-800'  // User-edited value
                              : 'bg-gray-100 text-gray-700'
                        }`}
                        title={`Click para editar.${product.min_stock ? ` Valor actual: ${product.min_stock.toLocaleString()}` : ''} Recomendado: ${(product.recommended_min_stock || 0).toLocaleString()}`}
                      >
                        {product.min_stock ? product.min_stock.toLocaleString() : (product.recommended_min_stock ? product.recommended_min_stock.toLocaleString() : '-')}
                      </span>
                    )}
                    {/* Show recommended value below ONLY if user edited to a different value */}
                    {product.recommended_min_stock && product.recommended_min_stock > 0 &&
                     product.min_stock && product.min_stock !== product.recommended_min_stock && (
                      <span
                        className="text-xs text-amber-600 font-medium"
                        title={`Recomendación basada en promedio de ventas de los últimos 6 meses`}
                      >
                        📊 Rec: {product.recommended_min_stock.toLocaleString()}
                      </span>
                    )}
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
    </div>
  );
}
