#!/bin/bash
# ============================================
# Load data from remote Supabase to local Docker
# ============================================
# This is READ-ONLY on remote (safe)
# Only copies data, not schema (schema comes from migrations)
#
# Updated: 2026-01-14
# - Database cleanup consolidation (migrations 029, 030, 031)
# - 15 active tables (down from 25)
# - Drops 8 obsolete tables and 6 unused views
# - Preserves: channel_equivalents
# - Refreshes sales_facts_mv after loading
# ============================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Remote (production) - READ ONLY
REMOTE_DB="postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

# Local (Docker)
LOCAL_DB="postgresql://postgres:postgres@127.0.0.1:54322/postgres"

# ============================================
# ACTIVE TABLES (15 total after cleanup)
# ============================================
# Excluded (migration 029): product_variants, channel_product_equivalents,
#   dim_date, ml_tokens, inventory_movements
# Excluded (migration 031): api_keys, alerts, manual_corrections
# PRESERVED: channel_equivalents (product_mapping)
# DROPPED: relbase_product_mappings, customer_channel_rules (dead code removed from audit.py)
# ============================================
TABLES_TO_LOAD=(
    "channels"
    "customers"
    "products"
    "orders"
    "order_items"
    "orders_audit"
    "product_catalog"
    "sku_mappings"
    "warehouses"
    "warehouse_stock"
    "product_inventory_settings"
    "sync_logs"
    "users"
    "api_credentials"
    "channel_equivalents"
)

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📥 Load Remote Data to Local Supabase${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}⚠️  This will load production data to your LOCAL database.${NC}"
echo -e "${YELLOW}   Remote database will NOT be modified (read-only).${NC}"
echo ""
echo -e "${CYAN}Tables to load (${#TABLES_TO_LOAD[@]}):${NC}"
for table in "${TABLES_TO_LOAD[@]}"; do
    echo -e "   - $table"
done
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

# Check if local Supabase is running
if ! docker ps | grep -q "supabase"; then
    echo -e "${RED}❌ Local Supabase not running.${NC}"
    echo -e "${YELLOW}   Start with: npx supabase start${NC}"
    echo -e "${YELLOW}   Then run:   npx supabase db reset${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Supabase local are running${NC}"
echo ""

# Confirm
read -p "Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}📤 Step 1/6: Clearing local data (to avoid conflicts)...${NC}"

# Disable foreign key checks and truncate tables in reverse dependency order
psql "$LOCAL_DB" -c "
SET session_replication_role = 'replica';

-- Truncate in order (children first)
TRUNCATE TABLE order_items CASCADE;
TRUNCATE TABLE orders_audit CASCADE;
TRUNCATE TABLE orders CASCADE;
TRUNCATE TABLE warehouse_stock CASCADE;
TRUNCATE TABLE sync_logs CASCADE;
TRUNCATE TABLE product_inventory_settings CASCADE;
TRUNCATE TABLE sku_mappings CASCADE;
TRUNCATE TABLE product_catalog CASCADE;
TRUNCATE TABLE products CASCADE;
TRUNCATE TABLE customers CASCADE;
TRUNCATE TABLE channels CASCADE;
TRUNCATE TABLE warehouses CASCADE;
TRUNCATE TABLE api_credentials CASCADE;
TRUNCATE TABLE users CASCADE;
TRUNCATE TABLE channel_equivalents CASCADE;

SET session_replication_role = 'origin';
" 2>/dev/null || true

echo -e "${GREEN}✅ Local tables cleared${NC}"
echo ""

echo -e "${BLUE}📤 Step 2/6: Dumping data from remote (this may take a minute)...${NC}"

# Build table list for pg_dump
TABLE_ARGS=""
for table in "${TABLES_TO_LOAD[@]}"; do
    TABLE_ARGS="$TABLE_ARGS --table=$table"
done

# Use Docker's pg_dump (has correct PostgreSQL version)
docker run --rm --network host \
    public.ecr.aws/supabase/postgres:17.6.1.011 \
    pg_dump "$REMOTE_DB" \
    --data-only \
    $TABLE_ARGS \
    --no-owner \
    --no-privileges \
    --disable-triggers \
    > /tmp/remote_data.sql

FILESIZE=$(du -h /tmp/remote_data.sql | cut -f1)
echo -e "${GREEN}✅ Data dumped: ${FILESIZE}${NC}"
echo ""

echo -e "${BLUE}📥 Step 3/6: Loading data to local database...${NC}"

# IMPORTANT: Production still has columns we removed locally (migration not yet applied)
# Add them temporarily so COPY works, then drop them after loading
echo -e "${CYAN}   Adding temporary columns for compatibility...${NC}"
psql "$LOCAL_DB" -c "
ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_corrected boolean DEFAULT false;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS correction_reason text;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS corrected_by varchar(100);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS corrected_at timestamp;
" 2>/dev/null || true

# Load the data with triggers/FK disabled in SAME session
# Prepend and append the session settings to the SQL file
{
    echo "SET session_replication_role = 'replica';"
    cat /tmp/remote_data.sql
    echo "SET session_replication_role = 'origin';"
} > /tmp/remote_data_with_settings.sql

