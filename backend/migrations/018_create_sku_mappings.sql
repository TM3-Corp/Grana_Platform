-- =====================================================================
-- Migration 018: Create SKU Mappings Table
-- =====================================================================
-- Purpose: Replace hardcoded SKU transformation rules in audit.py with
--          a database-driven mapping system.
-- Date: 2025-12-10
-- =====================================================================

-- Create the sku_mappings table
CREATE TABLE IF NOT EXISTS sku_mappings (
    id SERIAL PRIMARY KEY,

    -- Input (what we're mapping FROM)
    source_pattern VARCHAR(255) NOT NULL,   -- Raw SKU or pattern (e.g., "PACKBAMC_U04010", "ANU-*")
    pattern_type VARCHAR(20) NOT NULL,      -- 'exact', 'prefix', 'suffix', 'regex', 'contains'
    source_filter VARCHAR(50),              -- Optional: only apply for specific source ('relbase', 'mercadolibre', etc.)

    -- Output (what we're mapping TO)
    target_sku VARCHAR(100) NOT NULL,       -- Must exist in product_catalog.sku
    quantity_multiplier INTEGER DEFAULT 1,  -- For PACK rules: PACK5 -> target x 5

    -- Metadata
    rule_name VARCHAR(100),                 -- Human-readable name (e.g., "Pack prefix removal")
    confidence INTEGER DEFAULT 100,         -- Confidence score (0-100)
    priority INTEGER DEFAULT 50,            -- Higher = checked first (0-100)
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),                -- User who created the rule
    notes TEXT,                             -- Why this mapping exists

    -- Constraints
    CONSTRAINT fk_target_sku FOREIGN KEY (target_sku)
        REFERENCES product_catalog(sku) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_pattern_type CHECK (pattern_type IN ('exact', 'prefix', 'suffix', 'regex', 'contains')),
    CONSTRAINT chk_confidence CHECK (confidence BETWEEN 0 AND 100),
    CONSTRAINT chk_priority CHECK (priority BETWEEN 0 AND 100),
    CONSTRAINT chk_quantity_multiplier CHECK (quantity_multiplier > 0)
);

-- Indexes for fast lookup
CREATE INDEX idx_sku_mappings_active ON sku_mappings(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_sku_mappings_pattern ON sku_mappings(source_pattern);
CREATE INDEX idx_sku_mappings_priority ON sku_mappings(priority DESC);
CREATE INDEX idx_sku_mappings_source ON sku_mappings(source_filter) WHERE source_filter IS NOT NULL;
CREATE INDEX idx_sku_mappings_target ON sku_mappings(target_sku);

-- Unique constraint to prevent duplicate exact mappings
CREATE UNIQUE INDEX idx_sku_mappings_unique_exact
    ON sku_mappings(source_pattern, source_filter)
    WHERE pattern_type = 'exact' AND is_active = TRUE;

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_sku_mappings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_sku_mappings_updated_at
    BEFORE UPDATE ON sku_mappings
    FOR EACH ROW
    EXECUTE FUNCTION update_sku_mappings_updated_at();

-- Comments for documentation
COMMENT ON TABLE sku_mappings IS 'Database-driven SKU mapping rules to replace hardcoded logic in audit.py';
COMMENT ON COLUMN sku_mappings.source_pattern IS 'Raw SKU pattern to match (exact value or pattern based on pattern_type)';
COMMENT ON COLUMN sku_mappings.pattern_type IS 'How to interpret source_pattern: exact=literal match, prefix=startswith, suffix=endswith, regex=regular expression, contains=substring';
COMMENT ON COLUMN sku_mappings.source_filter IS 'Optional: only apply rule for specific data source (relbase, mercadolibre, shopify)';
COMMENT ON COLUMN sku_mappings.target_sku IS 'Official SKU from product_catalog that this maps to';
COMMENT ON COLUMN sku_mappings.quantity_multiplier IS 'Multiply order quantity by this factor (for PACK mappings)';
COMMENT ON COLUMN sku_mappings.priority IS 'Higher priority rules are checked first (0-100)';
COMMENT ON COLUMN sku_mappings.confidence IS 'Confidence score for the mapping (0-100%)';

-- =====================================================================
-- Seed Data: Migrate hardcoded rules from audit.py
-- =====================================================================

-- Rule 8b: Lokal cracker mappings (from hardcoded dict)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, rule_name, confidence, priority, notes)
VALUES
('CRSA1UES', 'exact', 'CRSM_U13510', 'Lokal Cracker Sal', 95, 80, 'Lokal uses SA for Sal de Mar'),
('CRPI1UES', 'exact', 'CRPM_U13510', 'Lokal Cracker Pimienta', 95, 80, 'Lokal uses PI for Pimienta');

-- Rule 9: Special CRSM bandeja
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, rule_name, confidence, priority, notes)
VALUES
('CRSM_U1000', 'exact', 'CRSM_U1000H', 'CRSM Bandeja mapping', 95, 80, 'Legacy code correction');

