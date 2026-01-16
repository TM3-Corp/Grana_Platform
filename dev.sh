#!/bin/bash
# ============================================
# Grana Platform - DEVELOPMENT Mode
# ============================================
# Verifica Docker, Supabase, .env files y levanta la app
# Conecta a: Supabase LOCAL (Docker) - NO produccion
# ============================================

set -e

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🍃 Grana Platform - DEVELOPMENT${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ============================================
# 1. Verificar Docker
# ============================================
echo -e "${BLUE}[1/6] Verificando Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}   ❌ Docker no esta corriendo${NC}"
    echo -e "${YELLOW}   Inicia Docker Desktop y vuelve a correr ./dev.sh${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ Docker corriendo${NC}"

# ============================================
# 2. Verificar/Iniciar Supabase Local
# ============================================
echo -e "${BLUE}[2/6] Verificando Supabase local...${NC}"
if ! docker ps | grep -q "supabase"; then
    echo -e "${YELLOW}   ⚠️  Supabase no esta corriendo. Iniciando...${NC}"
    npx supabase start
fi
echo -e "${GREEN}   ✅ Supabase local corriendo${NC}"

# Verificar que la DB tenga tablas (migraciones aplicadas)
TABLE_COUNT=$(psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
if [ "$TABLE_COUNT" -lt 5 ] 2>/dev/null; then
    echo -e "${YELLOW}   ⚠️  Base de datos vacia. Ejecuta:${NC}"
    echo -e "${CYAN}      npx supabase db reset${NC}"
    echo -e "${CYAN}      ./scripts/load-remote-data.sh${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ Base de datos con $TABLE_COUNT tablas${NC}"

# ============================================
# 3. Verificar archivos .env
# ============================================
echo -e "${BLUE}[3/6] Verificando archivos .env...${NC}"

MISSING_ENV=0

if [ ! -f "backend/.env.development" ]; then
    echo -e "${RED}   ❌ Falta backend/.env.development${NC}"
    MISSING_ENV=1
else
    echo -e "${GREEN}   ✅ backend/.env.development${NC}"
fi

if [ ! -f "frontend/.env.development" ]; then
    echo -e "${RED}   ❌ Falta frontend/.env.development${NC}"
    MISSING_ENV=1
else
    echo -e "${GREEN}   ✅ frontend/.env.development${NC}"
fi

if [ $MISSING_ENV -eq 1 ]; then
    echo -e "${YELLOW}   Copia los archivos desde feat/seba:${NC}"
    echo -e "${CYAN}      git checkout feat/seba -- backend/.env.development frontend/.env.development${NC}"
    exit 1
fi

# Verificar AUTH_SECRET en frontend
if ! grep -q "AUTH_SECRET" frontend/.env.development 2>/dev/null; then
    echo -e "${RED}   ❌ frontend/.env.development no tiene AUTH_SECRET${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ AUTH_SECRET configurado${NC}"

# ============================================
# 4. Cleanup function
# ============================================
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Deteniendo servicios...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${YELLOW}   Supabase sigue corriendo. Para detenerlo: npx supabase stop${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ============================================
# 5. Levantar Backend
# ============================================
echo -e "${BLUE}[4/6] Levantando Backend (FastAPI)...${NC}"

cd "$SCRIPT_DIR/backend"
source venv/bin/activate

# Exportar variables explicitamente para asegurar que use local
export APP_ENV=development
export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
export SUPABASE_URL="http://127.0.0.1:54321"

nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/grana_backend.log 2>&1 &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

sleep 3
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Backend en http://localhost:8000${NC}"
else
    echo -e "${YELLOW}   ⏳ Backend iniciando...${NC}"
fi

# ============================================
# 6. Levantar Frontend
# ============================================
echo -e "${BLUE}[5/6] Levantando Frontend (Next.js)...${NC}"

cd "$SCRIPT_DIR/frontend"
npm run dev > /tmp/grana_frontend.log 2>&1 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

sleep 5
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Frontend en http://localhost:3000${NC}"
else
    echo -e "${YELLOW}   ⏳ Frontend iniciando...${NC}"
fi

# ============================================
# 7. Resumen
# ============================================
echo ""
echo -e "${BLUE}[6/6] Verificacion final...${NC}"
echo -e "${GREEN}   ✅ Entorno: DEVELOPMENT${NC}"
echo -e "${GREEN}   ✅ Database: Supabase LOCAL (Docker)${NC}"
echo -e "${GREEN}   ✅ Backend .env: .env.development${NC}"
echo -e "${GREEN}   ✅ Frontend .env: .env.development${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Grana Platform DEVELOPMENT corriendo${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "   ${CYAN}Frontend:${NC}        http://localhost:3000"
echo -e "   ${CYAN}Backend:${NC}         http://localhost:8000"
echo -e "   ${CYAN}API Docs:${NC}        http://localhost:8000/docs"
echo -e "   ${CYAN}Supabase Studio:${NC} http://127.0.0.1:54323"
echo ""
echo -e "   ${YELLOW}Database:${NC} postgresql://postgres:postgres@127.0.0.1:54322/postgres"
echo ""
echo -e "${YELLOW}📋 Logs:${NC}"
echo -e "   tail -f /tmp/grana_backend.log"
echo -e "   tail -f /tmp/grana_frontend.log"
echo ""
echo -e "${YELLOW}🛑 Para detener: Ctrl+C${NC}"
echo ""

# Mostrar logs
tail -f /tmp/grana_frontend.log /tmp/grana_backend.log
