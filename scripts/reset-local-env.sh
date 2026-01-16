#!/bin/bash
# ============================================
# Full Local Environment Reset
# ============================================
# This script performs a complete reset of the local development environment:
#   1. Resets local Supabase database (applies migrations)
#   2. Loads fresh production data
#
# SAFE: Only affects LOCAL Docker database, never production.
#
# Usage: ./scripts/reset-local-env.sh
#
# NOTE: Handle git pull/merge manually before running this script
# ============================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🔄 Full Local Environment Reset${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}This script will:${NC}"
echo -e "   1. Reset local Supabase database (apply migrations)"
echo -e "   2. Load fresh production data"
echo ""
echo -e "${YELLOW}⚠️  Your local database will be COMPLETELY RESET.${NC}"
echo -e "${YELLOW}   Production database will NOT be affected.${NC}"
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
    exit 1
fi

echo -e "${GREEN}✅ Docker and Supabase local are running${NC}"
echo ""

# Show current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${CYAN}Current branch: ${CURRENT_BRANCH}${NC}"
echo ""

# Confirm
read -p "Continue with full reset? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# ============================================
# STEP 1: Reset Supabase database
# ============================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🗄️  Step 1/2: Resetting local Supabase database...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}Running: npx supabase db reset --local${NC}"
echo ""

# Reset with explicit --local flag for safety
npx supabase db reset --local

echo ""
echo -e "${GREEN}✅ Database reset complete (migrations applied)${NC}"

# ============================================
# STEP 2: Load production data
# ============================================
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📦 Step 2/2: Loading production data...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Run load-remote-data.sh but auto-confirm
# We do this by piping 'y' to the script
echo "y" | "$SCRIPT_DIR/load-remote-data.sh"

# ============================================
# DONE
# ============================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Full Environment Reset Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Summary:${NC}"
echo -e "   ✅ Database reset with migrations"
echo -e "   ✅ Production data loaded"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "   - Start development: ./dev.sh"
echo -e "   - View database: http://127.0.0.1:54323"
echo -e "   - API docs: http://localhost:8000/docs"
echo ""
