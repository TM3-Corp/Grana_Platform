"""
Grana Platform - Backend API
Sistema de integración para Grana SpA
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Configuración básica
API_TITLE = os.getenv("API_TITLE", "Grana API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db_connection():
    """Context manager para conexiones a PostgreSQL"""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    except Exception as e:
        print(f"⚠️ Error conectando a la base de datos: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

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
    """Endpoint de prueba - Verifica conexión REAL a PostgreSQL"""
    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL no está configurado."
        )

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Intentar leer canales de venta
                cursor.execute("SELECT * FROM channels LIMIT 5")
                channels = cursor.fetchall()

                return {
                    "status": "success",
                    "message": "✅ Conexión a PostgreSQL exitosa",
                    "database": "connected",
                    "database_url_configured": True,
                    "channels_found": len(channels),
                    "sample_channels": channels
                }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error conectando a la base de datos: {str(e)}"
        )

# TODO: Agregar rutas para:
# - /api/v1/orders - Gestión de pedidos
# - /api/v1/channels - Gestión de canales de venta
# - /api/v1/customers - Gestión de clientes
# - /api/v1/products - Gestión de productos
# - /api/v1/sync - Sincronización con plataformas externas
