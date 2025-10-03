# 🚀 Guía de Configuración de Vercel (Frontend)

## 📝 ¿Qué es Vercel?

**Vercel** es una plataforma de hosting especializada en aplicaciones frontend (páginas web). Es la empresa que creó **Next.js**, el framework que usaremos para el dashboard de Grana.

### ¿Por qué Vercel?

- ✅ **Gratis para proyectos personales** (hasta 100 GB de ancho de banda/mes)
- ✅ **Deploy automático** desde GitHub (igual que Railway)
- ✅ **CDN global** (tu sitio carga rápido en todo el mundo)
- ✅ **HTTPS automático** (certificados SSL gratis)
- ✅ **Perfect para Next.js** (optimizado al máximo)

---

## 🎯 Lo que Vamos a Hacer

1. Crear cuenta en Vercel
2. Crear proyecto Next.js localmente
3. Conectar Vercel con GitHub
4. Configurar variables de entorno
5. Ver tu dashboard funcionando en internet

**Tiempo estimado:** 20-30 minutos

---

## 📋 Prerequisitos

- ✅ Cuenta de GitHub (ya la tienes)
- ✅ Repositorio `Grana_Platform` en GitHub (ya existe)
- ✅ Backend funcionando en Railway (ya está listo)

---

## Paso 1: Crear Cuenta en Vercel

### 1.1 Ir a Vercel

1. Abre tu navegador
2. Ve a: **https://vercel.com**
3. Haz click en **"Sign Up"** (arriba a la derecha)

### 1.2 Conectar con GitHub

1. Vercel te preguntará cómo quieres crear la cuenta
2. **Selecciona: "Continue with GitHub"**
3. GitHub te pedirá autorización → **Haz click en "Authorize Vercel"**
4. Vercel puede pedirte un nombre de usuario → Usa `javierandrews` o `tm3-corp`

✅ **¡Listo!** Ya tienes cuenta en Vercel vinculada a tu GitHub.

---

## Paso 2: Crear el Proyecto Next.js Localmente

Antes de conectar Vercel, necesitamos crear el código del frontend.

### 2.1 Crear la carpeta del frontend

Vamos a crear la carpeta `frontend/` dentro de tu proyecto:

```bash
cd /home/javier/Proyectos/Grana/Grana_Platform
mkdir frontend
cd frontend
```

### 2.2 Crear proyecto Next.js

**Comando a ejecutar:**
```bash
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --import-alias "@/*"
```

**Respuestas a las preguntas:**
- ✅ Would you like to use TypeScript? → **Yes**
- ✅ Would you like to use ESLint? → **Yes**
- ✅ Would you like to use Tailwind CSS? → **Yes**
- ✅ Would you like to use `src/` directory? → **No**
- ✅ Would you like to use App Router? → **Yes**
- ✅ Would you like to customize the default import alias? → **No**

### 2.3 Verificar que se creó correctamente

```bash
ls -la
```

**Deberías ver:**
- `package.json`
- `next.config.js`
- `tailwind.config.ts`
- `app/` (carpeta con página principal)
- `public/` (carpeta para imágenes)

---

## Paso 3: Configurar Variables de Entorno (Frontend)

El frontend necesita saber la URL de tu backend en Railway.

### 3.1 Crear archivo `.env.local`

```bash
cd /home/javier/Proyectos/Grana/Grana_Platform/frontend
nano .env.local
```

### 3.2 Agregar la URL del backend

**Copia y pega esto:**
```env
# URL del backend en Railway
NEXT_PUBLIC_API_URL=https://granaplatform-production.up.railway.app

# Nombre de la aplicación
NEXT_PUBLIC_APP_NAME=Grana Platform
```

**Guarda el archivo:**
- `Ctrl + O` (guardar)
- `Enter` (confirmar)
- `Ctrl + X` (salir)

---

## Paso 4: Probar Localmente

Antes de subir a Vercel, vamos a verificar que funciona en tu computador.

### 4.1 Instalar dependencias

```bash
cd /home/javier/Proyectos/Grana/Grana_Platform/frontend
npm install
```

**Esto tomará 1-2 minutos** (descarga todas las librerías necesarias)

### 4.2 Iniciar servidor de desarrollo

```bash
npm run dev
```

**Deberías ver:**
```
   ▲ Next.js 14.x.x
   - Local:        http://localhost:3000
   - ready started server on 0.0.0.0:3000
```

### 4.3 Abrir en el navegador

1. Abre tu navegador
2. Ve a: **http://localhost:3000**
3. Deberías ver la página de inicio de Next.js

