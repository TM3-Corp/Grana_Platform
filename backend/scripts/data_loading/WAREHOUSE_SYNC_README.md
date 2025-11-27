## 📦 Warehouse Inventory Sync from Relbase

Automated sync of warehouse inventory data from Relbase API to Supabase.

### 🎯 Strategy: Download → Upload (Data Lake Approach)

This process uses a **2-step data lake strategy**:

1. **DOWNLOAD**: Fetch all data from Relbase → Save as JSON files (data lake)
2. **UPLOAD**: Read JSON files → Populate Supabase

**Benefits:**
- ✅ Inspect raw data before loading
- ✅ No need to re-fetch if upload fails
- ✅ JSON files serve as backup/snapshot
- ✅ Can process data incrementally

---

## 🗂️ What Gets Synced

| Relbase API | Data | Supabase Table |
|-------------|------|----------------|
| `GET /api/v1/bodegas` | 13 warehouses | `warehouses` |
| `GET /api/v1/productos/{id}/lotes_series/{warehouse_id}` | Stock with lots | `warehouse_stock` |

**Key Features:**
- **Lot Tracking**: Each stock entry includes `lot_number` and `expiration_date`
- **External ID Mapping**: `warehouses.external_id` = Relbase warehouse_id
- **Multi-Source Support**: `source` column tracks data origin ('relbase', 'manual', etc.)

---

## 📋 Prerequisites

1. **Migration 016 executed** ✅ (already done)
   - Adds `external_id` to warehouses
   - Adds `lot_number` and `expiration_date` to warehouse_stock
   - Modifies UNIQUE constraint

2. **Products with external_id** (Relbase products must be in database)
   - Script will only sync products that have `external_id` set
   - Use existing product enrichment scripts if needed

3. **Relbase API credentials** in `.env`:
   ```env
   RELBASE_COMPANY_TOKEN=8iNGjKSPBJQ7R2su4ZtftBsP
   RELBASE_USER_TOKEN=3dk4TybsDQwiCH39AvnSHiEi
   ```

---

## 🚀 Step 1: Download Data from Relbase (Data Lake)

**Script:** `download_warehouse_inventory_from_relbase.py`

```bash
cd /home/javier/Proyectos/Grana/Grana_Platform/backend
source venv/bin/activate

# Download all data and save to JSON
python3 scripts/data_loading/download_warehouse_inventory_from_relbase.py --verbose
```

**What it does:**
1. Fetches warehouses from `GET /api/v1/bodegas`
2. Fetches products from `GET /api/v1/productos` (optional)
3. For each product × warehouse combination:
   - Fetches lots from `GET /api/v1/productos/{product_id}/lotes_series/{warehouse_id}`
   - Saves to master JSON file

**Output files** (in `/tmp/relbase_data_lake/`):
```
/tmp/relbase_data_lake/
├── warehouses.json                 # All warehouses from Relbase
├── products_from_api.json          # All products from Relbase API
├── warehouse_stock_lots.json       # All stock records with lots
└── download_summary.json           # Download statistics
```

**Time:** ~12-15 minutes (for ~400 products × 13 warehouses = ~5,200 API calls)

**Options:**
```bash
# Custom output directory
python3 scripts/data_loading/download_warehouse_inventory_from_relbase.py \
    --output-dir /path/to/my/data \
    --verbose

# Skip downloading products (we already have them)
python3 scripts/data_loading/download_warehouse_inventory_from_relbase.py \
    --skip-products \
    --verbose
```

---

## ⬆️ Step 2: Upload Data to Supabase

**Script:** `upload_warehouse_inventory_to_supabase.py`

```bash
# Dry run first (recommended)
python3 scripts/data_loading/upload_warehouse_inventory_to_supabase.py --dry-run --verbose

# Real upload
python3 scripts/data_loading/upload_warehouse_inventory_to_supabase.py --verbose
```

**What it does:**
1. Reads JSON files from data lake
2. Uploads warehouses to `warehouses` table (with `external_id`)
3. Uploads stock records to `warehouse_stock` table (with `lot_number` and `expiration_date`)

**Time:** ~1-2 minutes (database inserts)

**Options:**
```bash
# Custom data directory
python3 scripts/data_loading/upload_warehouse_inventory_to_supabase.py \
    --data-dir /path/to/my/data \
    --verbose

# Dry run to see what would happen
python3 scripts/data_loading/upload_warehouse_inventory_to_supabase.py --dry-run --verbose
```

---

## 📊 Example Output

### Download Phase
```
================================================================================
🌊 RELBASE DATA LAKE DOWNLOAD
================================================================================

📁 Output directory: /tmp/relbase_data_lake

================================================================================
📍 PHASE 1: Download Warehouses
================================================================================
📦 Fetching warehouses from Relbase...
✅ Fetched 13 warehouses
💾 Saved 13 warehouses to: /tmp/relbase_data_lake/warehouses.json

================================================================================
🔍 PHASE 3: Download Warehouse Stock with Lots
================================================================================

🔍 Downloading 5200 combinations (400 products × 13 warehouses)
⏱️  Estimated time: ~14.7 minutes

[1/400] Product: BAKC_U04010 (external_id: 5054871)
   └─ Product 5054871 @ Warehouse 1855: 2 lots
   └─ Product 5054871 @ Warehouse 1991: 1 lot

💾 Saved 342 stock records (1,247 lots) to: /tmp/relbase_data_lake/warehouse_stock_lots.json

================================================================================
✅ DOWNLOAD COMPLETE - DATA LAKE READY
================================================================================

📊 Summary:
   • Warehouses: 13
   • Products (in DB): 400
   • Combinations checked: 5,200
   • Combinations with stock: 342
   • Total lots: 1,247
```

