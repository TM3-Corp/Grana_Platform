-- Migration 041: Fix GRBE items_per_master_box (10 → 20)
-- Date: 2026-02-18
--
-- PROBLEM:
-- GRBE_U26010 (Granola Low Carb Berries 260) had items_per_master_box = 10,
-- but the actual caja master sold (GRBE_C02010) contains 20 units.
--
-- EVIDENCE:
-- 1. SKU naming convention: _C02010 = 20 units (GRCA_C02010=20, GRKC_C02010=20)
--    vs _C01010 = 10 units (13 products, all 10)
-- 2. Zero orders exist with GRBE_C01010 (the 10-unit sku_master)
-- 3. All 304 caja master orders in 2025 use GRBE_C02010
-- 4. With 20 units/box: 6,340 total units (matches client's ~6,700 estimate)
--    With 10 units/box: 3,300 total units (half of reality)
-- 5. Pricing: $31,360/box ÷ 20 = $1,568/unit (reasonable B2B discount)
--    vs $31,360/box ÷ 10 = $3,136/unit (MORE than individual $2,772, nonsensical)
--
-- FIX: Update items_per_master_box from 10 to 20.
-- The sku_master stays as GRBE_C01010 (all sku_mappings route through it).
-- After update, REFRESH MATERIALIZED VIEW to propagate.

UPDATE product_catalog
SET items_per_master_box = 20,
    updated_at = NOW()
WHERE sku = 'GRBE_U26010'
  AND items_per_master_box = 10;

-- Refresh MV to pick up the new conversion factor
REFRESH MATERIALIZED VIEW CONCURRENTLY sales_facts_mv;
