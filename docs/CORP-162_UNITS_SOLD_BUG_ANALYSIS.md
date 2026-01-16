# CORP-162: Análisis Completo del Bug units_sold en sales_facts_mv

> **Fecha de análisis:** 2026-01-14
> **Issue:** [CORP-162](https://linear.app/tm3ai/issue/CORP-162)
> **Severidad:** 🔴 Crítica
> **Estado:** Análisis completado, pendiente corrección

---

## Resumen Ejecutivo

El campo `units_sold` en la vista materializada `sales_facts_mv` **no aplica los factores de conversión** (`units_per_display`, `items_per_master_box`), causando que las unidades vendidas se reporten **17-99% por debajo** del valor real.

| Métrica | Valor |
|---------|-------|
| Cantidad original (raw) | 1,030,723 |
| `sales_facts_mv.units_sold` actual | 1,038,054 |
| Unidades REALES calculadas | **1,251,122** |
| **Unidades faltantes** | **-213,068 (-17%)** |

---

## 1. La Fórmula Incorrecta

### Ubicación
`supabase/migrations/20260114000001_fix_mv_pack_products.sql`, líneas 66-68

### Código Actual (INCORRECTO)
```sql
oi.quantity AS original_units_sold,
oi.quantity * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier::bigint, 1::bigint) AS units_sold,
```

### Lo Que Falta
```sql
-- La fórmula correcta debería ser:
units_sold = oi.quantity
    * COALESCE(sm_multiplier, 1)           -- ✅ Esto SÍ aplica
    * COALESCE(units_per_display, 1)       -- ❌ FALTA
    * COALESCE(items_per_master_box, 1)    -- ❌ FALTA
```

### Columnas Disponibles vs Usadas

| Columna | ¿Seleccionada en MV? | ¿Usada en units_sold? | ¿Debería usarse? |
|---------|:--------------------:|:---------------------:|:----------------:|
| `oi.quantity` | ✅ | ✅ | ✅ |
| `quantity_multiplier` | ✅ | ✅ | ✅ |
| `units_per_display` | ✅ | ❌ | ✅ |
| `items_per_master_box` | ✅ | ❌ | ✅ |

---

## 2. Ejemplos del Impacto

| SKU | Descripción | Qty Vendida | Factor Conversión | MV Calcula | Debería Ser | Error |
|-----|-------------|-------------|-------------------|------------|-------------|-------|
| BAKC_U04010 | Barra X1 | 100 | 1 | 100 | 100 | 0% ✅ |
| BAKC_U20010 | Barra X5 | 100 | 5 | 100 | **500** | **-80%** ❌ |
| GRAL_U16010 | Granola X16 | 10 | 16 | 10 | **160** | **-94%** ❌ |
| BAKC_C02810 | Caja Master (140 items) | 2 | 140 | 2 | **280** | **-99%** ❌ |

### Desglose por Categoría (del notebook de análisis)

| Categoría | Unidades Calculadas | % del Total |
|-----------|--------------------:|------------:|
| BARRAS | 775,471 | 62.0% |
| UNMAPPED | 371,911 | 29.7% |
| CRACKERS | 56,325 | 4.5% |
| KEEPERS | 27,939 | 2.2% |
| GRANOLAS | 19,476 | 1.6% |

---

## 3. Evidencia: Workaround Existente

El equipo ya conocía este problema. En `backend/app/api/audit.py` líneas 934-947:

```python
# ===== UNITS TOTALS FROM MV =====
# Get accurate unit totals from sales_facts_mv (applies conversion factors)
# This ensures consistency with Sales Analytics view
mv_units_query = """
    SELECT
        SUM(
            CASE
                WHEN is_caja_master THEN units_sold * COALESCE(items_per_master_box, 1)
                ELSE units_sold * COALESCE(units_per_display, 1)
            END
        ) as total_units
    FROM sales_facts_mv
    WHERE order_date >= %s AND order_date <= %s
"""
```

**El comentario "applies conversion factors"** demuestra conocimiento del bug.

### Aplicación Inconsistente del Workaround

| Endpoint | ¿Tiene Workaround? |
|----------|:------------------:|
| `/api/v1/audit/data` (totales) | ✅ Sí |
| `/api/v1/audit/export` | ❌ No |
| `/api/v1/sales-analytics/*` | ❌ No |
| `/api/v1/analytics/quarterly-breakdown` | ❌ No |
| `/api/v1/inventory-planning/*` | ❌ No |

---

## 4. Endpoints Afectados

### Backend (24+ ubicaciones)

| Archivo | Endpoint | Líneas | Propósito | Impacto |
|---------|----------|--------|-----------|---------|
| `sales_analytics.py` | `GET /api/v1/sales-analytics` | 219-526 | KPIs, timeline, top items | 🔴 Units incorrectos |
| `sales_analytics.py` | `GET /api/v1/sales-analytics/export` | 616-802 | Export Excel | 🔴 Units incorrectos |
| `analytics.py` | `GET /api/v1/analytics/quarterly-breakdown` | 89-142 | Breakdown trimestral | 🔴 Units incorrectos |
| `orders.py` | `GET /api/v1/orders/dashboard/executive-kpis` | 185-245 | Dashboard ejecutivo | 🟡 No muestra units |
| `audit.py` | `GET /api/v1/audit/data` | 937-963 | Desglose pedidos | 🟢 Tiene workaround |
| `audit.py` | `GET /api/v1/audit/export` | — | Export Excel | 🔴 Sin workaround |
| `inventory_planning.py` | `GET /api/v1/inventory-planning/production-recommendations` | 102-227 | Planificación producción | 🔴 Units incorrectos |
| `warehouses.py` | `GET /warehouse-inventory/.../summary` | 352-378 | Cobertura inventario | 🔴 Units incorrectos |
| `sales_analytics_olap.py` | `GET /api/v1/sales-analytics` (OLAP) | 161-215 | Analytics OLAP | 🔴 Units incorrectos |

### Operaciones de Refresh

| Archivo | Función | Propósito |
|---------|---------|-----------|
| `product_catalog.py` | `POST /reload` | Refresh MV tras cambios catálogo |
| `sku_mappings.py` | `POST /` | Refresh MV tras nuevos mappings |
| `sync_service.py` | `sync_orders()` | Refresh MV tras sync |
| `admin.py` | `POST /refresh-analytics` | Refresh manual |

---

## 5. Vistas Frontend Afectadas

| Ruta | Componente | Muestra Units | API Source | Estado |
|------|------------|:-------------:|------------|--------|
| `/dashboard/analytics` | KPI "Unidades Vendidas" | ✅ | `/sales-analytics` | 🔴 Incorrecto |
| `/dashboard/sales-analytics` | KPICards, Timeline, Tables | ✅ | `/sales-analytics` | 🔴 Incorrecto |
| `/dashboard/audit` | Total Unidades (agregado) | ✅ | `/audit/data` | 🟢 Workaround |
| `/dashboard/product-mapping` | Units per family/source | ✅ | Calculado frontend | 🟡 Depende |
| `/dashboard` (home) | Pie charts | ❌ | — | N/A |

### Componentes Específicos

| Componente | Archivo | Líneas | Campo Usado |
|------------|---------|--------|-------------|
| KPICards | `components/sales-analytics/KPICards.tsx` | 50-55 | `data.total_units` |
| TimelineChart | `components/sales-analytics/TimelineChart.tsx` | 111-364 | `total_units`, `by_group[].units` |
| TopItemsChart | `components/sales-analytics/TopItemsChart.tsx` | 8-33 | `units` |
| GroupedDataTable | `components/sales-analytics/GroupedDataTable.tsx` | 6-52 | `units` |
| AuditView | `components/AuditView.tsx` | 717-1438 | `unidades`, `totalUnidades` |

---

## 6. Cadena de Datos Completa

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLUJO DE DATOS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  order_items.quantity (cantidad pedida)                                     │
│        │                                                                    │
│        ▼                                                                    │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │ sku_mappings    │     │ product_catalog │     │ product_catalog │       │
│  │ quantity_       │     │ units_per_      │     │ items_per_      │       │
│  │ multiplier      │     │ display         │     │ master_box      │       │
│  │ (para PACKS)    │     │ (X1=1, X5=5...) │     │ (CM=140...)     │       │
│  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘       │
│           │                       │                       │                 │
│           │ ✅ APLICA             │ ❌ NO APLICA          │ ❌ NO APLICA    │
│           ▼                       ▼                       ▼                 │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    sales_facts_mv.units_sold                     │       │
│  │                                                                  │       │
│  │   ACTUAL:   qty × multiplier                                     │       │
│  │   CORRECTO: qty × multiplier × units_per_display                 │       │
│  │                             (o × items_per_master_box)           │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                    │                                        │
│           ┌────────────────────────┼────────────────────────┐              │
│           ▼                        ▼                        ▼              │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐    │
│  │/sales-analytics │      │/analytics       │      │/inventory-      │    │
│  │                 │      │/quarterly       │      │planning         │    │
│  │ units: -17%     │      │ units: -17%     │      │ units: -17%     │    │
│  └────────┬────────┘      └────────┬────────┘      └────────┬────────┘    │
│           │                        │                        │              │
│           ▼                        ▼                        ▼              │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐    │
│  │ Sales Analytics │      │ Analytics Page  │      │ Inventory       │    │
│  │ Dashboard       │      │                 │      │ Planning        │    │
│  │                 │      │                 │      │                 │    │
│  │ KPIs INCORRECTOS│      │ Charts          │      │ Producción      │    │
│  │ Timeline        │      │ INCORRECTOS     │      │ MAL CALCULADA   │    │
│  │ INCORRECTO      │      │                 │      │                 │    │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Comparación con Implementación Python Correcta

### ProductCatalogService.calculate_units()
`backend/app/services/product_catalog_service.py`, líneas 220-295

```python
def calculate_units(self, sku: str, quantity: int, source: str = None) -> int:
    """
    Formula: Units = Quantity × SKU Mapping Multiplier × Target SKU Conversion Factor
    """

    # Paso 1: Verificar sku_mappings
    mapping_result = mapping_service.map_sku(sku, source)

    if mapping_result:
        multiplier = mapping_result.quantity_multiplier or 1
        target_sku = mapping_result.target_sku

        # Obtener factor de conversión del catálogo
        target_conversion = 1
        if target_sku in catalog:
            target_conversion = catalog[target_sku].get('units_per_display', 1) or 1
        elif target_sku in self._master_sku_lookup:
            target_conversion = self._master_sku_lookup[target_sku].get('items_per_master_box', 1) or 1

        return quantity * multiplier * target_conversion  # ← FÓRMULA COMPLETA

    # Paso 2: Match directo en catálogo
    if sku in catalog:
        conversion_factor = catalog[sku].get('units_per_display', 1)
        return quantity * (conversion_factor or 1)  # ← APLICA CONVERSIÓN

    # Paso 3: Match en Caja Master
    if sku in self._master_sku_lookup:
        conversion_factor = self._master_sku_lookup[sku].get('items_per_master_box', 1)
        return quantity * (conversion_factor or 1)  # ← APLICA CONVERSIÓN

    return quantity * 1
```

### Diferencia Clave

| Paso | Python (correcto) | SQL MV (incorrecto) |
|------|-------------------|---------------------|
| Qty base | ✅ | ✅ |
| × quantity_multiplier | ✅ | ✅ |
| × units_per_display | ✅ | ❌ **FALTA** |
| × items_per_master_box | ✅ | ❌ **FALTA** |

---

## 8. Impacto en el Negocio

| Área | Impacto | Severidad |
|------|---------|:---------:|
| **Dashboard KPIs** | Unidades vendidas subreportadas 17-99% | 🔴 |
| **Sales Analytics** | Gráficos de volumen incorrectos | 🔴 |
| **Inventory Planning** | Producción calculada con datos erróneos | 🔴 |
| **Warehouse Coverage** | Días de cobertura mal calculados | 🔴 |
| **Excel Exports** | Reportes con datos erróneos entregados a stakeholders | 🟡 |
| **Decisiones de Negocio** | Proyecciones basadas en datos 17-99% incorrectos | 🔴 |

---

## 9. Solución Propuesta

### Modificar la definición del MV

```sql
-- ANTES (incorrecto):
oi.quantity * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1) AS units_sold

-- DESPUÉS (correcto):
oi.quantity
    * COALESCE(sm_agg.total_multiplier, sm_single.quantity_multiplier, 1)
    * CASE
        WHEN (pc_master.sku IS NOT NULL OR pc_mapped_master.sku IS NOT NULL)
            THEN COALESCE(
                pc_master.items_per_master_box,
                pc_mapped_master.items_per_master_box,
                1
            )
        ELSE
            COALESCE(
                pc_direct.units_per_display,
                pc_mapped.units_per_display,
                1
            )
      END AS units_sold
```

### Pasos de Implementación

1. Crear nueva migración con la corrección
2. Aplicar en entorno local y verificar números
3. Comparar con valores del notebook de análisis
4. Eliminar workaround de audit.py (ya no será necesario)
5. Aplicar en producción
6. Refrescar MV: `REFRESH MATERIALIZED VIEW sales_facts_mv`

---

## 10. Archivos Relacionados

### Backend
- `backend/app/api/audit.py` - Workaround existente
- `backend/app/api/sales_analytics.py` - Endpoint afectado
- `backend/app/api/analytics.py` - Endpoint afectado
- `backend/app/api/inventory_planning.py` - Endpoint afectado
- `backend/app/services/product_catalog_service.py` - Implementación correcta

### Database
- `supabase/migrations/20260114000001_fix_mv_pack_products.sql` - Definición actual MV
- `supabase/migrations/20260109143335_remote_schema.sql` - Schema base

### Frontend
- `frontend/app/dashboard/sales-analytics/page.tsx`
- `frontend/app/dashboard/analytics/page.tsx`
- `frontend/components/sales-analytics/KPICards.tsx`
- `frontend/components/AuditView.tsx`

### Notebooks de Análisis
- `.claude_sessions/orders_units_analysis.ipynb` - Verificación numérica

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2026-01-14 | Análisis inicial completado |
| 2026-01-14 | Verificación numérica via notebooks |
| 2026-01-14 | Mapeo completo de endpoints y frontend afectados |
