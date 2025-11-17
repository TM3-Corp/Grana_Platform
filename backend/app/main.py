"""
Grana Platform - Backend API
Sistema de integración para Grana SpA
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from contextlib import contextmanager
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Import API routers
from app.api import conversion, shopify, products, orders, mercadolibre, product_mapping, relbase, audit, inventory, sales_analytics, sales_analytics_realtime, admin, warehouses

# Import psycopg2 with error handling
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
    PSYCOPG2_ERROR = None
except Exception as e:
    PSYCOPG2_AVAILABLE = False
    PSYCOPG2_ERROR = str(e)

# Configuración básica
API_TITLE = os.getenv("API_TITLE", "Grana API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")

# CORS Configuration
# Allow localhost for development and any *.vercel.app for production
def get_allowed_origins():
    """Get list of allowed origins from environment variable"""
    origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    if origins_str == "*":
        return ["*"]
    return [origin.strip() for origin in origins_str.split(",")]

ALLOWED_ORIGINS = get_allowed_origins()

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db_connection():
    """Context manager para conexiones a PostgreSQL"""
    if not PSYCOPG2_AVAILABLE:
        raise Exception(f"psycopg2 no está disponible: {PSYCOPG2_ERROR}")

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

# Configurar CORS con soporte para dominios dinámicos de Vercel
# Si ALLOWED_ORIGINS es "*", permite cualquier origen
# Si no, verifica si el origen está en la lista O termina en .vercel.app
def custom_cors_origin_check(origin: str) -> bool:
    """Check if origin is allowed (supports Vercel dynamic subdomains)"""
    if "*" in ALLOWED_ORIGINS:
        return True
    if origin in ALLOWED_ORIGINS:
        return True
    # Allow all Vercel preview deployments
    if origin.endswith(".vercel.app"):
        return True
    return False

# Configure CORS with both specific origins and Vercel regex pattern
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel preview/production deployments
    allow_origins=ALLOWED_ORIGINS,  # Also allow specific origins from env (localhost + production)
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API routers
app.include_router(conversion.router, prefix="/api/v1/conversion", tags=["Conversion"])
app.include_router(shopify.router, prefix="/api/v1/shopify", tags=["Shopify"])
app.include_router(mercadolibre.router, prefix="/api/v1/mercadolibre", tags=["MercadoLibre"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(product_mapping.router, prefix="/api/v1/product-mapping", tags=["Product Mapping"])
app.include_router(relbase.router, prefix="/api/v1/relbase", tags=["Relbase"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
# Use real-time sales analytics (aligned with Audit data)
app.include_router(sales_analytics_realtime.router, prefix="/api/v1/sales-analytics", tags=["Sales Analytics"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(inventory.router)

# Warehouse Inventory routers (new system)
app.include_router(warehouses.warehouses_router)
app.include_router(warehouses.inventory_router)

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

@app.get("/api/v1/debug")
async def debug_status():
    """Debug: muestra estado del sistema y librerías"""
    return {
        "environment": {
            "DATABASE_URL_configured": bool(DATABASE_URL),
            "DATABASE_URL_preview": DATABASE_URL[:50] + "..." if DATABASE_URL else None
        },
        "libraries": {
            "psycopg2_available": PSYCOPG2_AVAILABLE,
            "psycopg2_error": PSYCOPG2_ERROR
        },
        "message": "Si ves esto, FastAPI está funcionando correctamente"
    }

@app.get("/api/v1/channels")
async def get_channels():
    """Listar todos los canales de venta"""
    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL no está configurado."
        )

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        id, code, name, description, type, is_active,
                        created_at, updated_at
                    FROM channels
                    ORDER BY name
                """)
                channels = cursor.fetchall()

                return {
                    "status": "success",
                    "count": len(channels),
                    "data": channels
                }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo canales: {str(e)}"
        )

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

# TODO: Agregar más rutas:
# - /api/v1/orders - Gestión de pedidos
# - /api/v1/customers - Gestión de clientes
# - /api/v1/products - Gestión de productos
# - /api/v1/sync - Sincronización con plataformas externas
