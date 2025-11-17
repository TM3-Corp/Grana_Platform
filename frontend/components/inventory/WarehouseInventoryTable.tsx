'use client';

import { useState, useMemo } from 'react';

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

interface WarehouseInventoryTableProps {
  products: InventoryProduct[] | WarehouseSpecificProduct[];
  mode: 'general' | 'warehouse';
  loading?: boolean;
}

type SortField = 'sku' | 'name' | 'category' | 'stock_total' | 'stock' | keyof WarehouseStock;
type SortDirection = 'asc' | 'desc';

export default function WarehouseInventoryTable({ products, mode, loading = false }: WarehouseInventoryTableProps) {
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
      let aVal: any = a[sortField as keyof typeof a];
      let bVal: any = b[sortField as keyof typeof b];

      // Handle null values
      if (aVal === null) aVal = '';
      if (bVal === null) bVal = '';

      // String comparison
      if (typeof aVal === 'string') {
        const comparison = aVal.localeCompare(bVal);
        return sortDirection === 'asc' ? comparison : -comparison;
      }

      // Number comparison
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [products, sortField, sortDirection]);

  // Sort indicator
  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return (
      <span className="ml-1 text-xs">
        {sortDirection === 'asc' ? '↑' : '↓'}
      </span>
    );
  };

  // Table header cell with sorting
  const SortableHeader = ({ field, label }: { field: SortField; label: string }) => (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center">
        {label}
        <SortIndicator field={field} />
      </div>
    </th>
  );

  // Format stock with color coding
  const StockCell = ({ value }: { value: number }) => {
    const colorClass = value === 0 ? 'text-gray-400' : value > 100 ? 'text-green-600 font-semibold' : 'text-gray-900';
    return <span className={colorClass}>{value.toLocaleString()}</span>;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No hay productos en el inventario
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 bg-white shadow-sm rounded-lg">
        <thead className="bg-gray-50">
          <tr>
            <SortableHeader field="sku" label="SKU" />
            <SortableHeader field="name" label="Producto" />
            <SortableHeader field="category" label="Familia" />

            {mode === 'general' ? (
              <>
                <SortableHeader field="stock_amplifica_centro" label="Centro" />
                <SortableHeader field="stock_amplifica_lareina" label="La Reina" />
                <SortableHeader field="stock_amplifica_lobarnechea" label="Lo Barnechea" />
                <SortableHeader field="stock_amplifica_quilicura" label="Quilicura" />
                <SortableHeader field="stock_packner" label="Packner" />
                <SortableHeader field="stock_orinoco" label="Orinoco" />
                <SortableHeader field="stock_mercadolibre" label="Mercado Libre" />
                <SortableHeader field="stock_total" label="Total" />
              </>
            ) : (
              <>
                <SortableHeader field="stock" label="Stock" />
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                  % del Total
                </th>
              </>
            )}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedProducts.map((product, index) => (
            <tr key={`${product.sku}-${index}`} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 whitespace-nowrap text-sm font-mono text-gray-900">
                {product.sku}
              </td>
              <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate" title={product.name}>
                {product.name}
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                {product.category || '-'}
              </td>

              {mode === 'general' ? (
                <>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                    <StockCell value={(product as InventoryProduct).stock_amplifica_centro} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                    <StockCell value={(product as InventoryProduct).stock_amplifica_lareina} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                    <StockCell value={(product as InventoryProduct).stock_amplifica_lobarnechea} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                    <StockCell value={(product as InventoryProduct).stock_amplifica_quilicura} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                    <StockCell value={(product as InventoryProduct).stock_packner} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                    <StockCell value={(product as InventoryProduct).stock_orinoco} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                    <StockCell value={(product as InventoryProduct).stock_mercadolibre} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right font-semibold">
                    <StockCell value={(product as InventoryProduct).stock_total} />
                  </td>
                </>
              ) : (
                <>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                    <StockCell value={(product as WarehouseSpecificProduct).stock} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600">
                    {Number((product as WarehouseSpecificProduct).percentage_of_total).toFixed(1)}%
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Summary footer */}
      <div className="mt-4 px-4 py-3 bg-gray-50 rounded-lg">
        <div className="text-sm text-gray-600">
          <span className="font-semibold">{sortedProducts.length}</span> productos mostrados
          {mode === 'general' && (
            <>
              {' • '}
              <span className="font-semibold">
                {sortedProducts
                  .reduce((sum, p) => sum + (p as InventoryProduct).stock_total, 0)
                  .toLocaleString()}
              </span>{' '}
              unidades totales
            </>
          )}
        </div>
      </div>
    </div>
  );
}
