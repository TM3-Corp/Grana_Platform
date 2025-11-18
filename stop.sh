#!/bin/bash
# Script para detener Frontend + Backend de Grana Platform

echo "🛑 Deteniendo Grana Platform..."
echo ""

# Detener Backend (puerto 8000)
echo "🔧 Deteniendo Backend..."
BACKEND_PIDS=$(lsof -ti:8000 2>/dev/null)
if [ -n "$BACKEND_PIDS" ]; then
    echo "$BACKEND_PIDS" | xargs kill 2>/dev/null
    echo "✅ Backend detenido"
else
    echo "ℹ️  Backend no estaba corriendo"
fi

# Detener Frontend (puerto 3000)
echo "🎨 Deteniendo Frontend..."
FRONTEND_PIDS=$(lsof -ti:3000 2>/dev/null)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "$FRONTEND_PIDS" | xargs kill 2>/dev/null
    echo "✅ Frontend detenido"
else
    echo "ℹ️  Frontend no estaba corriendo"
fi

# También matar procesos de uvicorn y next
echo ""
echo "🧹 Limpiando procesos residuales..."
pkill -f "uvicorn.*grana" 2>/dev/null
pkill -f "next.*dev" 2>/dev/null

echo ""
echo "✅ Todos los servicios detenidos"
