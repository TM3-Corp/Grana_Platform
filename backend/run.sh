#!/bin/bash
# Script para levantar el backend de manera simple

# Unset system DATABASE_URL to ensure we use the Session Pooler from .env
# WSL2 only supports IPv4, so we must use Session Pooler, not direct connection
unset DATABASE_URL

source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
