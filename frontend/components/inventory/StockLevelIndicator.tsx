'use client';

interface StockLevelIndicatorProps {
  current: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  variant?: 'bar' | 'circular' | 'pill';
}

export default function StockLevelIndicator({
  current,
  max,
  size = 'md',
  showLabel = true,
  variant = 'bar',
}: StockLevelIndicatorProps) {
  // Calculate percentage (if max provided, otherwise use arbitrary scale)
  const percentage = max ? (current / max) * 100 : Math.min((current / 100) * 100, 100);

  // Determine color based on stock level
  const getColorClasses = () => {
    if (current === 0) return 'bg-gray-200 text-gray-600';
    if (percentage >= 70) return 'bg-green-500 text-green-900';
    if (percentage >= 30) return 'bg-amber-500 text-amber-900';
    return 'bg-red-500 text-red-900';
  };

  const getBgColorClasses = () => {
    if (current === 0) return 'bg-gray-100';
    if (percentage >= 70) return 'bg-green-100';
    if (percentage >= 30) return 'bg-amber-100';
    return 'bg-red-100';
  };

  const getTextColorClasses = () => {
    if (current === 0) return 'text-gray-600';
    if (percentage >= 70) return 'text-green-700';
    if (percentage >= 30) return 'text-amber-700';
    return 'text-red-700';
  };

  const sizeClasses = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3',
  };

  if (variant === 'bar') {
    return (
      <div className="flex items-center gap-2 w-full">
        <div className={`flex-1 ${getBgColorClasses()} rounded-full overflow-hidden`}>
          <div
            className={`${getColorClasses()} ${sizeClasses[size]} rounded-full transition-all duration-500 ease-out`}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
        {showLabel && (
          <span className={`text-xs font-medium ${getTextColorClasses()} min-w-[3rem] text-right`}>
            {current.toLocaleString()}
          </span>
        )}
      </div>
    );
  }

  if (variant === 'circular') {
    const radius = size === 'sm' ? 16 : size === 'md' ? 20 : 24;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percentage / 100) * circumference;

    return (
      <div className="relative inline-flex items-center justify-center">
        <svg className="transform -rotate-90" width={radius * 2.5} height={radius * 2.5}>
          <circle
            cx={radius * 1.25}
            cy={radius * 1.25}
            r={radius}
            stroke="currentColor"
            strokeWidth="3"
            fill="none"
            className="text-gray-200"
          />
          <circle
            cx={radius * 1.25}
            cy={radius * 1.25}
            r={radius}
            stroke="currentColor"
            strokeWidth="3"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={`transition-all duration-500 ease-out ${
              current === 0
                ? 'text-gray-400'
                : percentage >= 70
                ? 'text-green-500'
                : percentage >= 30
                ? 'text-amber-500'
                : 'text-red-500'
            }`}
          />
        </svg>
        {showLabel && (
          <span
            className={`absolute text-xs font-semibold ${getTextColorClasses()}`}
            style={{ fontSize: size === 'sm' ? '0.625rem' : size === 'md' ? '0.75rem' : '0.875rem' }}
          >
            {current}
          </span>
        )}
      </div>
    );
  }

  // Pill variant
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${getBgColorClasses()} transition-all duration-200`}
    >
      <div className={`w-2 h-2 rounded-full ${getColorClasses()} animate-pulse`} />
      <span className={`text-xs font-semibold ${getTextColorClasses()}`}>{current.toLocaleString()}</span>
    </div>
  );
}
