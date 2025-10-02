# 🚂 Guía de Configuración de Railway

## 📋 ¿Qué es Railway?

Railway es una plataforma que permite **hospedar tu backend (API)** en la nube de forma simple y gratuita. Es como tener un servidor en internet donde tu código Python (FastAPI) estará corriendo 24/7.

**¿Por qué Railway?**
- ✅ Gratis hasta $5 USD/mes de uso (suficiente para empezar)
- ✅ Se conecta directo con tu repositorio de Git
- ✅ Despliega automáticamente cuando haces cambios
- ✅ Muy fácil de configurar (sin conocimientos de DevOps)

---

## 🎯 Objetivo

Al terminar esta guía, tendrás:
1. ✅ Cuenta de Railway creada
2. ✅ Tu backend de Grana corriendo en Railway
3. ✅ URL pública para acceder a tu API (ej: `https://grana-backend.up.railway.app`)
4. ✅ Despliegue automático cada vez que actualices el código

---

## 📝 Pre-requisitos

Antes de empezar, necesitas:
- ✅ Cuenta de GitHub (donde está tu código)
- ✅ Haber completado la configuración de Supabase (Paso 1)
- ✅ Tarjeta de crédito/débito (Railway requiere verificación, pero no te cobra si estás en el plan gratis)

---

## 🚀 Paso 1: Crear Cuenta en Railway

### 1.1 Registrarse

1. Ve a **https://railway.app**
2. Clic en **"Login"** (arriba a la derecha)
3. Selecciona **"Login with GitHub"**
4. Autoriza Railway a acceder a tu GitHub

**📸 Deberías ver:**
```
Welcome to Railway!
Create your first project
```

### 1.2 Verificar Cuenta (Trial Plan)

Railway te da **$5 USD gratis** cada mes como trial. Para activarlo:

1. Clic en tu avatar (arriba a la derecha)
2. Clic en **"Account Settings"**
3. Ve a la pestaña **"Plans"**
4. Clic en **"Start Trial"**
5. Ingresa tu tarjeta (NO se cobrará nada mientras no excedas $5/mes)
6. Confirma

**✅ Verificación exitosa cuando veas:**
```
Trial Plan Active
$5.00 USD / month included
```

---

## 🔧 Paso 2: Preparar tu Código para Railway

Antes de desplegar, necesitamos crear algunos archivos de configuración.

### 2.1 Verificar Estructura de Archivos

Tu proyecto debe tener esta estructura:

```
grana-system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # Tu API FastAPI
│   │   ├── core/
│   │   ├── models/
│   │   └── routes/
│   ├── requirements.txt      # ✅ Ya existe
│   ├── .env                  # ✅ Ya existe (NO se sube a Git)
│   └── Procfile             # ⚠️ Vamos a crear este archivo
└── README.md
```

### 2.2 Crear archivo Procfile

El `Procfile` le dice a Railway cómo iniciar tu aplicación.

**Crear archivo:** `backend/Procfile`

```bash
cd /home/javier/Proyectos/Grana/grana-system/backend
```

**Contenido del archivo:**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**¿Qué hace esto?**
- `web:` - Indica que es un servicio web
- `uvicorn` - El servidor que corre FastAPI
- `app.main:app` - Apunta a tu aplicación en `app/main.py`
- `--host 0.0.0.0` - Acepta conexiones de cualquier IP
- `--port $PORT` - Usa el puerto que Railway asigna automáticamente

### 2.3 Verificar main.py

Tu archivo `backend/app/main.py` debe tener esta estructura básica:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION
)

# CORS - Permite que tu frontend se conecte desde otro dominio
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Grana API - Sistema de Integración",
        "status": "online",
        "version": settings.API_VERSION
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

---

## 📦 Paso 3: Subir Código a GitHub

Railway necesita que tu código esté en GitHub para desplegarlo.

### 3.1 Crear Repositorio en GitHub

1. Ve a **https://github.com/new**
2. Nombre del repositorio: `grana-system`
3. Descripción: `Sistema de integración para Grana - Backend API`
4. **⚠️ IMPORTANTE:** Selecciona **"Private"** (para proteger tus credenciales)
5. NO marques "Add README" (ya tienes uno)
6. Clic en **"Create repository"**

### 3.2 Verificar .gitignore

**MUY IMPORTANTE:** Antes de subir código, verifica que `.gitignore` esté configurado:

**Archivo:** `/home/javier/Proyectos/Grana/grana-system/.gitignore`

Debe incluir:
```
# Environment variables (NUNCA subir credenciales)
.env
.env.local
backend/.env

# Virtual environments
venv/
backend/venv/
env/
ENV/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database
*.db
*.sqlite3

# Logs
*.log
logs/
```

### 3.3 Subir Código a GitHub

```bash
cd /home/javier/Proyectos/Grana/grana-system

# Inicializar Git (si no lo hiciste antes)
git init

# Agregar todos los archivos
git add .

# Crear primer commit
git commit -m "Initial commit - Grana Backend API setup"

# Conectar con tu repositorio de GitHub
git remote add origin https://github.com/TU_USUARIO/grana-system.git

# Subir código
git push -u origin main
```

