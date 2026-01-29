'use client';

import Image from 'next/image';
import {
  Warehouse,
  FileUp,
  Link2,
  MapPin,
  AlertTriangle,
  Clock,
  Calendar,
  ShoppingCart,
  Package,
  Boxes,
} from 'lucide-react';

interface ExpirationSummary {
  expiring_soon_lots: number;
  expiring_soon_units: number;
  expired_lots: number;
  expired_units: number;
  earliest_expiration?: string | null;
}

interface WarehouseCardProps {
  code: string;
  name: string;
  location?: string | null;
  updateMethod: string;
  isActive: boolean;
  onClick: () => void;
  stockCount?: number;
  productCount?: number;
  expirationSummary?: ExpirationSummary;
}

export default function WarehouseCard({
  code,
  name,
  location,
  updateMethod,
  isActive,
  onClick,
  stockCount,
  productCount,
  expirationSummary,
}: WarehouseCardProps) {
  const isAmplifica = code.startsWith('amplifica');

  const formatExpDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: '2-digit' });
  };

  const getDaysToExpiration = (): number | null => {
    if (!expirationSummary?.earliest_expiration) return null;
    const expDate = new Date(expirationSummary.earliest_expiration);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    expDate.setHours(0, 0, 0, 0);
    return Math.ceil((expDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  };

  const daysToExpiration = getDaysToExpiration();

  return (
    <button
      onClick={onClick}
      className={`
        relative overflow-hidden rounded-xl border-2 p-3 text-left transition-all duration-200
        ${
          isActive
            ? 'border-[var(--primary)] bg-[var(--primary-lighter)] shadow-md'
            : 'border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-subtle)] hover:shadow-sm'
        }
        group
      `}
    >
      {/* Active Indicator */}
      {isActive && (
        <div className="absolute top-2 right-2">
          <div className="w-2.5 h-2.5 bg-[var(--primary)] rounded-full">
            <div className="absolute inset-0 bg-[var(--primary)] rounded-full animate-ping opacity-50" />
          </div>
        </div>
      )}

      {/* Warehouse Icon */}
      <div
        className={`
        inline-flex items-center justify-center w-11 h-11 rounded-lg mb-2 transition-all duration-200 overflow-hidden
        ${
          isActive
            ? 'bg-[var(--primary)] shadow-sm'
            : 'bg-stone-100 border border-stone-200 group-hover:border-stone-300'
        }
      `}
      >
        {isAmplifica ? (
          <Image
            src="/images/amplifica_logo.png"
            alt="Amplifica"
            width={26}
            height={26}
            className="rounded-full"
          />
        ) : code === 'packner' ? (
          <Image
            src="/images/logo_packner.png"
            alt="Packner"
            width={30}
            height={30}
          />
        ) : code === 'mercadolibre' ? (
          <Image
            src="/images/logo_ml.webp"
            alt="MercadoLibre"
            width={30}
            height={30}
            className="rounded-sm"
          />
        ) : code === 'orinoco' ? (
          <Boxes className={`w-5 h-5 ${isActive ? 'text-white' : 'text-[var(--secondary)]'}`} />
        ) : (
          <ShoppingCart className={`w-5 h-5 ${isActive ? 'text-white' : 'text-[var(--primary)]'}`} />
        )}
      </div>

      {/* Warehouse Name */}
      <div className="mb-1.5">
        <h3
          className={`text-sm font-semibold transition-colors truncate ${
            isActive ? 'text-[var(--primary-hover)]' : 'text-[var(--foreground)]'
          }`}
        >
          {name.replace('Amplifica - ', '')}
        </h3>
        {location && (
          <p className="text-xs text-[var(--foreground-muted)] mt-0.5 truncate flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {location}
          </p>
        )}
      </div>

      {/* Stats */}
      {(productCount !== undefined || stockCount !== undefined) && (
        <div className="flex items-center gap-2 mb-2 text-xs">
          {productCount !== undefined && (
            <div className="flex items-center gap-1">
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  productCount > 0 ? 'bg-[var(--success)]' : 'bg-stone-300'
                }`}
              />
              <span className="text-[var(--foreground-muted)] font-mono">{productCount}</span>
            </div>
          )}
          {stockCount !== undefined && (
            <div className="flex items-center gap-1">
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  stockCount > 0 ? 'bg-[var(--secondary)]' : 'bg-stone-300'
                }`}
              />
              <span className="text-[var(--foreground-muted)] font-mono">{stockCount.toLocaleString()}</span>
            </div>
          )}
        </div>
      )}

      {/* Expiration Indicators */}
      {expirationSummary && (expirationSummary.expiring_soon_lots > 0 || expirationSummary.expired_lots > 0 || expirationSummary.earliest_expiration) && (
        <div className="mb-2 space-y-1">
          {expirationSummary.expired_lots > 0 && (
            <div className="flex items-center gap-1 text-xs">
              <AlertTriangle className="w-3 h-3 text-[var(--danger)]" />
              <span className="text-[var(--danger)] font-medium">
                {expirationSummary.expired_lots} vencido{expirationSummary.expired_lots > 1 ? 's' : ''}
              </span>
            </div>
          )}
          {expirationSummary.expiring_soon_lots > 0 && (
            <div className="flex items-center gap-1 text-xs">
              <Clock className="w-3 h-3 text-[var(--warning)]" />
              <span className="text-amber-700 font-medium">
                {expirationSummary.expiring_soon_lots} por vencer
              </span>
            </div>
          )}
          {expirationSummary.earliest_expiration && daysToExpiration !== null && (
            <div className="flex items-center gap-1 text-xs">
              <Calendar className={`w-3 h-3 ${daysToExpiration < 30 ? 'text-[var(--warning)]' : 'text-[var(--success)]'}`} />
              <span className={`font-mono ${daysToExpiration < 30 ? 'text-amber-700' : 'text-[var(--foreground-muted)]'}`}>
                {formatExpDate(expirationSummary.earliest_expiration)}
                <span className="text-stone-400 ml-1">({daysToExpiration}d)</span>
              </span>
            </div>
          )}
        </div>
      )}

      {/* Update Method Badge */}
      <div
        className={`
        inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium
        ${
          updateMethod === 'manual_upload'
            ? isActive
              ? 'bg-[var(--primary-light)] text-[var(--primary-hover)]'
              : 'bg-stone-100 text-stone-600'
            : isActive
            ? 'bg-[var(--success-light)] text-green-800'
            : 'bg-emerald-50 text-emerald-700'
        }
      `}
      >
        {updateMethod === 'manual_upload' ? (
          <FileUp className="w-3 h-3" />
        ) : (
          <Link2 className="w-3 h-3" />
        )}
        <span>{updateMethod === 'manual_upload' ? 'Manual' : 'API'}</span>
      </div>

      {/* Bottom accent line */}
      <div
        className={`
        absolute bottom-0 left-0 right-0 h-1 transition-all duration-200
        ${isActive ? 'bg-[var(--primary)]' : 'bg-stone-200 group-hover:bg-stone-300'}
      `}
      />
    </button>
  );
}
