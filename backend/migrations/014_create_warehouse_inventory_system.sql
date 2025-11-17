-- Migration 014: Create Warehouse Inventory System
-- Date: 2025-11-13
-- Purpose: Create warehouse inventory management system with multi-location stock tracking
-- Dependencies: products table (must exist)

-- ============================================================================
-- STEP 1: Create warehouses table
-- ============================================================================

CREATE TABLE IF NOT EXISTS warehouses (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    update_method VARCHAR(20) NOT NULL CHECK (update_method IN ('manual_upload', 'api')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_warehouses_code ON warehouses(code);
CREATE INDEX IF NOT EXISTS idx_warehouses_is_active ON warehouses(is_active);

-- Add comments
COMMENT ON TABLE warehouses IS 'Catalog of warehouse locations (Amplifica locations, Packner, Orinoco, Mercado Libre)';
COMMENT ON COLUMN warehouses.code IS 'Unique identifier code for warehouse (e.g., amplifica_centro, packner)';
COMMENT ON COLUMN warehouses.name IS 'Human-readable name (e.g., Amplifica - Centro)';
COMMENT ON COLUMN warehouses.update_method IS 'How stock is updated: manual_upload (Excel) or api (automatic)';

-- ============================================================================
-- STEP 2: Create warehouse_stock table
-- ============================================================================

CREATE TABLE IF NOT EXISTS warehouse_stock (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id INT NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100),
    UNIQUE(product_id, warehouse_id)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_warehouse_stock_product ON warehouse_stock(product_id);
CREATE INDEX IF NOT EXISTS idx_warehouse_stock_warehouse ON warehouse_stock(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_warehouse_stock_quantity ON warehouse_stock(quantity);
CREATE INDEX IF NOT EXISTS idx_warehouse_stock_composite ON warehouse_stock(product_id, warehouse_id);

-- Add comments
COMMENT ON TABLE warehouse_stock IS 'Stock quantity per product per warehouse';
COMMENT ON COLUMN warehouse_stock.product_id IS 'Foreign key to products table';
COMMENT ON COLUMN warehouse_stock.warehouse_id IS 'Foreign key to warehouses table';
COMMENT ON COLUMN warehouse_stock.quantity IS 'Current stock quantity (can be negative for oversold items)';
COMMENT ON COLUMN warehouse_stock.last_updated IS 'Timestamp of last stock update';
COMMENT ON COLUMN warehouse_stock.updated_by IS 'User or system that updated the stock';

-- ============================================================================
-- STEP 3: Insert initial warehouse data
-- ============================================================================

INSERT INTO warehouses (code, name, location, update_method) VALUES
-- Amplifica locations (4 sucursales)
('amplifica_centro', 'Amplifica - Centro', 'Santiago Centro', 'manual_upload'),
('amplifica_lareina', 'Amplifica - La Reina', 'La Reina, Santiago', 'manual_upload'),
('amplifica_lobarnechea', 'Amplifica - Lo Barnechea', 'Lo Barnechea, Santiago', 'manual_upload'),
('amplifica_quilicura', 'Amplifica - Quilicura', 'Quilicura, Santiago', 'manual_upload'),

-- Other warehouses
('packner', 'Packner', NULL, 'manual_upload'),
('orinoco', 'Orinoco', NULL, 'manual_upload'),
('mercadolibre', 'Mercado Libre', NULL, 'api')

ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- STEP 4: Create inventory_general view
-- ============================================================================

CREATE OR REPLACE VIEW inventory_general AS
SELECT
    p.id,
    p.sku,
    p.name,
    p.category,
    p.subfamily,

    -- Stock by warehouse (Amplifica locations)
    MAX(CASE WHEN w.code = 'amplifica_centro' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_amplifica_centro,
    MAX(CASE WHEN w.code = 'amplifica_lareina' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_amplifica_lareina,
    MAX(CASE WHEN w.code = 'amplifica_lobarnechea' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_amplifica_lobarnechea,
    MAX(CASE WHEN w.code = 'amplifica_quilicura' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_amplifica_quilicura,

    -- Stock by warehouse (Other locations)
    MAX(CASE WHEN w.code = 'packner' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_packner,
    MAX(CASE WHEN w.code = 'orinoco' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_orinoco,
    MAX(CASE WHEN w.code = 'mercadolibre' THEN COALESCE(ws.quantity, 0) ELSE 0 END) as stock_mercadolibre,

    -- Total stock across all warehouses
    COALESCE(SUM(ws.quantity), 0) as stock_total,

    -- Last update timestamp
    MAX(ws.last_updated) as last_updated

FROM products p
LEFT JOIN warehouse_stock ws ON ws.product_id = p.id
LEFT JOIN warehouses w ON w.id = ws.warehouse_id AND w.is_active = true
WHERE p.is_active = true
GROUP BY p.id, p.sku, p.name, p.category, p.subfamily
ORDER BY p.category, p.name;

COMMENT ON VIEW inventory_general IS 'Consolidated inventory view with stock by warehouse location';

-- ============================================================================
-- STEP 5: Create helper function to update stock with audit trail
-- ============================================================================

CREATE OR REPLACE FUNCTION update_warehouse_stock(
    p_product_id INT,
    p_warehouse_id INT,
    p_quantity INT,
    p_updated_by VARCHAR DEFAULT 'system'
) RETURNS VOID AS $$
BEGIN
    INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, last_updated, updated_by)
    VALUES (p_product_id, p_warehouse_id, p_quantity, NOW(), p_updated_by)
    ON CONFLICT (product_id, warehouse_id)
    DO UPDATE SET
        quantity = EXCLUDED.quantity,
        last_updated = NOW(),
        updated_by = EXCLUDED.updated_by;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_warehouse_stock IS 'Upsert warehouse stock with automatic timestamp update';

-- ============================================================================
-- STEP 6: Create validation check constraints
-- ============================================================================

-- Ensure warehouse codes follow naming convention
ALTER TABLE warehouses
ADD CONSTRAINT check_warehouse_code_format
CHECK (code ~ '^[a-z_]+$');

COMMENT ON CONSTRAINT check_warehouse_code_format ON warehouses IS 'Warehouse codes must be lowercase with underscores only';

-- ============================================================================
-- Verification queries (run after migration)
-- ============================================================================

-- Uncomment to verify data after migration:

-- Check warehouses created
-- SELECT * FROM warehouses ORDER BY id;

-- Check inventory_general view
-- SELECT * FROM inventory_general LIMIT 10;

-- Check indexes
-- SELECT tablename, indexname FROM pg_indexes WHERE tablename IN ('warehouses', 'warehouse_stock');

-- ============================================================================
-- Migration complete
-- ============================================================================
