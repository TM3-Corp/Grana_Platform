# 🚀 Guía Rápida de Desarrollo

## 🎯 Comandos Esenciales

### **Opción 1: Levantar todo de una vez (RECOMENDADO)**

```bash
# Desde la raíz del proyecto
./dev.sh
```

Esto levanta:
- ✅ Backend en http://localhost:8000
- ✅ Frontend en http://localhost:3000
- ✅ Logs en tiempo real

Para detener: **Ctrl+C** o usa `./stop.sh`

---

### **Opción 2: Levantar manualmente (si prefieres control individual)**

```bash
# Terminal 1: Backend
cd backend
./run.sh

# Terminal 2: Frontend
cd frontend
npm run dev
```

---

## 📍 URLs Importantes

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Frontend** | http://localhost:3000 | Dashboard principal |
| **Backend API** | http://localhost:8000 | API REST |
| **API Docs** | http://localhost:8000/docs | Swagger UI interactivo |
| **Health Check** | http://localhost:8000/health | Verificar backend |

---

## 🛑 Detener Servicios

```bash
# Opción 1: Si usaste ./dev.sh
# Presiona Ctrl+C

# Opción 2: Detener todo
./stop.sh

# Opción 3: Detener manualmente por puerto
lsof -ti:3000 | xargs kill  # Frontend
lsof -ti:8000 | xargs kill  # Backend
```

---

## 📊 Ver Logs

```bash
# Backend
tail -f /tmp/grana_backend.log

# Frontend
tail -f /tmp/grana_frontend.log

# Ambos en paralelo
tail -f /tmp/grana_backend.log /tmp/grana_frontend.log
```

---

## 🔧 Troubleshooting

### Backend no levanta

```bash
# Verificar que el venv exista
ls backend/venv/

# Si no existe, créalo:
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Puerto ocupado

```bash
# Ver qué está usando el puerto
lsof -i:3000  # Frontend
lsof -i:8000  # Backend

# Matar el proceso
lsof -ti:3000 | xargs kill
```

### Base de datos no conecta

```bash
# Verificar que DATABASE_URL esté configurado
cat backend/.env | grep DATABASE_URL

# Test de conexión
curl http://localhost:8000/api/v1/test-db
```

---

## 📦 Estructura del Proyecto

```
Grana_Platform/
├── backend/              # FastAPI (Python)
│   ├── app/             # Código de la API
│   ├── venv/            # Virtual environment
│   └── run.sh           # Script de inicio
├── frontend/            # Next.js (TypeScript)
│   ├── app/             # App Router de Next.js
│   ├── components/      # Componentes React
│   ├── public/          # Assets estáticos
│   └── package.json     # Dependencias del frontend
├── dev.sh              # ⭐ Levantar todo
└── stop.sh             # ⭐ Detener todo
```

---

## 💡 Tips Rápidos

1. **Hot Reload:** Ambos servicios tienen hot reload automático
2. **CORS:** Ya está configurado para localhost
3. **Database:** Usa Session Pooler de Supabase (IPv4 compatible con WSL2)
4. **Git Hooks:** Pre-commit hook previene commits de archivos de sesión

---

## 🐛 Debug Común

### "Module not found" en Frontend
```bash
cd frontend
npm install
```

### "ENOENT: package.json not found"
```bash
# Asegúrate de correr npm desde frontend/, no desde la raíz
cd frontend
npm run dev
```

### "Module not found" en Backend
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Database SSL errors
```bash
# Reiniciar backend
./stop.sh
./dev.sh
```

---

## 📞 Ayuda

Si algo no funciona, verifica:
1. ✅ Estás en la raíz del proyecto (`~/Proyectos/Grana/Grana_Platform/`)
2. ✅ Los puertos 3000 y 8000 están libres
3. ✅ El backend tiene `venv/` creado
4. ✅ El archivo `backend/.env` existe y tiene `DATABASE_URL`
