'use client';

import { ReactNode } from 'react';
import {
  Package,
  BarChart3,
  Boxes,
  DollarSign,
  Clock,
  AlertTriangle,
  XCircle,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';

interface EnhancedSummaryCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  trend?: {
    value: number;
    label: string;
    isPositive: boolean;
  };
  color?: 'blue' | 'green' | 'amber' | 'gray' | 'red' | 'purple' | 'teal';
  subtitle?: string;
}

// Map icon strings to Lucide components
const iconMap: Record<string, ReactNode> = {
  '📦': <Package className="w-4 h-4" />,
  '📊': <BarChart3 className="w-4 h-4" />,
  '💰': <DollarSign className="w-4 h-4" />,
  '🕒': <Clock className="w-4 h-4" />,
  '⏰': <AlertTriangle className="w-4 h-4" />,
  '❌': <XCircle className="w-4 h-4" />,
};

export default function EnhancedSummaryCard({
  title,
  value,
  icon,
  trend,
  color = 'blue',
  subtitle,
}: EnhancedSummaryCardProps) {
  // Convert emoji icons to Lucide components
  const resolvedIcon = typeof icon === 'string' && iconMap[icon] ? iconMap[icon] : icon;

  const colorClasses = {
    blue: {
      bg: 'bg-sky-50',
      icon: 'bg-sky-100 text-sky-600',
      text: 'text-sky-700',
      border: 'border-sky-200',
    },
    green: {
      bg: 'bg-emerald-50',
      icon: 'bg-emerald-100 text-emerald-600',
      text: 'text-emerald-700',
      border: 'border-emerald-200',
    },
    amber: {
      bg: 'bg-amber-50',
      icon: 'bg-amber-100 text-amber-600',
      text: 'text-amber-700',
      border: 'border-amber-200',
    },
    gray: {
      bg: 'bg-stone-50',
      icon: 'bg-stone-100 text-stone-600',
      text: 'text-stone-700',
      border: 'border-stone-200',
    },
    red: {
      bg: 'bg-red-50',
      icon: 'bg-red-100 text-red-600',
      text: 'text-red-700',
      border: 'border-red-200',
    },
    purple: {
      bg: 'bg-violet-50',
      icon: 'bg-violet-100 text-violet-600',
      text: 'text-violet-700',
      border: 'border-violet-200',
    },
    teal: {
      bg: 'bg-teal-50',
      icon: 'bg-teal-100 text-teal-600',
      text: 'text-teal-700',
      border: 'border-teal-200',
    },
  };

  const classes = colorClasses[color];

  return (
    <div
      className={`relative overflow-hidden rounded-xl border ${classes.border} ${classes.bg} p-3 transition-all duration-200 hover:shadow-sm group`}
    >
      <div className="relative z-10 flex items-center gap-3">
        {/* Icon */}
        <div
          className={`inline-flex items-center justify-center w-9 h-9 rounded-lg ${classes.icon} transition-transform duration-200 group-hover:scale-105 flex-shrink-0`}
        >
          {resolvedIcon}
        </div>

        <div className="flex-1 min-w-0">
          {/* Title */}
          <div className="text-[11px] font-medium text-[var(--foreground-muted)] uppercase tracking-wide mb-0.5 truncate">
            {title}
          </div>

          {/* Value */}
          <div className="flex items-baseline gap-1.5">
            <div className={`text-lg font-bold ${classes.text} truncate font-mono`}>
              {typeof value === 'number' ? value.toLocaleString() : value}
            </div>

            {/* Trend Badge */}
            {trend && (
              <div
                className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                  trend.isPositive
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-red-100 text-red-700'
                }`}
              >
                {trend.isPositive ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <TrendingDown className="w-3 h-3" />
                )}
                <span>{Math.abs(trend.value)}%</span>
              </div>
            )}
          </div>

          {/* Subtitle */}
          {(subtitle || trend?.label) && (
            <div className="text-[10px] text-[var(--foreground-muted)] truncate mt-0.5">
              {subtitle || trend?.label}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
