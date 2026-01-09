# Setup en otro PC — Supabase Local (sin tocar producción)

> **IMPORTANTE: Este proyecto usa Supabase LOCAL para desarrollo.**
> La DB remota de producción NUNCA se toca durante el desarrollo.

---

## ADVERTENCIA CRÍTICA

```
╔══════════════════════════════════════════════════════════════════════╗
║  🚫 NUNCA EJECUTES ESTOS COMANDOS:                                   ║
║                                                                      ║
║     npx supabase link          ← Conecta con producción              ║
║     npx supabase db push       ← Modifica DB remota                  ║
║     npx supabase db pull       ← Descarga desde producción           ║
║                                                                      ║
║  ✅ SOLO USA COMANDOS LOCALES:                                       ║
║                                                                      ║
║     npx supabase start         ← Levanta Docker local                ║
║     npx supabase db reset      ← Reinicia DB local con migraciones   ║
║     npx supabase stop          ← Para contenedores locales           ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Claude Code tiene un hook que bloquea `supabase push` automáticamente.**

---

## 0) Qué NO se hace

- ❌ **No se modifica la DB remota de Supabase** (producción)
- ❌ **No se ejecuta `supabase link`** (conecta con remoto)
- ❌ **No se ejecuta `supabase db push`** (modifica remoto)
- ❌ **No se comparten keys remotas** en el repo
- ❌ **No se sube `supabase/.temp`** al repo

---

## 1) Requisitos previos (instalar en el nuevo PC)

### 1.1 Docker Desktop

1. Descarga Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Instálalo y ábrelo
3. Espera a que el ícono diga **"Running"** (ballena sin animación)
4. Verifica en terminal:

```bash
docker --version
docker ps   # Debe funcionar sin errores
```

### 1.2 Node.js

1. Descarga Node.js LTS: https://nodejs.org/
2. Instálalo
3. Verifica:

```bash
node -v    # Debe mostrar v18+ o v20+
npm -v     # Debe mostrar 9+ o 10+
```

### 1.3 Git

```bash
git --version   # Debe estar instalado
```

---

## 2) Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/Grana_Platform.git
cd Grana_Platform
```

---

## 3) Verificar estructura del proyecto

Después de clonar, verifica que existen estos archivos:

```bash
ls supabase/
```

Debes ver:
- ✅ `config.toml` — Configuración de Supabase CLI
- ✅ `migrations/` — Carpeta con archivos `.sql`
- ✅ `REMOTE_SUPABASE_SETUP.md` — Este documento

**NO debe existir:**
- ❌ `supabase/.temp/` — Si existe, bórrala: `rm -rf supabase/.temp`

---

## 4) Levantar Supabase local (Docker)

Desde la raíz del proyecto:

```bash
npx supabase start
```

**Primera vez:** Descargará imágenes Docker (~2-5 minutos).

Al terminar, verás output similar a:

```
Started supabase local development setup.

         API URL: http://127.0.0.1:54321
     GraphQL URL: http://127.0.0.1:54321/graphql/v1
          DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
      Studio URL: http://127.0.0.1:54323
    Inbucket URL: http://127.0.0.1:54324
        anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
service_role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU
```

**Guarda estos valores** — los necesitarás para configurar `.env`.

---

## 5) Aplicar migraciones (crear tablas)

La DB local está vacía. Aplica las migraciones para crear el esquema:

```bash
npx supabase db reset
```

Esto:
1. Borra la DB local (si tenía datos)
2. Aplica todas las migraciones en orden
3. Deja la DB con la estructura correcta (pero sin datos)

**Verifica en Studio:** http://127.0.0.1:54323 → Table Editor

---

## 6) Configurar variables de entorno

### 6.1 Backend (`backend/.env`)

Crea o edita `backend/.env`:

```env
# ============================================
# SUPABASE LOCAL (Docker) — NO PRODUCCIÓN
# ============================================

DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0

# Auth (debe coincidir con frontend)
AUTH_SECRET=grana_platform_secret_key_2025_production_ready

# Otras variables que tu app necesite...
```

### 6.2 Frontend (`frontend/.env.local`)

Crea o edita `frontend/.env.local`:

```env
# ============================================
# SUPABASE LOCAL (Docker) — NO PRODUCCIÓN
# ============================================

NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
NEXT_PUBLIC_API_URL=http://localhost:8000

# Auth
AUTH_SECRET=grana_platform_secret_key_2025_production_ready
NEXTAUTH_URL=http://localhost:3000
```

