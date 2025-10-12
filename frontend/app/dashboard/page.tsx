'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import KPICard from '@/components/charts/KPICard'
import SalesLineChart from '@/components/charts/SalesLineChart'
import SourcePieChart from '@/components/charts/SourcePieChart'
import TopProductsBar from '@/components/charts/TopProductsBar'

interface AnalyticsData {
  sales_by_period: any[]
  source_distribution: any[]
  top_products: any[]
  kpis: {
    total_orders: number
    total_revenue: number
    avg_ticket: number
  }
  growth_rates: any[]
}

export default function DashboardPage() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL
        const response = await fetch(`${apiUrl}/api/v1/orders/analytics?group_by=month`)

        if (!response.ok) throw new Error('Error fetching analytics')

        const result = await response.json()
        setData(result.data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando dashboard...</p>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-800 font-semibold text-lg mb-2">Error</h2>
          <p className="text-red-600">{error || 'No se pudieron cargar los datos'}</p>
        </div>
      </div>
    )
  }

  // Calculate average growth
  const avgGrowth = data.growth_rates.length > 0
    ? data.growth_rates.reduce((sum: number, g: any) => sum + g.growth_rate, 0) / data.growth_rates.length
    : 0

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                🍃 Dashboard Grana 2025
              </h1>
              <p className="mt-2 text-gray-600">
                Vista general de ventas, productos y tendencias
              </p>
            </div>
            <Link
              href="/"
              className="text-gray-600 hover:text-gray-900 transition"
            >
              ← Volver
            </Link>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <KPICard
            icon="💰"
            title="Ingresos Totales"
            value={`$${(data.kpis.total_revenue / 1000000).toFixed(1)}M CLP`}
            change={avgGrowth}
            trend={avgGrowth > 0 ? 'up' : avgGrowth < 0 ? 'down' : 'neutral'}
          />

          <KPICard
            icon="📦"
            title="Total Órdenes"
            value={data.kpis.total_orders.toLocaleString('es-CL')}
          />

          <KPICard
            icon="🎫"
            title="Ticket Promedio"
            value={`$${Math.round(data.kpis.avg_ticket).toLocaleString('es-CL')}`}
          />
        </div>

        {/* Main Chart - Sales Line */}
        <div className="mb-8">
          <SalesLineChart data={data.sales_by_period} />
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <SourcePieChart data={data.source_distribution} />
          <TopProductsBar data={data.top_products} />
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Acciones Rápidas
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              href="/dashboard/orders"
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
            >
              <span className="text-2xl">📦</span>
              <div>
                <div className="font-medium">Ver Órdenes</div>
                <div className="text-sm text-gray-600">
                  {data.kpis.total_orders} órdenes
                </div>
              </div>
            </Link>

            <Link
              href="/dashboard/products"
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
            >
              <span className="text-2xl">🏷️</span>
              <div>
                <div className="font-medium">Ver Productos</div>
                <div className="text-sm text-gray-600">
                  Gestionar inventario
                </div>
              </div>
            </Link>

            <button
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
              onClick={() => window.location.reload()}
            >
              <span className="text-2xl">🔄</span>
              <div>
                <div className="font-medium">Actualizar</div>
                <div className="text-sm text-gray-600">
                  Recargar datos
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* API Info */}
        <div className="mt-8 bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-800">
            <span className="font-semibold">✅ Conectado a:</span> {process.env.NEXT_PUBLIC_API_URL}
          </p>
        </div>
      </div>
    </div>
  )
}
