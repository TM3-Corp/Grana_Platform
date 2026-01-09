#!/bin/bash
# ============================================
# Load data from remote Supabase to local Docker
# ============================================
# This is READ-ONLY on remote (safe)
# Only copies data, not schema (schema comes from migrations)
# ============================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Remote (production) - READ ONLY
REMOTE_DB="postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

# Local (Docker)
LOCAL_DB="postgresql://postgres:postgres@127.0.0.1:54322/postgres"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📥 Load Remote Data to Local Supabase${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}⚠️  This will load production data to your LOCAL database.${NC}"
echo -e "${YELLOW}   Remote database will NOT be modified (read-only).${NC}"
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
echo -e "${BLUE}📤 Step 1/3: Dumping data from remote (this may take a minute)...${NC}"

# Use Docker's pg_dump (has correct PostgreSQL version)
docker run --rm --network host \
    public.ecr.aws/supabase/postgres:17.6.1.011 \
    pg_dump "$REMOTE_DB" \
    --data-only \
    --exclude-schema='auth' \
    --exclude-schema='storage' \
    --exclude-schema='supabase_*' \
    --exclude-schema='extensions' \
    --exclude-schema='graphql' \
    --exclude-schema='graphql_public' \
    --exclude-schema='realtime' \
    --exclude-schema='_realtime' \
    --exclude-schema='pgsodium*' \
    --exclude-schema='vault' \
    --exclude-table='schema_migrations' \
    --no-owner \
    --no-privileges \
    > /tmp/remote_data.sql

FILESIZE=$(du -h /tmp/remote_data.sql | cut -f1)
echo -e "${GREEN}✅ Data dumped: ${FILESIZE}${NC}"
echo ""

echo -e "${BLUE}📥 Step 2/3: Loading data to local database...${NC}"

# Load the data (suppress verbose output, show errors)
psql "$LOCAL_DB" -f /tmp/remote_data.sql 2>&1 | grep -E "^psql:|^ERROR:" || true

echo -e "${GREEN}✅ Data loaded${NC}"
echo ""

echo -e "${BLUE}📊 Step 3/3: Verifying data...${NC}"

# Show record counts
psql "$LOCAL_DB" -c "
SELECT
    'orders' as table_name, COUNT(*) as records FROM orders
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'product_catalog', COUNT(*) FROM product_catalog
UNION ALL SELECT 'users', COUNT(*) FROM users
ORDER BY records DESC;
"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Data loaded successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "View in Supabase Studio: ${BLUE}http://127.0.0.1:54323${NC}"
echo ""

# Cleanup
rm -f /tmp/remote_data.sql