⚠️ **Las keys locales son siempre las mismas** (son de demo, no son secretas).

---

## 7) Levantar la aplicación

### Opción A: Script unificado (recomendado)

```bash
./dev.sh
```

### Opción B: Manual (en terminales separadas)

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

### URLs locales:

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Supabase Studio | http://127.0.0.1:54323 |

---

## 8) Comandos útiles de Supabase CLI

### Ver estado de contenedores

```bash
npx supabase status
```

### Parar Supabase local

```bash
npx supabase stop
```

### Parar y borrar todos los datos locales

```bash
npx supabase stop --no-backup
```

### Reiniciar DB desde migraciones (borra datos)

```bash
npx supabase db reset
```

### Crear nueva migración

```bash
npx supabase migration new nombre_descriptivo
# Edita el archivo creado en supabase/migrations/
# Luego aplica con: npx supabase db reset
```

---

## 9) Poblar la DB local con datos de prueba (opcional)

La DB local está vacía después de `db reset`. Opciones:

### Opción A: Insertar datos manualmente

1. Abre Studio: http://127.0.0.1:54323
2. Ve a Table Editor
3. Inserta registros en las tablas que necesites

### Opción B: Crear script de seed

Crea `supabase/seed.sql` con INSERTs de datos de prueba:

```sql
-- Ejemplo de seed data
INSERT INTO users (email, name, role) VALUES
  ('admin@test.com', 'Admin Local', 'admin'),
  ('user@test.com', 'Usuario Local', 'user');
```

Luego aplica con:
```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -f supabase/seed.sql
```

---

## 10) Troubleshooting

### Error: "Cannot connect to Docker daemon"

```bash
# Verifica que Docker Desktop esté corriendo
docker ps

# Si no funciona, abre Docker Desktop y espera
```

### Error: "Port 54321 already in use"

```bash
# Para todos los contenedores de Supabase
npx supabase stop

# Si persiste, mata el proceso manualmente
lsof -i :54321
kill -9 <PID>
```

### Error: "Migration failed"

```bash
# Revisa el error específico en el output
# Luego corrige el archivo .sql en supabase/migrations/
# Y vuelve a intentar:
npx supabase db reset
```

### La app no conecta a la DB

1. Verifica que Supabase esté corriendo: `npx supabase status`
2. Verifica que `.env` apunte a `127.0.0.1` (no a producción)
3. Verifica puertos: DB=54322, API=54321, Studio=54323

---

## 11) Checklist de verificación

Antes de empezar a desarrollar, verifica:

- [ ] Docker Desktop está **Running**
- [ ] `docker ps` muestra contenedores de supabase
- [ ] `npx supabase status` muestra URLs y puertos
- [ ] Studio funciona: http://127.0.0.1:54323
- [ ] Las tablas existen en Studio → Table Editor
- [ ] `backend/.env` apunta a `127.0.0.1:54322`
- [ ] `frontend/.env.local` apunta a `127.0.0.1:54321`
- [ ] La app levanta sin errores de conexión

---

## 12) Diferencias Local vs Producción

| Aspecto | Local (Docker) | Producción (Supabase Cloud) |
|---------|----------------|----------------------------|
| DB Host | `127.0.0.1` | `aws-1-sa-east-1.pooler.supabase.com` |
| DB Puerto | `54322` | `6543` (Session Pooler) |
| API URL | `http://127.0.0.1:54321` | `https://lypuvibmtxjaxmcmahxr.supabase.co` |
| Studio | `http://127.0.0.1:54323` | `https://supabase.com/dashboard` |
| Keys | Keys de demo (públicas) | Keys reales (secretas) |
| Datos | Vacía / seed local | Datos de producción |

---

## 13) Protección de Claude Code

Este repositorio tiene un **hook de seguridad** que bloquea automáticamente comandos peligrosos cuando usas Claude Code:

**Bloqueados:**
- `supabase push` / `supabase db push` → Modifica producción
- `npm run build` → Puede conectar con remoto

**Permitidos:**
- `npx supabase start/stop/status`
- `npx supabase db reset`
- `npx supabase migration new`
- `npx tsc --noEmit` (verificar tipos)

El hook está en `.claude/hooks/block-remote-commands.sh`.
