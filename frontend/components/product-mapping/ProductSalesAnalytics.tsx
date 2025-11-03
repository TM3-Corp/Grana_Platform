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
  channel_name: string;
  status: string;
  items: OrderItem[];
  created_at: string;
}

interface SKUSales {
  sku: string;
  product_name: string;
  package_type: string;
  units_per_display: number;
  totalRevenue: number;
  totalUnits: number;
  byChannel: { channel: string; units: number; revenue: number }[];
  // Master box metrics (calculated from units / units_per_display)
  totalMasterBoxes: number;
}

interface SubfamilySales {
  base_code: string;
  product_name: string;
  totalRevenue: number;
  totalUnits: number;
  totalMasterBoxes: number;
  skus: SKUSales[];
}

interface FamilySales {
  family: string;
  totalRevenue: number;
  totalUnits: number;
  totalMasterBoxes: number;
  subfamilies: SubfamilySales[];
}

type AnalysisView = 'family' | 'source' | 'channel';

interface ChannelSales {
  channel: string;
  totalRevenue: number;
  totalUnits: number;
  totalOrders: number;
  avgTicket: number;
  avgUnitsPerOrder: number;
  byCategory: { category: string; revenue: number; units: number; orders: number }[];
  byPackageType: { packageType: string; revenue: number; units: number }[];
  topProducts: { sku: string; name: string; revenue: number; units: number }[];
}

