# Análisis de Problemas Críticos del Sistema

> **Fecha de análisis:** 2026-01-14
> **Última actualización:** 2026-02-10
> **Método:** Análisis multi-agente línea por línea del código fuente
> **Estado:** 4 resueltos, 1 pendiente

---

## Resumen Ejecutivo

Se identificaron y confirmaron **5 problemas críticos** en el sistema:

| # | Problema | Severidad | Estado | Issue |
|---|----------|-----------|--------|-------|
| 1 | `sales_facts_mv.units_sold` no aplica factores de conversión | 🔴 Crítico | ✅ **RESUELTO** | CORP-162 |
| 2 | Totales del audit ignoran filtros de categoría/canal/cliente | 🔴 Crítico | ✅ **RESUELTO** | CORP-155 |
| 3 | Tres sistemas de mapeo con diferente cobertura | 🔴 Crítico | 🔴 Pendiente | — |
| 4 | Sales sync silenciosamente fallando (5 bugs en cadena) | 🔴 Crítico | ✅ **RESUELTO** | — |
| 5 | Velocity subqueries usan `original_sku` en vez de `catalog_sku` | 🟡 Alto | ✅ **RESUELTO** | — |

---

## Problema #1: `sales_facts_mv.units_sold` No Calcula Unidades Correctamente

> ✅ **RESUELTO** - Migración `20260114180000_fix_mv_units_sold_conversion.sql`
> 📄 **Documentación:** `docs/2026-01-14_1800_CORP-162_units_sold_fix.md`

### Contexto del Negocio

Grana vende productos en diferentes presentaciones:
- **Unitario (X1)**: 1 barra
- **Display X5**: 5 barras en un pack
- **Display X16**: 16 barras
- **Caja Master**: 140 barras

Cuando se vende "10 displays X5", el sistema debe reportar **50 unidades** (10 × 5).

### Código Incorrecto

**Archivo:** `supabase/migrations/20260109143335_remote_schema.sql`
**Líneas:** 1703-1704

```sql
"oi"."quantity" AS "original_units_sold",
("oi"."quantity" * COALESCE("sm"."quantity_multiplier", 1)) AS "units_sold",
```

**Fórmula actual (incorrecta):**
```
units_sold = cantidad × multiplicador_mapeo
```

**Lo que falta:** Multiplicar por `units_per_display` o `items_per_master_box`.

### Código Correcto (Referencia)

**Archivo:** `backend/app/services/product_catalog_service.py`
**Líneas:** 220-295

```python
def calculate_units(self, sku: str, quantity: int, source: str = None) -> int:
    """
    Formula: Units = Quantity × SKU Mapping Multiplier × Target SKU Conversion Factor

    Examples:
        - BAKC_U04010 (X1): 10 × 1 = 10 bars
        - BAKC_U20010 (X5): 10 × 5 = 50 bars
        - BAKC_C02810 (CM): 2 × 140 = 280 bars
    """

    # Paso 1: Verificar si hay mapping en sku_mappings
    mapping_result = mapping_service.map_sku(sku, source)

    if mapping_result:
        multiplier = mapping_result.quantity_multiplier or 1
        target_sku = mapping_result.target_sku

        # Obtener factor de conversión del catálogo
        target_conversion = 1
        if target_sku in catalog:
            target_conversion = catalog[target_sku].get('units_per_display', 1) or 1
        elif self._master_sku_lookup and target_sku in self._master_sku_lookup:
            target_conversion = self._master_sku_lookup[target_sku].get('items_per_master_box', 1) or 1

        # Fórmula completa
        return quantity * multiplier * target_conversion

    # Paso 2: Match directo en catálogo
    if sku in catalog:
        conversion_factor = catalog[sku].get('units_per_display', 1)
        return quantity * (conversion_factor or 1)

    # Paso 3: Match en Caja Master
    if self._master_sku_lookup and sku in self._master_sku_lookup:
        conversion_factor = self._master_sku_lookup[sku].get('items_per_master_box', 1)
        return quantity * (conversion_factor or 1)

    # Paso 4: SKU no encontrado
    return quantity * 1
```

