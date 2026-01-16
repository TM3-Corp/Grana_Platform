#!/bin/bash
# ============================================================================
# Setup Script - Grana Platform
# Instala todas las dependencias necesarias para desarrollo
# ============================================================================

set -e  # Exit on error

echo "🍃 Configurando Grana Platform..."
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ============================================================================
# 1. Verificar requisitos del sistema
# ============================================================================
echo -e "${BLUE}[1/5] Verificando requisitos del sistema...${NC}"

# Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no encontrado. Instala Python 3.10+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "   ✓ Python $PYTHON_VERSION"

# Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js no encontrado. Instala Node.js 18+${NC}"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "   ✓ Node.js $NODE_VERSION"

# npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm no encontrado${NC}"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo -e "   ✓ npm $NPM_VERSION"

echo ""

# ============================================================================
# 2. Backend - Python Virtual Environment + Dependencies
# ============================================================================
echo -e "${BLUE}[2/5] Configurando Backend (Python)...${NC}"

cd backend

# Crear venv si no existe
if [ ! -d "venv" ]; then
    echo "   Creando virtual environment..."
    python3 -m venv venv
fi

# Activar venv e instalar dependencias
echo "   Instalando dependencias..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo -e "   ${GREEN}✓ Backend configurado${NC}"
cd ..
echo ""

# ============================================================================
# 3. Frontend - Node Dependencies
# ============================================================================
echo -e "${BLUE}[3/5] Configurando Frontend (Node.js)...${NC}"

cd frontend

# Instalar dependencias
echo "   Instalando dependencias..."
npm install --silent

echo -e "   ${GREEN}✓ Frontend configurado${NC}"
cd ..
echo ""

# ============================================================================
# 4. Archivos de Entorno
# ============================================================================
echo -e "${BLUE}[4/5] Verificando archivos de entorno...${NC}"

# Backend
if [ ! -f "backend/.env.development" ]; then
    if [ -f "backend/.env.example" ]; then
        echo "   Copiando backend/.env.example -> backend/.env.development"
        cp backend/.env.example backend/.env.development
        echo -e "   ${YELLOW}⚠️  Edita backend/.env.development con tus credenciales${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Falta backend/.env.development${NC}"
    fi
else
    echo -e "   ✓ backend/.env.development existe"
fi

# Frontend
if [ ! -f "frontend/.env.development" ]; then
    echo -e "   ${YELLOW}⚠️  Falta frontend/.env.development${NC}"
    echo "   Creando con valores por defecto para Supabase local..."
    cat > frontend/.env.development << 'EOF'
# DEVELOPMENT - Supabase LOCAL
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
AUTH_SECRET=grana_platform_secret_key_2025_production_ready
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
    echo -e "   ${GREEN}✓ frontend/.env.development creado${NC}"
else
    echo -e "   ✓ frontend/.env.development existe"
fi

echo ""

# ============================================================================
# 5. Supabase (opcional)
# ============================================================================
echo -e "${BLUE}[5/5] Verificando Supabase...${NC}"

if command -v npx &> /dev/null; then
    if npx supabase --version &> /dev/null; then
        SUPABASE_VERSION=$(npx supabase --version 2>/dev/null)
        echo -e "   ✓ Supabase CLI $SUPABASE_VERSION"

        # Verificar si Docker esta corriendo
        if docker info &> /dev/null; then
            echo -e "   ✓ Docker esta corriendo"
            echo ""
            echo -e "${YELLOW}   Para iniciar Supabase local:${NC}"
            echo "      npx supabase start"
            echo "      npx supabase db reset"
        else
            echo -e "   ${YELLOW}⚠️  Docker no esta corriendo${NC}"
            echo "      Inicia Docker Desktop para usar Supabase local"
        fi
    else
        echo -e "   ${YELLOW}⚠️  Supabase CLI no instalado${NC}"
        echo "      Ejecuta: npm install -g supabase"
    fi
else
    echo -e "   ${YELLOW}⚠️  npx no disponible${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Setup completado!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Proximos pasos (DESARROLLO):"
echo -e "   1. ${BLUE}npx supabase start${NC}        # Iniciar Supabase local"
echo -e "   2. ${BLUE}npx supabase db reset${NC}    # Aplicar migraciones"
echo -e "   3. ${BLUE}./dev.sh${NC}                  # Iniciar la app"
echo ""
echo -e "Para PRODUCCION (base de datos remota):"
echo -e "   1. Copia los archivos .env.production de 1Password/Drive"
echo -e "      - backend/.env.production"
echo -e "      - frontend/.env.production"
echo -e "   2. ${BLUE}./prod.sh${NC}                  # Iniciar con DB produccion"
echo ""
echo -e "Scripts disponibles:"
echo -e "   ${BLUE}./setup.sh${NC}  - Instalar dependencias"
echo -e "   ${BLUE}./dev.sh${NC}    - Desarrollo (Supabase local)"
echo -e "   ${BLUE}./prod.sh${NC}   - Produccion (Supabase remoto)"
echo -e "   ${BLUE}./stop.sh${NC}   - Detener servicios"
echo ""
