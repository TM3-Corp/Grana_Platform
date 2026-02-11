'use client';

import { toTitleCase, formatCurrencyFull } from '@/lib/utils';
import {
  Package,
  CheckCircle,
  Clock,
  XCircle,
  AlertTriangle,
} from 'lucide-react';

interface LotInfo {
  lot_number: string | null;
  quantity: number;
  expiration_date: string | null;
  last_updated: string;
  days_to_expiration?: number | null;
  expiration_status?: 'No Date' | 'Expired' | 'Expiring Soon' | 'Valid';
}

interface ProductDetail {
  sku: string;
  name: string;
  category: string | null;
  stock: number;
  lots: LotInfo[];
  valor?: number;
}

interface SpatialLotDetailProps {
  product: ProductDetail;
}

const StatusBadge = ({ status }: { status?: string }) => {
  if (!status) return null;
  const config: Record<string, { icon: React.ReactNode; text: string; classes: string }> = {
    'Valid': { icon: <CheckCircle className="w-3.5 h-3.5" />, text: 'Valido', classes: 'bg-[var(--success-light)] text-[var(--success)] border-emerald-200' },
    'Expiring Soon': { icon: <Clock className="w-3.5 h-3.5" />, text: 'Por vencer', classes: 'bg-[var(--warning-light)] text-amber-700 border-amber-200' },
    'Expired': { icon: <XCircle className="w-3.5 h-3.5" />, text: 'Vencido', classes: 'bg-[var(--danger-light)] text-[var(--danger)] border-red-200' },
    'No Date': { icon: <AlertTriangle className="w-3.5 h-3.5" />, text: 'Sin fecha', classes: 'bg-stone-100 text-stone-600 border-stone-200' },
  };
  const badge = config[status];
  if (!badge) return null;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold border rounded-lg ${badge.classes}`}>
      {badge.icon}
      {badge.text}
    </span>
  );
};

const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' });
};

export default function SpatialLotDetail({ product }: SpatialLotDetailProps) {
  const lots = product.lots || [];

  return (
    <div className="space-y-4">
      {/* Product header card */}
      <div
        className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-5 scope-item-stagger"
        style={{ '--item-index': 0 } as React.CSSProperties}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <code className="text-sm font-mono font-semibold text-stone-500 bg-stone-100 px-2 py-1 rounded">
              {product.sku}
            </code>
            <h3 className="text-lg font-bold text-[var(--foreground)] mt-2">
              {toTitleCase(product.name)}
            </h3>
            {product.category && (
              <span className="inline-flex items-center px-2 py-0.5 mt-1 rounded text-xs font-semibold bg-teal-100 text-teal-700 uppercase tracking-wide">
                {toTitleCase(product.category)}
              </span>
            )}
          </div>
          <div className="flex gap-6 text-right">
            <div>
              <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Stock Total</p>
              <p className="text-2xl font-bold text-[var(--foreground)] font-mono">{product.stock.toLocaleString('es-CL')}</p>
            </div>
            {product.valor && Number(product.valor) > 0 && (
              <div>
                <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Valor</p>
                <p className="text-2xl font-bold text-[var(--success)] font-mono">{formatCurrencyFull(Number(product.valor))}</p>
              </div>
            )}
            <div>
              <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Lotes</p>
              <p className="text-2xl font-bold text-[var(--secondary)] font-mono">{lots.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Lot cards grid */}
      {lots.length === 0 ? (
        <div className="text-center py-12 text-[var(--foreground-muted)]">
          <Package className="w-12 h-12 mx-auto mb-3 text-stone-300" />
          <p className="font-medium">No hay lotes disponibles</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {lots.map((lot, index) => {
            const pct = product.stock > 0 ? ((lot.quantity / product.stock) * 100) : 0;
            const staggerIdx = Math.min(index + 1, 14);

            return (
              <div
                key={`${lot.lot_number}-${index}`}
                className={`bg-[var(--surface)] rounded-xl border p-4 scope-item-stagger ${
                  lot.expiration_status === 'Expired'
                    ? 'border-red-200 bg-red-50/30'
                    : lot.expiration_status === 'Expiring Soon'
                      ? 'border-amber-200 bg-amber-50/30'
                      : 'border-[var(--border)]'
                }`}
                style={{ '--item-index': staggerIdx } as React.CSSProperties}
              >
                <div className="flex items-start justify-between mb-3">
                  <code className="text-sm font-mono font-bold text-[var(--foreground)]">
                    {lot.lot_number || <span className="text-stone-400 italic font-normal">Sin numero</span>}
                  </code>
                  <StatusBadge status={lot.expiration_status} />
                </div>

                <div className="space-y-2">
                  {/* Quantity */}
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs text-stone-500 uppercase tracking-wide font-semibold">Cantidad</span>
                    <span className="text-lg font-bold text-[var(--foreground)] font-mono">
                      {lot.quantity.toLocaleString('es-CL')}
                    </span>
                  </div>

                  {/* Expiration */}
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs text-stone-500 uppercase tracking-wide font-semibold">Vencimiento</span>
                    <span className="text-sm text-[var(--foreground-muted)] font-mono">
                      {formatDate(lot.expiration_date)}
                    </span>
                  </div>

                  {/* Days remaining */}
                  {lot.days_to_expiration != null && (
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-stone-500 uppercase tracking-wide font-semibold">Dias</span>
                      <span className={`text-sm font-bold font-mono ${
                        lot.days_to_expiration < 0 ? 'text-[var(--danger)]' :
                        lot.days_to_expiration < 30 ? 'text-amber-700' :
                        'text-[var(--success)]'
                      }`}>
                        {lot.days_to_expiration}d
                      </span>
                    </div>
                  )}

                  {/* Percentage bar */}
                  <div className="pt-2 border-t border-stone-100">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-stone-400 uppercase tracking-wide">% del producto</span>
                      <span className="text-xs font-semibold text-[var(--foreground-muted)] font-mono">
                        {pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-stone-200 rounded-full h-1.5">
                      <div
                        className="bg-[var(--primary)] h-1.5 rounded-full transition-all"
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
