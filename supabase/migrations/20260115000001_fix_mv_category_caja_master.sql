-- =============================================================================
-- FIX: CAJA MASTER products should inherit category from product_catalog
-- =============================================================================
-- Date: 2026-01-15
-- Issue: Category filter shows 695,716 units when selecting all categories,
--        but total is 1,251,827 units. Missing 184,200 units from CAJA MASTER
--        which was hardcoded as category='CAJA MASTER' instead of using the
--        actual product category (BARRAS, CRACKERS, etc.)
--
-- ROOT CAUSE:
-- The category logic was:
--   CASE WHEN pc_master.sku IS NOT NULL THEN 'CAJA MASTER' ...
--
-- But it should use the product's actual category from the catalog.
--
-- VERIFICATION:
-- All master boxes have a single category in product_catalog:
--   - BARRAS: 27 cajas master
--   - CRACKERS: 24 cajas master
--   - GRANOLAS: 18 cajas master
--   - KEEPERS: 6 cajas master
--   - KRUMS: 6 cajas master
--   - GALLETAS: 1 caja master
--
-- No mixed boxes exist, so we can safely use the catalog category.
-- =============================================================================

-- Drop and recreate the materialized view with corrected category logic
DROP MATERIALIZED VIEW IF EXISTS sales_facts_mv;

CREATE MATERIALIZED VIEW sales_facts_mv AS
SELECT
    to_char(o.order_date, 'YYYYMMDD'::text)::integer AS date_id,
    o.order_date,
    o.channel_id,
    o.customer_id,
    o.source,
    oi.product_sku AS original_sku,
    COALESCE(pc_direct.sku, pc_master.sku, pc_mapped.sku, pc_mapped_master.sku) AS catalog_sku,
    COALESCE(pc_direct.sku_primario, pc_master.sku_primario, pc_mapped.sku_primario, pc_mapped_master.sku_primario) AS sku_primario,
    COALESCE(pc_direct.product_name, pc_master.master_box_name, pc_mapped.product_name, pc_mapped_master.master_box_name, oi.product_name::text) AS product_name,

    -- ==========================================================================
    -- FIXED: Category now uses product_catalog.category for ALL products
    -- ==========================================================================
    -- Previously: CAJA MASTER products got hardcoded category='CAJA MASTER'
    -- Now: CAJA MASTER products inherit their actual category (BARRAS, CRACKERS, etc.)
    -- ==========================================================================
    COALESCE(
        pc_direct.category,
        pc_master.category,          -- Use catalog category (not hardcoded 'CAJA MASTER')
        pc_mapped.category,
        pc_mapped_master.category    -- Use catalog category (not hardcoded 'CAJA MASTER')
    ) AS category,

    COALESCE(pc_direct.package_type, pc_master.package_type, pc_mapped.package_type, pc_mapped_master.package_type) AS package_type,
    COALESCE(pc_direct.brand, pc_master.brand, pc_mapped.brand, pc_mapped_master.brand) AS brand,
    COALESCE(pc_direct.language, pc_master.language, pc_mapped.language, pc_mapped_master.language) AS language,

    -- Conversion factors (for reference and post-hoc calculations)
    COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, pc_mapped_master.units_per_display, 1) AS units_per_display,
    COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, pc_direct.items_per_master_box, pc_mapped.items_per_master_box) AS items_per_master_box,

    -- Is this a CAJA MASTER product? (kept for reference/filtering)
    CASE
        WHEN pc_master.sku IS NOT NULL THEN true
        WHEN pc_mapped_master.sku IS NOT NULL THEN true
        ELSE false
    END AS is_caja_master,

    -- Match type for debugging
    CASE
        WHEN pc_direct.sku IS NOT NULL THEN 'direct'::text
        WHEN pc_master.sku IS NOT NULL THEN 'caja_master'::text
        WHEN pc_mapped.sku IS NOT NULL THEN 'sku_mapping'::text
        WHEN pc_mapped_master.sku IS NOT NULL THEN 'sku_mapping_caja_master'::text
        ELSE 'unmapped'::text
    END AS match_type,
    sm_single.rule_name AS mapping_rule,

    -- SKU mapping multiplier (for PACK products with multiple components)
    COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier::bigint, 1::bigint) AS quantity_multiplier,

    -- Denormalized fields for performance
    ch.name AS channel_name,
    c.name AS customer_name,
    c.rut AS customer_rut,

    -- Original quantity from order (before any conversion)
    oi.quantity AS original_units_sold,

    -- units_sold with conversion factors (from migration 20260114180000)
    (
        oi.quantity
        * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier::bigint, 1::bigint)
        * CASE
            WHEN (pc_master.sku IS NOT NULL OR pc_mapped_master.sku IS NOT NULL)
                THEN COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, 1)::bigint
            ELSE
                COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, 1)::bigint
          END
    ) AS units_sold,

    -- Revenue and pricing
    oi.subtotal AS revenue,
    oi.unit_price,
    oi.total,
    oi.tax_amount,

    -- Order metadata
    o.id AS order_id,
    o.external_id AS order_external_id,
    o.invoice_status,
    o.payment_status,
    o.status AS order_status,
    o.created_at AS order_created_at

FROM orders o
JOIN order_items oi ON o.id = oi.order_id

-- PATH 1: Direct match on product_catalog.sku
LEFT JOIN product_catalog pc_direct
    ON pc_direct.sku::text = upper(oi.product_sku::text)
    AND pc_direct.is_active = true

