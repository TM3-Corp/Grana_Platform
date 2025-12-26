-- Migration 024: Add missing PACK product mappings
-- Purpose: Complete PACK→base SKU mappings discovered from sales_facts_mv
-- Author: Claude Code
-- Date: 2025-12-17
--
-- PROBLEM:
-- Migration 022 added some PACK mappings, but sales_facts_mv revealed more:
-- - PACKBABE_U20010, PACKBACM_U20010, PACKBAKC_U20010, PACKBAMC_U20010 (Barras X5)
-- - PACKCRSM_U25020 (Crackers X7)
-- - PACKGRKC_U21010 (Granola Keto)
-- - PACKKSMC_U54010 (Keeper x18)
--
-- SOLUTION:
-- Add mappings with appropriate quantity multipliers

-- ============================================
-- 1. ADD MISSING PACK PRODUCT MAPPINGS
-- ============================================

-- BARRAS X5 variants (Pack 4)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, quantity_multiplier, rule_name, confidence, priority, notes, is_active)
VALUES
    ('PACKBABE_U20010', 'exact', 'BABE_U20010', 4, 'PACK prefix removal', 95, 80, 'Pack 4 Barra Low Carb Berries X5', TRUE),
    ('PACKBACM_U20010', 'exact', 'BACM_U20010', 4, 'PACK prefix removal', 95, 80, 'Pack 4 Barra Low Carb Cacao Mani X5', TRUE),
    ('PACKBAKC_U20010', 'exact', 'BAKC_U20010', 4, 'PACK prefix removal', 95, 80, 'Pack 4 Barra Keto Nuez X5', TRUE),
    ('PACKBAMC_U20010', 'exact', 'BAMC_U20010', 4, 'PACK prefix removal', 95, 80, 'Pack 4 Barra Low Carb Manzana Canela X5', TRUE)
ON CONFLICT (source_pattern, source_filter) WHERE pattern_type = 'exact' AND is_active = TRUE
DO UPDATE SET
    target_sku = EXCLUDED.target_sku,
    quantity_multiplier = EXCLUDED.quantity_multiplier,
    notes = EXCLUDED.notes,
    updated_at = NOW();

-- CRACKERS X7 variant (Pack 5)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, quantity_multiplier, rule_name, confidence, priority, notes, is_active)
VALUES
    ('PACKCRSM_U25020', 'exact', 'CRSM_U25020', 5, 'PACK prefix removal', 95, 80, 'Pack 5 Crackers Keto Sea Salt 25g X7', TRUE)
ON CONFLICT (source_pattern, source_filter) WHERE pattern_type = 'exact' AND is_active = TRUE
DO UPDATE SET
    target_sku = EXCLUDED.target_sku,
    quantity_multiplier = EXCLUDED.quantity_multiplier,
    notes = EXCLUDED.notes,
    updated_at = NOW();

-- GRANOLA variant (Pack 4)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, quantity_multiplier, rule_name, confidence, priority, notes, is_active)
VALUES
    ('PACKGRKC_U21010', 'exact', 'GRKC_U21010', 4, 'PACK prefix removal', 95, 80, 'Pack 4 Granola Keto Nuez 210g', TRUE)
ON CONFLICT (source_pattern, source_filter) WHERE pattern_type = 'exact' AND is_active = TRUE
DO UPDATE SET
    target_sku = EXCLUDED.target_sku,
    quantity_multiplier = EXCLUDED.quantity_multiplier,
    notes = EXCLUDED.notes,
    updated_at = NOW();

-- KEEPER X18 variant (Pack 4)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, quantity_multiplier, rule_name, confidence, priority, notes, is_active)
VALUES
    ('PACKKSMC_U54010', 'exact', 'KSMC_U54010', 4, 'PACK prefix removal', 95, 80, 'Pack 4 Keeper Mani 30g X18', TRUE)
ON CONFLICT (source_pattern, source_filter) WHERE pattern_type = 'exact' AND is_active = TRUE
DO UPDATE SET
    target_sku = EXCLUDED.target_sku,
    quantity_multiplier = EXCLUDED.quantity_multiplier,
    notes = EXCLUDED.notes,
    updated_at = NOW();

-- ============================================
-- 2. SPECIAL PACKS (VARIETY/HOLIDAY) - Mark as notes only
-- ============================================

-- These are variety packs that can't be mapped to a single product:
-- - PACKCRSURTIDO: Cracker variety pack
-- - PACKDIECIOCHO: 18th of September (Chilean holiday) special
-- - PACKGRSURTIDA: Granola variety pack
-- - PACKNAVIDAD: Christmas special pack
-- - PACKBASURTIDA: Barra variety pack
--
-- These should remain unmapped OR be added with multiplier=1 to their own
-- catalog entry if one exists.

-- Check if variety pack SKUs exist in product_catalog (without PACK prefix)
-- If they do, add mapping with multiplier=1

-- ============================================
-- 3. VERIFICATION
-- ============================================

-- Check all PACK mappings
SELECT source_pattern, target_sku, quantity_multiplier, notes
FROM sku_mappings
WHERE source_pattern LIKE 'PACK%'
ORDER BY source_pattern;

-- Count total PACK mappings
SELECT 'Total PACK mappings' as type, COUNT(*) as count
FROM sku_mappings
WHERE source_pattern LIKE 'PACK%' AND is_active = TRUE;
