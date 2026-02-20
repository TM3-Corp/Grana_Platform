-- Migration 043: Rebuild MV to use product_master_boxes junction table
-- Date: 2026-02-20
--
-- Changes from migration 040:
-- A. Path 2 (caja master direct): Join through product_master_boxes instead of product_catalog.sku_master
-- B. Path 4 (sku_mapping -> caja master): Same junction table pattern
-- C. Remove is_active = TRUE filter from product_catalog joins (inactive products should appear in sales history)
-- D. items_per_master_box now reads from junction table (pmb/pmb_mapped), not product_catalog
-- E. is_caja_master uses pmb.sku_master IS NOT NULL instead of pc_master.sku IS NOT NULL
-- F. master_box_name from junction table
--
-- The junction table's is_active flag controls whether a specific box size is currently in use.
-- The product_catalog's is_active flag is NOT filtered — all products appear in sales history.

-- ============================================
-- 1. DROP AND RECREATE MV
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS sales_facts_mv CASCADE;

CREATE MATERIALIZED VIEW sales_facts_mv AS
SELECT
    -- UNIQUE KEY: enables REFRESH CONCURRENTLY
    oi.id AS order_item_id,

    TO_CHAR(o.order_date, 'YYYYMMDD')::INTEGER as date_id,
    o.order_date,
    o.channel_id,
    o.customer_id,
    o.source,
    oi.product_sku as original_sku,
    COALESCE(pc_direct.sku, pc_master.sku, pc_mapped.sku, pc_mapped_master.sku) as catalog_sku,
    COALESCE(pc_direct.sku_primario, pc_master.sku_primario, pc_mapped.sku_primario, pc_mapped_master.sku_primario) as sku_primario,
    COALESCE(
        pc_direct.product_name,
        pmb.master_box_name,
        pc_mapped.product_name,
        pmb_mapped.master_box_name,
        oi.product_name
    ) as product_name,
    COALESCE(
        pc_direct.category,
        pc_master.category,
        pc_mapped.category,
        pc_mapped_master.category
    ) as category,
    COALESCE(pc_direct.package_type, pc_master.package_type, pc_mapped.package_type, pc_mapped_master.package_type) as package_type,
    COALESCE(pc_direct.brand, pc_master.brand, pc_mapped.brand, pc_mapped_master.brand) as brand,
    COALESCE(pc_direct.language, pc_master.language, pc_mapped.language, pc_mapped_master.language) as language,
    COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, pc_mapped_master.units_per_display, 1) as units_per_display,
    COALESCE(pmb.items_per_master_box, pmb_mapped.items_per_master_box, pc_direct.items_per_master_box, pc_mapped.items_per_master_box) as items_per_master_box,
    CASE
        WHEN pmb.sku_master IS NOT NULL THEN TRUE
        WHEN pmb_mapped.sku_master IS NOT NULL THEN TRUE
        ELSE FALSE
    END as is_caja_master,
    CASE
        WHEN pc_direct.sku IS NOT NULL THEN 'direct'
        WHEN pmb.sku_master IS NOT NULL THEN 'caja_master'
        WHEN pc_mapped.sku IS NOT NULL THEN 'sku_mapping'
        WHEN pmb_mapped.sku_master IS NOT NULL THEN 'sku_mapping_caja_master'
        ELSE 'unmapped'
    END as match_type,
    sm_single.rule_name as mapping_rule,
    COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1) as quantity_multiplier,
    ch.name as channel_name,
    c.name as customer_name,
    c.rut as customer_rut,
    oi.quantity as original_units_sold,
    (oi.quantity * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1)) as units_sold,
    CAST(oi.subtotal AS DECIMAL(15,2)) as revenue,
    oi.unit_price,
    oi.total,
    oi.tax_amount,
    o.id as order_id,
    o.external_id as order_external_id,
    o.invoice_status,
    o.payment_status,
    o.status as order_status,
    o.created_at as order_created_at

FROM orders o
JOIN order_items oi ON o.id = oi.order_id

-- Path 1: Direct SKU match (no is_active filter — inactive products appear in sales history)
LEFT JOIN product_catalog pc_direct
    ON pc_direct.sku = UPPER(oi.product_sku)

-- Path 2: Caja master match via junction table
LEFT JOIN product_master_boxes pmb
    ON pmb.sku_master = UPPER(oi.product_sku)
    AND pmb.is_active = TRUE
    AND pc_direct.sku IS NULL
LEFT JOIN product_catalog pc_master
    ON pc_master.sku = pmb.product_sku
    AND pc_direct.sku IS NULL

-- Path 3: SKU mapping lookup (only when paths 1 & 2 fail)
LEFT JOIN LATERAL (
    SELECT sm.target_sku, sm.quantity_multiplier, sm.rule_name
    FROM sku_mappings sm
    WHERE sm.source_pattern = UPPER(oi.product_sku)
      AND sm.pattern_type = 'exact'
      AND sm.is_active = TRUE
      AND pc_direct.sku IS NULL
      AND pmb.sku_master IS NULL
    ORDER BY sm.id
    LIMIT 1
) sm_single ON TRUE