-- PATH 2: Match on product_catalog.sku_master (CAJA MASTER)
LEFT JOIN product_catalog pc_master
    ON pc_master.sku_master::text = upper(oi.product_sku::text)
    AND pc_master.is_active = true
    AND pc_direct.sku IS NULL

-- PATH 3a: Single SKU mapping (for rule_name display)
LEFT JOIN LATERAL (
    SELECT sm.target_sku, sm.quantity_multiplier, sm.rule_name
    FROM sku_mappings sm
    WHERE sm.source_pattern::text = upper(oi.product_sku::text)
      AND sm.pattern_type::text = 'exact'::text
      AND sm.is_active = true
      AND pc_direct.sku IS NULL
      AND pc_master.sku IS NULL
    ORDER BY sm.id
    LIMIT 1
) sm_single ON true

-- PATH 3b: Aggregated multiplier for PACK products (multiple components)
LEFT JOIN LATERAL (
    SELECT sum(COALESCE(sm2.quantity_multiplier, 1)) AS total_multiplier
    FROM sku_mappings sm2
    WHERE sm2.source_pattern::text = upper(oi.product_sku::text)
      AND sm2.pattern_type::text = 'exact'::text
      AND sm2.is_active = true
      AND pc_direct.sku IS NULL
      AND pc_master.sku IS NULL
    HAVING count(*) > 1
) sm_agg ON true

-- PATH 4a: Via sku_mappings → product_catalog.sku
LEFT JOIN product_catalog pc_mapped
    ON pc_mapped.sku::text = sm_single.target_sku::text
    AND pc_mapped.is_active = true

-- PATH 4b: Via sku_mappings → product_catalog.sku_master
LEFT JOIN product_catalog pc_mapped_master
    ON pc_mapped_master.sku_master::text = sm_single.target_sku::text
    AND pc_mapped_master.is_active = true
    AND pc_mapped.sku IS NULL

-- Join channel and customer for denormalization
LEFT JOIN channels ch ON o.channel_id = ch.id
LEFT JOIN customers c ON o.customer_id = c.id

-- Only include accepted invoices (SII validation)
WHERE o.invoice_status::text = ANY (ARRAY['accepted'::text, 'accepted_objection'::text])
  AND o.status::text <> 'cancelled'::text;

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_date_id ON sales_facts_mv(date_id);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_channel_id ON sales_facts_mv(channel_id);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_customer_id ON sales_facts_mv(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_category ON sales_facts_mv(category);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_order_date ON sales_facts_mv(order_date);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_sku_primario ON sales_facts_mv(sku_primario);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_source ON sales_facts_mv(source);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_is_caja_master ON sales_facts_mv(is_caja_master);

-- Refresh with data
REFRESH MATERIALIZED VIEW sales_facts_mv;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
DO $$
DECLARE
    caja_master_category TEXT;
    caja_master_count INTEGER;
    barras_units BIGINT;
    total_with_category BIGINT;
    total_null_category BIGINT;
BEGIN
    -- Check that no rows have category='CAJA MASTER' anymore
    SELECT COUNT(*) INTO caja_master_count
    FROM sales_facts_mv WHERE category = 'CAJA MASTER';

    -- Get units for BARRAS (should include CAJA MASTER de BARRAS now)
    SELECT COALESCE(SUM(units_sold), 0) INTO barras_units
    FROM sales_facts_mv
    WHERE source = 'relbase' AND category = 'BARRAS';

    -- Get total with valid category
    SELECT COALESCE(SUM(units_sold), 0) INTO total_with_category
    FROM sales_facts_mv
    WHERE source = 'relbase'
      AND category IN ('BARRAS', 'CRACKERS', 'GRANOLAS', 'KEEPERS', 'KRUMS', 'GALLETAS');

    -- Get total with NULL category
    SELECT COALESCE(SUM(units_sold), 0) INTO total_null_category
    FROM sales_facts_mv
    WHERE source = 'relbase' AND category IS NULL;

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'CATEGORY FIX VERIFICATION';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Rows with category=CAJA MASTER: % (should be 0)', caja_master_count;
    RAISE NOTICE '';
    RAISE NOTICE 'BARRAS units (now includes CAJA MASTER de BARRAS): %', barras_units;
    RAISE NOTICE 'Total with valid category: %', total_with_category;
    RAISE NOTICE 'Total with NULL category (unmapped): %', total_null_category;
    RAISE NOTICE '';
    RAISE NOTICE 'Expected: ~880,000 units with category (was 695,716 + 184,200)';
    RAISE NOTICE '============================================================';
END $$;

-- =============================================================================
-- DOCUMENTATION
-- =============================================================================
COMMENT ON MATERIALIZED VIEW sales_facts_mv IS 'Pre-aggregated sales facts for OLAP analytics.

FIXED (Migration 20260115000001):
- Category now uses product_catalog.category for ALL products
- CAJA MASTER products inherit their actual category (BARRAS, CRACKERS, etc.)
- Previously 184,200 units were categorized as "CAJA MASTER" instead of their real category

Previous fixes:
- Migration 20260114180000 (CORP-162): units_sold conversion factors
- Migration 20260114000001: PACK products aggregation

SKU matching uses 4-path logic:
1. Direct match on product_catalog.sku
2. Match on product_catalog.sku_master (CAJA MASTER)
3. Via sku_mappings → product_catalog
4. No match → unmapped

Refresh: REFRESH MATERIALIZED VIEW sales_facts_mv;';
