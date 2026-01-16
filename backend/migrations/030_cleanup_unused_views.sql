-- Migration 030: Cleanup Unused Views
-- Date: 2026-01-13
-- Purpose: Remove unused PostgreSQL views to simplify database schema
-- Reference: /docs/DATABASE_TABLE_USAGE_MAP.md
--
-- Views being removed (all confirmed unused via multi-agent analysis):
--
--   1. inventory_general
--      - Created in migrations 014/016
--      - NEVER queried - warehouses.py builds custom CTEs instead
--      - Function `get_inventory_general()` exists but uses inline SQL
--
--   2. v_low_stock_products
--      - Created in Supabase remote schema
--      - NEVER queried - products.py uses ProductRepository.find_low_stock()
--      - Chat tool builds custom SQL with warehouse_stock joins
--
--   3. v_orders_full
--      - Created in Supabase remote schema
--      - NEVER queried - OrderRepository uses direct table queries
--      - Designed to join orders+customers+channels (done inline now)
--
--   4. v_sales_by_channel
--      - Created in Supabase remote schema
--      - NEVER queried - chat tool builds custom SQL with order_items
--      - View doesn't have order_items joins that functions need
--
-- Linear Issues: CORP-145 through CORP-148

-- ============================================================================
-- STEP 1: Drop unused views
-- ============================================================================

-- inventory_general: Created in 014, updated in 016, never used
DROP VIEW IF EXISTS inventory_general CASCADE;

-- v_low_stock_products: Filters products by stock < min_stock (never queried)
DROP VIEW IF EXISTS v_low_stock_products CASCADE;

-- v_orders_full: Joins orders with customers and channels (never queried)
DROP VIEW IF EXISTS v_orders_full CASCADE;

-- v_sales_by_channel: Aggregates sales by channel (never queried)
DROP VIEW IF EXISTS v_sales_by_channel CASCADE;

-- ============================================================================
-- STEP 2: Verification
-- ============================================================================

DO $$
DECLARE
    deleted_views TEXT[] := ARRAY[
        'inventory_general',
        'v_low_stock_products',
        'v_orders_full',
        'v_sales_by_channel'
    ];
    v TEXT;
    still_exists BOOLEAN;
    remaining_views INTEGER;
    remaining_mvs INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'MIGRATION 030: Cleanup Unused Views';
    RAISE NOTICE '============================================';

    -- Check each view
    RAISE NOTICE '';
    RAISE NOTICE 'Checking deleted views:';
    FOREACH v IN ARRAY deleted_views
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.views
            WHERE table_schema = 'public'
            AND table_name = v
        ) INTO still_exists;

        IF still_exists THEN
            RAISE WARNING '  FAILED: View "%" still exists!', v;
        ELSE
            RAISE NOTICE '  OK: View "%" dropped', v;
        END IF;
    END LOOP;

    -- Count remaining views
    SELECT COUNT(*) INTO remaining_views
    FROM information_schema.views
    WHERE table_schema = 'public';

    -- Count remaining materialized views
    SELECT COUNT(*) INTO remaining_mvs
    FROM pg_matviews
    WHERE schemaname = 'public';

    -- Summary
    RAISE NOTICE '';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Summary:';
    RAISE NOTICE '  - Views deleted: 4';
    RAISE NOTICE '  - Remaining views: %', remaining_views;
    RAISE NOTICE '  - Remaining materialized views: %', remaining_mvs;
    RAISE NOTICE '============================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Remaining USED views:';
    RAISE NOTICE '  - inventory_planning_facts (Production Planning)';
    RAISE NOTICE '  - warehouse_stock_by_lot (Warehouse by Lot)';
    RAISE NOTICE '  - v_product_conversion (Conversion Service)';
    RAISE NOTICE '';
    RAISE NOTICE 'Remaining materialized views:';
    RAISE NOTICE '  - sales_facts_mv (Dashboard, Sales Analytics)';
    RAISE NOTICE '============================================';
END $$;
