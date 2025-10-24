-- Migration 008: Add description and product_id fields to relbase_product_mappings
-- Date: 2025-10-23
-- Purpose: Enable better product mapping using detailed description field and stable product_id

-- Add description column (contains detailed package information for ANU- codes)
ALTER TABLE relbase_product_mappings
ADD COLUMN IF NOT EXISTS description TEXT;

-- Add product_id_relbase column (Relbase's internal stable identifier)
-- Note: Different from product_id which is FK to products table
ALTER TABLE relbase_product_mappings
ADD COLUMN IF NOT EXISTS product_id_relbase INTEGER;

-- Add url_image column (product image URL for visual validation)
ALTER TABLE relbase_product_mappings
ADD COLUMN IF NOT EXISTS url_image TEXT;

-- Create index on product_id_relbase for faster lookups
CREATE INDEX IF NOT EXISTS idx_relbase_mappings_product_id_relbase ON relbase_product_mappings(product_id_relbase);

-- Add comment
COMMENT ON COLUMN relbase_product_mappings.description IS
'Detailed product description from Relbase API - critical for parsing ANU- code package information';

COMMENT ON COLUMN relbase_product_mappings.product_id_relbase IS
'Relbase internal product ID - stable identifier that does not change even if code changes';

COMMENT ON COLUMN relbase_product_mappings.url_image IS
'Product image URL from Relbase - useful for visual confirmation during manual mapping';

-- Migration complete
-- Next steps:
-- 1. Re-load Relbase data with new fields
-- 2. Run description parser to extract product info
-- 3. Update product mappings with parsed data
