# Resolución: Sales Sync Silent Failure (Feb 2026)

> **Fecha:** 2026-02-10
> **Autor:** Claude Code (Opus 4.6)
> **Estado:** ✅ Completado y verificado en producción
> **Impacto:** Dashboard mostraba $5.4M en Feb 2026 vs $11M real (-49.5%)

---

## Resumen

El sync diario de ventas desde RelBase estuvo fallando silenciosamente desde el 5 de febrero de 2026. GitHub Actions reportaba "success" (HTTP 200) pero **cero órdenes se creaban**. El dashboard quedó congelado en $5.398.685. Se identificaron y corrigieron 5 bugs en cadena.

---

## Problema Original

### Síntoma
- Dashboard mostraba Feb 2026: **$5.4M** (datos solo hasta Feb 5)
- Feb 2025 al mismo punto: **$17.4M** (-68.9% aparente)
- GitHub Actions daily-sync reportaba éxito todos los días
- Railway logs mostraban FK violations en cada DTE

### Cadena de Causa Raíz

```
Bug 1: channel_id FK violation en primer DTE
    ↓
Bug 2: Sin SAVEPOINT → transacción PostgreSQL envenenada
    ↓ Todos los DTEs subsiguientes fallan con "transaction aborted"
Bug 3: MV CONCURRENTLY refresh falla (sin unique index)
    ↓ Error handler no limpia transacción
Bug 4: sync_logs INSERT falla → excepción outer
    ↓ Respuesta: success=false pero HTTP 200
Bug 5: GitHub Actions solo verifica HTTP status code
    ↓ Reporta "success" cuando el sync falló completamente
```

---

## Bug 1: Wrong `channel_id` from `customers.assigned_channel_id`

### Evidencia (Railway logs)
```
Error processing DTE: insert or update on table "orders" violates foreign key
constraint "orders_channel_id_fkey"
DETAIL: Key (channel_id)=(1451) is not present in table "channels".
```

### Causa
Migration 029 almacenó `customer_channel_rules.channel_external_id` (ID externo de RelBase, ej. `1451`) en `customers.assigned_channel_id`. El sync Step 4 (`sync_service.py:950-962`) usaba este valor directamente como `orders.channel_id`, pero el FK espera el `channels.id` interno.

### Corrección
```python
# ANTES: usaba external ID directamente
SELECT assigned_channel_id FROM customers WHERE external_id = %s

# DESPUÉS: resuelve via JOIN a channels.id interno
SELECT ch.id
FROM customers cust
JOIN channels ch ON ch.external_id = cust.assigned_channel_id::text
                AND ch.source = 'relbase'
WHERE cust.external_id = %s AND cust.source = 'relbase'
```

**Archivo:** `backend/app/services/sync_service.py:953-967`

---

## Bug 2: Sin recovery de transacción por DTE

### Causa
`sync_service.py:1077-1080` capturaba la excepción y hacía `continue`, pero no emitía `ROLLBACK TO SAVEPOINT`. PostgreSQL rechaza todos los comandos SQL en una transacción abortada. Cada DTE subsiguiente fallaba con el mismo error en cascada.

### Corrección
```python
# SAVEPOINT al inicio de cada DTE
cursor.execute(f"SAVEPOINT sp_dte_{int(dte_id)}")

# ... procesamiento del DTE ...

# RELEASE en éxito
cursor.execute(f"RELEASE SAVEPOINT sp_dte_{int(dte_id)}")

# ROLLBACK TO SAVEPOINT en error
except Exception as e:
    cursor.execute(f"ROLLBACK TO SAVEPOINT sp_dte_{int(dte_id)}")
```

**Archivo:** `backend/app/services/sync_service.py:866-867, 1082-1093`

---

## Bug 3: MV refresh sin cleanup de transacción

### Causa
`REFRESH MATERIALIZED VIEW CONCURRENTLY` fallaba porque `sales_facts_mv` no tiene unique index (la MV tiene filas duplicadas por SKU por orden). El error handler capturaba la excepción Python pero **no hacía `conn.rollback()`**, dejando la transacción PostgreSQL abortada. El `INSERT INTO sync_logs` subsiguiente fallaba, propagando el error al except externo.

