'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { StatCardsGridSkeleton, TableSkeleton, FiltersSkeleton } from '@/components/ui/Skeleton';
import MultiSelect from '@/components/ui/MultiSelect';
import { cn, formatCurrency, formatNumber, toTitleCase } from '@/lib/utils';

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
  sku_primario_name?: string;  // Formatted product name for SKU Primario (e.g., "Barra Keto Nuez")
  match_type?: string;
  pack_quantity?: number;
  product_name: string;
  quantity: number;
  unidades?: number;
  conversion_factor?: number;
  peso_display_total?: number;  // Weight per display/unit (kg)
  peso_total?: number;          // Total weight for this order item (kg)
  unit_price: number;
  item_subtotal: number;
  category: string;  // Backend still uses 'category', maps to Familia (BARRAS, CRACKERS, etc)
  family: string;    // Backend still uses 'family', maps to Producto (specific variant)
  format: string;
  customer_null: boolean;
  channel_null: boolean;
  sku_null: boolean;
  in_catalog: boolean;
  is_pack_component?: boolean;  // True if this row is from an expanded variety pack
  pack_parent?: string;         // Original PACK SKU (e.g., "PACKNAVIDAD2")
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

interface FilteredTotals {
  total_pedidos?: number;
  total_unidades?: number;
  total_peso?: number;
  total_revenue?: number;
}

