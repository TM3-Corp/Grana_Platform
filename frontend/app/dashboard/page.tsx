'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Navigation from '@/components/Navigation'
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
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app'
        const fullUrl = `${apiUrl}/api/v1/orders/analytics?group_by=month`

        const response = await fetch(fullUrl)

        if (!response.ok) {
          throw new Error(`Error fetching analytics (${response.status})`)
        }

        const result = await response.json()
        setData(result.data)
      } catch (err) {
        console.error('Error:', err)
        setError(err instanceof Error ? err.message : 'Error desconocido')
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [])

  if (loading) {
    return (
      <>
        <Navigation />
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Cargando dashboard...</p>
          </div>
        </div>
      </>
    )
  }

  if (error || !data) {
    return (
      <>
        <Navigation />
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-red-800 font-semibold text-lg mb-2">Error</h2>
            <p className="text-red-600">{error || 'No se pudieron cargar los datos'}</p>
          </div>
        </div>
      </>
    )
  }

  // Calculate average growth
  const avgGrowth = data.growth_rates.length > 0
    ? data.growth_rates.reduce((sum: number, g: any) => sum + g.growth_rate, 0) / data.growth_rates.length
    : 0

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header with Refresh */}
          <div className="mb-8 flex justify-between items-center">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                Dashboard General
              </h1>
              <p className="text-lg text-gray-600">
                Vista consolidada de ventas, productos y tendencias 2025
              </p>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-2 px-6 py-3 bg-white hover:bg-gray-50 border border-gray-200 rounded-xl transition-all shadow-sm hover:shadow-md"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span className="font-medium text-gray-900">Actualizar</span>
            </button>
          </div>

          {/* KPI Cards - Enhanced Design */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all transform hover:scale-105">
              <div className="flex items-center justify-between mb-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <span className="text-3xl">💰</span>
                </div>
                {avgGrowth !== 0 && (
                  <div className={`flex items-center gap-1 px-3 py-1 rounded-full ${
                    avgGrowth > 0 ? 'bg-green-400/30' : 'bg-red-400/30'
                  }`}>
                    <svg className={`w-4 h-4 ${avgGrowth > 0 ? '' : 'transform rotate-180'}`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L6.707 7.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm font-medium">{avgGrowth.toFixed(1)}%</span>
                  </div>
                )}
              </div>
              <div className="text-sm opacity-90 mb-1">Ingresos Totales</div>
              <div className="text-3xl font-bold">${(data.kpis.total_revenue / 1000000).toFixed(1)}M</div>
              <div className="text-xs opacity-75 mt-1">CLP en 2025</div>
            </div>

            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all transform hover:scale-105">
              <div className="flex items-center justify-between mb-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <span className="text-3xl">📦</span>
                </div>
              </div>
              <div className="text-sm opacity-90 mb-1">Total Órdenes</div>
              <div className="text-3xl font-bold">{data.kpis.total_orders.toLocaleString('es-CL')}</div>
              <div className="text-xs opacity-75 mt-1">Pedidos procesados</div>
            </div>

            <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl p-6 text-white shadow-lg hover:shadow-xl transition-all transform hover:scale-105">
              <div className="flex items-center justify-between mb-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <span className="text-3xl">🎫</span>
                </div>
              </div>
              <div className="text-sm opacity-90 mb-1">Ticket Promedio</div>
              <div className="text-3xl font-bold">${(data.kpis.avg_ticket / 1000).toFixed(0)}k</div>
              <div className="text-xs opacity-75 mt-1">CLP por orden</div>
            </div>
          </div>

          {/* Main Chart - Sales Line - Full Width */}
          <div className="mb-10">
            <SalesLineChart data={data.sales_by_period} />
          </div>

          {/* Two-column Charts Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <SourcePieChart data={data.source_distribution} />
            <TopProductsBar data={data.top_products} />
          </div>
        </div>
      </div>
    </>
  )
}
