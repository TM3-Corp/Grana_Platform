# 📋 Contexto de Sesión - Grana Platform

**Fecha:** 2 de Octubre, 2025
**Proyecto:** Sistema de Integración de Datos de Ventas para Grana SpA
**Estado:** Configuración de infraestructura en progreso

---

## 🎯 Objetivo General del Proyecto

Crear un sistema completo que:
1. **Consolide datos** de múltiples canales de venta (Shopify, MercadoLibre, Walmart, Cencosud)
2. **Use PostgreSQL (Supabase)** como "single source of truth"
3. **Permita a Macarena editar y corregir datos** con auditoría completa
4. **Backend en Railway** (FastAPI)
5. **Frontend en Vercel** (Next.js - futuro)

**Problema que resuelve:** Macarena gasta 2.75 horas diarias en tareas manuales. El sistema reducirá esto a 5 minutos.

---

## ✅ Progreso Completado en Esta Sesión

### 1. Configuración de Supabase (Base de Datos) ✅

**Estado:** COMPLETADO

- ✅ Proyecto creado en Supabase
- ✅ Credenciales obtenidas:
  - `SUPABASE_URL`: https://lypuvibmtxjaxmcmahxr.supabase.co
  - `SUPABASE_ANON_KEY`: (configurada)
  - `SUPABASE_SERVICE_ROLE_KEY`: (configurada)
  - `DATABASE_URL`: (configurada con password: $Ilofono1)

- ✅ **Schema SQL ejecutado completamente** - Confirmado visualmente en Table Editor
  - 10 tablas creadas: customers, products, channels, orders, order_items, orders_audit, manual_corrections, sync_logs, alerts, inventory_movements
  - 3 vistas creadas: v_low_stock_products, v_orders_full, v_sales_by_channel
  - Triggers de auditoría automática funcionando

- ✅ **Conexión local probada exitosamente** con `test_connection.py`
  - Supabase Client: ✅ Funcionando
  - Tabla 'channels' accesible (1 registro encontrado)

**Archivos relacionados:**
- `/docs/database-schema.sql` - Schema completo de la base de datos
- `/docs/setup/01-SUPABASE-SETUP.md` - Guía paso a paso (completada)
- `/backend/test_connection.py` - Script de prueba de conexión

---

### 2. Configuración de GitHub ✅

**Estado:** COMPLETADO

- ✅ Repositorio creado: `TM3-Corp/Grana_Platform` (privado)
- ✅ Git inicializado localmente
- ✅ `.gitignore` configurado correctamente (protege credenciales)
- ✅ Código subido exitosamente
- ✅ Personal Access Token creado: `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`

**Comandos usados:**
```bash
cd /home/javier/Proyectos/Grana/Grana_Platform
git init
git branch -m main
git remote add origin https://github.com/TM3-Corp/Grana_Platform.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

---

### 3. Configuración de Railway (Backend Hosting) ✅ (PARCIAL)

**Estado:** BACKEND DEPLOYADO, PERO CON PROBLEMAS DE CONEXIÓN A SUPABASE

#### ✅ Logros:

1. **Proyecto Railway creado y conectado**
   - Conectado con GitHub (instalación de Railway App aprobada para TM3-Corp)
   - Repositorio: `TM3-Corp/Grana_Platform`
   - URL pública: https://granaplatform-production.up.railway.app/

2. **Dockerfile creado y funcionando**
   - Python 3.12-slim
   - Instala dependencias desde `backend/requirements.txt`
   - Usa variable `$PORT` de Railway correctamente
   - Build exitoso

3. **Variables de entorno configuradas en Railway**
   ```env
   SUPABASE_URL=https://lypuvibmtxjaxmcmahxr.supabase.co
   SUPABASE_ANON_KEY=[configurada sin comillas]
   SUPABASE_SERVICE_ROLE_KEY=[configurada sin comillas]
   DATABASE_URL=postgresql://postgres:%24Ilofono1@db.lypuvibmtxjaxmcmahxr.supabase.co:5432/postgres
   API_HOST=0.0.0.0
   API_PORT=8000
   API_DEBUG=false
   ALLOWED_ORIGINS=http://localhost:3000,https://grana-frontend.vercel.app
   ```

4. **Deployment exitoso inicial**
   - Commit: `"feat: add Dockerfile for Railway deployment"`
   - API respondiendo correctamente en `/` endpoint
   - Respuesta JSON: `{"message":"Grana API - Sistema de Integración","status":"online","version":"1.0.0"}`

5. **Despliegue automático configurado**
   - Cada `git push` a main → Railway redesplega automáticamente

#### ❌ Problema Actual: Error 502 al Intentar Conexión a Supabase

**Síntomas:**
- Endpoint `/` funciona ✅
- Endpoint `/health` funciona ✅
- Cualquier endpoint que intente usar Supabase → **502 Bad Gateway** ❌

**Deployments fallidos (últimos intentos):**
1. `"debug: add env debug endpoint"` - FAILED
2. `"fix: simplify debug endpoint"` - FAILED
3. `"feat: add test-db endpoint"` - FAILED
4. `"fix: update supabase to 2.20.0"` - FAILED
5. `"fix: use lazy loading for Supabase client"` - FAILED

**Logs observados:**
```
Starting Container
INFO:     Started server process [2]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080

