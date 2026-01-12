'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Navigation from '@/components/Navigation';
import { ProductProvider, useProducts } from '@/contexts/ProductContext';
import SalesLineChart from '@/components/charts/SalesLineChart';

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

interface OrderItem {
  product_sku: string;
  quantity: number;
  unit_price: number;
}

interface Order {
  id: number;
  order_number: string;
  source: string;
  channel_name: string;
  status: string;
  items: OrderItem[];
  created_at: string;
}

interface FilterState {
  families: string[];
  sources: string[];
  channels: string[];
  formats: string[];
  timeRange: number;
}

interface AggregatedMetric {
  name: string;
  revenue: number;
  units: number;
  orders: number;
}

interface KPIMetrics {
  totalRevenue: number;
  totalUnits: number;
  totalOrders: number;
  avgTicket: number;
}

interface TimeSeriesData {
  period: string;
  total_revenue: number;
  shopify_revenue: number;
  mercadolibre_revenue: number;
  relbase_revenue: number;
  lokal_revenue: number;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

function ConsolidatedAnalyticsContent() {
  const { products, loading: productsLoading } = useProducts();

  // State
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState<Order[]>([]);
  const [catalog, setCatalog] = useState<Map<string, any>>(new Map());
  const [officialChannels, setOfficialChannels] = useState<string[]>([]);
  const [filters, setFilters] = useState<FilterState>({
    families: [],
    sources: [],
    channels: [],
    formats: [],
    timeRange: 30,
  });

  // Load official Relbase channels on mount
  useEffect(() => {
    const loadChannels = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
        const response = await fetch(`${apiUrl}/api/v1/channels`);
        if (response.ok) {
          const result = await response.json();
          // Channels with no 2025 data (exclude from filters)
          const excludedChannels = ['EXPORTACIÓN', 'HORECA', 'MARKETPLACES'];

          // Filter only Relbase channels with 2025 data
          const relbaseChannels = result.data
            .filter((ch: any) =>
              ch.code?.startsWith('RB_') &&
              ch.is_active &&
              !excludedChannels.includes(ch.name)
            )
            .map((ch: any) => ch.name)
            .sort();
          // "Sin Canal Asignado" is already in the DB with code RB_SIN_CANAL
          setOfficialChannels(relbaseChannels);
        }
      } catch (error) {
        console.error('Error loading channels:', error);
      }
    };
    loadChannels();
  }, []);

  // Load catalog on mount
  useEffect(() => {
    const loadCatalog = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
        const response = await fetch(`${apiUrl}/api/v1/product-mapping/catalog`);
        if (response.ok) {
          const data = await response.json();
          const catalogMap = new Map();
          data.data.forEach((product: any) => {
            catalogMap.set(product.sku, product);
          });
          setCatalog(catalogMap);
        }
      } catch (err) {
        console.error('Error loading catalog:', err);
      }
    };
    loadCatalog();
  }, []);

  // Fetch orders when timeRange changes
  useEffect(() => {
    if (catalog.size > 0) {
      fetchOrders();
    }
  }, [filters.timeRange, catalog]);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';

      const startDate = new Date();
      startDate.setDate(startDate.getDate() - filters.timeRange);
      const startDateStr = startDate.toISOString().split('T')[0];

      let limit = 500;
      if (filters.timeRange >= 365) limit = 8000;
      else if (filters.timeRange >= 90) limit = 3000;
      else if (filters.timeRange >= 30) limit = 1500;

      const response = await fetch(
        `${apiUrl}/api/v1/orders/?limit=${limit}&from_date=${startDateStr}`
      );

      if (!response.ok) throw new Error('Error al cargar órdenes');

      const data = await response.json();
      setOrders(data.data);
    } catch (err) {
      console.error('Error fetching orders:', err);
    } finally {
      setLoading(false);
    }
  };

  // Helper functions
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const setTimeRange = (days: number) => {
    setFilters(prev => ({ ...prev, timeRange: days }));
  };

  const removeFilter = (filterType: 'families' | 'sources' | 'channels' | 'formats', value: string) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: prev[filterType].filter(v => v !== value)
    }));
  };

  const clearAllFilters = () => {
    setFilters({
      families: [],
      sources: [],
      channels: [],
      formats: [],
      timeRange: filters.timeRange,
    });
  };

  const hasActiveFilters = filters.families.length > 0 || filters.sources.length > 0 ||
                           filters.channels.length > 0 || filters.formats.length > 0;

  // Extract available filter options from data
  const filterOptions = useMemo(() => {
    if (orders.length === 0 || catalog.size === 0) {
      return {
        families: [],
        sources: [],
        channels: officialChannels, // Use official Relbase channels even if no data
        formats: [],
      };
    }

    const familiesSet = new Set<string>();
    const sourcesSet = new Set<string>();
    const formatsSet = new Set<string>();

    orders.forEach(order => {
      // Add source
      if (order.source) sourcesSet.add(order.source);

      // Extract families and formats from order items
      order.items?.forEach(item => {
        const product = catalog.get(item.product_sku);
        if (product) {
          if (product.category) familiesSet.add(product.category);
          if (product.package_type) formatsSet.add(product.package_type);
        }
      });
    });

    return {
      families: Array.from(familiesSet).sort(),
      sources: Array.from(sourcesSet).sort(),
      channels: officialChannels, // Use official Relbase channels instead of extracting from data
      formats: Array.from(formatsSet).sort(),
    };
  }, [orders, catalog, officialChannels]);

  // Filter orders based on active filters
  const filteredOrders = useMemo(() => {
    if (!hasActiveFilters) return orders;

    return orders.filter(order => {
      // Filter by source
      if (filters.sources.length > 0 && !filters.sources.includes(order.source)) {
        return false;
      }

      // Filter by channel
      if (filters.channels.length > 0 && !filters.channels.includes(order.channel_name)) {
        return false;
      }

      // Filter by family and format (need to check order items)
      if (filters.families.length > 0 || filters.formats.length > 0) {
        const hasMatchingItem = order.items?.some(item => {
          const product = catalog.get(item.product_sku);
          if (!product) return false;

          const familyMatch = filters.families.length === 0 ||
                             (product.category && filters.families.includes(product.category));
          const formatMatch = filters.formats.length === 0 ||
                             (product.package_type && filters.formats.includes(product.package_type));

          return familyMatch && formatMatch;
        });

        if (!hasMatchingItem) return false;
      }

      return true;
    });
  }, [orders, filters, catalog, hasActiveFilters]);

  // Aggregate data from filtered orders
  const aggregatedData = useMemo(() => {
    const byFamily = new Map<string, AggregatedMetric>();
    const bySource = new Map<string, AggregatedMetric>();
    const byChannel = new Map<string, AggregatedMetric>();
    const byFormat = new Map<string, AggregatedMetric>();
    const byProduct = new Map<string, {
      sku: string;
      name: string;
      revenue: number;
      units: number;
      family: string;
      sources: Set<string>;
      channels: Set<string>;
    }>();
    const byDate = new Map<string, { total_revenue: number; shopify_revenue: number; mercadolibre_revenue: number; relbase_revenue: number; lokal_revenue: number; units: number; orders: number }>();

    let totalRevenue = 0;
    let totalUnits = 0;
    const orderSet = new Set<number>();

    filteredOrders.forEach(order => {
      orderSet.add(order.id);

      // Aggregate by source
      if (order.source) {
        const existing = bySource.get(order.source) || { name: order.source, revenue: 0, units: 0, orders: 0 };
        bySource.set(order.source, existing);
      }

      // Aggregate by channel
      if (order.channel_name) {
        const existing = byChannel.get(order.channel_name) || { name: order.channel_name, revenue: 0, units: 0, orders: 0 };
        byChannel.set(order.channel_name, existing);
      }

      // Aggregate by day or month depending on time range
      const orderDate = order.created_at.split('T')[0]; // YYYY-MM-DD
      // For periods up to 90 days, aggregate by day; for longer periods, aggregate by month
      const timePeriod = filters.timeRange <= 90 ? orderDate : orderDate.substring(0, 7);
      const periodData = byDate.get(timePeriod) || {
        total_revenue: 0,
        shopify_revenue: 0,
        mercadolibre_revenue: 0,
        relbase_revenue: 0,
        lokal_revenue: 0,
        units: 0,
        orders: 0
      };
      periodData.orders += 1;
      byDate.set(timePeriod, periodData);

      // Process order items
      order.items?.forEach(item => {
        const product = catalog.get(item.product_sku);
        const itemRevenue = item.quantity * item.unit_price;
        const itemUnits = item.quantity;

        totalRevenue += itemRevenue;
        totalUnits += itemUnits;

        // Update source metrics
        if (order.source) {
          const sourceMetric = bySource.get(order.source)!;
          sourceMetric.revenue += itemRevenue;
          sourceMetric.units += itemUnits;
          sourceMetric.orders = orderSet.size;
        }

        // Update channel metrics
        if (order.channel_name) {
          const channelMetric = byChannel.get(order.channel_name)!;
          channelMetric.revenue += itemRevenue;
          channelMetric.units += itemUnits;
          channelMetric.orders = orderSet.size;
        }

        // Update period metrics
        const periodMetric = byDate.get(timePeriod)!;
        periodMetric.total_revenue += itemRevenue;
        periodMetric.units += itemUnits;

        // Update revenue by source for the period
        const source = order.source?.toLowerCase();
        if (source === 'shopify') {
          periodMetric.shopify_revenue += itemRevenue;
        } else if (source === 'mercadolibre') {
          periodMetric.mercadolibre_revenue += itemRevenue;
        } else if (source === 'relbase') {
          periodMetric.relbase_revenue += itemRevenue;
        } else if (source === 'lokal') {
          periodMetric.lokal_revenue += itemRevenue;
        }

        if (product) {
          // Aggregate by family
          if (product.category) {
            const familyMetric = byFamily.get(product.category) || { name: product.category, revenue: 0, units: 0, orders: 0 };
            familyMetric.revenue += itemRevenue;
            familyMetric.units += itemUnits;
            familyMetric.orders = orderSet.size;
            byFamily.set(product.category, familyMetric);
          }

          // Aggregate by format
          if (product.package_type) {
            const formatMetric = byFormat.get(product.package_type) || { name: product.package_type, revenue: 0, units: 0, orders: 0 };
            formatMetric.revenue += itemRevenue;
            formatMetric.units += itemUnits;
            formatMetric.orders = orderSet.size;
            byFormat.set(product.package_type, formatMetric);
          }

          // Aggregate by product
          const productMetric = byProduct.get(item.product_sku) || {
            sku: item.product_sku,
            name: product.product_name || item.product_sku,
            revenue: 0,
            units: 0,
            family: product.category || 'Sin Categoría',
            sources: new Set<string>(),
            channels: new Set<string>(),
          };
          productMetric.revenue += itemRevenue;
          productMetric.units += itemUnits;

          // Track which sources and channels this product is sold through
          if (order.source) productMetric.sources.add(order.source);
          if (order.channel_name) productMetric.channels.add(order.channel_name);

          byProduct.set(item.product_sku, productMetric);
        }
      });
    });

    // Convert maps to sorted arrays
    const topFamilies = Array.from(byFamily.values())
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 10);

    const topSources = Array.from(bySource.values())
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 10);

    const topChannels = Array.from(byChannel.values())
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 10);

    const topFormats = Array.from(byFormat.values())
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 10);

    const topProducts = Array.from(byProduct.values())
      .map(product => ({
        ...product,
        sources: Array.from(product.sources),
        channels: Array.from(product.channels),
      }))
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 20);

    // Convert period map to sorted time series
    const timeSeries = Array.from(byDate.entries())
      .map(([period, data]) => {
        // Format period based on whether it's a day (YYYY-MM-DD) or month (YYYY-MM)
        const formattedPeriod = period.length === 10
          ? period  // Daily format: 2025-09-15
          : period; // Monthly format: 2025-09

        return {
          period: formattedPeriod,
          total_revenue: data.total_revenue,
          shopify_revenue: data.shopify_revenue,
          mercadolibre_revenue: data.mercadolibre_revenue,
          relbase_revenue: data.relbase_revenue,
          lokal_revenue: data.lokal_revenue,
        };
      })
      .sort((a, b) => a.period.localeCompare(b.period));

    return {
      kpis: {
        totalRevenue,
        totalUnits,
        totalOrders: orderSet.size,
        avgTicket: orderSet.size > 0 ? totalRevenue / orderSet.size : 0,
      },
      topFamilies,
      topSources,
      topChannels,
      topFormats,
      topProducts,
      timeSeries,
    };
  }, [filteredOrders, catalog]);

  // RENDER
  if (productsLoading || loading) {
    return (
      <>
        <Navigation />
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Cargando análisis integral...</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              📊 Análisis Integral de Ventas
            </h1>
            <p className="text-lg text-gray-600">
              Vista consolidada con filtros multi-dimensionales
            </p>
          </div>

          {/* Time Range Filter */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Período de Tiempo</h3>
            <div className="flex flex-wrap gap-2">
              {[
                { value: 7, label: 'Últimos 7 días' },
                { value: 30, label: 'Últimos 30 días' },
                { value: 90, label: 'Últimos 90 días' },
                { value: 365, label: 'Último año' },
              ].map(option => (
                <button
                  key={option.value}
                  onClick={() => setTimeRange(option.value)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    filters.timeRange === option.value
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Multi-Dimensional Filters */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Filtros Multi-Dimensionales
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Family Filter */}
              {filterOptions.families.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-2">
                    Familia de Producto
                  </label>
                  <select
                    multiple
                    value={filters.families}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, option => option.value);
                      setFilters(prev => ({ ...prev, families: selected }));
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    style={{ height: '120px' }}
                  >
                    {filterOptions.families.map(family => (
                      <option key={family} value={family}>
                        {family}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-gray-500">Hold Ctrl/Cmd to select multiple</p>
                </div>
              )}

              {/* Source Filter */}
              {filterOptions.sources.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-2">
                    Fuente de Venta
                  </label>
                  <select
                    multiple
                    value={filters.sources}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, option => option.value);
                      setFilters(prev => ({ ...prev, sources: selected }));
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    style={{ height: '120px' }}
                  >
                    {filterOptions.sources.map(source => (
                      <option key={source} value={source}>
                        {source}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-gray-500">Hold Ctrl/Cmd to select multiple</p>
                </div>
              )}

              {/* Channel Filter */}
              {filterOptions.channels.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-2">
                    Canal de Negocio
                  </label>
                  <select
                    multiple
                    value={filters.channels}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, option => option.value);
                      setFilters(prev => ({ ...prev, channels: selected }));
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    style={{ height: '120px' }}
                  >
                    {filterOptions.channels.map(channel => (
                      <option key={channel} value={channel}>
                        {channel}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-gray-500">Hold Ctrl/Cmd to select multiple</p>
                </div>
              )}

              {/* Format Filter */}
              {filterOptions.formats.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-2">
                    Formato de Producto
                  </label>
                  <select
                    multiple
                    value={filters.formats}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, option => option.value);
                      setFilters(prev => ({ ...prev, formats: selected }));
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                    style={{ height: '120px' }}
                  >
                    {filterOptions.formats.map(format => (
                      <option key={format} value={format}>
                        {format}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-gray-500">Hold Ctrl/Cmd to select multiple</p>
                </div>
              )}
            </div>
          </div>

          {/* Active Filters Bar */}
          {hasActiveFilters && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 mb-6">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-indigo-900">
                    Filtros Activos:
                  </span>
                  {filters.families.map(family => (
                    <span
                      key={family}
                      className="inline-flex items-center gap-1.5 px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full"
                    >
                      <span>🏷️ {family}</span>
                      <button
                        onClick={() => removeFilter('families', family)}
                        className="hover:bg-green-200 rounded-full p-0.5"
                      >
                        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </span>
                  ))}
                  {filters.sources.map(source => (
                    <span
                      key={source}
                      className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full"
                    >
                      <span>🛒 {source}</span>
                      <button
                        onClick={() => removeFilter('sources', source)}
                        className="hover:bg-blue-200 rounded-full p-0.5"
                      >
                        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </span>
                  ))}
                  {filters.channels.map(channel => (
                    <span
                      key={channel}
                      className="inline-flex items-center gap-1.5 px-3 py-1 bg-purple-100 text-purple-800 text-sm font-medium rounded-full"
                    >
                      <span>📊 {channel}</span>
                      <button
                        onClick={() => removeFilter('channels', channel)}
                        className="hover:bg-purple-200 rounded-full p-0.5"
                      >
                        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </span>
                  ))}
                  {filters.formats.map(format => (
                    <span
                      key={format}
                      className="inline-flex items-center gap-1.5 px-3 py-1 bg-orange-100 text-orange-800 text-sm font-medium rounded-full"
                    >
                      <span>📦 {format}</span>
                      <button
                        onClick={() => removeFilter('formats', format)}
                        className="hover:bg-orange-200 rounded-full p-0.5"
                      >
                        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </span>
                  ))}
                </div>
                <button
                  onClick={clearAllFilters}
                  className="px-4 py-2 bg-white border border-indigo-300 text-indigo-700 text-sm font-medium rounded-lg hover:bg-indigo-50 transition-colors"
                >
                  Limpiar Todos
                </button>
              </div>
            </div>
          )}

          {/* Results Summary */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">
                  Mostrando <span className="font-semibold text-gray-900">{filteredOrders.length}</span> de{' '}
                  <span className="font-semibold text-gray-900">{orders.length}</span> órdenes
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Período: Últimos {filters.timeRange} días
                </p>
              </div>
              {hasActiveFilters && (
                <div className="flex items-center gap-2 text-sm">
                  <svg className="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.293.707l-2 2A1 1 0 018 17v-5.586L3.293 6.707A1 1 0 013 6V3z" clipRule="evenodd" />
                  </svg>
                  <span className="text-indigo-700 font-medium">
                    {filters.families.length + filters.sources.length + filters.channels.length + filters.formats.length} filtro(s) aplicado(s)
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Empty State */}
          {filteredOrders.length === 0 && (
            <div className="bg-white rounded-lg shadow-sm p-12 text-center">
              <svg className="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No hay datos que coincidan con los filtros</h3>
              <p className="text-gray-600 mb-6">
                Intenta ajustar o remover algunos filtros para ver resultados.
              </p>
              {hasActiveFilters && (
                <button
                  onClick={clearAllFilters}
                  className="px-6 py-3 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  Limpiar Todos los Filtros
                </button>
              )}
            </div>
          )}

          {/* KPI Cards */}
          {filteredOrders.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            {/* Total Revenue */}
            <div className="bg-white rounded-lg shadow-sm p-6 border-l-4 border-green-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Ingresos Totales</p>
                  <p className="text-2xl font-bold text-gray-900 mt-2">
                    {formatCurrency(aggregatedData.kpis.totalRevenue)}
                  </p>
                </div>
                <div className="p-3 bg-green-100 rounded-full">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Total Units */}
            <div className="bg-white rounded-lg shadow-sm p-6 border-l-4 border-blue-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Unidades Vendidas</p>
                  <p className="text-2xl font-bold text-gray-900 mt-2">
                    {aggregatedData.kpis.totalUnits.toLocaleString('es-CL')}
                  </p>
                </div>
                <div className="p-3 bg-blue-100 rounded-full">
                  <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Total Orders */}
            <div className="bg-white rounded-lg shadow-sm p-6 border-l-4 border-purple-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Órdenes Totales</p>
                  <p className="text-2xl font-bold text-gray-900 mt-2">
                    {aggregatedData.kpis.totalOrders.toLocaleString('es-CL')}
                  </p>
                </div>
                <div className="p-3 bg-purple-100 rounded-full">
                  <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Avg Ticket */}
            <div className="bg-white rounded-lg shadow-sm p-6 border-l-4 border-orange-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Ticket Promedio</p>
                  <p className="text-2xl font-bold text-gray-900 mt-2">
                    {formatCurrency(aggregatedData.kpis.avgTicket)}
                  </p>
                </div>
                <div className="p-3 bg-orange-100 rounded-full">
                  <svg className="w-8 h-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
          )}

          {/* Time Series Chart */}
          {filteredOrders.length > 0 && aggregatedData.timeSeries.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 Ventas en el Tiempo</h3>
              <SalesLineChart data={aggregatedData.timeSeries} />
            </div>
          )}

          {/* Top Rankings Grid */}
          {filteredOrders.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Top Families */}
            {aggregatedData.topFamilies.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">🏷️ Top Familias</h3>
                <div className="space-y-3">
                  {aggregatedData.topFamilies.map((family, idx) => {
                    const maxRevenue = aggregatedData.topFamilies[0].revenue;
                    const percentage = (family.revenue / maxRevenue) * 100;
                    return (
                      <div key={family.name}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{family.name}</span>
                          <span className="text-sm font-semibold text-gray-900">{formatCurrency(family.revenue)}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full transition-all"
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{family.units.toLocaleString('es-CL')} unidades</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Top Sources */}
            {aggregatedData.topSources.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">🛒 Top Fuentes</h3>
                <div className="space-y-3">
                  {aggregatedData.topSources.map((source, idx) => {
                    const maxRevenue = aggregatedData.topSources[0].revenue;
                    const percentage = (source.revenue / maxRevenue) * 100;
                    return (
                      <div key={source.name}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{source.name}</span>
                          <span className="text-sm font-semibold text-gray-900">{formatCurrency(source.revenue)}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{source.units.toLocaleString('es-CL')} unidades</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Top Channels */}
            {aggregatedData.topChannels.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Top Canales</h3>
                <div className="space-y-3">
                  {aggregatedData.topChannels.map((channel, idx) => {
                    const maxRevenue = aggregatedData.topChannels[0].revenue;
                    const percentage = (channel.revenue / maxRevenue) * 100;
                    return (
                      <div key={channel.name}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{channel.name}</span>
                          <span className="text-sm font-semibold text-gray-900">{formatCurrency(channel.revenue)}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-purple-600 h-2 rounded-full transition-all"
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{channel.units.toLocaleString('es-CL')} unidades</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Top Formats */}
            {aggregatedData.topFormats.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">📦 Top Formatos</h3>
                <div className="space-y-3">
                  {aggregatedData.topFormats.map((format, idx) => {
                    const maxRevenue = aggregatedData.topFormats[0].revenue;
                    const percentage = (format.revenue / maxRevenue) * 100;
                    return (
                      <div key={format.name}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{format.name}</span>
                          <span className="text-sm font-semibold text-gray-900">{formatCurrency(format.revenue)}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-orange-600 h-2 rounded-full transition-all"
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{format.units.toLocaleString('es-CL')} unidades</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
          )}

          {/* Top Products Table */}
          {filteredOrders.length > 0 && aggregatedData.topProducts.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm overflow-hidden">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">🏆 Top 20 Productos</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rank</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SKU</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Producto</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Familia</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fuentes</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Canales</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Ingresos</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Unidades</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">% del Total</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {aggregatedData.topProducts.map((product, idx) => {
                      const percentage = (product.revenue / aggregatedData.kpis.totalRevenue) * 100;
                      return (
                        <tr key={product.sku} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                              idx === 0 ? 'bg-yellow-100 text-yellow-800' :
                              idx === 1 ? 'bg-gray-100 text-gray-800' :
                              idx === 2 ? 'bg-orange-100 text-orange-800' :
                              'bg-gray-50 text-gray-600'
                            }`}>
                              {idx + 1}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{product.sku}</td>
                          <td className="px-6 py-4 text-sm text-gray-700 max-w-xs truncate">{product.name}</td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                              {product.family}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex flex-wrap gap-1">
                              {product.sources.map((source: string) => (
                                <span key={source} className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                                  {source}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex flex-wrap gap-1">
                              {product.channels.map((channel: string) => (
                                <span key={channel} className="px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 rounded">
                                  {channel}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 text-right">
                            {formatCurrency(product.revenue)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                            {product.units.toLocaleString('es-CL')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                            {percentage.toFixed(1)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function ConsolidatedAnalyticsPage() {
  return (
    <ProductProvider>
      <ConsolidatedAnalyticsContent />
    </ProductProvider>
  );
}
