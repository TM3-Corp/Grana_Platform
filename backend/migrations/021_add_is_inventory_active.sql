-- Migration 021: Add is_inventory_active column to product_catalog
-- Purpose: Allow hiding products from Inventario General view
-- Author: Claude Code
-- Date: 2025-12-17
--
-- PROBLEM:
-- - Some products in inventory should be hidden (discontinued, samples, etc.)
-- - No way to mark products as inactive for inventory purposes
--
-- SOLUTION:
-- Add is_inventory_active BOOLEAN column (default TRUE)
-- When FALSE, product is hidden from Inventario General

-- ============================================
-- 1. ADD COLUMN
-- ============================================

ALTER TABLE product_catalog
ADD COLUMN IF NOT EXISTS is_inventory_active BOOLEAN DEFAULT TRUE;

-- ============================================
-- 2. ADD COMMENT
-- ============================================

COMMENT ON COLUMN product_catalog.is_inventory_active IS
'When FALSE, this SKU is hidden from Inventario General view.
Used for discontinued products or SKUs we do not want to track in inventory.
Default TRUE - all products show by default.';

-- ============================================
-- 3. CREATE PARTIAL INDEX FOR ACTIVE PRODUCTS
-- ============================================

-- This index optimizes queries that filter for active inventory products
CREATE INDEX IF NOT EXISTS idx_product_catalog_is_inventory_active
ON product_catalog(is_inventory_active)
WHERE is_inventory_active = TRUE;

-- ============================================
-- 4. VERIFICATION
-- ============================================

-- Check that column was added
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'product_catalog'
AND column_name = 'is_inventory_active';
