"""
Configuración centralizada de la aplicación
"""
from pydantic_settings import BaseSettings
from typing import List


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

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://yourdomain.com",
    ]

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