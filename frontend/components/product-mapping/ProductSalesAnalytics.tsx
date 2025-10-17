'use client';

import React, { useState, useEffect } from 'react';
import {
  getProductOfficialCategory,
  getProductBaseCode,
  getProductBaseName,
  getFormat,
  type Product
} from '@/lib/product-utils';
import { useProducts } from '@/contexts/ProductContext';

interface OrderItem {
  product_sku: string;
  quantity: number;
  unit_price: number;
}

interface Order {
  id: number;
  order_number: string;
  source: string;
  status: string;
  items: OrderItem[];
  created_at: string;
}

interface FamilySales {
  family: string;
  totalRevenue: number;
  totalUnits: number;
  products: {
    name: string;
    revenue: number;
    units: number;
    byFormat: { format: string; units: number; revenue: number }[];
    byChannel: { channel: string; units: number; revenue: number }[];
  }[];
}

export default function ProductSalesAnalytics() {
  const { products, loading: productsLoading, error: productsError } = useProducts();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [familySales, setFamilySales] = useState<FamilySales[]>([]);
  const [selectedFamily, setSelectedFamily] = useState<string | null>(null);
  const [daysFilter, setDaysFilter] = useState<number | null>(null); // null = no data loaded yet
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);

  // Simple cache to avoid re-fetching same data
  const [ordersCache, setOrdersCache] = useState<Map<number, Order[]>>(new Map());

  // Load data when user selects a period
  useEffect(() => {
    if (daysFilter !== null && !productsLoading && products.length > 0) {
      fetchAndProcessSales();
    }
  }, [daysFilter]);

  const getFamilyIcon = (family: string): string => {
    const icons: Record<string, string> = {
      'GRANOLAS': '🥣',
      'BARRAS': '🍫',
      'CRACKERS': '🍘',
      'KEEPERS': '🍬',
      'KRUMS': '🥨',
    };
    return icons[family] || '📦';
  };

  const fetchAndProcessSales = async () => {
    try {
      setLoading(true);
      setHasLoadedOnce(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';

      // Build SKU to product mapping from context (cached products)
      const skuMap = new Map<string, Product>();
      products.forEach(p => skuMap.set(p.sku, p));

      // Check cache first
      let orders: Order[];
      if (ordersCache.has(daysFilter!)) {
        console.log(`Using cached orders for ${daysFilter} days`);
        orders = ordersCache.get(daysFilter!)!;
      } else {
        // Calculate date filter (últimos N días)
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - (daysFilter || 30));
        const startDateStr = startDate.toISOString().split('T')[0]; // YYYY-MM-DD

        // Dynamic limit based on period to ensure we get all data
        let limit = 100; // Default for 7 days
        if (daysFilter! >= 365) {
          limit = 2000; // Full year needs more data
        } else if (daysFilter! >= 90) {
          limit = 1100; // 90 days needs ~1000+ orders
        } else if (daysFilter! >= 30) {
          limit = 300; // 30 days needs ~250 orders
        }

        console.log(`Fetching orders from ${startDateStr} (${daysFilter} days) with limit=${limit}`);

        // Fetch orders with CORRECT parameter: from_date (not created_after)
        const ordersResponse = await fetch(
          `${apiUrl}/api/v1/orders/?limit=${limit}&from_date=${startDateStr}`
        );
        if (!ordersResponse.ok) {
          throw new Error('Error al cargar órdenes');
        }
        const ordersData = await ordersResponse.json();
        orders = ordersData.data;

        console.log(`Fetched ${orders.length} orders from API (total available: ${ordersData.total})`);

        // Cache the results
        setOrdersCache(prev => new Map(prev).set(daysFilter!, orders));
      }

      // Aggregate sales by base product code (from official catalog)
      const salesByBase = new Map<string, {
        baseCode: string;
        baseName: string;
        family: string;
        totalUnits: number;
        totalRevenue: number;
        byFormat: Map<string, { units: number; revenue: number }>;
        byChannel: Map<string, { units: number; revenue: number }>;
      }>();

      orders.forEach(order => {
        if (order.items) {
          order.items.forEach(item => {
            const product = skuMap.get(item.product_sku);
            if (!product) return; // Skip if product not found

            const baseCode = getProductBaseCode(product);
            const baseName = getProductBaseName(product);
            const format = getFormat(product.name);
            const channel = product.source || 'unknown';
            const family = getProductOfficialCategory(product);

            if (!salesByBase.has(baseCode)) {
              salesByBase.set(baseCode, {
                baseCode: baseCode,
                baseName: baseName,
                family: family,
                totalUnits: 0,
                totalRevenue: 0,
                byFormat: new Map(),
                byChannel: new Map(),
              });
            }

            const baseData = salesByBase.get(baseCode)!;
            baseData.totalUnits += item.quantity;
            baseData.totalRevenue += item.quantity * item.unit_price;

            // By format
            if (!baseData.byFormat.has(format)) {
              baseData.byFormat.set(format, { units: 0, revenue: 0 });
            }
            const formatData = baseData.byFormat.get(format)!;
            formatData.units += item.quantity;
            formatData.revenue += item.quantity * item.unit_price;

            // By channel
            if (!baseData.byChannel.has(channel)) {
              baseData.byChannel.set(channel, { units: 0, revenue: 0 });
            }
            const channelData = baseData.byChannel.get(channel)!;
            channelData.units += item.quantity;
            channelData.revenue += item.quantity * item.unit_price;
          });
        }
      });

      // Group by family
      const familyMap = new Map<string, FamilySales>();

      salesByBase.forEach((baseData) => {
        if (!familyMap.has(baseData.family)) {
          familyMap.set(baseData.family, {
            family: baseData.family,
            totalRevenue: 0,
            totalUnits: 0,
            products: [],
          });
        }

        const familyData = familyMap.get(baseData.family)!;
        familyData.totalRevenue += baseData.totalRevenue;
        familyData.totalUnits += baseData.totalUnits;

        familyData.products.push({
          name: baseData.baseName,
          revenue: baseData.totalRevenue,
          units: baseData.totalUnits,
          byFormat: Array.from(baseData.byFormat.entries()).map(([format, data]) => ({
            format,
            units: data.units,
            revenue: data.revenue,
          })),
          byChannel: Array.from(baseData.byChannel.entries()).map(([channel, data]) => ({
            channel,
            units: data.units,
            revenue: data.revenue,
          })),
        });
      });

      // Sort families and products
      const familiesArray = Array.from(familyMap.values())
        .map(family => ({
          ...family,
          products: family.products.sort((a, b) => b.revenue - a.revenue),
        }))
        .sort((a, b) => b.totalRevenue - a.totalRevenue);

      setFamilySales(familiesArray);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const getFormatColor = (format: string) => {
    if (format === '1un') return 'bg-blue-100 text-blue-800';
    if (format === '5un') return 'bg-green-100 text-green-800';
    if (format.includes('16')) return 'bg-purple-100 text-purple-800';
    return 'bg-gray-100 text-gray-800';
  };

  const getChannelColor = (channel: string) => {
    if (channel === 'shopify') return 'bg-green-100 text-green-800';
    if (channel === 'mercadolibre') return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  // Show errors if any
  if (productsError || error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">❌ {productsError || error}</p>
      </div>
    );
  }

  // If products are still loading, show spinner
  if (productsLoading) {
    return (
      <div className="flex justify-center items-center p-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <p className="ml-4 text-gray-600">Cargando productos...</p>
      </div>
    );
  }

  const totalRevenue = familySales.reduce((sum, f) => sum + f.totalRevenue, 0);
  const totalUnits = familySales.reduce((sum, f) => sum + f.totalUnits, 0);

  return (
    <div className="space-y-6">
      {/* Period Filter - ALWAYS VISIBLE */}
      <div className="bg-white border border-gray-300 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">Período de Análisis</h3>
            <p className="text-sm text-gray-600">Selecciona el rango de fechas para analizar las ventas</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setDaysFilter(7)}
              disabled={loading}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                daysFilter === 7
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              Últimos 7 días
            </button>
            <button
              onClick={() => setDaysFilter(30)}
              disabled={loading}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                daysFilter === 30
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              Últimos 30 días
            </button>
            <button
              onClick={() => setDaysFilter(90)}
              disabled={loading}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                daysFilter === 90
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              Últimos 90 días
            </button>
            <button
              onClick={() => setDaysFilter(365)}
              disabled={loading}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                daysFilter === 365
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              Último año
            </button>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center items-center p-12 bg-white border border-gray-300 rounded-lg">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="ml-4 text-gray-600">Cargando datos de ventas...</p>
        </div>
      )}

      {/* Initial State - No period selected */}
      {!loading && !hasLoadedOnce && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-12 text-center">
          <div className="text-5xl mb-4">📊</div>
          <h3 className="text-xl font-semibold text-blue-900 mb-2">Selecciona un Período</h3>
          <p className="text-blue-700">
            Elige uno de los períodos arriba para ver el análisis de ventas
          </p>
        </div>
      )}

      {/* No Data State */}
      {!loading && hasLoadedOnce && familySales.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
          <p className="text-yellow-700">⚠️ No hay datos de ventas en este período</p>
        </div>
      )}

      {/* Data Display - Only show when we have data */}
      {!loading && familySales.length > 0 && (
        <>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-r from-blue-50 to-blue-100 border border-blue-200 rounded-lg p-6">
          <div className="text-sm text-blue-600 mb-1">Ingresos Totales</div>
          <div className="text-3xl font-bold text-blue-900">{formatCurrency(totalRevenue)}</div>
        </div>
        <div className="bg-gradient-to-r from-green-50 to-green-100 border border-green-200 rounded-lg p-6">
          <div className="text-sm text-green-600 mb-1">Unidades Vendidas</div>
          <div className="text-3xl font-bold text-green-900">{totalUnits.toLocaleString()}</div>
        </div>
        <div className="bg-gradient-to-r from-purple-50 to-purple-100 border border-purple-200 rounded-lg p-6">
          <div className="text-sm text-purple-600 mb-1">Familias Activas</div>
          <div className="text-3xl font-bold text-purple-900">{familySales.length}</div>
        </div>
      </div>

      {/* Family Sales */}
      {familySales.map((family, idx) => {
        const isExpanded = selectedFamily === family.family;
        const revenuePercentage = (family.totalRevenue / totalRevenue) * 100;

        return (
          <div key={idx} className="bg-white border-2 border-gray-300 rounded-xl overflow-hidden shadow-md">
            {/* Family Header */}
            <div
              className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white p-6 cursor-pointer hover:from-indigo-600 hover:to-purple-600 transition-all"
              onClick={() => setSelectedFamily(isExpanded ? null : family.family)}
            >
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-4">
                  <span className="text-5xl">{getFamilyIcon(family.family)}</span>
                  <div>
                    <h2 className="text-2xl font-bold">{family.family}</h2>
                    <p className="text-sm opacity-90 mt-1">
                      {family.products.length} producto{family.products.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold">{formatCurrency(family.totalRevenue)}</div>
                  <div className="text-sm opacity-90">{revenuePercentage.toFixed(1)}% del total</div>
                  <div className="text-sm opacity-75 mt-1">{family.totalUnits.toLocaleString()} unidades</div>
                  <div className="text-xs opacity-75 mt-2">
                    {isExpanded ? '▲ Ocultar' : '▼ Ver productos'}
                  </div>
                </div>
              </div>
            </div>

            {/* Products within Family */}
            {isExpanded && (
              <div className="p-4 space-y-3 bg-gray-50">
                {family.products.map((product, pidx) => {
                  const productRevenuePercentage = (product.revenue / family.totalRevenue) * 100;

                  return (
                    <div key={pidx} className="bg-white border border-gray-300 rounded-lg p-4 shadow-sm">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="font-semibold text-gray-900 text-lg">{product.name}</h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {product.units.toLocaleString()} unidades • {formatCurrency(product.revenue)}
                          </p>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-indigo-600">
                            {productRevenuePercentage.toFixed(1)}%
                          </div>
                          <div className="text-xs text-gray-500">de la familia</div>
                        </div>
                      </div>

                      {/* Revenue Bar */}
                      <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                        <div
                          className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2 rounded-full"
                          style={{ width: `${productRevenuePercentage}%` }}
                        />
                      </div>

                      <div className="grid md:grid-cols-2 gap-4">
                        {/* By Format */}
                        <div>
                          <h4 className="font-medium text-gray-700 mb-2 text-sm">📦 Por Formato</h4>
                          <div className="space-y-2">
                            {product.byFormat
                              .sort((a, b) => b.revenue - a.revenue)
                              .map((format, fidx) => {
                                const formatPercentage = (format.revenue / product.revenue) * 100;
                                return (
                                  <div key={fidx} className="flex items-center justify-between">
                                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getFormatColor(format.format)}`}>
                                      {format.format}
                                    </span>
                                    <div className="flex-1 mx-3 bg-gray-200 rounded-full h-2">
                                      <div
                                        className="bg-blue-500 h-2 rounded-full"
                                        style={{ width: `${formatPercentage}%` }}
                                      />
                                    </div>
                                    <div className="text-xs text-gray-600 w-24 text-right">
                                      {format.units} un • {formatCurrency(format.revenue)}
                                    </div>
                                  </div>
                                );
                              })}
                          </div>
                        </div>

                        {/* By Channel */}
                        <div>
                          <h4 className="font-medium text-gray-700 mb-2 text-sm">🔄 Por Canal</h4>
                          <div className="space-y-2">
                            {product.byChannel
                              .sort((a, b) => b.revenue - a.revenue)
                              .map((channel, cidx) => {
                                const channelPercentage = (channel.revenue / product.revenue) * 100;
                                return (
                                  <div key={cidx} className="flex items-center justify-between">
                                    <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${getChannelColor(channel.channel)}`}>
                                      {channel.channel}
                                    </span>
                                    <div className="flex-1 mx-3 bg-gray-200 rounded-full h-2">
                                      <div
                                        className="bg-green-500 h-2 rounded-full"
                                        style={{ width: `${channelPercentage}%` }}
                                      />
                                    </div>
                                    <div className="text-xs text-gray-600 w-24 text-right">
                                      {channel.units} un • {formatCurrency(channel.revenue)}
                                    </div>
                                  </div>
                                );
                              })}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
        </>
      )}
    </div>
  );
}
