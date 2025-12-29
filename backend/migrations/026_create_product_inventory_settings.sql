-- Migration 026: Create product_inventory_settings table
-- Purpose: Store per-product inventory planning preferences (estimation period, safety buffer, etc.)

-- Create table for per-product inventory settings
CREATE TABLE IF NOT EXISTS product_inventory_settings (
    id SERIAL PRIMARY KEY,

    -- Product reference (by SKU to work with both products and product_catalog)
    sku VARCHAR(100) NOT NULL UNIQUE,

    -- Estimation method preference
    -- 1 = "Último Mes" (1 month average)
    -- 3 = "Últimos 3 meses" (3 month average)
    -- 6 = "Últimos 6 meses" (6 month average, default)
    estimation_months INTEGER NOT NULL DEFAULT 6 CHECK (estimation_months IN (1, 3, 6)),

    -- Safety stock buffer percentage (default 20%)
    -- production_needed = projected_demand * (1 + safety_buffer_pct)
    safety_buffer_pct DECIMAL(5,4) NOT NULL DEFAULT 0.20,

    -- Lead time in days (production/restock time)
    -- Used to calculate when to trigger production
    lead_time_days INTEGER NOT NULL DEFAULT 7,

    -- Custom notes for this product's planning
    planning_notes TEXT,

    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookups by SKU
CREATE INDEX IF NOT EXISTS idx_product_inv_settings_sku ON product_inventory_settings(sku);

-- Comments
COMMENT ON TABLE product_inventory_settings IS 'Per-product inventory planning preferences';
COMMENT ON COLUMN product_inventory_settings.estimation_months IS 'Sales averaging period: 1, 3, or 6 months';
COMMENT ON COLUMN product_inventory_settings.safety_buffer_pct IS 'Safety stock as percentage above projected demand (0.20 = 20%)';
COMMENT ON COLUMN product_inventory_settings.lead_time_days IS 'Production/restock lead time in days';