✅ **¡Funciona!** Puedes detener el servidor con `Ctrl + C`

---

## Paso 5: Actualizar `.gitignore`

Antes de subir a GitHub, asegurémonos de NO subir archivos innecesarios.

### 5.1 Verificar `.gitignore` del frontend

```bash
cd /home/javier/Proyectos/Grana/Grana_Platform/frontend
cat .gitignore
```

**Debería incluir:**
```
# next.js
/.next/
/out/
/build

# dependencies
/node_modules

# local env files
.env*.local
.env.local
.env.development.local
.env.test.local
.env.production.local
```

✅ **Si ves esto, estás listo.** Next.js crea el `.gitignore` automáticamente.

---

## Paso 6: Subir Frontend a GitHub

### 6.1 Agregar cambios a Git

```bash
cd /home/javier/Proyectos/Grana/Grana_Platform
git add .
git status
```

**Deberías ver:**
- `frontend/` (carpeta nueva)
- `frontend/package.json`
- `frontend/app/`
- etc.

**NO deberías ver:**
- ❌ `frontend/node_modules/` (demasiado pesado)
- ❌ `frontend/.env.local` (credenciales privadas)

### 6.2 Hacer commit

```bash
git commit -m "feat: add Next.js frontend project

- Initialize Next.js 14 with TypeScript
- Configure Tailwind CSS
- Set up environment variables for API connection
- Ready for Vercel deployment
"
```

### 6.3 Subir a GitHub

```bash
git push https://javierandrews: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@github.com/TM3-Corp/Grana_Platform.git main
```

✅ **¡Listo!** Tu frontend está en GitHub.

---

## Paso 7: Conectar Vercel con GitHub

Ahora viene la parte más fácil: conectar Vercel a tu repositorio.

### 7.1 Ir al Dashboard de Vercel

1. Ve a: **https://vercel.com/dashboard**
2. Haz click en **"Add New..."** (arriba a la derecha)
3. Selecciona **"Project"**

### 7.2 Importar Repositorio

1. Vercel te mostrará tus repositorios de GitHub
2. **Busca:** `TM3-Corp/Grana_Platform`
3. Haz click en **"Import"**

**Si no ves el repositorio:**
- Haz click en **"Adjust GitHub App Permissions"**
- Autoriza acceso a la organización `TM3-Corp`
- Selecciona `Grana_Platform`
- Guarda y vuelve a Vercel

### 7.3 Configurar el Proyecto

Vercel te preguntará algunos detalles:

**Project Name:**
- Nombre: `grana-platform` (automático, puedes dejarlo así)

**Framework Preset:**
- Vercel detectará **Next.js** automáticamente ✅
- No cambies nada aquí

**Root Directory:**
- ⚠️ **IMPORTANTE:** Haz click en **"Edit"**
- Escribe: `frontend`
- Esto le dice a Vercel que tu código Next.js está en la carpeta `frontend/`

**Build and Output Settings:**
- Dejar todo por defecto:
  - Build Command: `npm run build`
  - Output Directory: `.next`
  - Install Command: `npm install`

### 7.4 Configurar Variables de Entorno

Antes de hacer deploy, agregar las variables:

1. Haz click en **"Environment Variables"** (sección que se despliega)
2. Agrega estas variables:

**Variable 1:**
- Name: `NEXT_PUBLIC_API_URL`
- Value: `https://granaplatform-production.up.railway.app`
- Environment: **Production**, **Preview**, **Development** (todas marcadas)

**Variable 2:**
- Name: `NEXT_PUBLIC_APP_NAME`
- Value: `Grana Platform`
- Environment: **Production**, **Preview**, **Development** (todas marcadas)

### 7.5 Hacer Deploy

1. Haz click en **"Deploy"** (botón azul grande al final)
2. **Vercel empezará a construir tu aplicación** (esto toma 2-3 minutos)

**Verás:**
- ✅ Cloning repository
- ✅ Installing dependencies
- ✅ Building application
- ✅ Deploying to production

### 7.6 ¡Deploy Exitoso! 🎉

Cuando termine, verás:

**Confetti animation** 🎊 + mensaje:
```
Congratulations! Your project has been successfully deployed.
```

Tu frontend estará disponible en:
```
https://grana-platform.vercel.app
```

(o similar - Vercel te mostrará la URL exacta)

---

## Paso 8: Verificar que Funciona

### 8.1 Abrir tu Dashboard

1. Haz click en **"Visit"** o en la URL que te dio Vercel
2. Deberías ver la página de inicio de Next.js

