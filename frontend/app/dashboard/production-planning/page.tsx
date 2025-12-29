'use client';

import { useState, useEffect } from 'react';
import { toTitleCase } from '@/lib/utils';
import Navigation from '@/components/Navigation';

interface ProductionProduct {
  sku: string;
  name: string;
  category: string | null;
  stock_total: number;
  estimation_months: number;
  avg_monthly_sales: number;
  stock_usable: number;
  stock_expiring_30d: number;
  stock_expired: number;
  earliest_expiration: string | null;
  days_to_earliest_expiration: number | null;
  days_of_coverage: number;
  production_needed: number;
  urgency: 'critical' | 'high' | 'medium' | 'low';
}

interface ProductionSummary {
  products_needing_production: number;
  total_units_needed: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  expiring_units: number;
}

interface ProductionData {
  status: string;
  summary: ProductionSummary;
  count: number;
  data: ProductionProduct[];
}

export default function ProductionPlanningPage() {
  const [data, setData] = useState<ProductionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [urgencyFilter, setUrgencyFilter] = useState<string>('');
  const [onlyNeedingProduction, setOnlyNeedingProduction] = useState(true);

  // Categories for filter dropdown
  const [categories, setCategories] = useState<string[]>([]);

  // Fetch categories on mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/v1/inventory-planning/categories`);
        if (response.ok) {
          const result = await response.json();
          setCategories(result.data || []);
        }
      } catch (err) {
        console.error('Error fetching categories:', err);
      }
    };
    fetchCategories();
  }, []);

  // Fetch production recommendations
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const params = new URLSearchParams();

      if (categoryFilter) params.append('category', categoryFilter);
      if (urgencyFilter) params.append('urgency', urgencyFilter);
      params.append('only_needing_production', onlyNeedingProduction.toString());
      params.append('limit', '200');

      const response = await fetch(`${apiUrl}/api/v1/inventory-planning/production-recommendations?${params}`);

      if (!response.ok) {
        throw new Error('Failed to fetch production recommendations');
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [categoryFilter, urgencyFilter, onlyNeedingProduction]);

  // Urgency badge styles
  const getUrgencyBadge = (urgency: string) => {
    switch (urgency) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getUrgencyLabel = (urgency: string) => {
    switch (urgency) {
      case 'critical':
        return 'Crítico';
      case 'high':
        return 'Alto';
      case 'medium':
        return 'Medio';
      case 'low':
        return 'Bajo';
      default:
        return urgency;
    }
  };

  // Coverage color
  const getCoverageColor = (days: number) => {
    if (days < 15) return 'text-red-700 bg-red-100';
    if (days < 30) return 'text-amber-700 bg-amber-100';
    return 'text-green-700 bg-green-100';
  };

  return (
    <>
      <Navigation />
      <div className="p-6 max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Planificación de Producción</h1>
          <p className="text-gray-600 mt-2">
            Recomendaciones de producción basadas en ventas proyectadas y niveles de inventario
          </p>
        </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {/* Products to Produce */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Productos a Producir</p>
                <p className="text-3xl font-bold text-blue-600 mt-1">
                  {data.summary.products_needing_production}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
            </div>
          </div>

          {/* Total Units Needed */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Unidades Totales</p>
                <p className="text-3xl font-bold text-indigo-600 mt-1">
                  {data.summary.total_units_needed.toLocaleString('es-CL')}
                </p>
              </div>
              <div className="p-3 bg-indigo-100 rounded-lg">
                <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </div>
            </div>
          </div>

          {/* Critical + High Count */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Urgentes ({"<"}30d)</p>
                <p className="text-3xl font-bold text-red-600 mt-1">
                  {data.summary.critical_count + data.summary.high_count}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {data.summary.critical_count} críticos, {data.summary.high_count} altos
                </p>
              </div>
              <div className="p-3 bg-red-100 rounded-lg">
                <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Expiring Stock */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Stock Venciendo</p>
                <p className="text-3xl font-bold text-amber-600 mt-1">
                  {data.summary.expiring_units.toLocaleString('es-CL')}
                </p>
                <p className="text-xs text-gray-500 mt-1">próximos 30 días</p>
              </div>
              <div className="p-3 bg-amber-100 rounded-lg">
                <svg className="w-6 h-6 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Categoría:</label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Todas</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>{toTitleCase(cat)}</option>
              ))}
            </select>
          </div>

          {/* Urgency Filter */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Urgencia:</label>
            <select
              value={urgencyFilter}
              onChange={(e) => setUrgencyFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Todas</option>
              <option value="critical">Crítico ({"<"}15d)</option>
              <option value="high">Alto (15-30d)</option>
              <option value="medium">Medio (30-60d)</option>
              <option value="low">Bajo ({">"}60d)</option>
            </select>
          </div>

          {/* Only Needing Production Toggle */}
          <div className="flex items-center gap-2">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={onlyNeedingProduction}
                onChange={(e) => setOnlyNeedingProduction(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              <span className="ml-2 text-sm font-medium text-gray-700">Solo con producción pendiente</span>
            </label>
          </div>

          {/* Refresh Button */}
          <button
            onClick={fetchData}
            disabled={loading}
            className="ml-auto px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Actualizar
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 text-red-800">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="font-medium">Error: {error}</span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 flex flex-col items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mb-4"></div>
          <p className="text-gray-600 font-medium">Cargando recomendaciones...</p>
        </div>
      )}

      {/* Products Table */}
      {!loading && data && data.data.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    Producto
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    Stock Usable
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    Ventas/Mes
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    Cobertura
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    Vence
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    Estado
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    Producir
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wide">
                    Urgencia
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {data.data.map((product) => (
                  <tr key={product.sku} className="hover:bg-gray-50 transition-colors">
                    {/* Product Info */}
                    <td className="px-4 py-3 min-w-[280px]">
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-2">
                          <code className="text-xs font-mono font-medium text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                            {product.sku}
                          </code>
                          {product.category && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                              {toTitleCase(product.category)}
                            </span>
                          )}
                        </div>
                        <span className="text-sm font-medium text-gray-900">
                          {toTitleCase(product.name)}
                        </span>
                        <span className="text-xs text-gray-500">
                          Estimación: {product.estimation_months === 1 ? 'Último mes' : `Últimos ${product.estimation_months} meses`}
                        </span>
                      </div>
                    </td>

                    {/* Stock Usable */}
                    <td className="px-4 py-3 text-right tabular-nums">
                      <span className="text-sm font-semibold text-gray-900">
                        {product.stock_usable.toLocaleString('es-CL')}
                      </span>
                    </td>

                    {/* Avg Monthly Sales */}
                    <td className="px-4 py-3 text-right tabular-nums">
                      <span className="text-sm text-gray-700">
                        {product.avg_monthly_sales.toLocaleString('es-CL')}
                      </span>
                    </td>

                    {/* Days of Coverage */}
                    <td className="px-4 py-3 text-center">
                      {product.days_of_coverage < 999 ? (
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-sm font-semibold ${getCoverageColor(product.days_of_coverage)}`}>
                          {product.days_of_coverage}d
                        </span>
                      ) : (
                        <span className="text-gray-400 text-sm">—</span>
                      )}
                    </td>

                    {/* Earliest Expiration (Vence) - DD/MM/YYYY format */}
                    <td className="px-4 py-3 text-center">
                      {product.earliest_expiration ? (
                        <div className="flex flex-col items-center">
                          <span className={`text-sm font-medium ${
                            (product.days_to_earliest_expiration ?? 999) < 30
                              ? 'text-red-700'
                              : (product.days_to_earliest_expiration ?? 999) < 60
                              ? 'text-amber-700'
                              : 'text-gray-700'
                          }`}>
                            {new Date(product.earliest_expiration).toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                          </span>
                          <span className="text-xs text-gray-500">
                            ({product.days_to_earliest_expiration}d)
                          </span>
                        </div>
                      ) : (
                        <span className="text-gray-400 text-sm">—</span>
                      )}
                    </td>

                    {/* Stock Status (Estado) */}
                    <td className="px-4 py-3 text-center">
                      {(() => {
                        const coverage = product.days_of_coverage || 999;
                        const daysToExp = product.days_to_earliest_expiration;

                        if (!daysToExp || coverage >= 999) {
                          return <span className="text-gray-400 text-sm">—</span>;
                        }

                        if (coverage > daysToExp) {
                          return (
                            <span
                              className="inline-flex items-center px-2 py-1 rounded-lg bg-red-100 text-red-800 text-xs font-semibold"
                              title={`Stock excede vencimiento por ${coverage - daysToExp} días`}
                            >
                              <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                              </svg>
                              Exceso
                            </span>
                          );
                        }

                        if (coverage >= daysToExp * 0.8) {
                          return (
                            <span
                              className="inline-flex items-center px-2 py-1 rounded-lg bg-amber-100 text-amber-800 text-xs font-semibold"
                              title={`Margen de ${daysToExp - coverage} días antes del vencimiento`}
                            >
                              <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              Ajustado
                            </span>
                          );
                        }

                        return (
                          <span
                            className="inline-flex items-center px-2 py-1 rounded-lg bg-green-100 text-green-800 text-xs font-semibold"
                            title={`Margen de ${daysToExp - coverage} días antes del vencimiento`}
                          >
                            <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            OK
                          </span>
                        );
                      })()}
                    </td>

                    {/* Production Needed */}
                    <td className="px-4 py-3 text-right">
                      {product.production_needed > 0 ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-100 text-blue-800 font-semibold text-sm">
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                          </svg>
                          {product.production_needed.toLocaleString('es-CL')}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-sm">—</span>
                      )}
                    </td>

                    {/* Urgency Badge */}
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${getUrgencyBadge(product.urgency)}`}>
                        {getUrgencyLabel(product.urgency)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Table Footer */}
          <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <span>
                Mostrando <strong>{data.count}</strong> productos
              </span>
              <span>
                Total a producir: <strong className="text-blue-600">{data.summary.total_units_needed.toLocaleString('es-CL')} unidades</strong>
              </span>
            </div>
          </div>
        </div>
      )}

        {/* Empty State */}
        {!loading && data && data.data.length === 0 && (
          <div className="bg-white rounded-xl border-2 border-dashed border-gray-300 p-12 text-center">
            <div className="text-6xl mb-4">✅</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {onlyNeedingProduction ? 'No hay productos que necesiten producción' : 'No se encontraron productos'}
            </h3>
            <p className="text-gray-600">
              {onlyNeedingProduction
                ? 'Todos los productos tienen stock suficiente según las proyecciones actuales.'
                : 'Intenta ajustar los filtros para ver más resultados.'}
            </p>
          </div>
        )}
      </div>
    </>
  );
}
