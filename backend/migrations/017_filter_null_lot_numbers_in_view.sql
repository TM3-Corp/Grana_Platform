-- Migration 017: Filter NULL lot_number rows from warehouse_stock_by_lot view
-- Date: 2025-11-24
-- Purpose: Exclude legacy rows with lot_number=NULL from warehouse inventory views
-- Dependencies: Migration 016 (lot tracking system)
--
-- Background:
-- Before migration 016 (2025-11-18), warehouse_stock had rows without lot_number.
-- These legacy rows (created around 2025-11-14) cause duplicate stock display
-- in the frontend because they appear as separate "Sin número" entries.
--
-- Solution:
-- Modify warehouse_stock_by_lot view to only include rows where lot_number IS NOT NULL.
-- This ensures the view only shows valid lot-tracked inventory.

-- ============================================================================
-- Recreate warehouse_stock_by_lot view with NULL lot_number filter
-- ============================================================================

DROP VIEW IF EXISTS warehouse_stock_by_lot;

CREATE OR REPLACE VIEW warehouse_stock_by_lot AS
SELECT
    ws.id,
    p.sku,
    p.name as product_name,
    p.category,
    w.code as warehouse_code,
    w.name as warehouse_name,
    ws.quantity,
    ws.lot_number,
    ws.expiration_date,
    ws.last_updated,
    ws.updated_by,
    -- Days until expiration
    CASE
        WHEN ws.expiration_date IS NOT NULL
        THEN ws.expiration_date - CURRENT_DATE
        ELSE NULL
    END as days_to_expiration,
    -- Expiration status
    CASE
        WHEN ws.expiration_date IS NULL THEN 'No Date'
        WHEN ws.expiration_date < CURRENT_DATE THEN 'Expired'
        WHEN ws.expiration_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'Expiring Soon'
        ELSE 'Valid'
    END as expiration_status
FROM warehouse_stock ws
JOIN products p ON p.id = ws.product_id
JOIN warehouses w ON w.id = ws.warehouse_id
WHERE p.is_active = true
  AND w.is_active = true
  AND ws.lot_number IS NOT NULL  -- ⬅️ NEW: Exclude legacy rows without lot_number
ORDER BY w.name, p.category, p.name, ws.expiration_date;

COMMENT ON VIEW warehouse_stock_by_lot IS
'Detailed view of warehouse stock at lot level with expiration tracking.
Excludes legacy rows with NULL lot_number (pre-migration 016 data).';

-- ============================================================================
-- Verification Query
-- ============================================================================

-- Expected result: Should show NO rows with NULL lot_number
-- SELECT lot_number, COUNT(*) as count
-- FROM warehouse_stock_by_lot
-- WHERE lot_number IS NULL
-- GROUP BY lot_number;

-- ============================================================================
-- Migration Complete
-- ============================================================================
