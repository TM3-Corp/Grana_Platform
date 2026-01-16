#!/bin/bash
# Script para levantar Frontend + Backend de Grana Platform (PRODUCTION)
# Usa: .env (backend) + .env.local (frontend)
# Conecta a: Supabase REMOTO (Produccion)
#
# ADVERTENCIA: Este script conecta a la base de datos de PRODUCCION
# Usalo solo para debugging de UI o testing con datos reales

export APP_ENV=production

echo "🚀 Iniciando Grana Platform (PRODUCTION)..."
echo ""
echo -e "\033[1;31m⚠️  ADVERTENCIA: Conectando a BASE DE DATOS DE PRODUCCION\033[0m"
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funcion para limpiar procesos al salir
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Deteniendo servicios...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Verificar que existan los archivos de produccion
if [ ! -f "backend/.env.production" ]; then
    echo -e "${RED}❌ Error: backend/.env.production no existe${NC}"
    echo "   Crea el archivo con las credenciales de produccion"
    exit 1
fi

if [ ! -f "frontend/.env.production" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: frontend/.env.production no existe${NC}"
    echo "   El frontend usara .env.development como fallback"
fi

# 1. Levantar Backend (FastAPI)
echo -e "${BLUE}🔧 Levantando Backend (FastAPI en puerto 8000)...${NC}"
cd backend
# Unset system DATABASE_URL to use the one from .env
unset DATABASE_URL
source venv/bin/activate
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/grana_backend_prod.log 2>&1 &
BACKEND_PID=$!
cd ..
sleep 3

# Verificar que el backend este corriendo
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend corriendo en http://localhost:8000${NC}"
else
    echo -e "${YELLOW}⚠️  Backend iniciando... (puede tomar unos segundos)${NC}"
fi

echo ""

# 2. Levantar Frontend (Next.js)
echo -e "${BLUE}🎨 Levantando Frontend (Next.js en puerto 3000)...${NC}"
cd frontend
npm run dev > /tmp/grana_frontend_prod.log 2>&1 &
FRONTEND_PID=$!
cd ..
sleep 5

# Verificar que el frontend este corriendo
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend corriendo en http://localhost:3000${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend iniciando... (puede tomar unos segundos)${NC}"
fi

echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}🚀 Grana Platform (PROD) esta corriendo!${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "   📱 Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "   🔧 Backend:  ${BLUE}http://localhost:8000${NC}"
echo -e "   📚 API Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "   Backend PID: $BACKEND_PID"
echo -e "   Frontend PID: $FRONTEND_PID"
echo ""
echo -e "${YELLOW}💡 Logs:${NC}"
echo -e "   Backend:  tail -f /tmp/grana_backend_prod.log"
echo -e "   Frontend: tail -f /tmp/grana_frontend_prod.log"
echo ""
echo -e "${RED}⚠️  RECUERDA: Estas conectado a PRODUCCION${NC}"
echo -e "${YELLOW}🛑 Para detener: Ctrl+C${NC}"
echo ""

# Mantener el script corriendo y mostrar logs en tiempo real
tail -f /tmp/grana_frontend_prod.log /tmp/grana_backend_prod.log
