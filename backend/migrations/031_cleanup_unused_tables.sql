-- Migration 031: Cleanup Unused Tables
-- Date: 2026-01-13
-- Purpose: Remove unused tables identified via multi-agent codebase analysis
-- Reference: /docs/DATABASE_TABLE_USAGE_MAP.md
--
-- Tables being removed:
--
--   1. api_keys
--      - Incomplete feature: verify_api_key() exists but never called
--      - Endpoints exist but no actual authentication
--      - No frontend UI
--
--   2. alerts
--      - Trigger writes data, but NEVER queried
--      - No API endpoints, no frontend display
--      - Dead accumulated data
--
--   3. manual_corrections
--      - Zero usage: no API, no service, no frontend
--      - Redundant with orders_audit trigger system
--      - ORM model exists but never used
--
-- Also cleaning up:
--   - Unused columns in orders table (is_corrected, correction_reason, etc.)
--   - update_product_stock trigger (references deleted tables)
--
-- Linear Issues: CORP-149 through CORP-151

-- ============================================================================
-- STEP 1: Update trigger function (remove references to deleted tables)
-- ============================================================================

-- The update_product_stock trigger inserts into:
-- - inventory_movements (deleted in migration 029)
-- - alerts (being deleted now)
-- We need to recreate it without those INSERT statements

CREATE OR REPLACE FUNCTION update_product_stock() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Al crear un order_item, reducir stock
    IF (TG_OP = 'INSERT') THEN
        UPDATE products
        SET current_stock = current_stock - NEW.quantity
        WHERE id = NEW.product_id;

        -- REMOVED: INSERT INTO inventory_movements (table deleted in migration 029)
        -- REMOVED: INSERT INTO alerts (table deleted in migration 031)
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION update_product_stock() IS 'Trigger to update product stock on order_item insert. Cleaned up in migration 031.';

-- ============================================================================
-- STEP 2: Drop unused tables
-- ============================================================================

-- api_keys: Incomplete API key authentication feature
DROP TABLE IF EXISTS api_keys CASCADE;

-- alerts: Trigger-populated but never queried
DROP TABLE IF EXISTS alerts CASCADE;

-- manual_corrections: Redundant with orders_audit, zero usage
DROP TABLE IF EXISTS manual_corrections CASCADE;

-- ============================================================================
-- STEP 3: Remove unused columns from orders table
-- ============================================================================

-- These columns were for manual corrections but are unused
-- orders_audit trigger system is the actual audit mechanism
ALTER TABLE orders DROP COLUMN IF EXISTS is_corrected;
ALTER TABLE orders DROP COLUMN IF EXISTS correction_reason;
ALTER TABLE orders DROP COLUMN IF EXISTS corrected_by;
ALTER TABLE orders DROP COLUMN IF EXISTS corrected_at;

-- ============================================================================
-- STEP 4: Verification
-- ============================================================================

DO $$
DECLARE
    deleted_tables TEXT[] := ARRAY[
        'api_keys',
        'alerts',
        'manual_corrections'
    ];
    deleted_columns TEXT[] := ARRAY[
        'is_corrected',
        'correction_reason',
        'corrected_by',
        'corrected_at'
    ];
    t TEXT;
    still_exists BOOLEAN;
    col_exists BOOLEAN;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'MIGRATION 031: Cleanup Unused Tables';
    RAISE NOTICE '============================================';

    -- Check tables
    RAISE NOTICE '';
    RAISE NOTICE 'Checking deleted tables:';
    FOREACH t IN ARRAY deleted_tables
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = t
        ) INTO still_exists;

        IF still_exists THEN
            RAISE WARNING '  FAILED: Table "%" still exists!', t;
        ELSE
            RAISE NOTICE '  OK: Table "%" dropped', t;
        END IF;
    END LOOP;

    -- Check columns removed from orders
    RAISE NOTICE '';
    RAISE NOTICE 'Checking removed columns from orders:';
    FOREACH t IN ARRAY deleted_columns
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'orders'
            AND column_name = t
        ) INTO col_exists;

        IF col_exists THEN
            RAISE WARNING '  FAILED: Column "orders.%" still exists!', t;
        ELSE
            RAISE NOTICE '  OK: Column "orders.%" removed', t;
        END IF;
    END LOOP;

    -- Summary
    RAISE NOTICE '';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Summary:';
    RAISE NOTICE '  - Tables deleted: 3 (api_keys, alerts, manual_corrections)';
    RAISE NOTICE '  - Columns removed: 4 (from orders table)';
    RAISE NOTICE '  - Trigger updated: update_product_stock()';
    RAISE NOTICE '============================================';
END $$;
