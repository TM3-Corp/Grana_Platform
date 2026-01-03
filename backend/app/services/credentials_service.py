"""
Credentials Service - Manages external API tokens with database persistence

This service provides a centralized way to manage OAuth tokens for external services
like MercadoLibre. Tokens are stored in the database so they survive container restarts.

Features:
- Read tokens from database (with env var fallback for initial setup)
- Update tokens after refresh
- Track token expiration
- Automatic migration from env vars to database on first run

Author: Claude Code
Date: 2026-01-03
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class CredentialsService:
    """Service for managing external API credentials with database persistence"""

    def __init__(self, database_url: str = None):
        """
        Initialize credentials service

        Args:
            database_url: PostgreSQL connection string. If not provided, reads from DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")

    def _get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

    def get_mercadolibre_credentials(self) -> Dict[str, Any]:
        """
        Get MercadoLibre API credentials

        Returns credentials from database if available, otherwise falls back to env vars.
        On fallback, automatically stores env var tokens in database for future use.

        Returns:
            Dict with keys: app_id, secret, access_token, refresh_token, seller_id, expires_at
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT access_token, refresh_token, token_expires_at, additional_data
                FROM api_credentials
                WHERE service_name = 'mercadolibre'
            """)
            row = cur.fetchone()
            cur.close()
            conn.close()

            # Get static credentials from env (always needed for refresh)
            app_id = os.getenv('ML_APP_ID') or os.getenv('MERCADOLIBRE_APP_ID')
            secret = os.getenv('ML_SECRET') or os.getenv('MERCADOLIBRE_SECRET')
            seller_id = os.getenv('ML_SELLER_ID') or os.getenv('MERCADOLIBRE_SELLER_ID')

            if row and row['access_token']:
                # Use database tokens
                logger.debug("Using MercadoLibre tokens from database")
                return {
                    'app_id': app_id,
                    'secret': secret,
                    'seller_id': row['additional_data'].get('seller_id', seller_id),
                    'access_token': row['access_token'],
                    'refresh_token': row['refresh_token'],
                    'expires_at': row['token_expires_at']
                }
            else:
                # Fallback to env vars and migrate to database
                logger.info("No ML tokens in database, falling back to environment variables")
                env_access_token = os.getenv('ML_ACCESS_TOKEN') or os.getenv('MERCADOLIBRE_ACCESS_TOKEN')
                env_refresh_token = os.getenv('ML_REFRESH_TOKEN') or os.getenv('MERCADOLIBRE_REFRESH_TOKEN')

                if env_access_token:
                    # Store in database for future use
                    self.update_mercadolibre_tokens(
                        access_token=env_access_token,
                        refresh_token=env_refresh_token,
                        expires_in_seconds=21600  # Default 6 hours, will be updated on first refresh
                    )
                    logger.info("Migrated ML tokens from env vars to database")

                return {
                    'app_id': app_id,
                    'secret': secret,
                    'seller_id': seller_id,
                    'access_token': env_access_token,
                    'refresh_token': env_refresh_token,
                    'expires_at': None
                }

        except Exception as e:
            logger.error(f"Error fetching ML credentials from database: {e}")
            # Fallback to env vars on any error
            return {
                'app_id': os.getenv('ML_APP_ID') or os.getenv('MERCADOLIBRE_APP_ID'),
                'secret': os.getenv('ML_SECRET') or os.getenv('MERCADOLIBRE_SECRET'),
                'seller_id': os.getenv('ML_SELLER_ID') or os.getenv('MERCADOLIBRE_SELLER_ID'),
                'access_token': os.getenv('ML_ACCESS_TOKEN') or os.getenv('MERCADOLIBRE_ACCESS_TOKEN'),
                'refresh_token': os.getenv('ML_REFRESH_TOKEN') or os.getenv('MERCADOLIBRE_REFRESH_TOKEN'),
                'expires_at': None
            }

    def update_mercadolibre_tokens(
        self,
        access_token: str,
        refresh_token: str = None,
        expires_in_seconds: int = 21600
    ) -> bool:
        """
        Update MercadoLibre tokens in database

        Called after a successful token refresh to persist the new tokens.

        Args:
            access_token: New access token from ML API
            refresh_token: New refresh token (optional, sometimes ML returns the same one)
            expires_in_seconds: Token lifetime in seconds (default 6 hours = 21600)

        Returns:
            True if update successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)

            cur.execute("""
                UPDATE api_credentials
                SET
                    access_token = %s,
                    refresh_token = COALESCE(%s, refresh_token),
                    token_expires_at = %s,
                    updated_at = NOW()
                WHERE service_name = 'mercadolibre'
            """, (access_token, refresh_token, expires_at))

            if cur.rowcount == 0:
                # Row doesn't exist, insert it
                cur.execute("""
                    INSERT INTO api_credentials (service_name, access_token, refresh_token, token_expires_at, additional_data)
                    VALUES ('mercadolibre', %s, %s, %s, %s)
                """, (access_token, refresh_token, expires_at,
                      f'{{"seller_id": "{os.getenv("ML_SELLER_ID", "")}"}}'))

            conn.commit()
            cur.close()
            conn.close()

            logger.info(f"ML tokens updated in database, expires at {expires_at}")
            return True

        except Exception as e:
            logger.error(f"Error updating ML tokens in database: {e}")
            return False

    def is_token_expired(self, service_name: str = 'mercadolibre') -> bool:
        """
        Check if the token for a service is expired or about to expire

        Returns True if token expires within 5 minutes (to allow preemptive refresh)

        Args:
            service_name: Service to check (default: mercadolibre)

        Returns:
            True if token is expired or expires within 5 minutes
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT token_expires_at
                FROM api_credentials
                WHERE service_name = %s
            """, (service_name,))

            row = cur.fetchone()
            cur.close()
            conn.close()

            if not row or not row['token_expires_at']:
                return True  # No expiration info = assume expired

            # Check if expires within 5 minutes
            buffer_time = timedelta(minutes=5)
            return row['token_expires_at'] <= datetime.now(timezone.utc) + buffer_time

        except Exception as e:
            logger.error(f"Error checking token expiration: {e}")
            return True  # Assume expired on error

    def get_credentials_status(self) -> Dict[str, Any]:
        """
        Get status of all stored credentials

        Returns:
            Dict with service statuses including expiration info
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    service_name,
                    CASE WHEN access_token IS NOT NULL THEN TRUE ELSE FALSE END as has_token,
                    token_expires_at,
                    updated_at,
                    additional_data
                FROM api_credentials
            """)

            results = {}
            for row in cur.fetchall():
                expires_at = row['token_expires_at']
                is_expired = expires_at and expires_at <= datetime.now(timezone.utc) if expires_at else None

                results[row['service_name']] = {
                    'has_token': row['has_token'],
                    'expires_at': expires_at.isoformat() if expires_at else None,
                    'is_expired': is_expired,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                    'additional_data': row['additional_data']
                }

            cur.close()
            conn.close()

            return results

        except Exception as e:
            logger.error(f"Error getting credentials status: {e}")
            return {}


# Singleton instance for easy import
_credentials_service: Optional[CredentialsService] = None

def get_credentials_service() -> CredentialsService:
    """Get the singleton credentials service instance"""
    global _credentials_service
    if _credentials_service is None:
        _credentials_service = CredentialsService()
    return _credentials_service