### 8.2 Verificar Conexión con Backend

Tu frontend ahora puede llamar a tu backend con:

```javascript
// En cualquier componente de Next.js
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/channels`)
const data = await response.json()
```

---

## 📊 Resumen: Tu Infraestructura Completa

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  🌐 USUARIO (Navegador)                                 │
│                                                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────┐
│  ☁️ VERCEL (Frontend - Next.js)                         │
│  https://grana-platform.vercel.app                      │
│                                                         │
│  - Dashboard (React/Next.js)                            │
│  - Tablas, gráficos, formularios                        │
│  - Interfaz para Macarena                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ API Calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│  🚂 RAILWAY (Backend - FastAPI)                         │
│  https://granaplatform-production.up.railway.app        │
│                                                         │
│  - REST API (FastAPI)                                   │
│  - Lógica de negocio                                    │
│  - Integraciones con Shopify, ML, etc.                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ SQL Queries (port 6543)
                     ▼
┌─────────────────────────────────────────────────────────┐
│  🗄️ SUPABASE (Database - PostgreSQL)                    │
│  https://lypuvibmtxjaxmcmahxr.supabase.co              │
│                                                         │
│  - PostgreSQL Database                                  │
│  - Single Source of Truth                               │
│  - 10 tablas + 3 vistas                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Deploy Automático (Bonus)

**Cada vez que hagas `git push` a GitHub:**

1. ✅ **Vercel detecta el cambio automáticamente**
2. ✅ **Construye el frontend** (npm run build)
3. ✅ **Deploya a producción** (en ~2 minutos)
4. ✅ **Tu dashboard se actualiza** sin hacer nada más

**Igual que Railway** - pero para el frontend 🚀

---

## ⚙️ Configuraciones Adicionales (Opcional)

### Dominio Personalizado

Si quieres usar tu propio dominio (ej: `dashboard.grana.cl`):

1. Ve a Vercel Dashboard → Tu proyecto
2. Click en **"Settings"** → **"Domains"**
3. Agrega tu dominio
4. Configura los DNS según te indica Vercel

### Preview Deployments

Vercel crea URLs de preview para cada Pull Request:

- Cada PR → URL única (ej: `grana-platform-git-feature-123.vercel.app`)
- Puedes probar cambios antes de mergear a main
- Útil para mostrarle avances a Macarena

---

## ❓ Troubleshooting Común

### Error: "Build failed - Cannot find module 'next'"

**Causa:** Vercel no está usando la carpeta correcta

**Solución:**
1. Ve a Project Settings → General
2. Root Directory → Cambiar a `frontend`
3. Redeploy

### Error: "API calls returning 404"

**Causa:** Variable `NEXT_PUBLIC_API_URL` no configurada

**Solución:**
1. Ve a Project Settings → Environment Variables
2. Agregar `NEXT_PUBLIC_API_URL=https://granaplatform-production.up.railway.app`
3. Redeploy

### Error: "This page could not be found"

**Causa:** Next.js aún no tiene páginas personalizadas

**Solución:** Normal - en el siguiente paso crearemos las páginas del dashboard

---

## ✅ Checklist Final

Antes de continuar, verifica:

- [ ] ✅ Cuenta de Vercel creada y conectada a GitHub
- [ ] ✅ Proyecto Next.js creado en `/frontend`
- [ ] ✅ Variables de entorno configuradas (`.env.local` local y en Vercel)
- [ ] ✅ Código subido a GitHub
- [ ] ✅ Vercel conectado al repositorio `TM3-Corp/Grana_Platform`
- [ ] ✅ Root Directory configurado como `frontend`
- [ ] ✅ Deployment exitoso
- [ ] ✅ Dashboard accesible en `https://grana-platform.vercel.app` (o tu URL)

---

## 🎯 Próximos Pasos

Ahora que tienes el frontend deployado, podemos:

1. **Crear el Dashboard** - Páginas para ver datos
2. **Conectar con el Backend** - Fetch de datos desde Railway
3. **Agregar Autenticación** - Login para Macarena
4. **Tablas y Gráficos** - Visualización de ventas

---

## 📞 Ayuda y Recursos

- **Documentación de Vercel:** https://vercel.com/docs
- **Documentación de Next.js:** https://nextjs.org/docs
- **Dashboard de Vercel:** https://vercel.com/dashboard
- **Estado de Vercel:** https://www.vercel-status.com

---

**Última actualización:** 3 de Octubre, 2025
**Creado para:** Grana Platform - TM3 Corp
