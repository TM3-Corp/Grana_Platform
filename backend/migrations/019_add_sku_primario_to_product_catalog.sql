-- Migration 019: Add sku_primario column to product_catalog
-- Purpose: Store explicit primary/unit SKU relationship for each product
--
-- This replaces the dynamic calculation in product_catalog_service.py
-- which had issues with:
-- 1. Ambiguous base_codes (multiple products with units_per_display=1)
-- 2. Missing primarios (base_codes with no units_per_display=1 product)
--
-- Author: TM3
-- Date: 2025-12-16

-- Step 1: Add the column (nullable initially)
ALTER TABLE product_catalog
ADD COLUMN IF NOT EXISTS sku_primario VARCHAR(50);

-- Step 2: Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_product_catalog_sku_primario
ON product_catalog(sku_primario);

-- Step 3: Add comment explaining the column
COMMENT ON COLUMN product_catalog.sku_primario IS
'Primary/unit SKU for this product family. For unit SKUs, this is themselves. For packs/displays, this is the base unit SKU.';

-- Step 4: Populate sku_primario for products that ARE the primario (units_per_display = 1, ESPAÑOL)
-- These products point to themselves
UPDATE product_catalog
SET sku_primario = sku
WHERE units_per_display = 1
AND UPPER(language) = 'ESPAÑOL'
AND sku_primario IS NULL;

-- Step 5: For pack products (units_per_display > 1), find their primario
-- This uses the same logic as before but EXPLICITLY stores the relationship
-- Note: This handles the simple cases where there's only ONE primario candidate
UPDATE product_catalog pc
SET sku_primario = (
    SELECT p2.sku
    FROM product_catalog p2
    WHERE p2.base_code = pc.base_code
    AND p2.units_per_display = 1
    AND UPPER(p2.language) = 'ESPAÑOL'
    LIMIT 1  -- Take first match for now (will need manual review for ambiguous cases)
)
WHERE pc.units_per_display > 1
AND pc.base_code IS NOT NULL
AND pc.sku_primario IS NULL;

-- Step 6: Also set sku_primario for master box SKUs (sku_master)
-- These should point to the same primario as their unit counterpart
UPDATE product_catalog pc
SET sku_primario = (
    SELECT p2.sku
    FROM product_catalog p2
    WHERE p2.base_code = pc.base_code
    AND p2.units_per_display = 1
    AND UPPER(p2.language) = 'ESPAÑOL'
    LIMIT 1
)
WHERE pc.is_master_sku = TRUE
AND pc.base_code IS NOT NULL
AND pc.sku_primario IS NULL;

-- Verification queries (run these after migration to check results):
--
-- Check products without sku_primario:
-- SELECT sku, base_code, units_per_display, language FROM product_catalog WHERE sku_primario IS NULL;
--
-- Check ambiguous base_codes that need manual review:
-- SELECT base_code, COUNT(*) as candidates
-- FROM product_catalog
-- WHERE units_per_display = 1 AND UPPER(language) = 'ESPAÑOL'
-- GROUP BY base_code HAVING COUNT(*) > 1;
