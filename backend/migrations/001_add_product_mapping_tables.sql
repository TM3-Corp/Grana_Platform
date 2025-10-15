-- Migration: Add Product Mapping Tables
-- Purpose: Enable product variant tracking and cross-channel equivalents
-- Author: TM3
-- Date: 2025-10-13

-- Table 1: product_variants
-- Tracks packaging relationships (e.g., BAKC_U64010 = 16 × BAKC_U04010)
CREATE TABLE IF NOT EXISTS product_variants (
    id SERIAL PRIMARY KEY,
    base_product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity_multiplier INT NOT NULL CHECK (quantity_multiplier > 0),
    packaging_type VARCHAR(50),  -- 'individual', 'display_5', 'display_16', 'pack', 'box'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(base_product_id, variant_product_id),
    CHECK (base_product_id != variant_product_id)  -- Can't be variant of itself
);

CREATE INDEX idx_product_variants_base ON product_variants(base_product_id);
CREATE INDEX idx_product_variants_variant ON product_variants(variant_product_id);

-- Table 2: channel_equivalents
-- Maps equivalent products across sales channels (Shopify ↔ MercadoLibre)
CREATE TABLE IF NOT EXISTS channel_equivalents (
    id SERIAL PRIMARY KEY,
    shopify_product_id INT REFERENCES products(id) ON DELETE CASCADE,
    mercadolibre_product_id INT REFERENCES products(id) ON DELETE CASCADE,
    equivalence_confidence DECIMAL(3,2) CHECK (equivalence_confidence BETWEEN 0 AND 1),
    verified BOOLEAN DEFAULT false,  -- Manually confirmed
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(shopify_product_id, mercadolibre_product_id)
);

CREATE INDEX idx_channel_equiv_shopify ON channel_equivalents(shopify_product_id);
CREATE INDEX idx_channel_equiv_ml ON channel_equivalents(mercadolibre_product_id);

-- View: inventory_consolidated
-- Shows real inventory in base units for each product family
CREATE OR REPLACE VIEW inventory_consolidated AS
SELECT
    p_base.id as base_product_id,
    p_base.sku as base_sku,
    p_base.name as base_name,
    p_base.source as base_source,
    p_base.sale_price as base_unit_price,
    -- Direct stock of base product
    p_base.current_stock as base_direct_stock,
    -- Count of variant types
    COUNT(DISTINCT pv.variant_product_id) as num_variants,
    -- Stock from variants (converted to base units)
    COALESCE(SUM(p_variant.current_stock * pv.quantity_multiplier), 0) as variant_stock_as_units,
    -- Total stock in base units
    p_base.current_stock + COALESCE(SUM(p_variant.current_stock * pv.quantity_multiplier), 0) as total_units_available,
    -- Stock status
    CASE
        WHEN p_base.current_stock + COALESCE(SUM(p_variant.current_stock * pv.quantity_multiplier), 0) < 0 THEN 'OVERSOLD'
        WHEN p_base.current_stock + COALESCE(SUM(p_variant.current_stock * pv.quantity_multiplier), 0) = 0 THEN 'OUT_OF_STOCK'
        WHEN p_base.current_stock + COALESCE(SUM(p_variant.current_stock * pv.quantity_multiplier), 0) < 50 THEN 'LOW_STOCK'
        ELSE 'OK'
    END as stock_status,
    -- Value of inventory (in base units)
    (p_base.current_stock + COALESCE(SUM(p_variant.current_stock * pv.quantity_multiplier), 0)) * p_base.sale_price as inventory_value
FROM products p_base
LEFT JOIN product_variants pv ON p_base.id = pv.base_product_id AND pv.is_active = true
LEFT JOIN products p_variant ON pv.variant_product_id = p_variant.id
WHERE p_base.is_active = true
GROUP BY p_base.id, p_base.sku, p_base.name, p_base.source, p_base.sale_price, p_base.current_stock;

-- View: product_families
-- Shows complete product families with all variants
CREATE OR REPLACE VIEW product_families AS
SELECT
    p_base.id as base_product_id,
    p_base.sku as base_sku,
    p_base.name as base_name,
    p_variant.id as variant_product_id,
    p_variant.sku as variant_sku,
    p_variant.name as variant_name,
    pv.quantity_multiplier,
    pv.packaging_type,
    p_variant.current_stock as variant_stock,
    p_variant.current_stock * pv.quantity_multiplier as variant_stock_as_base_units,
    p_variant.sale_price as variant_price,
    p_base.sale_price as base_unit_price,
    ROUND((p_variant.sale_price / pv.quantity_multiplier), 2) as variant_unit_price,
    -- Price comparison (is the bundle cheaper per unit?)
    CASE
        WHEN ROUND((p_variant.sale_price / pv.quantity_multiplier), 2) < p_base.sale_price
        THEN ROUND(((p_base.sale_price - (p_variant.sale_price / pv.quantity_multiplier)) / p_base.sale_price * 100), 1)
        ELSE 0
    END as discount_percentage
FROM products p_base
INNER JOIN product_variants pv ON p_base.id = pv.base_product_id AND pv.is_active = true
INNER JOIN products p_variant ON pv.variant_product_id = p_variant.id
WHERE p_base.is_active = true;

-- Comments
COMMENT ON TABLE product_variants IS 'Tracks packaging relationships between products (e.g., Display 16 = 16× Individual)';
COMMENT ON TABLE channel_equivalents IS 'Maps equivalent products across sales channels (Shopify ↔ MercadoLibre)';
COMMENT ON VIEW inventory_consolidated IS 'Real inventory in base units for each product family';
COMMENT ON VIEW product_families IS 'Complete product families showing all packaging variants';
