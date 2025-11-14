#!/usr/bin/env python3
"""
Refresh MercadoLibre Access Token
Tokens expire every 6 hours and must be refreshed using the refresh token

Usage:
    python refresh_ml_token.py

Output:
    Prints new ML_ACCESS_TOKEN and ML_REFRESH_TOKEN values
    Update these in your .env files and GitHub Secrets

Author: TM3
Date: 2025-11-14
"""
import os
import httpx
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

ML_APP_ID = os.getenv('ML_APP_ID')
ML_SECRET = os.getenv('ML_SECRET')
ML_REFRESH_TOKEN = os.getenv('ML_REFRESH_TOKEN')

logger.info("=" * 80)
logger.info("MERCADOLIBRE TOKEN REFRESH")
logger.info("=" * 80)

if not all([ML_APP_ID, ML_SECRET, ML_REFRESH_TOKEN]):
    logger.error("❌ Missing environment variables!")
    logger.error(f"ML_APP_ID: {'✓' if ML_APP_ID else '✗'}")
    logger.error(f"ML_SECRET: {'✓' if ML_SECRET else '✗'}")
    logger.error(f"ML_REFRESH_TOKEN: {'✓' if ML_REFRESH_TOKEN else '✗'}")
    exit(1)

logger.info(f"App ID: {ML_APP_ID}")
logger.info(f"Refresh Token: {ML_REFRESH_TOKEN[:20]}...")
logger.info("")

url = "https://api.mercadolibre.com/oauth/token"
data = {
    'grant_type': 'refresh_token',
    'client_id': ML_APP_ID,
    'client_secret': ML_SECRET,
    'refresh_token': ML_REFRESH_TOKEN
}

try:
    response = httpx.post(url, data=data, timeout=30.0)
    response.raise_for_status()

    token_data = response.json()

    logger.info("✅ TOKEN REFRESHED SUCCESSFULLY!")
    logger.info("")
    logger.info("=" * 80)
    logger.info("NEW CREDENTIALS - UPDATE YOUR .ENV FILES AND GITHUB SECRETS")
    logger.info("=" * 80)
    logger.info(f"ML_ACCESS_TOKEN={token_data['access_token']}")
    logger.info(f"ML_REFRESH_TOKEN={token_data.get('refresh_token', ML_REFRESH_TOKEN)}")
    logger.info("=" * 80)
    logger.info("")
    logger.info("📝 To update GitHub Secrets:")
    logger.info("   1. Go to: https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions")
    logger.info("   2. Update ML_ACCESS_TOKEN secret")
    logger.info("   3. Update ML_REFRESH_TOKEN secret (if changed)")
    logger.info("")
    logger.info("📝 To update .env files:")
    logger.info("   - Update backend/.env")
    logger.info("   - Update grana-integration/.env (if exists)")

except httpx.HTTPStatusError as e:
    logger.error(f"❌ HTTP Error: {e.response.status_code}")
    logger.error(f"Response: {e.response.text}")
    exit(1)
except Exception as e:
    logger.error(f"❌ Error: {e}")
    exit(1)
