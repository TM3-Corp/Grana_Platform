'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useSession } from 'next-auth/react';
import Navigation from '@/components/Navigation';
import { toTitleCase, formatCurrencyFull } from '@/lib/utils';
import {
  Factory,
  TrendingDown,
  AlertTriangle,
  RefreshCw,
  Search,
  X,
  Loader2,
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  DollarSign,
  Clock,
  Package,
  Calendar,
} from 'lucide-react';

// =============================================================================
// Types
// =============================================================================

// Production Planning Types
interface ProductionProduct {
  sku: string;
  name: string;
  category: string | null;
  stock_total: number;
  stock_usable: number;
  avg_monthly_sales: number;
  days_of_coverage: number;
  production_needed: number;
  urgency: 'critical' | 'high' | 'medium' | 'low';
  earliest_expiration: string | null;
  days_to_earliest_expiration: number | null;
}

interface ProductionSummary {
  products_needing_production: number;
  total_units_needed: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  expiring_units: number;
}

interface LotInfo {
  lot_number: string;
  warehouse_code: string;
  warehouse_name: string;
  quantity: number;
  expiration_date: string | null;
  days_to_expiration: number | null;
  status: string;
  at_risk: boolean;
}

interface LotBreakdownData {
  lots: LotInfo[];
  risk_analysis: {
    units_at_risk: number;
    risk_message: string;
  };
}

// Stockout Risk Types
interface StockoutRisk {
  sku_primario: string;
  product_name: string;
  category: string;
  current_stock: number;
  avg_monthly_demand: number;
  days_of_coverage: number;
  safety_stock: number;
  reorder_point: number;
  risk_level: 'critical' | 'high' | 'medium' | 'low';
  forecasted_stockout_date: string | null;
  units_needed: number;
}

interface TopProductLoss {
  sku: string;
  name: string;
  stockout_count: number;
  lost_revenue: number;
}

interface LostRevenueSummary {
  analysis_date: string;
  data_period_start: string;
  data_period_end: string;
  months_analyzed: number;
  products_analyzed: number;
  products_with_stockouts: number;
  total_stockout_periods: number;
  total_lost_revenue: number;
  annualized_opportunity: number;
  conservative_estimate: number;
  optimistic_estimate: number;
  top_products: TopProductLoss[];
}

type ActiveTab = 'produccion' | 'riesgo';

// =============================================================================
// Component
// =============================================================================

