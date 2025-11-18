#!/bin/bash
# Script para levantar Frontend + Backend de Grana Platform

echo "🍃 Iniciando Grana Platform..."
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para limpiar procesos al salir
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Deteniendo servicios...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# 1. Levantar Backend (FastAPI)
echo -e "${BLUE}🔧 Levantando Backend (FastAPI en puerto 8000)...${NC}"
cd backend
nohup ./run.sh > /tmp/grana_backend.log 2>&1 &
BACKEND_PID=$!
cd ..
sleep 3

# Verificar que el backend esté corriendo
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend corriendo en http://localhost:8000${NC}"
else
    echo -e "${YELLOW}⚠️  Backend iniciando... (puede tomar unos segundos)${NC}"
fi

echo ""

# 2. Levantar Frontend (Next.js)
echo -e "${BLUE}🎨 Levantando Frontend (Next.js en puerto 3000)...${NC}"
cd frontend
npm run dev > /tmp/grana_frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
sleep 5

# Verificar que el frontend esté corriendo
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend corriendo en http://localhost:3000${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend iniciando... (puede tomar unos segundos)${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Grana Platform está corriendo!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "   📱 Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "   🔧 Backend:  ${BLUE}http://localhost:8000${NC}"
echo -e "   📚 API Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "   Backend PID: $BACKEND_PID"
echo -e "   Frontend PID: $FRONTEND_PID"
echo ""
echo -e "${YELLOW}💡 Logs:${NC}"
echo -e "   Backend:  tail -f /tmp/grana_backend.log"
echo -e "   Frontend: tail -f /tmp/grana_frontend.log"
echo ""
echo -e "${YELLOW}🛑 Para detener: Ctrl+C${NC}"
echo ""

# Mantener el script corriendo y mostrar logs en tiempo real
tail -f /tmp/grana_frontend.log /tmp/grana_backend.log
