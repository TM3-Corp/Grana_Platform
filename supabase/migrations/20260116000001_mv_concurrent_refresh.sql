-- =============================================================================
-- Enable CONCURRENT refresh for sales_facts_mv
-- =============================================================================
-- Date: 2026-01-16
-- Purpose: Add unique index to enable REFRESH MATERIALIZED VIEW CONCURRENTLY
--
-- BENEFITS:
-- - No read locks during refresh (users can query during refresh)
-- - Atomic swap (readers see either old or new data, never partial)
-- - Required for high-availability dashboards
--
-- REQUIREMENTS:
-- - Unique index on MV for CONCURRENTLY to work
-- - Adding order_item_id column for guaranteed uniqueness
--
-- PERFORMANCE:
-- - CONCURRENTLY is slightly slower (~10-20%) than regular refresh
-- - But eliminates blocking, which is worth the trade-off
-- =============================================================================

-- Drop and recreate the materialized view with order_item_id for unique index
DROP MATERIALIZED VIEW IF EXISTS sales_facts_mv;

CREATE MATERIALIZED VIEW sales_facts_mv AS
SELECT
    -- UNIQUE KEY: order_item_id for CONCURRENTLY refresh support
    oi.id AS order_item_id,

    to_char(o.order_date, 'YYYYMMDD'::text)::integer AS date_id,
    o.order_date,
    o.channel_id,
    o.customer_id,
    o.source,
    oi.product_sku AS original_sku,
    COALESCE(pc_direct.sku, pc_master.sku, pc_mapped.sku, pc_mapped_master.sku) AS catalog_sku,
    COALESCE(pc_direct.sku_primario, pc_master.sku_primario, pc_mapped.sku_primario, pc_mapped_master.sku_primario) AS sku_primario,
    COALESCE(pc_direct.product_name, pc_master.master_box_name, pc_mapped.product_name, pc_mapped_master.master_box_name, oi.product_name::text) AS product_name,

    -- Category from product_catalog (CAJA MASTER inherits actual category)
    COALESCE(
        pc_direct.category,
        pc_master.category,
        pc_mapped.category,
        pc_mapped_master.category
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

    -- units_sold with conversion factors
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
-- UNIQUE INDEX FOR CONCURRENTLY REFRESH
-- =============================================================================
-- This is REQUIRED for REFRESH MATERIALIZED VIEW CONCURRENTLY to work
CREATE UNIQUE INDEX idx_sales_facts_mv_unique_order_item
    ON sales_facts_mv(order_item_id);

-- =============================================================================
-- PERFORMANCE INDEXES
-- =============================================================================
CREATE INDEX idx_sales_facts_mv_date_id ON sales_facts_mv(date_id);
CREATE INDEX idx_sales_facts_mv_channel_id ON sales_facts_mv(channel_id);
CREATE INDEX idx_sales_facts_mv_customer_id ON sales_facts_mv(customer_id);
CREATE INDEX idx_sales_facts_mv_category ON sales_facts_mv(category);
CREATE INDEX idx_sales_facts_mv_order_date ON sales_facts_mv(order_date);
CREATE INDEX idx_sales_facts_mv_sku_primario ON sales_facts_mv(sku_primario);
CREATE INDEX idx_sales_facts_mv_source ON sales_facts_mv(source);
CREATE INDEX idx_sales_facts_mv_is_caja_master ON sales_facts_mv(is_caja_master);

-- Composite indexes for common query patterns
CREATE INDEX idx_sales_facts_mv_date_source_category
    ON sales_facts_mv(date_id, source, category)
    INCLUDE (revenue, units_sold);

CREATE INDEX idx_sales_facts_mv_date_source_channel
    ON sales_facts_mv(date_id, source, channel_id)
    INCLUDE (revenue, units_sold);

-- Refresh with data
REFRESH MATERIALIZED VIEW sales_facts_mv;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
DO $$
DECLARE
    row_count INTEGER;
    has_unique_index BOOLEAN;
    can_concurrent BOOLEAN;
BEGIN
    -- Verify row count
    SELECT COUNT(*) INTO row_count FROM sales_facts_mv;

    -- Check unique index exists
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'sales_facts_mv'
        AND indexdef LIKE '%UNIQUE%'
    ) INTO has_unique_index;

    -- Test CONCURRENTLY support (will work if unique index exists)
    can_concurrent := has_unique_index;

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'CONCURRENT REFRESH MIGRATION VERIFICATION';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Row count: %', row_count;
    RAISE NOTICE 'Has unique index: %', has_unique_index;
    RAISE NOTICE 'CONCURRENTLY refresh supported: %', can_concurrent;
    RAISE NOTICE '';
    RAISE NOTICE 'You can now use: REFRESH MATERIALIZED VIEW CONCURRENTLY sales_facts_mv;';
    RAISE NOTICE '============================================================';
END $$;

-- =============================================================================
-- DOCUMENTATION
-- =============================================================================
COMMENT ON MATERIALIZED VIEW sales_facts_mv IS 'Pre-aggregated sales facts for OLAP analytics.

NEW (Migration 20260116000001):
- Added order_item_id column for unique indexing
- Supports REFRESH MATERIALIZED VIEW CONCURRENTLY (no read locks during refresh)
- Atomic refresh: readers see either old or new data, never partial

Previous fixes:
- Migration 20260115000001: Category inheritance for CAJA MASTER
- Migration 20260114180000: units_sold conversion factors
- Migration 20260114000001: PACK products aggregation

SKU matching uses 4-path logic:
1. Direct match on product_catalog.sku
2. Match on product_catalog.sku_master (CAJA MASTER)
3. Via sku_mappings → product_catalog
4. No match → unmapped

Refresh: REFRESH MATERIALIZED VIEW CONCURRENTLY sales_facts_mv;';
