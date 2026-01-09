#!/bin/bash
# ============================================
# Grana Platform - Development Mode
# ============================================
# This script starts the app in DEVELOPMENT mode
# using local Supabase Docker (NOT production)
# ============================================

set -e

echo ""
echo -e "\033[0;32m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "\033[0;32m🍃 Grana Platform - DEVELOPMENT Mode\033[0m"
echo -e "\033[0;32m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ============================================
# 1. Check Docker
# ============================================
echo -e "${BLUE}🐳 Checking Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# ============================================
# 2. Check/Start Supabase Local
# ============================================
echo -e "${BLUE}🗄️  Checking Supabase local...${NC}"

# Check if Supabase containers are running
if docker ps | grep -q "supabase"; then
    echo -e "${GREEN}✅ Supabase local is already running${NC}"
else
    echo -e "${YELLOW}⚠️  Supabase local not running. Starting...${NC}"
    npx supabase start
    echo -e "${GREEN}✅ Supabase local started${NC}"
fi

# Show Supabase status
echo ""
echo -e "${BLUE}📊 Supabase local status:${NC}"
npx supabase status 2>/dev/null | grep -E "API URL|DB URL|Studio URL" || true
echo ""

# ============================================
# 3. Cleanup function
# ============================================
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${YELLOW}💡 Supabase local is still running. Stop with: npx supabase stop${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ============================================
# 4. Start Backend (FastAPI)
# ============================================
echo -e "${BLUE}🔧 Starting Backend (FastAPI)...${NC}"
echo -e "   Environment: ${GREEN}DEVELOPMENT${NC}"
echo -e "   Config: ${GREEN}.env.development${NC}"
echo ""

cd backend
export APP_ENV=development
unset DATABASE_URL
nohup bash -c 'source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000' > /tmp/grana_backend.log 2>&1 &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

# Wait for backend to start
sleep 3
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend running at http://localhost:8000${NC}"
else
    echo -e "${YELLOW}⚠️  Backend starting... (may take a few seconds)${NC}"
fi
echo ""

# ============================================
# 5. Start Frontend (Next.js)
# ============================================
echo -e "${BLUE}🎨 Starting Frontend (Next.js)...${NC}"
echo -e "   Environment: ${GREEN}DEVELOPMENT${NC}"
echo -e "   Config: ${GREEN}.env.development${NC}"
echo ""

cd frontend
# Next.js uses NODE_ENV and loads .env.development automatically
npm run dev > /tmp/grana_frontend.log 2>&1 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

# Wait for frontend to start
sleep 5
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend running at http://localhost:3000${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend starting... (may take a few seconds)${NC}"
fi

# ============================================
# 6. Summary
# ============================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Grana Platform running in DEVELOPMENT mode${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "   ${BLUE}Frontend:${NC}        http://localhost:3000"
echo -e "   ${BLUE}Backend API:${NC}     http://localhost:8000"
echo -e "   ${BLUE}API Docs:${NC}        http://localhost:8000/docs"
echo -e "   ${BLUE}Supabase Studio:${NC} http://127.0.0.1:54323"
echo ""
echo -e "   ${YELLOW}Database:${NC} Local Supabase Docker (NOT production)"
echo ""
echo -e "   Backend PID:  $BACKEND_PID"
echo -e "   Frontend PID: $FRONTEND_PID"
echo ""
echo -e "${YELLOW}📋 Logs:${NC}"
echo -e "   Backend:  tail -f /tmp/grana_backend.log"
echo -e "   Frontend: tail -f /tmp/grana_frontend.log"
echo ""
echo -e "${YELLOW}🛑 To stop: Ctrl+C${NC}"
echo -e "${YELLOW}🗄️  To stop Supabase: npx supabase stop${NC}"
echo ""

# Keep script running and show logs
tail -f /tmp/grana_frontend.log /tmp/grana_backend.log
