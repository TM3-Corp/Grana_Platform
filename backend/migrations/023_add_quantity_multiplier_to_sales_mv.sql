-- Migration 023: Add quantity_multiplier support to sales_facts_mv
-- Purpose: Align sales_facts_mv with Desglose Pedidos SKU mapping logic
-- Author: Claude Code
-- Date: 2025-12-17
--
-- PROBLEM:
-- - sales_facts_mv uses sku_mappings for SKU resolution
-- - BUT it ignores the quantity_multiplier column!
-- - PACK products (PACKGRCA_U26010 = 4x GRCA_U26010) show wrong unit counts
-- - Desglose Pedidos applies multiplier correctly, sales-analytics does not
--
-- EXAMPLE:
-- PACKGRCA_U26010 sold: 10 units
-- - Desglose Pedidos: 10 × 4 = 40 units of GRCA_U26010 ✅
-- - Sales Analytics:  10 units of GRCA_U26010 ❌ (should be 40!)
--
-- SOLUTION:
-- Add quantity_multiplier to SELECT and calculate adjusted_units_sold

-- ============================================
-- 1. DROP EXISTING MATERIALIZED VIEW
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS sales_facts_mv CASCADE;

-- ============================================
-- 2. RECREATE WITH QUANTITY MULTIPLIER SUPPORT
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
    -- Priority: 1. Direct sku match, 2. sku_master match, 3a. sku_mappings→sku, 3b. sku_mappings→sku_master
    oi.product_sku as original_sku,
    COALESCE(pc_direct.sku, pc_master.sku, pc_mapped.sku, pc_mapped_master.sku) as catalog_sku,
    COALESCE(pc_direct.sku_primario, pc_master.sku_primario, pc_mapped.sku_primario, pc_mapped_master.sku_primario) as sku_primario,
    COALESCE(
        pc_direct.product_name,        -- Path 1: Match on product_catalog.sku
        pc_master.master_box_name,     -- Path 2: Match on product_catalog.sku_master (CAJA MASTER)
        pc_mapped.product_name,        -- Path 3a: Match via sku_mappings → product_catalog.sku
        pc_mapped_master.master_box_name, -- Path 3b: Match via sku_mappings → product_catalog.sku_master (CAJA MASTER)
        oi.product_name                -- Fallback for completely unmapped
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
    sm.rule_name as mapping_rule,

    -- NEW: Quantity multiplier from sku_mappings (for PACK products)
    COALESCE(sm.quantity_multiplier, 1) as quantity_multiplier,

    -- Channel & Customer names (denormalized for fast filtering)
    ch.name as channel_name,
    c.name as customer_name,
    c.rut as customer_rut,

    -- Measures - ORIGINAL (raw from order_items)
    oi.quantity as original_units_sold,

    -- Measures - ADJUSTED (with quantity multiplier applied)
    -- PACK products: PACKGRCA_U26010 (qty 10) → GRCA_U26010 (qty 10 × 4 = 40)
    (oi.quantity * COALESCE(sm.quantity_multiplier, 1)) as units_sold,

    -- Revenue stays the same (customer paid for 10 PACKs, not 40 units)
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
-- Only if direct match failed (pc_direct.sku IS NULL)
LEFT JOIN product_catalog pc_master
    ON pc_master.sku_master = UPPER(oi.product_sku)
    AND pc_master.is_active = TRUE
    AND pc_direct.sku IS NULL

-- Path 3: Via sku_mappings table (for external/transformed SKUs like ANU-*, _WEB, ML IDs, PACK*)
-- Only if both direct and sku_master matches failed
LEFT JOIN sku_mappings sm
    ON sm.source_pattern = UPPER(oi.product_sku)
    AND sm.pattern_type = 'exact'
    AND sm.is_active = TRUE
    AND pc_direct.sku IS NULL
    AND pc_master.sku IS NULL

-- Path 3a: target_sku matches product_catalog.sku (normal products)
LEFT JOIN product_catalog pc_mapped
    ON pc_mapped.sku = sm.target_sku
    AND pc_mapped.is_active = TRUE

-- Path 3b: target_sku matches product_catalog.sku_master (caja master via sku_mappings)
-- Example: ANU-BAKC_C02810 → BAKC_C02810 (in sku_mappings) → matches sku_master
LEFT JOIN product_catalog pc_mapped_master
    ON pc_mapped_master.sku_master = sm.target_sku
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

-- Date-based queries (timeline charts)
CREATE INDEX idx_sales_mv_date_id ON sales_facts_mv(date_id);
CREATE INDEX idx_sales_mv_order_date ON sales_facts_mv(order_date);

-- Source filtering (always used)
CREATE INDEX idx_sales_mv_source ON sales_facts_mv(source);

-- Dimension filtering
CREATE INDEX idx_sales_mv_category ON sales_facts_mv(category);
CREATE INDEX idx_sales_mv_channel_id ON sales_facts_mv(channel_id);
CREATE INDEX idx_sales_mv_customer_id ON sales_facts_mv(customer_id);
CREATE INDEX idx_sales_mv_sku_primario ON sales_facts_mv(sku_primario);
CREATE INDEX idx_sales_mv_is_caja_master ON sales_facts_mv(is_caja_master);
CREATE INDEX idx_sales_mv_match_type ON sales_facts_mv(match_type);
CREATE INDEX idx_sales_mv_package_type ON sales_facts_mv(package_type);

-- Composite indexes for common query patterns
CREATE INDEX idx_sales_mv_date_source_category
    ON sales_facts_mv(date_id, source, category)
    INCLUDE (revenue, units_sold);

CREATE INDEX idx_sales_mv_date_source_channel
    ON sales_facts_mv(date_id, source, channel_id)
    INCLUDE (revenue, units_sold);

CREATE INDEX idx_sales_mv_date_source
    ON sales_facts_mv(date_id, source);

-- Revenue sorting (for top N queries)
CREATE INDEX idx_sales_mv_revenue_desc ON sales_facts_mv(revenue DESC);

-- BRIN index for time-series optimization
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
FIXED (Migration 023): Now applies quantity_multiplier from sku_mappings for PACK products.
- units_sold = original_quantity × quantity_multiplier (e.g., 10 PACKs → 40 units)
- original_units_sold = raw quantity from order_items
- revenue stays unchanged (customer paid for PACKs, not individual units)

SKU matching uses 4-path logic:
1. Direct match on product_catalog.sku → product_name
2. Match on product_catalog.sku_master → master_box_name (CAJA MASTER)
3a. Via sku_mappings → product_catalog.sku → mapped product data
3b. Via sku_mappings → product_catalog.sku_master → master_box_name (CAJA MASTER via ANU-/WEB)
4. No match → fallback to order_items (unmapped)

Refresh hourly or after data sync: REFRESH MATERIALIZED VIEW sales_facts_mv;';

-- ============================================
-- 6. VERIFICATION QUERIES
-- ============================================

-- Check PACK products are now mapped with multipliers
SELECT
    original_sku,
    catalog_sku,
    quantity_multiplier,
    original_units_sold,
    units_sold,
    match_type,
    mapping_rule
FROM sales_facts_mv
WHERE original_sku LIKE 'PACK%'
LIMIT 20;

-- Verify category totals (CAJA MASTER should still be ~$167M)
SELECT
    category,
    match_type,
    COUNT(*) as items,
    SUM(original_units_sold) as raw_units,
    SUM(units_sold) as adjusted_units,
    ROUND(SUM(revenue)::numeric, 0) as total_revenue
FROM sales_facts_mv
WHERE source = 'relbase'
  AND EXTRACT(YEAR FROM order_date) = 2025
GROUP BY category, match_type
ORDER BY total_revenue DESC;
