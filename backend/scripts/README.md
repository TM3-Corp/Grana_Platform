# 🔧 Scripts - Grana Platform Backend

Utility scripts for operational tasks, data management, and debugging.

## 📁 Script Organization

```
scripts/
├── data_loading/         # One-time data imports
├── sync/                 # Regular sync operations
└── debug/                # Debug & inspection tools
```

## 📥 Data Loading Scripts

**Purpose**: One-time bulk imports and initial data loading

### `load_shopify_bulk.py`
Bulk load Shopify products and orders into database.

```bash
python scripts/data_loading/load_shopify_bulk.py
```

**Use cases**:
- Initial database population
- Migrating historical data
- Full data refresh

### `load_ml_bulk.py`
Bulk load MercadoLibre products and orders.

```bash
python scripts/data_loading/load_ml_bulk.py
```

**Use cases**:
- Import MercadoLibre catalog
- Load historical ML orders
- One-time ML data migration

### `load_csv_orders.py`
Import orders from CSV files (manual exports).

```bash
python scripts/data_loading/load_csv_orders.py --file path/to/orders.csv
```

**Use cases**:
- Import manually exported data
- Load historical CSV exports
- Recover data from backups

### `import_historical_data.py`
Import historical data from multiple sources.

```bash
python scripts/data_loading/import_historical_data.py
```

**Use cases**:
- Complete historical data import
- Multi-source data migration
- Initial system setup

### `populate_product_variants.py` ✨ NEW
Populate `product_variants` table from official catalog.

```bash
python scripts/data_loading/populate_product_variants.py [--dry-run]
```

**Use cases**:
- Create packaging variant relationships (1un → 5un, 16un)
- Link display packages to individual units
- Populate consolidated inventory data

**What it does**:
- Groups products by base_code (BAKC, GRAL, etc.)
- Identifies base products (1 unit) and their variants
- Creates `product_variants` entries with quantity multipliers
- Enables consolidated inventory views

**Example**: Links BAKC_U04010 (1 unit) to BAKC_U20010 (5 units) and BAKC_U64010 (16 units)

### `populate_channel_equivalents.py` ✨ NEW
Populate `channel_equivalents` table with Shopify ↔ MercadoLibre mappings.

```bash
python scripts/data_loading/populate_channel_equivalents.py [--dry-run]
```

**Use cases**:
- Create cross-channel product mappings
- Link equivalent products between Shopify and MercadoLibre
- Enable consolidated cross-channel analytics

**What it does**:
- Maps MercadoLibre SKUs to Shopify SKUs
- Creates `channel_equivalents` entries with confidence scores
- All mappings are marked as `verified=true` (manual mappings)
- Enables cross-channel inventory and sales analysis

**Example**: Maps ML-MLC2929973548 (MercadoLibre) to BAKC_U64010 (Shopify)

## 🔄 Sync Scripts

**Purpose**: Regular synchronization operations (can be scheduled with cron)

### `sync_shopify_data.py`
Sync latest Shopify products and orders.

```bash
python scripts/sync/sync_shopify_data.py
```

**Use cases**:
- Daily product updates
- Hourly order syncing
- Keeping database current

**Recommended schedule**: Every 15-30 minutes

### `sync_mercadolibre_data.py`
Sync latest MercadoLibre products and orders.

```bash
python scripts/sync/sync_mercadolibre_data.py
```

**Use cases**:
- Regular ML catalog updates
- Order synchronization
- Stock level updates

**Recommended schedule**: Every 30-60 minutes

### `resync_orders_metadata.py`
Re-sync order metadata and update calculated fields.

```bash
python scripts/sync/resync_orders_metadata.py
```

**Use cases**:
- Fix missing metadata
- Recalculate order totals
- Update denormalized fields

**Recommended schedule**: Daily at night

### `refresh_materialized_views.py`
Refresh database materialized views (for analytics).

```bash
python scripts/sync/refresh_materialized_views.py
```

**Use cases**:
- Update analytics views
- Refresh dashboard data
- Maintain query performance

**Recommended schedule**: Every hour or after bulk imports

## 🐛 Debug Scripts

**Purpose**: Inspection, debugging, and data verification

### `check_current_data.py`
Display current database statistics and health check.

```bash
python scripts/debug/check_current_data.py
```

**Shows**:
- Total products count
- Total orders count
- Latest orders
- Data quality metrics

### `inspect_order.py`
Detailed inspection of a specific order.

```bash
python scripts/debug/inspect_order.py --order-id 12345
```

**Shows**:
- Order details
- Line items
- Customer information
- Payment status
- Fulfillment status

