"""
Configuración centralizada de la aplicación

Environment loading priority:
1. If APP_ENV=development → loads .env.development (local Supabase Docker)
2. If APP_ENV=production → loads .env.production (remote Supabase)
3. Default (no APP_ENV) → loads .env.development for safety

For local development, always use .env.development which points to
local Supabase Docker (127.0.0.1:54321/54322).
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional

# Get the absolute path to the backend directory
BACKEND_DIR = Path(__file__).parent.parent.parent  # app/core/config.py -> backend/

# Determine which env file to load based on APP_ENV
# Default to 'development' for safety (never touch production by accident)
APP_ENV = os.getenv("APP_ENV", "development")

if APP_ENV == "production":
    ENV_FILE_PATH = BACKEND_DIR / ".env.production"
    # Fallback to .env if .env.production doesn't exist
    if not ENV_FILE_PATH.exists():
        ENV_FILE_PATH = BACKEND_DIR / ".env"
else:
    # development or any other value defaults to development
    ENV_FILE_PATH = BACKEND_DIR / ".env.development"
    # Fallback to .env if .env.development doesn't exist
    if not ENV_FILE_PATH.exists():
        ENV_FILE_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    model_config = ConfigDict(
        env_file=str(ENV_FILE_PATH),  # Use environment-specific file
        case_sensitive=True,
        extra="ignore"  # Allow extra environment variables without error
    )

    # Environment
    APP_ENV: str = "development"

    # API Settings
    API_TITLE: str = "Grana API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API para sistema de integración Grana"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = True

    # Database
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Authentication
    AUTH_SECRET: str = ""  # Must match frontend NextAuth AUTH_SECRET

    # CORS - Can be string (comma-separated) or JSON array
    # Example: "http://localhost:3000,https://yourdomain.com" or '["http://localhost:3000"]'
    ALLOWED_ORIGINS: Optional[str] = "http://localhost:3000,http://localhost:3001"

    def get_allowed_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into list"""
        if not self.ALLOWED_ORIGINS:
            return ["http://localhost:3000"]

        # Try JSON parse first (for array format)
        import json
        try:
            origins = json.loads(self.ALLOWED_ORIGINS)
            if isinstance(origins, list):
                return origins
        except (json.JSONDecodeError, ValueError):
            pass

        # Fall back to comma-separated string
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # External APIs (opcional por ahora)
    SHOPIFY_PASSWORD: str = ""
    SHOPIFY_STORE_NAME: str = ""
    MERCADOLIBRE_CLIENT_ID: str = ""
    MERCADOLIBRE_CLIENT_SECRET: str = ""
    WALMART_CLIENT_ID: str = ""
    WALMART_CLIENT_SECRET: str = ""
    CENCOSUD_ACCESS_TOKEN: str = ""


settings = Settings()