**Fórmula correcta:**
```
unidades = cantidad × multiplicador_mapeo × factor_conversión
```

### Evidencia: Comparación de Resultados

| SKU | Descripción | Cantidad | Factor | MV Calcula | Debería Ser | Error |
|-----|-------------|----------|--------|------------|-------------|-------|
| BAKC_U04010 | Barra X1 | 10 | 1 | 10 | 10 | 0% ✅ |
| BAKC_U20010 | Barra X5 | 10 | 5 | 10 | **50** | -80% ❌ |
| BAKC_U64010 | Barra X16 | 10 | 16 | 10 | **160** | -94% ❌ |
| BAKC_C02810 | Caja Master | 2 | 140 | 2 | **280** | -99% ❌ |

### Evidencia: Workaround Existente

El equipo ya conocía este problema. En `audit.py` líneas 959-978 existe un parche:

```python
mv_units_query_with_dates = """
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

Este query **multiplica `units_sold` por el factor de conversión al momento de consultar**, demostrando conocimiento del bug.

### Impacto

- **Dashboard Ejecutivo:** KPIs de unidades vendidas incorrectos
- **Sales Analytics:** Gráficos de volumen subreportados
- **Reportes:** Exportaciones con datos erróneos
- **Decisiones de Negocio:** Proyecciones basadas en datos 80-99% incorrectos

### Solución Propuesta

Modificar la definición de la MV:

```sql
-- ANTES (incorrecto):
("oi"."quantity" * COALESCE("sm"."quantity_multiplier", 1)) AS "units_sold"

-- DESPUÉS (correcto):
("oi"."quantity"
  * COALESCE("sm"."quantity_multiplier", 1)
  * CASE
      WHEN ("pc_master"."sku" IS NOT NULL OR "pc_mapped_master"."sku" IS NOT NULL)
        THEN COALESCE("items_per_master_box", 1)
      ELSE
        COALESCE("units_per_display", 1)
    END
) AS "units_sold"
```

---

## Problema #2: Totales del Audit Ignoran Filtros

> ✅ **RESUELTO** - Actualizado mv_units_query en audit.py
> 📄 **Documentación:** `docs/2026-01-14_1930_CORP-155_invoice_status_fix.md`

### Contexto

La vista "Desglose de Pedidos" (`/api/v1/audit/data`) permite filtrar por:
- Categoría (BARRAS, CRACKERS, GRANOLAS, KEEPERS)
- Canal (CORPORATIVO, ECOMMERCE, MERCADO LIBRE)
- Cliente
- Fechas
- Source (relbase, shopify, mercadolibre)

Cuando el usuario aplica un filtro, **todos los números deberían reflejarlo**.

### Código de Filtros para Filas

**Archivo:** `backend/app/api/audit.py`
**Líneas:** 361-476

```python
# Construcción de where_sql con TODOS los filtros

# Línea 365 - Filtro base
where_clauses = ["o.source = 'relbase'"]

# Línea 369 - Estado de factura
where_clauses.append("o.invoice_status IN ('accepted', 'accepted_objection')")

# Líneas 381-418 - Categoría
if category:
    # Obtiene SKUs de la categoría del catálogo
    skus_for_category = [sku for sku, info in product_map.items()
                         if info.get('category') == category]
    where_clauses.append(f"UPPER(oi.product_sku) IN ({skus_list})")

# Líneas 420-425 - Canal
if channel:
    where_clauses.append("ch.name ILIKE %s")
    params.append(f"%{channel}%")

# Líneas 427-432 - Cliente
if customer:
    where_clauses.append("cust_direct.name ILIKE %s")
    params.append(f"%{customer}%")

# Líneas 464-474 - Fechas
if from_date:
    where_clauses.append("o.order_date >= %s")
if to_date:
    where_clauses.append("o.order_date <= %s")