GET / 502 58ms
GET /api/v1/test-db 502 3ms
```

- ✅ Build exitoso
- ✅ Servidor arranca correctamente (Uvicorn running)
- ❌ Requests devuelven 502 (app no puede responder)

---

## 🔴 PROBLEMA ACTUAL: Railway-Supabase Connection

### Contexto del Problema

**Objetivo:** Verificar que Railway puede conectarse a Supabase y leer datos reales.

**Qué hemos intentado:**

#### Intento 1: Inicializar Supabase al arranque
```python
from supabase import create_client, Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
```
**Resultado:** 502 Bad Gateway (app crashea al arrancar)

#### Intento 2: Lazy Loading de Supabase
```python
def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error: {e}")
        return None
```
**Resultado:** 502 Bad Gateway (app crashea al arrancar)

#### Intento 3: Endpoint de debug para variables
```python
@app.get("/api/v1/debug/env")
async def debug_env():
    return {
        "SUPABASE_URL_exists": bool(os.getenv("SUPABASE_URL")),
        # ...
    }
```
**Resultado:** 502 Bad Gateway (app crashea al arrancar)

#### Intento 4: Actualizar dependencias
**Cambio en requirements.txt:**
```diff
- supabase==2.3.0
- httpx>=0.24.0,<0.25.0
+ supabase>=2.20.0
+ httpx>=0.26.0
```
**Resultado:** 502 Bad Gateway (app crashea al arrancar)

### Estado Actual de la Solución

**Último intento (EN PROGRESO):**

Creamos `backend/app/main_simple.py` - Una versión **SIN Supabase** para diagnosticar:
```python
# Sin import de supabase
# Solo endpoints básicos
@app.get("/api/v1/env-check")
async def env_check():
    return {
        "SUPABASE_URL": "SET" if os.getenv("SUPABASE_URL") else "NOT_SET",
        # ...
    }
