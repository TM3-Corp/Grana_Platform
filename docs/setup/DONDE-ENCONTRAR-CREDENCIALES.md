# 🔑 Dónde Encontrar las Credenciales de Supabase

## 🎯 Resumen Rápido

Necesitas copiar **4 valores** desde Supabase a tus archivos `.env`:

| Credencial | Dónde encontrarla en Supabase |
|------------|-------------------------------|
| `SUPABASE_URL` | Project Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Project Settings → API → anon public |
| `SUPABASE_SERVICE_ROLE_KEY` | Project Settings → API → service_role ⚠️ |
| `DATABASE_URL` | Project Settings → Database → URI |

---

## 📍 Paso a Paso Visual

### 1️⃣ SUPABASE_URL

```
1. En Supabase, clic en el ícono de ⚙️ (Settings) abajo a la izquierda
2. Clic en "API"
3. Buscar sección "Project URL"
4. Copiar el valor (ejemplo: https://abcdefghijklmnop.supabase.co)
```

**Se ve así:**
```
Project URL
https://abcdefghijklmnop.supabase.co
```

**Pegar en `.env` como:**
```bash
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
```

---

### 2️⃣ SUPABASE_ANON_KEY

```
1. En la MISMA pantalla (Settings → API)
2. Buscar sección "Project API keys"
3. Copiar el valor de "anon public" (es un JWT largo)
```

**Se ve así:**
```
anon public
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTY5ODc2NTQzMiwiZXhwIjoyMDE0MzQxNDMyfQ.abc123xyz789...
[Clic en "Copy"]
```

**Pegar en `.env` como:**
```bash
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOi...
```

---

### 3️⃣ SUPABASE_SERVICE_ROLE_KEY ⚠️ SECRETO

```
1. En la MISMA pantalla (Settings → API)
2. Buscar "service_role" en "Project API keys"
3. Puede estar OCULTO - clic en "Reveal" o el ícono de 👁️
4. Copiar el valor (otro JWT largo)
```

**⚠️ IMPORTANTE:**
- Esta key es **SECRETA**
- Tiene acceso total a la DB
- NUNCA la expongas en frontend
- NUNCA la subas a Git público

**Se ve así:**
```
service_role ⚠️ secret
[👁️ Reveal]  [Copy]
```

**Pegar en `.env` como:**
```bash
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOi...
```

---

### 4️⃣ DATABASE_URL

```
1. En Supabase, Settings → Database
2. Buscar sección "Connection string"
3. Seleccionar pestaña "URI"
4. Copiar el string completo
```

**Se ve así:**
```
Connection string
URI | Session mode | Transaction mode

postgresql://postgres:[YOUR-PASSWORD]@db.abcdefghijklmnop.supabase.co:5432/postgres
```

**⚠️ IMPORTANTE:**
- Donde dice `[YOUR-PASSWORD]`, reemplaza con tu contraseña real
- Es la contraseña que pusiste cuando CREASTE el proyecto
- Si la olvidaste, puedes resetearla en Settings → Database → "Reset Database Password"

**Pegar en `.env` como:**
```bash
DATABASE_URL=postgresql://postgres:tu_password_real_aqui@db.abcdefghijklmnop.supabase.co:5432/postgres
```

---

## ✅ Checklist de Verificación

Después de copiar las 4 credenciales:

- [ ] `SUPABASE_URL` empieza con `https://` y termina con `.supabase.co`
- [ ] `SUPABASE_ANON_KEY` es un JWT largo (empieza con `eyJhbGc...`)
- [ ] `SUPABASE_SERVICE_ROLE_KEY` es un JWT largo (empieza con `eyJhbGc...`)
- [ ] `DATABASE_URL` empieza con `postgresql://postgres:` y tiene tu password
- [ ] No tiene la palabra "REEMPLAZA" en ningún lado
- [ ] Guardaste los archivos `.env` y `.env.local`

---

## 🧪 Probar que Funciona

Una vez que hayas copiado TODAS las credenciales:

```bash
cd /home/javier/Proyectos/Grana/grana-system/backend
python3 test_connection.py
```

**Deberías ver:**
```
🧪 TEST DE CONEXIÓN A SUPABASE
================================================================================

1️⃣ Verificando variables de entorno...
   ✅ SUPABASE_URL: https://abcdefghijklmnop...
   ✅ SUPABASE_ANON_KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6...
   ✅ SUPABASE_SERVICE_ROLE_KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6...
   ✅ DATABASE_URL: postgresql://postgres:...

✅ Todas las variables de entorno están configuradas

2️⃣ Probando conexión con Supabase Client...
   ✅ Conexión exitosa con Supabase Client
   ✅ Tabla 'channels' accesible (1 registros)

...
```

---

## 🆘 Troubleshooting

### Error: "Variables con REEMPLAZA"
**Problema:** No reemplazaste los placeholders
**Solución:** Edita `backend/.env` y copia las credenciales reales

### Error: "password authentication failed"
**Problema:** Contraseña incorrecta en `DATABASE_URL`
**Solución:**
1. Ve a Supabase → Settings → Database
2. Clic en "Reset Database Password"
3. Copia la nueva contraseña
4. Actualiza `DATABASE_URL` con la nueva contraseña

### Error: "relation 'channels' does not exist"
**Problema:** No ejecutaste el schema SQL
**Solución:**
1. Ve a Supabase → SQL Editor
2. Copia TODO el archivo `docs/database-schema.sql`
3. Pega y ejecuta (Ctrl+Enter)

### No sé cuál es mi contraseña de DB
**Solución:**
1. Supabase → Settings → Database
2. Clic en "Reset Database Password"
3. Genera nueva contraseña
4. Cópiala INMEDIATAMENTE (solo se muestra una vez)
5. Actualiza tu `.env`

---

## 📄 Archivos que Debes Editar

Necesitas editar **2 archivos** con las mismas credenciales:

### 1. `/home/javier/Proyectos/Grana/grana-system/.env.local`
```bash
# Para el proyecto completo
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
DATABASE_URL=postgresql://...
```

### 2. `/home/javier/Proyectos/Grana/grana-system/backend/.env`
```bash
# Para el backend específicamente
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
DATABASE_URL=postgresql://...

# El resto de variables déjalas como están
API_HOST=0.0.0.0
API_PORT=8000
...
```

---

## 🎯 Próximo Paso

Una vez que el test de conexión pase exitosamente, continúa con:

**Ejecutar el análisis de Relbase** (Paso 2 del setup)

```bash
cd /home/javier/Proyectos/Grana/grana-integration
python3 analisis_completo_relbase.py
```

---

¿Listo? ¡Copia las credenciales y prueba! 🚀