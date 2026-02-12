-- Migration 038: Backfill Boleta order_items to net prices
-- Date: 2026-02-11
--
-- PROBLEM:
-- Boleta order_items store prices derived from /1.19 on RelBase gross prices.
-- But RelBase applies per-item discounts (especially on PACKs) that make
-- SUM(item.price/1.19 * qty) > order.amount_neto.
-- Result: MV revenue inflated by ~$480K for Boleta orders.
--
-- FIX:
-- Proportionally redistribute each order's net total (orders.subtotal, which
-- correctly stores RelBase amount_neto) across its line items weighted by
-- their current subtotal share.
-- After this: SUM(order_items.subtotal) = orders.subtotal for all Boletas.

-- Step 1: Proportionally reallocate Boleta order_items to match order-level net
WITH boleta_totals AS (
    SELECT
        o.id as order_id,
        o.subtotal as order_net,
        SUM(oi.subtotal) as items_total
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    WHERE o.source = 'relbase'
      AND o.invoice_type = 'boleta'
      AND o.subtotal > 0
    GROUP BY o.id, o.subtotal
    HAVING ABS(SUM(oi.subtotal) - o.subtotal) > 1  -- only fix orders with >$1 discrepancy
)
UPDATE order_items oi
SET
    subtotal = ROUND((oi.subtotal / bt.items_total) * bt.order_net, 2),
    total    = ROUND((oi.subtotal / bt.items_total) * bt.order_net, 2),
    unit_price = CASE
        WHEN oi.quantity > 0
        THEN ROUND(((oi.subtotal / bt.items_total) * bt.order_net) / oi.quantity, 2)
        ELSE oi.unit_price
    END
FROM boleta_totals bt
WHERE oi.order_id = bt.order_id
  AND bt.items_total > 0;

-- Step 2: Refresh the materialized view so dashboard shows corrected numbers
REFRESH MATERIALIZED VIEW sales_facts_mv;
