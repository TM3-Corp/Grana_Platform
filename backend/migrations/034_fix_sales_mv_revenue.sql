-- Migration 034: Fix Sales MV Revenue Calculation (Net vs Gross)
-- Purpose: Correctly calculate Net Revenue for Boletas (which store Gross prices in order_items)
-- Author: Gemini CLI
-- Date: 2026-02-05
--
-- PROBLEM:
-- - order_items table stores 'subtotal' = quantity * price.
-- - For Facturas, 'price' is Net.
-- - For Boletas, 'price' is Gross.
-- - Previous sales_facts_mv used 'oi.subtotal' directly as revenue.
-- - Result: Boleta revenue was inflated by 19% (IVA), causing discrepancy with client report.
--
-- SOLUTION:
-- - In sales_facts_mv, apply logic:
--   - IF invoice_type = 'boleta': revenue = oi.subtotal / 1.19
--   - ELSE: revenue = oi.subtotal

-- ============================================
-- 1. DROP EXISTING MATERIALIZED VIEW
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS sales_facts_mv CASCADE;

-- ============================================
-- 2. RECREATE WITH CORRECT REVENUE LOGIC
-- ============================================

CREATE MATERIALIZED VIEW sales_facts_mv AS
SELECT
    -- Date dimension (for OLAP queries)
    TO_CHAR(o.order_date, 'YYYYMMDD')::INTEGER as date_id,
    o.order_date,

    -- Dimension keys
    o.channel_id,
    o.customer_id,
    o.source,

    -- Product info from product_catalog
    oi.product_sku as original_sku,
    COALESCE(pc_direct.sku, pc_master.sku, pc_mapped.sku, pc_mapped_master.sku) as catalog_sku,
    COALESCE(pc_direct.sku_primario, pc_master.sku_primario, pc_mapped.sku_primario, pc_mapped_master.sku_primario) as sku_primario,
    COALESCE(
        pc_direct.product_name,
        pc_master.master_box_name,
        pc_mapped.product_name,
        pc_mapped_master.master_box_name,
        oi.product_name
    ) as product_name,
    COALESCE(
        pc_direct.category,
        CASE WHEN pc_master.sku IS NOT NULL THEN 'CAJA MASTER' END,
        pc_mapped.category,
        CASE WHEN pc_mapped_master.sku IS NOT NULL THEN 'CAJA MASTER' END
    ) as category,
    COALESCE(pc_direct.package_type, pc_master.package_type, pc_mapped.package_type, pc_mapped_master.package_type) as package_type,
    COALESCE(pc_direct.brand, pc_master.brand, pc_mapped.brand, pc_mapped_master.brand) as brand,
    COALESCE(pc_direct.language, pc_master.language, pc_mapped.language, pc_mapped_master.language) as language,

    -- Conversion factors
    COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, pc_mapped_master.units_per_display, 1) as units_per_display,
    COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, pc_direct.items_per_master_box, pc_mapped.items_per_master_box) as items_per_master_box,
    CASE
        WHEN pc_master.sku IS NOT NULL THEN TRUE
        WHEN pc_mapped_master.sku IS NOT NULL THEN TRUE
        ELSE FALSE
    END as is_caja_master,

    -- Mapping info
    CASE
        WHEN pc_direct.sku IS NOT NULL THEN 'direct'
        WHEN pc_master.sku IS NOT NULL THEN 'caja_master'
        WHEN pc_mapped.sku IS NOT NULL THEN 'sku_mapping'
        WHEN pc_mapped_master.sku IS NOT NULL THEN 'sku_mapping_caja_master'
        ELSE 'unmapped'
    END as match_type,
    sm_single.rule_name as mapping_rule,
    COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1) as quantity_multiplier,

    -- Channel & Customer names
    ch.name as channel_name,
    c.name as customer_name,
    c.rut as customer_rut,

    -- Measures
    oi.quantity as original_units_sold,
    (oi.quantity * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1)) as units_sold,

    -- REVENUE CORRECTION (Fixes Migration 034)
    CAST(
        CASE
            WHEN LOWER(o.invoice_type) = 'boleta' THEN oi.subtotal / 1.19
            ELSE oi.subtotal
        END
    AS DECIMAL(15,2)) as revenue,

    oi.unit_price,
    oi.total,
    oi.tax_amount,

    -- Order info
    o.id as order_id,
    o.external_id as order_external_id,
    o.invoice_status,
    o.payment_status,
    o.status as order_status,
    o.created_at as order_created_at

FROM orders o
JOIN order_items oi ON o.id = oi.order_id

-- Joins for Product Catalog & Mappings (Unchanged)
LEFT JOIN product_catalog pc_direct
    ON pc_direct.sku = UPPER(oi.product_sku)
    AND pc_direct.is_active = TRUE

LEFT JOIN product_catalog pc_master
    ON pc_master.sku_master = UPPER(oi.product_sku)
    AND pc_master.is_active = TRUE
    AND pc_direct.sku IS NULL

LEFT JOIN LATERAL (
    SELECT sm.target_sku, sm.quantity_multiplier, sm.rule_name
    FROM sku_mappings sm
    WHERE sm.source_pattern = UPPER(oi.product_sku)
      AND sm.pattern_type = 'exact'
      AND sm.is_active = TRUE
      AND pc_direct.sku IS NULL
      AND pc_master.sku IS NULL
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
      AND pc_master.sku IS NULL
    HAVING COUNT(*) > 1
) sm_agg ON TRUE

LEFT JOIN product_catalog pc_mapped
    ON pc_mapped.sku = sm_single.target_sku
    AND pc_mapped.is_active = TRUE

LEFT JOIN product_catalog pc_mapped_master
    ON pc_mapped_master.sku_master = sm_single.target_sku
    AND pc_mapped_master.is_active = TRUE
    AND pc_mapped.sku IS NULL

LEFT JOIN channels ch ON o.channel_id = ch.id
LEFT JOIN customers c ON o.customer_id = c.id

WHERE
    o.invoice_status IN ('accepted', 'accepted_objection')
    AND o.status != 'cancelled';

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
-- 5. COMMENTS
-- ============================================

COMMENT ON MATERIALIZED VIEW sales_facts_mv IS
'Pre-aggregated sales facts for OLAP analytics.
FIXED (Migration 034): Revenue calculation now accounts for Gross/Net difference in order_items.
- Boletas: revenue = subtotal / 1.19 (converting Gross to Net)
- Facturas: revenue = subtotal (already Net)
- Also includes previous fix (Migration 024) for PACK duplication.
Refresh: REFRESH MATERIALIZED VIEW sales_facts_mv;';