-- Rule 10: Keeper Pioneros
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, rule_name, confidence, priority, notes)
VALUES
('KEEPER_PIONEROS', 'exact', 'KPMC_U30010', 'Keeper Pioneros', 95, 80, 'Pioneros promo product');

-- Rule 13: MercadoLibre mappings (17 entries from hardcoded dict)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, source_filter, rule_name, confidence, priority, notes)
VALUES
('MLC1630337051', 'exact', 'BABE_U20010', 'mercadolibre', 'ML Sour Berries 5Un', 80, 60, 'Auto-migrated from audit.py'),
('MLC1630349929', 'exact', 'BACM_U04010', 'mercadolibre', 'ML Cacao Mani', 90, 60, 'Auto-migrated from audit.py'),
('MLC1630349931', 'exact', 'GRCA_U26010', 'mercadolibre', 'ML Granola Keto Cacao', 100, 60, 'Auto-migrated from audit.py'),
('MLC1630369169', 'exact', 'CRPM_U13510', 'mercadolibre', 'ML Crackers Pimienta', 95, 60, 'Auto-migrated from audit.py'),
('MLC1630416135', 'exact', 'BAMC_U04010', 'mercadolibre', 'ML Manzana Canela', 70, 60, 'Auto-migrated from audit.py'),
('MLC1644022833', 'exact', 'GRCA_U26010', 'mercadolibre', 'ML Granola Low Carb Cacao', 90, 60, 'Auto-migrated from audit.py'),
('MLC2929973548', 'exact', 'BAKC_U04010', 'mercadolibre', 'ML Keto Chocolate Nuez', 70, 60, 'Auto-migrated from audit.py'),
('MLC2930070644', 'exact', 'GRCA_U26020', 'mercadolibre', 'ML Granola Cacao 260g', 75, 60, 'Auto-migrated from audit.py'),
('MLC2930199094', 'exact', 'BAKC_U04010', 'mercadolibre', 'ML Keto Nuez Display', 90, 60, 'Auto-migrated from audit.py'),
('MLC2930200766', 'exact', 'CRAA_U13510', 'mercadolibre', 'ML Crackers Ajo Albahaca', 95, 60, 'Auto-migrated from audit.py'),
('MLC2930215860', 'exact', 'CRSM_U13510', 'mercadolibre', 'ML Crackers Sal de Mar', 95, 60, 'Auto-migrated from audit.py'),
('MLC2930238714', 'exact', 'CRRO_U13510', 'mercadolibre', 'ML Crackers Romero', 95, 60, 'Auto-migrated from audit.py'),
('MLC2930251054', 'exact', 'KSMC_U03010', 'mercadolibre', 'ML Keeper Mani 30g', 100, 60, 'Auto-migrated from audit.py'),
('MLC2933751572', 'exact', 'CRRO_U13510', 'mercadolibre', 'ML Crackers Romero (dup)', 95, 60, 'Duplicate listing'),
('MLC2978631042', 'exact', 'BACM_U04010', 'mercadolibre', 'ML Cacao Mani Display', 90, 60, 'Auto-migrated from audit.py'),
('MLC2978641268', 'exact', 'GRBE_U26010', 'mercadolibre', 'ML Granola Berries', 90, 60, 'Auto-migrated from audit.py'),
('MLC3016921654', 'exact', 'KSMC_U03010', 'mercadolibre', 'ML Keeper Mani (dup)', 100, 60, 'Duplicate listing');

-- =====================================================================
-- Dynamic seed: ANU- prefix and _WEB suffix rules
-- These are generated from product_catalog SKUs
-- =====================================================================

-- Rule 3: ANU- prefix removal (generates ~86 mappings)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, rule_name, confidence, priority, notes)
SELECT
    'ANU-' || sku,
    'exact',
    sku,
    'ANU prefix removal',
    95,
    70,
    'Auto-generated: ANU- prefix removal for ' || sku
FROM product_catalog
WHERE is_active = TRUE
ON CONFLICT DO NOTHING;

-- Rule 5: _WEB suffix removal (generates ~86 mappings)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, rule_name, confidence, priority, notes)
SELECT
    sku || '_WEB',
    'exact',
    sku,
    'Web suffix removal',
    96,
    70,
    'Auto-generated: _WEB suffix removal for ' || sku
FROM product_catalog
WHERE is_active = TRUE
ON CONFLICT DO NOTHING;

-- =====================================================================
-- Verification Query
-- =====================================================================
-- SELECT pattern_type, COUNT(*) FROM sku_mappings GROUP BY pattern_type;
-- Expected: ~176 exact mappings initially (86 ANU + 86 WEB + 4 special + 17 ML)
