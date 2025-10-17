"""
Conexión a base de datos PostgreSQL (Supabase)

Este módulo centraliza TODAS las formas de acceso a la base de datos:
- SQLAlchemy ORM (para modelos complejos)
- psycopg2 directo (para queries SQL raw)
- Supabase client (para funcionalidades específicas de Supabase)

Author: TM3
Updated: 2025-10-17
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client
from .config import settings


# ============================================================================
# SQLAlchemy Configuration (for ORM models)
# ============================================================================

# SQLAlchemy Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verificar conexión antes de usar
    pool_size=10,  # Número de conexiones en el pool
    max_overflow=20,  # Conexiones extras si se necesitan
)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def get_db():
    """
    FastAPI dependency para obtener sesión de SQLAlchemy

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# psycopg2 Direct Connections (for raw SQL queries)
# ============================================================================

def get_db_connection():
    """
    Get a direct psycopg2 database connection (returns tuples)

    Use this for:
    - Raw SQL queries
    - Bulk operations
    - Performance-critical queries

    Returns:
        psycopg2 connection object

    Raises:
        Exception if DATABASE_URL is not configured

    Example:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders")
        results = cursor.fetchall()
        cursor.close()
        conn.close()
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL not configured")

    return psycopg2.connect(database_url)


def get_db_connection_dict():
    """
    Get a database connection with RealDictCursor (returns dictionaries)

    Use this for:
    - API responses (easier to serialize to JSON)
    - Code that expects dict results

    Returns:
        psycopg2 connection with RealDictCursor

    Example:
        conn = get_db_connection_dict()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders")
        results = cursor.fetchall()  # Returns list of dicts
        cursor.close()
        conn.close()
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL not configured")

    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


# ============================================================================
# Supabase Client (for Supabase-specific features)
# ============================================================================

# Supabase Client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_supabase():
    """
    FastAPI dependency para obtener cliente de Supabase

    Usage:
        @app.get("/data")
        def get_data(sb: Client = Depends(get_supabase)):
            ...
    """
    return supabase