export default function ProductSalesAnalytics() {
  const { products, loading: productsLoading, error: productsError } = useProducts();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [familySales, setFamilySales] = useState<FamilySales[]>([]);
  const [sourceSales, setSourceSales] = useState<ChannelSales[]>([]);
  const [businessChannelSales, setBusinessChannelSales] = useState<ChannelSales[]>([]);
  const [selectedFamily, setSelectedFamily] = useState<string | null>(null);
  const [selectedSubfamily, setSelectedSubfamily] = useState<string | null>(null);
  const [selectedSKU, setSelectedSKU] = useState<string | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [daysFilter, setDaysFilter] = useState<number | null>(null); // null = no data loaded yet
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [analysisView, setAnalysisView] = useState<AnalysisView>('family');

  // Catalog data for SKU metadata
  const [catalog, setCatalog] = useState<Map<string, any>>(new Map());

  // Simple cache to avoid re-fetching same data
  const [ordersCache, setOrdersCache] = useState<Map<number, Order[]>>(new Map());

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

  // Load data when user selects a period
  useEffect(() => {
    if (daysFilter !== null && !productsLoading && products.length > 0 && catalog.size > 0) {
      fetchAndProcessSales();
    }
  }, [daysFilter, catalog]);

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
        // IMPORTANT: Higher limits needed to include ALL channels (LOKAL, Shopify, ML, Relbase)
        // Orders are sorted by date DESC, so we need enough to reach older orders
        let limit = 500; // Default for 7 days (increased to catch all channels)
        if (daysFilter! >= 365) {
          limit = 8000; // Full year - need high limit to include all 7,233 orders
        } else if (daysFilter! >= 90) {
          limit = 3000; // 90 days - need to reach LOKAL (Mar-Oct) and older Shopify/ML orders
        } else if (daysFilter! >= 30) {
          limit = 1500; // 30 days - ensure all channels included despite Relbase dominance
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

      // Aggregate sales by SKU (hierarchical: Category → Subfamily → SKU → Channel)
      const salesBySKU = new Map<string, {
        sku: string;
        catalogData: any;
        totalUnits: number;
        totalRevenue: number;
        byChannel: Map<string, { units: number; revenue: number }>;
      }>();

      orders.forEach(order => {
        if (order.items) {
          order.items.forEach(item => {
            const product = skuMap.get(item.product_sku);
            if (!product) return; // Skip if product not found

            const sku = product.sku;
            const channel = product.source || 'unknown';

            if (!salesBySKU.has(sku)) {
              salesBySKU.set(sku, {
                sku: sku,
                catalogData: catalog.get(sku),
                totalUnits: 0,
                totalRevenue: 0,
                byChannel: new Map(),
              });
            }

            const skuData = salesBySKU.get(sku)!;
            skuData.totalUnits += item.quantity;
            skuData.totalRevenue += item.quantity * item.unit_price;

            // By channel
            if (!skuData.byChannel.has(channel)) {
              skuData.byChannel.set(channel, { units: 0, revenue: 0 });
            }
            const channelData = skuData.byChannel.get(channel)!;
            channelData.units += item.quantity;
            channelData.revenue += item.quantity * item.unit_price;
          });
        }
      });

      // Group by base_code (subfamily)
      const subfamilyMap = new Map<string, {
        base_code: string;
        category: string;
        product_name: string;
        totalRevenue: number;
        totalUnits: number;
        totalMasterBoxes: number;
        skus: Map<string, any>;
      }>();

      salesBySKU.forEach((skuData) => {
        const catalogProduct = skuData.catalogData;
        if (!catalogProduct) return; // Skip if not in official catalog

        const base_code = catalogProduct.base_code;
        const category = catalogProduct.category;

        if (!subfamilyMap.has(base_code)) {
          subfamilyMap.set(base_code, {
            base_code: base_code,
            category: category,
            product_name: catalogProduct.product_name.split(' ').slice(0, -1).join(' ') || catalogProduct.product_name, // Remove last word (format)
            totalRevenue: 0,
            totalUnits: 0,
            totalMasterBoxes: 0,
            skus: new Map(),
          });
        }

        const subfamilyData = subfamilyMap.get(base_code)!;
        subfamilyData.totalRevenue += skuData.totalRevenue;
        subfamilyData.totalUnits += skuData.totalUnits;

        // Calculate master boxes for this SKU
        const units_per_display = catalogProduct.units_per_display || 1;
        const masterBoxes = skuData.totalUnits / units_per_display;
        subfamilyData.totalMasterBoxes += masterBoxes;

        // Add SKU to subfamily
        subfamilyData.skus.set(skuData.sku, {
          sku: skuData.sku,
          product_name: catalogProduct.product_name,
          package_type: catalogProduct.package_type,
          units_per_display: units_per_display,
          totalRevenue: skuData.totalRevenue,
          totalUnits: skuData.totalUnits,
          totalMasterBoxes: masterBoxes,
          byChannel: Array.from(skuData.byChannel.entries()).map(([channel, data]) => ({
            channel,
            units: data.units,
            revenue: data.revenue,
          })),
        });
      });

      // Group by category (family)
      const familyMap = new Map<string, FamilySales>();

      subfamilyMap.forEach((subfamilyData) => {
        const category = subfamilyData.category;

        if (!familyMap.has(category)) {
          familyMap.set(category, {
            family: category,
            totalRevenue: 0,
            totalUnits: 0,
            totalMasterBoxes: 0,
            subfamilies: [],
          });
        }

        const familyData = familyMap.get(category)!;
        familyData.totalRevenue += subfamilyData.totalRevenue;
        familyData.totalUnits += subfamilyData.totalUnits;
        familyData.totalMasterBoxes += subfamilyData.totalMasterBoxes;

        familyData.subfamilies.push({
          base_code: subfamilyData.base_code,
          product_name: subfamilyData.product_name,
          totalRevenue: subfamilyData.totalRevenue,
          totalUnits: subfamilyData.totalUnits,
          totalMasterBoxes: subfamilyData.totalMasterBoxes,
          skus: Array.from(subfamilyData.skus.values())
            .sort((a, b) => b.totalRevenue - a.totalRevenue),
        });
      });

      // Sort families and subfamilies
      const familiesArray = Array.from(familyMap.values())
        .map(family => ({
          ...family,
          subfamilies: family.subfamilies.sort((a, b) => b.totalRevenue - a.totalRevenue),
        }))
        .sort((a, b) => b.totalRevenue - a.totalRevenue);

      setFamilySales(familiesArray);

      // ============================================================================
      // SOURCE ANALYSIS AGGREGATION (shopify, relbase, mercadolibre, lokal)
      // ============================================================================

      const sourceMap = new Map<string, {
        channel: string;
        totalRevenue: number;
        totalUnits: number;
        orderIds: Set<string>;
        byCategory: Map<string, { revenue: number; units: number; orderIds: Set<string> }>;
        byPackageType: Map<string, { revenue: number; units: number }>;
        productSales: Map<string, { sku: string; name: string; revenue: number; units: number }>;
      }>();

      // Aggregate by source from orders
      orders.forEach(order => {
        if (order.items) {
          order.items.forEach(item => {
            const product = skuMap.get(item.product_sku);

            // Determine source based on product SKU pattern:
            // 1. ML- prefix = MercadoLibre sale
            // 2. Official SKU (BAKC_, GRAL_, etc.) from products table with source = channel
            // 3. WEB_ prefix = Shopify sale
            // 4. ANU- prefix or other = Relbase direct sale

            let source = 'relbase'; // Default

            const sku = item.product_sku;

            // Check SKU patterns
            if (sku.startsWith('ML-')) {
              source = 'mercadolibre';
            } else if (sku.startsWith('WEB_')) {
              source = 'shopify';
            } else if (product && product.source && product.source !== 'CATALOG') {
              // Use product.source for official SKUs
              source = product.source;
            } else if (order.source && order.source !== 'relbase') {
              // Fallback to order source if not relbase
              source = order.source;
            }

            const catalogProduct = catalog.get(product?.sku || item.product_sku);

            if (!sourceMap.has(source)) {
              sourceMap.set(source, {
                channel: source,
                totalRevenue: 0,
                totalUnits: 0,
                orderIds: new Set(),
                byCategory: new Map(),
                byPackageType: new Map(),
                productSales: new Map(),
              });
            }

            const sourceData = sourceMap.get(source)!;
            sourceData.totalRevenue += item.quantity * item.unit_price;
            sourceData.totalUnits += item.quantity;
            sourceData.orderIds.add(order.order_number);

            // By category
            if (catalogProduct) {
              const category = catalogProduct.category;
              if (!sourceData.byCategory.has(category)) {
                sourceData.byCategory.set(category, { revenue: 0, units: 0, orderIds: new Set() });
              }
              const categoryData = sourceData.byCategory.get(category)!;
              categoryData.revenue += item.quantity * item.unit_price;
              categoryData.units += item.quantity;
              categoryData.orderIds.add(order.order_number);

              // By package type
              const packageType = catalogProduct.package_type;
              if (!sourceData.byPackageType.has(packageType)) {
                sourceData.byPackageType.set(packageType, { revenue: 0, units: 0 });
              }
              const packageData = sourceData.byPackageType.get(packageType)!;
              packageData.revenue += item.quantity * item.unit_price;
              packageData.units += item.quantity;

              // Product sales
              const productKey = product.sku;
              if (!sourceData.productSales.has(productKey)) {
                sourceData.productSales.set(productKey, {
                  sku: product.sku,
                  name: catalogProduct.product_name || product.name,
                  revenue: 0,
                  units: 0,
                });
              }
              const productData = sourceData.productSales.get(productKey)!;
              productData.revenue += item.quantity * item.unit_price;
              productData.units += item.quantity;
            }
          });
        }
      });

      // Convert to ChannelSales array for sources
      const sourcesArray: ChannelSales[] = Array.from(sourceMap.values())
        .map(sourceData => ({
          channel: sourceData.channel,
          totalRevenue: sourceData.totalRevenue,
          totalUnits: sourceData.totalUnits,
          totalOrders: sourceData.orderIds.size,
          avgTicket: sourceData.totalRevenue / sourceData.orderIds.size,
          avgUnitsPerOrder: sourceData.totalUnits / sourceData.orderIds.size,
          byCategory: Array.from(sourceData.byCategory.entries())
            .map(([category, data]) => ({
              category,
              revenue: data.revenue,
              units: data.units,
              orders: data.orderIds.size,
            }))
            .sort((a, b) => b.revenue - a.revenue),
          byPackageType: Array.from(sourceData.byPackageType.entries())
            .map(([packageType, data]) => ({
              packageType,
              revenue: data.revenue,
              units: data.units,
            }))
            .sort((a, b) => b.revenue - a.revenue),
          topProducts: Array.from(sourceData.productSales.values())
            .sort((a, b) => b.revenue - a.revenue)
            .slice(0, 10),
        }))
        .sort((a, b) => b.totalRevenue - a.totalRevenue);

      setSourceSales(sourcesArray);

      // ============================================================================
      // BUSINESS CHANNEL ANALYSIS AGGREGATION (Corporativo, Distribuidor, E-commerce, etc.)
      // ============================================================================

      const businessChannelMap = new Map<string, {
        channel: string;
        totalRevenue: number;
        totalUnits: number;
        orderIds: Set<string>;
        byCategory: Map<string, { revenue: number; units: number; orderIds: Set<string> }>;
        byPackageType: Map<string, { revenue: number; units: number }>;
        productSales: Map<string, { sku: string; name: string; revenue: number; units: number }>;
      }>();

      // Aggregate by business channel from orders
      orders.forEach(order => {
        if (order.items) {
          order.items.forEach(item => {
            const product = skuMap.get(item.product_sku);

            // Use channel_name from order (business channel like "Corporativo", "Distribuidor", etc.)
            const businessChannel = order.channel_name || 'Sin Canal Asignado';

            const catalogProduct = catalog.get(product?.sku || item.product_sku);

            if (!businessChannelMap.has(businessChannel)) {
              businessChannelMap.set(businessChannel, {
                channel: businessChannel,
                totalRevenue: 0,
                totalUnits: 0,
                orderIds: new Set(),
                byCategory: new Map(),
                byPackageType: new Map(),
                productSales: new Map(),
              });
            }

            const channelData = businessChannelMap.get(businessChannel)!;
            channelData.totalRevenue += item.quantity * item.unit_price;
            channelData.totalUnits += item.quantity;
            channelData.orderIds.add(order.order_number);

            // By category
            if (catalogProduct) {
              const category = catalogProduct.category;
              if (!channelData.byCategory.has(category)) {
                channelData.byCategory.set(category, { revenue: 0, units: 0, orderIds: new Set() });
              }
              const categoryData = channelData.byCategory.get(category)!;
              categoryData.revenue += item.quantity * item.unit_price;
              categoryData.units += item.quantity;
              categoryData.orderIds.add(order.order_number);

              // By package type
              const packageType = catalogProduct.package_type;
              if (!channelData.byPackageType.has(packageType)) {
                channelData.byPackageType.set(packageType, { revenue: 0, units: 0 });
              }
              const packageData = channelData.byPackageType.get(packageType)!;
              packageData.revenue += item.quantity * item.unit_price;
              packageData.units += item.quantity;

              // Product sales
              const productKey = product?.sku || item.product_sku;
              if (!channelData.productSales.has(productKey)) {
                channelData.productSales.set(productKey, {
                  sku: productKey,
                  name: catalogProduct.product_name || product?.name || item.product_sku,
                  revenue: 0,
                  units: 0,
                });
              }
              const productData = channelData.productSales.get(productKey)!;
              productData.revenue += item.quantity * item.unit_price;
              productData.units += item.quantity;
            }
          });
        }
      });

      // Convert to ChannelSales array for business channels
      const businessChannelsArray: ChannelSales[] = Array.from(businessChannelMap.values())
        .map(channelData => ({
          channel: channelData.channel,
          totalRevenue: channelData.totalRevenue,
          totalUnits: channelData.totalUnits,
          totalOrders: channelData.orderIds.size,
          avgTicket: channelData.totalRevenue / channelData.orderIds.size,
          avgUnitsPerOrder: channelData.totalUnits / channelData.orderIds.size,
          byCategory: Array.from(channelData.byCategory.entries())
            .map(([category, data]) => ({
              category,
              revenue: data.revenue,
              units: data.units,
              orders: data.orderIds.size,
            }))
            .sort((a, b) => b.revenue - a.revenue),
          byPackageType: Array.from(channelData.byPackageType.entries())
            .map(([packageType, data]) => ({
              packageType,
              revenue: data.revenue,
              units: data.units,
            }))
            .sort((a, b) => b.revenue - a.revenue),
          topProducts: Array.from(channelData.productSales.values())
            .sort((a, b) => b.revenue - a.revenue)
            .slice(0, 10),
        }))
        .sort((a, b) => b.totalRevenue - a.totalRevenue);

      setBusinessChannelSales(businessChannelsArray);
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
    if (channel === 'relbase') return 'bg-blue-100 text-blue-800';
    if (channel === 'lokal') return 'bg-purple-100 text-purple-800';
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
      {/* Analysis View Tabs */}
      <div className="bg-white border border-gray-300 rounded-lg p-2">
        <div className="flex gap-2">
          <button
            onClick={() => setAnalysisView('family')}
            className={`flex-1 px-6 py-3 rounded-lg font-semibold transition-all ${
              analysisView === 'family'
                ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            📊 Análisis por Familia
          </button>
          <button
            onClick={() => setAnalysisView('source')}
            className={`flex-1 px-6 py-3 rounded-lg font-semibold transition-all ${
              analysisView === 'source'
                ? 'bg-gradient-to-r from-green-500 to-blue-500 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            🔄 Análisis por Fuente
          </button>
          <button
            onClick={() => setAnalysisView('channel')}
            className={`flex-1 px-6 py-3 rounded-lg font-semibold transition-all ${
              analysisView === 'channel'
                ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            📊 Análisis por Canal
          </button>
        </div>
      </div>

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
      {/* ANALYSIS BY FAMILY */}
      {analysisView === 'family' && (
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

      {/* Family Sales - Hierarchical View */}
      {familySales.map((family, idx) => {
        const isFamilyExpanded = selectedFamily === family.family;
        const revenuePercentage = (family.totalRevenue / totalRevenue) * 100;

        return (
          <div key={idx} className="bg-white border-2 border-gray-300 rounded-xl overflow-hidden shadow-md">
            {/* Family Header */}
            <div
              className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white p-6 cursor-pointer hover:from-indigo-600 hover:to-purple-600 transition-all"
              onClick={() => {
                setSelectedFamily(isFamilyExpanded ? null : family.family);
                setSelectedSubfamily(null); // Reset subfamily when collapsing
                setSelectedSKU(null); // Reset SKU when collapsing
              }}
            >
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-4">
                  <span className="text-5xl">{getFamilyIcon(family.family)}</span>
                  <div>
                    <h2 className="text-2xl font-bold">{family.family}</h2>
                    <p className="text-sm opacity-90 mt-1">
                      {family.subfamilies.length} subfamilia{family.subfamilies.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold">{formatCurrency(family.totalRevenue)}</div>
                  <div className="text-sm opacity-90">{revenuePercentage.toFixed(1)}% del total</div>
                  <div className="grid grid-cols-2 gap-2 mt-2 text-xs opacity-90">
                    <div>
                      <span className="opacity-75">Unidades:</span> <span className="font-semibold">{family.totalUnits.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="opacity-75">Cajas:</span> <span className="font-semibold">{family.totalMasterBoxes.toFixed(1)}</span>
                    </div>
                  </div>
                  <div className="text-xs opacity-75 mt-2">
                    {isFamilyExpanded ? '▲ Ocultar' : '▼ Ver subfamilias'}
                  </div>
                </div>
              </div>
            </div>

            {/* Subfamilies within Family */}
            {isFamilyExpanded && (
              <div className="p-4 space-y-3 bg-gray-50">
                {family.subfamilies.map((subfamily, sfidx) => {
                  const isSubfamilyExpanded = selectedSubfamily === subfamily.base_code;
                  const subfamilyRevenuePercentage = (subfamily.totalRevenue / family.totalRevenue) * 100;

                  return (
                    <div key={sfidx} className="bg-white border border-gray-300 rounded-lg overflow-hidden shadow-sm">
                      {/* Subfamily Header */}
                      <div
                        className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 cursor-pointer hover:from-blue-100 hover:to-purple-100 transition-all border-b border-gray-200"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedSubfamily(isSubfamilyExpanded ? null : subfamily.base_code);
                          setSelectedSKU(null); // Reset SKU when collapsing
                        }}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="font-semibold text-gray-900 text-lg">{subfamily.product_name}</h3>
                              <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-mono rounded">
                                {subfamily.base_code}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600">
                              {subfamily.skus.length} SKU{subfamily.skus.length !== 1 ? 's' : ''} • {formatCurrency(subfamily.totalRevenue)}
                            </p>
                          </div>
                          <div className="text-right">
                            <div className="text-xl font-bold text-indigo-600">
                              {subfamilyRevenuePercentage.toFixed(1)}%
                            </div>
                            <div className="text-xs text-gray-500">de la familia</div>
                            <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
                              <div className="bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                {subfamily.totalUnits.toLocaleString()} un
                              </div>
                              <div className="bg-purple-100 text-purple-800 px-2 py-1 rounded">
                                {subfamily.totalMasterBoxes.toFixed(1)} cajas
                              </div>
                            </div>
                            <div className="text-[10px] text-gray-500 mt-1">
                              {isSubfamilyExpanded ? '▲ Ocultar SKUs' : '▼ Ver SKUs'}
                            </div>
                          </div>
                        </div>

                        {/* Revenue Bar */}
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
                          <div
                            className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2 rounded-full"
                            style={{ width: `${subfamilyRevenuePercentage}%` }}
                          />
                        </div>
                      </div>

                      {/* SKUs within Subfamily */}
                      {isSubfamilyExpanded && (
                        <div className="p-3 space-y-2 bg-gray-50">
                          {subfamily.skus.map((sku, skuidx) => {
                            const isSKUExpanded = selectedSKU === sku.sku;
                            const skuRevenuePercentage = (sku.totalRevenue / subfamily.totalRevenue) * 100;

                            return (
                              <div key={skuidx} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                                {/* SKU Header */}
                                <div
                                  className="p-3 cursor-pointer hover:bg-gray-50 transition-all"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedSKU(isSKUExpanded ? null : sku.sku);
                                  }}
                                >
                                  <div className="flex justify-between items-start">
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 mb-1">
                                        <span className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-mono rounded">
                                          {sku.sku}
                                        </span>
                                        <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getFormatColor(sku.package_type)}`}>
                                          {sku.package_type}
                                        </span>
                                      </div>
                                      <p className="text-sm text-gray-900 font-medium">{sku.product_name}</p>
                                      <p className="text-xs text-gray-600 mt-1">
                                        {sku.units_per_display} unidades por display
                                      </p>
                                    </div>
                                    <div className="text-right">
                                      <div className="text-lg font-bold text-gray-900">
                                        {formatCurrency(sku.totalRevenue)}
                                      </div>
                                      <div className="text-xs text-gray-500">{skuRevenuePercentage.toFixed(1)}%</div>
                                      <div className="grid grid-cols-2 gap-1 mt-2 text-[10px]">
                                        <div className="bg-green-100 text-green-800 px-1.5 py-0.5 rounded">
                                          {sku.totalUnits} un
                                        </div>
                                        <div className="bg-orange-100 text-orange-800 px-1.5 py-0.5 rounded">
                                          {sku.totalMasterBoxes.toFixed(1)} cajas
                                        </div>
                                      </div>
                                      <div className="text-[9px] text-gray-500 mt-1">
                                        {isSKUExpanded ? '▲' : '▼'} {isSKUExpanded ? 'Ocultar' : 'Ver canales'}
                                      </div>
                                    </div>
                                  </div>
                                </div>

                                {/* Channels for this SKU */}
                                {isSKUExpanded && (
                                  <div className="p-3 pt-0 space-y-2">
                                    <h4 className="text-xs font-semibold text-gray-700 mb-2">🔄 Ventas por Canal</h4>
                                    {sku.byChannel
                                      .sort((a, b) => b.revenue - a.revenue)
                                      .map((channel, cidx) => {
                                        const channelPercentage = (channel.revenue / sku.totalRevenue) * 100;
                                        return (
                                          <div key={cidx} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${getChannelColor(channel.channel)}`}>
                                              {channel.channel}
                                            </span>
                                            <div className="flex-1 mx-3 bg-gray-200 rounded-full h-2">
                                              <div
                                                className="bg-green-500 h-2 rounded-full"
                                                style={{ width: `${channelPercentage}%` }}
                                              />
                                            </div>
                                            <div className="text-xs text-gray-600 text-right">
                                              <div>{channel.units} un</div>
                                              <div className="font-semibold">{formatCurrency(channel.revenue)}</div>
                                            </div>
                                          </div>
                                        );
                                      })}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
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
      {/* END ANALYSIS BY FAMILY */}

      {/* ANALYSIS BY SOURCE */}
      {analysisView === 'source' && sourceSales.length > 0 && (
        <>
      {/* Source Comparison Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sourceSales.map((channel, idx) => {
          const totalChannelRevenue = sourceSales.reduce((sum, c) => sum + c.totalRevenue, 0);
          const revenuePercentage = (channel.totalRevenue / totalChannelRevenue) * 100;

          return (
            <div key={idx} className="bg-white border-2 border-gray-300 rounded-xl overflow-hidden shadow-md">
              {/* Channel Header */}
              <div className={`p-6 text-white ${
                channel.channel === 'shopify'
                  ? 'bg-gradient-to-r from-green-500 to-emerald-600'
                  : channel.channel === 'mercadolibre'
                  ? 'bg-gradient-to-r from-yellow-500 to-orange-500'
                  : channel.channel === 'relbase'
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-600'
                  : channel.channel === 'lokal'
                  ? 'bg-gradient-to-r from-purple-500 to-violet-600'
                  : 'bg-gradient-to-r from-gray-500 to-gray-600'
              }`}>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-4xl">
                    {channel.channel === 'shopify' ? '🛒' :
                     channel.channel === 'mercadolibre' ? '🏪' :
                     channel.channel === 'relbase' ? '🧾' :
                     channel.channel === 'lokal' ? '🏬' : '📦'}
                  </span>
                  <div>
                    <h3 className="text-2xl font-bold capitalize">{channel.channel}</h3>
                    <p className="text-sm opacity-90">{revenuePercentage.toFixed(1)}% del total</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-600 mb-1">Ingresos</div>
                    <div className="text-xl font-bold text-gray-900">{formatCurrency(channel.totalRevenue)}</div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-600 mb-1">Órdenes</div>
                    <div className="text-xl font-bold text-gray-900">{channel.totalOrders.toLocaleString()}</div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-600 mb-1">Ticket Promedio</div>
                    <div className="text-lg font-bold text-gray-900">{formatCurrency(channel.avgTicket)}</div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-600 mb-1">Unidades/Orden</div>
                    <div className="text-lg font-bold text-gray-900">{channel.avgUnitsPerOrder.toFixed(1)}</div>
                  </div>
                </div>
              </div>

              {/* Channel Details */}
              <div className="p-4 space-y-4">
                {/* Categories Performance */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <span>📊</span> Categorías Más Vendidas
                  </h4>
                  <div className="space-y-2">
                    {channel.byCategory.slice(0, 5).map((cat, cidx) => {
                      const catPercentage = (cat.revenue / channel.totalRevenue) * 100;
                      return (
                        <div key={cidx} className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-900">{cat.category}</div>
                            <div className="text-xs text-gray-600">{cat.units} un • {cat.orders} órdenes</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-24 bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-indigo-500 h-2 rounded-full"
                                style={{ width: `${catPercentage}%` }}
                              />
                            </div>
                            <div className="text-xs font-semibold text-gray-700 w-12 text-right">
                              {catPercentage.toFixed(0)}%
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Package Types */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <span>📦</span> Formatos Preferidos
                  </h4>
                  <div className="grid grid-cols-2 gap-2">
                    {channel.byPackageType.slice(0, 6).map((pkg, pidx) => {
                      const pkgPercentage = (pkg.units / channel.totalUnits) * 100;
                      return (
                        <div key={pidx} className="bg-gray-50 rounded-lg p-2 border border-gray-200">
                          <div className="text-xs font-semibold text-gray-700 mb-1">{pkg.packageType}</div>
                          <div className="flex items-center justify-between">
                            <div className="text-xs text-gray-600">{pkg.units} un</div>
                            <div className="text-xs font-bold text-indigo-600">{pkgPercentage.toFixed(0)}%</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Top Products */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <span>🏆</span> Top 5 Productos
                  </h4>
                  <div className="space-y-2">
                    {channel.topProducts.slice(0, 5).map((prod, pidx) => (
                      <div key={pidx} className="flex items-center justify-between bg-gray-50 rounded-lg p-2 border border-gray-200">
                        <div className="flex-1">
                          <div className="text-xs font-mono text-gray-600">{prod.sku}</div>
                          <div className="text-sm font-medium text-gray-900 truncate">{prod.name}</div>
                        </div>
                        <div className="text-right ml-2">
                          <div className="text-sm font-bold text-gray-900">{formatCurrency(prod.revenue)}</div>
                          <div className="text-xs text-gray-600">{prod.units} un</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
        </>
      )}
      {/* END ANALYSIS BY SOURCE */}

      {/* ANALYSIS BY BUSINESS CHANNEL */}
      {analysisView === 'channel' && businessChannelSales.length > 0 && (
        <>
      {/* Business Channel Comparison Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {businessChannelSales.map((channel, idx) => {
          const totalChannelRevenue = businessChannelSales.reduce((sum, c) => sum + c.totalRevenue, 0);
          const revenuePercentage = (channel.totalRevenue / totalChannelRevenue) * 100;

          return (
            <div key={idx} className="bg-white border-2 border-gray-300 rounded-xl overflow-hidden shadow-md">
              {/* Business Channel Header */}
              <div className={`p-6 text-white ${
                channel.channel === 'Corporativo'
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-600'
                  : channel.channel === 'Distribuidor'
                  ? 'bg-gradient-to-r from-purple-500 to-violet-600'
                  : channel.channel === 'E-commerce' || channel.channel === 'ECOMMERCE'
                  ? 'bg-gradient-to-r from-green-500 to-emerald-600'
                  : channel.channel === 'Retail' || channel.channel === 'RETAIL'
                  ? 'bg-gradient-to-r from-orange-500 to-red-600'
                  : channel.channel === 'Emporio/Tiendas Locales' || channel.channel === 'LOKAL'
                  ? 'bg-gradient-to-r from-yellow-500 to-orange-500'
                  : channel.channel === 'Emporios y Cafeterías'
                  ? 'bg-gradient-to-r from-pink-500 to-rose-600'
                  : channel.channel === 'Tienda Web Shopify'
                  ? 'bg-gradient-to-r from-green-600 to-teal-600'
                  : channel.channel === 'MercadoLibre'
                  ? 'bg-gradient-to-r from-yellow-400 to-yellow-600'
                  : 'bg-gradient-to-r from-gray-500 to-gray-600'
              }`}>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-4xl">
                    {channel.channel === 'Corporativo' ? '🏢' :
                     channel.channel === 'Distribuidor' ? '🚚' :
                     channel.channel === 'E-commerce' || channel.channel === 'ECOMMERCE' ? '🛒' :
                     channel.channel === 'Retail' || channel.channel === 'RETAIL' ? '🏪' :
                     channel.channel === 'Emporio/Tiendas Locales' || channel.channel === 'LOKAL' ? '🏬' :
                     channel.channel === 'Emporios y Cafeterías' ? '☕' :
                     channel.channel === 'Tienda Web Shopify' ? '🛍️' :
                     channel.channel === 'MercadoLibre' ? '🏪' :
                     channel.channel === 'Sin Canal Asignado' ? '❓' : '📦'}
                  </span>
                  <div>
                    <h3 className="text-2xl font-bold">{channel.channel}</h3>
                    <p className="text-sm opacity-90">{revenuePercentage.toFixed(1)}% del total</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-600 mb-1">Ingresos</div>
                    <div className="text-xl font-bold text-gray-900">{formatCurrency(channel.totalRevenue)}</div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-600 mb-1">Órdenes</div>
                    <div className="text-xl font-bold text-gray-900">{channel.totalOrders.toLocaleString()}</div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-600 mb-1">Ticket Promedio</div>
                    <div className="text-lg font-bold text-gray-900">{formatCurrency(channel.avgTicket)}</div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-600 mb-1">Unidades/Orden</div>
                    <div className="text-lg font-bold text-gray-900">{channel.avgUnitsPerOrder.toFixed(1)}</div>
                  </div>
                </div>
              </div>

              {/* Business Channel Details */}
              <div className="p-4 space-y-4">
                {/* Categories Performance */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <span>📊</span> Categorías Más Vendidas
                  </h4>
                  <div className="space-y-2">
                    {channel.byCategory.slice(0, 5).map((cat, cidx) => {
                      const catPercentage = (cat.revenue / channel.totalRevenue) * 100;
                      return (
                        <div key={cidx} className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-900">{cat.category}</div>
                            <div className="text-xs text-gray-600">{cat.units} un • {cat.orders} órdenes</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-24 bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-indigo-500 h-2 rounded-full"
                                style={{ width: `${catPercentage}%` }}
                              />
                            </div>
                            <div className="text-xs font-semibold text-gray-700 w-12 text-right">
                              {catPercentage.toFixed(0)}%
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Package Types */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <span>📦</span> Formatos Preferidos
                  </h4>
                  <div className="grid grid-cols-2 gap-2">
                    {channel.byPackageType.slice(0, 6).map((pkg, pidx) => {
                      const pkgPercentage = (pkg.units / channel.totalUnits) * 100;
                      return (
                        <div key={pidx} className="bg-gray-50 rounded-lg p-2 border border-gray-200">
                          <div className="text-xs font-semibold text-gray-700 mb-1">{pkg.packageType}</div>
                          <div className="flex items-center justify-between">
                            <div className="text-xs text-gray-600">{pkg.units} un</div>
                            <div className="text-xs font-bold text-indigo-600">{pkgPercentage.toFixed(0)}%</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Top Products */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <span>🏆</span> Top 5 Productos
                  </h4>
                  <div className="space-y-2">
                    {channel.topProducts.slice(0, 5).map((prod, pidx) => (
                      <div key={pidx} className="flex items-center justify-between bg-gray-50 rounded-lg p-2 border border-gray-200">
                        <div className="flex-1">
                          <div className="text-xs font-mono text-gray-600">{prod.sku}</div>
                          <div className="text-sm font-medium text-gray-900 truncate">{prod.name}</div>
                        </div>
                        <div className="text-right ml-2">
                          <div className="text-sm font-bold text-gray-900">{formatCurrency(prod.revenue)}</div>
                          <div className="text-xs text-gray-600">{prod.units} un</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
        </>
      )}
      {/* END ANALYSIS BY BUSINESS CHANNEL */}

        </>
      )}
    </div>
  );
}
