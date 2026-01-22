import { DollarSign, Package, ShoppingCart, Receipt, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { type LucideIcon } from 'lucide-react'

interface SummaryMetrics {
  total_revenue: number
  total_units: number
  total_orders: number
  avg_ticket: number
  growth_rate?: number
}

interface KPICardsProps {
  data: SummaryMetrics | null
  loading?: boolean
}

interface CardConfig {
  title: string
  value: string
  icon: LucideIcon
  iconBg: string
  iconColor: string
  borderColor: string
  hoverBorder: string
}

export default function KPICards({ data, loading }: KPICardsProps) {
  const loadingColors = ['border-l-green-300', 'border-l-blue-300', 'border-l-purple-300', 'border-l-amber-300']

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className={`bg-white rounded-xl border border-gray-200 border-l-4 ${loadingColors[i]} p-5 animate-pulse`}>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-gray-200" />
              <div className="flex-1">
                <div className="h-3 bg-gray-200 rounded w-24 mb-2" />
                <div className="h-6 bg-gray-200 rounded w-32" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (!data) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-8">
        <p className="text-amber-700 text-sm">No hay datos disponibles para mostrar</p>
      </div>
    )
  }

  const formatCurrency = (value: number): string => {
    return `$${Math.round(value).toLocaleString('es-CL')}`
  }

  const formatNumber = (value: number): string => {
    return Math.round(value).toLocaleString('es-CL')
  }

  const cards: CardConfig[] = [
    {
      title: 'Ingresos Totales',
      value: formatCurrency(data.total_revenue),
      icon: DollarSign,
      iconBg: 'bg-gradient-to-br from-green-50 to-emerald-100',
      iconColor: 'text-green-600',
      borderColor: 'border-l-green-500',
      hoverBorder: 'hover:border-l-green-600',
    },
    {
      title: 'Unidades Vendidas',
      value: formatNumber(data.total_units),
      icon: Package,
      iconBg: 'bg-gradient-to-br from-blue-50 to-sky-100',
      iconColor: 'text-blue-600',
      borderColor: 'border-l-blue-500',
      hoverBorder: 'hover:border-l-blue-600',
    },
    {
      title: 'Órdenes Totales',
      value: formatNumber(data.total_orders),
      icon: ShoppingCart,
      iconBg: 'bg-gradient-to-br from-purple-50 to-violet-100',
      iconColor: 'text-purple-600',
      borderColor: 'border-l-purple-500',
      hoverBorder: 'hover:border-l-purple-600',
    },
    {
      title: 'Ticket Promedio',
      value: formatCurrency(data.avg_ticket),
      icon: Receipt,
      iconBg: 'bg-gradient-to-br from-amber-50 to-orange-100',
      iconColor: 'text-amber-600',
      borderColor: 'border-l-amber-500',
      hoverBorder: 'hover:border-l-amber-600',
    }
  ]

  const growthRate = data.growth_rate || 0
  const growthTrend = growthRate > 0 ? 'up' : growthRate < 0 ? 'down' : 'neutral'

  const TrendIcon = growthTrend === 'up' ? TrendingUp : growthTrend === 'down' ? TrendingDown : Minus

  const trendStyles = {
    up: 'text-green-600 bg-green-50',
    down: 'text-red-600 bg-red-50',
    neutral: 'text-gray-500 bg-gray-50',
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {cards.map((card, index) => {
        const IconComponent = card.icon
        return (
          <div
            key={index}
            className={`bg-white rounded-xl border border-gray-200 border-l-4 ${card.borderColor} ${card.hoverBorder} p-5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200`}
          >
            <div className="flex items-start gap-4">
              {/* Icon */}
              <div className={`w-12 h-12 rounded-lg ${card.iconBg} flex items-center justify-center flex-shrink-0`}>
                <IconComponent className={`w-6 h-6 ${card.iconColor}`} strokeWidth={1.75} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <h3 className="text-sm font-medium text-gray-500 truncate">
                    {card.title}
                  </h3>
                  {/* Growth indicator (only on first card) */}
                  {index === 0 && growthRate !== 0 && (
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${trendStyles[growthTrend]}`}>
                      <TrendIcon className="w-3 h-3" strokeWidth={2} />
                      {Math.abs(growthRate).toFixed(1)}%
                    </span>
                  )}
                </div>
                <p className="text-2xl font-semibold text-gray-900 truncate">
                  {card.value}
                </p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