**⚠️ Reemplaza `TU_USUARIO`** con tu nombre de usuario de GitHub.

**Si te pide credenciales:**
- Usuario: Tu username de GitHub
- Contraseña: Usa un **Personal Access Token** (no tu contraseña)
  - Ve a GitHub → Settings → Developer settings → Personal access tokens
  - Generate new token → Selecciona "repo" → Generate → Copia el token

---

## 🚢 Paso 4: Desplegar en Railway

### 4.1 Crear Nuevo Proyecto

1. En Railway, clic en **"New Project"**
2. Selecciona **"Deploy from GitHub repo"**
3. Busca y selecciona tu repositorio **`grana-system`**
4. Railway detectará automáticamente que es un proyecto Python

**✅ Deberías ver:**
```
Building grana-system...
Installing dependencies from requirements.txt
```

### 4.2 Configurar Variables de Entorno

⚠️ **IMPORTANTE:** Railway necesita las mismas variables de entorno que tienes en tu `.env` local.

1. En tu proyecto de Railway, clic en tu servicio (aparece como "grana-system")
2. Ve a la pestaña **"Variables"**
3. Clic en **"+ New Variable"**

**Agrega TODAS estas variables:**

```bash
# Supabase (copia desde tu archivo backend/.env)
SUPABASE_URL=https://lypuvibmtxjaxmcmahxr.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:%24Ilofono1@db.lypuvibmtxjaxmcmahxr.supabase.co:5432/postgres

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# CORS - Permitir acceso desde frontend (ajustar después cuando tengas dominio)
ALLOWED_ORIGINS=http://localhost:3000,https://grana-frontend.vercel.app

# APIs Externas (llenar después cuando las tengas)
SHOPIFY_PASSWORD=
SHOPIFY_STORE_NAME=
MERCADOLIBRE_CLIENT_ID=
MERCADOLIBRE_CLIENT_SECRET=
WALMART_CLIENT_ID=
WALMART_CLIENT_SECRET=
CENCOSUD_ACCESS_TOKEN=
```

**💡 Tip:** Puedes copiar todas las variables de una vez:
- Clic en **"RAW Editor"**
- Pega todas las líneas juntas
- Railway las separará automáticamente

4. Clic en **"Save"** (arriba a la derecha)

**⚠️ Nota sobre API_DEBUG:**
- En local: `API_DEBUG=true` (para ver errores detallados)
- En Railway: `API_DEBUG=false` (por seguridad en producción)

### 4.3 Configurar Directorio de Inicio

Railway necesita saber que tu código está en la carpeta `backend/`:

1. En tu servicio, ve a **"Settings"**
2. Busca **"Root Directory"**
3. Ingresa: `backend`
4. Busca **"Start Command"** (opcional, el Procfile ya lo maneja)
5. Guarda cambios

### 4.4 Desplegar

1. Railway redesplegará automáticamente después de guardar settings
2. Ve a la pestaña **"Deployments"**
3. Observa el log en tiempo real

**✅ Despliegue exitoso cuando veas:**
```
✓ Build successful
✓ Starting...
✓ Application started on port 8000
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🌐 Paso 5: Obtener URL Pública

### 5.1 Generar Dominio

1. En tu servicio Railway, ve a **"Settings"**
2. Busca **"Networking"** o **"Domains"**
3. Clic en **"Generate Domain"**

Railway te asignará una URL como:
```
https://grana-backend-production-XXXX.up.railway.app
```

### 5.2 Probar tu API

Abre en tu navegador:
```
https://grana-backend-production-XXXX.up.railway.app
```

**Deberías ver:**
```json
{
  "message": "Grana API - Sistema de Integración",
  "status": "online",
  "version": "1.0.0"
}
```

**También prueba el endpoint de health:**
```
https://grana-backend-production-XXXX.up.railway.app/health
```

**Deberías ver:**
```json
{
  "status": "healthy"
}
```

### 5.3 Probar Conexión a Supabase

Prueba que tu API en Railway puede conectarse a Supabase:
```
https://grana-backend-production-XXXX.up.railway.app/api/v1/channels
```

(Este endpoint aún no existe, lo crearemos en el siguiente paso)

---

## 🔄 Paso 6: Configurar Despliegue Automático

Railway ya está configurado para redesplegar automáticamente cada vez que hagas `git push` a tu repositorio.

### 6.1 Workflow Normal de Desarrollo

```bash
# 1. Hacer cambios en tu código local
nano backend/app/main.py

# 2. Probar localmente
cd backend
./venv/bin/python3 -m uvicorn app.main:app --reload

# 3. Cuando esté listo, subir a GitHub
git add .
git commit -m "feat: agregar endpoint de canales"
git push origin main

