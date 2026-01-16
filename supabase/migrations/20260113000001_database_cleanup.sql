-- =============================================================================
-- CONSOLIDATED DATABASE CLEANUP MIGRATION
-- =============================================================================
-- Date: 2026-01-13
-- Combines: migrations 029, 030, 031 from backend/migrations/
-- Purpose: Remove unused tables, views, and columns to simplify database schema
-- Reference: /docs/DATABASE_TABLE_USAGE_MAP.md
-- Linear Issue: CORP-151
--
-- SUMMARY OF CHANGES:
--
-- TABLES DELETED (7 total):
--   From 029: product_variants, channel_product_equivalents, dim_date, ml_tokens, inventory_movements
--   From 031: api_keys, alerts, manual_corrections
--
-- TABLES PRESERVED (1 total):
--   channel_equivalents - Required by product_mapping_repository.py
--
-- TABLES DELETED (added 2026-01-14):
--   relbase_product_mappings - Orphan audit table with stale Oct 2025 data (relbase.py deleted)
--   customer_channel_rules - Dead code in audit.py (all orders have customer_id directly)
--
-- VIEWS DELETED (6 total):
--   From 029: inventory_consolidated, product_families
--   From 030: inventory_general, v_low_stock_products, v_orders_full, v_sales_by_channel
--
-- COLUMNS REMOVED:
--   From 031: orders.is_corrected, orders.correction_reason,
--             orders.corrected_by, orders.corrected_at
--
-- TRIGGER UPDATED:
--   update_product_stock() - removed INSERT to deleted tables
--
-- =============================================================================

-- ============================================================================
-- PART 1: Drop Views (from 029 and 030)
-- ============================================================================

-- Views depending on product_variants (029)
DROP VIEW IF EXISTS inventory_consolidated CASCADE;
DROP VIEW IF EXISTS product_families CASCADE;

-- Unused views (030)
DROP VIEW IF EXISTS inventory_general CASCADE;
DROP VIEW IF EXISTS v_low_stock_products CASCADE;
DROP VIEW IF EXISTS v_orders_full CASCADE;
DROP VIEW IF EXISTS v_sales_by_channel CASCADE;

-- ============================================================================
-- PART 2: Update Trigger Function (from 031)
-- ============================================================================
-- Remove references to inventory_movements and alerts tables

CREATE OR REPLACE FUNCTION update_product_stock() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- On order_item insert, reduce stock
    IF (TG_OP = 'INSERT') THEN
        UPDATE products
        SET current_stock = current_stock - NEW.quantity
        WHERE id = NEW.product_id;
        -- REMOVED: INSERT INTO inventory_movements (deleted)
        -- REMOVED: INSERT INTO alerts (deleted)
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION update_product_stock() IS 'Trigger to update product stock on order_item insert. Cleaned in migration 20260113.';

-- ============================================================================
-- PART 3: Drop Tables (from 029 and 031)
-- ============================================================================

-- Tables with foreign keys (drop first)
DROP TABLE IF EXISTS inventory_movements CASCADE;
DROP TABLE IF EXISTS product_variants CASCADE;
-- NOTE: channel_equivalents is PRESERVED (required by product_mapping_repository.py)

-- Standalone tables (029)
DROP TABLE IF EXISTS channel_product_equivalents CASCADE;
DROP TABLE IF EXISTS relbase_product_mappings CASCADE;  -- Orphan table with stale Oct 2025 data
DROP TABLE IF EXISTS customer_channel_rules CASCADE;  -- Dead code removed from audit.py
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS ml_tokens CASCADE;

-- Unused tables (031)
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS manual_corrections CASCADE;

-- ============================================================================
-- PART 4: Remove Unused Columns from orders table (from 031)
-- ============================================================================

ALTER TABLE orders DROP COLUMN IF EXISTS is_corrected;
ALTER TABLE orders DROP COLUMN IF EXISTS correction_reason;
ALTER TABLE orders DROP COLUMN IF EXISTS corrected_by;
ALTER TABLE orders DROP COLUMN IF EXISTS corrected_at;

-- ============================================================================
-- PART 5: Verification
-- ============================================================================

DO $$
DECLARE
    deleted_tables TEXT[] := ARRAY[
        'product_variants', 'channel_product_equivalents',
        'dim_date', 'ml_tokens', 'inventory_movements',
        'api_keys', 'alerts', 'manual_corrections',
        'relbase_product_mappings', 'customer_channel_rules'
    ];
    -- PRESERVED TABLES (not in deleted list):
    -- channel_equivalents
    deleted_views TEXT[] := ARRAY[
        'inventory_consolidated', 'product_families',
        'inventory_general', 'v_low_stock_products', 'v_orders_full', 'v_sales_by_channel'
    ];
    deleted_columns TEXT[] := ARRAY[
        'is_corrected', 'correction_reason', 'corrected_by', 'corrected_at'
    ];
    item TEXT;
    still_exists BOOLEAN;
    table_count INTEGER;
    view_count INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'DATABASE CLEANUP MIGRATION - VERIFICATION';
    RAISE NOTICE '============================================================';

    -- Check tables
    RAISE NOTICE '';
    RAISE NOTICE 'Deleted tables (10):';
    FOREACH item IN ARRAY deleted_tables
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = item
        ) INTO still_exists;
        IF still_exists THEN
            RAISE WARNING '  FAILED: Table "%" still exists!', item;
        ELSE
            RAISE NOTICE '  OK: %', item;
        END IF;
    END LOOP;

    -- Check views
    RAISE NOTICE '';
    RAISE NOTICE 'Deleted views (6):';
    FOREACH item IN ARRAY deleted_views
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.views
            WHERE table_schema = 'public' AND table_name = item
        ) INTO still_exists;
        IF still_exists THEN
            RAISE WARNING '  FAILED: View "%" still exists!', item;
        ELSE
            RAISE NOTICE '  OK: %', item;
        END IF;
    END LOOP;

    -- Check columns
    RAISE NOTICE '';
    RAISE NOTICE 'Removed columns from orders (4):';
    FOREACH item IN ARRAY deleted_columns
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'orders' AND column_name = item
        ) INTO still_exists;
        IF still_exists THEN
            RAISE WARNING '  FAILED: Column "orders.%" still exists!', item;
        ELSE
            RAISE NOTICE '  OK: orders.%', item;
        END IF;
    END LOOP;

    -- Final counts
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'public';

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'FINAL STATE:';
    RAISE NOTICE '  - Remaining tables: %', table_count;
    RAISE NOTICE '  - Remaining views: %', view_count;
    RAISE NOTICE '============================================================';
END $$;
