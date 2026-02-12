-- Migration 039: Reconcile Platform Revenue with RelBase
-- Date: 2026-02-12
--
-- Fixes 3 discrepancies totaling +$1,255,349 gap vs RelBase report:
--
-- 1. Factura 43403859 (folio 3526, $2,590,556): DB has 'accepted' but
--    RelBase shows 'cancel'. Update status to match.
--
-- 2. Boleta 44212199 (folio 16827, net $8,992): Never synced to DB
--    due to transient API failure. Insert manually.
--    NOTE: This boleta is inserted WITHOUT order_items because we want
--    the sync service to handle item creation with proper pricing logic.
--    The next sync run will skip this order (already exists) but the
--    order-level subtotal is correct for MV revenue.
--
-- 3. MV WHERE clause: Add 'sent_sii' to include emitted-but-pending
--    boletas (1 doc, $33,703). This matches RelBase's report which
--    counts all emitted DTEs.
--
-- 4. DTE 43 (Liquidacion Factura, 8 docs, $1,292,512): RelBase API
--    returns 404 for type_document=43. These appear to be received
--    documents not queryable via the /dtes endpoint. Documented as
--    a known limitation; the $1.3M gap remains until RelBase adds
--    API support or an alternative endpoint is found.
--
-- Expected result after this migration:
--   Facturas: 44 docs, ~$42,258,337 (was 45 / $44,848,893)
--   Boletas:  164 docs, ~$4,547,947 (was 162 / $4,505,252)
--   Total:    ~$46,806,284 (gap reduced from $1,255,349 to ~$1,292,512)
--   Remaining gap = DTE 43 only ($1,292,512), unfetchable via API

-- ============================================
-- 1. FIX FACTURA STATUS MISMATCH
-- ============================================
-- Factura ext_id=43403859 is cancelled in RelBase but accepted in our DB

UPDATE orders
SET invoice_status = 'cancel',
    updated_at = NOW()
WHERE external_id = '43403859'
  AND source = 'relbase'
  AND invoice_type = 'factura'
  AND invoice_status = 'accepted';

-- ============================================
-- 2. INSERT MISSING BOLETA
-- ============================================
-- Boleta id=44212199, folio=16827, was skipped during sync
-- Customer: 10555405, Channel: 1448
-- Products: GRAL_U26010 (qty=1, gross=4990), KSMC_U15010 (qty=1, gross=6900)
-- Gross total = 11890, IVA = 1709, Net = 8992

-- First resolve the customer and channel IDs
DO $$
DECLARE
    v_customer_id INTEGER;
    v_channel_id INTEGER;
    v_order_id INTEGER;
    v_net NUMERIC := 8992;
    v_gross_total NUMERIC := 11890;  -- sum of gross prices
BEGIN
    -- Resolve customer
    SELECT id INTO v_customer_id
    FROM customers
    WHERE external_id = '10555405' AND source = 'relbase';

    -- Resolve channel
    SELECT id INTO v_channel_id
    FROM channels
    WHERE external_id = '1448' AND source = 'relbase';

    -- Insert the order (only if not already present)
    INSERT INTO orders
        (external_id, order_number, source, channel_id, customer_id,
         subtotal, tax_amount, total, status, payment_status,
         invoice_status, order_date, invoice_number, invoice_type, invoice_date,
         customer_notes, created_at)
    VALUES
        ('44212199', '16827', 'relbase', v_channel_id, v_customer_id,
         8992, 1709, 10701, 'completed', 'paid',
         'accepted_objection', '2026-02-11', '16827', 'boleta', '2026-02-11',
         '{"relbase_id": 44212199, "customer_id_relbase": 10555405, "channel_id_relbase": 1448}',
         NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_order_id;

    -- Insert order items with proportional net pricing (Boleta gross->net)
    IF v_order_id IS NOT NULL THEN
        -- Product 1: GRAL_U26010 Granola Low Carb Almendras 260 grs
        -- gross_share = 4990/11890 = 0.4197, item_net = 8992 * 0.4197 = 3774.05
        INSERT INTO order_items
            (order_id, product_id, product_sku, product_name,
             quantity, unit_price, subtotal, total, created_at)
        VALUES
            (v_order_id, NULL, 'GRAL_U26010', 'Granola Low Carb Almendras 260 grs',
             1, ROUND(v_net * (4990.0 / v_gross_total), 2),
             ROUND(v_net * (4990.0 / v_gross_total), 2),
             ROUND(v_net * (4990.0 / v_gross_total), 2),
             NOW());

        -- Product 2: KSMC_U15010 KEEPER MANI 30 GRS X5
        -- gross_share = 6900/11890 = 0.5803, item_net = 8992 * 0.5803 = 5217.95
        INSERT INTO order_items
            (order_id, product_id, product_sku, product_name,
             quantity, unit_price, subtotal, total, created_at)
        VALUES
            (v_order_id, NULL, 'KSMC_U15010', 'KEEPER MANI 30 GRS X5',
             1, ROUND(v_net * (6900.0 / v_gross_total), 2),
             ROUND(v_net * (6900.0 / v_gross_total), 2),
             ROUND(v_net * (6900.0 / v_gross_total), 2),
             NOW());

        RAISE NOTICE 'Inserted missing boleta 44212199 with 2 order items';
    ELSE
        RAISE NOTICE 'Boleta 44212199 already exists, skipped';
    END IF;
END $$;

-- ============================================
-- 3. RECREATE MV WITH sent_sii INCLUDED
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS sales_facts_mv CASCADE;

CREATE MATERIALIZED VIEW sales_facts_mv AS
SELECT
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
    COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, pc_mapped_master.units_per_display, 1) as units_per_display,
    COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, pc_direct.items_per_master_box, pc_mapped.items_per_master_box) as items_per_master_box,
    CASE
        WHEN pc_master.sku IS NOT NULL THEN TRUE
        WHEN pc_mapped_master.sku IS NOT NULL THEN TRUE
        ELSE FALSE
    END as is_caja_master,
    CASE
        WHEN pc_direct.sku IS NOT NULL THEN 'direct'
        WHEN pc_master.sku IS NOT NULL THEN 'caja_master'
        WHEN pc_mapped.sku IS NOT NULL THEN 'sku_mapping'
        WHEN pc_mapped_master.sku IS NOT NULL THEN 'sku_mapping_caja_master'
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
    o.invoice_status IN ('accepted', 'accepted_objection', 'sent_sii')
    AND o.status != 'cancelled';

-- ============================================
-- 4. PERFORMANCE INDEXES
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
-- 5. ANALYZE
-- ============================================

ANALYZE sales_facts_mv;
