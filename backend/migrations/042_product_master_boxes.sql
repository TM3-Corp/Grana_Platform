-- Migration 042: Create product_master_boxes junction table
-- Date: 2026-02-20
--
-- Products can have MULTIPLE caja master (master box) sizes.
-- Example: GRBE_U26010 ships in both GRBE_C01010 (10 units) and GRBE_C02010 (20 units).
--
-- The current product_catalog.sku_master column is 1:1, so only one master box can be
-- linked per product. This migration creates a proper junction table to support N master
-- boxes per product.
--
-- Also reverts migration 041's hack that changed GRBE_U26010.items_per_master_box from 10→20.
-- The correct approach is two separate master box entries in the junction table.

-- ============================================
-- 1. CREATE JUNCTION TABLE
-- ============================================

CREATE TABLE product_master_boxes (
    id SERIAL PRIMARY KEY,
    product_sku VARCHAR(100) NOT NULL REFERENCES product_catalog(sku),
    sku_master VARCHAR(100) NOT NULL UNIQUE,
    master_box_name VARCHAR(255),
    items_per_master_box INTEGER,
    units_per_master_box INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pmb_product_sku ON product_master_boxes(product_sku);
CREATE INDEX idx_pmb_sku_master ON product_master_boxes(sku_master);

-- ============================================
-- 2. MIGRATE EXISTING DATA FROM product_catalog
-- ============================================

-- Use DISTINCT ON to handle duplicate sku_master values in product_catalog
-- (e.g., CRSM_C10020 is shared by CRSM_U02520 and CRPM_U02520 — data issue to fix separately)
INSERT INTO product_master_boxes (product_sku, sku_master, master_box_name, items_per_master_box, units_per_master_box)
SELECT DISTINCT ON (sku_master) sku, sku_master, master_box_name, items_per_master_box, units_per_master_box
FROM product_catalog
WHERE sku_master IS NOT NULL
ORDER BY sku_master, sku;

-- ============================================
-- 3. REVERT MIGRATION 041 HACK
-- ============================================

-- Migration 041 changed GRBE_U26010.items_per_master_box from 10 to 20.
-- The 10-unit value corresponds to GRBE_C01010; the 20-unit box gets its own junction row.
UPDATE product_catalog SET items_per_master_box = 10 WHERE sku = 'GRBE_U26010';

-- Also revert in the junction table row that was migrated from product_catalog
UPDATE product_master_boxes SET items_per_master_box = 10
WHERE product_sku = 'GRBE_U26010' AND sku_master = 'GRBE_C01010';

-- ============================================
-- 4. ADD MISSING MASTER BOX ENTRIES
-- ============================================

-- These master box codes appear in orders but were not in product_catalog.
-- Per client input, these are confirmed mappings.

-- Some of these may already exist from the product_catalog migration above.
-- Use ON CONFLICT to skip those and only insert genuinely new entries.

-- GRBE: 20-unit box (the one actually sold most)
INSERT INTO product_master_boxes (product_sku, sku_master, master_box_name, items_per_master_box)
VALUES ('GRBE_U26010', 'GRBE_C02010', 'Caja Master Granola Low Carb Berries 260 x20', 20)
ON CONFLICT (sku_master) DO NOTHING;

-- GRAL: 10-unit and 20-unit boxes
INSERT INTO product_master_boxes (product_sku, sku_master, master_box_name, items_per_master_box)
VALUES ('GRAL_U26010', 'GRAL_C01010', 'Caja Master Granola Low Carb Almendras 260 x10', 10)
ON CONFLICT (sku_master) DO NOTHING;

INSERT INTO product_master_boxes (product_sku, sku_master, master_box_name, items_per_master_box)
VALUES ('GRAL_U26010', 'GRAL_C02010', 'Caja Master Granola Low Carb Almendras 260 x20', 20)
ON CONFLICT (sku_master) DO NOTHING;

-- GRCA: 10-unit and 20-unit boxes (per client: "va a pasar con GRCA")
INSERT INTO product_master_boxes (product_sku, sku_master, master_box_name, items_per_master_box)
VALUES ('GRCA_U26010', 'GRCA_C01010', 'Caja Master Granola Low Carb Cacao 260 x10', 10)
ON CONFLICT (sku_master) DO NOTHING;

INSERT INTO product_master_boxes (product_sku, sku_master, master_box_name, items_per_master_box)
VALUES ('GRCA_U26010', 'GRCA_C02010', 'Caja Master Granola Low Carb Cacao 260 x20', 20)
ON CONFLICT (sku_master) DO NOTHING;

-- NOTE: Other missing codes (GRBE_C02020, GRAL_C02020, GRCA_C02020, _C3000H bulk codes)
-- need client confirmation on items_per_master_box. They will show as unmapped until
-- confirmed and added. "Always work with mappings that are stored, no improvisation."

-- ============================================
-- 5. VERIFICATION
-- ============================================

DO $$
DECLARE
    v_junction_count INTEGER;
    v_old_master_count INTEGER;
    v_grbe_count INTEGER;
    v_grbe_ipmb INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_junction_count FROM product_master_boxes;
    SELECT COUNT(*) INTO v_old_master_count FROM product_catalog WHERE sku_master IS NOT NULL;
    SELECT COUNT(*) INTO v_grbe_count FROM product_master_boxes WHERE product_sku = 'GRBE_U26010';
    SELECT items_per_master_box INTO v_grbe_ipmb FROM product_catalog WHERE sku = 'GRBE_U26010';

    RAISE NOTICE '';
    RAISE NOTICE '=== Migration 042 Verification ===';
    RAISE NOTICE 'Junction table rows: % (old product_catalog sku_master count: %)', v_junction_count, v_old_master_count;
    RAISE NOTICE 'Junction should have MORE rows than old count (new entries added)';
    RAISE NOTICE 'GRBE_U26010 master boxes: % (should be 2)', v_grbe_count;
    RAISE NOTICE 'GRBE_U26010 product_catalog.items_per_master_box: % (should be 10, not 20)', v_grbe_ipmb;
    RAISE NOTICE '';

    IF v_grbe_count != 2 THEN
        RAISE WARNING 'GRBE_U26010 should have exactly 2 master boxes, got %', v_grbe_count;
    END IF;

    IF v_grbe_ipmb != 10 THEN
        RAISE WARNING 'GRBE_U26010 items_per_master_box should be 10 (migration 041 hack not reverted), got %', v_grbe_ipmb;
    END IF;

    IF v_junction_count <= v_old_master_count THEN
        RAISE WARNING 'Junction table should have MORE rows than old count (new entries were added)';
    END IF;
END $$;
