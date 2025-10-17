"""
Pytest fixtures and configuration for Grana Platform Backend tests

This file provides shared fixtures that can be used across all test modules.

Author: TM3
Date: 2025-10-17
"""
import pytest
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables for tests
load_dotenv()


@pytest.fixture(scope="session")
def database_url():
    """
    Provides the database URL for tests

    Scope: session (created once per test session)
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not configured")
    return url


@pytest.fixture(scope="function")
def db_connection(database_url):
    """
    Provides a fresh database connection for each test

    Scope: function (new connection per test)
    Automatically closes connection after test
    """
    conn = psycopg2.connect(database_url)
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def db_cursor(db_connection):
    """
    Provides a database cursor with RealDictCursor for each test

    Scope: function (new cursor per test)
    Returns results as dictionaries instead of tuples
    """
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    yield cursor
    cursor.close()


@pytest.fixture(scope="session")
def api_base_url():
    """
    Provides the base URL for API tests

    Can be overridden with API_BASE_URL environment variable
    """
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def sample_product_data():
    """
    Provides sample product data for tests
    """
    return {
        "sku": "BAKC_U04010",
        "name": "Barra Keto Cacao",
        "source": "shopify",
        "category": "BARRAS",
        "unit": "1un"
    }


@pytest.fixture
def sample_order_data():
    """
    Provides sample order data for tests
    """
    return {
        "order_number": "TEST-001",
        "source": "shopify",
        "total": 15000,
        "status": "completed",
        "payment_status": "paid"
    }


# Add more fixtures as needed for specific test scenarios
