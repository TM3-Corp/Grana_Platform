"""
Conexión a base de datos PostgreSQL (Supabase)
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client
from .config import settings

# SQLAlchemy Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verificar conexión antes de usar
    pool_size=10,  # Número de conexiones en el pool
    max_overflow=20,  # Conexiones extras si se necesitan
)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Supabase Client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_db():
    """
    Dependency para obtener sesión de DB
    Uso en FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_supabase():
    """
    Dependency para obtener cliente de Supabase
    Uso en FastAPI:
        @app.get("/data")
        def get_data(sb: Client = Depends(get_supabase)):
            ...
    """
    return supabase