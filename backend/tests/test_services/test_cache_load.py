#!/usr/bin/env python3
import json
import os

CACHE_DIR = "/home/javier/Proyectos/Grana/grana-integration/validacion_2025_corregido/cache"
SHOPIFY_CACHE = f"{CACHE_DIR}/shopify_2025_corregido.json"
ML_CACHE = f"{CACHE_DIR}/mercadolibre_2025_corregido.json"

print("Testing cache file loading...")
print("="*70)

# Test Shopify cache
print("\n📦 Loading Shopify cache...")
print(f"File: {SHOPIFY_CACHE}")
print(f"Exists: {os.path.exists(SHOPIFY_CACHE)}")
print(f"Size: {os.path.getsize(SHOPIFY_CACHE) / 1024 / 1024:.2f} MB")

with open(SHOPIFY_CACHE, 'r') as f:
    shopify_orders = json.load(f)
print(f"✅ Loaded {len(shopify_orders)} Shopify orders")
print(f"First order date: {shopify_orders[0].get('created_at', 'N/A')[:10]}")
print(f"Last order date: {shopify_orders[-1].get('created_at', 'N/A')[:10]}")

# Filter to 2025
shopify_2025 = [o for o in shopify_orders if o.get('created_at', '').startswith('2025')]
print(f"2025 orders: {len(shopify_2025)}")

# Test ML cache
print("\n📦 Loading MercadoLibre cache...")
print(f"File: {ML_CACHE}")
print(f"Exists: {os.path.exists(ML_CACHE)}")
print(f"Size: {os.path.getsize(ML_CACHE) / 1024:.2f} KB")

with open(ML_CACHE, 'r') as f:
    ml_orders = json.load(f)
print(f"✅ Loaded {len(ml_orders)} ML orders")
print(f"First order date: {ml_orders[0].get('date_created', 'N/A')[:10]}")
print(f"Last order date: {ml_orders[-1].get('date_created', 'N/A')[:10]}")

# Filter to 2025
ml_2025 = [o for o in ml_orders if o.get('date_created', '').startswith('2025')]
print(f"2025 orders: {len(ml_2025)}")

print("\n✅ Cache files loaded successfully!")