where_sql = " AND ".join(where_clauses)
```

### Código del Query de Filas

**Líneas:** 837-900

```sql
SELECT
    o.id, o.external_id, o.order_number, o.order_date,
    oi.product_sku, oi.product_name, oi.quantity, oi.subtotal,
    ch.name as channel_name,
    cust_direct.name as customer_name
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.id
LEFT JOIN channels ch ON ch.id = o.channel_id
LEFT JOIN customers cust_direct ON cust_direct.id = o.customer_id
WHERE {where_sql}  -- ← Usa TODOS los filtros
ORDER BY o.order_date DESC
LIMIT %s OFFSET %s
```

### Código del Query de Summary (Correcto)

**Líneas:** 928-947

```sql
SELECT
    COUNT(DISTINCT o.external_id) as total_pedidos,
    SUM(oi.quantity) as total_quantity,
    SUM(oi.subtotal) as total_revenue
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.id
LEFT JOIN channels ch ON ch.id = o.channel_id
LEFT JOIN customers cust_direct ON cust_direct.id = o.customer_id
WHERE {where_sql}  -- ← Usa TODOS los filtros ✅
```

### Código del Query de Unidades MV (Incorrecto)

**Líneas:** 959-979

```python
mv_units_query_with_dates = """
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
# ❌ SOLO filtra por fechas
# ❌ NO filtra por: source, invoice_status, category, channel, customer
```

### Evidencia: Preferencia por Valor de MV

**Línea:** 1068

```python
filtered_totals["total_unidades"] = filtered_totals.get("total_unidades_mv",
    sum(row.get('unidades', 0) for row in enriched_rows))
```

El sistema **prefiere** `total_unidades_mv` (sin filtros) sobre el valor calculado de las filas.

### Comparación de Filtros Aplicados

| Filtro | Query Filas | Query Summary | Query MV Units |
|--------|:-----------:|:-------------:|:--------------:|
| source = 'relbase' | ✅ | ✅ | ❌ |
| invoice_status | ✅ | ✅ | ❌ |
| category | ✅ | ✅ | ❌ |
| channel | ✅ | ✅ | ❌ |
| customer | ✅ | ✅ | ❌ |
| sku_primario | ✅ | ✅ | ❌ |
| from_date | ✅ | ✅ | ✅ |
| to_date | ✅ | ✅ | ✅ |

### Ejemplo de Inconsistencia

**Escenario:** Usuario filtra por `category = "BARRAS"`

| Métrica | Valor | Origen | Filtrado |
|---------|-------|--------|----------|
| Filas mostradas | 50 filas de BARRAS | Query con filtros | ✅ Solo BARRAS |
| Total Pedidos | 45 | Summary con filtros | ✅ Solo BARRAS |
| Total Revenue | $2,500,000 | Summary con filtros | ✅ Solo BARRAS |
| **Total Unidades** | **150,000** | MV sin filtro categoría | ❌ TODAS las categorías |

**Resultado:** Las filas suman 25,000 unidades de BARRAS, pero el total dice 150,000 porque incluye CRACKERS, GRANOLAS, KEEPERS.

### Impacto

- **UX Confusa:** Los números no cuadran, usuario piensa que hay un bug
- **Desconfianza:** Se pierde credibilidad en los datos
- **Exportaciones Incorrectas:** Si exporta datos filtrados, el total no corresponde
- **Decisiones Erróneas:** Análisis basados en totales incorrectos

### Solución Propuesta

Aplicar los mismos filtros al query de MV:

```python
# Construir filtros para MV basados en los mismos parámetros
mv_where_clauses = ["order_date >= %s", "order_date <= %s"]
mv_params = [from_date, to_date]

if category:
    mv_where_clauses.append("category = %s")
    mv_params.append(category)

if channel:
    mv_where_clauses.append("channel_name ILIKE %s")
    mv_params.append(f"%{channel}%")

# ... aplicar todos los filtros relevantes

mv_units_query = f"""
    SELECT SUM(...) as total_units
    FROM sales_facts_mv
    WHERE {' AND '.join(mv_where_clauses)}
