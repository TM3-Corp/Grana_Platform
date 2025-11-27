-- Migration 016: Add Lot Tracking and Relbase Integration to Warehouse System
-- Date: 2025-11-18
-- Purpose: Enable lot/batch tracking and Relbase API integration for warehouse inventory
-- Dependencies: Migration 014 (warehouse inventory system)

-- ============================================================================
-- STEP 1: Add external_id to warehouses for Relbase integration
-- ============================================================================

-- Add external_id column (Relbase warehouse_id)
ALTER TABLE warehouses
ADD COLUMN IF NOT EXISTS external_id VARCHAR(255);

-- Add source column (default 'relbase' for API-synced warehouses)
ALTER TABLE warehouses
ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'relbase';

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_warehouses_external_id ON warehouses(external_id);

-- Create composite unique constraint for external_id + source
CREATE UNIQUE INDEX IF NOT EXISTS idx_warehouses_external_source
ON warehouses(external_id, source)
WHERE external_id IS NOT NULL;

COMMENT ON COLUMN warehouses.external_id IS 'External ID from source system (e.g., Relbase warehouse_id)';
COMMENT ON COLUMN warehouses.source IS 'Source system: relbase, manual, etc.';

-- ============================================================================
-- STEP 2: Add lot tracking columns to warehouse_stock
-- ============================================================================

-- Add lot_number column (e.g., "222", "333" from Relbase)
ALTER TABLE warehouse_stock
ADD COLUMN IF NOT EXISTS lot_number VARCHAR(100);

-- Add expiration_date column (lot expiration date)
ALTER TABLE warehouse_stock
ADD COLUMN IF NOT EXISTS expiration_date DATE;

-- Create index for lot searches
CREATE INDEX IF NOT EXISTS idx_warehouse_stock_lot_number ON warehouse_stock(lot_number);

-- Create index for expiration date queries
CREATE INDEX IF NOT EXISTS idx_warehouse_stock_expiration ON warehouse_stock(expiration_date);

COMMENT ON COLUMN warehouse_stock.lot_number IS 'Lot/Batch serial number from Relbase API';
COMMENT ON COLUMN warehouse_stock.expiration_date IS 'Expiration date of this lot';

-- ============================================================================
-- STEP 3: Modify UNIQUE constraint to allow multiple lots per product/warehouse
-- ============================================================================

-- Drop old UNIQUE constraint (product_id, warehouse_id)
-- This constraint prevented multiple lots of same product in same warehouse
ALTER TABLE warehouse_stock
DROP CONSTRAINT IF EXISTS warehouse_stock_product_id_warehouse_id_key;

-- Add new UNIQUE constraint including lot_number
-- This allows multiple lots of same product in same warehouse
ALTER TABLE warehouse_stock
ADD CONSTRAINT warehouse_stock_product_warehouse_lot_unique
UNIQUE(product_id, warehouse_id, lot_number);

COMMENT ON CONSTRAINT warehouse_stock_product_warehouse_lot_unique ON warehouse_stock IS
'Allows multiple lots of same product in same warehouse, each lot identified by lot_number';

-- ============================================================================
-- STEP 4: Update existing warehouses with Relbase data structure
-- ============================================================================

-- Update existing warehouses to match Relbase naming
-- This prepares them for sync with Relbase API

-- Amplifica warehouses
UPDATE warehouses SET
    name = 'AMPLIFICA SANTIAGO CENTRO',
    source = 'relbase'
WHERE code = 'amplifica_centro';

UPDATE warehouses SET
    name = 'AMPLIFICA LA REINA',
    source = 'relbase'
WHERE code = 'amplifica_lareina';

UPDATE warehouses SET
    name = 'AMPLIFICA LO BARNECHEA',
    source = 'relbase'
WHERE code = 'amplifica_lobarnechea';

UPDATE warehouses SET
    name = 'AMPLIFICA QUILICURA',
    source = 'relbase'
WHERE code = 'amplifica_quilicura';

-- Other warehouses
UPDATE warehouses SET
    name = 'PACKNER',
    source = 'relbase'
WHERE code = 'packner';

UPDATE warehouses SET
    name = 'ORINOCO 90',
    source = 'relbase'
WHERE code = 'orinoco';

UPDATE warehouses SET
    name = 'MERCADO LIBRE',
    source = 'relbase',
    update_method = 'api'
