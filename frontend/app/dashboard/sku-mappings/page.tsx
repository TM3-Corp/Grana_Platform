'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Navigation from '@/components/Navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SKUMapping {
  id: number;
  source_pattern: string;
  pattern_type: string;
  source_filter: string | null;
  target_sku: string;
  quantity_multiplier: number;
  rule_name: string | null;
  confidence: number;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  notes: string | null;
}

interface MappingComponent {
  id: number;
  target_sku: string;
  quantity_multiplier: number;
  rule_name: string | null;
}

// Form component for creating/editing mappings
interface FormComponent {
  id?: number;  // Existing mapping ID (undefined for new components)
  target_sku: string;
  quantity_multiplier: number;
}

interface OrderSKU {
  sku: string;
  product_name: string;
  order_count: number;
  total_quantity: number;
  total_revenue: number;
  last_order_date: string;
  mapping_status: 'mapped' | 'in_catalog' | 'unmapped';
  mapped_to: string | null;
  quantity_multiplier: number | null;
  rule_name: string | null;
  mapping_components: MappingComponent[] | null;
  component_count: number;
}

interface CatalogSKU {
  sku: string;
  product_name: string;
  category: string;
}

interface OrderSKUStats {
  total_order_skus: number;
  mapped_count: number;
  in_catalog_count: number;
  unmapped_count: number;
  unmapped_revenue: number;
  coverage_percent: number;
}