"""
```

---

## Problema #3: Tres Sistemas de Mapeo con Diferente Cobertura

### Contexto

Los pedidos llegan con SKUs "sucios" de diferentes fuentes:

| Fuente | SKU Original | SKU Oficial |
|--------|--------------|-------------|
| Relbase | `ANU-BAKC_U04010` | `BAKC_U04010` |
| MercadoLibre | `MLC1630337051` | `BABE_U20010` |
| Shopify | `BAKC_U04010_WEB` | `BAKC_U04010` |
| Typo | `BAKC_U040120` | `BAKC_U04010` |

La tabla `sku_mappings` permite crear reglas de transformación con diferentes tipos:
- `exact`: Match exacto
- `prefix`: Quitar prefijo (ej: `ANU-`)
- `suffix`: Quitar sufijo (ej: `_WEB`)
- `regex`: Expresión regular
- `contains`: Contiene substring

### Sistema 1: Python en audit.py

**Archivo:** `backend/app/api/audit.py`
**Líneas:** 181-312

```python
def map_sku_with_quantity(sku, product_name, product_map, catalog_skus,
                          catalog_master_skus, source):
    """
    Mapea SKU raw a SKU oficial del catálogo.

    Prioridad de matching:
    1. Match exacto en catalog_skus
    2. Match en catalog_master_skus (Caja Master)
    3. Regla en sku_mappings (via SKUMappingService)
    4. Fallbacks programáticos (regex hardcodeados)
    5. Substring matching
    """

    # Prioridad 1: Match exacto en catálogo (100% confidence)
    if sku in catalog_skus:
        return sku, 'exact_match', 1, product_map[sku], 100

    # Prioridad 2: Match en Caja Master (100% confidence)
    if sku in catalog_master_skus:
        return sku, 'caja_master', 1, product_map[sku], 100

    # Prioridad 3: Buscar en sku_mappings via SKUMappingService
    # Soporta: exact, prefix, suffix, regex, contains
    mapping_result = mapping_service.map_sku(sku, source or None)
    if mapping_result:
        return (mapping_result.target_sku,
                f'db_{mapping_result.match_type}',
                mapping_result.quantity_multiplier or 1,
                product_map.get(mapping_result.target_sku),
                mapping_result.confidence or 95)

    # Prioridad 4: Fallbacks programáticos (90% confidence)

    # 4a. Trailing "20" → "10" (variante idioma)
    if sku.endswith('20') and not sku.endswith('010'):
        clean_sku = sku[:-2] + '10'
        if clean_sku in catalog_skus:
            return clean_sku, 'trailing_20_to_10', 1, product_map[clean_sku], 90

    # 4b. Extra digits pattern (BABE_C028220 → BABE_C02810)
    extra_digit_match = re.match(r'^(.+)([0-9]{3})([0-9]{2})0$', sku)
    if extra_digit_match:
        # ... lógica de limpieza

    # 4c. Cracker "1UES" variants (CRAA1UES → CRAA_U13510)
    cracker_match = re.match(r'^CR([A-Z]{2})1UES$', sku)
    if cracker_match:
        # ... mapeo específico de crackers

    # Prioridad 5: Substring matching (85% confidence)
    for catalog_sku in sorted(catalog_skus, key=len, reverse=True):
        if len(catalog_sku) >= 8 and catalog_sku in sku:
            return catalog_sku, 'substring_match_unitary', 1, product_map[catalog_sku], 85

    # No match
    return None, 'no_match', 1, None, 0
```

**Capacidades:**
- ✅ Match exacto en catálogo
- ✅ Match en Caja Master
- ✅ sku_mappings: exact, prefix, suffix, regex, contains
- ✅ Fallbacks programáticos (regex hardcodeados)
- ✅ Substring matching

### Sistema 2: SQL en sales_facts_mv

**Archivo:** `supabase/migrations/20260109143335_remote_schema.sql`
**Líneas:** 1670-1725

```sql
-- Vista materializada para analytics
CREATE MATERIALIZED VIEW sales_facts_mv AS
SELECT
    ...
FROM orders o
JOIN order_items oi ON o.id = oi.order_id

-- Path 1: Match directo en product_catalog.sku
LEFT JOIN product_catalog pc_direct
    ON pc_direct.sku = upper(oi.product_sku)
    AND pc_direct.is_active = true

-- Path 2: Match en product_catalog.sku_master (Caja Master)
LEFT JOIN product_catalog pc_master
    ON pc_master.sku_master = upper(oi.product_sku)
    AND pc_master.is_active = true
    AND pc_direct.sku IS NULL  -- Solo si path 1 falló

-- Path 3: Match en sku_mappings
LEFT JOIN sku_mappings sm
    ON sm.source_pattern = upper(oi.product_sku)
    AND sm.pattern_type = 'exact'   -- ❌ SOLO EXACT
    AND sm.is_active = true
    AND pc_direct.sku IS NULL
    AND pc_master.sku IS NULL  -- Solo si paths 1 y 2 fallaron

-- Path 4: Target SKU del mapping → catálogo
LEFT JOIN product_catalog pc_mapped
    ON pc_mapped.sku = sm.target_sku
    AND pc_mapped.is_active = true

-- Path 5: Target SKU del mapping → catálogo (master)
LEFT JOIN product_catalog pc_mapped_master
    ON pc_mapped_master.sku_master = sm.target_sku
    AND pc_mapped_master.is_active = true
    AND pc_mapped.sku IS NULL
```

**Línea crítica:**
```sql
AND sm.pattern_type = 'exact'   -- ❌ IGNORA prefix, suffix, regex, contains
```

**Capacidades:**
- ✅ Match exacto en catálogo
- ✅ Match en Caja Master
- ✅ sku_mappings: exact
- ❌ sku_mappings: prefix
- ❌ sku_mappings: suffix
- ❌ sku_mappings: regex
- ❌ sku_mappings: contains
- ❌ Fallbacks programáticos
- ❌ Substring matching

### Sistema 3: SKUMappingService (Python)

**Archivo:** `backend/app/services/sku_mapping_service.py`
**Líneas:** 157-196

```python
def _matches_pattern(self, sku: str, mapping: Dict, source: Optional[str]) -> bool:
    """
    Evalúa si un SKU coincide con un patrón de mapeo.
    """
    pattern = mapping['source_pattern']
    pattern_type = mapping['pattern_type']

    # Filtro por source (opcional)
    mapping_source = mapping.get('source_filter')
    if mapping_source and source and mapping_source.lower() != source.lower():
        return False

    if pattern_type == 'exact':
        return sku == pattern

    elif pattern_type == 'prefix':
        return sku.startswith(pattern)

    elif pattern_type == 'suffix':
        return sku.endswith(pattern)

    elif pattern_type == 'contains':
        return pattern in sku

    elif pattern_type == 'regex':
        try:
            return re.match(pattern, sku) is not None
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
            return False

    return False
```

**Capacidades:**
- ✅ sku_mappings: exact
- ✅ sku_mappings: prefix
- ✅ sku_mappings: suffix
- ✅ sku_mappings: regex
- ✅ sku_mappings: contains
- ✅ Filtro por source

### Matriz de Capacidades Comparativa

| Capacidad | Python (audit.py) | SQL (sales_facts_mv) | SKUMappingService |
|-----------|:-----------------:|:--------------------:|:-----------------:|
| Match exacto catálogo | ✅ | ✅ | N/A |
| Match Caja Master | ✅ | ✅ | N/A |
| sku_mappings: exact | ✅ | ✅ | ✅ |
| sku_mappings: prefix | ✅ | ❌ | ✅ |
| sku_mappings: suffix | ✅ | ❌ | ✅ |
| sku_mappings: regex | ✅ | ❌ | ✅ |
| sku_mappings: contains | ✅ | ❌ | ✅ |
| Fallbacks programáticos | ✅ | ❌ | ❌ |
| Substring matching | ✅ | ❌ | ❌ |
| Filtro por source | ✅ | ❌ | ✅ |

### Ejemplos de Comportamiento Divergente

#### Ejemplo 1: SKU con prefijo ANU-

**Regla en base de datos:**
```sql
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku)
VALUES ('ANU-', 'prefix', NULL);  -- Quita prefijo, usa resto como target
```

**SKU de entrada:** `ANU-BAKC_U04010`

| Sistema | Resultado | Razón |
|---------|-----------|-------|
| audit.py | ✅ **MAPEADO** → BAKC_U04010 | SKUMappingService soporta prefix |
| sales_facts_mv | ❌ **UNMAPPED** | `pattern_type = 'exact'` no matchea |

#### Ejemplo 2: ID de MercadoLibre con regex

**Regla en base de datos:**
```sql
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku, source_filter)
VALUES ('^MLC[0-9]+$', 'regex', 'BABE_U20010', 'mercadolibre');
```

**SKU de entrada:** `MLC1630337051`

| Sistema | Resultado | Razón |
|---------|-----------|-------|
| audit.py | ✅ **MAPEADO** → BABE_U20010 | SKUMappingService evalúa regex |
| sales_facts_mv | ❌ **UNMAPPED** | SQL no puede evaluar regex en JOIN |

#### Ejemplo 3: SKU con typo (dígito extra)

**SKU de entrada:** `BAKC_U040120` (tiene "1" extra)

| Sistema | Resultado | Razón |
|---------|-----------|-------|
| audit.py | ✅ **MAPEADO** → BAKC_U04010 | Fallback `trailing_20_to_10` |
| sales_facts_mv | ❌ **UNMAPPED** | No tiene fallbacks programáticos |

#### Ejemplo 4: SKU con sufijo _WEB

**Regla en base de datos:**
```sql
INSERT INTO sku_mappings (source_pattern, pattern_type, target_sku)
VALUES ('_WEB', 'suffix', NULL);  -- Quita sufijo
```

**SKU de entrada:** `BAKC_U04010_WEB`

| Sistema | Resultado | Razón |
|---------|-----------|-------|
| audit.py | ✅ **MAPEADO** → BAKC_U04010 | SKUMappingService soporta suffix |
| sales_facts_mv | ❌ **UNMAPPED** | Solo busca `pattern_type = 'exact'` |

### Impacto

1. **Inconsistencia de Datos:**
   - Mismo pedido aparece mapeado en Audit, sin mapear en Sales Analytics
   - Porcentajes de "unmapped" difieren entre vistas

2. **Administradores Confundidos:**
   - Crean reglas con `prefix` o `regex`
   - Funcionan en Desglose de Pedidos
   - Sales Analytics sigue mostrando SKUs sin mapear
   - Piensan que el sistema no funciona

3. **Métricas Incorrectas:**
   - Sales Analytics tiene mayor % de "unmapped"
   - Revenue de productos "sin mapear" inflado artificialmente
   - Análisis por categoría/producto incompleto

4. **Decisiones Erróneas:**
   - Si 20% de ventas aparece como "unmapped" en analytics pero 5% en audit
   - ¿Cuál es la verdad?
   - Imposible tomar decisiones confiables

### Solución Propuesta

**Opción A: Expandir capacidades de la MV (complejo)**

Requeriría cambiar JOINs a subqueries con CASE/WHEN para evaluar cada pattern_type. Impacto en performance.

**Opción B: Pre-calcular mapeos en order_items (recomendado)**

1. Durante sync, resolver el SKU y guardar en `order_items.canonical_sku`
2. La MV usa `canonical_sku` directamente, sin JOINs a sku_mappings
3. Un solo punto de mapeo (Python) garantiza consistencia

**Opción C: Convertir todos los mappings a 'exact' (workaround)**

1. Script que expande reglas prefix/suffix/regex a reglas exact
2. `ANU-` prefix genera: `ANU-BAKC_U04010` → exact, `ANU-BAKC_U20010` → exact, etc.
3. Más filas en sku_mappings pero MV las puede usar

---

## Archivos Relacionados

### Backend

| Archivo | Propósito |
|---------|-----------|
| `backend/app/api/audit.py` | Endpoint de desglose, mapeo Python |
| `backend/app/api/sales_analytics.py` | Usa sales_facts_mv |
| `backend/app/services/product_catalog_service.py` | Cálculo de unidades correcto |
| `backend/app/services/sku_mapping_service.py` | Evaluación de patrones |

### Database

| Archivo | Propósito |
|---------|-----------|
| `supabase/migrations/20260109143335_remote_schema.sql` | Definición de sales_facts_mv |

### Frontend

| Archivo | Propósito |
|---------|-----------|
| `frontend/app/dashboard/orders/page.tsx` | Vista de pedidos con tab Desglose |
| `frontend/app/dashboard/sales-analytics/page.tsx` | Analytics (usa MV) |

---

## Prioridad de Corrección

| # | Problema | Esfuerzo | Impacto | Prioridad |
|---|----------|----------|---------|-----------|
| 1 | MV units_sold | Medio | Alto (métricas erróneas) | 🔴 P1 |
| 2 | Totales sin filtros | Bajo | Alto (UX confusa) | 🔴 P1 |
| 3 | Sistemas de mapeo | Alto | Alto (inconsistencia) | 🟡 P2 |

---

---

## Nota: Filtros Intencionales en Sales Analytics

> ℹ️ **Esto NO es un bug** - Es lógica de negocio documentada

### Contexto

El endpoint `/api/v1/sales-analytics` tiene dos filtros hardcodeados que **excluyen datos históricos intencionalmente**.

### Filtro 1: SKUs ANU% (línea 73)

```python
where_clauses.append("mv.original_sku NOT LIKE 'ANU%%'")
```

**¿Qué es ANU?**
- Sistema de codificación de SKUs **ANTIGUO** (2014-2024)
- En 2025 se migró a un nuevo sistema de SKUs
- ANU = "Anterior" / "Antiguo"

**Distribución temporal:**
| Año | Órdenes ANU | Órdenes Normal | % ANU |
|-----|-------------|----------------|-------|
| 2014-2020 | 1,582 | 0 | 100% |
| 2021-2024 | 2,021 | 209 | ~90% |
| **2025** | 77 | 1,933 | **3.9%** |
| 2026 | 0 | 17 | 0% |

**Impacto del filtro:**
- Excluye: 3,506 órdenes (62%), $812M revenue (63%)
- Incluye: 2,159 órdenes (38%), $475M revenue (37%)

**¿Por qué se filtran?**
- El 91% de los SKUs ANU son **unmapped** (no tienen categoría, units_per_display, etc.)
- Sales Analytics requiere metadata completa para análisis por categoría/formato
- Los datos ANU no aportan valor analítico sin la metadata

### Filtro 2: Año 2025 por defecto (línea 91)

```python
# Solo se aplica cuando NO se especifican fechas
where_clauses.append("EXTRACT(YEAR FROM mv.order_date) = 2025")
```

**Razón:** Coherente con el filtro ANU - por defecto muestra solo datos del "nuevo sistema".

### Diferencia entre Vistas

| Vista | Endpoint | Filtros | Propósito |
|-------|----------|---------|-----------|
| **Sales Analytics** | `/api/v1/sales-analytics` | ANU excluido, 2025 default | Datos limpios con metadata |
| **Desglose Pedidos** | `/api/v1/audit/data` | Sin filtros | Todos los datos históricos |

### Clientes con solo datos ANU (nunca usaron nuevo sistema)

Algunos clientes históricos solo tienen órdenes con SKUs ANU:
- SERVICIOS GASTRONOMICOS MURTILLA LIMITADA: 45 órdenes
- FUND DIABETES JUVENIL DE CHILE: 41 órdenes
- INVERSIONES MONEY MAKER LIMITADA: 24 órdenes
- (y ~10 más con >10 órdenes)

Estos clientes **no aparecen en Sales Analytics** pero sí en Desglose Pedidos.

### Mejoras Opcionales (si se requieren)

1. **Agregar parámetro `include_legacy`** para incluir datos ANU opcionalmente
2. **Cambiar default de año** a dinámico (año actual en vez de hardcoded 2025)
3. **Documentar en UI** que Sales Analytics solo muestra datos post-migración

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2026-01-14 | Documento creado con análisis multi-agente |
| 2026-01-14 | Confirmados los 3 problemas críticos mediante código |
| 2026-01-14 19:00 | Problema #1 marcado como RESUELTO (CORP-162) |
| 2026-01-14 19:00 | Agregada documentación de filtros ANU% y año 2025 |
| 2026-01-14 21:27 | Problema #2 marcado como RESUELTO (CORP-155) |
