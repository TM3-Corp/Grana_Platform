-- Migration 017: Fix sales_facts_mv revenue column and invoice_status filter
-- Purpose: Use oi.subtotal instead of oi.total to match Dashboard Ejecutivo
-- Author: Claude Code
-- Date: 2025-11-19
--
-- PROBLEM:
-- - Dashboard Ejecutivo shows $548.5M for 2025 (correct - uses oi.subtotal)
-- - Sales Analytics (OLAP) shows $652.7M for 2025 (incorrect - uses oi.total)
-- - Difference: $104.2M from using oi.total instead of oi.subtotal
--
-- ROOT CAUSE:
-- - Migration 013 line 54 used: oi.total as revenue
-- - Dashboard Ejecutivo uses: SUM(oi.subtotal) as total_revenue
-- - oi.total includes tax, oi.subtotal does not
--
-- FIX:
-- - Change revenue column from oi.total to oi.subtotal
-- - Match exactly what Dashboard Ejecutivo uses for revenue calculation

-- ============================================
-- 1. DROP EXISTING MATERIALIZED VIEW
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS sales_facts_mv CASCADE;

-- ============================================
-- 2. RECREATE WITH CORRECTED FILTER
-- ============================================

CREATE MATERIALIZED VIEW sales_facts_mv AS
SELECT
    -- Date dimension (join to dim_date)
    TO_CHAR(o.order_date, 'YYYYMMDD')::INTEGER as date_id,
    o.order_date,

    -- Dimension keys
    oi.product_id,
    o.channel_id,
    o.customer_id,
    o.source,

    -- Denormalized dimension attributes (for filtering without JOINs)
    p.category,
    p.format,
    p.brand,
    p.name as product_name,
    p.sku as product_sku,
    ch.name as channel_name,
    c.name as customer_name,
    c.rut as customer_rut,

    -- Pre-aggregated measures (SUM/COUNT per order_item)
    oi.quantity as units_sold,
    oi.subtotal as revenue,  -- FIXED: Use subtotal (excludes tax) to match Dashboard Ejecutivo
    oi.unit_price,
    oi.total,
    oi.tax_amount,

    -- Order-level attributes
    o.id as order_id,
    o.external_id as order_external_id,
    o.invoice_status,
    o.payment_status,
    o.status as order_status,

    -- Timestamps
    o.created_at as order_created_at

FROM orders o
JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN products p ON oi.product_id = p.id
LEFT JOIN channels ch ON o.channel_id = ch.id
LEFT JOIN customers c ON o.customer_id = c.id

WHERE
    -- CRITICAL FIX: Only accepted invoices (no NULL)
    -- NULL invoice_status means the invoice was not accepted/finalized
    o.invoice_status IN ('accepted', 'accepted_objection')

    -- Exclude test/cancelled orders
    AND o.status != 'cancelled';

-- ============================================
-- 3. RECREATE PERFORMANCE INDEXES
-- ============================================

-- Most critical: date-based queries (timeline charts)
CREATE INDEX idx_sales_mv_date_id ON sales_facts_mv(date_id);
CREATE INDEX idx_sales_mv_order_date ON sales_facts_mv(order_date);

-- Source filtering (always used)
CREATE INDEX idx_sales_mv_source ON sales_facts_mv(source);

-- Dimension filtering
CREATE INDEX idx_sales_mv_category ON sales_facts_mv(category);
CREATE INDEX idx_sales_mv_channel_id ON sales_facts_mv(channel_id);
CREATE INDEX idx_sales_mv_customer_id ON sales_facts_mv(customer_id);
CREATE INDEX idx_sales_mv_product_id ON sales_facts_mv(product_id);
CREATE INDEX idx_sales_mv_format ON sales_facts_mv(format);

-- Composite indexes for common query patterns
-- Pattern 1: Date + Source + Category (most common)
CREATE INDEX idx_sales_mv_date_source_category
    ON sales_facts_mv(date_id, source, category)
    INCLUDE (revenue, units_sold);

-- Pattern 2: Date + Source + Channel
CREATE INDEX idx_sales_mv_date_source_channel
    ON sales_facts_mv(date_id, source, channel_id)
    INCLUDE (revenue, units_sold);

-- Pattern 3: Date + Source filtering
CREATE INDEX idx_sales_mv_date_source
    ON sales_facts_mv(date_id, source);

-- Revenue sorting (for top N queries)
CREATE INDEX idx_sales_mv_revenue_desc ON sales_facts_mv(revenue DESC);

-- BRIN index for time-series optimization (very efficient for date ranges)
CREATE INDEX idx_sales_mv_date_brin ON sales_facts_mv USING BRIN(order_date);

-- ============================================
-- 4. ANALYZE FOR QUERY OPTIMIZER
-- ============================================

ANALYZE sales_facts_mv;

-- ============================================
-- 5. UPDATE COMMENTS
-- ============================================

COMMENT ON MATERIALIZED VIEW sales_facts_mv IS
'Pre-aggregated sales facts for OLAP analytics. Provides 10-30x faster queries compared to raw OLTP tables.
FIXED (Migration 017): Now excludes NULL invoice_status - only accepted invoices represent real sales.
Refresh hourly or after data sync.';

-- ============================================
-- 6. VERIFICATION QUERY
-- ============================================

-- Check that revenue now matches Dashboard Ejecutivo
SELECT
    EXTRACT(YEAR FROM order_date) as year,
    COUNT(DISTINCT order_id) as orders,
    ROUND(SUM(revenue), 2) as total_revenue
FROM sales_facts_mv
WHERE source = 'relbase'
GROUP BY EXTRACT(YEAR FROM order_date)
ORDER BY year DESC;

-- Should show approximately $548.5M for 2025 (matching Dashboard Ejecutivo)
