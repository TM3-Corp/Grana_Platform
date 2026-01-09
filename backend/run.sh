#!/bin/bash
# Script para levantar el backend en modo DESARROLLO
# Usa .env.development (Supabase local Docker)

# Set environment to development (loads .env.development)
export APP_ENV=development

# Unset any system DATABASE_URL to ensure we use local config
unset DATABASE_URL

echo "🔧 Starting backend in DEVELOPMENT mode..."
echo "   Using: .env.development (local Supabase Docker)"
echo ""

source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
