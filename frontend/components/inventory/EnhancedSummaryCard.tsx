'use client';

import { ReactNode } from 'react';

interface EnhancedSummaryCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  trend?: {
    value: number;
    label: string;
    isPositive: boolean;
  };
  color?: 'blue' | 'green' | 'amber' | 'gray' | 'red' | 'purple';
  subtitle?: string;
}

export default function EnhancedSummaryCard({
  title,
  value,
  icon,
  trend,
  color = 'blue',
  subtitle,
}: EnhancedSummaryCardProps) {
  const colorClasses = {
    blue: {
      bg: 'bg-blue-50',
      icon: 'bg-blue-100 text-blue-600',
      text: 'text-blue-600',
      border: 'border-blue-200',
    },
    green: {
      bg: 'bg-green-50',
      icon: 'bg-green-100 text-green-600',
      text: 'text-green-600',
      border: 'border-green-200',
    },
    amber: {
      bg: 'bg-amber-50',
      icon: 'bg-amber-100 text-amber-600',
      text: 'text-amber-600',
      border: 'border-amber-200',
    },
    gray: {
      bg: 'bg-gray-50',
      icon: 'bg-gray-100 text-gray-600',
      text: 'text-gray-600',
      border: 'border-gray-200',
    },
    red: {
      bg: 'bg-red-50',
      icon: 'bg-red-100 text-red-600',
      text: 'text-red-600',
      border: 'border-red-200',
    },
    purple: {
      bg: 'bg-purple-50',
      icon: 'bg-purple-100 text-purple-600',
      text: 'text-purple-600',
      border: 'border-purple-200',
    },
  };

  const classes = colorClasses[color];

  return (
    <div
      className={`relative overflow-hidden rounded-lg border ${classes.border} ${classes.bg} p-3 transition-all duration-300 hover:shadow-md group`}
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-16 h-16 transform translate-x-4 -translate-y-4 opacity-10">
        <div className={`w-full h-full rounded-full ${classes.icon}`} />
      </div>

      <div className="relative z-10 flex items-center gap-3">
        {/* Icon */}
        <div
          className={`inline-flex items-center justify-center w-8 h-8 rounded-md ${classes.icon} transition-transform duration-300 group-hover:scale-110 flex-shrink-0`}
        >
          <div className="text-lg">{icon}</div>
        </div>

        <div className="flex-1 min-w-0">
          {/* Title */}
          <div className="text-xs font-medium text-gray-600 mb-0.5 truncate">{title}</div>

          {/* Value */}
          <div className="flex items-baseline gap-1.5">
            <div className={`text-xl font-bold ${classes.text} truncate`}>
              {typeof value === 'number' ? value.toLocaleString() : value}
            </div>

            {/* Trend Badge */}
            {trend && (
              <div
                className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs font-medium ${
                  trend.isPositive
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700'
                }`}
              >
                <span>{trend.isPositive ? '↑' : '↓'}</span>
                <span>{Math.abs(trend.value)}%</span>
              </div>
            )}
          </div>

          {/* Subtitle or Trend Label */}
          {(subtitle || trend?.label) && (
            <div className="text-xs text-gray-500 truncate">{subtitle || trend?.label}</div>
          )}
        </div>
      </div>

      {/* Shine effect on hover */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-10 transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-all duration-700" />
    </div>
  );
}
