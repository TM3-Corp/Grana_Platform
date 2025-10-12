import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface TopProductsBarProps {
  data: Array<{
    name: string
    revenue: number
    units_sold: number
  }>
}

export default function TopProductsBar({ data }: TopProductsBarProps) {
  // Format names (truncate if too long)
  const formattedData = data.map(item => ({
    ...item,
    shortName: item.name.length > 30 ? item.name.substring(0, 27) + '...' : item.name
  }))

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        🏆 Top 5 Productos
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={formattedData} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            type="number"
            tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
          />
          <YAxis
            type="category"
            dataKey="shortName"
            width={150}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === 'revenue') return [`$${value.toLocaleString('es-CL')} CLP`, 'Ingresos']
              return [value, 'Unidades']
            }}
          />
          <Bar dataKey="revenue" fill="#10B981" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