### Corrección
```python
except Exception as mv_error:
    conn.rollback()  # Limpiar transacción abortada
    # Fallback a refresh no-concurrente
    cursor.execute("REFRESH MATERIALIZED VIEW sales_facts_mv")
    conn.commit()
```

**Archivo:** `backend/app/services/sync_service.py:1130-1140`

---

## Bug 4: HTTP 200 en sync failure total

### Causa
El endpoint siempre retornaba HTTP 200, incluso con `success: false` y 0 órdenes creadas.

### Corrección
```python
if not result.success and result.orders_created == 0:
    return JSONResponse(status_code=500, content=response.model_dump())
```

**Archivo:** `backend/app/api/sync.py:187-190`

---

## Bug 5: GitHub Actions no verificaba campo `success`

### Causa
`daily-sync.yml:63` solo verificaba `HTTP_CODE >= 200 && < 300`. La variable `SUCCESS` (parseada en línea 55) nunca se validaba.

### Corrección
```bash
if [ "$SUCCESS" = "false" ] && [ "$ORDERS_CREATED" = "0" ]; then
    echo "::error::Sales sync returned success=false with 0 orders created"
    exit 1
fi
```

**Archivo:** `.github/workflows/daily-sync.yml:64-68`

---

## Cambios Adicionales (sesión paralela)

### Velocity SKU bug en inventario
Las subqueries de velocidad en `warehouses.py` usaban `original_sku` en lugar de `catalog_sku`, lo que omitía ventas de variantes (ANU-, _WEB, ML). Se corrigieron 4 subqueries y el endpoint de timeline en `sales_analytics.py`.

### Migration 037: Indexes en `sales_facts_mv`
```sql
CREATE INDEX idx_sales_mv_catalog_sku ON sales_facts_mv(catalog_sku);
CREATE INDEX idx_sales_mv_original_sku ON sales_facts_mv(original_sku);
CREATE INDEX idx_sales_mv_catalog_sku_date ON sales_facts_mv(catalog_sku, order_date) INCLUDE (units_sold);
```

---

## Verificación en Producción

### Deploy y backfill
1. Deploy v1 → Railway SUCCESS
2. Backfill Feb 1-9 → 38 órdenes nuevas, pero MV refresh falló (Bug 3)
3. Deploy v2 (fix MV handler) → Railway SUCCESS
4. Backfill retry → `success: true`, 143 órdenes actualizadas, 0 errores
5. Daily sync test (`days_back=1`) → `success: true`, 9 órdenes, 6.7s
6. MV manual refresh → 1.5s, completado

### Datos verificados
| Métrica | Antes | Después |
|---------|-------|---------|
| orders table (Feb 1-9) | 143 órdenes, $10.69M | Sin cambio (datos estaban OK) |
| sales_facts_mv (Feb 1-9) | 5 días, $5.40M | 9 días, $11.05M |
| YTD 2026 (MV) | Congelado | $49.19M |
| Daily sync | `success: false`, FK errors | `success: true`, 0 errors |

### Commit
```
a6da862 fix(sync,inventory): resolve silent sales sync failure and inventory velocity bugs
```

---

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `backend/app/services/sync_service.py` | FK JOIN, SAVEPOINTs, MV fallback |
| `backend/app/api/sync.py` | HTTP 500 on total failure |
| `.github/workflows/daily-sync.yml` | Check `success` field |
| `backend/app/api/warehouses.py` | 4 velocity subqueries → catalog_sku |
| `backend/app/api/sales_analytics.py` | Timeline endpoint → catalog_sku |
| `backend/migrations/037_add_catalog_sku_index_to_mv.sql` | 3 nuevos indexes |

---

## Nota: Unique Index para CONCURRENTLY

`REFRESH MATERIALIZED VIEW CONCURRENTLY` requiere un unique index sin WHERE clause. `sales_facts_mv` no tiene clave natural única (múltiples line items por orden con mismo SKU). El fallback non-concurrent (1.5s) es suficiente para el sync diario. Si se necesita CONCURRENTLY en el futuro, habría que agregar un `row_number()` a la definición de la MV.