### `verify_product_mapping.py`
Verify product mapping and SKU consistency.

```bash
python scripts/debug/verify_product_mapping.py
```

**Checks**:
- SKU format validation
- Product variant relationships
- Cross-channel equivalents
- Mapping confidence scores

### `test_api_connections.py`
Test all external API connections.

```bash
python scripts/debug/test_api_connections.py
```

**Tests**:
- Shopify API connection
- MercadoLibre API connection
- Supabase connection
- Database connectivity

### `analyze_data_quality.py`
Comprehensive data quality analysis.

```bash
python scripts/debug/analyze_data_quality.py
```

**Reports**:
- Missing data fields
- Duplicate records
- Data inconsistencies
- Validation errors

## 🚀 Running Scripts

### Prerequisites

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Set environment variables**
   ```bash
   export DATABASE_URL="postgresql://..."
   export SHOPIFY_PASSWORD="shpat_..."
   # Or use .env file
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Execution from Backend Root

All scripts should be run from the `backend/` directory:

```bash
# Correct ✅
cd /path/to/Grana_Platform/backend
python scripts/data_loading/load_shopify_bulk.py

# Wrong ❌
cd scripts/data_loading
python load_shopify_bulk.py  # Import errors!
```

## ⏰ Scheduling with Cron

Example crontab for automated syncing:

```bash
# Edit crontab
crontab -e

# Add these lines:

# Sync Shopify every 15 minutes
*/15 * * * * cd /path/to/backend && /path/to/venv/bin/python scripts/sync/sync_shopify_data.py

# Sync MercadoLibre every 30 minutes
*/30 * * * * cd /path/to/backend && /path/to/venv/bin/python scripts/sync/sync_mercadolibre_data.py

# Refresh analytics daily at 2 AM
0 2 * * * cd /path/to/backend && /path/to/venv/bin/python scripts/sync/refresh_materialized_views.py

# Data quality check daily at 3 AM
0 3 * * * cd /path/to/backend && /path/to/venv/bin/python scripts/debug/analyze_data_quality.py
```

## 📝 Script Logging

Most scripts log to stdout. Redirect to files for cron jobs:

```bash
python scripts/sync/sync_shopify_data.py >> logs/shopify_sync.log 2>&1
```

Create logs directory:
```bash
mkdir -p logs/
```

## 🔐 Security Considerations

1. **Never commit credentials**: Use `.env` file (git-ignored)
2. **Limit API permissions**: Use read-only tokens when possible
3. **Rate limiting**: Respect API rate limits
4. **Backup before bulk operations**: Always backup database first

## 🛠️ Creating New Scripts

### Template for Data Loading Script

```python
#!/usr/bin/env python3
"""
Description of what this script does
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

load_dotenv()

from app.core.database import get_db_connection

def main():
    """Main execution function"""
    print("Starting data load...")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Your logic here
        cursor.execute("...")
        conn.commit()
        print("✅ Data loaded successfully")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
```

### Best Practices

1. **Add docstrings**: Explain what the script does
2. **Handle errors**: Use try/except blocks
3. **Log progress**: Print status messages
4. **Use transactions**: Commit or rollback properly
5. **Close connections**: Always close database connections
6. **Make idempotent**: Script should be safe to run multiple times
7. **Add dry-run mode**: Allow testing without changes

## 📊 Monitoring Script Execution

### Check last sync status
```bash
# View recent log entries
tail -100 logs/shopify_sync.log

# Check for errors
grep "ERROR" logs/*.log
```

### Monitor cron jobs
```bash
# Check cron logs (Ubuntu/Debian)
grep CRON /var/log/syslog

# Check cron logs (CentOS/RHEL)
grep CRON /var/log/cron
```

## 🚨 Troubleshooting

### Import errors
```bash
# Ensure running from backend/ directory
pwd  # Should show .../backend

# Check Python path
python -c "import sys; print(sys.path)"
```

### Database connection errors
```bash
# Test database connection
python scripts/debug/test_api_connections.py

# Check environment variables
echo $DATABASE_URL
```

### API errors
```bash
# Check API credentials
python scripts/debug/test_api_connections.py

# Verify .env file exists
cat .env | grep -E "SHOPIFY|MERCADOLIBRE"
```

## 📚 Additional Resources

- Main README: `../README.md`
- API Documentation: `../app/api/README.md`
- Database Schema: `../migrations/README.md`

---

**Note**: Scripts in `data_loading/` are typically one-time use. Scripts in `sync/` should be scheduled regularly. Scripts in `debug/` are for manual inspection and troubleshooting.
