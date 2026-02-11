-- Migration: Backfill Boleta order_items from Gross to Net prices
-- Date: 2026-02-07
-- Corresponding backend migration: 036_backfill_boleta_net_prices.sql
--
-- Converts all 2026 Boleta order_items prices from Gross (IVA-included) to Net.
-- These were synced before the sync_service.py fix that handles this at ingest time.

UPDATE order_items oi
SET unit_price = ROUND(oi.unit_price / 1.19, 2),
    subtotal   = ROUND(oi.subtotal / 1.19, 2),
    total      = ROUND(oi.total / 1.19, 2)
FROM orders o
WHERE oi.order_id = o.id
  AND o.source = 'relbase'
  AND o.invoice_type = 'boleta'
  AND EXTRACT(YEAR FROM o.order_date) = 2026;

REFRESH MATERIALIZED VIEW sales_facts_mv;
