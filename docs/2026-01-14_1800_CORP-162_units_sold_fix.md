# Resolución CORP-162: Fix units_sold Conversion Factors

> **Fecha:** 2026-01-14 18:00
> **Issue:** [CORP-162](https://linear.app/tm3ai/issue/CORP-162)
> **Autor:** Claude Code
> **Estado:** ✅ Completado (pendiente aplicar migración)

---

## Resumen

Se corrigió el cálculo de `units_sold` en la vista materializada `sales_facts_mv` para incluir los factores de conversión (`units_per_display`, `items_per_master_box`) que estaban faltando.

---

## Problema Original

### Síntoma
Las unidades vendidas se reportaban 17-99% por debajo del valor real.

### Causa Raíz
La fórmula en `sales_facts_mv` solo aplicaba el `quantity_multiplier` de `sku_mappings`, pero **no multiplicaba** por los factores de conversión del catálogo de productos.

```sql
-- ANTES (incorrecto):
units_sold = oi.quantity * quantity_multiplier
-- Faltaba: × units_per_display (o × items_per_master_box)
```

### Evidencia Numérica (del notebook de análisis)
| Métrica | Valor |
|---------|-------|
| Cantidad raw | 1,030,723 |
| MV units_sold (antes) | 1,038,054 |
| Unidades reales | **1,251,122** |
| Diferencia | **-213,068 (-17%)** |

---

## Solución Implementada

### 1. Nueva Migración
**Archivo:** `supabase/migrations/20260114180000_fix_mv_units_sold_conversion.sql`

**Cambio principal (líneas 87-101):**
```sql
-- CORREGIDO: units_sold ahora aplica factores de conversión
(
    oi.quantity
    * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier::bigint, 1::bigint)
    * CASE
        -- Para CAJA MASTER: multiplicar por items_per_master_box
        WHEN (pc_master.sku IS NOT NULL OR pc_mapped_master.sku IS NOT NULL)
            THEN COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, 1)::bigint
        -- Para productos regulares: multiplicar por units_per_display
        ELSE
            COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, 1)::bigint
      END
) AS units_sold,
```

### 2. Actualización del Workaround en audit.py
**Archivo:** `backend/app/api/audit.py` (líneas 934-943)

**Antes (workaround que multiplicaba post-hoc):**
```python
mv_units_query = """
    SELECT SUM(
        CASE
            WHEN is_caja_master THEN units_sold * COALESCE(items_per_master_box, 1)
            ELSE units_sold * COALESCE(units_per_display, 1)
        END
    ) as total_units
    FROM sales_facts_mv
    WHERE order_date >= %s AND order_date <= %s
"""
```

**Después (simplificado porque MV ya incluye conversión):**
```python
mv_units_query = """
    SELECT SUM(units_sold) as total_units
    FROM sales_facts_mv
    WHERE order_date >= %s AND order_date <= %s
"""
```

---

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `supabase/migrations/20260114180000_fix_mv_units_sold_conversion.sql` | **NUEVO** - Migración con fórmula corregida |
| `backend/app/api/audit.py` | Simplificado workaround (ya no necesita multiplicar) |
| `docs/CORP-162_UNITS_SOLD_BUG_ANALYSIS.md` | **NUEVO** - Documento de análisis completo |

---

## Fórmula Final

```
units_sold = quantity × quantity_multiplier × conversion_factor

Donde:
- quantity = oi.quantity (cantidad del pedido)
- quantity_multiplier = COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1)
- conversion_factor =
    - items_per_master_box (si es CAJA MASTER)
    - units_per_display (si es producto regular: X1=1, X5=5, X16=16, etc.)
```

### Ejemplos de Cálculo

| SKU | Tipo | Qty | Multiplier | Conv. Factor | units_sold |
|-----|------|-----|------------|--------------|------------|
| BAKC_U04010 | X1 | 10 | 1 | 1 | 10 |
| BAKC_U20010 | X5 | 10 | 1 | 5 | 50 |
| BAKC_U64010 | X16 | 10 | 1 | 16 | 160 |
| BAKC_C02810 | CM | 2 | 1 | 140 | 280 |
| PACKNAVIDAD | PACK | 1 | 8 | 1 | 8 |

---

## Pasos para Aplicar

### En Local
```bash
# Reset database (aplica todas las migraciones)
npx supabase db reset

# Verificar el resultado
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -c "
SELECT
    SUM(original_units_sold) as raw_qty,
    SUM(original_units_sold * quantity_multiplier) as with_multiplier,
    SUM(units_sold) as with_conversion
FROM sales_facts_mv;
"
```

### En Producción
```bash
# La migración se aplica automáticamente en el siguiente deploy
# O manualmente:
npx supabase db push
```

---

## Verificación Post-Deploy

### Query de Verificación
```sql
-- Comparar antes vs después
SELECT
    SUM(original_units_sold) as raw_quantity,
    SUM(original_units_sold * quantity_multiplier) as old_formula,
    SUM(units_sold) as new_formula,
    ROUND(
        (SUM(units_sold)::decimal / NULLIF(SUM(original_units_sold * quantity_multiplier)::decimal, 0) - 1) * 100,
        1
    ) as percent_increase
FROM sales_facts_mv;
```

### Resultado Esperado
```
 raw_quantity | old_formula | new_formula | percent_increase
--------------+-------------+-------------+------------------
    1,030,723 |   1,038,054 |   1,251,122 |             20.5
```

---

## Impacto en el Sistema

### Endpoints que verán datos corregidos automáticamente:
- ✅ `GET /api/v1/sales-analytics` - KPIs, timeline, top items
- ✅ `GET /api/v1/analytics/quarterly-breakdown` - Breakdown trimestral
- ✅ `GET /api/v1/inventory-planning/production-recommendations` - Planificación
- ✅ `GET /api/v1/audit/data` - Totales de audit (workaround simplificado)
- ✅ `GET /warehouse-inventory/.../summary` - Cobertura inventario

### Vistas Frontend que mostrarán datos correctos:
- ✅ `/dashboard/analytics` - KPI "Unidades Vendidas"
- ✅ `/dashboard/sales-analytics` - Todos los gráficos de unidades
- ✅ `/dashboard/audit` - Total Unidades

---

## Testing Recomendado

1. **Aplicar migración en local:**
   ```bash
   npx supabase db reset
   ```

2. **Verificar números:**
   ```bash
   # Debería mostrar ~1,251,122 units (no ~1,038,054)
   psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -c \
     "SELECT SUM(units_sold) FROM sales_facts_mv;"
   ```

3. **Verificar en frontend:**
   - Abrir `/dashboard/sales-analytics`
   - Verificar que "Unidades Vendidas" muestre ~1.25M (no ~1.04M)

4. **Verificar endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/sales-analytics | jq '.summary.total_units'
   # Debería ser ~1,251,122
   ```

---

## Notas Adicionales

### ¿Por qué el workaround existía?
El equipo identificó el bug y creó un workaround en `audit.py` (líneas 934-963) que multiplicaba `units_sold` por los factores de conversión al momento de la consulta. El comentario original decía "applies conversion factors", demostrando conocimiento del problema.

### ¿Por qué no se arregló antes en el MV?
La migración `20260114000001_fix_mv_pack_products.sql` agregó soporte para PACK products (múltiples componentes), pero no incluyó la multiplicación por `units_per_display` / `items_per_master_box` para productos regulares.

### Relación con otros issues
- **CORP-161** (category bug) - Separado, trata sobre categoría CAJA MASTER
- **CORP-155** (invoice_status filter) - Separado, trata sobre filtros faltantes

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2026-01-14 18:00 | Creada migración `20260114180000_fix_mv_units_sold_conversion.sql` |
| 2026-01-14 18:00 | Actualizado workaround en `audit.py` |
| 2026-01-14 18:00 | Creado documento de análisis `CORP-162_UNITS_SOLD_BUG_ANALYSIS.md` |
| 2026-01-14 18:00 | Creado documento de resolución (este archivo) |