WHERE code = 'mercadolibre';

-- ============================================================================
-- STEP 5: Create helper function for lot-aware stock updates
-- ============================================================================

-- Drop old function
DROP FUNCTION IF EXISTS update_warehouse_stock(INT, INT, INT, VARCHAR);

-- Create new function that includes lot tracking
CREATE OR REPLACE FUNCTION update_warehouse_stock(
    p_product_id INT,
    p_warehouse_id INT,
    p_quantity INT,
    p_lot_number VARCHAR DEFAULT NULL,
    p_expiration_date DATE DEFAULT NULL,
    p_updated_by VARCHAR DEFAULT 'system'
) RETURNS VOID AS $$
BEGIN
    INSERT INTO warehouse_stock (
        product_id,
        warehouse_id,
        quantity,
        lot_number,
        expiration_date,
        last_updated,
        updated_by
    )
    VALUES (
        p_product_id,
        p_warehouse_id,
        p_quantity,
        p_lot_number,
        p_expiration_date,
        NOW(),
        p_updated_by
    )
    ON CONFLICT (product_id, warehouse_id, lot_number)
    DO UPDATE SET
        quantity = EXCLUDED.quantity,
        expiration_date = EXCLUDED.expiration_date,
        last_updated = NOW(),
        updated_by = EXCLUDED.updated_by;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_warehouse_stock IS
'Upsert warehouse stock with lot tracking - allows multiple lots per product/warehouse';

-- ============================================================================
-- STEP 6: Update inventory_general view to aggregate lots
-- ============================================================================

-- Drop old view
DROP VIEW IF EXISTS inventory_general;

-- Recreate view with lot aggregation
CREATE OR REPLACE VIEW inventory_general AS
SELECT
    p.id,
    p.sku,
    p.name,
    p.category,
    p.subfamily,

    -- Stock by warehouse (Amplifica locations) - SUM all lots
    MAX(CASE WHEN w.code = 'amplifica_centro' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_amplifica_centro,
    MAX(CASE WHEN w.code = 'amplifica_lareina' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_amplifica_lareina,
    MAX(CASE WHEN w.code = 'amplifica_lobarnechea' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_amplifica_lobarnechea,
    MAX(CASE WHEN w.code = 'amplifica_quilicura' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_amplifica_quilicura,

    -- Stock by warehouse (Other locations) - SUM all lots
    MAX(CASE WHEN w.code = 'packner' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_packner,
    MAX(CASE WHEN w.code = 'orinoco' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_orinoco,
    MAX(CASE WHEN w.code = 'mercadolibre' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_mercadolibre,

    -- Total stock across all warehouses and lots
    COALESCE(SUM(ws.quantity), 0) as stock_total,

    -- Last update timestamp
    MAX(ws.last_updated) as last_updated

FROM products p
LEFT JOIN warehouse_stock ws ON ws.product_id = p.id
LEFT JOIN warehouses w ON w.id = ws.warehouse_id AND w.is_active = true
WHERE p.is_active = true
GROUP BY p.id, p.sku, p.name, p.category, p.subfamily
ORDER BY p.category, p.name;

COMMENT ON VIEW inventory_general IS
'Consolidated inventory view with stock by warehouse (aggregates all lots per product)';

-- ============================================================================
-- STEP 7: Create warehouse_stock_by_lot view for lot-level visibility
-- ============================================================================

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
WHERE p.is_active = true AND w.is_active = true
ORDER BY w.name, p.category, p.name, ws.expiration_date;

COMMENT ON VIEW warehouse_stock_by_lot IS
'Detailed view of warehouse stock at lot level with expiration tracking';

-- ============================================================================
-- Verification queries (run after migration)
-- ============================================================================

-- Uncomment to verify data after migration:

-- Check warehouses with external_id
-- SELECT id, code, name, external_id, source FROM warehouses ORDER BY id;

-- Check warehouse_stock with lot tracking
-- SELECT * FROM warehouse_stock LIMIT 10;

-- Check inventory_general view (aggregated)
-- SELECT * FROM inventory_general LIMIT 10;

-- Check warehouse_stock_by_lot view (detailed)
-- SELECT * FROM warehouse_stock_by_lot LIMIT 20;

-- ============================================================================
-- Migration complete
-- ============================================================================