### Upload Phase
```
================================================================================
⬆️  UPLOAD WAREHOUSE INVENTORY TO SUPABASE
================================================================================

📊 Data loaded:
   • Warehouses: 13
   • Stock records: 342
   • Total lots: 1,247

================================================================================
📍 PHASE 1: Upload Warehouses
================================================================================
   + Created: AMPLIFICA SANTIAGO CENTRO (code: amplifica_santiago_centro, external_id: 1910)
   + Created: AMPLIFICA LA REINA (code: amplifica_la_reina, external_id: 2012)
   ...

📊 Warehouses: 13 created, 0 updated

================================================================================
📦 PHASE 2: Upload Warehouse Stock with Lots
================================================================================
   ✓ Lot 222: 30 units (exp: 2026-07-01)
   ✓ Lot 333: 16 units (exp: 2026-07-02)
   ...

📊 Stock: 1,247 lots inserted, 0 lots updated, 0 errors

================================================================================
✅ UPLOAD COMPLETE
================================================================================
```

---

## 🔍 Verification Queries

After upload, verify data:

```sql
-- Check warehouses with external_id
SELECT id, code, name, external_id, source
FROM warehouses
WHERE source = 'relbase'
ORDER BY name;

-- Check warehouse stock with lots
SELECT
    ws.id,
    p.sku,
    p.name as product_name,
    w.name as warehouse_name,
    ws.quantity,
    ws.lot_number,
    ws.expiration_date
FROM warehouse_stock ws
JOIN products p ON p.id = ws.product_id
JOIN warehouses w ON w.id = ws.warehouse_id
WHERE ws.lot_number IS NOT NULL
ORDER BY w.name, p.sku, ws.expiration_date
LIMIT 20;

-- Use the warehouse_stock_by_lot view
SELECT * FROM warehouse_stock_by_lot
WHERE expiration_status = 'Expiring Soon'
ORDER BY days_to_expiration
LIMIT 20;

-- Summary statistics
SELECT
    w.name as warehouse,
    COUNT(DISTINCT ws.product_id) as products,
    COUNT(*) as lots,
    SUM(ws.quantity) as total_units
FROM warehouse_stock ws
JOIN warehouses w ON w.id = ws.warehouse_id
WHERE ws.lot_number IS NOT NULL
GROUP BY w.name
ORDER BY total_units DESC;
```

---

## 🔄 Future Incremental Syncs

For future updates (once initial data is loaded):

1. **Modify download script** to fetch only active products from `product_catalog`:
   ```python
   # Instead of all products with external_id
   # Fetch only products in product_catalog (active SKUs)
   ```

2. **Clear old stock before re-sync**:
   ```sql
   -- Option A: Delete all stock from Relbase
   DELETE FROM warehouse_stock ws
   USING warehouses w
   WHERE ws.warehouse_id = w.id AND w.source = 'relbase';

   -- Option B: Delete per warehouse (incremental)
   DELETE FROM warehouse_stock
   WHERE warehouse_id = (
       SELECT id FROM warehouses WHERE external_id = '1855'
   );
   ```

3. **Schedule with cron** (future):
   ```bash
   # Daily at 2 AM
   0 2 * * * cd /path/to/backend && ./scripts/sync_warehouse_daily.sh
   ```

---

## ⚠️ Important Notes

1. **Rate Limiting**: Scripts respect Relbase API rate limit (~6 req/s)
2. **Products Must Exist**: Only syncs products that already have `external_id` in database
3. **Lot Uniqueness**: Same product can have multiple lots in same warehouse
4. **Data Lake**: JSON files are backup - don't delete them after upload
5. **Dry Run First**: Always test with `--dry-run` before real upload

---

## 📚 Related Files

| File | Purpose |
|------|---------|
| `migrations/016_add_lot_tracking_to_warehouse_stock.sql` | Database schema changes |
| `download_warehouse_inventory_from_relbase.py` | Step 1: Download from Relbase |
| `upload_warehouse_inventory_to_supabase.py` | Step 2: Upload to Supabase |
| `sync_warehouse_inventory_from_relbase.py` | Old direct sync (deprecated) |

---

## 🐛 Troubleshooting

### "Products not found in DB"
**Problem**: Products don't have `external_id` set.

**Solution**: Run product enrichment first:
```bash
python3 scripts/data_loading/enrich_products_from_orders.py
```

### "Warehouse not found in DB"
**Problem**: Warehouse external_id mismatch.

**Solution**: Check warehouses were created in Phase 1 of upload.

### "Network unreachable"
**Problem**: Using wrong DATABASE_URL (IPv6 instead of IPv4 pooler).

**Solution**: Ensure `.env` uses Transaction Pooler (port 6543).

---

**Last Updated**: 2025-11-18
**Author**: Claude Code
