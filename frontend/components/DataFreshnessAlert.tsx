"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { AlertTriangle, X } from "lucide-react";

interface SyncStatus {
  is_stale: boolean;
  staleness_level: "fresh" | "warning" | "critical";
  sales_sync_age_hours: number | null;
  inventory_sync_age_hours: number | null;
}

function formatAge(hours: number): string {
  if (hours < 24) return `${Math.round(hours)} horas`;
  const days = Math.round(hours / 24);
  return `${days} ${days === 1 ? "día" : "días"}`;
}

export default function DataFreshnessAlert() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const pathname = usePathname();

  // Reset dismissal on navigation
  useEffect(() => {
    setDismissed(false);
  }, [pathname]);

  useEffect(() => {
    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiUrl}/api/v1/sync/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.is_stale) setStatus(data);
      })
      .catch(() => {});
  }, []);

  if (!status || !status.is_stale || dismissed) return null;

  const maxAge = Math.max(
    status.sales_sync_age_hours ?? 0,
    status.inventory_sync_age_hours ?? 0
  );
  const isCritical = status.staleness_level === "critical";

  return (
    <div
      className={`${
        isCritical
          ? "bg-red-50 border-red-200 text-red-800"
          : "bg-amber-50 border-amber-200 text-amber-800"
      } border-b px-4 py-2 text-sm flex items-center justify-between`}
    >
      <div className="flex items-center gap-2 max-w-7xl mx-auto w-full">
        <AlertTriangle className="w-4 h-4 flex-shrink-0" strokeWidth={2} />
        <span>
          Datos desactualizados — última sincronización hace{" "}
          <strong>{formatAge(maxAge)}</strong>
        </span>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="p-1 hover:bg-black/5 rounded"
        aria-label="Cerrar"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