```

**Dockerfile temporalmente modificado:**
```dockerfile
CMD uvicorn app.main_simple:app --host 0.0.0.0 --port ${PORT:-8000}
```

**Commit:** `"debug: add simplified main without supabase to diagnose 502 errors"`

**PENDIENTE:** Probar si esta versión simplificada funciona.

---

## 🔍 Análisis del Problema

### Hipótesis sobre la causa:

1. **Librería Supabase incompatible con el entorno de Railway**
   - Posible conflicto de versiones
   - Dependencias que fallan en el contenedor Docker

2. **Variables de entorno no se cargan correctamente**
   - Aunque están configuradas en Railway
   - Puede que el formato no sea el correcto

3. **Error silencioso al importar la librería**
   - Python crashea antes de poder logear el error
   - El 502 sugiere que la app no llega a responder

4. **Problema con la inicialización de FastAPI**
   - Algo en el código hace que FastAPI no pueda arrancar
   - Pero localmente funciona bien

### Lo que SÍ sabemos:

✅ **Supabase funciona:** Probado localmente con test_connection.py
✅ **Variables están en Railway:** Configuradas correctamente
✅ **Railway funciona:** API simple responde bien
✅ **Dockerfile funciona:** Build exitoso, servidor arranca
❌ **Conexión Railway → Supabase:** NO PROBADA AÚN

---

## 📁 Estructura del Proyecto

```
Grana_Platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # ❌ Versión con Supabase (crashea en Railway)
│   │   ├── main_simple.py       # ⏳ Versión sin Supabase (en prueba)
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   └── models/
│   │       ├── __init__.py
│   │       └── order.py
│   ├── .env                     # ✅ Credenciales locales (NO en Git)
│   ├── .env.example
│   ├── Procfile                 # (No usado, usamos Dockerfile)
│   ├── requirements.txt         # ✅ Actualizado a supabase>=2.20.0
│   ├── runtime.txt              # python-3.12.0
│   └── test_connection.py       # ✅ Funciona localmente
├── docs/
│   ├── database-schema.sql      # ✅ Ejecutado en Supabase
│   └── setup/
│       ├── 01-SUPABASE-SETUP.md # ✅ Completado
│       └── 02-RAILWAY-SETUP.md  # ⏳ En progreso
├── .dockerignore                # ✅ Configurado
├── .gitignore                   # ✅ Protege credenciales
├── Dockerfile                   # ✅ Funciona (temporalmente usa main_simple)
├── nixpacks.toml                # (Intentado, Railway usa Dockerfile)
└── README.md
```

---

## 🚀 Próximos Pasos

### INMEDIATO (Resolver 502):

1. **Probar versión simplificada actual**
   - URL: https://granaplatform-production.up.railway.app/
   - Endpoint: https://granaplatform-production.up.railway.app/api/v1/env-check

   **SI FUNCIONA:**
   - ✅ Confirma que el problema es específico de Supabase
   - ✅ Sabemos que las variables de entorno llegan
   - **Siguiente paso:** Agregar Supabase paso a paso

   **SI FALLA:**
   - ❌ Hay un problema más fundamental
   - **Siguiente paso:** Revisar configuración de Railway (puerto, health checks, etc.)

2. **Si la versión simple funciona:**
   - Agregar solo el import de Supabase (sin usarlo)
   - Ver si crashea solo con el import
   - Luego intentar crear cliente sin usarlo
   - Finalmente agregar el endpoint de test

3. **Soluciones alternativas si Supabase sigue fallando:**
   - **Opción A:** Usar psycopg2 directamente (sin librería Supabase)
   - **Opción B:** Usar SQLAlchemy con DATABASE_URL
   - **Opción C:** Investigar logs más detallados en Railway

### MEDIANO PLAZO (Una vez resuelto 502):

4. **Crear endpoint `GET /api/v1/channels`**
   - Listar canales de venta desde Supabase
   - Probar que Railway → Supabase funciona end-to-end

5. **Optimizar código para producción**
   - Cambiar de lazy loading a inicialización al arranque
   - Implementar connection pooling
   - Agregar health checks que prueben la BD

6. **Crear más endpoints:**
   - `GET /api/v1/orders` - Listar pedidos
   - `POST /api/v1/orders` - Crear pedidos
   - `GET /api/v1/customers` - Listar clientes
   - etc.

### LARGO PLAZO (Roadmap general):

7. **Análisis de Relbase**
   - Ejecutar `analisis_completo_relbase.py`
   - Obtener datos históricos de ventas
   - Importar a Supabase

8. **Crear Frontend (Next.js en Vercel)**
   - Dashboard de visualización
   - Interfaz para que Macarena edite datos
   - Historial de auditoría

9. **Integrar APIs externas:**
   - Shopify (credenciales pendientes)
   - MercadoLibre (credenciales pendientes)
   - Walmart (credenciales pendientes)
   - Cencosud (credenciales pendientes)

10. **Sistema de sincronización automática**
    - Webhooks desde plataformas
    - Cron jobs para polling
    - Detección de duplicados

---

## 🔑 Información Importante

### Credenciales (NO compartir)

**GitHub:**
- Token: `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`
- Organización: TM3-Corp
- Repo: Grana_Platform

**Supabase:**
- Project URL: https://lypuvibmtxjaxmcmahxr.supabase.co
- Password: `$Ilofono1` (URL encoded: `%24Ilofono1`)
- Anon Key: (en .env)
- Service Role Key: (en .env)

**Railway:**
- URL: https://granaplatform-production.up.railway.app/
- Plan: Trial ($5 USD/mes gratis)
- Región: us-east4

### Comandos Útiles

**Git:**
```bash
cd /home/javier/Proyectos/Grana/Grana_Platform
git add .
git commit -m "mensaje"
git push https://javierandrews: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@github.com/TM3-Corp/Grana_Platform.git main
```

**Test Local:**
```bash
cd /home/javier/Proyectos/Grana/Grana_Platform/backend
python3 test_connection.py
```

**Railway:**
- Cada push a main → auto-deploy
- Ver logs: Railway → Deployments → View logs
- Rollback: Railway → Deployments → ... → Redeploy

---

## 🐛 Debug Checklist

Cuando retomes el trabajo, verifica:

- [ ] ¿La versión `main_simple.py` funciona en Railway?
- [ ] ¿El endpoint `/api/v1/env-check` muestra las variables como "SET"?
- [ ] ¿Los logs de Railway muestran algún error de Python?
- [ ] ¿El build log muestra que todas las dependencias se instalaron?
- [ ] ¿Uvicorn dice que está corriendo en el puerto correcto?

**Si todo lo anterior es ✅ pero sigue fallando:**
- Revisar configuración de Railway (Health Check Path, Watch Paths)
- Verificar que no haya firewall bloqueando Supabase → Railway
- Probar usar psycopg2 directo en lugar de la librería supabase

---

## 📚 Documentación Relacionada

**En el proyecto:**
- `/docs/setup/01-SUPABASE-SETUP.md` - Setup de Supabase (COMPLETADO)
- `/docs/setup/02-RAILWAY-SETUP.md` - Setup de Railway (EN PROGRESO)
- `/docs/database-schema.sql` - Schema de la base de datos
- `/Research/doc/` - Documentación original del análisis

**Archivos clave:**
- `/backend/app/main.py` - Versión con Supabase (crashea)
- `/backend/app/main_simple.py` - Versión sin Supabase (en prueba)
- `/Dockerfile` - Configuración de Docker
- `/backend/requirements.txt` - Dependencias Python

---

## 💡 Aprendizajes de Esta Sesión

### ✅ Qué funcionó bien:
1. **Supabase setup completo** - Documentación clara, ejecución exitosa
2. **GitHub integration** - Proceso suave, organización correcta
3. **Railway auto-deploy** - Funciona perfectamente con GitHub
4. **Dockerfile approach** - Mejor que Railpack/Nixpacks para este caso

### ❌ Desafíos enfrentados:
1. **Librería Supabase en Railway** - Incompatibilidad no esperada
2. **502 sin logs detallados** - Difícil de debuggear
3. **Versiones de dependencias** - Conflictos entre supabase 2.3.0 y 2.20.0

### 🎓 Lecciones aprendidas:
1. **Siempre crear versión mínima primero** - Agregar complejidad gradualmente
2. **Lazy loading puede ser útil para debugging** - Pero no es óptimo para producción
3. **Los 502 en Railway son frustrantes** - Necesitas logs más detallados
4. **Test local ≠ Test en producción** - Entornos diferentes, problemas diferentes

---

## 🎯 Estado Mental / Contexto del Desarrollador

**Filosofía del proyecto:**
- "No sobre-ingeniería"
- Empezar simple, escalar después
- PostgreSQL como single source of truth
- Macarena debe poder confiar y editar los datos

**Decisiones técnicas tomadas:**
- ✅ Supabase sobre AWS RDS (simplicidad + costo)
- ✅ Railway sobre AWS Lambda (menos configuración)
- ✅ Dockerfile sobre Nixpacks (más control)
- ⏳ FastAPI + Supabase library vs psycopg2 directo (pendiente)

**Próxima decisión importante:**
Si la librería de Supabase no funciona en Railway, ¿usamos psycopg2 directamente o seguimos debuggeando?

---

**Última actualización:** 2 de Octubre, 2025 - 16:30
**Último commit:** `a422f80` - "debug: add simplified main without supabase to diagnose 502 errors"
**Deployment activo:** Versión con `main_simple.py` (pendiente de probar)

---

## 🔄 Para Continuar en la Próxima Sesión

1. **Primero:** Probar https://granaplatform-production.up.railway.app/api/v1/env-check
2. **Si funciona:** Agregar Supabase incrementalmente
3. **Si falla:** Investigar problema fundamental de Railway
4. **Goal final de hoy:** Tener endpoint funcional que lea de Supabase desde Railway

**Comando para verificar deployment:**
```bash
curl https://granaplatform-production.up.railway.app/
curl https://granaplatform-production.up.railway.app/api/v1/env-check
```
