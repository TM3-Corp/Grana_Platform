"""
Grana Platform - Backend API
Sistema de integración para Grana SpA
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from supabase import create_client, Client

# Configuración básica
API_TITLE = os.getenv("API_TITLE", "Grana API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# Inicializar cliente Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Error inicializando Supabase: {e}")

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

@app.get("/api/v1/test-db")
async def test_database_connection():
    """Endpoint de prueba - Verifica conexión REAL a Supabase"""
    if not supabase:
        raise HTTPException(
            status_code=500,
            detail="Supabase no está inicializado. Revisa las variables de entorno."
        )

    try:
        # Intentar leer canales de venta desde Supabase
        response = supabase.table("channels").select("*").limit(5).execute()

        return {
            "status": "success",
            "message": "✅ Conexión a Supabase exitosa",
            "database": "connected",
            "channels_found": len(response.data),
            "sample_channels": response.data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error conectando a Supabase: {str(e)}"
        )

# TODO: Agregar rutas para:
# - /api/v1/orders - Gestión de pedidos
# - /api/v1/channels - Gestión de canales de venta
# - /api/v1/customers - Gestión de clientes
# - /api/v1/products - Gestión de productos
# - /api/v1/sync - Sincronización con plataformas externas