LEFT JOIN LATERAL (
    SELECT SUM(COALESCE(sm2.quantity_multiplier, 1)) as total_multiplier
    FROM sku_mappings sm2
    WHERE sm2.source_pattern = UPPER(oi.product_sku)
      AND sm2.pattern_type = 'exact'
      AND sm2.is_active = TRUE
      AND pc_direct.sku IS NULL
      AND pmb.sku_master IS NULL
    HAVING COUNT(*) > 1
) sm_agg ON TRUE

-- Path 3a: SKU mapping target → direct product match (no is_active filter)
LEFT JOIN product_catalog pc_mapped
    ON pc_mapped.sku = sm_single.target_sku

-- Path 4: SKU mapping target → caja master match via junction table
LEFT JOIN product_master_boxes pmb_mapped
    ON pmb_mapped.sku_master = sm_single.target_sku
    AND pmb_mapped.is_active = TRUE
    AND pc_mapped.sku IS NULL
LEFT JOIN product_catalog pc_mapped_master
    ON pc_mapped_master.sku = pmb_mapped.product_sku
    AND pc_mapped.sku IS NULL

LEFT JOIN channels ch ON o.channel_id = ch.id
LEFT JOIN customers c ON o.customer_id = c.id

WHERE
    o.invoice_status IN ('accepted', 'accepted_objection', 'sent_sii')
    AND o.status != 'cancelled';

-- ============================================
-- 2. UNIQUE INDEX (enables REFRESH CONCURRENTLY)
-- ============================================

CREATE UNIQUE INDEX idx_sales_facts_mv_unique_order_item
    ON sales_facts_mv(order_item_id);

-- ============================================
-- 3. PERFORMANCE INDEXES
-- ============================================

CREATE INDEX idx_sales_mv_date_id ON sales_facts_mv(date_id);
CREATE INDEX idx_sales_mv_order_date ON sales_facts_mv(order_date);
CREATE INDEX idx_sales_mv_source ON sales_facts_mv(source);
CREATE INDEX idx_sales_mv_category ON sales_facts_mv(category);
CREATE INDEX idx_sales_mv_channel_id ON sales_facts_mv(channel_id);
CREATE INDEX idx_sales_mv_customer_id ON sales_facts_mv(customer_id);
CREATE INDEX idx_sales_mv_sku_primario ON sales_facts_mv(sku_primario);
CREATE INDEX idx_sales_mv_is_caja_master ON sales_facts_mv(is_caja_master);
CREATE INDEX idx_sales_mv_match_type ON sales_facts_mv(match_type);
CREATE INDEX idx_sales_mv_package_type ON sales_facts_mv(package_type);

CREATE INDEX idx_sales_mv_date_source_category
    ON sales_facts_mv(date_id, source, category)
    INCLUDE (revenue, units_sold);

CREATE INDEX idx_sales_mv_date_source_channel
    ON sales_facts_mv(date_id, source, channel_id)
    INCLUDE (revenue, units_sold);

CREATE INDEX idx_sales_mv_date_source ON sales_facts_mv(date_id, source);
CREATE INDEX idx_sales_mv_revenue_desc ON sales_facts_mv(revenue DESC);
CREATE INDEX idx_sales_mv_date_brin ON sales_facts_mv USING BRIN(order_date);

-- ============================================
-- 4. ANALYZE
-- ============================================

ANALYZE sales_facts_mv;

-- ============================================
-- 5. VERIFICATION
-- ============================================

DO $$
DECLARE
    v_caja_master_count INTEGER;
    v_total_rows INTEGER;
    v_has_unique BOOLEAN;
    v_total_revenue NUMERIC;
BEGIN
    SELECT COUNT(*) INTO v_total_rows FROM sales_facts_mv;
    SELECT COUNT(*) INTO v_caja_master_count FROM sales_facts_mv WHERE category = 'CAJA MASTER';
    SELECT SUM(revenue) INTO v_total_revenue FROM sales_facts_mv;
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'sales_facts_mv'
        AND indexdef LIKE '%UNIQUE%'
    ) INTO v_has_unique;

    RAISE NOTICE '';
    RAISE NOTICE '=== Migration 043 Verification ===';
    RAISE NOTICE 'Total rows: %', v_total_rows;
    RAISE NOTICE 'Total revenue: %', v_total_revenue;
    RAISE NOTICE 'Rows with category=CAJA MASTER: % (should be 0)', v_caja_master_count;
    RAISE NOTICE 'Has unique index (CONCURRENTLY support): %', v_has_unique;
    RAISE NOTICE '';

    IF v_caja_master_count > 0 THEN
        RAISE WARNING 'Category regression — % rows still have CAJA MASTER', v_caja_master_count;
    END IF;
END $$;
