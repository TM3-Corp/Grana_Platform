"""
Grana Platform - Backend API (Versión Simplificada)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Configuración básica
API_TITLE = os.getenv("API_TITLE", "Grana API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# Crear aplicación FastAPI
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="Sistema de Integración y Visualización de Datos para Grana"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "Grana API - Sistema de Integración",
        "status": "online",
        "version": API_VERSION
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}

@app.get("/api/v1/env-check")
async def env_check():
    """Verificar que las variables de entorno están llegando"""
    return {
        "SUPABASE_URL": "SET" if os.getenv("SUPABASE_URL") else "NOT_SET",
        "SUPABASE_SERVICE_ROLE_KEY": "SET" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "NOT_SET",
        "DATABASE_URL": "SET" if os.getenv("DATABASE_URL") else "NOT_SET"
    }
