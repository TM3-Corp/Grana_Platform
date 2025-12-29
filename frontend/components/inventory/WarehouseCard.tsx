'use client';

import Image from 'next/image';

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

  // Format expiration date as DD/MM/YYYY
  const formatExpDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  // Calculate days until earliest expiration
  const getDaysToExpiration = (): number | null => {
    if (!expirationSummary?.earliest_expiration) return null;
    const expDate = new Date(expirationSummary.earliest_expiration);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    expDate.setHours(0, 0, 0, 0);
    return Math.ceil((expDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  };

  const daysToExpiration = getDaysToExpiration();
  const hasExpirationWarning = expirationSummary && (expirationSummary.expiring_soon_lots > 0 || expirationSummary.expired_lots > 0);

  return (
    <button
      onClick={onClick}
      className={`
        relative overflow-hidden rounded-lg border-2 p-3 text-left transition-all duration-300
        ${
          isActive
            ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-blue-100 shadow-md scale-[1.02]'
            : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
        }
        group
      `}
    >
      {/* Active Indicator */}
      {isActive && (
        <div className="absolute top-2 right-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse">
            <div className="absolute inset-0 bg-blue-500 rounded-full animate-ping opacity-75" />
          </div>
        </div>
      )}

      {/* Warehouse Icon */}
      <div
        className={`
        inline-flex items-center justify-center w-12 h-12 rounded-md mb-2 transition-all duration-300 overflow-hidden
        ${
          isActive
            ? 'bg-blue-500 shadow-md'
            : 'bg-white border border-gray-200 group-hover:border-gray-300'
        }
      `}
      >
        {isAmplifica ? (
          <Image
            src="/images/amplifica_logo.png"
            alt="Amplifica"
            width={28}
            height={28}
            className="rounded-full"
          />
        ) : code === 'packner' ? (
          <Image
            src="/images/logo_packner.png"
            alt="Packner"
            width={32}
            height={32}
          />
        ) : code === 'mercadolibre' ? (
          <Image
            src="/images/logo_ml.webp"
            alt="MercadoLibre"
            width={32}
            height={32}
            className="rounded-sm"
          />
        ) : code === 'orinoco' ? (
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
        ) : (
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
        )}
      </div>

      {/* Warehouse Name */}
      <div className="mb-1.5">
        <h3
          className={`text-sm font-bold transition-colors truncate ${
            isActive ? 'text-blue-900' : 'text-gray-900'
          }`}
        >
          {name.replace('Amplifica - ', '')}
        </h3>
        {location && (
          <p className="text-xs text-gray-500 mt-0.5 truncate">
            📍 {location}
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
                  productCount > 0 ? 'bg-green-500' : 'bg-gray-300'
                }`}
              />
              <span className="text-gray-600">{productCount} prod.</span>
            </div>
          )}
          {stockCount !== undefined && (
            <div className="flex items-center gap-1">
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  stockCount > 0 ? 'bg-blue-500' : 'bg-gray-300'
                }`}
              />
              <span className="text-gray-600">{stockCount.toLocaleString()} un.</span>
            </div>
          )}
        </div>
      )}

      {/* Expiration Indicators */}
      {expirationSummary && (expirationSummary.expiring_soon_lots > 0 || expirationSummary.expired_lots > 0 || expirationSummary.earliest_expiration) && (
        <div className="mb-2 space-y-1">
          {/* Expired warning */}
          {expirationSummary.expired_lots > 0 && (
            <div className="flex items-center gap-1 text-xs">
              <span className="text-red-500">❌</span>
              <span className="text-red-600 font-medium">
                {expirationSummary.expired_lots} vencido{expirationSummary.expired_lots > 1 ? 's' : ''}
              </span>
            </div>
          )}
          {/* Expiring soon warning */}
          {expirationSummary.expiring_soon_lots > 0 && (
            <div className="flex items-center gap-1 text-xs">
              <span className="text-amber-500">⏰</span>
              <span className="text-amber-600 font-medium">
                {expirationSummary.expiring_soon_lots} por vencer
              </span>
            </div>
          )}
          {/* Earliest expiration date */}
          {expirationSummary.earliest_expiration && daysToExpiration !== null && (
            <div className="flex items-center gap-1 text-xs">
              <span className={daysToExpiration < 30 ? 'text-amber-500' : 'text-green-500'}>📅</span>
              <span className={`${daysToExpiration < 30 ? 'text-amber-600' : 'text-gray-600'}`}>
                Vence: {formatExpDate(expirationSummary.earliest_expiration)}
                <span className="text-gray-400 ml-1">({daysToExpiration}d)</span>
              </span>
            </div>
          )}
        </div>
      )}

      {/* Update Method Badge */}
      <div
        className={`
        inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
        ${
          updateMethod === 'manual_upload'
            ? isActive
              ? 'bg-blue-200 text-blue-800'
              : 'bg-gray-100 text-gray-700'
            : isActive
            ? 'bg-green-200 text-green-800'
            : 'bg-green-50 text-green-700'
        }
      `}
      >
        <span className="text-xs">{updateMethod === 'manual_upload' ? '📁' : '🔗'}</span>
        <span>{updateMethod === 'manual_upload' ? 'Manual' : 'API'}</span>
      </div>

      {/* Hover shine effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-10 transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-all duration-700" />

      {/* Bottom accent line */}
      <div
        className={`
        absolute bottom-0 left-0 right-0 h-1 transition-all duration-300
        ${isActive ? 'bg-gradient-to-r from-blue-500 to-blue-600' : 'bg-gray-200 group-hover:bg-gray-300'}
      `}
      />
    </button>
  );
}
