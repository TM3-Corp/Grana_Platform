-- Migration 029: Cleanup Obsolete Tables
-- Date: 2026-01-12
-- Updated: 2026-01-13 - Added customer_channel_rules data migration
-- Purpose: Remove unused/obsolete tables to simplify database schema
-- Reference: /docs/DATABASE_TABLE_USAGE_MAP.md
--
-- Tables being removed:
--   1. product_variants - Empty, replaced by product_catalog families
--   2. channel_equivalents - Empty, never implemented
--   3. channel_product_equivalents - Empty, abandoned concept
--   4. relbase_product_mappings - Replaced by sku_mappings
--   5. dim_date - Not used in queries (sales_facts_mv uses order_date directly)
--   6. ml_tokens - Migrated to api_credentials
--   7. inventory_movements - Low usage, no UI
--   8. customer_channel_rules - 4 records, migrated to customers.assigned_channel_id
--
-- Linear Issues: CORP-137 through CORP-144

-- ============================================================================
-- STEP 0: Migrate customer_channel_rules data to customers.assigned_channel_id
-- ============================================================================
-- This ensures all channel assignments are preserved before dropping the table.
-- Migration 012 already migrated 3 customers, but customer 1314455 was added later.

-- Migrate any customer_channel_rules entries that aren't already in customers
UPDATE customers c
SET
    assigned_channel_id = ccr.channel_external_id,
    assigned_channel_name = ccr.channel_name,
    channel_assigned_by = 'migration_029_from_customer_channel_rules',
    channel_assigned_at = NOW()
FROM customer_channel_rules ccr
WHERE c.external_id = ccr.customer_external_id
  AND c.source = 'relbase'
  AND c.assigned_channel_id IS NULL
  AND ccr.is_active = TRUE;

-- Verify migration (will show in NOTICE output)
DO $$
DECLARE
    migrated_count INTEGER;
    unmigrated_count INTEGER;
BEGIN
    -- Count customers with assigned_channel_id from the rules
    SELECT COUNT(*) INTO migrated_count
    FROM customers c
    WHERE c.source = 'relbase'
      AND c.assigned_channel_id IS NOT NULL
      AND EXISTS (
          SELECT 1 FROM customer_channel_rules ccr
          WHERE ccr.customer_external_id = c.external_id
      );

    -- Count rules that weren't migrated (customer doesn't exist)
    SELECT COUNT(*) INTO unmigrated_count
    FROM customer_channel_rules ccr
    WHERE NOT EXISTS (
        SELECT 1 FROM customers c
        WHERE c.external_id = ccr.customer_external_id
          AND c.source = 'relbase'
    );

    RAISE NOTICE '';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'STEP 0: Migrate customer_channel_rules';
    RAISE NOTICE '============================================';
    RAISE NOTICE '  - Rules migrated to customers.assigned_channel_id: %', migrated_count;
    IF unmigrated_count > 0 THEN
        RAISE WARNING '  - Rules not migrated (customer not found): %', unmigrated_count;
    END IF;
END $$;

-- ============================================================================
-- STEP 1: Drop dependent views FIRST (before dropping tables they reference)
-- ============================================================================

-- Views from migration 001 that depend on product_variants
DROP VIEW IF EXISTS inventory_consolidated CASCADE;
DROP VIEW IF EXISTS product_families CASCADE;

-- ============================================================================
-- STEP 2: Drop tables with foreign keys TO other tables first
-- ============================================================================

-- inventory_movements has FK to orders(id)
DROP TABLE IF EXISTS inventory_movements CASCADE;

-- product_variants has FKs to products(id)
DROP TABLE IF EXISTS product_variants CASCADE;

-- channel_equivalents has FKs to products(id)
DROP TABLE IF EXISTS channel_equivalents CASCADE;

-- ============================================================================
-- STEP 3: Drop standalone tables (no FK dependencies)
-- ============================================================================

-- channel_product_equivalents - empty, abandoned
DROP TABLE IF EXISTS channel_product_equivalents CASCADE;

-- relbase_product_mappings - replaced by sku_mappings
DROP TABLE IF EXISTS relbase_product_mappings CASCADE;

-- dim_date - not used in any queries
DROP TABLE IF EXISTS dim_date CASCADE;

-- ml_tokens - migrated to api_credentials
DROP TABLE IF EXISTS ml_tokens CASCADE;

-- customer_channel_rules - only 4 records, moving to customers table
DROP TABLE IF EXISTS customer_channel_rules CASCADE;

-- ============================================================================
-- STEP 4: Verification
-- ============================================================================

DO $$
DECLARE
    deleted_tables TEXT[] := ARRAY[
        'product_variants',
        'channel_equivalents',
        'channel_product_equivalents',
        'relbase_product_mappings',
        'dim_date',
        'ml_tokens',
        'inventory_movements',
        'customer_channel_rules'
    ];
    deleted_views TEXT[] := ARRAY[
        'inventory_consolidated',
        'product_families'
    ];
    t TEXT;
    still_exists BOOLEAN;
    remaining_count INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'MIGRATION 029: Cleanup Obsolete Tables';
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

    -- Check views
    RAISE NOTICE '';
    RAISE NOTICE 'Checking deleted views:';
    FOREACH t IN ARRAY deleted_views
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.views
            WHERE table_schema = 'public'
            AND table_name = t
        ) INTO still_exists;

        IF still_exists THEN
            RAISE WARNING '  FAILED: View "%" still exists!', t;
        ELSE
            RAISE NOTICE '  OK: View "%" dropped', t;
        END IF;
    END LOOP;

    -- Summary
    SELECT COUNT(*) INTO remaining_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';

    RAISE NOTICE '';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Summary:';
    RAISE NOTICE '  - Tables deleted: 8';
    RAISE NOTICE '  - Views deleted: 2';
    RAISE NOTICE '  - Remaining base tables: %', remaining_count;
    RAISE NOTICE '============================================';
END $$;

-- ============================================================================
-- Post-migration code cleanup status:
-- ============================================================================
--
-- COMPLETED (2026-01-13):
--
-- 1. app/api/audit.py
--    - FIXED: Removed all customer_channel_rules references (14 occurrences)
--    - Now uses customers.assigned_channel_id via ch_assigned JOIN
--
-- 2. app/api/sales_analytics_realtime.py
--    - FIXED: Removed all customer_channel_rules references (5 occurrences)
--    - Now uses customers.assigned_channel_id via ch_assigned JOIN
--
-- 3. app/services/sync_service.py
--    - FIXED: Already updated to use customers.assigned_channel_id
--    - Only comments remain referencing the old table
--
-- STILL NEEDS REVIEW (may or may not need changes):
--
-- 4. app/repositories/product_mapping_repository.py
--    - Uses inventory_consolidated view (now dropped)
--    - Uses product_families view (now dropped)
--    - ACTION: Remove or refactor these methods if they exist
--
-- 5. app/services/inventory_service.py
--    - May have INSERT INTO inventory_movements
--    - ACTION: Remove inventory movement logging code if present
--
-- 6. scripts/debug/check_current_data.py
--    - May reference inventory_movements
--    - ACTION: Remove this query if present
--
-- 7. tests/test_integration/test_connection.py
--    - Lists expected tables
--    - ACTION: Update expected tables list
--
-- ============================================================================
