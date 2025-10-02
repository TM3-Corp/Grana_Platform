# 🗄️ Setup de Supabase - Base de Datos PostgreSQL

## 🎯 Objetivo
Configurar PostgreSQL en Supabase como "Single Source of Truth" con auditoría completa.

---

## ⏱️ Tiempo Estimado: 15 minutos

---

## 📋 PASO 1: Crear Cuenta en Supabase

### 1.1 Ir a Supabase
```
🌐 https://supabase.com
```

### 1.2 Sign Up
- Clic en "Start your project"
- Usa tu email de trabajo o GitHub
- Verifica tu email

---

## 📋 PASO 2: Crear Nuevo Proyecto

### 2.1 New Project
- Clic en "New Project"
- Llenar datos:

```
Project Name:      grana-production
Database Password: [GENERA UNO FUERTE - GUÁRDALO]
Region:            South America (São Paulo)
Pricing Plan:      Free (de momento)
```

**⚠️ IMPORTANTE**: Guarda la contraseña de DB en un lugar seguro. La necesitarás.

### 2.2 Esperar creación
- Toma ~2 minutos
- Verás pantalla de "Setting up your project..."
- ☕ Toma un café

---

## 📋 PASO 3: Ejecutar Schema SQL

### 3.1 Ir a SQL Editor
- En el menú lateral, clic en "SQL Editor"
- Clic en "New query"

### 3.2 Copiar y Ejecutar Schema
- Abrir archivo: `/home/javier/Proyectos/Grana/grana-system/docs/database-schema.sql`
- Copiar TODO el contenido (Ctrl+A, Ctrl+C)
- Pegar en SQL Editor de Supabase
- Clic en "Run" (o Ctrl+Enter)

**Deberías ver:**
```
Success. No rows returned
```

### 3.3 Verificar Tablas Creadas
- En menú lateral, clic en "Table Editor"
- Deberías ver todas las tablas:
  - customers
  - products
  - channels
  - orders ⭐
  - order_items
  - orders_audit ⭐⭐⭐
  - manual_corrections
  - inventory_movements
  - sync_logs
  - alerts

---

## 📋 PASO 4: Obtener Credenciales de Conexión

### 4.1 Ir a Settings
- Menú lateral → "Project Settings"
- Clic en "Database"

### 4.2 Copiar Connection String
Verás algo como:
```
postgresql://postgres:[YOUR-PASSWORD]@db.abcdefghijklmnop.supabase.co:5432/postgres
```

### 4.3 Obtener API Keys
- Menú lateral → "Project Settings"
- Clic en "API"
- Copiar:
  - `Project URL`: https://abcdefghijklmnop.supabase.co
  - `anon public key`: eyJhbGc...
  - `service_role key`: eyJhbGc... (⚠️ SECRETO - nunca expongas)

---

## 📋 PASO 5: Guardar Credenciales

### 5.1 Crear archivo de credenciales
Crear archivo: `/home/javier/Proyectos/Grana/grana-system/.env.local`

```bash
# Supabase Credentials
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.abcdefghijklmnop.supabase.co:5432/postgres
```

**⚠️ IMPORTANTE**:
- Reemplaza `[PASSWORD]` con tu contraseña real
- NO subas este archivo a Git
- Ya está en `.gitignore`

---

## 📋 PASO 6: Verificar que Funciona

### 6.1 Test desde SQL Editor
En Supabase SQL Editor, ejecuta:

```sql
-- Ver canales predefinidos
SELECT * FROM channels;

-- Deberías ver 8 canales:
-- web_shopify, marketplace_ml, retail_walmart, etc.
```

### 6.2 Crear un cliente de prueba
```sql
INSERT INTO customers (rut, name, email, source)
VALUES ('76221779-1', 'GRANA SPA', 'macarena@grana.cl', 'system');

SELECT * FROM customers;
```

### 6.3 Crear un pedido de prueba
```sql
-- Primero obtener el ID del customer
SELECT id FROM customers WHERE rut = '76221779-1';

-- Crear pedido (reemplaza CUSTOMER_ID con el ID que obtuviste)
INSERT INTO orders (
    order_number,
    source,
    customer_id,
    channel_id,
    total,
    order_date
)
VALUES (
    'TEST-001',
    'manual',
    1,  -- Reemplaza con el ID real
    1,  -- web_shopify
    150000,
    NOW()
);

SELECT * FROM orders;
```

