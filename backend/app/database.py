"""
Database connection utilities
Simple psycopg2 connection helper for direct SQL access
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """
    Get a direct psycopg2 database connection

    Returns:
        psycopg2 connection object

    Raises:
        Exception if DATABASE_URL is not configured
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL not configured")

    return psycopg2.connect(database_url)


def get_db_connection_dict():
    """
    Get a database connection with RealDictCursor for dict results

    Returns:
        psycopg2 connection with RealDictCursor
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL not configured")

    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
