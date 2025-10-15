'use client';

import React, { useState, useEffect } from 'react';

interface ConsolidatedInventory {
  base_product_id: number;
  base_sku: string;
  base_name: string;
  base_source: string | null;
  base_unit_price: number | null;
  base_direct_stock: number;
  num_variants: number;
  variant_stock_as_units: number;
  total_units_available: number;
  stock_status: 'OVERSOLD' | 'OUT_OF_STOCK' | 'LOW_STOCK' | 'OK';
  inventory_value: number | null;
}

const stockStatusConfig = {
  OVERSOLD: {
    label: 'Sobreventa',
    color: 'text-red-700 bg-red-50 border-red-200',
    icon: '🔴',
  },
  OUT_OF_STOCK: {
    label: 'Sin Stock',
    color: 'text-gray-700 bg-gray-50 border-gray-200',
    icon: '⚪',
  },
  LOW_STOCK: {
    label: 'Stock Bajo',
    color: 'text-yellow-700 bg-yellow-50 border-yellow-200',
    icon: '🟡',
  },
  OK: {
    label: 'OK',
    color: 'text-green-700 bg-green-50 border-green-200',
    icon: '🟢',
  },
};

export default function ConsolidatedInventoryTable() {
  const [inventory, setInventory] = useState<ConsolidatedInventory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/product-mapping/consolidated-inventory`);

      if (!response.ok) {
        throw new Error('Error al cargar inventario consolidado');
      }

      const data = await response.json();
      setInventory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const filteredInventory = inventory.filter((item) => {
    if (filterStatus === 'all') return true;
    return item.stock_status === filterStatus;
  });

  const formatCurrency = (value: number | null) => {
    if (value === null) return 'N/A';
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(value);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center p-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">❌ {error}</p>
      </div>
    );
  }

  const statsData = {
    total: inventory.length,
    oversold: inventory.filter((i) => i.stock_status === 'OVERSOLD').length,
    lowStock: inventory.filter((i) => i.stock_status === 'LOW_STOCK').length,
    ok: inventory.filter((i) => i.stock_status === 'OK').length,
  };

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Productos</div>
          <div className="text-2xl font-bold">{statsData.total}</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-sm text-red-600">🔴 Sobrevendidos</div>
          <div className="text-2xl font-bold text-red-700">{statsData.oversold}</div>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="text-sm text-yellow-600">🟡 Stock Bajo</div>
          <div className="text-2xl font-bold text-yellow-700">{statsData.lowStock}</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="text-sm text-green-600">🟢 OK</div>
          <div className="text-2xl font-bold text-green-700">{statsData.ok}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilterStatus('all')}
          className={`px-4 py-2 rounded-lg border ${
            filterStatus === 'all' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'
          }`}
        >
          Todos ({statsData.total})
        </button>
        <button
          onClick={() => setFilterStatus('OVERSOLD')}
          className={`px-4 py-2 rounded-lg border ${
            filterStatus === 'OVERSOLD' ? 'bg-red-600 text-white' : 'bg-white text-gray-700'
          }`}
        >
          🔴 Sobrevendidos ({statsData.oversold})
        </button>
        <button
          onClick={() => setFilterStatus('LOW_STOCK')}
          className={`px-4 py-2 rounded-lg border ${
            filterStatus === 'LOW_STOCK' ? 'bg-yellow-600 text-white' : 'bg-white text-gray-700'
          }`}
        >
          🟡 Stock Bajo ({statsData.lowStock})
        </button>
        <button
          onClick={() => setFilterStatus('OK')}
          className={`px-4 py-2 rounded-lg border ${
            filterStatus === 'OK' ? 'bg-green-600 text-white' : 'bg-white text-gray-700'
          }`}
        >
          🟢 OK ({statsData.ok})
        </button>
      </div>

      {/* Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-4 text-sm font-semibold text-gray-700">Estado</th>
                <th className="text-left p-4 text-sm font-semibold text-gray-700">SKU</th>
                <th className="text-left p-4 text-sm font-semibold text-gray-700">Producto</th>
                <th className="text-right p-4 text-sm font-semibold text-gray-700">Stock Directo</th>
                <th className="text-right p-4 text-sm font-semibold text-gray-700">Stock Variantes</th>
                <th className="text-right p-4 text-sm font-semibold text-gray-700">Total Real</th>
                <th className="text-center p-4 text-sm font-semibold text-gray-700"># Variantes</th>
                <th className="text-right p-4 text-sm font-semibold text-gray-700">Valor Inventario</th>
              </tr>
            </thead>
            <tbody>
              {filteredInventory.map((item) => {
                const statusConfig = stockStatusConfig[item.stock_status];
                return (
                  <tr key={item.base_product_id} className="border-b hover:bg-gray-50">
                    <td className="p-4">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded-full border ${statusConfig.color}`}
                      >
                        {statusConfig.icon} {statusConfig.label}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-sm">{item.base_sku}</td>
                    <td className="p-4 text-sm">{item.base_name}</td>
                    <td className={`p-4 text-right text-sm font-mono ${item.base_direct_stock < 0 ? 'text-red-600' : ''}`}>
                      {item.base_direct_stock.toLocaleString()}
                    </td>
                    <td className={`p-4 text-right text-sm font-mono ${item.variant_stock_as_units < 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {item.variant_stock_as_units > 0 ? '+' : ''}{item.variant_stock_as_units.toLocaleString()}
                    </td>
                    <td className={`p-4 text-right text-sm font-bold font-mono ${item.total_units_available < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                      {item.total_units_available.toLocaleString()}
                    </td>
                    <td className="p-4 text-center text-sm text-gray-600">
                      {item.num_variants}
                    </td>
                    <td className={`p-4 text-right text-sm font-mono ${item.inventory_value && item.inventory_value < 0 ? 'text-red-600' : ''}`}>
                      {formatCurrency(item.inventory_value)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filteredInventory.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No se encontraron productos con el filtro seleccionado
          </div>
        )}
      </div>
    </div>
  );
}