# 4. Railway detecta el push y redesplega automáticamente (1-2 minutos)
```

### 6.2 Ver Logs en Tiempo Real

Para ver qué está pasando en tu aplicación en Railway:

1. Ve a tu proyecto en Railway
2. Clic en tu servicio
3. Ve a **"Deployments"**
4. Clic en el deployment más reciente
5. Verás los logs en tiempo real

**Comandos útiles:**
- Ver logs: `View Logs` en Railway dashboard
- Reiniciar servicio: Settings → Restart

---

## 📊 Paso 7: Monitoreo y Métricas

### 7.1 Ver Uso de Recursos

Railway te muestra métricas en tiempo real:

1. En tu servicio, ve a **"Metrics"**
2. Verás:
   - CPU usage
   - Memory usage
   - Network traffic
   - Request count

### 7.2 Monitorear Créditos

Recuerda que tienes **$5 USD gratis/mes**:

1. Clic en tu avatar → **"Account Settings"**
2. Ve a **"Usage"**
3. Verás cuánto has usado del crédito mensual

**Estimación de uso para Grana:**
- Backend pequeño (FastAPI): ~$1-2 USD/mes
- Con tráfico bajo/medio: Estarás bien dentro del límite

---

## 🔒 Paso 8: Seguridad y Buenas Prácticas

### 8.1 Variables de Entorno Sensibles

✅ **NUNCA** subas a Git:
- `.env` archivos
- Contraseñas
- API keys
- Tokens de acceso

✅ **SIEMPRE** usa variables de entorno en Railway

### 8.2 CORS Configuration

En producción, actualiza `ALLOWED_ORIGINS` para permitir solo tu frontend:

```python
# En Railway variables
ALLOWED_ORIGINS=https://tu-dominio-frontend.vercel.app,https://grana.com
```

### 8.3 Rate Limiting (Futuro)

Cuando tengas más tráfico, considera agregar rate limiting para proteger tu API.

---

## 🆘 Troubleshooting

### ❌ Error: "Application failed to respond"

**Causa:** El puerto no está configurado correctamente.

**Solución:**
1. Verifica que `Procfile` tenga `--port $PORT`
2. Verifica que `main.py` no tenga un puerto hardcodeado

### ❌ Error: "Module not found"

**Causa:** Falta una dependencia en `requirements.txt`

**Solución:**
1. Verifica que `requirements.txt` esté actualizado
2. Asegúrate de incluir todas las librerías que usas

### ❌ Error: "Database connection failed"

**Causa:** Variables de entorno mal configuradas

**Solución:**
1. Ve a Railway → Variables
2. Verifica que `DATABASE_URL` tenga la contraseña correcta
3. Verifica que `SUPABASE_SERVICE_ROLE_KEY` sea correcta

### ❌ Build muy lento o falla

**Causa:** `requirements.txt` tiene versiones muy antiguas o conflictivas

**Solución:**
1. Actualiza las versiones en `requirements.txt`
2. Usa rangos de versiones: `fastapi>=0.104.1`

---

## 📚 Recursos Adicionales

### Documentación Oficial
- Railway Docs: https://docs.railway.app
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/

### Comandos Útiles de Railway CLI (Opcional)

Puedes instalar Railway CLI para controlar tu proyecto desde la terminal:

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Ver logs en tiempo real
railway logs

# Ejecutar comandos en Railway
railway run python manage.py migrate
```

---

## ✅ Checklist Final

Antes de continuar al siguiente paso, verifica:

- [ ] Cuenta de Railway creada y verificada
- [ ] Repositorio privado en GitHub creado
- [ ] `.gitignore` configurado correctamente
- [ ] Código subido a GitHub sin credenciales
- [ ] Proyecto desplegado en Railway
- [ ] Variables de entorno configuradas en Railway
- [ ] URL pública funcionando (devuelve JSON)
- [ ] Endpoint `/health` responde correctamente
- [ ] Despliegue automático probado (hacer un cambio y push)

---

## 🎉 ¡Felicitaciones!

Tu backend de Grana está ahora corriendo en la nube, accesible desde cualquier lugar, y se actualiza automáticamente cada vez que haces cambios.

**Próximo paso:** Crear el frontend con Next.js y desplegarlo en Vercel (Paso 3)

---

## 💡 Notas Importantes

### Costo Estimado
Con el uso normal de Grana (Macarena + 2-3 usuarios):
- **Mes 1-3:** $0 (dentro del trial de $5)
- **Mes 4+:** ~$2-3 USD/mes si sigues en Railway
- **Alternativa futura:** Migrar a un VPS si creces ($5-10/mes con más recursos)

### Escalabilidad
Railway es perfecto para empezar, pero cuando Grana crezca (más de 1000 pedidos/día), considera:
- AWS/Google Cloud para más control
- Load balancers para múltiples instancias
- Cache con Redis

### Soporte
Si tienes problemas con Railway:
- Discord de Railway: https://discord.gg/railway
- Soporte via email: team@railway.app

---

**Última actualización:** Septiembre 2024
**Autor:** Claude + Javier Andrews (TM3)
