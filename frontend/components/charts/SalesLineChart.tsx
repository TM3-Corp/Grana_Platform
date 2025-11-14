import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface SalesLineChartProps {
  data: Array<{
    period: string
    shopify_revenue?: number
    mercadolibre_revenue?: number
    manual_revenue?: number
    total_revenue: number
  }>
}

export default function SalesLineChart({ data }: SalesLineChartProps) {
  // Format data for Spanish locale
  const formattedData = data.map(d => {
    // Check if period is daily (YYYY-MM-DD) or monthly (YYYY-MM)
    const isDaily = d.period.length === 10;
    const dateStr = isDaily ? d.period : d.period + '-01';
    const date = new Date(dateStr);

    const label = isDaily
      ? date.toLocaleDateString('es-CL', { day: 'numeric', month: 'short' })
      : date.toLocaleDateString('es-CL', { month: 'short', year: '2-digit' });

    return {
      ...d,
      mes: label
    };
  })

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        📈 Ventas por Mes (2025)
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="mes" />
          <YAxis
            tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
          />
          <Tooltip
            formatter={(value: number) => `$${value.toLocaleString('es-CL')} CLP`}
            labelStyle={{ color: '#000' }}
          />
          <Legend />

          <Line
            type="monotone"
            dataKey="total_revenue"
            stroke="#10B981"
            strokeWidth={3}
            name="Total"
            dot={{ r: 5 }}
          />
          <Line
            type="monotone"
            dataKey="shopify_revenue"
            stroke="#50E3C2"
            strokeWidth={2}
            name="Shopify"
            dot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="mercadolibre_revenue"
            stroke="#F5A623"
            strokeWidth={2}
            name="MercadoLibre"
            dot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
