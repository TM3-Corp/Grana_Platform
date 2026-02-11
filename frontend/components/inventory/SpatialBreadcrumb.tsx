'use client';

import { ArrowLeft, ChevronRight } from 'lucide-react';
import type { Breadcrumb, ZoomLevel } from '@/lib/use-spatial-zoom';

interface SpatialBreadcrumbProps {
  breadcrumbs: Breadcrumb[];
  currentLevel: ZoomLevel;
  onBack: () => void;
  onNavigate: (level: ZoomLevel) => void;
}

export default function SpatialBreadcrumb({
  breadcrumbs,
  currentLevel,
  onBack,
  onNavigate,
}: SpatialBreadcrumbProps) {
  if (currentLevel === 0) return null;

  return (
    <div className="flex items-center gap-3 mb-4">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-[var(--foreground-muted)] bg-[var(--surface)] border border-[var(--border)] rounded-lg hover:border-[var(--border-subtle)] hover:text-[var(--foreground)] transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Volver
      </button>

      <nav className="flex items-center gap-1 text-sm">
        {breadcrumbs.map((crumb, i) => {
          const isLast = i === breadcrumbs.length - 1;
          const isClickable = !isLast && crumb.level < currentLevel;

          return (
            <span key={crumb.level} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="w-3.5 h-3.5 text-stone-300" />}
              {isClickable ? (
                <button
                  onClick={() => onNavigate(crumb.level)}
                  className="text-[var(--primary)] hover:text-[var(--primary-hover)] font-medium transition-colors"
                >
                  {crumb.label}
                </button>
              ) : (
                <span className={isLast ? 'text-[var(--foreground)] font-semibold' : 'text-[var(--foreground-muted)]'}>
                  {crumb.label}
                </span>
              )}
            </span>
          );
        })}
      </nav>
    </div>
  );
}
