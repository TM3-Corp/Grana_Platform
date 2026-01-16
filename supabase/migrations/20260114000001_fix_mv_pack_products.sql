-- =============================================================================
-- FIX: Sync sales_facts_mv with Production
-- =============================================================================
-- Date: 2026-01-14
-- Issue: Local MV was using old definition, production was manually updated
-- Linear Issue: CORP-151
--
-- CHANGES:
-- 1. Add CAJA MASTER category logic for master box products
-- 2. Add sm_agg LATERAL JOIN to SUM multipliers for PACK products
--    (PACKNAVIDAD, PACKDIECIOCHO, etc. have multiple target SKUs)
-- 3. Use COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1)
--
-- This makes LOCAL match PRODUCTION exactly.
-- =============================================================================

-- Drop and recreate the materialized view
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

    -- FIXED: Add CAJA MASTER category for master box products
    COALESCE(
        pc_direct.category,
        CASE WHEN pc_master.sku IS NOT NULL THEN 'CAJA MASTER'::text ELSE NULL END::character varying,
        pc_mapped.category,
        CASE WHEN pc_mapped_master.sku IS NOT NULL THEN 'CAJA MASTER'::text ELSE NULL END::character varying
    ) AS category,

    COALESCE(pc_direct.package_type, pc_master.package_type, pc_mapped.package_type, pc_mapped_master.package_type) AS package_type,
    COALESCE(pc_direct.brand, pc_master.brand, pc_mapped.brand, pc_mapped_master.brand) AS brand,
    COALESCE(pc_direct.language, pc_master.language, pc_mapped.language, pc_mapped_master.language) AS language,
    COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, pc_mapped_master.units_per_display, 1) AS units_per_display,
    COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, pc_direct.items_per_master_box, pc_mapped.items_per_master_box) AS items_per_master_box,
    CASE
        WHEN pc_master.sku IS NOT NULL THEN true
        WHEN pc_mapped_master.sku IS NOT NULL THEN true
        ELSE false
    END AS is_caja_master,
    CASE
        WHEN pc_direct.sku IS NOT NULL THEN 'direct'::text
        WHEN pc_master.sku IS NOT NULL THEN 'caja_master'::text
        WHEN pc_mapped.sku IS NOT NULL THEN 'sku_mapping'::text
        WHEN pc_mapped_master.sku IS NOT NULL THEN 'sku_mapping_caja_master'::text
        ELSE 'unmapped'::text
    END AS match_type,
    sm_single.rule_name AS mapping_rule,

    -- FIXED: Use aggregated multiplier for PACK products
    COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier::bigint, 1::bigint) AS quantity_multiplier,

    ch.name AS channel_name,
    c.name AS customer_name,
    c.rut AS customer_rut,
    oi.quantity AS original_units_sold,

    -- FIXED: units_sold uses aggregated multiplier
    oi.quantity * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier::bigint, 1::bigint) AS units_sold,

    oi.subtotal AS revenue,
    oi.unit_price,
    oi.total,
    oi.tax_amount,
    o.id AS order_id,
    o.external_id AS order_external_id,
    o.invoice_status,
    o.payment_status,
    o.status AS order_status,
    o.created_at AS order_created_at
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN product_catalog pc_direct
    ON pc_direct.sku::text = upper(oi.product_sku::text)
    AND pc_direct.is_active = true
LEFT JOIN product_catalog pc_master
    ON pc_master.sku_master::text = upper(oi.product_sku::text)
    AND pc_master.is_active = true
    AND pc_direct.sku IS NULL

-- FIXED: sm_single gets first matching rule (for rule_name display)
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

-- FIXED: sm_agg sums ALL multipliers for PACK products (multiple components)
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

LEFT JOIN product_catalog pc_mapped
    ON pc_mapped.sku::text = sm_single.target_sku::text
    AND pc_mapped.is_active = true
LEFT JOIN product_catalog pc_mapped_master
    ON pc_mapped_master.sku_master::text = sm_single.target_sku::text
    AND pc_mapped_master.is_active = true
    AND pc_mapped.sku IS NULL
LEFT JOIN channels ch ON o.channel_id = ch.id
LEFT JOIN customers c ON o.customer_id = c.id
WHERE o.invoice_status::text = ANY (ARRAY['accepted'::text, 'accepted_objection'::text])
  AND o.status::text <> 'cancelled'::text;

-- Add comment documenting the fix
COMMENT ON MATERIALIZED VIEW sales_facts_mv IS 'Pre-aggregated sales facts for OLAP analytics.

FIXED (Migration 20260114000001):
- Added sm_agg LATERAL JOIN to handle PACK products with multiple components
- PACK products (PACKNAVIDAD, PACKDIECIOCHO, etc.) now correctly sum all multipliers
- Added CAJA MASTER category logic for master box products

SKU matching uses 4-path logic:
1. Direct match on product_catalog.sku → product_name
2. Match on product_catalog.sku_master → master_box_name (CAJA MASTER)
3a. Via sku_mappings → product_catalog.sku → mapped product data
3b. Via sku_mappings → product_catalog.sku_master → master_box_name
4. No match → fallback to order_items (unmapped)

Refresh: REFRESH MATERIALIZED VIEW sales_facts_mv;';

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_date_id ON sales_facts_mv(date_id);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_channel_id ON sales_facts_mv(channel_id);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_customer_id ON sales_facts_mv(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_category ON sales_facts_mv(category);
CREATE INDEX IF NOT EXISTS idx_sales_facts_mv_order_date ON sales_facts_mv(order_date);

-- Refresh with data
REFRESH MATERIALIZED VIEW sales_facts_mv;

-- Verification
DO $$
DECLARE
    row_count INTEGER;
    caja_master_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO row_count FROM sales_facts_mv;
    SELECT COUNT(*) INTO caja_master_count FROM sales_facts_mv WHERE category = 'CAJA MASTER';

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'MIGRATION VERIFICATION';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Total rows in MV: %', row_count;
    RAISE NOTICE 'CAJA MASTER rows: %', caja_master_count;
    RAISE NOTICE '============================================================';
END $$;
