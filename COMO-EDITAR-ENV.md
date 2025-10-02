# 📝 Cómo Editar los Archivos .env

## 🎯 Archivos que Debes Editar

Hay **2 archivos** que necesitas editar con tus credenciales de Supabase:

### 1️⃣ Archivo Principal del Proyecto
```bash
/home/javier/Proyectos/Grana/grana-system/.env.local
```

### 2️⃣ Archivo del Backend
```bash
/home/javier/Proyectos/Grana/grana-system/backend/.env
```

---

## 🖊️ Opción 1: Editar con VSCode (Recomendado)

```bash
# Abrir el proyecto completo en VSCode
code /home/javier/Proyectos/Grana/grana-system
```

Luego en VSCode:
1. Abrir `.env.local` desde el explorador de archivos
2. Buscar las líneas con "REEMPLAZA"
3. Reemplazar con tus credenciales reales de Supabase
4. Guardar (Ctrl+S)
5. Hacer lo mismo con `backend/.env`

---

## 🖊️ Opción 2: Editar con nano (en terminal)

```bash
# Editar archivo principal
nano /home/javier/Proyectos/Grana/grana-system/.env.local
```

**Teclas de nano:**
- `Ctrl+O` → Guardar
- `Enter` → Confirmar
- `Ctrl+X` → Salir

Luego editar el del backend:
```bash
nano /home/javier/Proyectos/Grana/grana-system/backend/.env
```

---

## 🖊️ Opción 3: Editar con vim

```bash
vim /home/javier/Proyectos/Grana/grana-system/.env.local
```

**Teclas de vim:**
- `i` → Modo inserción (para editar)
- `Esc` → Salir de modo inserción
- `:wq` → Guardar y salir
- `:q!` → Salir sin guardar

---

## ✅ Qué Reemplazar Exactamente

Busca estas líneas y reemplaza:

### Antes (placeholder):
```bash
SUPABASE_URL=https://REEMPLAZA-ESTO.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.REEMPLAZA-ESTO
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.REEMPLAZA-ESTO
DATABASE_URL=postgresql://postgres:REEMPLAZA-PASSWORD@db.REEMPLAZA-REF.supabase.co:5432/postgres
```

### Después (con tus valores reales):
```bash
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTY5ODc2NTQzMiwiZXhwIjoyMDE0MzQxNDMyfQ.abc123xyz789
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjk4NzY1NDMyLCJleHAiOjIwMTQzNDE0MzJ9.xyz789abc
DATABASE_URL=postgresql://postgres:mi_password_real@db.abcdefghijklmnop.supabase.co:5432/postgres
```

---

## 🔍 Cómo Verificar que lo Hiciste Bien

Después de editar, verifica con:

```bash
# Ver las primeras líneas del archivo (sin mostrar valores completos por seguridad)
head -20 /home/javier/Proyectos/Grana/grana-system/.env.local
```

**Deberías ver:**
- ✅ URLs que NO dicen "REEMPLAZA"
- ✅ Keys largas que empiezan con `eyJhbGc...`
- ✅ DATABASE_URL con tu password (no con "REEMPLAZA-PASSWORD")

---

## 🧪 Probar que Funciona

Después de editar AMBOS archivos, prueba la conexión:

```bash
cd /home/javier/Proyectos/Grana/grana-system/backend
python3 test_connection.py
```

**Si ves errores tipo "REEMPLAZA"**, significa que no editaste correctamente.

---

## 🆘 Ayuda Rápida

### "No sé cómo usar los editores de texto"
**Solución más simple:**
```bash
# Usa VS Code (más amigable)
code /home/javier/Proyectos/Grana/grana-system/.env.local

# Edita como si fuera Word, guarda (Ctrl+S), listo
```

### "Borré algo sin querer"
**Solución:**
```bash
# Restaura el archivo original
cd /home/javier/Proyectos/Grana/grana-system
# Yo te lo regenero si me avisas
```

### "Ya edité pero el test falla"
**Posibles causas:**
1. No guardaste el archivo (Ctrl+S)
2. Editaste solo 1 archivo (debes editar los 2)
3. Copiaste las credenciales incorrectas
4. Falta ejecutar el schema SQL en Supabase

---

## 📸 Ejemplo Visual

```
ANTES DE EDITAR:
┌─────────────────────────────────────────────┐
│ SUPABASE_URL=https://REEMPLAZA-ESTO.supa... │ ❌
│ SUPABASE_ANON_KEY=eyJhbG...REEMPLAZA...     │ ❌
│ DATABASE_URL=postgresql://...REEMPLAZA...   │ ❌
└─────────────────────────────────────────────┘

DESPUÉS DE EDITAR:
┌─────────────────────────────────────────────┐
│ SUPABASE_URL=https://vxwyzmtq.supabase.co   │ ✅
│ SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5. │ ✅
│ DATABASE_URL=postgresql://postgres:mypas...  │ ✅
└─────────────────────────────────────────────┘
```

---

## ✅ Checklist Final

Después de editar, verifica:

- [ ] Edité `.env.local` en la raíz del proyecto
- [ ] Edité `backend/.env` también
- [ ] No hay ningún "REEMPLAZA" en los archivos
- [ ] Las URLs y keys son largas y reales
- [ ] Guardé los archivos (Ctrl+S)
- [ ] Ejecuté `python3 test_connection.py` y pasó ✅

---

¿Listo? ¡Edita los archivos y prueba la conexión! 🚀