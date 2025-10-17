# 🧪 Tests - Grana Platform Backend

This directory contains all automated tests for the Grana Platform backend API.

## 📁 Test Structure

```
tests/
├── conftest.py              # Shared pytest fixtures
├── test_api/                # API endpoint tests
│   └── test_products.py     # Products API tests
├── test_services/           # Business logic tests
│   ├── test_conversion_service.py
│   └── test_cache_load.py
└── test_integration/        # Integration tests
    ├── test_connection.py
    ├── test_db_connection.py
    └── test_shopify_connection.py
```

## 🎯 Test Categories

### Unit Tests (`test_services/`)
Fast, isolated tests for business logic and services.
- No external dependencies
- Mock database calls
- Test single functions/methods

**Run with**: `pytest -m unit`

### API Tests (`test_api/`)
Tests for REST API endpoints.
- Test request/response handling
- Validate status codes and JSON structure
- Test error handling

**Run with**: `pytest -m api`

### Integration Tests (`test_integration/`)
Tests that verify integration with external services.
- Database connection tests
- External API tests (Shopify, MercadoLibre)
- Slower execution time

**Run with**: `pytest -m integration`

## 🚀 Running Tests

### Run All Tests
```bash
# From backend/ directory
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=app --cov-report=html
```

### Run Specific Categories
```bash
# Only unit tests (fast)
pytest -m unit

# Only integration tests
pytest -m integration

# Only API tests
pytest -m api

# Only database tests
pytest -m database
```

### Run Specific Test Files
```bash
# Single test file
pytest tests/test_api/test_products.py

# Single test function
pytest tests/test_api/test_products.py::test_get_products

# All tests in a directory
pytest tests/test_services/
```

## 📝 Shared Fixtures (conftest.py)

Available fixtures for all tests:

### `database_url`
```python
def test_something(database_url):
    # Get database URL
    assert database_url.startswith("postgresql://")
```

### `db_connection`
```python
def test_with_db(db_connection):
    # Get fresh database connection
    cursor = db_connection.cursor()
    cursor.execute("SELECT 1")
    # Connection auto-closes after test
```

### `db_cursor`
```python
def test_with_cursor(db_cursor):
    # Get RealDictCursor (returns dicts)
    db_cursor.execute("SELECT * FROM products LIMIT 1")
    result = db_cursor.fetchone()
    # result is a dictionary
```

### `sample_product_data`
```python
def test_product_creation(sample_product_data):
    # Get sample product data for testing
    assert sample_product_data["sku"] == "BAKC_U04010"
```

### `sample_order_data`
```python
def test_order_creation(sample_order_data):
    # Get sample order data for testing
    assert sample_order_data["status"] == "completed"
```

## ✍️ Writing New Tests

### Test File Naming
- Files must start with `test_`
- Example: `test_order_service.py`

### Test Function Naming
- Functions must start with `test_`
- Use descriptive names
- Example: `test_create_order_with_valid_data()`

### Test Class Naming
- Classes must start with `Test`
- Example: `class TestOrderService:`

### Example Test Structure
```python
"""
Tests for Order Service
"""
import pytest
from app.services.order_service import OrderService

@pytest.mark.unit
def test_calculate_total():
    """Test order total calculation"""
    service = OrderService()
    total = service.calculate_total(items=[...])
    assert total == 15000

@pytest.mark.integration
@pytest.mark.database
def test_fetch_orders(db_connection):
    """Test fetching orders from database"""
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    assert count > 0
```

## 🏷️ Test Markers

Mark your tests with appropriate markers:

```python
@pytest.mark.unit          # Fast, isolated tests
@pytest.mark.integration   # Tests with external services
@pytest.mark.api           # API endpoint tests
@pytest.mark.database      # Tests requiring database
@pytest.mark.slow          # Tests taking >1 second
@pytest.mark.external      # Tests calling external APIs
```

## 🔧 Test Configuration

Configuration is in `pytest.ini` (backend root directory):
- Test discovery patterns
- Output options
- Available markers
- Coverage settings

## 📊 Coverage Reports

Generate coverage reports to see what code is tested:

```bash
# Generate HTML report
pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🐛 Debugging Failed Tests

### Show full error output
```bash
pytest --tb=long
```

### Stop at first failure
```bash
pytest -x
```

### Run last failed tests
```bash
pytest --lf
```

### Show print statements
```bash
pytest -s
```

### Debug with pdb
```bash
pytest --pdb
```

## ✅ Best Practices

1. **Test Independence**: Each test should be independent
2. **Clear Names**: Use descriptive test function names
3. **One Assertion**: Prefer one logical assertion per test
4. **Fast Tests**: Keep unit tests fast (<100ms)
5. **Use Fixtures**: Reuse common setup with fixtures
6. **Mark Tests**: Always use appropriate markers
7. **Clean Up**: Tests should clean up after themselves
8. **Mock External**: Mock external API calls in unit tests

## 🚨 Common Issues

### Tests not discovered
- Check file/function names start with `test_`
- Ensure `__init__.py` exists in test directories
- Verify `testpaths` in pytest.ini

### Database connection errors
- Check `DATABASE_URL` environment variable
- Ensure database is running
- Tests may be skipped if DATABASE_URL not set

### Import errors
- Run tests from `backend/` directory
- Check that `app/` is in Python path
- Ensure virtual environment is activated

## 📚 Additional Resources

- Pytest documentation: https://docs.pytest.org/
- Coverage.py docs: https://coverage.readthedocs.io/
- Testing best practices: See `../README.md`

---

**Note**: All tests should pass before deploying to production. Run the full test suite with `pytest` before committing changes.