export default function AuditView() {
  const { data: session, status } = useSession();
  const [data, setData] = useState<AuditData[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [filteredTotals, setFilteredTotals] = useState<FilteredTotals | null>(null);
  const [filters, setFilters] = useState<Filters>({ sources: [], channels: [], customers: [], skus: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states (multi-select arrays)
  const [selectedFamilia, setSelectedFamilia] = useState<string[]>([]);
  const [selectedSource, setSelectedSource] = useState<string[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<string[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<string[]>([]);
  const [selectedSKU, setSelectedSKU] = useState<string>('');
  const [skuSearchInput, setSkuSearchInput] = useState<string>('');
  const [showNullsOnly, setShowNullsOnly] = useState(false);
  const [showNotInCatalogOnly, setShowNotInCatalogOnly] = useState(false);

  // Date filter states (multi-select arrays for year and month)
  const [dateFilterType, setDateFilterType] = useState<string>('all'); // 'all', 'year', 'month', 'custom'
  const [selectedYear, setSelectedYear] = useState<string[]>(['2025']);
  const [selectedMonth, setSelectedMonth] = useState<string[]>([]);
  const [customFromDate, setCustomFromDate] = useState<string>('');
  const [customToDate, setCustomToDate] = useState<string>('');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [pageSize, setPageSize] = useState(100);

  // Grouping
  const [groupBy, setGroupBy] = useState<string>('');
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [expandedGroupDetails, setExpandedGroupDetails] = useState<{ [key: string]: AuditData[] }>({});
  const [loadingGroupDetails, setLoadingGroupDetails] = useState<Set<string>>(new Set());

  // Sorting
  const [sortColumn, setSortColumn] = useState<string>('');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Group sorting state
  const [groupSortColumn, setGroupSortColumn] = useState<'none' | 'unidades' | 'revenue'>('none');
  const [groupSortDirection, setGroupSortDirection] = useState<'asc' | 'desc'>('desc');
  const [isAggregatedMode, setIsAggregatedMode] = useState<boolean>(false);

  // Export state
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    if (status === 'authenticated') {
      fetchFilters();
      fetchSummary();
    }
  }, [status]);

  useEffect(() => {
    if (status === 'authenticated') {
      // Clear expanded group details when filters change (forces refetch on next expand)
      setExpandedGroupDetails({});
      fetchData();
    }
  }, [status, selectedFamilia, selectedSource, selectedChannel, selectedCustomer, selectedSKU, showNullsOnly, showNotInCatalogOnly, currentPage, pageSize, groupBy, dateFilterType, selectedYear, selectedMonth, customFromDate, customToDate]);

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

      // Multi-select filters - add each selected value as separate param
      selectedFamilia.forEach(familia => params.append('category', familia));
      selectedSource.forEach(source => params.append('source', source));
      selectedChannel.forEach(channel => params.append('channel', channel));
      selectedCustomer.forEach(customer => params.append('customer', customer));

      if (selectedSKU) params.append('sku', selectedSKU);
      if (showNullsOnly) params.append('has_nulls', 'true');
      if (showNotInCatalogOnly) params.append('not_in_catalog', 'true');

      // Date filters with multi-select support
      if (dateFilterType === 'year' && selectedYear.length > 0) {
        // For multiple years, use the earliest start and latest end
        const years = selectedYear.map(y => parseInt(y)).sort();
        params.append('from_date', `${years[0]}-01-01`);
        params.append('to_date', `${years[years.length - 1]}-12-31`);
      } else if (dateFilterType === 'month' && selectedYear.length > 0 && selectedMonth.length > 0) {
        // For multiple months, calculate range from earliest to latest
        const yearMonths = selectedYear.flatMap(year =>
          selectedMonth.map(month => ({ year: parseInt(year), month: parseInt(month) }))
        ).sort((a, b) => {
          if (a.year !== b.year) return a.year - b.year;
          return a.month - b.month;
        });

        const first = yearMonths[0];
        const last = yearMonths[yearMonths.length - 1];
        const lastDay = new Date(last.year, last.month, 0).getDate();

        params.append('from_date', `${first.year}-${first.month.toString().padStart(2, '0')}-01`);
        params.append('to_date', `${last.year}-${last.month.toString().padStart(2, '0')}-${lastDay}`);
      } else if (dateFilterType === 'custom' && customFromDate && customToDate) {
        params.append('from_date', customFromDate);
        params.append('to_date', customToDate);
      } else if (dateFilterType === 'all') {
        // No date filters - show all data
      }

      // Add server-side group_by parameter (when backend supports it)
      // Map frontend groupBy values to backend parameter values
      // sku_primario uses hybrid server aggregation with CSV mapping
      const groupByMapping: Record<string, string> = {
        'customer_name': 'customer_name',
        'sku_primario': 'sku_primario',  // ✅ Hybrid: server fetches + CSV maps + aggregates
        'category': 'category',
        'channel_name': 'channel_name',
        'order_date': 'order_date',
        'order_month': 'order_month',  // ✅ Group by year-month
        // Additional OLAP-supported group fields
        'sku': 'sku',  // ✅ SKU Original - SQL aggregation
        'order_external_id': 'order_external_id',  // ✅ Pedido - SQL aggregation
        'order_source': 'order_source',  // ✅ Fuente - SQL aggregation
        'family': 'family',  // ✅ Producto - SQL aggregation
        'format': 'format'  // ✅ Formato - SQL aggregation
      };

      // Only add group_by param if backend supports this groupBy value
      if (groupBy && groupByMapping[groupBy]) {
        params.append('group_by', groupByMapping[groupBy]);
        console.log('✅ OLAP: Adding group_by parameter:', groupByMapping[groupBy]);
      } else if (groupBy) {
        console.log('⚠️ Client-side: groupBy value not supported for server aggregation:', groupBy);
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const fullUrl = `${apiUrl}/api/v1/audit/data?${params}`;
      console.log('🌐 API Call:', fullUrl);
      const response = await fetch(fullUrl);
      if (!response.ok) throw new Error('Error fetching audit data');

      const result = await response.json();

      // Check if response is in aggregated mode
      const aggregated = result.mode === 'aggregated';
      console.log('📊 API Response:', {
        mode: result.mode,
        group_by: result.group_by,
        total_groups: result.summary?.total_groups,
        total_pedidos: result.summary?.total_pedidos,
        isAggregated: aggregated
      });
      setIsAggregatedMode(aggregated);

      setData(result.data);

      // Set total count based on mode
      if (aggregated) {
        // In aggregated mode, pagination.total_items represents total groups
        setTotalCount(result.pagination?.total_items || 0);
      } else {
        // In detail mode, meta.total represents total individual items
        setTotalCount(result.meta?.total || 0);
      }

      // Set filtered totals from API summary (all filtered data, not just current page)
      if (result.summary) {
        setFilteredTotals(result.summary);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const fetchGroupDetails = async (groupKey: string, groupValue: string) => {
    // Check if already loaded
    if (expandedGroupDetails[groupKey]) {
      return;
    }

    // Mark as loading
    setLoadingGroupDetails(prev => new Set(prev).add(groupKey));

    try {
      const params = new URLSearchParams({
        limit: '1000', // Fetch up to 1000 detail rows for this group
        offset: '0',
      });

      // Add all current filters
      selectedFamilia.forEach(familia => params.append('category', familia));
      selectedSource.forEach(source => params.append('source', source));
      selectedChannel.forEach(channel => params.append('channel', channel));
      selectedCustomer.forEach(customer => params.append('customer', customer));

      if (selectedSKU) params.append('sku', selectedSKU);
      if (showNullsOnly) params.append('has_nulls', 'true');
      if (showNotInCatalogOnly) params.append('not_in_catalog', 'true');

      // Add date filters
      if (dateFilterType === 'year' && selectedYear.length > 0) {
        const years = selectedYear.map(y => parseInt(y)).sort();
        params.append('from_date', `${years[0]}-01-01`);
        params.append('to_date', `${years[years.length - 1]}-12-31`);
      } else if (dateFilterType === 'month' && selectedYear.length > 0 && selectedMonth.length > 0) {
        const yearMonths = selectedYear.flatMap(year =>
          selectedMonth.map(month => ({ year: parseInt(year), month: parseInt(month) }))
        ).sort((a, b) => {
          if (a.year !== b.year) return a.year - b.year;
          return a.month - b.month;
        });

        const first = yearMonths[0];
        const last = yearMonths[yearMonths.length - 1];
        const lastDay = new Date(last.year, last.month, 0).getDate();

        params.append('from_date', `${first.year}-${first.month.toString().padStart(2, '0')}-01`);
        params.append('to_date', `${last.year}-${last.month.toString().padStart(2, '0')}-${lastDay}`);
      } else if (dateFilterType === 'custom' && customFromDate && customToDate) {
        params.append('from_date', customFromDate);
        params.append('to_date', customToDate);
      }

      // Add specific filter for this group value
      if (groupBy === 'order_date') {
        // For date grouping, filter by specific date
        params.set('from_date', groupValue);
        params.set('to_date', groupValue);
      } else if (groupBy === 'order_month') {
        // For month grouping (e.g., "2025-09"), filter by date range for that month
        const [year, month] = groupValue.split('-').map(Number);
        const lastDay = new Date(year, month, 0).getDate(); // Get last day of month
        params.set('from_date', `${year}-${month.toString().padStart(2, '0')}-01`);
        params.set('to_date', `${year}-${month.toString().padStart(2, '0')}-${lastDay}`);
      } else if (groupBy === 'customer_name') {
        params.set('customer', groupValue);
      } else if (groupBy === 'channel_name') {
        params.set('channel', groupValue);
      } else if (groupBy === 'category') {
        params.set('category', groupValue);
      } else if (groupBy === 'order_source') {
        params.set('source', groupValue);
      } else if (groupBy === 'sku' || groupBy === 'family') {
        // For SKU or family grouping, filter by the SKU value
        params.set('sku', groupValue);
      }
      // Note: sku_primario can't be filtered server-side (requires CSV mapping)
      // We'll fetch detail rows and filter client-side below

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const fullUrl = `${apiUrl}/api/v1/audit/data?${params}`;
      console.log('🔍 Fetching group details:', { groupKey, groupValue, url: fullUrl });

      const response = await fetch(fullUrl);
      if (!response.ok) throw new Error('Error fetching group details');

      const result = await response.json();
      let detailData = result.data;

      // For sku_primario, filter client-side to only show rows matching this group
      if (groupBy === 'sku_primario') {
        detailData = detailData.filter((item: AuditData) => {
          // Match if sku_primario equals groupValue, or if both are null/undefined
          return (item.sku_primario === groupValue) ||
                 (!item.sku_primario && groupValue === 'SIN CLASIFICAR');
        });
      }

      // Store detail rows for this group
      setExpandedGroupDetails(prev => ({
        ...prev,
        [groupKey]: detailData
      }));

      console.log(`✅ Loaded ${detailData.length} detail rows for group: ${groupKey}`);
    } catch (err) {
      console.error('Error fetching group details:', err);
    } finally {
      // Remove from loading set
      setLoadingGroupDetails(prev => {
        const newSet = new Set(prev);
        newSet.delete(groupKey);
        return newSet;
      });
    }
  };

  const clearFilters = () => {
    setSelectedFamilia([]);
    setSelectedSource([]);
    setSelectedChannel([]);
    setSelectedCustomer([]);
    setSelectedSKU('');
    setSkuSearchInput('');
    setShowNullsOnly(false);
    setShowNotInCatalogOnly(false);
    setDateFilterType('all');
    setSelectedYear(['2025']);
    setSelectedMonth([]);
    setCustomFromDate('');
    setCustomToDate('');
    setCurrentPage(1);
    // Clear expanded group details when filters change
    setExpandedGroupDetails({});
  };

  const handleExport = async () => {
    setIsExporting(true);

    try {
      const params = new URLSearchParams();

      // Add all current filters (same as fetchData)
      selectedFamilia.forEach(familia => params.append('category', familia));
      selectedSource.forEach(source => params.append('source', source));
      selectedChannel.forEach(channel => params.append('channel', channel));
      selectedCustomer.forEach(customer => params.append('customer', customer));

      if (selectedSKU) params.append('sku', selectedSKU);
      if (showNullsOnly) params.append('has_nulls', 'true');
      if (showNotInCatalogOnly) params.append('not_in_catalog', 'true');

      // Date filters
      if (dateFilterType === 'year' && selectedYear.length > 0) {
        const years = selectedYear.map(y => parseInt(y)).sort();
        params.append('from_date', `${years[0]}-01-01`);
        params.append('to_date', `${years[years.length - 1]}-12-31`);
      } else if (dateFilterType === 'month' && selectedYear.length > 0 && selectedMonth.length > 0) {
        const yearMonths = selectedYear.flatMap(year =>
          selectedMonth.map(month => ({ year: parseInt(year), month: parseInt(month) }))
        ).sort((a, b) => {
          if (a.year !== b.year) return a.year - b.year;
          return a.month - b.month;
        });

        const first = yearMonths[0];
        const last = yearMonths[yearMonths.length - 1];
        const lastDay = new Date(last.year, last.month, 0).getDate();

        params.append('from_date', `${first.year}-${first.month.toString().padStart(2, '0')}-01`);
        params.append('to_date', `${last.year}-${last.month.toString().padStart(2, '0')}-${lastDay}`);
      } else if (dateFilterType === 'custom' && customFromDate && customToDate) {
        params.append('from_date', customFromDate);
        params.append('to_date', customToDate);
      }

      // Include grouping if active
      if (groupBy) {
        params.append('group_by', groupBy);
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const exportUrl = `${apiUrl}/api/v1/audit/export?${params}`;

      // Fetch the file as blob and trigger download
      const response = await fetch(exportUrl);

      if (!response.ok) {
        throw new Error('Error al exportar datos');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // Extract filename from Content-Disposition header if available
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'auditoria_export.xlsx';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) {
          filename = match[1].replace(/"/g, '');
        }
      }

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (err) {
      console.error('Error exporting:', err);
      alert('Error al exportar. Por favor intenta de nuevo.');
    } finally {
      setIsExporting(false);
    }
  };

  const toggleGroupCollapse = (groupKey: string) => {
    const isCurrentlyCollapsed = collapsedGroups.has(groupKey);

    // Toggle collapse state
    setCollapsedGroups((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(groupKey)) {
        newSet.delete(groupKey);
      } else {
        newSet.add(groupKey);
      }
      return newSet;
    });

    // If expanding in OLAP/aggregated mode, fetch detail rows
    if (isCurrentlyCollapsed && isAggregatedMode) {
      fetchGroupDetails(groupKey, groupKey); // groupKey is the group value
    }
  };

  const toggleAllGroups = () => {
    const allGroupKeys = Object.keys(groupData(data, groupBy));

    // If all groups are collapsed, expand them all
    // If any group is expanded, collapse them all
    if (collapsedGroups.size === allGroupKeys.length) {
      setCollapsedGroups(new Set());
    } else {
      setCollapsedGroups(new Set(allGroupKeys));
    }
  };

  const handleGroupSort = (column: 'unidades' | 'revenue') => {
    if (groupSortColumn === column) {
      // Toggle direction if clicking same column
      setGroupSortDirection(groupSortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New column, default to descending (highest first)
      setGroupSortColumn(column);
      setGroupSortDirection('desc');
    }
  };

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      // Toggle direction if clicking same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New column - default to ascending
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const sortData = (data: AuditData[]) => {
    if (!sortColumn) return data;

    return [...data].sort((a, b) => {
      let aVal: any = (a as any)[sortColumn];
      let bVal: any = (b as any)[sortColumn];

      // Handle null/undefined
      if (aVal === null || aVal === undefined) aVal = '';
      if (bVal === null || bVal === undefined) bVal = '';

      // Handle numbers
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      // Handle strings (case-insensitive)
      const aStr = String(aVal).toLowerCase();
      const bStr = String(bVal).toLowerCase();

      if (aStr < bStr) return sortDirection === 'asc' ? -1 : 1;
      if (aStr > bStr) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  };

  const groupData = (data: AuditData[], groupByField: string) => {
    // AGGREGATED MODE: Data is already grouped by server
    // Structure: [{group_value, pedidos, cantidad, total_revenue}, ...]
    if (isAggregatedMode) {
      const grouped: { [key: string]: any[] } = {};
      data.forEach((item: any) => {
        const key = String(item.group_value || 'SIN CLASIFICAR');
        // Store aggregated data as-is (already computed on server)
        grouped[key] = [item];
      });
      return grouped;
    }

    // DETAIL MODE: Client-side grouping of individual items
    if (!groupByField) return { '': sortData(data) };

    const grouped: { [key: string]: AuditData[] } = {};
    data.forEach((item) => {
      const key = String((item as any)[groupByField] || 'SIN CLASIFICAR');
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(item);
    });

    // Sort each group's items
    Object.keys(grouped).forEach((key) => {
      grouped[key] = sortData(grouped[key]);
    });

    // Sort groups by totals if requested
    if (groupSortColumn !== 'none') {
      const groupsWithTotals = Object.entries(grouped).map(([key, items]) => ({
        key,
        items,
        totalUnidades: items.reduce((sum, item) => sum + (item.unidades || 0), 0),
        totalRevenue: items.reduce((sum, item) => sum + (item.item_subtotal || 0), 0),
      }));

      // Sort by selected column and direction
      groupsWithTotals.sort((a, b) => {
        let comparison = 0;
        if (groupSortColumn === 'unidades') {
          comparison = a.totalUnidades - b.totalUnidades;
        } else if (groupSortColumn === 'revenue') {
          comparison = a.totalRevenue - b.totalRevenue;
        }
        return groupSortDirection === 'asc' ? comparison : -comparison;
      });

      // Reconstruct grouped object in sorted order
      const sortedGrouped: { [key: string]: AuditData[] } = {};
      groupsWithTotals.forEach(({ key, items }) => {
        sortedGrouped[key] = items;
      });
      return sortedGrouped;
    }

    return grouped;
  };

  const groupedData = groupData(data, groupBy);
  const totalPages = Math.ceil(totalCount / pageSize);

  // Use filtered totals from API (all filtered data) instead of current page totals
  // Add defensive defaults (|| 0) in case API doesn't return all fields
  const overallTotals = filteredTotals ? {
    totalPedidos: filteredTotals.total_pedidos || 0,
    totalUnidades: filteredTotals.total_unidades || 0,
    totalPeso: filteredTotals.total_peso || 0,
    totalRevenue: filteredTotals.total_revenue || 0,
  } : {
    // Fallback to page totals if API summary not available yet
    totalPedidos: new Set(data.map(item => item.order_external_id)).size,
    totalUnidades: data.reduce((sum, item) => sum + (item.unidades || 0), 0),
    totalPeso: data.reduce((sum, item) => sum + (item.peso_total || 0), 0),
    totalRevenue: data.reduce((sum, item) => sum + (item.item_subtotal || 0), 0),
  };

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600">Cargando...</div>
      </div>
    );
  }

  return (
    <div>
      {/* Debug Badge - Shows aggregation mode */}
      {groupBy && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
              isAggregatedMode
                ? 'bg-green-100 text-green-800'
                : 'bg-yellow-100 text-yellow-800'
            }`}>
              {isAggregatedMode ? '✅ Modo OLAP (servidor)' : '⚠️ Modo Detail (cliente)'}
            </span>
            <span className="text-sm text-gray-600">
              Agrupado por: <strong>{groupBy}</strong>
            </span>
            {isAggregatedMode && groupBy === 'sku_primario' && (
              <span className="text-xs text-green-600 font-medium">
                ✨ Totales con mapeo CSV (100% precisión) sobre TODOS los datos filtrados
              </span>
            )}
            {isAggregatedMode && groupBy !== 'sku_primario' && (
              <span className="text-xs text-green-600 font-medium">
                Totales calculados por PostgreSQL sobre TODOS los datos filtrados
              </span>
            )}
            {!isAggregatedMode && (
              <span className="text-xs text-yellow-600 font-medium">
                ⚠️ Totales solo de la página actual - refresca la página para activar OLAP
              </span>
            )}
          </div>
        </div>
      )}

      {/* Summary Cards - Always visible, with loading skeleton */}
      {loading ? (
        <StatCardsGridSkeleton count={4} />
      ) : data.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {[
            { label: 'Total Pedidos', icon: '📦', gradient: 'from-blue-500 to-blue-600' },
            { label: 'Total Unidades', icon: '📊', gradient: 'from-green-500 to-green-600' },
            { label: 'Peso Total', icon: '⚖️', gradient: 'from-orange-500 to-orange-600' },
            { label: 'Total Ingresos', icon: '💰', gradient: 'from-purple-500 to-purple-600' },
          ].map((card, i) => (
            <div key={i} className={cn('bg-gradient-to-br rounded-xl shadow-lg p-6 text-white opacity-60', card.gradient)}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/70 text-sm font-medium uppercase tracking-wide">{card.label}</p>
                  <p className="text-4xl font-bold mt-2">--</p>
                  <p className="text-white/50 text-xs mt-1">Sin datos</p>
                </div>
                <div className="text-5xl opacity-20">{card.icon}</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {/* Total Pedidos */}
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg p-6 text-white transform hover:scale-[1.02] transition-all duration-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100 text-sm font-medium uppercase tracking-wide">Total Pedidos</p>
                <p className="text-4xl font-bold mt-2">{overallTotals.totalPedidos.toLocaleString('es-CL')}</p>
                <p className="text-blue-100 text-xs mt-1">
                  {filteredTotals ? 'Filtros aplicados' : 'En esta página'}
                </p>
              </div>
              <div className="text-5xl opacity-20">
                📦
              </div>
            </div>
          </div>

          {/* Total Unidades */}
          <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-lg p-6 text-white transform hover:scale-[1.02] transition-all duration-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-100 text-sm font-medium uppercase tracking-wide">Total Unidades</p>
                <p className="text-4xl font-bold mt-2">{overallTotals.totalUnidades.toLocaleString('es-CL')}</p>
                <p className="text-green-100 text-xs mt-1">
                  {filteredTotals ? 'Todas las páginas' : 'En esta página'}
                </p>
              </div>
              <div className="text-5xl opacity-20">
                📊
              </div>
            </div>
          </div>

          {/* Total Peso */}
          <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl shadow-lg p-6 text-white transform hover:scale-[1.02] transition-all duration-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-orange-100 text-sm font-medium uppercase tracking-wide">Peso Total</p>
                <p className="text-4xl font-bold mt-2">{overallTotals.totalPeso.toLocaleString('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg</p>
                <p className="text-orange-100 text-xs mt-1">
                  {filteredTotals ? 'Todas las páginas' : 'En esta página'}
                </p>
              </div>
              <div className="text-5xl opacity-20">
                ⚖️
              </div>
            </div>
          </div>

          {/* Total Revenue */}
          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-lg p-6 text-white transform hover:scale-[1.02] transition-all duration-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-purple-100 text-sm font-medium uppercase tracking-wide">Total Ingresos</p>
                <p className="text-4xl font-bold mt-2">${(overallTotals.totalRevenue / 1000000).toFixed(1)}M</p>
                <p className="text-purple-100 text-xs mt-1">
                  ${overallTotals.totalRevenue.toLocaleString('es-CL')} CLP • {filteredTotals ? 'Filtrados' : 'Página actual'}
                </p>
              </div>
              <div className="text-5xl opacity-20">
                💰
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Large Dataset Warning */}
      {!loading && filteredTotals && filteredTotals.total_pedidos !== undefined && filteredTotals.total_pedidos > 1000 && groupBy && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-700">
                <strong>Dataset grande detectado:</strong> {filteredTotals.total_pedidos.toLocaleString('es-CL')} pedidos encontrados.
                Se recomienda usar filtros de fecha o familia para mejorar el rendimiento.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gray-100 rounded-lg">
              <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Filtros</h2>
              <p className="text-xs text-gray-500">Refina tu búsqueda para obtener resultados específicos</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExport}
              disabled={isExporting || loading}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-green-400 disabled:cursor-not-allowed rounded-lg transition-colors shadow-sm"
            >
              {isExporting ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Exportando...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Exportar Excel
                </>
              )}
            </button>
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Limpiar filtros
            </button>
          </div>
        </div>

        {/* Familia Selector */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Familia de Producto</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <button
              onClick={() => { setSelectedFamilia([]); setCurrentPage(1); }}
              className={`flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all ${
                selectedFamilia.length === 0
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }`}
            >
              <span className="text-3xl mb-1">📦</span>
              <span className={`text-sm font-medium ${selectedFamilia.length === 0 ? 'text-green-700' : 'text-gray-700'}`}>
                Todas
              </span>
            </button>
            <button
              onClick={() => {
                if (selectedFamilia.includes('BARRAS')) {
                  setSelectedFamilia(selectedFamilia.filter(f => f !== 'BARRAS'));
                } else {
                  setSelectedFamilia([...selectedFamilia, 'BARRAS']);
                }
                setCurrentPage(1);
              }}
              className={`flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all ${
                selectedFamilia.includes('BARRAS')
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }`}
            >
              <span className="text-3xl mb-1">🍫</span>
              <span className={`text-sm font-medium ${selectedFamilia.includes('BARRAS') ? 'text-green-700' : 'text-gray-700'}`}>
                BARRAS
              </span>
            </button>
            <button
              onClick={() => {
                if (selectedFamilia.includes('CRACKERS')) {
                  setSelectedFamilia(selectedFamilia.filter(f => f !== 'CRACKERS'));
                } else {
                  setSelectedFamilia([...selectedFamilia, 'CRACKERS']);
                }
                setCurrentPage(1);
              }}
              className={`flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all ${
                selectedFamilia.includes('CRACKERS')
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }`}
            >
              <span className="text-3xl mb-1">🍘</span>
              <span className={`text-sm font-medium ${selectedFamilia.includes('CRACKERS') ? 'text-green-700' : 'text-gray-700'}`}>
                CRACKERS
              </span>
            </button>
            <button
              onClick={() => {
                if (selectedFamilia.includes('GRANOLAS')) {
                  setSelectedFamilia(selectedFamilia.filter(f => f !== 'GRANOLAS'));
                } else {
                  setSelectedFamilia([...selectedFamilia, 'GRANOLAS']);
                }
                setCurrentPage(1);
              }}
              className={`flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all ${
                selectedFamilia.includes('GRANOLAS')
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }`}
            >
              <span className="text-3xl mb-1">🥣</span>
              <span className={`text-sm font-medium ${selectedFamilia.includes('GRANOLAS') ? 'text-green-700' : 'text-gray-700'}`}>
                GRANOLAS
              </span>
            </button>
            <button
              onClick={() => {
                if (selectedFamilia.includes('KEEPERS')) {
                  setSelectedFamilia(selectedFamilia.filter(f => f !== 'KEEPERS'));
                } else {
                  setSelectedFamilia([...selectedFamilia, 'KEEPERS']);
                }
                setCurrentPage(1);
              }}
              className={`flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all ${
                selectedFamilia.includes('KEEPERS')
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }`}
            >
              <span className="text-3xl mb-1">🍪</span>
              <span className={`text-sm font-medium ${selectedFamilia.includes('KEEPERS') ? 'text-green-700' : 'text-gray-700'}`}>
                KEEPERS
              </span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
          {/* Channel Filter - Modern MultiSelect */}
          <MultiSelect
            label="Canal"
            options={filters.channels}
            selected={selectedChannel}
            onChange={(values) => { setSelectedChannel(values); setCurrentPage(1); }}
            placeholder="Seleccionar canales..."
            searchable={true}
            maxHeight="200px"
          />

          {/* Customer Filter - Modern MultiSelect */}
          <MultiSelect
            label="Cliente"
            options={filters.customers}
            selected={selectedCustomer}
            onChange={(values) => { setSelectedCustomer(values); setCurrentPage(1); }}
            placeholder="Seleccionar clientes..."
            searchable={true}
            maxHeight="250px"
          />

          {/* Multi-field Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Búsqueda Global</label>
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={skuSearchInput}
                onChange={(e) => setSkuSearchInput(e.target.value)}
                placeholder="Cliente, Producto, Pedido, Canal, SKU..."
                className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
              />
              {skuSearchInput && (
                <button
                  type="button"
                  onClick={() => setSkuSearchInput('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
            {skuSearchInput && (
              <div className="mt-1.5 text-xs text-gray-500 flex items-center gap-1">
                <span className="inline-block w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
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
            <option value="order_external_id">Pedido</option>
            <option value="order_source">Fuente</option>
            <option value="channel_name">Canal</option>
            <option value="customer_name">Cliente</option>
            <option value="order_month">Mes</option>
            <option value="sku">SKU Original</option>
            <option value="sku_primario">SKU Primario</option>
            <option value="family">Producto</option>
            <option value="format">Formato</option>
          </select>
        </div>

        {/* Group Controls - Show only when grouping is active */}
        {groupBy && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-3">Controles de Grupos</h4>

            <div className="flex flex-col md:flex-row gap-4">
              {/* Toggle Expand/Collapse All */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-2">Vista</label>
                <button
                  onClick={toggleAllGroups}
                  className={`px-4 py-2 text-white text-sm rounded-lg transition-colors flex items-center gap-2 ${
                    collapsedGroups.size === Object.keys(groupData(data, groupBy)).length
                      ? 'bg-blue-500 hover:bg-blue-600'
                      : 'bg-gray-500 hover:bg-gray-600'
                  }`}
                >
                  <span>{collapsedGroups.size === Object.keys(groupData(data, groupBy)).length ? '▼' : '▶'}</span>
                  {collapsedGroups.size === Object.keys(groupData(data, groupBy)).length ? 'Expandir Todos' : 'Colapsar Todos'}
                </button>
              </div>

              {/* Group Sorting Buttons */}
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-600 mb-2">Ordenar grupos por</label>
                <div className="flex gap-2 flex-wrap">
                  {/* Alphabetical (default) */}
                  <button
                    onClick={() => {
                      setGroupSortColumn('none');
                      setGroupSortDirection('asc');
                    }}
                    className={`px-4 py-2 text-sm rounded-lg border transition-colors flex items-center gap-2 ${
                      groupSortColumn === 'none'
                        ? 'bg-blue-500 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    Alfabético
                    <span className="text-gray-400">{groupSortColumn === 'none' ? '🔤' : ''}</span>
                  </button>

                  {/* Sort by Unidades */}
                  <button
                    onClick={() => handleGroupSort('unidades')}
                    className={`px-4 py-2 text-sm rounded-lg border transition-colors flex items-center gap-2 ${
                      groupSortColumn === 'unidades'
                        ? 'bg-green-500 text-white border-green-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    Unidades
                    <span className="text-xs">
                      {groupSortColumn === 'unidades' ? (
                        groupSortDirection === 'asc' ? '▲' : '▼'
                      ) : (
                        '⇅'
                      )}
                    </span>
                  </button>

                  {/* Sort by Revenue */}
                  <button
                    onClick={() => handleGroupSort('revenue')}
                    className={`px-4 py-2 text-sm rounded-lg border transition-colors flex items-center gap-2 ${
                      groupSortColumn === 'revenue'
                        ? 'bg-purple-500 text-white border-purple-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    Total $
                    <span className="text-xs">
                      {groupSortColumn === 'revenue' ? (
                        groupSortDirection === 'asc' ? '▲' : '▼'
                      ) : (
                        '⇅'
                      )}
                    </span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Date Filters */}
        <div className="mt-6 border-t border-gray-200 pt-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">📅 Filtros Temporales</h3>

          {/* Date Filter Type Selector */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de filtro</label>
            <select
              value={dateFilterType}
              onChange={(e) => { setDateFilterType(e.target.value); setCurrentPage(1); }}
              className="w-full md:w-64 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">📦 Todos los periodos</option>
              <option value="year">📅 Por año</option>
              <option value="month">📆 Por mes</option>
              <option value="custom">🗓️ Rango personalizado</option>
            </select>
          </div>

          {/* Year Filter */}
          {(dateFilterType === 'year' || dateFilterType === 'month') && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  Año <span className="text-xs text-gray-500">(Ctrl/Cmd + click)</span>
                </label>
                {selectedYear.length > 0 && (
                  <button
                    onClick={() => { setSelectedYear(['2025']); setCurrentPage(1); }}
                    className="text-xs text-blue-600 hover:text-blue-800 underline"
                  >
                    Limpiar
                  </button>
                )}
              </div>
              <select
                multiple
                value={selectedYear}
                onChange={(e) => {
                  const options = Array.from(e.target.selectedOptions, option => option.value);
                  setSelectedYear(options);
                  setCurrentPage(1);
                }}
                size={5}
                className="w-full md:w-48 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="2025">2025 (3,687 órdenes)</option>
                <option value="2024">2024 (379 órdenes)</option>
                <option value="2023">2023 (502 órdenes)</option>
                <option value="2022">2022 (270 órdenes)</option>
                <option value="2021">2021 (2,543 órdenes)</option>
              </select>
              {selectedYear.length > 0 && (
                <div className="mt-1 text-xs text-blue-600">
                  {selectedYear.length} año{selectedYear.length > 1 ? 's' : ''} seleccionado{selectedYear.length > 1 ? 's' : ''}
                </div>
              )}
            </div>
          )}

          {/* Month Filter */}
          {dateFilterType === 'month' && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  Mes <span className="text-xs text-gray-500">(Ctrl/Cmd + click)</span>
                </label>
                {selectedMonth.length > 0 && (
                  <button
                    onClick={() => { setSelectedMonth([]); setCurrentPage(1); }}
                    className="text-xs text-blue-600 hover:text-blue-800 underline"
                  >
                    Limpiar
                  </button>
                )}
              </div>
              <select
                multiple
                value={selectedMonth}
                onChange={(e) => {
                  const options = Array.from(e.target.selectedOptions, option => option.value);
                  setSelectedMonth(options);
                  setCurrentPage(1);
                }}
                size={6}
                className="w-full md:w-48 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="1">Enero</option>
                <option value="2">Febrero</option>
                <option value="3">Marzo</option>
                <option value="4">Abril</option>
                <option value="5">Mayo</option>
                <option value="6">Junio</option>
                <option value="7">Julio</option>
                <option value="8">Agosto</option>
                <option value="9">Septiembre</option>
                <option value="10">Octubre</option>
                <option value="11">Noviembre</option>
                <option value="12">Diciembre</option>
              </select>
              {selectedMonth.length > 0 && (
                <div className="mt-1 text-xs text-blue-600">
                  {selectedMonth.length} mes{selectedMonth.length > 1 ? 'es' : ''} seleccionado{selectedMonth.length > 1 ? 's' : ''}
                </div>
              )}
            </div>
          )}

          {/* Custom Date Range */}
          {dateFilterType === 'custom' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Desde
                  <span className="text-xs text-gray-500 ml-1">(desde may 2021)</span>
                </label>
                <input
                  type="date"
                  value={customFromDate}
                  onChange={(e) => { setCustomFromDate(e.target.value); setCurrentPage(1); }}
                  min="2021-05-06"
                  max="2025-11-05"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Hasta
                  <span className="text-xs text-gray-500 ml-1">(hasta nov 2025)</span>
                </label>
                <input
                  type="date"
                  value={customToDate}
                  onChange={(e) => { setCustomToDate(e.target.value); setCurrentPage(1); }}
                  min="2021-05-06"
                  max="2025-11-05"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}

          {/* Date Filter Summary */}
          {dateFilterType !== 'all' && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <div className="text-sm text-blue-800">
                <strong>Filtro activo:</strong>{' '}
                {dateFilterType === 'year' && selectedYear.length > 0 && (
                  selectedYear.length === 1
                    ? `Año ${selectedYear[0]}`
                    : `Años ${selectedYear.join(', ')}`
                )}
                {dateFilterType === 'month' && selectedYear.length > 0 && selectedMonth.length > 0 && (
                  (() => {
                    const months = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
                    const combinations = selectedYear.flatMap(year =>
                      selectedMonth.map(month => `${months[parseInt(month)]} ${year}`)
                    );
                    return combinations.join(', ');
                  })()
                )}
                {dateFilterType === 'custom' && customFromDate && customToDate && (
                  `Desde ${customFromDate} hasta ${customToDate}`
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-6">
              <div className="flex items-center justify-center gap-3 py-8">
                <div className="relative">
                  <div className="w-10 h-10 border-4 border-gray-200 rounded-full"></div>
                  <div className="w-10 h-10 border-4 border-green-500 rounded-full animate-spin border-t-transparent absolute top-0 left-0"></div>
                </div>
                <div className="text-gray-600">
                  <p className="font-medium">Cargando datos...</p>
                  <p className="text-xs text-gray-400">Esto puede tomar unos segundos</p>
                </div>
              </div>
              <TableSkeleton rows={5} columns={8} />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-16 px-4">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <p className="text-red-600 font-medium text-lg">Error al cargar datos</p>
              <p className="text-gray-500 text-sm mt-1">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors text-sm font-medium"
              >
                Reintentar
              </button>
            </div>
          ) : data.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-4">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-gray-700 font-medium text-lg">Sin resultados</p>
              <p className="text-gray-500 text-sm mt-1 text-center max-w-md">
                No se encontraron datos con los filtros seleccionados. Intenta ajustar tus criterios de búsqueda.
              </p>
              <button
                onClick={clearFilters}
                className="mt-4 px-4 py-2 bg-green-50 text-green-600 rounded-lg hover:bg-green-100 transition-colors text-sm font-medium"
              >
                Limpiar filtros
              </button>
            </div>
          ) : (
            <>
              {Object.entries(groupedData).map(([groupKey, groupItems]) => {
                // Calculate group subtotals based on mode
                let groupCantidad, groupUnidades, groupTotal, groupPedidos, groupSkuPrimarioName;

                if (isAggregatedMode && groupItems[0]) {
                  // AGGREGATED MODE: Use pre-computed totals from server
                  const agg = groupItems[0] as any;
                  groupCantidad = agg.cantidad || 0;  // Raw quantity sum
                  groupUnidades = agg.total_unidades || 0;  // Properly converted units
                  groupTotal = agg.total_revenue || 0;
                  groupPedidos = agg.pedidos || 0;
                  groupSkuPrimarioName = agg.sku_primario_name || null;
                } else {
                  // DETAIL MODE: Calculate from individual items
                  groupCantidad = groupItems.reduce((sum, item) => sum + (item.quantity || 0), 0);
                  groupUnidades = groupItems.reduce((sum, item) => sum + (item.unidades || 0), 0);
                  groupTotal = groupItems.reduce((sum, item) => sum + (item.item_subtotal || 0), 0);
                  groupPedidos = new Set(groupItems.map(item => item.order_external_id)).size;
                  // Get sku_primario_name from first item if grouping by sku_primario
                  groupSkuPrimarioName = groupBy === 'sku_primario' && groupItems[0] ? groupItems[0].sku_primario_name : null;
                }

                const isCollapsed = collapsedGroups.has(groupKey);

                return (
                <div key={groupKey} className="mb-6">
                  {groupBy && (
                    <div className="bg-gray-100 px-6 py-3 border-b border-gray-200">
                      <div className="flex justify-between items-center">
                        <button
                          onClick={() => toggleGroupCollapse(groupKey)}
                          className="flex items-center gap-3 hover:bg-gray-200 rounded-lg px-3 py-2 -ml-3 transition-colors"
                        >
                          <span className="text-gray-600 text-lg">
                            {isCollapsed ? '▶' : '▼'}
                          </span>
                          <h3 className="font-semibold text-gray-900">
                            {groupKey}
                            {groupSkuPrimarioName && groupBy === 'sku_primario' && (
                              <span className="font-normal"> - {groupSkuPrimarioName}</span>
                            )}
                            {' '}
                            <span className="text-sm font-normal text-gray-600">
                              ({isAggregatedMode ? `${groupPedidos} pedidos` : `${groupItems.length} registros`})
                            </span>
                          </h3>
                        </button>
                        <div className="flex gap-6 text-sm">
                          <div className="text-right">
                            <span className="text-gray-600">Cantidad Total: </span>
                            <span className="font-semibold text-orange-600">{groupCantidad.toLocaleString('es-CL')}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-gray-600">Unidades Totales: </span>
                            <span className="font-semibold text-green-600">{groupUnidades.toLocaleString('es-CL')}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-gray-600">Total Grupo: </span>
                            <span className="font-semibold text-blue-600">${groupTotal.toLocaleString('es-CL')}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  {!isCollapsed && (
                    <>
                      {/* OLAP MODE: Show detail rows if available */}
                      {isAggregatedMode && (
                        <div className="px-6 py-4">
                          {loadingGroupDetails.has(groupKey) ? (
                            <div className="text-center py-4 text-gray-600">
                              <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-2"></div>
                              Cargando detalles del grupo...
                            </div>
                          ) : expandedGroupDetails[groupKey] ? (
                            <>
                              <div className="mb-2 text-sm text-blue-600 font-medium">
                                📋 Mostrando {expandedGroupDetails[groupKey].length} registros detallados
                                {expandedGroupDetails[groupKey].length >= 1000 && (
                                  <span className="ml-2 text-yellow-600">
                                    ⚠️ Limitado a 1000 registros. Use filtros más específicos para ver todos los datos.
                                  </span>
                                )}
                              </div>
                              <table className="min-w-full divide-y divide-gray-200 text-xs">
                                <thead className="bg-gray-50">
                                  <tr>
                                    {[
                                      { label: 'Pedido', field: 'order_external_id' },
                                      { label: 'Fecha', field: 'order_date' },
                                      { label: 'Cliente', field: 'customer_name' },
                                      { label: 'Canal', field: 'channel_name' },
                                      { label: 'SKU', field: 'sku' },
                                      { label: 'Primario', field: 'sku_primario' },
                                      { label: 'Familia', field: 'category' },
                                      { label: 'Producto', field: 'product_name' },
                                      { label: 'Cant.', field: 'quantity' },
                                      { label: 'Uds.', field: 'unidades' },
                                      { label: 'Peso', field: 'peso_total' },
                                      { label: 'Precio', field: 'unit_price' },
                                      { label: 'Total', field: 'item_subtotal' },
                                    ].map(({ label, field }) => (
                                      <th
                                        key={field}
                                        className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-tight"
                                      >
                                        {label}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                  {expandedGroupDetails[groupKey].map((item, idx) => (
                                    <tr key={`${item.item_id}-${idx}`} className={`hover:bg-gray-50 ${item.is_pack_component ? 'bg-indigo-50/50' : ''}`}>
                                      <td className="px-2 py-2 text-xs text-gray-900">
                                        <div className="font-medium">{item.order_external_id}</div>
                                        <div className="text-gray-500">{item.order_source}</div>
                                      </td>
                                      <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-600">
                                        {new Date(item.order_date).toLocaleDateString('es-CL')}
                                      </td>
                                      <td className="px-2 py-2 text-xs max-w-24">
                                        <div className={`break-words leading-tight ${item.customer_null ? 'text-red-600 font-medium' : 'text-gray-900'}`}>
                                          {toTitleCase(item.customer_name)}
                                        </div>
                                        <div className="text-gray-500 truncate">{item.customer_rut}</div>
                                      </td>
                                      <td className="px-2 py-2 text-xs max-w-20">
                                        <div className={`break-words ${item.channel_null ? 'text-red-600 font-medium' : 'text-gray-900'}`}>
                                          {toTitleCase(item.channel_name)}
                                        </div>
                                      </td>
                                      <td className="px-2 py-2 text-xs max-w-24">
                                        <div className={`break-all font-mono ${item.sku_null ? 'text-red-600 font-medium' : 'text-gray-900'}`}>
                                          {item.sku || 'SIN SKU'}
                                          {item.is_pack_component && item.pack_parent && (
                                            <div className="text-xs text-indigo-600 font-normal" title={`Componente de ${item.pack_parent}`}>
                                              📦 {item.pack_parent}
                                            </div>
                                          )}
                                        </div>
                                      </td>
                                      <td className="px-2 py-2 text-xs max-w-24">
                                        <div className="text-blue-600 font-mono break-all">
                                          {item.sku_primario || '-'}
                                        </div>
                                      </td>
                                      <td className="px-2 py-2 text-xs">
                                        <span className="font-medium text-gray-900">
                                          {item.category || '-'}
                                        </span>
                                      </td>
                                      <td className="px-2 py-2 text-xs text-gray-900 max-w-32">
                                        <div className="break-words leading-tight">
                                          {toTitleCase(item.product_name) || '-'}
                                        </div>
                                      </td>
                                      <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 text-right">
                                        {item.quantity}
                                      </td>
                                      <td className="px-2 py-2 whitespace-nowrap text-xs text-right">
                                        <span className="font-semibold text-green-600">
                                          {item.conversion_factor && item.conversion_factor > 1 && (
                                            <span className="text-gray-400 text-xs">(x{item.conversion_factor}) </span>
                                          )}
                                          {item.unidades ? item.unidades.toLocaleString('es-CL') : '-'}
                                        </span>
                                      </td>
                                      <td className="px-2 py-2 whitespace-nowrap text-xs text-right">
                                        <span className="font-semibold text-purple-600">
                                          {item.peso_total ? item.peso_total.toLocaleString('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
                                        </span>
                                      </td>
                                      <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 text-right">
                                        ${item.unit_price ? item.unit_price.toLocaleString('es-CL') : '0'}
                                      </td>
                                      <td className="px-2 py-2 whitespace-nowrap text-xs text-right">
                                        <span className="font-semibold text-blue-600">
                                          ${item.item_subtotal ? item.item_subtotal.toLocaleString('es-CL') : '0'}
                                        </span>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </>
                          ) : (
                            <div className="text-center py-4 text-gray-500">
                              <p>💡 Haz clic en el grupo para cargar los detalles</p>
                            </div>
                          )}
                        </div>
                      )}

                      {/* DETAIL MODE: Show regular table */}
                      {!isAggregatedMode && (
                  <table className="min-w-full divide-y divide-gray-200 text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        {/* Sortable Column Helper */}
                        {[
                          { label: 'Pedido', field: 'order_external_id' },
                          { label: 'Fecha', field: 'order_date' },
                          { label: 'Cliente', field: 'customer_name' },
                          { label: 'Canal', field: 'channel_name' },
                          { label: 'SKU', field: 'sku' },
                          { label: 'Primario', field: 'sku_primario' },
                          { label: 'Familia', field: 'category' },
                          { label: 'Producto', field: 'product_name' },
                          { label: 'Cant.', field: 'quantity' },
                          { label: 'Uds.', field: 'unidades' },
                          { label: 'Peso', field: 'peso_total' },
                          { label: 'Precio', field: 'unit_price' },
                          { label: 'Total', field: 'item_subtotal' },
                        ].map(({ label, field }) => (
                          <th
                            key={field}
                            onClick={() => handleSort(field)}
                            className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-tight cursor-pointer hover:bg-gray-100 select-none"
                          >
                            <div className="flex items-center gap-1">
                              {label}
                              <span className="text-gray-400 text-xs">
                                {sortColumn === field ? (
                                  sortDirection === 'asc' ? '▲' : '▼'
                                ) : (
                                  '⇅'
                                )}
                              </span>
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {groupItems.map((item, idx) => (
                        <tr key={`${item.item_id}-${idx}`} className={`hover:bg-gray-50 ${item.is_pack_component ? 'bg-indigo-50/50' : ''}`}>
                          <td className="px-2 py-2 text-xs text-gray-900">
                            <div className="font-medium">{item.order_external_id}</div>
                            <div className="text-gray-500">{item.order_source}</div>
                          </td>
                          <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-600">
                            {new Date(item.order_date).toLocaleDateString('es-CL')}
                          </td>
                          <td className="px-2 py-2 text-xs max-w-24">
                            <div className={`break-words leading-tight ${item.customer_null ? 'text-red-600 font-medium' : 'text-gray-900'}`}>
                              {toTitleCase(item.customer_name)}
                            </div>
                            <div className="text-gray-500 truncate">{item.customer_rut}</div>
                          </td>
                          <td className="px-2 py-2 text-xs max-w-20">
                            <div className={`break-words ${item.channel_null ? 'text-red-600 font-medium' : 'text-gray-900'}`}>
                              {toTitleCase(item.channel_name)}
                            </div>
                          </td>
                          <td className="px-2 py-2 text-xs max-w-24">
                            <div className={`break-all font-mono ${item.sku_null ? 'text-red-600 font-medium' : 'text-gray-900'}`}>
                              {item.sku || 'SIN SKU'}
                              {item.is_pack_component && item.pack_parent && (
                                <div className="text-xs text-indigo-600 font-normal" title={`Componente de ${item.pack_parent}`}>
                                  📦 {item.pack_parent}
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="px-2 py-2 text-xs max-w-24">
                            <div className="text-blue-600 font-mono break-all">
                              {item.sku_primario || '-'}
                            </div>
                          </td>
                          <td className="px-2 py-2 text-xs">
                            <span className="font-medium text-gray-900">
                              {item.category || '-'}
                            </span>
                          </td>
                          <td className="px-2 py-2 text-xs text-gray-900 max-w-32">
                            <div className="break-words leading-tight">
                              {toTitleCase(item.product_name) || '-'}
                            </div>
                          </td>
                          <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 text-right">
                            {item.quantity}
                          </td>
                          <td className="px-2 py-2 whitespace-nowrap text-xs text-right">
                            <span className="font-semibold text-green-600">
                              {item.conversion_factor && item.conversion_factor > 1 && (
                                <span className="text-gray-400 text-xs">(x{item.conversion_factor}) </span>
                              )}
                              {item.unidades ? item.unidades.toLocaleString('es-CL') : '-'}
                            </span>
                          </td>
                          <td className="px-2 py-2 whitespace-nowrap text-xs text-right">
                            <span className="font-semibold text-purple-600">
                              {item.peso_total ? item.peso_total.toLocaleString('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
                            </span>
                          </td>
                          <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 text-right">
                            ${item.unit_price ? item.unit_price.toLocaleString('es-CL') : '0'}
                          </td>
                          <td className="px-2 py-2 whitespace-nowrap text-xs text-right">
                            <span className="font-semibold text-blue-600">
                              ${item.item_subtotal ? item.item_subtotal.toLocaleString('es-CL') : '0'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                      )}
                    </>
                  )}
                </div>
                );
              })}
            </>
          )}
        </div>

        {/* Pagination */}
        {!loading && data.length > 0 && (
          <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              {/* Left: Records info + Page size selector */}
              <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                <div className="text-sm text-gray-700">
                  Mostrando <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> a{' '}
                  <span className="font-medium">{Math.min(currentPage * pageSize, totalCount)}</span> de{' '}
                  <span className="font-medium">{totalCount}</span> registros
                </div>

                {/* Page size selector */}
                <div className="flex items-center gap-2">
                  <label htmlFor="pageSize" className="text-sm text-gray-600">
                    Mostrar:
                  </label>
                  <select
                    id="pageSize"
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1); // Reset to first page when changing page size
                    }}
                    className="border border-gray-300 rounded-lg px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={100}>100</option>
                    <option value={500}>500</option>
                    <option value={1000}>1000</option>
                  </select>
                  <span className="text-sm text-gray-600">por página</span>
                </div>
              </div>

              {/* Right: Navigation buttons */}
              <div className="flex items-center gap-2">
                {/* Primera (First) */}
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Primera página"
                >
                  Primera
                </button>

                {/* Anterior (Previous) */}
                <button
                  onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Página anterior"
                >
                  Anterior
                </button>

                {/* Page indicator */}
                <div className="flex items-center gap-2 px-4">
                  <span className="text-sm text-gray-700">
                    Página {currentPage} de {totalPages}
                  </span>
                </div>

                {/* Siguiente (Next) */}
                <button
                  onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Página siguiente"
                >
                  Siguiente
                </button>

                {/* Última (Last) */}
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Última página"
                >
                  Última
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
