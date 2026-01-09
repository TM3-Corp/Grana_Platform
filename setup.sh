#!/bin/bash
# ============================================
# First-time setup script for Grana Platform
# ============================================
# Run this once after cloning the repository
# Sets up DEVELOPMENT environment (local Supabase Docker)
# ============================================

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🍃 Grana Platform - First Time Setup${NC}"
echo -e "${GREEN}   Environment: DEVELOPMENT (Local Supabase)${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check prerequisites
echo -e "${BLUE}📋 Checking prerequisites...${NC}"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "   ✅ Python: $PYTHON_VERSION"
else
    echo -e "   ${RED}❌ Python3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "   ✅ Node.js: $NODE_VERSION"
else
    echo -e "   ${RED}❌ Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "   ✅ npm: $NPM_VERSION"
else
    echo -e "   ${RED}❌ npm not found. Please install npm${NC}"
    exit 1
fi

echo ""

# ============================================
# Backend Setup
# ============================================
echo -e "${BLUE}🔧 Setting up Backend...${NC}"

cd "$SCRIPT_DIR/backend"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "   Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "   ${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "   ${YELLOW}⚠️  Virtual environment already exists${NC}"
fi

# Activate venv and install dependencies
echo -e "   Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "   ${GREEN}✅ Backend dependencies installed${NC}"

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "   ${YELLOW}⚠️  No .env file found. Copying from .env.example${NC}"
        cp .env.example .env
        echo -e "   ${YELLOW}📝 Please edit backend/.env with your credentials${NC}"
    else
        echo -e "   ${RED}❌ No .env or .env.example found${NC}"
    fi
else
    echo -e "   ${GREEN}✅ .env file exists${NC}"
fi

cd "$SCRIPT_DIR"
echo ""

# ============================================
# Frontend Setup
# ============================================
echo -e "${BLUE}🎨 Setting up Frontend...${NC}"

cd "$SCRIPT_DIR/frontend"

# Install npm dependencies
if [ ! -d "node_modules" ]; then
    echo -e "   Installing npm dependencies..."
    npm install
    echo -e "   ${GREEN}✅ Frontend dependencies installed${NC}"
else
    echo -e "   ${YELLOW}⚠️  node_modules already exists. Running npm install to ensure up-to-date...${NC}"
    npm install -q
    echo -e "   ${GREEN}✅ Frontend dependencies verified${NC}"
fi

# Check for .env.local file
if [ ! -f ".env.local" ]; then
    echo -e "   ${YELLOW}⚠️  No .env.local file found${NC}"
    echo -e "   ${YELLOW}📝 Please create frontend/.env.local with your credentials${NC}"
else
    echo -e "   ${GREEN}✅ .env.local file exists${NC}"
fi

cd "$SCRIPT_DIR"
echo ""

# ============================================
# Git Hooks (Optional)
# ============================================
echo -e "${BLUE}🪝 Setting up Git hooks...${NC}"
if [ -f "scripts/setup-git-hooks.sh" ]; then
    ./scripts/setup-git-hooks.sh 2>/dev/null || true
    echo -e "   ${GREEN}✅ Git hooks configured${NC}"
else
    echo -e "   ${YELLOW}⚠️  Git hooks script not found${NC}"
fi

echo ""

# ============================================
# Summary
# ============================================
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo -e "   1. Start Supabase local (Docker):"
echo -e "      ${GREEN}npx supabase start${NC}"
echo -e "      ${GREEN}npx supabase db reset${NC}  (apply migrations)"
echo ""
echo -e "   2. Start the application:"
echo -e "      ${GREEN}./dev.sh${NC}"
echo ""
echo -e "   3. Access the app:"
echo -e "      - Frontend:        ${BLUE}http://localhost:3000${NC}"
echo -e "      - Backend:         ${BLUE}http://localhost:8000${NC}"
echo -e "      - API Docs:        ${BLUE}http://localhost:8000/docs${NC}"
echo -e "      - Supabase Studio: ${BLUE}http://127.0.0.1:54323${NC}"
echo ""
echo -e "   4. Stop the application:"
echo -e "      ${GREEN}./stop.sh${NC} or ${GREEN}Ctrl+C${NC}"
echo -e "      ${GREEN}npx supabase stop${NC}  (stop Docker containers)"
echo ""
echo -e "${YELLOW}📖 See supabase/REMOTE_SUPABASE_SETUP.md for full local setup guide${NC}"
echo ""
