'use client';

import { useRelbaseStats } from '../hooks/useRelbaseData';

export default function StatsCards() {
  const { stats, loading, error } = useRelbaseStats();

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-white p-6 rounded-lg shadow animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-24 mb-4"></div>
            <div className="h-8 bg-gray-200 rounded w-16 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-32"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <p className="text-red-700">Error loading stats: {error || 'Unknown error'}</p>
      </div>
    );
  }

  const mappedPct = ((stats.mapped_sales / stats.total_sales) * 100).toFixed(1);
  const unmappedPct = ((stats.unmapped_sales / stats.total_sales) * 100).toFixed(1);

  return (
    <>
      {/* Main stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Total Products */}
        <div className="bg-white p-6 rounded-lg shadow border-2 border-gray-100">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Total Productos</h3>
          <p className="text-3xl font-bold text-gray-900">{stats.total_products}</p>
          <p className="text-sm text-gray-600 mt-1">
            {stats.total_sales.toLocaleString()} ventas totales
          </p>
        </div>

        {/* Mapped (High Confidence) */}
        <div className="bg-green-50 p-6 rounded-lg shadow border-2 border-green-300">
          <h3 className="text-sm font-medium text-green-700 mb-1">✅ Mapeados</h3>
          <p className="text-3xl font-bold text-green-900">{stats.mapped_products}</p>
          <p className="text-sm text-green-600 mt-1">
            {stats.mapped_sales.toLocaleString()} ventas ({mappedPct}%)
          </p>
          <p className="text-xs text-green-500 mt-2">
            Alta confianza: {stats.by_confidence.high?.count || 0} productos
          </p>
        </div>

        {/* Unmapped */}
        <div className="bg-red-50 p-6 rounded-lg shadow border-2 border-red-300">
          <h3 className="text-sm font-medium text-red-700 mb-1">❌ Sin Mapear</h3>
          <p className="text-3xl font-bold text-red-900">{stats.unmapped_products}</p>
          <p className="text-sm text-red-600 mt-1">
            {stats.unmapped_sales.toLocaleString()} ventas ({unmappedPct}%)
          </p>
          <p className="text-xs text-red-500 mt-2">
            Requiere atención
          </p>
        </div>

        {/* Needs Review */}
        <div className="bg-yellow-50 p-6 rounded-lg shadow border-2 border-yellow-300">
          <h3 className="text-sm font-medium text-yellow-700 mb-1">🔍 Revisar</h3>
          <p className="text-3xl font-bold text-yellow-900">{stats.needs_review}</p>
          <p className="text-sm text-yellow-600 mt-1">
            Legacy: {stats.legacy_codes} | Servicios: {stats.service_items}
          </p>
          <p className="text-xs text-yellow-500 mt-2">
            Necesita revisión manual
          </p>
        </div>
      </div>

      {/* Breakdown by match type */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Desglose por Tipo de Mapeo</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {Object.entries(stats.by_match_type).map(([type, data]) => (
            <div key={type} className="text-center">
              <div className={`text-2xl font-bold ${
                type === 'exact' ? 'text-green-600' :
                type === 'pack_variant' ? 'text-blue-600' :
                type === 'caja_master' ? 'text-purple-600' :
                type === 'caja_fuzzy' ? 'text-yellow-600' :
                'text-red-600'
              }`}>
                {data.count}
              </div>
              <div className="text-xs text-gray-600 mt-1">
                {type === 'exact' ? 'Exacto' :
                 type === 'pack_variant' ? 'Pack' :
                 type === 'caja_master' ? 'Caja Exact' :
                 type === 'caja_fuzzy' ? 'Caja Fuzzy' :
                 'Sin Match'}
              </div>
              <div className="text-xs text-gray-500">
                {data.sales.toLocaleString()} ventas
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
