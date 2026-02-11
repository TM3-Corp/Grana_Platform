'use client';

import { useRef } from 'react';
import WarehouseCard from '@/components/inventory/WarehouseCard';

interface WarehouseInfo {
  id: number;
  code: string;
  name: string;
  location: string | null;
  update_method: string;
  is_active: boolean;
}

interface WarehouseExpirationData {
  expired_lots: number;
  expired_units: number;
  expiring_soon_lots: number;
  expiring_soon_units: number;
  valid_lots: number;
  valid_units: number;
  earliest_expiration: string | null;
  days_to_earliest: number | null;
}

interface InventoryProduct {
  sku: string;
  name: string;
  category: string | null;
  warehouses: { [code: string]: number };
  stock_total: number;
}

interface SpatialWarehouseGridProps {
  warehouses: WarehouseInfo[];
  warehouseExpiration: Record<string, WarehouseExpirationData>;
  products: InventoryProduct[];
  onWarehouseClick: (code: string, name: string, updateMethod: string) => void;
}

export default function SpatialWarehouseGrid({
  warehouses,
  warehouseExpiration,
  products,
  onWarehouseClick,
}: SpatialWarehouseGridProps) {
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // Aggregate per-warehouse stats from products
  const warehouseStats = new Map<string, { stock: number; productCount: number }>();
  for (const w of warehouses) {
    warehouseStats.set(w.code, { stock: 0, productCount: 0 });
  }
  for (const p of products) {
    for (const [code, qty] of Object.entries(p.warehouses)) {
      if (qty > 0) {
        const stats = warehouseStats.get(code);
        if (stats) {
          stats.stock += qty;
          stats.productCount += 1;
        }
      }
    }
  }

  const activeWarehouses = warehouses.filter((w) => w.is_active);

  if (activeWarehouses.length === 0) {
    return (
      <div className="text-center py-12 text-[var(--foreground-muted)]">
        <p className="text-sm">No hay bodegas activas.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {activeWarehouses.map((w, index) => {
        const stats = warehouseStats.get(w.code);
        const expData = warehouseExpiration[w.code];
        const staggerIndex = Math.min(index, 14);

        return (
          <div
            key={w.code}
            ref={(el) => { cardRefs.current[w.code] = el; }}
            className="warehouse-zoom-card scope-item-stagger"
            style={{ '--item-index': staggerIndex } as React.CSSProperties}
          >
            <WarehouseCard
              code={w.code}
              name={w.name}
              location={w.location}
              updateMethod={w.update_method}
              isActive={false}
              onClick={() => onWarehouseClick(w.code, w.name, w.update_method)}
              stockCount={stats?.stock}
              productCount={stats?.productCount}
              expirationSummary={expData ? {
                expired_lots: expData.expired_lots,
                expired_units: expData.expired_units,
                expiring_soon_lots: expData.expiring_soon_lots,
                expiring_soon_units: expData.expiring_soon_units,
                earliest_expiration: expData.earliest_expiration,
              } : undefined}
            />
          </div>
        );
      })}
    </div>
  );
}
