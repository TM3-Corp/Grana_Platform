"""
Grana Platform - Backend API
Sistema de integración para Grana SpA
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
    """Endpoint raíz - Verificación de estado de la API"""
    return {
        "message": "Grana API - Sistema de Integración",
        "status": "online",
        "version": API_VERSION,
        "description": "API para consolidación de datos de ventas de Grana SpA"
    }

@app.get("/health")
async def health():
    """Health check endpoint para monitoreo"""
    return {
        "status": "healthy",
        "service": "grana-api",
        "version": API_VERSION
    }

@app.get("/api/v1/status")
async def api_status():
    """Estado de las integraciones"""
    return {
        "supabase": {
            "connected": bool(os.getenv("SUPABASE_URL")),
            "status": "configured" if os.getenv("SUPABASE_URL") else "not_configured"
        },
        "integrations": {
            "shopify": bool(os.getenv("SHOPIFY_PASSWORD")),
            "mercadolibre": bool(os.getenv("MERCADOLIBRE_CLIENT_ID")),
            "walmart": bool(os.getenv("WALMART_CLIENT_ID")),
            "cencosud": bool(os.getenv("CENCOSUD_ACCESS_TOKEN"))
        }
    }

@app.get("/api/v1/debug/env")
async def debug_env():
    """Debug endpoint - Ver qué variables están disponibles (TEMPORAL)"""
    return {
        "env_vars": {
            "SUPABASE_URL": "SET" if os.getenv("SUPABASE_URL") else "NOT_SET",
            "SUPABASE_URL_value": os.getenv("SUPABASE_URL", "")[:30] + "..." if os.getenv("SUPABASE_URL") else None,
            "DATABASE_URL": "SET" if os.getenv("DATABASE_URL") else "NOT_SET",
            "API_HOST": os.getenv("API_HOST", "NOT_SET"),
            "API_PORT": os.getenv("API_PORT", "NOT_SET"),
            "PORT": os.getenv("PORT", "NOT_SET"),
            "ALLOWED_ORIGINS": os.getenv("ALLOWED_ORIGINS", "NOT_SET"),
        },
        "all_env_keys": [key for key in os.environ.keys() if not key.startswith("_")]
    }

# TODO: Agregar rutas para:
# - /api/v1/orders - Gestión de pedidos
# - /api/v1/channels - Gestión de canales de venta
# - /api/v1/customers - Gestión de clientes
# - /api/v1/products - Gestión de productos
# - /api/v1/sync - Sincronización con plataformas externas
