-- Migration: 007_relbase_product_mappings
-- Description: Create table to store Relbase product code mappings to official catalog
-- Date: 2025-10-21

-- Create relbase_product_mappings table
CREATE TABLE IF NOT EXISTS relbase_product_mappings (
    id SERIAL PRIMARY KEY,

    -- Relbase product code (from their system)
    relbase_code VARCHAR(100) NOT NULL UNIQUE,
    relbase_name VARCHAR(500),

    -- Official catalog mapping
    official_sku VARCHAR(100),  -- NULL if unmapped
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,

    -- Mapping metadata
    match_type VARCHAR(50) NOT NULL,  -- exact, pack_variant, caja_master, caja_fuzzy, no_match
    confidence_level VARCHAR(20) NOT NULL,  -- high, medium, low, none
    mapping_notes TEXT,

    -- Statistics
    total_sales INTEGER DEFAULT 0,  -- Number of times this code appeared in Relbase
    first_seen_date TIMESTAMP,
    last_seen_date TIMESTAMP,

    -- Product categorization (from Relbase name analysis)
    inferred_category VARCHAR(100),  -- granola, barra, cracker, keeper
    inferred_variant VARCHAR(100),   -- cacao, almendras, berries

    -- Flags
    is_service_item BOOLEAN DEFAULT false,  -- DESPACHO, Diferencia, etc.
    is_legacy_code BOOLEAN DEFAULT false,   -- ANU- codes
    needs_manual_review BOOLEAN DEFAULT false,

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for fast lookups
CREATE INDEX idx_relbase_mappings_code ON relbase_product_mappings(relbase_code);
CREATE INDEX idx_relbase_mappings_sku ON relbase_product_mappings(official_sku);
CREATE INDEX idx_relbase_mappings_product_id ON relbase_product_mappings(product_id);
CREATE INDEX idx_relbase_mappings_match_type ON relbase_product_mappings(match_type);
CREATE INDEX idx_relbase_mappings_needs_review ON relbase_product_mappings(needs_manual_review) WHERE needs_manual_review = true;
CREATE INDEX idx_relbase_mappings_is_service ON relbase_product_mappings(is_service_item) WHERE is_service_item = true;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_relbase_mappings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER trigger_update_relbase_mappings_updated_at
    BEFORE UPDATE ON relbase_product_mappings
    FOR EACH ROW
    EXECUTE FUNCTION update_relbase_mappings_updated_at();

-- Add comments
COMMENT ON TABLE relbase_product_mappings IS 'Maps Relbase product codes to official Grana catalog SKUs';
COMMENT ON COLUMN relbase_product_mappings.relbase_code IS 'Product code from Relbase system (e.g., BAKC_U20010, ANU-3322808180)';
COMMENT ON COLUMN relbase_product_mappings.official_sku IS 'Mapped SKU from official Grana catalog';
COMMENT ON COLUMN relbase_product_mappings.match_type IS 'Mapping strategy: exact, pack_variant, caja_master, caja_fuzzy, no_match';
COMMENT ON COLUMN relbase_product_mappings.confidence_level IS 'Mapping confidence: high, medium, low, none';
COMMENT ON COLUMN relbase_product_mappings.is_service_item IS 'True for shipping fees, price adjustments, etc. (not actual products)';
COMMENT ON COLUMN relbase_product_mappings.is_legacy_code IS 'True for auto-generated ANU- codes from system migrations';

-- Insert example mapping data (will be populated by data migration script)
-- This is just a sample to show the structure
INSERT INTO relbase_product_mappings
    (relbase_code, relbase_name, official_sku, match_type, confidence_level, total_sales, is_legacy_code, needs_manual_review)
VALUES
    ('BAKC_U20010', 'BARRA KETO NUEZ X5', 'BAKC_U20010', 'exact', 'high', 242, false, false),
    ('PACKKSMC_U15010', 'PACK KEEPER MANÍ X5', 'KSMC_U15010', 'pack_variant', 'high', 33, false, false),
    ('GRCA_C02010', 'CAJA MASTER GRANOLA CACAO', 'GRCA_U26010', 'caja_master', 'high', 50, false, false),
    ('GRAL_C02010', 'CAJA MASTER GRANOLA ALMENDRAS', 'GRAL_U26010', 'caja_fuzzy', 'medium', 21, false, false),
    ('ANU-3322808180', 'MIX GRANA CLÁSICO', NULL, 'no_match', 'none', 706, true, true),
    ('ANU-D-DW-995240', 'DESPACHO WEB', NULL, 'no_match', 'none', 468, false, false)
ON CONFLICT (relbase_code) DO NOTHING;

-- Update the service item flag for known service codes
UPDATE relbase_product_mappings
SET is_service_item = true
WHERE relbase_name LIKE '%DESPACHO%'
   OR relbase_name LIKE '%Diferencia%'
   OR relbase_code LIKE 'ANU-D-%'
   OR relbase_code LIKE 'D-D-%'
   OR relbase_code LIKE 'O-D-%';
