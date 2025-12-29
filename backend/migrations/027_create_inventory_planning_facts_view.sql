-- Migration 027: Create inventory_planning_facts view
-- Purpose: Expiration-aware stock aggregation for production planning

-- Drop view if exists (to allow recreation)
DROP VIEW IF EXISTS inventory_planning_facts;

-- Create view with expiration-aware stock classification
CREATE OR REPLACE VIEW inventory_planning_facts AS
WITH stock_by_expiration AS (
    SELECT
        ws.product_id,
        p.sku,
        w.code as warehouse_code,
        ws.quantity,
        ws.lot_number,
        ws.expiration_date,
        -- Days until expiration (NULL if no date)
        CASE
            WHEN ws.expiration_date IS NOT NULL
            THEN ws.expiration_date - CURRENT_DATE
            ELSE NULL
        END as days_to_expiration,
        -- Expiration category
        CASE
            WHEN ws.expiration_date IS NULL THEN 'no_date'
            WHEN ws.expiration_date < CURRENT_DATE THEN 'expired'
            WHEN ws.expiration_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'expiring_soon'
            WHEN ws.expiration_date <= CURRENT_DATE + INTERVAL '60 days' THEN 'expiring_60d'
            ELSE 'valid'
        END as expiration_category
    FROM warehouse_stock ws
    JOIN products p ON p.id = ws.product_id AND p.is_active = true
    JOIN warehouses w ON w.id = ws.warehouse_id AND w.is_active = true
    WHERE ws.lot_number IS NOT NULL  -- Exclude legacy rows without lot tracking
)
SELECT
    sku,

    -- Total stock (all states)
    COALESCE(SUM(quantity), 0) as stock_total,

    -- Stock by expiration state
    COALESCE(SUM(CASE WHEN expiration_category = 'expired' THEN quantity ELSE 0 END), 0) as stock_expired,
    COALESCE(SUM(CASE WHEN expiration_category = 'expiring_soon' THEN quantity ELSE 0 END), 0) as stock_expiring_30d,
    COALESCE(SUM(CASE WHEN expiration_category = 'expiring_60d' THEN quantity ELSE 0 END), 0) as stock_expiring_60d,
    COALESCE(SUM(CASE WHEN expiration_category = 'valid' THEN quantity ELSE 0 END), 0) as stock_valid,
    COALESCE(SUM(CASE WHEN expiration_category = 'no_date' THEN quantity ELSE 0 END), 0) as stock_no_date,

    -- Usable stock (valid + no_date + expiring_60d; excludes expired and expiring_soon)
    -- Reason: stock expiring in 30 days may not be sellable in time
    COALESCE(SUM(CASE WHEN expiration_category IN ('valid', 'no_date', 'expiring_60d') THEN quantity ELSE 0 END), 0) as stock_usable,

    -- Stock at risk (expiring soon - may need promotion)
    COALESCE(SUM(CASE WHEN expiration_category = 'expiring_soon' THEN quantity ELSE 0 END), 0) as stock_at_risk,

    -- Earliest expiration date (for lots with dates, excluding already expired)
    MIN(CASE WHEN expiration_date IS NOT NULL AND expiration_date > CURRENT_DATE
        THEN expiration_date END) as earliest_expiration,

    -- Days to earliest expiration
    MIN(CASE WHEN expiration_date IS NOT NULL AND expiration_date > CURRENT_DATE
        THEN expiration_date - CURRENT_DATE END) as days_to_earliest_expiration,

    -- Lot counts by state
    COUNT(DISTINCT CASE WHEN expiration_category = 'expired' THEN lot_number END) as lots_expired,
    COUNT(DISTINCT CASE WHEN expiration_category = 'expiring_soon' THEN lot_number END) as lots_expiring_soon,
    COUNT(DISTINCT CASE WHEN expiration_category = 'valid' THEN lot_number END) as lots_valid,
    COUNT(DISTINCT lot_number) as lots_total

FROM stock_by_expiration
GROUP BY sku;

-- Index on the view is not directly possible, but the underlying table indexes help
COMMENT ON VIEW inventory_planning_facts IS
'Aggregated inventory by SKU with expiration-aware stock classification for production planning.
stock_usable = valid + no_date + expiring_60d (excludes expired and expiring_soon).
stock_at_risk = expiring_soon (within 30 days, may need promotion).';
