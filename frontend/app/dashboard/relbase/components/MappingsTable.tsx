'use client';

import { useState } from 'react';
import { useMappings } from '../hooks/useRelbaseData';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function MappingsTable() {
  const [filters, setFilters] = useState({
    page: 1,
    page_size: 50,
    search: '',
    match_type: '',
    confidence: '',
    needs_review: undefined as boolean | undefined,
    exclude_service: false,
    sort_by: 'sales',
    sort_order: 'desc'
  });

  const { data, total, page, page_size, total_pages, loading, error } = useMappings(filters);

  // Get confidence badge
  const getConfidenceBadge = (percentage: number) => {
    if (percentage === 100) {
      return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">🟢 100%</span>;
    } else if (percentage === 70) {
      return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">🟡 70%</span>;
    } else {
      return <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">🔴 0%</span>;
    }
  };

  // Get match type badge
  const getMatchTypeBadge = (type: string) => {
    const styles = {
      exact: 'bg-green-100 text-green-800',
      pack_variant: 'bg-blue-100 text-blue-800',
      caja_master: 'bg-purple-100 text-purple-800',
      caja_fuzzy: 'bg-yellow-100 text-yellow-800',
      no_match: 'bg-red-100 text-red-800'
    }[type] || 'bg-gray-100 text-gray-800';

    const labels = {
      exact: 'Exacto',
      pack_variant: 'Pack',
      caja_master: 'Caja Exact',
      caja_fuzzy: 'Caja Fuzzy',
      no_match: 'Sin Match'
    }[type] || type;

    return <span className={`px-2 py-1 text-xs font-medium rounded ${styles}`}>{labels}</span>;
  };

  // Export to CSV
  const handleExportCSV = async () => {
    try {
      // Build query params with current filters, but fetch ALL data (no pagination)
      const params = new URLSearchParams();
      params.append('page_size', '500'); // Increased limit
      if (filters.search) params.append('search', filters.search);
      if (filters.match_type) params.append('match_type', filters.match_type);
      if (filters.confidence) params.append('confidence', filters.confidence);
      if (filters.needs_review !== undefined) params.append('needs_review', String(filters.needs_review));
      if (filters.exclude_service !== undefined) params.append('exclude_service', String(filters.exclude_service));
      params.append('sort_by', filters.sort_by);
      params.append('sort_order', filters.sort_order);

      console.log('Fetching from:', `${API_URL}/api/v1/relbase/mappings?${params.toString()}`);
      const response = await fetch(`${API_URL}/api/v1/relbase/mappings?${params.toString()}`);

      console.log('Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error:', errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('API Response:', result);
      console.log('Data array length:', result?.data?.length);

      // Validate response structure
      if (!result || !result.data || !Array.isArray(result.data)) {
        console.error('Invalid API response:', result);
        throw new Error('La respuesta del servidor no tiene el formato esperado');
      }

      if (result.data.length === 0) {
        alert('No hay datos para exportar con los filtros actuales.');
        return;
      }

      // CSV headers
      const headers = [
        'Código Relbase',
        'Nombre Producto',
        'SKU Oficial',
        'Tipo Mapeo',
        'Confianza (%)',
        'Ventas',
        'Es Servicio',
        'Es Legacy',
        'Necesita Revisión'
      ];

      // CSV rows
      const rows = result.data.map((row: any) => [
        row.relbase_code || '',
        (row.relbase_name || '').replace(/,/g, ';'), // Replace commas to avoid CSV issues
        row.official_sku || '',
        row.match_type || '',
        row.confidence_percentage || 0,
        row.total_sales || 0,
        row.is_service_item ? 'Sí' : 'No',
        row.is_legacy_code ? 'Sí' : 'No',
        row.needs_manual_review ? 'Sí' : 'No'
      ]);

      // Build CSV content
      const csvContent = [
        headers.join(','),
        ...rows.map((row: any[]) => row.map(cell => `"${cell}"`).join(','))
      ].join('\n');

      // Create and download file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      const timestamp = new Date().toISOString().split('T')[0];
      link.setAttribute('href', url);
      link.setAttribute('download', `relbase_mappings_${timestamp}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error exporting CSV:', error);
      alert('Error al exportar CSV. Por favor intenta de nuevo.');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Filters Bar */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        {/* Export Button */}
        <div className="mb-4 flex justify-between items-center">
          <div className="text-sm text-gray-600">
            {total > 0 && (
              <span>
                Mostrando {total.toLocaleString()} productos
                {(filters.search || filters.match_type || filters.confidence || filters.needs_review || filters.exclude_service) &&
                  ' (filtrados)'}
              </span>
            )}
          </div>
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2 text-sm font-medium shadow-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Exportar CSV
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Buscar</label>
            <input
              type="text"
              placeholder="Código o nombre..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Match Type Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Mapeo</label>
            <select
              value={filters.match_type}
              onChange={(e) => setFilters({ ...filters, match_type: e.target.value, page: 1 })}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Todos</option>
              <option value="exact">Exacto</option>
              <option value="pack_variant">Pack Variant</option>
              <option value="caja_master">Caja Master</option>
              <option value="caja_fuzzy">Caja Fuzzy</option>
              <option value="no_match">Sin Match</option>
            </select>
          </div>

          {/* Confidence Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confianza</label>
            <select
              value={filters.confidence}
              onChange={(e) => setFilters({ ...filters, confidence: e.target.value, page: 1 })}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Todos</option>
              <option value="high">Alta (100%)</option>
              <option value="medium">Media (70%)</option>
              <option value="low">Baja</option>
              <option value="none">Ninguna (0%)</option>
            </select>
          </div>

          {/* Sort By */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ordenar por</label>
            <select
              value={filters.sort_by}
              onChange={(e) => setFilters({ ...filters, sort_by: e.target.value })}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="sales">Ventas (↓)</option>
              <option value="code">Código</option>
              <option value="confidence">Confianza</option>
            </select>
          </div>
        </div>

        {/* Checkboxes */}
        <div className="mt-4 flex gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={filters.exclude_service}
              onChange={(e) => setFilters({ ...filters, exclude_service: e.target.checked, page: 1 })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-gray-700">Excluir servicios (envíos, ajustes)</span>
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={filters.needs_review === true}
              onChange={(e) => setFilters({ ...filters, needs_review: e.target.checked ? true : undefined, page: 1 })}
              className="rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
            />
            <span className="text-gray-700">Solo que necesitan revisión</span>
          </label>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        {loading ? (
          <div className="p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Cargando...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-600">
            Error: {error}
          </div>
        ) : data.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No se encontraron resultados
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Código Relbase
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Nombre
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SKU Oficial
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo Mapeo
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Confianza
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ventas
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Flags
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.map((row, index) => (
                <tr key={index} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="font-mono text-sm font-medium text-gray-900">
                      {row.relbase_code}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600">
                      {row.relbase_name ? row.relbase_name.substring(0, 40) : '-'}
                      {row.relbase_name && row.relbase_name.length > 40 && '...'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {row.official_sku ? (
                      <span className="font-mono text-sm font-medium text-blue-600">
                        {row.official_sku}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-sm">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getMatchTypeBadge(row.match_type)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getConfidenceBadge(row.confidence_percentage)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-semibold text-gray-900">
                      {row.total_sales.toLocaleString()}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex gap-1">
                      {row.is_service_item && (
                        <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                          Servicio
                        </span>
                      )}
                      {row.is_legacy_code && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">
                          Legacy
                        </span>
                      )}
                      {row.needs_manual_review && (
                        <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs">
                          🚨 Revisar
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {!loading && data.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Mostrando <span className="font-medium">{(page - 1) * page_size + 1}</span> a{' '}
              <span className="font-medium">{Math.min(page * page_size, total)}</span> de{' '}
              <span className="font-medium">{total}</span> productos
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setFilters({ ...filters, page: page - 1 })}
                disabled={page === 1}
                className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Anterior
              </button>

              <div className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700">
                Página <span className="font-medium">{page}</span> de{' '}
                <span className="font-medium">{total_pages}</span>
              </div>

              <button
                onClick={() => setFilters({ ...filters, page: page + 1 })}
                disabled={page === total_pages}
                className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Siguiente
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
