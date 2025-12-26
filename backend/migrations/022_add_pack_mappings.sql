-- Migration 022: Add PACK product mappings to sku_mappings
-- Purpose: Map PACK SKUs to their base product catalog SKUs with quantity multipliers
-- Author: Claude Code
-- Date: 2025-12-17
--
-- PROBLEM:
-- - Inventory has PACK products (PACKGRCA_U26010, PACKCRPM_U13510, etc.)
-- - These need to be consolidated under their base SKUs (GRCA_U26010, CRPM_U13510)
-- - Each PACK has a quantity multiplier (e.g., Pack 4 = 4x, Pack 5 = 5x)
--
-- SOLUTION:
-- Add exact mappings to sku_mappings with quantity_multiplier
-- This allows inventory consolidation using the same logic as order mapping

-- ============================================
-- 1. ADD PACK PRODUCT MAPPINGS
-- ============================================

-- Note: These mappings have source_filter = NULL (apply to all sources)
-- The unique constraint is on (source_pattern, source_filter) WHERE pattern_type = 'exact' AND is_active = TRUE

-- GRANOLAS (Pack 4)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, quantity_multiplier, rule_name, confidence, priority, notes, is_active)
VALUES
  ('PACKGRCA_U26010', 'exact', 'GRCA_U26010', 4, 'PACK prefix removal', 95, 80, 'Pack 4 Granola Low Carb Cacao 260 Grs', TRUE),
  ('PACKGRAL_U26010', 'exact', 'GRAL_U26010', 4, 'PACK prefix removal', 95, 80, 'Pack 4 Granola Low Carb Almendras 260 Grs', TRUE),
  ('PACKGRBE_U26010', 'exact', 'GRBE_U26010', 4, 'PACK prefix removal', 95, 80, 'Pack 4 Granola Low Carb Berries 260 Grs', TRUE)
ON CONFLICT (source_pattern, source_filter) WHERE pattern_type = 'exact' AND is_active = TRUE
DO UPDATE SET
  target_sku = EXCLUDED.target_sku,
  quantity_multiplier = EXCLUDED.quantity_multiplier,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- CRACKERS (Pack 5)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, quantity_multiplier, rule_name, confidence, priority, notes, is_active)
VALUES
  ('PACKCRPM_U13510', 'exact', 'CRPM_U13510', 5, 'PACK prefix removal', 95, 80, 'Pack 5 Crackers Keto Pimienta 135 Grs', TRUE),
  ('PACKCRSM_U13510', 'exact', 'CRSM_U13510', 5, 'PACK prefix removal', 95, 80, 'Pack 5 Crackers Keto Sesamo Maravilla 135 Grs', TRUE),
  ('PACKCRRO_U13510', 'exact', 'CRRO_U13510', 5, 'PACK prefix removal', 95, 80, 'Pack 5 Crackers Keto Romero 135 Grs', TRUE),
  ('PACKCRAA_U13510', 'exact', 'CRAA_U13510', 5, 'PACK prefix removal', 95, 80, 'Pack 5 Crackers Keto Ajo Albahaca 135 Grs', TRUE)
ON CONFLICT (source_pattern, source_filter) WHERE pattern_type = 'exact' AND is_active = TRUE
DO UPDATE SET
  target_sku = EXCLUDED.target_sku,
  quantity_multiplier = EXCLUDED.quantity_multiplier,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- BARRAS (Pack variants - add more as discovered)
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, quantity_multiplier, rule_name, confidence, priority, notes, is_active)
VALUES
  ('PACKBAMC_U04010', 'exact', 'BAMC_U04010', 5, 'PACK prefix removal', 95, 80, 'Pack 5 Barra Low Carb Manzana Canela 40 Grs', TRUE),
  ('PACKBAKC_U04010', 'exact', 'BAKC_U04010', 5, 'PACK prefix removal', 95, 80, 'Pack 5 Barra Low Carb Keto Chocolate Nuez 40 Grs', TRUE),
  ('PACKBACM_U04010', 'exact', 'BACM_U04010', 5, 'PACK prefix removal', 95, 80, 'Pack 5 Barra Low Carb Cacao Mani 40 Grs', TRUE),
  ('PACKBABE_U04010', 'exact', 'BABE_U04010', 5, 'PACK prefix removal', 95, 80, 'Pack 5 Barra Low Carb Sour Berries 40 Grs', TRUE)
ON CONFLICT (source_pattern, source_filter) WHERE pattern_type = 'exact' AND is_active = TRUE
DO UPDATE SET
  target_sku = EXCLUDED.target_sku,
  quantity_multiplier = EXCLUDED.quantity_multiplier,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ============================================
-- 2. VERIFICATION
-- ============================================

-- Check PACK mappings were added
SELECT source_pattern, target_sku, quantity_multiplier, notes
FROM sku_mappings
WHERE source_pattern LIKE 'PACK%'
ORDER BY source_pattern;

-- Count total mappings
SELECT 'Total PACK mappings' as type, COUNT(*) as count
FROM sku_mappings
WHERE source_pattern LIKE 'PACK%' AND is_active = TRUE;
