'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';

interface AuditData {
  order_id: number;
  order_external_id: string;
  order_date: string;
  order_total: number;
  order_source: string;
  customer_id: string;
  customer_external_id: string;
  customer_name: string;
  customer_rut: string;
  channel_name: string;
  channel_id: string;
  channel_source: string;
  item_id: number;
  sku: string;
  sku_primario?: string;
  match_type?: string;
  pack_quantity?: number;
  product_name: string;
  quantity: number;
  unit_price: number;
  item_subtotal: number;
  category: string;
  family: string;
  format: string;
  customer_null: boolean;
  channel_null: boolean;
  sku_null: boolean;
  in_catalog: boolean;
}

interface AuditSummary {
  total_orders: number;
  data_quality: {
    null_customers: number;
    null_channels: number;
    null_skus: number;
    completeness_pct: number;
  };
  product_mapping: {
    unique_skus: number;
    in_catalog: number;
    not_in_catalog: number;
    catalog_coverage_pct: number;
    mapped_skus: number;
    unmapped_skus_sample: string[];
  };
}

interface Filters {
  sources: string[];
  channels: string[];
  customers: string[];
  skus: string[];
}

export default function AuditView() {
  const { data: session, status } = useSession();
  const [data, setData] = useState<AuditData[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [filters, setFilters] = useState<Filters>({ sources: [], channels: [], customers: [], skus: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [selectedSource, setSelectedSource] = useState<string>('');
  const [selectedChannel, setSelectedChannel] = useState<string>('');
  const [selectedCustomer, setSelectedCustomer] = useState<string>('');
  const [selectedSKU, setSelectedSKU] = useState<string>('');
  const [skuSearchInput, setSkuSearchInput] = useState<string>('');
  const [showNullsOnly, setShowNullsOnly] = useState(false);
  const [showNotInCatalogOnly, setShowNotInCatalogOnly] = useState(false);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 100;

  // Grouping
  const [groupBy, setGroupBy] = useState<string>('');

  useEffect(() => {
    if (status === 'authenticated') {
      fetchFilters();
      fetchSummary();
    }
  }, [status]);

  useEffect(() => {
    if (status === 'authenticated') {
      fetchData();
    }
  }, [status, selectedSource, selectedChannel, selectedCustomer, selectedSKU, showNullsOnly, showNotInCatalogOnly, currentPage]);

  // Debounce SKU search input
  useEffect(() => {
    const timer = setTimeout(() => {
      if (skuSearchInput !== selectedSKU) {
        setSelectedSKU(skuSearchInput);
        setCurrentPage(1);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [skuSearchInput]);

  const fetchFilters = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const response = await fetch(`${apiUrl}/api/v1/audit/filters`);
      if (!response.ok) throw new Error('Error fetching filters');
      const result = await response.json();
      setFilters(result.data);
    } catch (err) {
      console.error('Error fetching filters:', err);
    }
  };

  const fetchSummary = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const response = await fetch(`${apiUrl}/api/v1/audit/summary`);
      if (!response.ok) throw new Error('Error fetching summary');
      const result = await response.json();
      setSummary(result.data);
    } catch (err) {
      console.error('Error fetching summary:', err);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        limit: pageSize.toString(),
        offset: ((currentPage - 1) * pageSize).toString(),
      });

      if (selectedSource) params.append('source', selectedSource);
      if (selectedChannel) params.append('channel', selectedChannel);
      if (selectedCustomer) params.append('customer', selectedCustomer);
      if (selectedSKU) params.append('sku', selectedSKU);
      if (showNullsOnly) params.append('has_nulls', 'true');
      if (showNotInCatalogOnly) params.append('not_in_catalog', 'true');

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const response = await fetch(`${apiUrl}/api/v1/audit/data?${params}`);
      if (!response.ok) throw new Error('Error fetching audit data');

      const result = await response.json();
      setData(result.data);
      setTotalCount(result.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = () => {
    setSelectedSource('');
    setSelectedChannel('');
    setSelectedCustomer('');
    setSelectedSKU('');
    setSkuSearchInput('');
    setShowNullsOnly(false);
    setShowNotInCatalogOnly(false);
    setCurrentPage(1);
  };

  const groupData = (data: AuditData[], groupByField: string) => {
    if (!groupByField) return { '': data };

    const grouped: { [key: string]: AuditData[] } = {};
    data.forEach((item) => {
      const key = String((item as any)[groupByField] || 'SIN CLASIFICAR');
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(item);
    });
    return grouped;
  };

  const groupedData = groupData(data, groupBy);
  const totalPages = Math.ceil(totalCount / pageSize);

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600">Cargando...</div>
      </div>
    );
  }

  return (
    <div>
      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600 mb-1">Total Órdenes 2025</div>
            <div className="text-2xl font-bold text-gray-900">{summary.total_orders.toLocaleString()}</div>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600 mb-1">Completitud de Datos</div>
            <div className="text-2xl font-bold text-green-600">{summary.data_quality.completeness_pct}%</div>
            <div className="text-xs text-gray-500 mt-1">
              {summary.data_quality.null_customers} clientes NULL · {summary.data_quality.null_channels} canales NULL · {summary.data_quality.null_skus} SKUs NULL
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600 mb-1">SKUs Únicos</div>
            <div className="text-2xl font-bold text-gray-900">{summary.product_mapping.unique_skus}</div>
            <div className="text-xs text-gray-500 mt-1">
              {summary.product_mapping.mapped_skus} mapeados · {summary.product_mapping.not_in_catalog} sin mapear
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600 mb-1">Cobertura Catálogo</div>
            <div className="text-2xl font-bold text-blue-600">{summary.product_mapping.catalog_coverage_pct}%</div>
            <div className="text-xs text-gray-500 mt-1">
              SKUs mapeados en Códigos_Grana_Final.csv
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Filtros</h2>
          <button
            onClick={clearFilters}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Limpiar filtros
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          {/* Source Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Fuente</label>
            <select
              value={selectedSource}
              onChange={(e) => { setSelectedSource(e.target.value); setCurrentPage(1); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todas las fuentes</option>
              {filters.sources.map((source) => (
                <option key={source} value={source}>{source}</option>
              ))}
            </select>
          </div>

          {/* Channel Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Canal</label>
            <select
              value={selectedChannel}
              onChange={(e) => { setSelectedChannel(e.target.value); setCurrentPage(1); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos los canales</option>
              {filters.channels.map((channel) => (
                <option key={channel} value={channel}>{channel}</option>
              ))}
            </select>
          </div>

          {/* Customer Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cliente</label>
            <select
              value={selectedCustomer}
              onChange={(e) => { setSelectedCustomer(e.target.value); setCurrentPage(1); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos los clientes</option>
              {filters.customers.map((customer) => (
                <option key={customer} value={customer}>{customer}</option>
              ))}
            </select>
          </div>

          {/* SKU Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Buscar SKU</label>
            <input
              type="text"
              value={skuSearchInput}
              onChange={(e) => setSkuSearchInput(e.target.value)}
              placeholder="Escribe para buscar SKU..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {skuSearchInput && (
              <div className="mt-1 text-xs text-gray-500">
                Buscando: "{skuSearchInput}"
              </div>
            )}
          </div>
        </div>

        {/* Quality Toggles */}
        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showNullsOnly}
              onChange={(e) => { setShowNullsOnly(e.target.checked); setCurrentPage(1); }}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Solo registros con NULLs</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showNotInCatalogOnly}
              onChange={(e) => { setShowNotInCatalogOnly(e.target.checked); setCurrentPage(1); }}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Solo SKUs no mapeados</span>
          </label>
        </div>

        {/* Group By */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Agrupar por</label>
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value)}
            className="w-full md:w-64 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Sin agrupación</option>
            <option value="order_source">Fuente</option>
            <option value="channel_name">Canal</option>
            <option value="customer_name">Cliente</option>
            <option value="sku">SKU Original</option>
            <option value="sku_primario">SKU Primario</option>
            <option value="category">Categoría</option>
            <option value="family">Familia</option>
            <option value="format">Formato</option>
          </select>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-gray-600">Cargando datos...</div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-red-600">Error: {error}</div>
            </div>
          ) : data.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-gray-600">No se encontraron datos con los filtros seleccionados</div>
            </div>
          ) : (
            <>
              {Object.entries(groupedData).map(([groupKey, groupItems]) => (
                <div key={groupKey} className="mb-6">
                  {groupBy && (
                    <div className="bg-gray-100 px-6 py-3 border-b border-gray-200">
                      <h3 className="font-semibold text-gray-900">
                        {groupKey} <span className="text-sm font-normal text-gray-600">({groupItems.length} registros)</span>
                      </h3>
                    </div>
                  )}
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pedido</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cliente</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Canal</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SKU Original</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Producto</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cantidad</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {groupItems.map((item, idx) => (
                        <tr key={`${item.item_id}-${idx}`} className="hover:bg-gray-50">
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                            {item.order_external_id}
                            <div className="text-xs text-gray-500">{item.order_source}</div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                            {new Date(item.order_date).toLocaleDateString('es-CL')}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <div className={item.customer_null ? 'text-red-600 font-medium' : 'text-gray-900'}>
                              {item.customer_name}
                            </div>
                            <div className="text-xs text-gray-500">{item.customer_rut}</div>
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <div className={item.channel_null ? 'text-red-600 font-medium' : 'text-gray-900'}>
                              {item.channel_name}
                            </div>
                            <div className="text-xs text-gray-500">{item.channel_source}</div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            <div className={item.sku_null ? 'text-red-600 font-medium' : 'text-gray-900'}>
                              {item.sku || 'SIN SKU'}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900">
                            {item.product_name}
                            <div className="text-xs text-gray-500">
                              {item.category && `${item.category} `}
                              {item.family && `· ${item.family}`}
                            </div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                            {item.quantity}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            {!item.in_catalog && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                No en catálogo
                              </span>
                            )}
                            {(item.customer_null || item.channel_null || item.sku_null) && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 ml-1">
                                NULLs
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </>
          )}
        </div>

        {/* Pagination */}
        {!loading && data.length > 0 && (
          <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Mostrando <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> a{' '}
              <span className="font-medium">{Math.min(currentPage * pageSize, totalCount)}</span> de{' '}
              <span className="font-medium">{totalCount}</span> registros
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Anterior
              </button>
              <div className="flex items-center gap-2 px-4">
                <span className="text-sm text-gray-700">
                  Página {currentPage} de {totalPages}
                </span>
              </div>
              <button
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
