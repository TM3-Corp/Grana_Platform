import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

interface SourcePieChartProps {
  data: Array<{
    source: string
    revenue: number
  }>
}

const COLORS: Record<string, string> = {
  shopify: '#50E3C2',
  mercadolibre: '#F5A623',
  manual: '#7B68EE'
}

const NAMES: Record<string, string> = {
  shopify: 'Shopify',
  mercadolibre: 'MercadoLibre',
  manual: 'Manual'
}

export default function SourcePieChart({ data }: SourcePieChartProps) {
  const total = data.reduce((sum, item) => sum + item.revenue, 0)

  const chartData = data.map(item => ({
    name: NAMES[item.source as keyof typeof NAMES] || item.source,
    value: item.revenue,
    percentage: ((item.revenue / total) * 100).toFixed(1)
  }))

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        📊 Distribución por Fuente
      </h2>

      <ResponsiveContainer width="100%" height={350}>
        <PieChart margin={{ top: 30, right: 20, bottom: 20, left: 20 }}>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percentage }) => `${name}: ${percentage}%`}
            outerRadius={90}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => {
              const source = data[index].source
              return (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[source as keyof typeof COLORS] || '#888'}
                />
              )
            })}
          </Pie>
          <Tooltip
            formatter={(value: number) => `$${value.toLocaleString('es-CL')} CLP`}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Custom legend */}
      <div className="mt-4 space-y-2">
        {chartData.map((item, idx) => {
          const source = data[idx].source
          return (
            <div key={idx} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-4 h-4 rounded"
                  style={{ backgroundColor: COLORS[source as keyof typeof COLORS] }}
                />
                <span className="text-sm text-gray-700">{item.name}</span>
              </div>
              <span className="text-sm font-medium">
                ${(item.value / 1000000).toFixed(1)}M ({item.percentage}%)
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
