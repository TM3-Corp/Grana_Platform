-- =============================================================================
-- FIX: Apply conversion factors to units_sold in sales_facts_mv
-- =============================================================================
-- Date: 2026-01-14 18:00
-- Issue: CORP-162 - units_sold missing conversion factors (80-99% under-reported)
-- Linear Issue: https://linear.app/tm3ai/issue/CORP-162
--
-- ROOT CAUSE:
-- The units_sold calculation was:
--   oi.quantity * quantity_multiplier
--
-- But it should be:
--   oi.quantity * quantity_multiplier * conversion_factor
--
-- Where conversion_factor is:
--   - items_per_master_box (for CAJA MASTER products: 140, 72, etc.)
--   - units_per_display (for regular products: X5=5, X16=16, etc.)
--
-- IMPACT:
-- - Dashboard KPIs: 17-99% under-reported
-- - Sales Analytics: incorrect volume charts
-- - Inventory Planning: production calculations wrong
--
-- VERIFICATION (from notebooks):
-- Before fix: 1,038,054 units (wrong)
-- After fix:  1,251,122 units (correct)
-- Difference: +213,068 units (+20.5%)
--
-- =============================================================================

-- Drop and recreate the materialized view with corrected formula
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

    -- Category logic (inherited from previous migration)
    COALESCE(
        pc_direct.category,
        CASE WHEN pc_master.sku IS NOT NULL THEN 'CAJA MASTER'::text ELSE NULL END::character varying,
        pc_mapped.category,
        CASE WHEN pc_mapped_master.sku IS NOT NULL THEN 'CAJA MASTER'::text ELSE NULL END::character varying
    ) AS category,

    COALESCE(pc_direct.package_type, pc_master.package_type, pc_mapped.package_type, pc_mapped_master.package_type) AS package_type,
    COALESCE(pc_direct.brand, pc_master.brand, pc_mapped.brand, pc_mapped_master.brand) AS brand,
    COALESCE(pc_direct.language, pc_master.language, pc_mapped.language, pc_mapped_master.language) AS language,

    -- Conversion factors (for reference and post-hoc calculations)
    COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, pc_mapped_master.units_per_display, 1) AS units_per_display,
    COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, pc_direct.items_per_master_box, pc_mapped.items_per_master_box) AS items_per_master_box,

    -- Is this a CAJA MASTER product?
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

    -- ==========================================================================
    -- FIXED: units_sold now applies conversion factors
    -- ==========================================================================
    -- Formula: quantity * sku_mapping_multiplier * conversion_factor
    --
    -- Where conversion_factor is:
    --   - items_per_master_box for CAJA MASTER products
    --   - units_per_display for regular products (X1=1, X5=5, X16=16, etc.)
    --
    -- Examples:
    --   BAKC_U04010 (X1):  10 qty × 1 multiplier × 1 units_per_display = 10 units
    --   BAKC_U20010 (X5):  10 qty × 1 multiplier × 5 units_per_display = 50 units
    --   BAKC_C02810 (CM):  2 qty × 1 multiplier × 140 items_per_master = 280 units
    --   PACKNAVIDAD:       1 qty × 8 multiplier × 1 = 8 units (8 items in pack)
    -- ==========================================================================
    (
        oi.quantity
        * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier::bigint, 1::bigint)
        * CASE
            -- For CAJA MASTER products: multiply by items_per_master_box
            WHEN (pc_master.sku IS NOT NULL OR pc_mapped_master.sku IS NOT NULL)
                THEN COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, 1)::bigint
            -- For regular products: multiply by units_per_display
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
-- DOCUMENTATION
-- =============================================================================
COMMENT ON MATERIALIZED VIEW sales_facts_mv IS 'Pre-aggregated sales facts for OLAP analytics.

FIXED (Migration 20260114180000 - CORP-162):
- units_sold now correctly applies conversion factors:
  * items_per_master_box for CAJA MASTER products
  * units_per_display for regular products (X1, X5, X16, etc.)
- Formula: quantity × quantity_multiplier × conversion_factor

Previous fixes (Migration 20260114000001):
- Added sm_agg LATERAL JOIN for PACK products (multiple components)
- Added CAJA MASTER category logic

SKU matching uses 4-path logic:
1. Direct match on product_catalog.sku → product_name
2. Match on product_catalog.sku_master → master_box_name (CAJA MASTER)
3a. Via sku_mappings → product_catalog.sku → mapped product data
3b. Via sku_mappings → product_catalog.sku_master → master_box_name
4. No match → fallback to order_items (unmapped)

Refresh: REFRESH MATERIALIZED VIEW sales_facts_mv;';

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

-- Refresh with data
REFRESH MATERIALIZED VIEW sales_facts_mv;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
DO $$
DECLARE
    row_count INTEGER;
    old_units BIGINT;
    new_units BIGINT;
    caja_master_units BIGINT;
    regular_units BIGINT;
BEGIN
    -- Get total row count
    SELECT COUNT(*) INTO row_count FROM sales_facts_mv;

    -- Get new units total (with conversion factors applied)
    SELECT COALESCE(SUM(units_sold), 0) INTO new_units FROM sales_facts_mv;

    -- Get original units (without conversion - for comparison)
    SELECT COALESCE(SUM(original_units_sold * quantity_multiplier), 0) INTO old_units FROM sales_facts_mv;

    -- Breakdown by type
    SELECT COALESCE(SUM(units_sold), 0) INTO caja_master_units
    FROM sales_facts_mv WHERE is_caja_master = true;

    SELECT COALESCE(SUM(units_sold), 0) INTO regular_units
    FROM sales_facts_mv WHERE is_caja_master = false;

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'CORP-162 FIX VERIFICATION - units_sold Conversion Factors';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Total rows in MV: %', row_count;
    RAISE NOTICE '';
    RAISE NOTICE 'UNITS COMPARISON:';
    RAISE NOTICE '  Before fix (qty × multiplier only): %', old_units;
    RAISE NOTICE '  After fix (with conversion factors): %', new_units;
    RAISE NOTICE '  Difference: +% units (+% %%)',
        new_units - old_units,
        ROUND(((new_units::decimal - old_units::decimal) / NULLIF(old_units::decimal, 0)) * 100, 1);
    RAISE NOTICE '';
    RAISE NOTICE 'BREAKDOWN BY TYPE:';
    RAISE NOTICE '  CAJA MASTER units: %', caja_master_units;
    RAISE NOTICE '  Regular units: %', regular_units;
    RAISE NOTICE '';
    RAISE NOTICE 'Expected from notebook analysis:';
    RAISE NOTICE '  Before: ~1,038,054';
    RAISE NOTICE '  After:  ~1,251,122';
    RAISE NOTICE '============================================================';
END $$;
