# MercadoLibre Stock Sync

Automated stock synchronization from MercadoLibre API to the warehouse inventory system.

## 📋 Overview

This system automatically fetches product stock data from MercadoLibre every hour and updates the `warehouse_stock` table in Supabase.

**Features:**
- ✅ Hourly automatic sync via GitHub Actions
- ✅ Manual sync capability
- ✅ Token refresh automation
- ✅ Error notifications
- ✅ Logging and monitoring

---

## 🚀 Quick Start

### Prerequisites

1. **MercadoLibre API Credentials**
   - `ML_APP_ID` - Your ML app ID
   - `ML_SECRET` - Your ML secret key
   - `ML_ACCESS_TOKEN` - OAuth access token (expires every 6 hours)
   - `ML_REFRESH_TOKEN` - OAuth refresh token (expires every 6 months)
   - `ML_SELLER_ID` - Your seller ID

2. **Database**
   - Supabase PostgreSQL with `warehouses` and `warehouse_stock` tables

### Setup GitHub Actions

1. **Add GitHub Secrets** (Settings → Secrets and variables → Actions):
   ```
   ML_ACCESS_TOKEN=APP_USR-...
   ML_REFRESH_TOKEN=TG-...
   ML_SELLER_ID=2506482242
   DATABASE_URL=postgresql://...
   ```

2. **Enable workflow**:
   - The workflow file is already at `.github/workflows/sync-mercadolibre-stock.yml`
   - It runs automatically every hour
   - You can also trigger it manually from Actions tab

---

## 🔧 Manual Usage

### Run Sync Manually

```bash
cd backend

# Install dependencies
pip install httpx psycopg2-binary python-dotenv

# Run sync
python scripts/sync/sync_mercadolibre_stock.py
```

### Refresh Access Token

Access tokens expire every 6 hours. When you see `401 Unauthorized` errors:

```bash
cd backend

# Refresh token
python scripts/sync/refresh_ml_token.py

# Copy the output and update:
# 1. backend/.env file
# 2. GitHub Secrets (ML_ACCESS_TOKEN and ML_REFRESH_TOKEN)
```

---

## 📊 Monitoring

### Check Sync Status

**GitHub Actions:**
- Go to: `https://github.com/YOUR_USERNAME/YOUR_REPO/actions`
- Click on "Sync MercadoLibre Stock" workflow
- View recent runs and logs

**Database:**
```sql
-- Check last update timestamp
SELECT
    w.name,
    ws.last_updated,
    ws.updated_by,
    COUNT(*) as products_with_stock
FROM warehouse_stock ws
JOIN warehouses w ON w.id = ws.warehouse_id
WHERE w.code = 'mercadolibre'
GROUP BY w.name, ws.last_updated, ws.updated_by
ORDER BY ws.last_updated DESC
LIMIT 1;
```

**Frontend:**
- Navigate to: `http://localhost:3000/dashboard/warehouse-inventory/by-warehouse`
- Select "Mercado Libre" warehouse
- Check "Última Actualización" card

---

## 📁 Files

| File | Purpose |
|------|---------|
| `sync_mercadolibre_stock.py` | Main sync script |
| `refresh_ml_token.py` | Token refresh utility |
| `.github/workflows/sync-mercadolibre-stock.yml` | GitHub Actions workflow |
| `README_MERCADOLIBRE.md` | This file |

---

## 🔍 How It Works

1. **Fetch Active Items** - Gets list of all active listings from ML API
2. **Get User Product IDs** - Extracts user_product_id from each item
3. **Fetch Stock Data** - Calls `/user-products/{id}/stock` endpoint
4. **Calculate Total Stock** - Sums stock across all locations (selling_address + meli_facility)
5. **Update Database** - Upserts to `warehouse_stock` table

### Stock Location Types

MercadoLibre returns stock in multiple locations:

```json
{
  "locations": [
    {
      "type": "selling_address",  // Your warehouse (can update via API)
      "quantity": 17
    },
    {
      "type": "meli_facility",    // ML Fulfillment (managed by ML)
      "quantity": 3
    }
  ]
}
```

We store the **total stock** (sum of all locations) in our database.

---

## ⚠️ Troubleshooting

### Sync Fails with 401 Unauthorized

**Problem:** Access token expired (they expire every 6 hours)

**Solution:**
```bash
python scripts/sync/refresh_ml_token.py
# Update GitHub Secrets with new tokens
```

### Products Not Found in Database

**Problem:** Products from ML are not in the `products` table

**Solution:**
1. Check if product exists with:
   ```sql
   SELECT * FROM products
   WHERE external_id = 'MLC1234567890'
   AND source = 'mercadolibre';
   ```

2. If missing, import the product first using the ML sync service

### GitHub Action Not Running

**Problem:** Workflow not executing on schedule

**Possible causes:**
- Repository is private and on free plan (limited minutes)
- Workflow file has syntax errors
- GitHub Actions are disabled for the repo

**Solution:**
- Check Actions tab for errors
- Manually trigger the workflow to test
- Verify `.github/workflows/sync-mercadolibre-stock.yml` syntax

---

## 📝 Token Expiration Timeline

| Token | Expires | Refresh Method |
|-------|---------|----------------|
| Access Token | 6 hours | Use `refresh_ml_token.py` |
| Refresh Token | 6 months | Manual OAuth flow |

**Important:** Set a calendar reminder to refresh the refresh token before it expires!

---

## 🔐 Security Notes

- ❌ **Never commit tokens** to git
- ✅ Use GitHub Secrets for credentials
- ✅ Use `.env` files for local development
- ✅ Rotate tokens regularly
- ✅ Monitor API usage for anomalies

---

## 📞 Support

**ML API Documentation:**
- https://developers.mercadolibre.cl
- https://developers.mercadolibre.com.ar/es_ar/api-docs-es

**Stock API Docs:**
- https://developers.mercadolibre.com.ar/es_ar/stock-distribuido

**Issues:**
- Check GitHub Actions logs
- Review Supabase database logs
- Check ML API status: https://status.mercadolibre.com

---

**Last Updated:** November 14, 2025
**Author:** TM3
**Status:** ✅ Production Ready
