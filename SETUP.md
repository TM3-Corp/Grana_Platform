# Guia de Instalacion - Grana Platform

Guia completa para configurar el entorno de desarrollo desde cero.

---

## Tabla de Contenidos

1. [Requisitos Previos](#1-requisitos-previos)
2. [Instalacion Paso a Paso](#2-instalacion-paso-a-paso)
3. [Configuracion de Credenciales](#3-configuracion-de-credenciales)
4. [Levantar el Proyecto](#4-levantar-el-proyecto)
5. [Verificar que Todo Funciona](#5-verificar-que-todo-funciona)
6. [Comandos del Dia a Dia](#6-comandos-del-dia-a-dia)
7. [Solucion de Problemas](#7-solucion-de-problemas)

---

## 1. Requisitos Previos

### Software Necesario

| Software | Version | Verificar | Instalar (macOS) |
|----------|---------|-----------|------------------|
| Python | 3.10+ | `python3 --version` | `brew install python@3.12` |
| Node.js | 18+ | `node --version` | `brew install node@20` |
| npm | 8+ | `npm --version` | (viene con Node.js) |
| Docker Desktop | Latest | `docker --version` | [Descargar](https://www.docker.com/products/docker-desktop/) |
| Git | 2.0+ | `git --version` | `brew install git` |

### Instalacion de Homebrew (macOS)

Si no tienes Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Windows (WSL2)

```bash
# En PowerShell como Admin
wsl --install

# En WSL2 Ubuntu
sudo apt update
sudo apt install python3 python3-venv python3-pip nodejs npm docker.io
```

---

## 2. Instalacion Paso a Paso

### Paso 1: Clonar el Repositorio

```bash
git clone https://github.com/granafoods/grana-platform.git
cd grana-platform
```

### Paso 2: Ejecutar Setup

```bash
./setup.sh
```

Este script automaticamente:
- Verifica Python, Node.js y npm
- Crea el virtual environment (`backend/venv/`)
- Instala dependencias de Python (`requirements.txt`)
- Instala dependencias de Node.js (`npm install`)
- Verifica archivos `.env.development`

### Paso 3: Iniciar Docker Desktop

Abre Docker Desktop y espera a que este corriendo (icono verde).

### Paso 4: Iniciar Supabase Local

```bash
npx supabase start
```

Primera vez toma ~5 minutos (descarga imagenes Docker).

Cuando termine, veras:

```
Started supabase local development setup.

         API URL: http://127.0.0.1:54321
     GraphQL URL: http://127.0.0.1:54321/graphql/v1
          DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
      Studio URL: http://127.0.0.1:54323
```

### Paso 5: Aplicar Migraciones

```bash
npx supabase db reset
```

Esto aplica todas las migraciones de `supabase/migrations/` y crea las tablas.

### Paso 6: Cargar Datos (Opcional pero Recomendado)

Para trabajar con datos reales:

```bash
./scripts/load-remote-data.sh
```

Este script copia datos de produccion a tu base local.

---

## 3. Configuracion de Credenciales

### Archivos Necesarios

| Archivo | Proposito | En Git? |
|---------|-----------|---------|
| `backend/.env.development` | Desarrollo (DB local) | Si |
| `frontend/.env.development` | Desarrollo (DB local) | Si |
| `backend/.env.production` | Produccion (DB remota) | No |
| `frontend/.env.production` | Produccion (DB remota) | No |

### Archivos de Desarrollo (Ya incluidos)

Los archivos `.env.development` YA estan en el repositorio con credenciales para Supabase local (Docker). No necesitas hacer nada.

### Archivos de Produccion (Obtener del equipo)

Para conectar a la base de datos de produccion, necesitas obtener:
- `backend/.env.production`
- `frontend/.env.production`

**Donde obtenerlos:**
1. Solicitar a un administrador del proyecto
2. Carpeta compartida del equipo
3. Si tienes acceso, estan en `.credentials_backup/` (gitignored)

**Copiar desde backup (si existe):**
```bash
cp .credentials_backup/backend.env.production backend/.env.production
cp .credentials_backup/frontend.env.production frontend/.env.production
```

### Variables Criticas

**AUTH_SECRET debe ser identico en backend y frontend.**

```
# Valor actual (desarrollo y produccion)
AUTH_SECRET=grana_platform_secret_key_2025_production_ready
```

---

## 4. Levantar el Proyecto

### Desarrollo (Base de datos local)

```bash
./dev.sh
```

Esto levanta:
- Backend (FastAPI): http://localhost:8000
- Frontend (Next.js): http://localhost:3000
- API Docs: http://localhost:8000/docs
- Supabase Studio: http://127.0.0.1:54323

### Produccion (Base de datos remota)

```bash
./prod.sh
```

**ADVERTENCIA:** Conecta a datos reales. Ten cuidado.

### Detener Servicios

```bash
./stop.sh              # Detiene frontend y backend
npx supabase stop      # Detiene Supabase (opcional)
```

---

## 5. Verificar que Todo Funciona

### Verificar Backend

```bash
curl http://localhost:8000/health
# Debe retornar: {"status":"ok"}
```

### Verificar Frontend

Abre http://localhost:3000 en el navegador.

### Verificar Base de Datos

```bash
# Conectar a PostgreSQL local
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -c "SELECT COUNT(*) FROM products;"
```

### Ver Logs

```bash
# Backend
tail -f /tmp/grana_backend.log

# Frontend
tail -f /tmp/grana_frontend.log
```

---

## 6. Comandos del Dia a Dia

### Inicio Rapido

```bash
# Si Supabase no esta corriendo
npx supabase start

# Levantar la app
./dev.sh
```

### Despues de Cambiar de Rama

```bash
git checkout otra-rama
./setup.sh                        # Reinstalar dependencias
npx supabase db reset             # Re-aplicar migraciones
./scripts/load-remote-data.sh    # Re-cargar datos (opcional)
./dev.sh
```

### Comandos de Supabase

```bash
npx supabase status      # Ver estado
npx supabase db reset    # Reiniciar DB (borra todo)
npx supabase stop        # Detener contenedores
npx supabase logs        # Ver logs
```

### Tests y Linting

```bash
# Backend
cd backend && source venv/bin/activate
pytest                    # Correr tests
flake8 app/               # Linting
black app/ --check        # Verificar formato

# Frontend
cd frontend
npm run lint              # ESLint
npx tsc --noEmit          # Type check
```

---

## 7. Solucion de Problemas

### "Docker is not running"

**Solucion:** Abre Docker Desktop y espera a que inicie.

### "Connection refused" a Supabase

**Solucion:**
```bash
npx supabase start
```

### "Port 3000/8000 already in use"

**Solucion:**
```bash
./stop.sh
# O manualmente:
lsof -ti:3000 | xargs kill
lsof -ti:8000 | xargs kill
```

### "Module not found: psycopg2"

**Solucion:**
```bash
cd backend
source venv/bin/activate
pip install psycopg2-binary
```

### "venv not found" o errores de Python

**Solucion:**
```bash
rm -rf backend/venv
./setup.sh
```

### "npm install" falla

**Solucion:**
```bash
rm -rf frontend/node_modules
rm frontend/package-lock.json
cd frontend && npm install
```

### Base de datos vacia

**Solucion:**
```bash
npx supabase db reset
./scripts/load-remote-data.sh
```

### Frontend no carga datos

**Verificar:**
1. Backend corriendo: `curl http://localhost:8000/health`
2. Ver logs: `tail -f /tmp/grana_backend.log`
3. CORS configurado en `.env` del backend

### "Invalid credentials" en produccion

**Verificar:**
1. Archivos `.env.production` existen
2. `AUTH_SECRET` es igual en backend y frontend
3. `DATABASE_URL` usa puerto 6543 (Session Pooler)

---

## Resumen: Primera Instalacion

```bash
# 1. Clonar
git clone https://github.com/granafoods/grana-platform.git
cd grana-platform

# 2. Instalar dependencias
./setup.sh

# 3. Iniciar Docker Desktop (manualmente)

# 4. Iniciar Supabase
npx supabase start

# 5. Crear tablas
npx supabase db reset

# 6. Cargar datos (opcional)
./scripts/load-remote-data.sh

# 7. Levantar app
./dev.sh

# 8. Abrir en navegador
# http://localhost:3000
```

---

## URLs de Referencia

| Servicio | URL Local | URL Produccion |
|----------|-----------|----------------|
| Frontend | http://localhost:3000 | https://grana-platform.vercel.app |
| Backend | http://localhost:8000 | https://granaplatform-production.up.railway.app |
| API Docs | http://localhost:8000/docs | - |
| Supabase Studio | http://127.0.0.1:54323 | https://supabase.com/dashboard |
| PostgreSQL | localhost:54322 | puerto 6543 (pooler) |

---

## Estructura del Proyecto

```
grana-platform/
├── backend/                 # FastAPI (Python)
│   ├── app/
│   │   ├── api/            # Endpoints
│   │   ├── core/           # Config, auth, database
│   │   ├── models/         # SQLAlchemy models
│   │   └── services/       # Business logic
│   ├── tests/
│   ├── requirements.txt
│   └── .env.development    # Credenciales locales
│
├── frontend/               # Next.js (React)
│   ├── app/               # Pages (App Router)
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── .env.development   # Credenciales locales
│
├── supabase/
│   ├── migrations/        # SQL migrations
│   └── config.toml        # Supabase config
│
├── scripts/
│   └── load-remote-data.sh  # Copia datos de prod
│
├── setup.sh               # Instala dependencias
├── dev.sh                 # Inicia en desarrollo
├── prod.sh                # Inicia en produccion
└── stop.sh                # Detiene servicios
```
