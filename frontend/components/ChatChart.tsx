'use client';

import { useMemo } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// ============================================================================
// CHAT CHART COMPONENT
// Renders charts from AI tool responses (get_chart_data, get_sales_forecast)
// ============================================================================

interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string[];
  borderColor?: string[];
}

interface ChartData {
  chart_type: 'line' | 'bar' | 'pie' | 'stacked_bar';
  title: string;
  subtitle?: string;
  data: {
    labels: string[];
    datasets: ChartDataset[];
  };
  summary?: {
    total: number;
    count: number;
    average: number;
    max: number;
    min: number;
    percentages?: Record<string, number>;
  };
  render_hint?: {
    type: string;
    show_legend: boolean;
    show_data_labels: boolean;
    x_axis_label?: string;
    y_axis_label?: string;
  };
}

interface ForecastData {
  year: number;
  historical_data: {
    monthly: Array<{
      month: number;
      month_name: string;
      revenue: number;
      units: number;
      orders: number;
    }>;
    summary: {
      total_revenue: number;
      total_units: number;
      total_orders: number;
      months_with_data: number;
    };
  };
  forecast: {
    methodology: string;
    base_monthly_revenue: number;
    trend_per_month: number;
    projected_year: number;
    monthly_forecast: Array<{
      month: number;
      month_name: string;
      projected_revenue: number;
      seasonality_factor: number;
    }>;
    summary: {
      projected_annual_revenue: number;
      average_monthly: number;
      growth_vs_base: number;
      confidence_level: string;
    };
  };
}

interface ChatChartProps {
  data: ChartData | ForecastData;
  compact?: boolean;
}

// Default colors
const COLORS = [
  '#4F46E5', // Indigo
  '#10B981', // Emerald
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#8B5CF6', // Violet
  '#06B6D4', // Cyan
  '#EC4899', // Pink
  '#84CC16', // Lime
  '#F97316', // Orange
  '#6366F1', // Indigo-lighter
];

// Type guard for ForecastData
function isForecastData(data: ChartData | ForecastData): data is ForecastData {
  return 'historical_data' in data && 'forecast' in data;
}