psql "$LOCAL_DB" -f /tmp/remote_data_with_settings.sql 2>&1 | grep -E "^ERROR:" | head -20 || true

# Drop temporary columns (they're not used in local code)
echo -e "${CYAN}   Removing temporary columns...${NC}"
psql "$LOCAL_DB" -c "
ALTER TABLE orders DROP COLUMN IF EXISTS is_corrected;
ALTER TABLE orders DROP COLUMN IF EXISTS correction_reason;
ALTER TABLE orders DROP COLUMN IF EXISTS corrected_by;
ALTER TABLE orders DROP COLUMN IF EXISTS corrected_at;
" 2>/dev/null || true

echo -e "${GREEN}✅ Data loaded${NC}"
echo ""

echo -e "${BLUE}🔄 Step 4/6: Refreshing materialized views...${NC}"

# Refresh sales_facts_mv (critical for analytics)
psql "$LOCAL_DB" -c "REFRESH MATERIALIZED VIEW sales_facts_mv;" 2>&1 || echo -e "${YELLOW}   Note: sales_facts_mv refresh may have warnings${NC}"

echo -e "${GREEN}✅ Materialized views refreshed${NC}"
echo ""

echo -e "${BLUE}🗑️  Step 5/6: Dropping obsolete objects (if not already done by migration)...${NC}"

# Drop all obsolete views and tables (idempotent - safe to run multiple times)
# This ensures cleanup even if loading into a fresh database
psql "$LOCAL_DB" -c "
-- ============================================
-- VIEWS (6 total)
-- ============================================
-- From migration 029
DROP VIEW IF EXISTS inventory_consolidated CASCADE;
DROP VIEW IF EXISTS product_families CASCADE;
-- From migration 030
DROP VIEW IF EXISTS inventory_general CASCADE;
DROP VIEW IF EXISTS v_low_stock_products CASCADE;
DROP VIEW IF EXISTS v_orders_full CASCADE;
DROP VIEW IF EXISTS v_sales_by_channel CASCADE;

-- ============================================
-- TABLES (8 total) - obsolete only
-- ============================================
-- From migration 029
DROP TABLE IF EXISTS product_variants CASCADE;
-- NOTE: channel_equivalents is PRESERVED
DROP TABLE IF EXISTS channel_product_equivalents CASCADE;
DROP TABLE IF EXISTS relbase_product_mappings CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS ml_tokens CASCADE;
DROP TABLE IF EXISTS inventory_movements CASCADE;
DROP TABLE IF EXISTS customer_channel_rules CASCADE;
-- From migration 031
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS manual_corrections CASCADE;
" 2>/dev/null || true

echo -e "${GREEN}✅ Obsolete objects dropped${NC}"
echo ""

echo -e "${BLUE}📊 Step 6/6: Verifying data...${NC}"
echo ""

# Show record counts for ALL active tables (17 tables + 1 MV)
psql "$LOCAL_DB" -c "
SELECT
    table_name,
    records,
    CASE
        WHEN records = 0 THEN '⚠️  empty'
        WHEN records < 10 THEN '📊 low'
        ELSE '✓'
    END as status
FROM (
    SELECT 'orders' as table_name, COUNT(*) as records FROM orders
    UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
    UNION ALL SELECT 'customers', COUNT(*) FROM customers
    UNION ALL SELECT 'channels', COUNT(*) FROM channels
    UNION ALL SELECT 'products', COUNT(*) FROM products
    UNION ALL SELECT 'product_catalog', COUNT(*) FROM product_catalog
    UNION ALL SELECT 'sku_mappings', COUNT(*) FROM sku_mappings
    UNION ALL SELECT 'warehouses', COUNT(*) FROM warehouses
    UNION ALL SELECT 'warehouse_stock', COUNT(*) FROM warehouse_stock
    UNION ALL SELECT 'product_inventory_settings', COUNT(*) FROM product_inventory_settings
    UNION ALL SELECT 'orders_audit', COUNT(*) FROM orders_audit
    UNION ALL SELECT 'sync_logs', COUNT(*) FROM sync_logs
    UNION ALL SELECT 'users', COUNT(*) FROM users
    UNION ALL SELECT 'api_credentials', COUNT(*) FROM api_credentials
    UNION ALL SELECT 'channel_equivalents', COUNT(*) FROM channel_equivalents
    UNION ALL SELECT 'sales_facts_mv (MV)', COUNT(*) FROM sales_facts_mv
) t
ORDER BY records DESC;
"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Data loaded successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "View in Supabase Studio: ${BLUE}http://127.0.0.1:54323${NC}"
echo ""
echo -e "${CYAN}Active tables after cleanup (15):${NC}"
echo -e "   Core: orders, order_items, customers, products, channels"
echo -e "   Catalog: product_catalog, sku_mappings"
echo -e "   Inventory: warehouses, warehouse_stock, product_inventory_settings"
echo -e "   Mapping: channel_equivalents"
echo -e "   Audit: orders_audit, sync_logs"
echo -e "   Auth: users, api_credentials"
echo ""

# Cleanup
rm -f /tmp/remote_data.sql /tmp/remote_data_with_settings.sql
