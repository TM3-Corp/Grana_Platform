# Dockerfile para Grana Platform Backend
FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY backend/requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY backend/app ./app

# Exponer puerto
EXPOSE 8000

# Comando de inicio (usa $PORT de Railway, default 8000)
# Temporalmente usando main_simple para diagnosticar
CMD uvicorn app.main_simple:app --host 0.0.0.0 --port ${PORT:-8000}
