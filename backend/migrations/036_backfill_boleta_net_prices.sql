-- Migration 036: Backfill Boleta order_items from Gross to Net prices
-- Date: 2026-02-07
--
-- PROBLEM:
-- All 2026 Boleta order_items (312 items across 120 orders) were synced on 2026-02-05
-- BEFORE the sync fix (commit 5c43ef0) that converts Boleta prices from Gross to Net.
-- Since sync_service.py skips existing orders (line 874), these items were never updated.
-- Result: Boleta product revenue overstated by ~19% (723K CLP overstatement).
--
-- FIX:
-- Divide unit_price, subtotal, and total by 1.19 for all Boleta order_items.
-- The sync fix already handles new Boletas correctly going forward.
--
-- SCOPE:
-- - 120 Boleta orders (invoice_type = 'boleta') from 2026
-- - 312 order_items total
-- - All synced on 2026-02-05 (single batch, all affected)
--
-- NOTE ON DISCOUNTS:
-- Some orders have order-level discounts (orders.subtotal < SUM(items)/1.19).
-- This is expected — discounts are applied at the order header, not item level.
-- Item prices represent full list prices (before discount), converted to Net.

-- ============================================
-- 1. BACKFILL: Convert Gross → Net prices
-- ============================================

UPDATE order_items oi
SET unit_price = ROUND(oi.unit_price / 1.19, 2),
    subtotal   = ROUND(oi.subtotal / 1.19, 2),
    total      = ROUND(oi.total / 1.19, 2)
FROM orders o
WHERE oi.order_id = o.id
  AND o.source = 'relbase'
  AND o.invoice_type = 'boleta'
  AND EXTRACT(YEAR FROM o.order_date) = 2026;

-- ============================================
-- 2. REFRESH MATERIALIZED VIEW
-- ============================================

REFRESH MATERIALIZED VIEW sales_facts_mv;
