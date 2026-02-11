'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Navigation from '@/components/Navigation';
import { toTitleCase, formatCurrencyFull } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

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

type SortField = 'days_of_coverage' | 'current_stock' | 'units_needed' | 'avg_monthly_demand';
type SortDirection = 'asc' | 'desc';

// =============================================================================
// Component
// =============================================================================

export default function ForecastingPage() {
  // Data state
  const [summary, setSummary] = useState<LostRevenueSummary | null>(null);
  const [risks, setRisks] = useState<StockoutRisk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [riskFilter, setRiskFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  // Sort state
  const [sortField, setSortField] = useState<SortField>('days_of_coverage');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Extract unique categories from data
  const categories = useMemo(() => {
    const cats = new Set(risks.map(r => r.category).filter(Boolean));
    return Array.from(cats).sort();
  }, [risks]);

  // Fetch data
  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Fetch both endpoints in parallel
      const [summaryRes, risksRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/forecasting/lost-revenue-summary`),
        fetch(`${apiUrl}/api/v1/forecasting/stockout-risk?limit=100`)
      ]);

      if (!summaryRes.ok || !risksRes.ok) {
        throw new Error('Error al cargar datos de forecasting');
      }

      const [summaryData, risksData] = await Promise.all([
        summaryRes.json(),
        risksRes.json()
      ]);

      setSummary(summaryData);
      setRisks(risksData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Filtered and sorted data
  const filteredRisks = useMemo(() => {
    let filtered = [...risks];

    // Apply risk level filter
    if (riskFilter) {
      filtered = filtered.filter(r => r.risk_level === riskFilter);
    }

    // Apply category filter
    if (categoryFilter) {
      filtered = filtered.filter(r => r.category === categoryFilter);
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(r =>
        r.sku_primario.toLowerCase().includes(query) ||
        r.product_name.toLowerCase().includes(query)
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      const modifier = sortDirection === 'asc' ? 1 : -1;
      return (aVal - bVal) * modifier;
    });

    return filtered;
  }, [risks, riskFilter, categoryFilter, searchQuery, sortField, sortDirection]);

  // Risk counts
  const riskCounts = useMemo(() => {
    return {
      critical: risks.filter(r => r.risk_level === 'critical').length,
      high: risks.filter(r => r.risk_level === 'high').length,
      medium: risks.filter(r => r.risk_level === 'medium').length,
      low: risks.filter(r => r.risk_level === 'low').length,
    };
  }, [risks]);

  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Risk level badge styles
  const getRiskBadge = (level: string) => {
    switch (level) {
      case 'critical':
        return 'bg-red-600 text-white ring-red-600/20';
      case 'high':
        return 'bg-orange-500 text-white ring-orange-500/20';
      case 'medium':
        return 'bg-amber-400 text-amber-900 ring-amber-400/20';
      case 'low':
        return 'bg-emerald-500 text-white ring-emerald-500/20';
      default:
        return 'bg-gray-400 text-white ring-gray-400/20';
    }
  };

  const getRiskLabel = (level: string) => {
    switch (level) {
      case 'critical': return 'CRITICO';
      case 'high': return 'ALTO';
      case 'medium': return 'MEDIO';
      case 'low': return 'BAJO';
      default: return level.toUpperCase();
    }
  };

  // Coverage color
  const getCoverageStyle = (days: number) => {
    if (days < 15) return 'text-red-700 bg-red-50 border-red-200';
    if (days < 30) return 'text-orange-700 bg-orange-50 border-orange-200';
    if (days < 60) return 'text-amber-700 bg-amber-50 border-amber-200';
    return 'text-emerald-700 bg-emerald-50 border-emerald-200';
  };

  // Sort indicator
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return (
        <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return sortDirection === 'asc' ? (
      <svg className="w-3.5 h-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-3.5 h-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
        <div className="p-6 max-w-[1600px] mx-auto">

          {/* Page Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-blue-600 rounded-lg">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                  Forecasting & Riesgo de Stockout
                </h1>
                <p className="text-slate-500 text-sm">
                  Analisis predictivo de demanda y oportunidades de ingresos perdidos
                </p>
              </div>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-24">
              <div className="flex flex-col items-center gap-4">
                <div className="relative">
                  <div className="w-16 h-16 border-4 border-slate-200 rounded-full"></div>
                  <div className="absolute top-0 left-0 w-16 h-16 border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
                </div>
                <p className="text-slate-600 font-medium">Cargando analisis de forecasting...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 rounded-lg">
                  <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-red-800">Error al cargar datos</h3>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
                <button
                  onClick={fetchData}
                  className="ml-auto px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
                >
                  Reintentar
                </button>
              </div>
            </div>
          )}

          {/* Main Content */}
          {!loading && summary && (
            <>
              {/* KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">

                {/* Annualized Opportunity */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-3">
                    <div className="p-2.5 bg-emerald-100 rounded-xl">
                      <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                      ANUAL
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                    Oportunidad de Ingresos
                  </p>
                  <p className="text-2xl font-bold text-slate-900 tabular-nums">
                    {formatCurrencyFull(summary.annualized_opportunity)}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Rango: {formatCurrencyFull(summary.conservative_estimate)} - {formatCurrencyFull(summary.optimistic_estimate)}
                  </p>
                </div>

                {/* Products at Risk */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-3">
                    <div className="p-2.5 bg-orange-100 rounded-xl">
                      <svg className="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                      </svg>
                    </div>
                    <span className="text-xs font-medium text-orange-600 bg-orange-50 px-2 py-1 rounded-full">
                      EN RIESGO
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                    Productos con Stockouts
                  </p>
                  <p className="text-2xl font-bold text-slate-900">
                    {summary.products_with_stockouts}
                    <span className="text-base font-normal text-slate-400 ml-1">
                      / {summary.products_analyzed}
                    </span>
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    {((summary.products_with_stockouts / summary.products_analyzed) * 100).toFixed(0)}% del catalogo afectado
                  </p>
                </div>

                {/* Critical Alerts */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-3">
                    <div className="p-2.5 bg-red-100 rounded-xl">
                      <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    </div>
                    <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-1 rounded-full">
                      {"<"}15 DIAS
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                    Alertas Criticas
                  </p>
                  <p className="text-2xl font-bold text-red-600">
                    {riskCounts.critical}
                  </p>
                  <div className="flex gap-2 mt-2">
                    <span className="text-xs text-orange-600 bg-orange-50 px-2 py-0.5 rounded">
                      {riskCounts.high} alto
                    </span>
                    <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded">
                      {riskCounts.medium} medio
                    </span>
                  </div>
                </div>

                {/* Total Stockout Periods */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-3">
                    <div className="p-2.5 bg-slate-100 rounded-xl">
                      <svg className="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-1 rounded-full">
                      HISTORICO
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                    Periodos de Stockout
                  </p>
                  <p className="text-2xl font-bold text-slate-900">
                    {summary.total_stockout_periods}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    En {summary.months_analyzed} meses ({summary.data_period_start} - {summary.data_period_end})
                  </p>
                </div>
              </div>

              {/* Two Column Layout: Table + Sidebar */}
              <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">

                {/* Main Table Section */}
                <div className="xl:col-span-3">
                  {/* Filters */}
                  <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4 shadow-sm">
                    <div className="flex flex-wrap items-center gap-4">
                      {/* Search */}
                      <div className="flex-1 min-w-[200px]">
                        <div className="relative">
                          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                          <input
                            type="text"
                            placeholder="Buscar por SKU o nombre..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                          />
                        </div>
                      </div>

                      {/* Risk Level Filter */}
                      <div className="flex items-center gap-2">
                        <label className="text-xs font-medium text-slate-600">Riesgo:</label>
                        <select
                          value={riskFilter}
                          onChange={(e) => setRiskFilter(e.target.value)}
                          className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">Todos</option>
                          <option value="critical">Critico</option>
                          <option value="high">Alto</option>
                          <option value="medium">Medio</option>
                          <option value="low">Bajo</option>
                        </select>
                      </div>

                      {/* Category Filter */}
                      <div className="flex items-center gap-2">
                        <label className="text-xs font-medium text-slate-600">Categoria:</label>
                        <select
                          value={categoryFilter}
                          onChange={(e) => setCategoryFilter(e.target.value)}
                          className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">Todas</option>
                          {categories.map(cat => (
                            <option key={cat} value={cat}>{toTitleCase(cat)}</option>
                          ))}
                        </select>
                      </div>

                      {/* Refresh */}
                      <button
                        onClick={fetchData}
                        disabled={loading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                      >
                        <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Actualizar
                      </button>
                    </div>
                  </div>

                  {/* Risk Table */}
                  <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide">
                              Producto
                            </th>
                            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wide">
                              <button
                                onClick={() => handleSort('current_stock')}
                                className="flex items-center gap-1 ml-auto hover:text-blue-600"
                              >
                                Stock <SortIcon field="current_stock" />
                              </button>
                            </th>
                            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wide">
                              <button
                                onClick={() => handleSort('avg_monthly_demand')}
                                className="flex items-center gap-1 ml-auto hover:text-blue-600"
                              >
                                Demanda/Mes <SortIcon field="avg_monthly_demand" />
                              </button>
                            </th>
                            <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wide">
                              <button
                                onClick={() => handleSort('days_of_coverage')}
                                className="flex items-center gap-1 justify-center hover:text-blue-600"
                              >
                                Cobertura <SortIcon field="days_of_coverage" />
                              </button>
                            </th>
                            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wide">
                              Safety Stock
                            </th>
                            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wide">
                              <button
                                onClick={() => handleSort('units_needed')}
                                className="flex items-center gap-1 ml-auto hover:text-blue-600"
                              >
                                Necesita <SortIcon field="units_needed" />
                              </button>
                            </th>
                            <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wide">
                              Riesgo
                            </th>
                            <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wide">
                              Stockout Est.
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-slate-100">
                          {filteredRisks.length === 0 ? (
                            <tr>
                              <td colSpan={8} className="px-4 py-12 text-center">
                                <div className="flex flex-col items-center text-slate-400">
                                  <svg className="w-12 h-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                  </svg>
                                  <p className="font-medium">No hay productos que coincidan</p>
                                  <p className="text-sm">Ajusta los filtros para ver resultados</p>
                                </div>
                              </td>
                            </tr>
                          ) : (
                            filteredRisks.map((risk) => (
                              <tr key={risk.sku_primario} className="hover:bg-slate-50 transition-colors">
                                {/* Product */}
                                <td className="px-4 py-3 min-w-[280px]">
                                  <div className="flex flex-col gap-0.5">
                                    <div className="flex items-center gap-2">
                                      <code className="text-xs font-mono font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                        {risk.sku_primario}
                                      </code>
                                      {risk.category && (
                                        <span className="text-xs font-medium text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                                          {toTitleCase(risk.category)}
                                        </span>
                                      )}
                                    </div>
                                    <span className="text-sm font-medium text-slate-800">
                                      {toTitleCase(risk.product_name)}
                                    </span>
                                  </div>
                                </td>

                                {/* Current Stock */}
                                <td className="px-4 py-3 text-right tabular-nums">
                                  <span className="text-sm font-semibold text-slate-900">
                                    {risk.current_stock.toLocaleString('es-CL')}
                                  </span>
                                </td>

                                {/* Avg Monthly Demand */}
                                <td className="px-4 py-3 text-right tabular-nums">
                                  <span className="text-sm text-slate-600">
                                    {Math.round(risk.avg_monthly_demand).toLocaleString('es-CL')}
                                  </span>
                                </td>

                                {/* Days of Coverage */}
                                <td className="px-4 py-3 text-center">
                                  <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-sm font-semibold border ${getCoverageStyle(risk.days_of_coverage)}`}>
                                    {risk.days_of_coverage < 999 ? `${Math.round(risk.days_of_coverage)}d` : '—'}
                                  </span>
                                </td>

                                {/* Safety Stock */}
                                <td className="px-4 py-3 text-right tabular-nums">
                                  <span className="text-sm text-slate-600">
                                    {risk.safety_stock.toLocaleString('es-CL')}
                                  </span>
                                </td>

                                {/* Units Needed */}
                                <td className="px-4 py-3 text-right">
                                  {risk.units_needed > 0 ? (
                                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-blue-50 text-blue-700 font-semibold text-sm">
                                      +{risk.units_needed.toLocaleString('es-CL')}
                                    </span>
                                  ) : (
                                    <span className="text-slate-400 text-sm">—</span>
                                  )}
                                </td>

                                {/* Risk Level */}
                                <td className="px-4 py-3 text-center">
                                  <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold tracking-wide ring-1 ring-inset ${getRiskBadge(risk.risk_level)}`}>
                                    {getRiskLabel(risk.risk_level)}
                                  </span>
                                </td>

                                {/* Forecasted Stockout Date */}
                                <td className="px-4 py-3 text-center">
                                  {risk.forecasted_stockout_date ? (
                                    <span className="text-sm text-slate-600">
                                      {new Date(risk.forecasted_stockout_date).toLocaleDateString('es-CL', {
                                        day: '2-digit',
                                        month: 'short'
                                      })}
                                    </span>
                                  ) : (
                                    <span className="text-slate-400 text-sm">—</span>
                                  )}
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>

                    {/* Table Footer */}
                    <div className="bg-slate-50 px-4 py-3 border-t border-slate-200">
                      <div className="flex items-center justify-between text-sm text-slate-600">
                        <span>
                          Mostrando <strong>{filteredRisks.length}</strong> de <strong>{risks.length}</strong> productos
                        </span>
                        <span className="flex items-center gap-4">
                          <span className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-red-600"></span>
                            {riskCounts.critical} criticos
                          </span>
                          <span className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                            {riskCounts.high} altos
                          </span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Sidebar - Top Lost Revenue */}
                <div className="xl:col-span-1">
                  <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm sticky top-6">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="p-2 bg-red-100 rounded-lg">
                        <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                        </svg>
                      </div>
                      <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">
                        Top Perdidas
                      </h3>
                    </div>

                    <div className="space-y-3">
                      {summary.top_products.map((product, index) => {
                        // Calculate bar width as percentage of max
                        const maxRevenue = summary.top_products[0]?.lost_revenue || 1;
                        const percentage = (product.lost_revenue / maxRevenue) * 100;

                        return (
                          <div key={product.sku} className="group">
                            <div className="flex items-start justify-between mb-1">
                              <div className="flex items-center gap-2 min-w-0">
                                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-100 text-slate-600 text-xs font-bold flex items-center justify-center">
                                  {index + 1}
                                </span>
                                <div className="min-w-0">
                                  <p className="text-xs font-mono text-slate-500 truncate" title={product.sku}>
                                    {product.sku}
                                  </p>
                                  <p className="text-sm font-medium text-slate-800 truncate" title={product.name}>
                                    {toTitleCase(product.name)}
                                  </p>
                                </div>
                              </div>
                            </div>
                            <div className="ml-7">
                              <div className="flex items-center justify-between text-xs mb-1">
                                <span className="text-slate-500">
                                  {product.stockout_count} stockouts
                                </span>
                                <span className="font-semibold text-red-600">
                                  {formatCurrencyFull(product.lost_revenue)}
                                </span>
                              </div>
                              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-red-500 to-red-400 rounded-full transition-all duration-500"
                                  style={{ width: `${percentage}%` }}
                                />
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Total */}
                    <div className="mt-6 pt-4 border-t border-slate-200">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500 uppercase">
                          Total Perdido
                        </span>
                        <span className="text-lg font-bold text-red-600">
                          {formatCurrencyFull(summary.total_lost_revenue)}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        En {summary.months_analyzed} meses analizados
                      </p>
                    </div>

                    {/* Investment Justification */}
                    <div className="mt-4 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                      <p className="text-xs font-semibold text-emerald-800 mb-1">
                        Justificacion de Inversion
                      </p>
                      <p className="text-xs text-emerald-700">
                        Si se previene el 50% de stockouts:
                      </p>
                      <p className="text-sm font-bold text-emerald-700 mt-1">
                        {formatCurrencyFull(summary.annualized_opportunity * 0.5)} / ano
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