// Format number as Chilean currency
function formatCLP(value: number): string {
  if (value >= 1000000000) {
    return `$${(value / 1000000000).toFixed(1)}B`;
  }
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toLocaleString('es-CL')}`;
}

export default function ChatChart({ data, compact = false }: ChatChartProps) {
  // Handle forecast data
  if (isForecastData(data)) {
    return <ForecastChart data={data} compact={compact} />;
  }

  // Handle regular chart data
  return <StandardChart data={data} compact={compact} />;
}

// ============================================================================
// FORECAST CHART (for get_sales_forecast tool)
// ============================================================================

function ForecastChart({ data, compact }: { data: ForecastData; compact: boolean }) {
  const chartData = useMemo(() => {
    // Create a map of historical data by month number
    const historicalMap = new Map<number, { name: string; revenue: number }>();
    data.historical_data.monthly.forEach((m) => {
      historicalMap.set(m.month, {
        name: m.month_name.substring(0, 3),
        revenue: m.revenue,
      });
    });

    // Create a map of forecast data by month number
    const forecastMap = new Map<number, { name: string; projected_revenue: number }>();
    data.forecast.monthly_forecast.forEach((m) => {
      forecastMap.set(m.month, {
        name: m.month_name.substring(0, 3),
        projected_revenue: m.projected_revenue,
      });
    });

    // Merge both datasets by month (1-12)
    // X-axis shows months, with both historical and forecast as separate lines
    const merged: Array<{
      name: string;
      month: number;
      historical: number | null;
      forecast: number | null;
    }> = [];

    for (let month = 1; month <= 12; month++) {
      const hist = historicalMap.get(month);
      const fore = forecastMap.get(month);

      // Get month name from whichever source has it
      const monthName = hist?.name || fore?.name || '';

      merged.push({
        name: monthName,
        month,
        historical: hist?.revenue ?? null,
        forecast: fore?.projected_revenue ?? null,
      });
    }

    return merged;
  }, [data]);

  const height = compact ? 200 : 280;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="mb-2">
        <h4 className="text-sm font-semibold text-gray-800">
          Proyección de Ventas {data.forecast.projected_year}
        </h4>
        <p className="text-xs text-gray-500">
          Basado en {data.year} · {data.forecast.methodology}
        </p>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10 }}
            axisLine={{ stroke: '#E5E7EB' }}
          />
          <YAxis
            tick={{ fontSize: 10 }}
            tickFormatter={formatCLP}
            width={55}
            axisLine={{ stroke: '#E5E7EB' }}
          />
          <Tooltip
            formatter={(value: number) => [formatCLP(value), '']}
            labelStyle={{ fontSize: 11 }}
            contentStyle={{ fontSize: 11 }}
          />
          <Legend wrapperStyle={{ fontSize: 10 }} />
          <Line
            type="monotone"
            dataKey="historical"
            stroke="#10B981"
            strokeWidth={2}
            name={`${data.year} Real`}
            dot={{ r: 3 }}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#8B5CF6"
            strokeWidth={2}
            strokeDasharray="5 5"
            name={`${data.forecast.projected_year} Proyectado`}
            dot={{ r: 3 }}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Summary stats */}
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
        <div className="bg-emerald-50 rounded p-2">
          <span className="text-gray-500">Real {data.year}:</span>
          <span className="ml-1 font-semibold text-emerald-700">
            {formatCLP(data.historical_data.summary.total_revenue)}
          </span>
        </div>
        <div className="bg-violet-50 rounded p-2">
          <span className="text-gray-500">Proyección {data.forecast.projected_year}:</span>
          <span className="ml-1 font-semibold text-violet-700">
            {formatCLP(data.forecast.summary.projected_annual_revenue)}
          </span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// STANDARD CHART (for get_chart_data tool)
// ============================================================================

function StandardChart({ data, compact }: { data: ChartData; compact: boolean }) {
  const chartType = data.chart_type || data.render_hint?.type || 'bar';
  const height = compact ? 200 : 260;

  // Transform data for Recharts
  const chartData = useMemo(() => {
    const { labels, datasets } = data.data;
    return labels.map((label, i) => ({
      name: label.length > 15 ? label.substring(0, 15) + '...' : label,
      fullName: label,
      value: datasets[0]?.data[i] || 0,
      color: datasets[0]?.backgroundColor?.[i] || COLORS[i % COLORS.length],
    }));
  }, [data]);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="mb-2">
        <h4 className="text-sm font-semibold text-gray-800">{data.title}</h4>
        {data.subtitle && (
          <p className="text-xs text-gray-500">{data.subtitle}</p>
        )}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        {chartType === 'pie' ? (
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={compact ? 60 : 80}
              label={({ name, percent }) =>
                compact ? '' : `${name}: ${(percent * 100).toFixed(0)}%`
              }
              labelLine={!compact}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [formatCLP(value), '']}
              contentStyle={{ fontSize: 11 }}
            />
            <Legend wrapperStyle={{ fontSize: 10 }} />
          </PieChart>
        ) : chartType === 'line' ? (
          <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              axisLine={{ stroke: '#E5E7EB' }}
            />
            <YAxis
              tick={{ fontSize: 10 }}
              tickFormatter={formatCLP}
              width={55}
              axisLine={{ stroke: '#E5E7EB' }}
            />
            <Tooltip
              formatter={(value: number) => [formatCLP(value), '']}
              contentStyle={{ fontSize: 11 }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#10B981"
              strokeWidth={2}
              dot={{ r: 3, fill: '#10B981' }}
              name={data.data.datasets[0]?.label || 'Valor'}
            />
          </LineChart>
        ) : (
          <BarChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 9 }}
              axisLine={{ stroke: '#E5E7EB' }}
              interval={0}
              angle={-30}
              textAnchor="end"
              height={50}
            />
            <YAxis
              tick={{ fontSize: 10 }}
              tickFormatter={formatCLP}
              width={55}
              axisLine={{ stroke: '#E5E7EB' }}
            />
            <Tooltip
              formatter={(value: number) => [formatCLP(value), '']}
              contentStyle={{ fontSize: 11 }}
            />
            <Bar dataKey="value" name={data.data.datasets[0]?.label || 'Valor'}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>

      {/* Summary stats */}
      {data.summary && (
        <div className="mt-2 flex flex-wrap gap-2 text-xs">
          <div className="bg-gray-50 rounded px-2 py-1">
            <span className="text-gray-500">Total:</span>
            <span className="ml-1 font-semibold">{formatCLP(data.summary.total)}</span>
          </div>
          {data.summary.count > 1 && (
            <div className="bg-gray-50 rounded px-2 py-1">
              <span className="text-gray-500">Promedio:</span>
              <span className="ml-1 font-semibold">{formatCLP(data.summary.average)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// UTILITY: Parse chart data from message content
// ============================================================================

export function parseChartDataFromMessage(content: string): (ChartData | ForecastData)[] {
  const charts: (ChartData | ForecastData)[] = [];

  // Pattern 1: Look for ```json blocks containing chart data
  const jsonBlockRegex = /```(?:json)?\s*\n?([\s\S]*?)\n?```/g;
  let match;

  while ((match = jsonBlockRegex.exec(content)) !== null) {
    try {
      const parsed = JSON.parse(match[1]);
      // Check if it's chart data
      if (parsed.chart_type && parsed.data?.labels) {
        charts.push(parsed as ChartData);
      }
      // Check if it's forecast data
      if (parsed.historical_data && parsed.forecast) {
        charts.push(parsed as ForecastData);
      }
    } catch {
      // Not valid JSON, skip
    }
  }

  // Pattern 2: Look for inline JSON objects with chart data signatures
  // Match JSON starting with {"chart_type": or {"historical_data":
  const inlineChartRegex = /\{["\s]*(?:chart_type|historical_data)["\s]*:[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g;

  while ((match = inlineChartRegex.exec(content)) !== null) {
    try {
      const parsed = JSON.parse(match[0]);
      if ((parsed.chart_type && parsed.data?.labels) || (parsed.historical_data && parsed.forecast)) {
        // Avoid duplicates
        const isDuplicate = charts.some(
          (c) => JSON.stringify(c) === JSON.stringify(parsed)
        );
        if (!isDuplicate) {
          charts.push(parsed);
        }
      }
    } catch {
      // Not valid JSON, skip
    }
  }

  return charts;
}

// ============================================================================
// UTILITY: Remove chart JSON from message content for cleaner display
// ============================================================================

export function removeChartDataFromMessage(content: string): string {
  // Remove ```json blocks containing chart data
  let cleaned = content.replace(/```(?:json)?\s*\n?\{[\s\S]*?"chart_type"[\s\S]*?\}\n?```/g, '');
  cleaned = cleaned.replace(/```(?:json)?\s*\n?\{[\s\S]*?"historical_data"[\s\S]*?\}\n?```/g, '');

  // Clean up extra whitespace
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

  return cleaned;
}
