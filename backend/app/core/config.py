"""
Configuración centralizada de la aplicación
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Configuración de la aplicación"""

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

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()