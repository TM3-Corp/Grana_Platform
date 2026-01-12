-- Migration 024: Fix MV duplicate rows from multi-target SKU mappings
-- Purpose: Prevent duplicate rows when PACK products have multiple sku_mappings targets
-- Author: Claude Code
-- Date: 2025-12-31
--
-- PROBLEM:
-- - PACK products like PACKNAVIDAD2 have 8 mappings (one per product in bundle)
-- - LEFT JOIN sku_mappings creates 8 rows per order_item → revenue counted 8x!
-- - Result: $462.9M in MV vs $455.7M actual (7.2M inflation)
--
-- EXAMPLE:
-- PACKNAVIDAD2 has 8 target_sku mappings (for bundle contents)
-- Order with qty=1, $40,112 creates 8 MV rows → $320,896 counted!
--
-- SOLUTION:
-- Use LATERAL subquery with LIMIT 1 to pick only one mapping per source SKU
-- For PACK products, we aggregate the quantity_multiplier to sum all bundle contents

-- ============================================
-- 1. DROP EXISTING MATERIALIZED VIEW
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS sales_facts_mv CASCADE;

-- ============================================
-- 2. RECREATE WITH FIXED SKU_MAPPINGS JOIN
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
    -- Priority: 1. Direct sku match, 2. sku_master match, 3. sku_mappings
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

    -- Conversion factors (for UDS calculation)
    COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, pc_mapped_master.units_per_display, 1) as units_per_display,
    COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, pc_direct.items_per_master_box, pc_mapped.items_per_master_box) as items_per_master_box,
    CASE
        WHEN pc_master.sku IS NOT NULL THEN TRUE
        WHEN pc_mapped_master.sku IS NOT NULL THEN TRUE
        ELSE FALSE
    END as is_caja_master,

    -- Mapping info (for debugging/audit)
    CASE
        WHEN pc_direct.sku IS NOT NULL THEN 'direct'
        WHEN pc_master.sku IS NOT NULL THEN 'caja_master'
        WHEN pc_mapped.sku IS NOT NULL THEN 'sku_mapping'
        WHEN pc_mapped_master.sku IS NOT NULL THEN 'sku_mapping_caja_master'
        ELSE 'unmapped'
    END as match_type,
    sm_single.rule_name as mapping_rule,

    -- Quantity multiplier: For PACK products, sum all multipliers from mappings
    -- PACKNAVIDAD2 has 8 items → total multiplier = sum of all (2+1+1+1+1+1+1+1 = 9)
    COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1) as quantity_multiplier,

    -- Channel & Customer names (denormalized for fast filtering)
    ch.name as channel_name,
    c.name as customer_name,
    c.rut as customer_rut,

    -- Measures - ORIGINAL (raw from order_items)
    oi.quantity as original_units_sold,

    -- Measures - ADJUSTED (with quantity multiplier applied)
    -- For PACK products, uses sum of all bundle multipliers
    (oi.quantity * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1)) as units_sold,

    -- Revenue stays the same (customer paid for the PACK, not individual units)
    oi.subtotal as revenue,
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

-- Path 1: Direct match on product_catalog.sku
LEFT JOIN product_catalog pc_direct
    ON pc_direct.sku = UPPER(oi.product_sku)
    AND pc_direct.is_active = TRUE

-- Path 2: Match on product_catalog.sku_master (CAJA MASTER)
LEFT JOIN product_catalog pc_master
    ON pc_master.sku_master = UPPER(oi.product_sku)
    AND pc_master.is_active = TRUE
    AND pc_direct.sku IS NULL

-- Path 3: Via sku_mappings - FIXED: Use LATERAL with LIMIT 1 to avoid duplicates
-- Pick one mapping per source_pattern (for catalog lookup)
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

-- ALSO: Get aggregated multiplier for PACK products (sum all bundle components)
LEFT JOIN LATERAL (
    SELECT SUM(COALESCE(sm2.quantity_multiplier, 1)) as total_multiplier
    FROM sku_mappings sm2
    WHERE sm2.source_pattern = UPPER(oi.product_sku)
      AND sm2.pattern_type = 'exact'
      AND sm2.is_active = TRUE
      AND pc_direct.sku IS NULL
      AND pc_master.sku IS NULL
    HAVING COUNT(*) > 1  -- Only for multi-mapping PACKs
) sm_agg ON TRUE

-- Path 3a: target_sku matches product_catalog.sku (normal products)
LEFT JOIN product_catalog pc_mapped
    ON pc_mapped.sku = sm_single.target_sku
    AND pc_mapped.is_active = TRUE

-- Path 3b: target_sku matches product_catalog.sku_master (caja master via sku_mappings)
LEFT JOIN product_catalog pc_mapped_master
    ON pc_mapped_master.sku_master = sm_single.target_sku
    AND pc_mapped_master.is_active = TRUE
    AND pc_mapped.sku IS NULL

-- Channel and Customer info
LEFT JOIN channels ch ON o.channel_id = ch.id
LEFT JOIN customers c ON o.customer_id = c.id

WHERE
    -- Only accepted invoices (no NULL) - matches Dashboard Ejecutivo
    o.invoice_status IN ('accepted', 'accepted_objection')
    -- Exclude cancelled orders
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
-- 4. ANALYZE FOR QUERY OPTIMIZER
-- ============================================

ANALYZE sales_facts_mv;

-- ============================================
-- 5. UPDATE COMMENTS
-- ============================================

COMMENT ON MATERIALIZED VIEW sales_facts_mv IS
'Pre-aggregated sales facts for OLAP analytics.
FIXED (Migration 024): No more duplicate rows from multi-target sku_mappings.
- Uses LATERAL LIMIT 1 to pick one mapping per SKU for catalog lookup
- Uses SUM aggregation for quantity_multiplier (PACK bundle totals)

Example: PACKNAVIDAD2 (9 items):
- Before: 8 rows per order_item (revenue counted 8x)
- After: 1 row, quantity_multiplier = 9 (sum of all bundle contents)

Refresh: REFRESH MATERIALIZED VIEW sales_facts_mv;';

-- ============================================
-- 6. VERIFICATION
-- ============================================

-- Should show no duplicates
SELECT
    'Duplicate check' as test,
    COUNT(*) as total_rows,
    COUNT(DISTINCT (order_id, original_sku)) as unique_combinations,
    CASE
        WHEN COUNT(*) = COUNT(DISTINCT (order_id, original_sku)) THEN 'PASS - No duplicates'
        ELSE 'FAIL - Duplicates found!'
    END as result
FROM sales_facts_mv
WHERE EXTRACT(YEAR FROM order_date) = 2025;

-- Revenue totals
SELECT
    'Revenue totals' as test,
    SUM(revenue) as mv_revenue,
    (SELECT SUM(oi.subtotal)
     FROM orders o
     JOIN order_items oi ON o.id = oi.order_id
     WHERE o.order_date >= '2025-01-01'
       AND o.invoice_status IN ('accepted', 'accepted_objection')
       AND o.status != 'cancelled') as order_items_revenue
FROM sales_facts_mv
WHERE EXTRACT(YEAR FROM order_date) = 2025;
