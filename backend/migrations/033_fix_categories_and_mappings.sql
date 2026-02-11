-- Migration 033: Fix __new__ categories and add missing SKU mappings
-- Purpose:
-- 1. Eliminate '__new__' category label by reassigning to 'DESPACHOS' or 'OTROS'
-- 2. Add mappings for known unmapped RelBase SKUs (Despacho, etc.)

BEGIN;

-- =====================================================================
-- 1. Fix '__new__' categories in product_catalog
-- =====================================================================

-- Update Despacho-related products
UPDATE product_catalog
SET category = 'DESPACHOS',
    updated_at = NOW()
WHERE category = '__new__'
  AND (product_name ILIKE '%Despacho%' OR product_name ILIKE '%Envío%' OR product_name ILIKE '%Delivery%');

-- Update Ajustes and others to OTROS
UPDATE product_catalog
SET category = 'OTROS',
    updated_at = NOW()
WHERE category = '__new__';

-- =====================================================================
-- 2. Add Missing SKU Mappings
-- =====================================================================

-- Insert mappings for legacy/unmapped SKUs to canonical targets.
-- using ON CONFLICT DO NOTHING to ensure idempotency.

INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, rule_name, confidence, priority, notes)
VALUES
    -- Despacho Mappings
    ('ANU-D-DW-995240', 'exact', 'D-D-942609', 'Despacho Web Relbase', 95, 90, 'Fix unmapped Despacho Web'),
    ('ANU-01', 'exact', 'D-D-942609', 'Despacho Generic', 95, 90, 'Fix unmapped Despacho'),
    ('DESPACHO', 'exact', 'D-D-942609', 'Despacho Simple', 95, 90, 'Fix unmapped Despacho'),
    
    -- Other Mappings
    ('ANU-EMPORIO_BAketo5ud', 'exact', 'BAKC_U20010', 'Barra Keto Display 5', 90, 80, 'Inferred from name'),
    ('WEB_DESphysalis', 'exact', 'OTROS', 'Chips de Physalis', 80, 80, 'Legacy unmapped item')

ON CONFLICT (source_pattern, source_filter) WHERE pattern_type = 'exact' AND is_active = TRUE
DO NOTHING;

-- =====================================================================
-- 3. Refresh the view to apply changes
-- =====================================================================
REFRESH MATERIALIZED VIEW sales_facts_mv;

COMMIT;
