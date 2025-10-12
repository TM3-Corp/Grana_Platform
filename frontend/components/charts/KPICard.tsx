interface KPICardProps {
  title: string
  value: string | number
  change?: number  // % change
  icon: string
  trend?: 'up' | 'down' | 'neutral'
}

export default function KPICard({
  title,
  value,
  change,
  icon,
  trend = 'neutral'
}: KPICardProps) {
  const trendColors = {
    up: 'text-green-600 bg-green-50',
    down: 'text-red-600 bg-red-50',
    neutral: 'text-gray-600 bg-gray-50'
  }

  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→'
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{icon}</span>
        {change !== undefined && (
          <span className={`text-sm px-2 py-1 rounded ${trendColors[trend]}`}>
            {trendIcons[trend]} {Math.abs(change).toFixed(1)}%
          </span>
        )}
      </div>

      <h3 className="text-sm text-gray-600 mb-1">{title}</h3>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </div>
  )
}
