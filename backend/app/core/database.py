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
    # Use settings.DATABASE_URL which loads from .env file
    database_url = settings.DATABASE_URL
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
    # Use settings.DATABASE_URL which loads from .env file
    database_url = settings.DATABASE_URL
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


# ============================================================================
# Database Connection with Retry Logic (SSL Failure Recovery)
# ============================================================================

import time
import logging

logger = logging.getLogger(__name__)


def get_db_connection_with_retry(max_retries=3, retry_delay=1.0):
    """
    Get a psycopg2 connection with automatic retry on SSL/connection failures

    This function handles intermittent Supabase connection issues by:
    - Retrying failed connections up to max_retries times
    - Adding exponential backoff between retries
    - Logging connection attempts for debugging

    Args:
        max_retries: Maximum number of connection attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)

    Returns:
        psycopg2 connection object

    Raises:
        psycopg2.OperationalError: If all retry attempts fail

    Example:
        conn = get_db_connection_with_retry()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders")
        results = cursor.fetchall()
        cursor.close()
        conn.close()
    """
    # Use settings.DATABASE_URL which loads from .env file
    database_url = settings.DATABASE_URL
    if not database_url:
        raise Exception("DATABASE_URL not configured")

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Database connection attempt {attempt}/{max_retries}")
            conn = psycopg2.connect(database_url)

            # Test connection with a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()

            logger.debug(f"Database connection successful on attempt {attempt}")
            return conn

        except psycopg2.OperationalError as e:
            last_error = e
            error_msg = str(e)

            # Check if it's an SSL connection error
            if "SSL connection has been closed unexpectedly" in error_msg:
                logger.warning(f"SSL connection error on attempt {attempt}/{max_retries}: {error_msg}")
            else:
                logger.warning(f"Connection error on attempt {attempt}/{max_retries}: {error_msg}")

            # Don't retry on last attempt
            if attempt < max_retries:
                # Exponential backoff
                delay = retry_delay * (2 ** (attempt - 1))
                logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} connection attempts failed")
                raise last_error

        except Exception as e:
            # For non-connection errors, fail immediately
            logger.error(f"Unexpected error during connection: {e}")
            raise

    # Should never reach here, but just in case
    raise last_error if last_error else Exception("Connection failed after all retries")


def get_db_connection_dict_with_retry(max_retries=3, retry_delay=1.0):
    """
    Get a psycopg2 connection with RealDictCursor and automatic retry

    Same as get_db_connection_with_retry but returns dicts instead of tuples.

    Args:
        max_retries: Maximum number of connection attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)

    Returns:
        psycopg2 connection with RealDictCursor

    Example:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders")
        results = cursor.fetchall()  # Returns list of dicts
        cursor.close()
        conn.close()
    """
    # Use settings.DATABASE_URL which loads from .env file
    database_url = settings.DATABASE_URL
    if not database_url:
        raise Exception("DATABASE_URL not configured")

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Database connection (dict) attempt {attempt}/{max_retries}")
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)

            # Test connection with a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()

            logger.debug(f"Database connection (dict) successful on attempt {attempt}")
            return conn

        except psycopg2.OperationalError as e:
            last_error = e
            error_msg = str(e)

            if "SSL connection has been closed unexpectedly" in error_msg:
                logger.warning(f"SSL connection error on attempt {attempt}/{max_retries}: {error_msg}")
            else:
                logger.warning(f"Connection error on attempt {attempt}/{max_retries}: {error_msg}")

            if attempt < max_retries:
                delay = retry_delay * (2 ** (attempt - 1))
                logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} connection attempts failed")
                raise last_error

        except Exception as e:
            logger.error(f"Unexpected error during connection: {e}")
            raise

    raise last_error if last_error else Exception("Connection failed after all retries")