export default function PlanificacionIntegralPage() {
  const { data: session, status: authStatus } = useSession();

  // Tab state
  const [activeTab, setActiveTab] = useState<ActiveTab>('produccion');

  // Production data
  const [productionData, setProductionData] = useState<ProductionProduct[]>([]);
  const [productionSummary, setProductionSummary] = useState<ProductionSummary | null>(null);
  const [productionLoading, setProductionLoading] = useState(true);

  // Risk data
  const [riskData, setRiskData] = useState<StockoutRisk[]>([]);
  const [revenueSummary, setRevenueSummary] = useState<LostRevenueSummary | null>(null);
  const [riskLoading, setRiskLoading] = useState(true);

  // Shared state
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState('');

  // Expansion state (for production tab)
  const [expandedSku, setExpandedSku] = useState<string | null>(null);
  const [lotBreakdown, setLotBreakdown] = useState<LotBreakdownData | null>(null);
  const [lotLoading, setLotLoading] = useState(false);

  // Categories from both datasets
  const categories = useMemo(() => {
    const prodCats = productionData.map(p => p.category).filter(Boolean);
    const riskCats = riskData.map(r => r.category).filter(Boolean);
    return [...new Set([...prodCats, ...riskCats])].sort() as string[];
  }, [productionData, riskData]);

  // Filtered data
  const filteredProduction = useMemo(() => {
    let filtered = [...productionData];

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        p.sku.toLowerCase().includes(query) ||
        p.name.toLowerCase().includes(query)
      );
    }

    if (categoryFilter) {
      filtered = filtered.filter(p => p.category === categoryFilter);
    }

    if (urgencyFilter) {
      filtered = filtered.filter(p => p.urgency === urgencyFilter);
    }

    return filtered;
  }, [productionData, searchQuery, categoryFilter, urgencyFilter]);

  const filteredRisks = useMemo(() => {
    let filtered = [...riskData];

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(r =>
        r.sku_primario.toLowerCase().includes(query) ||
        r.product_name.toLowerCase().includes(query)
      );
    }

    if (categoryFilter) {
      filtered = filtered.filter(r => r.category === categoryFilter);
    }

    if (urgencyFilter) {
      filtered = filtered.filter(r => r.risk_level === urgencyFilter);
    }

    return filtered;
  }, [riskData, searchQuery, categoryFilter, urgencyFilter]);

  // Fetch production data
  const fetchProductionData = async () => {
    setProductionLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/inventory-planning/production-recommendations?only_needing_production=false&limit=200`);

      if (response.ok) {
        const data = await response.json();
        setProductionData(data.data || []);
        setProductionSummary(data.summary || null);
      }
    } catch (err) {
      console.error('Error fetching production data:', err);
    } finally {
      setProductionLoading(false);
    }
  };

  // Fetch risk data
  const fetchRiskData = async () => {
    setRiskLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const [risksRes, summaryRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/forecasting/stockout-risk?limit=100`),
        fetch(`${apiUrl}/api/v1/forecasting/lost-revenue-summary`)
      ]);

      if (risksRes.ok) {
        const data = await risksRes.json();
        setRiskData(data);
      }

      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setRevenueSummary(data);
      }
    } catch (err) {
      console.error('Error fetching risk data:', err);
    } finally {
      setRiskLoading(false);
    }
  };

  // Fetch lot breakdown
  const fetchLotBreakdown = async (sku: string) => {
    setLotLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/inventory-planning/lot-breakdown/${encodeURIComponent(sku)}`);

      if (response.ok) {
        const data = await response.json();
        setLotBreakdown(data);
      } else {
        setLotBreakdown(null);
      }
    } catch (err) {
      setLotBreakdown(null);
    } finally {
      setLotLoading(false);
    }
  };

  // Handle row expansion
  const handleRowClick = (sku: string) => {
    if (expandedSku === sku) {
      setExpandedSku(null);
      setLotBreakdown(null);
    } else {
      setExpandedSku(sku);
      fetchLotBreakdown(sku);
    }
  };

  // Refresh all data
  const refreshData = () => {
    fetchProductionData();
    fetchRiskData();
  };

  // Initial load
  useEffect(() => {
    if (authStatus === 'authenticated') {
      refreshData();
    }
  }, [authStatus]);

  // Helper functions
  const getUrgencyBadge = (urgency: string) => {
    switch (urgency) {
      case 'critical': return 'bg-red-600 text-white';
      case 'high': return 'bg-orange-500 text-white';
      case 'medium': return 'bg-amber-400 text-amber-900';
      case 'low': return 'bg-emerald-500 text-white';
      default: return 'bg-gray-400 text-white';
    }
  };

  const getUrgencyLabel = (urgency: string) => {
    switch (urgency) {
      case 'critical': return 'CRITICO';
      case 'high': return 'ALTO';
      case 'medium': return 'MEDIO';
      case 'low': return 'BAJO';
      default: return urgency.toUpperCase();
    }
  };

  const getCoverageStyle = (days: number) => {
    if (days < 15) return 'text-red-700 bg-red-50 border-red-200';
    if (days < 30) return 'text-orange-700 bg-orange-50 border-orange-200';
    if (days < 60) return 'text-amber-700 bg-amber-50 border-amber-200';
    return 'text-emerald-700 bg-emerald-50 border-emerald-200';
  };

  const getLotStatusBadge = (status: string, atRisk: boolean) => {
    if (atRisk) return 'bg-red-100 text-red-700 border-red-200';
    switch (status) {
      case 'Vencido': return 'bg-red-100 text-red-700 border-red-200';
      case 'Por vencer': return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'Vigente': return 'bg-green-100 text-green-700 border-green-200';
      default: return 'bg-gray-100 text-gray-600 border-gray-200';
    }
  };

  // Auth states
  if (authStatus === 'loading') {
    return (
      <div className="flex justify-center items-center min-h-screen bg-slate-50">
        <Loader2 className="w-12 h-12 animate-spin text-blue-600" />
      </div>
    );
  }

  if (authStatus === 'unauthenticated') {
    return (
      <div className="p-8">
        <div className="bg-amber-50 border-l-4 border-amber-500 p-6 rounded-lg">
          <div className="flex items-center gap-4">
            <ShieldAlert className="w-8 h-8 text-amber-500" />
            <div>
              <p className="font-semibold">Acceso Restringido</p>
              <p className="text-gray-600">Por favor inicia sesion para acceder.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isLoading = productionLoading || riskLoading;
  const criticalCount = (productionSummary?.critical_count || 0) + (riskData.filter(r => r.risk_level === 'critical').length);

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
        <div className="p-6 max-w-[1800px] mx-auto">

          {/* Page Header */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2.5 bg-blue-600 rounded-xl">
                <Factory className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                  Planificacion Integral
                </h1>
                <p className="text-slate-500 text-sm">
                  Produccion, riesgo de stockout y oportunidades de ingresos
                </p>
              </div>
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-24">
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-12 h-12 animate-spin text-blue-600" />
                <p className="text-slate-600 font-medium">Cargando datos de planificacion...</p>
              </div>
            </div>
          )}

          {/* Main Content */}
          {!isLoading && (
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">

              {/* Main Content Area */}
              <div className="xl:col-span-3 space-y-4">

                {/* KPI Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  {/* Revenue Opportunity */}
                  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                    <div className="flex items-start justify-between mb-3">
                      <div className="p-2 bg-emerald-100 rounded-lg">
                        <DollarSign className="w-5 h-5 text-emerald-600" />
                      </div>
                    </div>
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Oportunidad Anual</p>
                    <p className="text-xl font-bold text-emerald-600">
                      {formatCurrencyFull(revenueSummary?.annualized_opportunity || 0)}
                    </p>
                  </div>

                  {/* Critical Alerts */}
                  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                    <div className="flex items-start justify-between mb-3">
                      <div className="p-2 bg-red-100 rounded-lg">
                        <AlertTriangle className="w-5 h-5 text-red-600" />
                      </div>
                    </div>
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Criticos ({"<"}15d)</p>
                    <p className="text-xl font-bold text-red-600">
                      {productionSummary?.critical_count || 0}
                    </p>
                  </div>

                  {/* Units to Produce */}
                  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                    <div className="flex items-start justify-between mb-3">
                      <div className="p-2 bg-blue-100 rounded-lg">
                        <Factory className="w-5 h-5 text-blue-600" />
                      </div>
                    </div>
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Producir</p>
                    <p className="text-xl font-bold text-blue-600">
                      {(productionSummary?.total_units_needed || 0).toLocaleString('es-CL')}
                    </p>
                  </div>

                  {/* Stockout Periods */}
                  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                    <div className="flex items-start justify-between mb-3">
                      <div className="p-2 bg-slate-100 rounded-lg">
                        <Clock className="w-5 h-5 text-slate-600" />
                      </div>
                    </div>
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Stockouts Hist.</p>
                    <p className="text-xl font-bold text-slate-900">
                      {revenueSummary?.total_stockout_periods || 0}
                    </p>
                  </div>
                </div>

                {/* Tabs */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                  {/* Tab Headers */}
                  <div className="border-b border-slate-200">
                    <div className="flex">
                      <button
                        onClick={() => setActiveTab('produccion')}
                        className={`px-6 py-4 text-sm font-semibold border-b-2 transition-colors ${
                          activeTab === 'produccion'
                            ? 'border-blue-600 text-blue-600 bg-blue-50/50'
                            : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Factory className="w-4 h-4" />
                          Produccion
                          {productionSummary && (
                            <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">
                              {productionSummary.products_needing_production}
                            </span>
                          )}
                        </div>
                      </button>
                      <button
                        onClick={() => setActiveTab('riesgo')}
                        className={`px-6 py-4 text-sm font-semibold border-b-2 transition-colors ${
                          activeTab === 'riesgo'
                            ? 'border-red-600 text-red-600 bg-red-50/50'
                            : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <TrendingDown className="w-4 h-4" />
                          Riesgo de Stockout
                          <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700">
                            {riskData.filter(r => r.risk_level === 'critical' || r.risk_level === 'high').length}
                          </span>
                        </div>
                      </button>
                    </div>
                  </div>

                  {/* Filters */}
                  <div className="p-4 border-b border-slate-100">
                    <div className="flex flex-wrap items-center gap-4">
                      <div className="flex-1 min-w-[200px]">
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                          <input
                            type="text"
                            placeholder="Buscar por SKU o nombre..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                      </div>

                      <select
                        value={urgencyFilter}
                        onChange={(e) => setUrgencyFilter(e.target.value)}
                        className="px-3 py-2 border border-slate-200 rounded-lg text-sm"
                      >
                        <option value="">Todas las Urgencias</option>
                        <option value="critical">Critico</option>
                        <option value="high">Alto</option>
                        <option value="medium">Medio</option>
                        <option value="low">Bajo</option>
                      </select>

                      <select
                        value={categoryFilter}
                        onChange={(e) => setCategoryFilter(e.target.value)}
                        className="px-3 py-2 border border-slate-200 rounded-lg text-sm"
                      >
                        <option value="">Todas las Categorias</option>
                        {categories.map(cat => (
                          <option key={cat} value={cat}>{toTitleCase(cat)}</option>
                        ))}
                      </select>

                      <button
                        onClick={refreshData}
                        className="px-4 py-2 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-900 flex items-center gap-2"
                      >
                        <RefreshCw className="w-4 h-4" />
                        Actualizar
                      </button>
                    </div>
                  </div>

                  {/* Tab Content */}
                  <div className="overflow-x-auto">
                    {/* Production Tab */}
                    {activeTab === 'produccion' && (
                      <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase w-8"></th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Producto</th>
                            <th className="px-3 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Stock</th>
                            <th className="px-3 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Ventas/Mes</th>
                            <th className="px-3 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Cobertura</th>
                            <th className="px-3 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Producir</th>
                            <th className="px-3 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Urgencia</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {filteredProduction.map((product) => (
                            <React.Fragment key={product.sku}>
                              <tr
                                className="hover:bg-slate-50 cursor-pointer"
                                onClick={() => handleRowClick(product.sku)}
                              >
                                <td className="px-4 py-3">
                                  {expandedSku === product.sku ? (
                                    <ChevronDown className="w-4 h-4 text-slate-400" />
                                  ) : (
                                    <ChevronRight className="w-4 h-4 text-slate-400" />
                                  )}
                                </td>
                                <td className="px-4 py-3">
                                  <div className="flex flex-col gap-0.5">
                                    <div className="flex items-center gap-2">
                                      <code className="text-xs font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">{product.sku}</code>
                                      {product.category && (
                                        <span className="text-xs text-purple-700 bg-purple-50 px-2 py-0.5 rounded">{toTitleCase(product.category)}</span>
                                      )}
                                    </div>
                                    <span className="text-sm font-medium text-slate-800">{toTitleCase(product.name)}</span>
                                  </div>
                                </td>
                                <td className="px-3 py-3 text-right tabular-nums text-sm font-medium text-slate-700">
                                  {product.stock_usable.toLocaleString('es-CL')}
                                </td>
                                <td className="px-3 py-3 text-right tabular-nums text-sm text-slate-600">
                                  {product.avg_monthly_sales.toLocaleString('es-CL')}
                                </td>
                                <td className="px-3 py-3 text-center">
                                  <span className={`inline-flex px-2.5 py-1 rounded-lg text-sm font-semibold border ${getCoverageStyle(product.days_of_coverage)}`}>
                                    {product.days_of_coverage < 999 ? `${product.days_of_coverage}d` : '—'}
                                  </span>
                                </td>
                                <td className="px-3 py-3 text-right">
                                  {product.production_needed > 0 ? (
                                    <span className="inline-flex px-2 py-1 rounded-lg bg-blue-50 text-blue-700 font-semibold text-sm">
                                      +{product.production_needed.toLocaleString('es-CL')}
                                    </span>
                                  ) : (
                                    <span className="text-slate-400">—</span>
                                  )}
                                </td>
                                <td className="px-3 py-3 text-center">
                                  <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-bold ${getUrgencyBadge(product.urgency)}`}>
                                    {getUrgencyLabel(product.urgency)}
                                  </span>
                                </td>
                              </tr>

                              {/* Expanded lot details */}
                              {expandedSku === product.sku && (
                                <tr>
                                  <td colSpan={7} className="px-4 py-4 bg-slate-50">
                                    {lotLoading ? (
                                      <div className="flex items-center justify-center py-6">
                                        <Loader2 className="w-5 h-5 animate-spin text-blue-500 mr-2" />
                                        <span className="text-slate-600">Cargando lotes...</span>
                                      </div>
                                    ) : lotBreakdown && lotBreakdown.lots.length > 0 ? (
                                      <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                          <h4 className="text-sm font-semibold text-slate-700">Detalle de Lotes</h4>
                                          {lotBreakdown.risk_analysis.units_at_risk > 0 && (
                                            <span className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                                              {lotBreakdown.risk_analysis.units_at_risk.toLocaleString('es-CL')} unidades en riesgo
                                            </span>
                                          )}
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                                          {lotBreakdown.lots.slice(0, 9).map((lot, idx) => (
                                            <div key={idx} className={`flex items-center justify-between p-2 rounded border ${lot.at_risk ? 'bg-red-50 border-red-200' : 'bg-white border-slate-200'}`}>
                                              <div className="flex items-center gap-2">
                                                <code className="text-xs font-mono text-slate-500">{lot.lot_number}</code>
                                                <span className={`px-1.5 py-0.5 rounded text-xs font-medium border ${getLotStatusBadge(lot.status, lot.at_risk)}`}>
                                                  {lot.at_risk ? 'Riesgo' : lot.status}
                                                </span>
                                              </div>
                                              <span className="text-sm font-medium text-slate-700">{lot.quantity.toLocaleString('es-CL')}</span>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    ) : (
                                      <p className="text-center text-slate-400 py-4">Sin datos de lotes</p>
                                    )}
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          ))}
                        </tbody>
                      </table>
                    )}

                    {/* Risk Tab */}
                    {activeTab === 'riesgo' && (
                      <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Producto</th>
                            <th className="px-3 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Stock</th>
                            <th className="px-3 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Demanda/Mes</th>
                            <th className="px-3 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Cobertura</th>
                            <th className="px-3 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Safety Stock</th>
                            <th className="px-3 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Necesita</th>
                            <th className="px-3 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Riesgo</th>
                            <th className="px-3 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Stockout Est.</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {filteredRisks.map((risk) => (
                            <tr key={risk.sku_primario} className="hover:bg-slate-50">
                              <td className="px-4 py-3">
                                <div className="flex flex-col gap-0.5">
                                  <div className="flex items-center gap-2">
                                    <code className="text-xs font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">{risk.sku_primario}</code>
                                    {risk.category && (
                                      <span className="text-xs text-purple-700 bg-purple-50 px-2 py-0.5 rounded">{toTitleCase(risk.category)}</span>
                                    )}
                                  </div>
                                  <span className="text-sm font-medium text-slate-800">{toTitleCase(risk.product_name)}</span>
                                </div>
                              </td>
                              <td className="px-3 py-3 text-right tabular-nums text-sm font-medium text-slate-700">
                                {risk.current_stock.toLocaleString('es-CL')}
                              </td>
                              <td className="px-3 py-3 text-right tabular-nums text-sm text-slate-600">
                                {Math.round(risk.avg_monthly_demand).toLocaleString('es-CL')}
                              </td>
                              <td className="px-3 py-3 text-center">
                                <span className={`inline-flex px-2.5 py-1 rounded-lg text-sm font-semibold border ${getCoverageStyle(risk.days_of_coverage)}`}>
                                  {risk.days_of_coverage < 999 ? `${Math.round(risk.days_of_coverage)}d` : '—'}
                                </span>
                              </td>
                              <td className="px-3 py-3 text-right tabular-nums text-sm text-slate-600">
                                {risk.safety_stock.toLocaleString('es-CL')}
                              </td>
                              <td className="px-3 py-3 text-right">
                                {risk.units_needed > 0 ? (
                                  <span className="inline-flex px-2 py-1 rounded-lg bg-blue-50 text-blue-700 font-semibold text-sm">
                                    +{risk.units_needed.toLocaleString('es-CL')}
                                  </span>
                                ) : (
                                  <span className="text-slate-400">—</span>
                                )}
                              </td>
                              <td className="px-3 py-3 text-center">
                                <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-bold ${getUrgencyBadge(risk.risk_level)}`}>
                                  {getUrgencyLabel(risk.risk_level)}
                                </span>
                              </td>
                              <td className="px-3 py-3 text-center text-sm text-slate-600">
                                {risk.forecasted_stockout_date
                                  ? new Date(risk.forecasted_stockout_date).toLocaleDateString('es-CL', { day: '2-digit', month: 'short' })
                                  : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* Table Footer */}
                  <div className="bg-slate-50 px-4 py-3 border-t border-slate-200">
                    <span className="text-sm text-slate-600">
                      Mostrando <strong>{activeTab === 'produccion' ? filteredProduction.length : filteredRisks.length}</strong> productos
                    </span>
                  </div>
                </div>
              </div>

              {/* Sidebar - Top Lost Revenue */}
              <div className="xl:col-span-1">
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm sticky top-6">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 bg-red-100 rounded-lg">
                      <TrendingDown className="w-4 h-4 text-red-600" />
                    </div>
                    <h3 className="text-sm font-bold text-slate-800 uppercase">Top Perdidas</h3>
                  </div>

                  {revenueSummary && revenueSummary.top_products.length > 0 ? (
                    <>
                      <div className="space-y-3">
                        {revenueSummary.top_products.map((product, index) => {
                          const maxRevenue = revenueSummary.top_products[0]?.lost_revenue || 1;
                          const percentage = (product.lost_revenue / maxRevenue) * 100;

                          return (
                            <div key={product.sku}>
                              <div className="flex items-start justify-between mb-1">
                                <div className="flex items-center gap-2">
                                  <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-600 text-xs font-bold flex items-center justify-center">
                                    {index + 1}
                                  </span>
                                  <div className="min-w-0">
                                    <p className="text-xs font-mono text-slate-500 truncate">{product.sku}</p>
                                    <p className="text-sm font-medium text-slate-800 truncate">{toTitleCase(product.name)}</p>
                                  </div>
                                </div>
                              </div>
                              <div className="ml-7">
                                <div className="flex items-center justify-between text-xs mb-1">
                                  <span className="text-slate-500">{product.stockout_count} stockouts</span>
                                  <span className="font-semibold text-red-600">{formatCurrencyFull(product.lost_revenue)}</span>
                                </div>
                                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-gradient-to-r from-red-500 to-red-400 rounded-full"
                                    style={{ width: `${percentage}%` }}
                                  />
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      <div className="mt-6 pt-4 border-t border-slate-200">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-500 uppercase">Total Perdido</span>
                          <span className="text-lg font-bold text-red-600">{formatCurrencyFull(revenueSummary.total_lost_revenue)}</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">En {revenueSummary.months_analyzed} meses</p>
                      </div>

                      <div className="mt-4 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                        <p className="text-xs font-semibold text-emerald-800 mb-1">Si se previene 50%:</p>
                        <p className="text-sm font-bold text-emerald-700">
                          {formatCurrencyFull(revenueSummary.annualized_opportunity * 0.5)} / ano
                        </p>
                      </div>
                    </>
                  ) : (
                    <p className="text-center text-slate-400 py-6">Sin datos de perdidas</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