### 6.4 Probar Auditoría (LO MÁS IMPORTANTE)
```sql
-- Editar el pedido (cambiar canal)
UPDATE orders
SET channel_id = 6,  -- emporio
    is_corrected = true,
    corrected_by = 'macarena@grana.cl',
    corrected_at = NOW(),
    correction_reason = 'Error de captura, era venta directa'
WHERE order_number = 'TEST-001';

-- Ver que se registró en auditoría ⭐
SELECT * FROM orders_audit
ORDER BY changed_at DESC;

-- Deberías ver el cambio registrado automáticamente!
```

---

## ✅ PASO 7: Configurar Row Level Security (RLS)

### 7.1 Deshabilitar RLS temporalmente (para desarrollo)
```sql
-- Durante desarrollo, deshabilitar RLS
ALTER TABLE customers DISABLE ROW LEVEL SECURITY;
ALTER TABLE products DISABLE ROW LEVEL SECURITY;
ALTER TABLE orders DISABLE ROW LEVEL SECURITY;
ALTER TABLE order_items DISABLE ROW LEVEL SECURITY;
ALTER TABLE orders_audit DISABLE ROW LEVEL SECURITY;
ALTER TABLE manual_corrections DISABLE ROW LEVEL SECURITY;
ALTER TABLE channels DISABLE ROW LEVEL SECURITY;
ALTER TABLE sync_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE alerts DISABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_movements DISABLE ROW LEVEL SECURITY;
```

**Nota:** Más adelante, cuando implementemos autenticación, habilitaremos RLS con políticas específicas.

---

## 📋 PASO 8: Explorar Dashboard de Supabase

### 8.1 Table Editor
- Navega entre tablas
- Edita registros manualmente si quieres
- Muy útil para debugging

### 8.2 Database
- Ver schema visual
- Ver relaciones entre tablas
- Explorar índices

### 8.3 Storage
- Por ahora vacío
- Más adelante: logos, documentos, PDFs de facturas

---

## 🎉 ¡Setup Completo!

### Checklist Final:
- [ ] ✅ Cuenta Supabase creada
- [ ] ✅ Proyecto "grana-production" creado
- [ ] ✅ Schema SQL ejecutado sin errores
- [ ] ✅ Todas las tablas visibles en Table Editor
- [ ] ✅ Credenciales guardadas en `.env.local`
- [ ] ✅ Test de inserción funcionando
- [ ] ✅ Trigger de auditoría funcionando

---

## 🚀 Próximos Pasos

Ahora que tienes la base de datos lista, continúa con:

**[02-RAILWAY-SETUP.md](./02-RAILWAY-SETUP.md)** - Configurar el backend en Railway

---

## 🆘 Troubleshooting

### Error: "relation 'orders' does not exist"
**Solución:** El schema no se ejecutó correctamente. Vuelve a ejecutarlo.

### Error: "password authentication failed"
**Solución:** La contraseña en `DATABASE_URL` es incorrecta. Cópiala de nuevo.

### Error: "permission denied for table"
**Solución:** Estás usando `anon` key en lugar de `service_role` key. Usa la correcta.

### No veo los triggers funcionando
**Solución:**
```sql
-- Verificar que existen
SELECT * FROM pg_trigger WHERE tgname LIKE 'audit%';
```

---

## 📞 Notas Importantes

1. **Plan Gratuito**: Incluye:
   - 500MB de base de datos
   - 2GB de bandwidth
   - 50MB de storage
   - **Suficiente para Grana por 6+ meses**

2. **Cuando Migrar a Pro ($25/mes)**:
   - >500MB de datos (~50,000+ pedidos)
   - >2GB bandwidth/mes
   - Necesitas backups diarios (incluidos en Pro)

3. **Backups**:
   - Plan gratuito: backups cada 7 días
   - Plan Pro: backups diarios + Point-in-Time Recovery

4. **Performance**:
   - Plan gratuito: compartido
   - Plan Pro: dedicated CPU
   - **Para Grana, gratuito es suficiente**

---

## 🔒 Seguridad

### Credenciales que NUNCA expongas:
- ❌ `service_role` key (puede hacer CUALQUIER cosa)
- ❌ `DATABASE_URL` con contraseña

### Credenciales que SÍ puedes usar en frontend:
- ✅ `SUPABASE_URL` (pública)
- ✅ `anon` key (limitada por RLS)

---

¿Listo? ✅ Continúa con [02-RAILWAY-SETUP.md](./02-RAILWAY-SETUP.md)