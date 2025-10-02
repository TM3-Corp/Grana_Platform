# ⚠️ FALTA SOLO LA CONTRASEÑA DE LA BASE DE DATOS

## ✅ Lo que ya está configurado:

- ✅ SUPABASE_URL
- ✅ SUPABASE_ANON_KEY
- ✅ SUPABASE_SERVICE_ROLE_KEY

## ❌ Lo que falta:

**Tu contraseña de la base de datos** para completar el `DATABASE_URL`

---

## 🔍 Cómo obtener/crear tu contraseña:

### Opción 1: Si la recuerdas
Si recuerdas la contraseña que pusiste cuando creaste el proyecto, úsala.

### Opción 2: Resetear la contraseña (RECOMENDADO)
1. Ve a Supabase
2. Settings → Database
3. Busca "Database Password"
4. Clic en "Reset Database Password"
5. Genera una nueva contraseña
6. **CÓPIALA INMEDIATAMENTE** (solo se muestra una vez)

---

## 📝 Cómo agregarla a los archivos:

Necesitas editar **2 archivos** y reemplazar `[YOUR-PASSWORD]` con tu contraseña real:

### Archivo 1:
```bash
nano /home/javier/Proyectos/Grana/grana-system/.env.local
```

Busca esta línea:
```
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.lypuvibmtxjaxmcmahxr.supabase.co:5432/postgres
```

Reemplaza `[YOUR-PASSWORD]` con tu contraseña, ejemplo:
```
DATABASE_URL=postgresql://postgres:miPassword123!@db.lypuvibmtxjaxmcmahxr.supabase.co:5432/postgres
```

Guarda: `Ctrl+O`, `Enter`, `Ctrl+X`

### Archivo 2:
```bash
nano /home/javier/Proyectos/Grana/grana-system/backend/.env
```

Haz lo mismo, guarda y sal.

---

## 🧪 Luego prueba la conexión:

```bash
cd /home/javier/Proyectos/Grana/grana-system/backend
python3 test_connection.py
```

Deberías ver ✅ en todos los pasos.

---

## 💡 Tip:

Si tu contraseña tiene caracteres especiales (!, @, #, $, etc.), puede que necesites "escaparlos" o ponerlos en formato URL-encoded:

| Carácter | Reemplazo |
|----------|-----------|
| `!` | `%21` |
| `@` | `%40` |
| `#` | `%23` |
| `$` | `%24` |
| `%` | `%25` |
| `&` | `%26` |

Ejemplo:
- Contraseña: `myPass!@#`
- En URL: `myPass%21%40%23`

**O más fácil:** Resetea la password y usa una sin caracteres especiales (solo letras y números).

---

## ✅ Cuando termines:

Ejecuta el test y avísame si todo pasa bien! 🚀