export default function SKUMappingsPage() {
  // View mode: 'mappings' or 'order-skus'
  const [viewMode, setViewMode] = useState<'order-skus' | 'mappings'>('order-skus');

  // Order SKUs data
  const [orderSKUs, setOrderSKUs] = useState<OrderSKU[]>([]);
  const [orderSKUStats, setOrderSKUStats] = useState<OrderSKUStats | null>(null);

  // Existing mappings data
  const [mappings, setMappings] = useState<SKUMapping[]>([]);
  const [catalogSKUs, setCatalogSKUs] = useState<CatalogSKU[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination state
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('unmapped'); // 'all', 'unmapped', 'mapped'

  // Sorting
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMapping, setEditingMapping] = useState<SKUMapping | null>(null);
  const [prefillSKU, setPrefillSKU] = useState<{sku: string; product_name: string} | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    source_pattern: '',
    rule_name: '',
    notes: '',
  });

  // Multi-component form state
  const [formComponents, setFormComponents] = useState<FormComponent[]>([
    { target_sku: '', quantity_multiplier: 1 }
  ]);

  // Searchable dropdown state
  const [openDropdownIndex, setOpenDropdownIndex] = useState<number | null>(null);
  const [dropdownSearch, setDropdownSearch] = useState<string>('');

  // Track deleted component IDs for proper CRUD
  const [deletedComponentIds, setDeletedComponentIds] = useState<number[]>([]);

  // Saving state for modal feedback
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

  // Fetch order SKU stats (always fetch for KPI cards)
  const fetchOrderSKUStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/sku-mappings/order-skus/stats`);
      const data = await response.json();
      if (data.status === 'success') {
        setOrderSKUStats(data.data);
      }
    } catch (err) {
      console.error('Error loading order SKU stats:', err);
    }
  };

  // Fetch order SKUs with mapping status
  const fetchOrderSKUs = useCallback(async () => {
    if (viewMode !== 'order-skus') return;

    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (debouncedSearch) params.append('search', debouncedSearch);
      if (filterStatus === 'unmapped') params.append('unmapped_only', 'true');
      else if (filterStatus === 'mapped') params.append('mapped_only', 'true');
      if (sortBy) {
        params.append('sort_by', sortBy);
        params.append('sort_dir', sortDir);
      }
      params.append('limit', pageSize.toString());
      params.append('offset', ((currentPage - 1) * pageSize).toString());

      const response = await fetch(`${API_URL}/api/v1/sku-mappings/order-skus/all?${params.toString()}`);
      const data = await response.json();
      if (data.status === 'success') {
        setOrderSKUs(data.data);
        setTotalCount(data.total);
      }
    } catch (err) {
      setError('Error loading order SKUs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [viewMode, debouncedSearch, filterStatus, sortBy, sortDir, pageSize, currentPage]);

  // Fetch existing mappings
  const fetchMappings = useCallback(async () => {
    if (viewMode !== 'mappings') return;

    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (debouncedSearch) params.append('search', debouncedSearch);
      params.append('is_active', 'true');
      params.append('limit', pageSize.toString());
      params.append('offset', ((currentPage - 1) * pageSize).toString());

      const response = await fetch(`${API_URL}/api/v1/sku-mappings/?${params.toString()}`);
      const data = await response.json();
      if (data.status === 'success') {
        setMappings(data.data);
        setTotalCount(data.total);
      }
    } catch (err) {
      setError('Error loading mappings');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [viewMode, debouncedSearch, pageSize, currentPage]);

  // Fetch catalog SKUs for dropdown
  const fetchCatalogSKUs = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/sku-mappings/catalog-skus?limit=500`);
      const data = await response.json();
      if (data.status === 'success') {
        setCatalogSKUs(data.data);
      }
    } catch (err) {
      console.error('Error loading catalog SKUs:', err);
    }
  };

  useEffect(() => {
    fetchOrderSKUStats();
    fetchCatalogSKUs();
  }, []);

  useEffect(() => {
    if (viewMode === 'order-skus') {
      fetchOrderSKUs();
    } else {
      fetchMappings();
    }
  }, [viewMode, fetchOrderSKUs, fetchMappings]);

  // Create/Update/Delete mappings (full CRUD support)
  const handleSave = async () => {
    console.log('=== handleSave called ===');
    console.log('formComponents:', formComponents);
    console.log('deletedComponentIds:', deletedComponentIds);
    console.log('formData:', formData);

    setIsSaving(true);
    setSaveError(null);

    try {
      // Filter out empty components
      const validComponents = formComponents.filter(c => c.target_sku);
      console.log('validComponents:', validComponents);

      if (validComponents.length === 0) {
        setSaveError('Debe agregar al menos un SKU destino');
        setIsSaving(false);
        return;
      }

      const errors: string[] = [];
      let successCount = 0;

      // 1. DELETE removed components (ones with IDs that were removed from form)
      console.log('Starting DELETE phase for:', deletedComponentIds);
      for (const deletedId of deletedComponentIds) {
        try {
          console.log(`Deleting mapping ${deletedId}...`);
          const response = await fetch(
            `${API_URL}/api/v1/sku-mappings/${deletedId}?hard_delete=true`,
            { method: 'DELETE' }
          );
          const data = await response.json();
          console.log(`DELETE ${deletedId} response:`, data);
          if (data.status === 'success') {
            successCount++;
          } else {
            errors.push(data.detail || `Error eliminando mapeo ${deletedId}`);
          }
        } catch (err) {
          console.error(`DELETE ${deletedId} error:`, err);
          errors.push(`Error eliminando mapeo ${deletedId}`);
        }
      }

      // 2. CREATE or UPDATE each component
      console.log('Starting CREATE/UPDATE phase...');
      for (const component of validComponents) {
        // If component has ID, it exists in database -> UPDATE (PUT)
        // If component has no ID, it's new -> CREATE (POST)
        const isUpdate = !!component.id;
        const url = isUpdate
          ? `${API_URL}/api/v1/sku-mappings/${component.id}`
          : `${API_URL}/api/v1/sku-mappings/`;
        const method = isUpdate ? 'PUT' : 'POST';

        const body = {
          source_pattern: formData.source_pattern,
          pattern_type: 'exact',
          target_sku: component.target_sku,
          source_filter: null,
          quantity_multiplier: component.quantity_multiplier,
          rule_name: formData.rule_name || null,
          confidence: 100,
          priority: 50,
          notes: formData.notes || null,
        };

        console.log(`${method} to ${url}`, body);

        try {
          const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });

          console.log(`Response status: ${response.status}`);
          const data = await response.json();
          console.log(`Response data:`, data);

          if (data.status === 'success') {
            successCount++;
          } else {
            errors.push(data.detail || `Error con ${component.target_sku}`);
          }
        } catch (err) {
          console.error(`${method} error for ${component.target_sku}:`, err);
          errors.push(`Error de conexión con ${component.target_sku}`);
        }
      }

      console.log(`Final: successCount=${successCount}, errors=`, errors);

      if (errors.length > 0) {
        setSaveError(errors.join(', '));
      }

      if (successCount > 0 && errors.length === 0) {
        setIsModalOpen(false);
        setEditingMapping(null);
        setPrefillSKU(null);
        resetForm();
        fetchOrderSKUStats();
        if (viewMode === 'order-skus') {
          fetchOrderSKUs();
        } else {
          fetchMappings();
        }
      }
    } catch (err) {
      console.error('handleSave error:', err);
      setSaveError(`Error inesperado: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Delete mapping
  const handleDelete = async (id: number, hardDelete: boolean = false) => {
    if (!confirm(hardDelete ? 'Eliminar permanentemente este mapeo?' : 'Desactivar este mapeo?')) {
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/api/v1/sku-mappings/${id}?hard_delete=${hardDelete}`,
        { method: 'DELETE' }
      );
      const data = await response.json();
      if (data.status === 'success') {
        fetchOrderSKUStats();
        if (viewMode === 'order-skus') {
          fetchOrderSKUs();
        } else {
          fetchMappings();
        }
      }
    } catch (err) {
      console.error('Error deleting mapping:', err);
    }
  };

  // Open modal for new mapping from order SKU
  const openAddMappingModal = (orderSKU: OrderSKU) => {
    setPrefillSKU({ sku: orderSKU.sku, product_name: orderSKU.product_name });
    setFormData({
      source_pattern: orderSKU.sku,
      rule_name: orderSKU.product_name,
      notes: '',
    });

    // Pre-fill existing components if mapped (PRESERVE IDs for CRUD)
    if (orderSKU.mapping_components && orderSKU.mapping_components.length > 0) {
      setFormComponents(orderSKU.mapping_components.map(comp => ({
        id: comp.id,  // Preserve the ID for updates/deletes
        target_sku: comp.target_sku,
        quantity_multiplier: comp.quantity_multiplier
      })));
    } else if (orderSKU.mapped_to && orderSKU.mapping_status === 'mapped') {
      // Single mapping - we don't have the ID here, so it will be treated as new
      setFormComponents([{
        target_sku: orderSKU.mapped_to,
        quantity_multiplier: orderSKU.quantity_multiplier || 1
      }]);
    } else {
      setFormComponents([{ target_sku: '', quantity_multiplier: 1 }]);
    }

    // Clear state for new modal session
    setDeletedComponentIds([]);
    setOpenDropdownIndex(null);
    setDropdownSearch('');
    setSaveError(null);
    setEditingMapping(null);
    setIsModalOpen(true);
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      source_pattern: '',
      rule_name: '',
      notes: '',
    });
    setFormComponents([{ target_sku: '', quantity_multiplier: 1 }]);
    setPrefillSKU(null);
    setOpenDropdownIndex(null);
    setDropdownSearch('');
    setDeletedComponentIds([]);  // Clear deleted tracking
    setSaveError(null);  // Clear any save errors
  };

  // Filter catalog SKUs based on search (case-insensitive partial match)
  const getFilteredCatalogSKUs = (search: string) => {
    if (!search.trim()) return catalogSKUs;
    const searchLower = search.toLowerCase();
    return catalogSKUs.filter(sku =>
      (sku.sku?.toLowerCase() || '').includes(searchLower) ||
      (sku.product_name?.toLowerCase() || '').includes(searchLower) ||
      (sku.category?.toLowerCase() || '').includes(searchLower)
    );
  };

  // Get display text for selected SKU
  const getSkuDisplayText = (targetSku: string) => {
    if (!targetSku) return '';
    const found = catalogSKUs.find(s => s.sku === targetSku);
    return found ? `${found.sku} - ${found.product_name || 'Sin nombre'}` : targetSku;
  };

  // Add component row
  const addComponent = () => {
    setFormComponents([...formComponents, { target_sku: '', quantity_multiplier: 1 }]);
  };

  // Remove component row (track deleted IDs for database deletion)
  const removeComponent = (index: number) => {
    if (formComponents.length > 1) {
      const componentToRemove = formComponents[index];
      // If this component has an ID (exists in database), track it for deletion
      if (componentToRemove.id) {
        setDeletedComponentIds(prev => [...prev, componentToRemove.id!]);
      }
      setFormComponents(formComponents.filter((_, i) => i !== index));
    }
  };

  // Update component
  const updateComponent = (index: number, field: keyof FormComponent, value: string | number) => {
    const updated = [...formComponents];
    updated[index] = { ...updated[index], [field]: value };
    setFormComponents(updated);
  };

  // Pagination calculations
  const totalPages = Math.ceil(totalCount / pageSize);
  const startIndex = (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, totalCount);

  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible + 2) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (currentPage > 3) pages.push('...');
      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);
      for (let i = start; i <= end; i++) pages.push(i);
      if (currentPage < totalPages - 2) pages.push('...');
      pages.push(totalPages);
    }

    return pages;
  };

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(amount);
  };

  // Handle column sort
  const handleSort = (column: string) => {
    if (sortBy === column) {
      // Toggle direction if same column
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      // New column, default to desc
      setSortBy(column);
      setSortDir('desc');
    }
    setCurrentPage(1);
  };

  // Sort indicator component
  const SortIndicator = ({ column }: { column: string }) => {
    if (sortBy !== column) {
      return (
        <svg className="w-4 h-4 ml-1 text-gray-400 opacity-0 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return sortDir === 'desc' ? (
      <svg className="w-4 h-4 ml-1 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    ) : (
      <svg className="w-4 h-4 ml-1 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    );
  };

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Mapeo de SKUs</h1>
            <p className="text-gray-600">
              Mapea SKUs de pedidos a sus SKUs Primarios del catalogo
            </p>
          </div>

          {/* KPI Stats Cards */}
          {orderSKUStats && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-2xl font-bold text-gray-700">{orderSKUStats.total_order_skus}</div>
                <div className="text-sm text-gray-500">SKUs en Pedidos</div>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-2xl font-bold text-green-600">{orderSKUStats.in_catalog_count}</div>
                <div className="text-sm text-gray-500">En Catalogo</div>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-2xl font-bold text-blue-600">{orderSKUStats.mapped_count}</div>
                <div className="text-sm text-gray-500">Con Mapeo</div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 border-2 border-red-200">
                <div className="text-2xl font-bold text-red-600">{orderSKUStats.unmapped_count}</div>
                <div className="text-sm text-gray-500">Sin Mapear</div>
                <div className="text-xs text-red-500 mt-1">
                  {formatCurrency(orderSKUStats.unmapped_revenue)} en ventas
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-2xl font-bold text-purple-600">{orderSKUStats.coverage_percent}%</div>
                <div className="text-sm text-gray-500">Cobertura</div>
              </div>
            </div>
          )}

          {/* View Toggle & Filters */}
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex gap-4 flex-wrap items-end">
              {/* View Toggle */}
              <div className="flex gap-2">
                <button
                  onClick={() => { setViewMode('order-skus'); setCurrentPage(1); }}
                  className={`px-4 py-2 rounded font-medium ${
                    viewMode === 'order-skus'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  SKUs de Pedidos
                </button>
                <button
                  onClick={() => { setViewMode('mappings'); setCurrentPage(1); }}
                  className={`px-4 py-2 rounded font-medium ${
                    viewMode === 'mappings'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Reglas de Mapeo
                </button>
              </div>

              <div className="flex-1 min-w-[250px]">
                <label className="block text-sm text-gray-600 mb-1">Buscar SKU</label>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Buscar..."
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              {viewMode === 'order-skus' && (
                <div className="w-40">
                  <label className="block text-sm text-gray-600 mb-1">Estado</label>
                  <select
                    value={filterStatus}
                    onChange={(e) => { setFilterStatus(e.target.value); setCurrentPage(1); }}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="unmapped">Sin Mapear</option>
                    <option value="mapped">Mapeados</option>
                    <option value="all">Todos</option>
                  </select>
                </div>
              )}

              <div className="w-28">
                <label className="block text-sm text-gray-600 mb-1">Por pagina</label>
                <select
                  value={pageSize}
                  onChange={(e) => { setPageSize(parseInt(e.target.value)); setCurrentPage(1); }}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="50">50</option>
                  <option value="100">100</option>
                  <option value="500">500</option>
                  <option value="1000">1000</option>
                </select>
              </div>

              <button
                onClick={() => {
                  setEditingMapping(null);
                  setPrefillSKU(null);
                  resetForm();
                  setIsModalOpen(true);
                }}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                + Agregar Mapeo
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded mb-4">
              {error}
              <button onClick={() => setError(null)} className="float-right font-bold">×</button>
            </div>
          )}

          {/* Table */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Cargando...</div>
            ) : viewMode === 'order-skus' ? (
              /* Order SKUs Table */
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 group"
                      onClick={() => handleSort('sku')}
                    >
                      <div className="flex items-center">
                        SKU
                        <SortIndicator column="sku" />
                      </div>
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                    <th
                      className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 group"
                      onClick={() => handleSort('order_count')}
                    >
                      <div className="flex items-center justify-end">
                        Pedidos
                        <SortIndicator column="order_count" />
                      </div>
                    </th>
                    <th
                      className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 group"
                      onClick={() => handleSort('total_revenue')}
                    >
                      <div className="flex items-center justify-end">
                        Ventas
                        <SortIndicator column="total_revenue" />
                      </div>
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estado</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mapeo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Accion</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {orderSKUs.map((sku) => (
                    <tr
                      key={sku.sku}
                      className={`transition-colors ${
                        sku.mapping_status === 'unmapped'
                          ? 'bg-red-50 hover:bg-red-100'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <td className="px-4 py-3 font-mono text-sm">{sku.sku}</td>
                      <td className="px-4 py-3 text-sm text-gray-600 max-w-[250px] truncate" title={sku.product_name}>
                        {sku.product_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-right">{sku.order_count}</td>
                      <td className="px-4 py-3 text-sm text-right">{formatCurrency(sku.total_revenue)}</td>
                      <td className="px-4 py-3 text-center">
                        {sku.mapping_status === 'unmapped' ? (
                          <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">
                            Sin Mapear
                          </span>
                        ) : sku.mapping_status === 'mapped' ? (
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                            Mapeado
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">
                            En Catalogo
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {sku.mapping_status === 'mapped' ? (
                          // Mapped via sku_mappings table
                          sku.mapping_components && sku.component_count > 1 ? (
                            // Multiple components (pack product)
                            <div className="space-y-1">
                              <span className="text-xs text-purple-600 font-medium">
                                Pack ({sku.component_count} componentes)
                              </span>
                              {sku.mapping_components.map((comp, idx) => (
                                <div key={idx} className="font-mono text-xs text-green-700">
                                  → {comp.target_sku}
                                  {comp.quantity_multiplier > 1 && (
                                    <span className="ml-1 text-blue-600">(x{comp.quantity_multiplier})</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span className="font-mono text-green-700">
                              → {sku.mapped_to}
                              {sku.quantity_multiplier && sku.quantity_multiplier > 1 && (
                                <span className="ml-1 text-blue-600">(x{sku.quantity_multiplier})</span>
                              )}
                            </span>
                          )
                        ) : sku.mapping_status === 'in_catalog' ? (
                          // In catalog (direct match or via sku_master)
                          sku.mapped_to && sku.mapped_to !== sku.sku ? (
                            <div>
                              <span className="text-xs text-gray-500">Caja Master →</span>
                              <span className="font-mono text-gray-600 ml-1">{sku.mapped_to}</span>
                              {sku.quantity_multiplier && sku.quantity_multiplier > 1 && (
                                <span className="ml-1 text-gray-500">(x{sku.quantity_multiplier})</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-400">SKU directo</span>
                          )
                        ) : (
                          <span className="text-red-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {sku.mapping_status === 'unmapped' ? (
                          <button
                            onClick={() => openAddMappingModal(sku)}
                            className="text-green-600 hover:text-green-800 font-medium"
                          >
                            + Mapear
                          </button>
                        ) : sku.mapping_status === 'mapped' ? (
                          <div className="flex gap-2">
                            <button
                              onClick={() => openAddMappingModal(sku)}
                              className="text-blue-600 hover:text-blue-800 text-sm"
                              title="Editar mapeo"
                            >
                              Editar
                            </button>
                            {sku.mapping_components && sku.mapping_components.length > 0 && (
                              <button
                                onClick={() => {
                                  // Delete all mapping components for this SKU
                                  if (confirm(`¿Eliminar todos los mapeos para ${sku.sku}?`)) {
                                    Promise.all(
                                      sku.mapping_components!.map(comp =>
                                        fetch(`${API_URL}/api/v1/sku-mappings/${comp.id}?hard_delete=true`, { method: 'DELETE' })
                                      )
                                    ).then(() => {
                                      fetchOrderSKUStats();
                                      fetchOrderSKUs();
                                    });
                                  }
                                }}
                                className="text-red-600 hover:text-red-800 text-sm"
                                title="Eliminar mapeo"
                              >
                                Eliminar
                              </button>
                            )}
                          </div>
                        ) : sku.mapping_status === 'in_catalog' ? (
                          <button
                            onClick={() => openAddMappingModal(sku)}
                            className="text-gray-500 hover:text-gray-700 text-sm"
                            title="Crear mapeo personalizado"
                          >
                            Editar
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              /* Existing Mappings Table */
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU Original</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU Primario</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Multiplicador</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre de Regla</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Notas</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {mappings.map((mapping) => (
                    <tr key={mapping.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-sm">{mapping.source_pattern}</td>
                      <td className="px-4 py-3 font-mono text-sm font-semibold text-green-700">{mapping.target_sku}</td>
                      <td className="px-4 py-3 text-center">
                        {mapping.quantity_multiplier > 1 ? (
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded font-semibold">
                            x{mapping.quantity_multiplier}
                          </span>
                        ) : (
                          <span className="text-gray-400">x1</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700 max-w-[200px] truncate">
                        {mapping.rule_name || <span className="text-gray-400">-</span>}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate">
                        {mapping.notes || <span className="text-gray-400">-</span>}
                      </td>
                      <td className="px-4 py-3 space-x-2">
                        <button
                          onClick={() => handleDelete(mapping.id, true)}
                          className="text-red-600 hover:text-red-800 font-medium"
                        >
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {!loading && ((viewMode === 'order-skus' && orderSKUs.length === 0) || (viewMode === 'mappings' && mappings.length === 0)) && (
              <div className="p-8 text-center text-gray-500">
                No se encontraron resultados
              </div>
            )}
          </div>

          {/* Pagination */}
          {totalCount > 0 && (
            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Mostrando {startIndex} - {endIndex} de {totalCount}
              </div>

              {totalPages > 1 && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => goToPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Anterior
                  </button>

                  {getPageNumbers().map((page, idx) => (
                    page === '...' ? (
                      <span key={`ellipsis-${idx}`} className="px-2 text-gray-400">...</span>
                    ) : (
                      <button
                        key={page}
                        onClick={() => goToPage(page as number)}
                        className={`px-3 py-1 border rounded ${
                          currentPage === page
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'hover:bg-gray-50'
                        }`}
                      >
                        {page}
                      </button>
                    )
                  ))}

                  <button
                    onClick={() => goToPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Siguiente
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">
              {editingMapping ? 'Editar Mapeo' : 'Agregar Mapeo'}
            </h2>

            <div className="space-y-4">
              {/* Source SKU */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SKU Original *
                </label>
                <input
                  type="text"
                  value={formData.source_pattern}
                  onChange={(e) => setFormData({ ...formData, source_pattern: e.target.value })}
                  placeholder="Ej: PACKKSMC_U54010"
                  className="w-full border rounded px-3 py-2 font-mono"
                  readOnly={!!prefillSKU}
                />
                {prefillSKU && (
                  <p className="text-xs text-blue-600 mt-1">
                    Producto: {prefillSKU.product_name}
                  </p>
                )}
              </div>

              {/* Component list */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Componentes del Mapeo *
                  </label>
                  <span className="text-xs text-gray-500">
                    {formComponents.length > 1 ? `${formComponents.length} componentes` : '1 componente'}
                  </span>
                </div>

                <div className="space-y-3 border rounded-lg p-3 bg-gray-50">
                  {formComponents.map((component, index) => (
                    <div key={index} className="flex gap-2 items-start bg-white p-3 rounded border">
                      <div className="flex-1 relative">
                        <label className="block text-xs text-gray-600 mb-1">
                          SKU Primario (Destino)
                        </label>
                        <input
                          type="text"
                          value={openDropdownIndex === index ? dropdownSearch : getSkuDisplayText(component.target_sku)}
                          onChange={(e) => setDropdownSearch(e.target.value)}
                          onFocus={() => {
                            setOpenDropdownIndex(index);
                            setDropdownSearch('');
                          }}
                          onBlur={() => {
                            // Delay to allow click on dropdown item
                            setTimeout(() => setOpenDropdownIndex(null), 200);
                          }}
                          placeholder="Buscar SKU o producto..."
                          className="w-full border rounded px-2 py-1.5 text-sm"
                        />
                        {/* Searchable dropdown */}
                        {openDropdownIndex === index && (
                          <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                            {getFilteredCatalogSKUs(dropdownSearch).length > 0 ? (
                              getFilteredCatalogSKUs(dropdownSearch).slice(0, 50).map((sku) => (
                                <div
                                  key={sku.sku}
                                  onMouseDown={() => {
                                    updateComponent(index, 'target_sku', sku.sku);
                                    setOpenDropdownIndex(null);
                                    setDropdownSearch('');
                                  }}
                                  className={`px-3 py-2 cursor-pointer text-sm hover:bg-blue-50 ${
                                    component.target_sku === sku.sku ? 'bg-blue-100' : ''
                                  }`}
                                >
                                  <span className="font-mono text-blue-600">{sku.sku}</span>
                                  <span className="text-gray-600 ml-2 text-xs">{sku.product_name}</span>
                                  {sku.category && (
                                    <span className="text-gray-400 ml-1 text-xs">({sku.category})</span>
                                  )}
                                </div>
                              ))
                            ) : (
                              <div className="px-3 py-2 text-gray-500 text-sm">
                                No se encontraron resultados para "{dropdownSearch}"
                              </div>
                            )}
                          </div>
                        )}
                        {/* Clear button when SKU is selected */}
                        {component.target_sku && openDropdownIndex !== index && (
                          <button
                            type="button"
                            onClick={() => updateComponent(index, 'target_sku', '')}
                            className="absolute right-2 top-6 text-gray-400 hover:text-gray-600"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        )}
                      </div>
                      <div className="w-24">
                        <label className="block text-xs text-gray-600 mb-1">
                          Cantidad
                        </label>
                        <input
                          type="number"
                          min="1"
                          value={component.quantity_multiplier}
                          onChange={(e) => updateComponent(index, 'quantity_multiplier', parseInt(e.target.value) || 1)}
                          className="w-full border rounded px-2 py-1.5 text-sm"
                        />
                      </div>
                      {formComponents.length > 1 && (
                        <button
                          onClick={() => removeComponent(index)}
                          className="mt-5 text-red-500 hover:text-red-700 p-1"
                          title="Eliminar componente"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </div>
                  ))}

                  <button
                    onClick={addComponent}
                    className="w-full py-2 border-2 border-dashed border-gray-300 rounded text-gray-600 hover:border-blue-400 hover:text-blue-600 text-sm flex items-center justify-center gap-1"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Agregar componente
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Para packs o productos compuestos, agrega un componente por cada SKU que lo conforma
                </p>
              </div>

              {/* Rule name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre de la Regla
                </label>
                <input
                  type="text"
                  value={formData.rule_name}
                  onChange={(e) => setFormData({ ...formData, rule_name: e.target.value })}
                  placeholder="Ej: Pack 4 Barras Surtidas x5"
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notas
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Explicacion adicional..."
                  rows={2}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
            </div>

            {/* Error display inside modal */}
            {saveError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="flex-1">
                    <p className="text-sm text-red-700 font-medium">Error al guardar</p>
                    <p className="text-sm text-red-600 mt-1">{saveError}</p>
                  </div>
                  <button
                    onClick={() => setSaveError(null)}
                    className="text-red-400 hover:text-red-600"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setIsModalOpen(false);
                  setEditingMapping(null);
                  resetForm();
                }}
                disabled={isSaving}
                className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving || !formData.source_pattern || formComponents.every(c => !c.target_sku)}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
              >
                {isSaving ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Guardando...
                  </>
                ) : (
                  formComponents.some(c => c.id)
                    ? `Guardar ${formComponents.filter(c => c.target_sku).length} Mapeos`
                    : formComponents.filter(c => c.target_sku).length > 1
                      ? `Crear ${formComponents.filter(c => c.target_sku).length} Mapeos`
                      : 'Crear Mapeo'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
