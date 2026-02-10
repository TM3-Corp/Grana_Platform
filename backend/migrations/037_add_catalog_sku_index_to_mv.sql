-- Migration 037: Add indexes on catalog_sku and original_sku to sales_facts_mv
--
-- The velocity calculation in warehouse-inventory/general now uses catalog_sku
-- instead of original_sku to capture all variant SKU sales (ANU-, _WEB, ML listings).
-- These indexes are critical for performance since the velocity subqueries run
-- once per inventory SKU row.
--
-- Date: 2026-02-09

-- Index on catalog_sku for the primary velocity lookup
CREATE INDEX IF NOT EXISTS idx_sales_mv_catalog_sku
    ON sales_facts_mv(catalog_sku);

-- Index on original_sku for the fallback when catalog_sku IS NULL
CREATE INDEX IF NOT EXISTS idx_sales_mv_original_sku
    ON sales_facts_mv(original_sku);

-- Composite index for the velocity date-range query pattern:
-- WHERE (catalog_sku = X OR ...) AND order_date >= Y
-- INCLUDE units_sold so it's an index-only scan
CREATE INDEX IF NOT EXISTS idx_sales_mv_catalog_sku_date
    ON sales_facts_mv(catalog_sku, order_date) INCLUDE (units_sold);
