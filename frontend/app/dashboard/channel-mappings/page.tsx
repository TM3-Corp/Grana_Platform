'use client';

import React, { useState, useEffect } from 'react';
import Navigation from '@/components/Navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types
interface RelBaseChannel {
  id: number;
  name: string;
  external_id: string;
  is_active_relbase: boolean;
}

interface ClientAnalysis {
  customer_id: number;
  customer_external_id: string;
  customer_name: string;
  customer_rut: string | null;
  channel_count: number;
  channels: string[] | null;
  channel_ids: string[] | null;
  order_count: number;
  total_revenue: number;
  // Override rule info (if exists)
  rule_id: number | null;
  override_channel: string | null;
  override_channel_id: number | null;
  rule_reason: string | null;
  rule_active: boolean | null;
}

interface AnalysisStats {
  clients: {
    total: number;
    single_channel: number;
    multi_channel: number;
    no_channel: number;
  };
  channels: {
    active_relbase: number;
    total_relbase: number;
  };
  rules: {
    total: number;
    active: number;
  };
}

export default function ChannelMappingsPage() {
  // Data state
  const [clients, setClients] = useState<ClientAnalysis[]>([]);
  const [relbaseChannels, setRelbaseChannels] = useState<RelBaseChannel[]>([]);
  const [stats, setStats] = useState<AnalysisStats | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  // Pagination state
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(50);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterChannel, setFilterChannel] = useState<string>('');
  const [filterAnomaly, setFilterAnomaly] = useState<string>(''); // '', 'multiple', 'none'

  // Modal state for creating/editing rules
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedClient, setSelectedClient] = useState<ClientAnalysis | null>(null);
  const [formData, setFormData] = useState({
    channel_external_id: 0,
    channel_name: '',
    rule_reason: '',
    priority: 1
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Debounce search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Fetch stats
  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/channel-mappings/analysis-stats`);
      const data = await response.json();
      if (data.status === 'success') {
        setStats(data.data);
      }
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  // Fetch RelBase channels
  const fetchRelbaseChannels = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/channel-mappings/relbase-channels`);
      const data = await response.json();
      if (data.status === 'success') {
        setRelbaseChannels(data.data);
      }
    } catch (err) {
      console.error('Error loading RelBase channels:', err);
    }
  };

  // Sync channels from RelBase API
  const syncChannels = async () => {
    setSyncing(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/channel-mappings/sync-relbase-channels`, {
        method: 'POST'
      });
      const data = await response.json();
      if (data.status === 'success') {
        await fetchRelbaseChannels();
        await fetchStats();
      }
    } catch (err) {
      console.error('Error syncing channels:', err);
    } finally {
      setSyncing(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchStats();
    fetchRelbaseChannels();
  }, []);

  // Fetch client-channel analysis
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const params = new URLSearchParams();
        if (debouncedSearch) params.append('search', debouncedSearch);
        if (filterChannel) params.append('channel_external_id', filterChannel);
        if (filterAnomaly) params.append('anomaly_type', filterAnomaly);
        params.append('limit', pageSize.toString());
        params.append('offset', ((currentPage - 1) * pageSize).toString());

        const response = await fetch(`${API_URL}/api/v1/channel-mappings/client-channel-analysis?${params.toString()}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        if (data.status === 'success') {
          setClients(data.data);
          setTotalCount(data.total);
        } else {
          throw new Error(data.detail || 'Unknown error');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading data');
        console.error('Error loading client analysis:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [debouncedSearch, filterChannel, filterAnomaly, pageSize, currentPage]);

  // Open modal to create rule for a client
  const handleCreateRule = (client: ClientAnalysis) => {
    setSelectedClient(client);
    setFormData({
      channel_external_id: 0,
      channel_name: '',
      rule_reason: '',
      priority: 1
    });
    setSaveError(null);
    setIsModalOpen(true);
  };

  // Open modal to edit existing rule
  const handleEditRule = (client: ClientAnalysis) => {
    setSelectedClient(client);
    setFormData({
      channel_external_id: client.override_channel_id || 0,
      channel_name: client.override_channel || '',
      rule_reason: client.rule_reason || '',
      priority: 1
    });
    setSaveError(null);
    setIsModalOpen(true);
  };

  // Save rule
  const handleSaveRule = async () => {
    if (!selectedClient || !formData.channel_external_id || !formData.rule_reason) {
      setSaveError('Complete todos los campos requeridos');
      return;
    }

    setIsSaving(true);
    setSaveError(null);

    try {
      const isEdit = selectedClient.rule_id !== null;
      const url = isEdit
        ? `${API_URL}/api/v1/channel-mappings/${selectedClient.rule_id}`
        : `${API_URL}/api/v1/channel-mappings/`;
      const method = isEdit ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_external_id: selectedClient.customer_external_id,
          channel_external_id: formData.channel_external_id,
          channel_name: formData.channel_name,
          rule_reason: formData.rule_reason,
          priority: formData.priority,
          created_by: 'web_ui'
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        setIsModalOpen(false);
        // Refresh data
        const params = new URLSearchParams();
        if (debouncedSearch) params.append('search', debouncedSearch);
        if (filterChannel) params.append('channel_external_id', filterChannel);
        if (filterAnomaly) params.append('anomaly_type', filterAnomaly);
        params.append('limit', pageSize.toString());
        params.append('offset', ((currentPage - 1) * pageSize).toString());

        const refreshResponse = await fetch(`${API_URL}/api/v1/channel-mappings/client-channel-analysis?${params.toString()}`);
        const refreshData = await refreshResponse.json();
        if (refreshData.status === 'success') {
          setClients(refreshData.data);
        }
        await fetchStats();
      } else {
        setSaveError(data.detail || 'Error guardando regla');
      }
    } catch (err) {
      setSaveError('Error de conexion');
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  // Delete rule
  const handleDeleteRule = async (client: ClientAnalysis) => {
    if (!client.rule_id) return;
    if (!confirm('Eliminar esta regla de override?')) return;

    try {
      const response = await fetch(`${API_URL}/api/v1/channel-mappings/${client.rule_id}?hard_delete=true`, {
        method: 'DELETE'
      });
      const data = await response.json();
      if (data.status === 'success') {
        // Refresh data
        const params = new URLSearchParams();
        if (debouncedSearch) params.append('search', debouncedSearch);
        if (filterChannel) params.append('channel_external_id', filterChannel);
        if (filterAnomaly) params.append('anomaly_type', filterAnomaly);
        params.append('limit', pageSize.toString());
        params.append('offset', ((currentPage - 1) * pageSize).toString());

        const refreshResponse = await fetch(`${API_URL}/api/v1/channel-mappings/client-channel-analysis?${params.toString()}`);
        const refreshData = await refreshResponse.json();
        if (refreshData.status === 'success') {
          setClients(refreshData.data);
        }
        await fetchStats();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(value);
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Analisis de Canales por Cliente</h1>
            <p className="text-gray-600 mt-1">
              Identifica clientes con problemas de canal y crea reglas de correccion
            </p>
          </div>
          <button
            onClick={syncChannels}
            disabled={syncing}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
          >
            {syncing ? (
              <>
                <span className="animate-spin">&#8635;</span>
                <span>Sincronizando...</span>
              </>
            ) : (
              <>
                <span>&#8635;</span>
                <span>Sync RelBase</span>
              </>
            )}
          </button>
        </div>

        {/* KPI Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-3xl font-bold text-blue-600">{stats.clients.total}</div>
              <div className="text-gray-500 text-sm">Total Clientes</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-3xl font-bold text-green-600">{stats.clients.single_channel}</div>
              <div className="text-gray-500 text-sm">1 Canal (OK)</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4 border-l-4 border-orange-500">
              <div className="text-3xl font-bold text-orange-600">{stats.clients.multi_channel}</div>
              <div className="text-gray-500 text-sm">Multiples Canales</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
              <div className="text-3xl font-bold text-red-600">{stats.clients.no_channel}</div>
              <div className="text-gray-500 text-sm">Sin Canal</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-3xl font-bold text-purple-600">{stats.rules.active}</div>
              <div className="text-gray-500 text-sm">Reglas Override</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="Buscar cliente por nombre o RUT..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="min-w-[180px]">
              <select
                value={filterChannel}
                onChange={(e) => { setFilterChannel(e.target.value); setCurrentPage(1); }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos los canales</option>
                {relbaseChannels.map(ch => (
                  <option key={ch.id} value={ch.external_id}>{ch.name}</option>
                ))}
              </select>
            </div>
            <div className="min-w-[180px]">
              <select
                value={filterAnomaly}
                onChange={(e) => { setFilterAnomaly(e.target.value); setCurrentPage(1); }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos los clientes</option>
                <option value="multiple">Con multiples canales</option>
                <option value="none">Sin canal asignado</option>
              </select>
            </div>
          </div>
        </div>

        {/* Results count */}
        <div className="text-gray-600 text-sm mb-4">
          Mostrando {clients.length} de {totalCount} clientes
          {filterAnomaly === 'multiple' && ' con problemas de canal'}
          {filterAnomaly === 'none' && ' sin canal asignado'}
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Cargando...</div>
          ) : error ? (
            <div className="p-8 text-center text-red-500">{error}</div>
          ) : clients.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No se encontraron clientes</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cliente</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Canales Actuales</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ordenes</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Revenue</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Override</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {clients.map(client => {
                    const hasAnomaly = client.channel_count > 1 || client.channel_count === 0;
                    const hasRule = client.rule_id !== null;

                    return (
                      <tr key={client.customer_id} className={`hover:bg-gray-50 ${hasAnomaly && !hasRule ? 'bg-orange-50' : ''}`}>
                        <td className="px-4 py-3">
                          <div className="font-medium text-gray-900">
                            {client.customer_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            {client.customer_rut} | ID: {client.customer_external_id}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {client.channels && client.channels.length > 0 ? (
                              client.channels.map((ch, idx) => (
                                <span
                                  key={idx}
                                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                    client.channel_count > 1
                                      ? 'bg-orange-100 text-orange-800'
                                      : 'bg-blue-100 text-blue-800'
                                  }`}
                                >
                                  {ch}
                                </span>
                              ))
                            ) : (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                SIN CANAL
                              </span>
                            )}
                          </div>
                          {client.channel_count > 1 && (
                            <div className="text-xs text-orange-600 mt-1 font-medium">
                              ⚠ {client.channel_count} canales distintos
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-600">
                          {client.order_count.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-right font-medium text-gray-900">
                          {formatCurrency(client.total_revenue)}
                        </td>
                        <td className="px-4 py-3">
                          {hasRule ? (
                            <div>
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                &#10003; {client.override_channel}
                              </span>
                              <div className="text-xs text-gray-500 mt-1 max-w-xs truncate" title={client.rule_reason || ''}>
                                {client.rule_reason}
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-400 text-sm">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            {hasRule ? (
                              <>
                                <button
                                  onClick={() => handleEditRule(client)}
                                  className="text-blue-600 hover:text-blue-800 text-sm"
                                >
                                  Editar
                                </button>
                                <button
                                  onClick={() => handleDeleteRule(client)}
                                  className="text-red-600 hover:text-red-800 text-sm"
                                >
                                  Eliminar
                                </button>
                              </>
                            ) : (
                              <button
                                onClick={() => handleCreateRule(client)}
                                className="text-green-600 hover:text-green-800 text-sm font-medium"
                              >
                                + Crear Regla
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-4">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border rounded disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="px-3 py-1">
              Pagina {currentPage} de {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 border rounded disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        )}

        {/* Modal for creating/editing rules */}
        {isModalOpen && selectedClient && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <h2 className="text-xl font-bold mb-2">
                  {selectedClient.rule_id ? 'Editar Regla Override' : 'Crear Regla Override'}
                </h2>
                <p className="text-gray-600 text-sm mb-4">
                  Cliente: <strong>{selectedClient.customer_name}</strong>
                </p>

                {/* Current channels info */}
                <div className="bg-gray-50 rounded-lg p-3 mb-4">
                  <div className="text-sm text-gray-600 mb-2">Canales actuales en ordenes:</div>
                  <div className="flex flex-wrap gap-1">
                    {selectedClient.channels?.map((ch, idx) => (
                      <span key={idx} className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-xs">
                        {ch}
                      </span>
                    )) || <span className="text-gray-400">Sin canales</span>}
                  </div>
                </div>

                {saveError && (
                  <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4">
                    {saveError}
                  </div>
                )}

                <div className="space-y-4">
                  {/* Channel select */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Canal Correcto *
                    </label>
                    <select
                      value={formData.channel_external_id}
                      onChange={(e) => {
                        const channel = relbaseChannels.find(ch => ch.external_id === e.target.value);
                        if (channel) {
                          setFormData(prev => ({
                            ...prev,
                            channel_external_id: parseInt(channel.external_id),
                            channel_name: channel.name
                          }));
                        }
                      }}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Seleccionar canal correcto...</option>
                      {relbaseChannels.map(ch => (
                        <option key={ch.id} value={ch.external_id}>
                          {ch.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Rule reason */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Razon del cambio *
                    </label>
                    <textarea
                      value={formData.rule_reason}
                      onChange={(e) => setFormData(prev => ({ ...prev, rule_reason: e.target.value }))}
                      placeholder="Explicar por que este cliente debe estar en este canal..."
                      rows={3}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Esta regla tendra prioridad sobre los datos de RelBase
                    </p>
                  </div>
                </div>

                {/* Modal actions */}
                <div className="flex justify-end gap-3 mt-6">
                  <button
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                    disabled={isSaving}
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleSaveRule}
                    disabled={isSaving}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {isSaving ? 'Guardando...' : 'Guardar Regla'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
