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

export default function KPICards({ data, loading }: KPICardsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="rounded-2xl bg-gray-200 animate-pulse h-32" />
        ))}
      </div>
    )
  }

  if (!data) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-10">
        <p className="text-yellow-800">No hay datos disponibles para mostrar</p>
      </div>
    )
  }

  const formatCurrency = (value: number): string => {
    return `$${Math.round(value).toLocaleString('es-CL')}`
  }

  const formatNumber = (value: number): string => {
    return Math.round(value).toLocaleString('es-CL')
  }

  const cards = [
    {
      title: 'Ingresos Totales',
      value: formatCurrency(data.total_revenue),
      icon: '💰',
      gradient: 'from-green-500 to-green-600',
      hoverGradient: 'hover:from-green-600 hover:to-green-700'
    },
    {
      title: 'Unidades Vendidas',
      value: formatNumber(data.total_units),
      icon: '📊',
      gradient: 'from-blue-500 to-blue-600',
      hoverGradient: 'hover:from-blue-600 hover:to-blue-700'
    },
    {
      title: 'Órdenes Totales',
      value: formatNumber(data.total_orders),
      icon: '📦',
      gradient: 'from-purple-500 to-purple-600',
      hoverGradient: 'hover:from-purple-600 hover:to-purple-700'
    },
    {
      title: 'Ticket Promedio',
      value: formatCurrency(data.avg_ticket),
      icon: '🎫',
      gradient: 'from-orange-500 to-orange-600',
      hoverGradient: 'hover:from-orange-600 hover:to-orange-700'
    }
  ]

  const growthRate = data.growth_rate || 0
  const growthTrend = growthRate > 0 ? 'up' : growthRate < 0 ? 'down' : 'neutral'
  const growthIcon = growthTrend === 'up' ? '↑' : growthTrend === 'down' ? '↓' : '→'
  const growthColor = growthTrend === 'up'
    ? 'text-green-200'
    : growthTrend === 'down'
    ? 'text-red-200'
    : 'text-gray-200'

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
      {cards.map((card, index) => (
        <div
          key={index}
          className={`
            bg-gradient-to-br ${card.gradient} ${card.hoverGradient}
            rounded-2xl shadow-lg hover:shadow-xl
            transform hover:scale-105
            transition-all duration-300
            p-6
            text-white
          `}
        >
          {/* Icon and Growth (only show growth on first card) */}
          <div className="flex items-center justify-between mb-3">
            <span className="text-4xl">{card.icon}</span>
            {index === 0 && growthRate !== 0 && (
              <span className={`text-sm font-semibold ${growthColor}`}>
                {growthIcon} {Math.abs(growthRate).toFixed(1)}%
              </span>
            )}
          </div>

          {/* Title */}
          <h3 className="text-sm font-medium text-white/90 mb-2">
            {card.title}
          </h3>

          {/* Value */}
          <p className="text-3xl font-bold">
            {card.value}
          </p>
        </div>
      ))}
    </div>
  )
}
