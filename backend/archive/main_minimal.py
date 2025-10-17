"""
Minimal FastAPI app - no dependencies, no database, nothing
"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "alive", "message": "Minimal app working"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/v1/debug")
def debug():
    import os
    return {
        "PORT": os.getenv("PORT", "not set"),
        "DATABASE_URL_exists": bool(os.getenv("DATABASE_URL")),
        "message": "If you see this, the app is working"
    }
