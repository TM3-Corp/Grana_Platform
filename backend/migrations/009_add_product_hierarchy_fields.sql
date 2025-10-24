-- Migration 009: Add product hierarchy fields
-- Date: 2025-10-23
-- Purpose: Add category, subfamily, format, and master box fields to support proper product hierarchy

-- Add category field (Familia principal: GRANOLAS, BARRAS, CRACKERS, KEEPERS, etc.)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS category VARCHAR(100);

-- Add subfamily field (Subfamilia: "Granola Low Carb Almendras", "Barra Low Carb Cacao Maní", etc.)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS subfamily VARCHAR(200);

-- Add format field (Formato: "260g", "X1", "X5", "X16", "Sachet 40g", etc.)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS format VARCHAR(100);

-- Add package type (DISPLAY, GRANEL, DOYPACK, SACHET, BANDEJA, UNIDAD)
ALTER TABLE products
ADD COLUMN IF NOT EXISTS package_type VARCHAR(50);

-- Add units per display/package
ALTER TABLE products
ADD COLUMN IF NOT EXISTS units_per_package INTEGER;

-- Add master box SKU
ALTER TABLE products
ADD COLUMN IF NOT EXISTS master_box_sku VARCHAR(50);

-- Add master box name
ALTER TABLE products
ADD COLUMN IF NOT EXISTS master_box_name VARCHAR(200);

-- Add displays/items per master box
ALTER TABLE products
ADD COLUMN IF NOT EXISTS items_per_master_box INTEGER;

-- Add total units per master box
ALTER TABLE products
ADD COLUMN IF NOT EXISTS units_per_master_box INTEGER;

-- Create indexes for hierarchy queries
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_subfamily ON products(subfamily);
CREATE INDEX IF NOT EXISTS idx_products_format ON products(format);
CREATE INDEX IF NOT EXISTS idx_products_master_box_sku ON products(master_box_sku);

-- Add comments
COMMENT ON COLUMN products.category IS 'Product family: GRANOLAS, BARRAS, CRACKERS, KEEPERS, KRUMS';
COMMENT ON COLUMN products.subfamily IS 'Product subfamily: e.g., "Granola Low Carb Almendras", "Barra Low Carb Cacao Maní"';
COMMENT ON COLUMN products.format IS 'Product format: e.g., "260g", "X1", "X5", "X16", "Sachet 40g"';
COMMENT ON COLUMN products.package_type IS 'Package type: DISPLAY, GRANEL, DOYPACK, SACHET, BANDEJA, UNIDAD';
COMMENT ON COLUMN products.units_per_package IS 'Number of units in this package (e.g., 5 for X5 display)';
COMMENT ON COLUMN products.master_box_sku IS 'SKU of the master box containing this product';
COMMENT ON COLUMN products.master_box_name IS 'Name of the master box';
COMMENT ON COLUMN products.items_per_master_box IS 'Number of displays/packages in master box';
COMMENT ON COLUMN products.units_per_master_box IS 'Total number of individual units in master box';
