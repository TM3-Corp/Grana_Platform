'use client';

import { useState } from 'react';
import { useTopProducts } from '../hooks/useRelbaseData';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function TopProductsChart() {
  const [limit, setLimit] = useState(20);
  const { products, loading, error } = useTopProducts(limit);

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-48 mb-4"></div>
          <div className="h-96 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !products) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">Error loading chart: {error || 'Unknown error'}</p>
      </div>
    );
  }

  // Get color based on confidence
  const getBarColor = (confidence: number) => {
    if (confidence === 100) return '#22c55e'; // Green - exact match
    if (confidence === 70) return '#eab308';   // Yellow - fuzzy match
    return '#ef4444';                           // Red - no match
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-4 rounded shadow-lg border border-gray-200">
          <p className="font-semibold text-gray-900">{data.relbase_code}</p>
          {data.relbase_name && (
            <p className="text-xs text-gray-600 mb-2">{data.relbase_name.substring(0, 50)}</p>
          )}
          <p className="text-sm text-gray-700">
            Ventas: <span className="font-bold">{data.total_sales}</span>
          </p>
          <p className="text-sm text-gray-700">
            Tipo: <span className="font-semibold">{data.match_type}</span>
          </p>
          <p className="text-sm">
            Confianza: <span className={`font-bold ${
              data.confidence_percentage === 100 ? 'text-green-600' :
              data.confidence_percentage === 70 ? 'text-yellow-600' :
              'text-red-600'
            }`}>
              {data.confidence_percentage}%
            </span>
          </p>
          {data.official_sku && (
            <p className="text-xs text-gray-600 mt-2">
              SKU: {data.official_sku}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow mb-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Top Productos por Volumen</h3>
          <p className="text-sm text-gray-600">Ordenados por cantidad de ventas</p>
        </div>

        {/* Limit selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-700 font-medium">Mostrar:</label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
            <option value={30}>Top 30</option>
            <option value={50}>Top 50</option>
            <option value={100}>Top 100</option>
          </select>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-6 mb-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-500 rounded"></div>
          <span className="text-gray-700">100% Confianza (Exacto)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-500 rounded"></div>
          <span className="text-gray-700">70% Confianza (Fuzzy)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded"></div>
          <span className="text-gray-700">0% Confianza (Sin Match)</span>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={products} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <XAxis
            dataKey="relbase_code"
            angle={-45}
            textAnchor="end"
            height={100}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            label={{ value: 'Ventas', angle: -90, position: 'insideLeft' }}
            tick={{ fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="total_sales" radius={[4, 4, 0, 0]}>
            {products.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry.confidence_percentage)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Summary below chart */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-center text-sm">
          <div>
            <p className="text-gray-600">Productos Mostrados</p>
            <p className="text-2xl font-bold text-gray-900">{products.length}</p>
          </div>
          <div>
            <p className="text-gray-600">Mapeados</p>
            <p className="text-2xl font-bold text-green-600">
              {products.filter(p => p.is_mapped).length}
            </p>
          </div>
          <div>
            <p className="text-gray-600">Sin Mapear</p>
            <p className="text-2xl font-bold text-red-600">
              {products.filter(p => !p.is_mapped).length}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
