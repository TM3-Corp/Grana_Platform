# Sistema de Mapeo de SKUs - Análisis Completo

> **Fecha:** 2026-01-12
> **Propósito:** Documentar el sistema actual de mapeo de SKUs, sus inconsistencias y problemas para planificar mejoras.

---

## 1. Contexto del Negocio

### Problema a Resolver
Grana vende productos en diferentes formatos:
- **Unitario** (1 barra)
- **Display** (5 barras)
- **Caja Master** (140 barras)

Cuando se vende "17 Cajas Master", necesitamos saber que son **2,380 barras** para:
- Reportes de ventas precisos
- Control de inventario
- Proyecciones de demanda

### Jerarquía de Productos
```
Caja Master (BAKC_C02810) → 140 unidades
    └── Display X5 (BAKC_U20010) → 5 unidades
        └── Unitario (BAKC_U04010) → 1 unidad
```

---

## 2. Tablas de Base de Datos

### 2.1 Tablas Activas

#### `product_catalog` (Fuente de verdad para productos)
```sql
CREATE TABLE product_catalog (
    id BIGINT PRIMARY KEY,
    sku VARCHAR(100) NOT NULL,           -- SKU del producto (ej: BAKC_U04010)
    sku_master VARCHAR(100),             -- SKU de Caja Master (ej: BAKC_C02810)
    sku_primario VARCHAR(50),            -- SKU base para agrupar (ej: BAKC_U04010)
    category VARCHAR(100),               -- BARRAS, CRACKERS, GRANOLAS, KEEPERS
    product_name TEXT,
    master_box_name TEXT,
    units_per_display INTEGER,           -- Factor conversión (1, 5, 16, etc.)
    items_per_master_box INTEGER,        -- Unidades en Caja Master (140, 120, etc.)
    is_active BOOLEAN DEFAULT TRUE
);
```

**Campos clave para conversión:**
- `units_per_display`: Cuántas unidades tiene este SKU (1 para unitario, 5 para X5, etc.)
- `items_per_master_box`: Total de unidades en la Caja Master asociada
- `sku_master`: Código de la Caja Master (para match inverso)

#### `sku_mappings` (Reglas de mapeo manual)
```sql
CREATE TABLE sku_mappings (
    id INTEGER PRIMARY KEY,
    source_pattern VARCHAR(255) NOT NULL,  -- SKU a mapear (ej: PACKBAMC_U04010)
    pattern_type VARCHAR(20) NOT NULL,     -- 'exact', 'prefix', 'suffix', 'regex', 'contains'
    source_filter VARCHAR(50),             -- Filtro por fuente (relbase, mercadolibre, etc.)
    target_sku VARCHAR(100) NOT NULL,      -- SKU destino en product_catalog
    quantity_multiplier INTEGER DEFAULT 1, -- Multiplicador (ej: 4 para PACK de 4)
    rule_name VARCHAR(100),
    confidence INTEGER DEFAULT 100,
    priority INTEGER DEFAULT 50,
    is_active BOOLEAN DEFAULT TRUE
);
```

**Uso:** Mapear SKUs externos/legacy a SKUs del catálogo:
- `ANU-BAKC_U04010` → `BAKC_U04010` (prefijo ANU-)
- `PACKGRCA_U26010` → `GRCA_U26010` × 4 (pack de 4)
- `MLC1630337051` → `BABE_U20010` (ID MercadoLibre)

#### `order_items` (Items de pedidos)
```sql
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER,                    -- ⚠️ Siempre NULL (no se usa)
    product_sku VARCHAR(100),              -- SKU original del pedido
    product_name VARCHAR(255),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12,2),
    subtotal NUMERIC(12,2),
    sku_primario VARCHAR(100)              -- ⚠️ Existe pero siempre NULL
);
```

**Problemas identificados:**
- `product_id`: FK a tabla `products` que no se usa
- `sku_primario`: Columna creada pero nunca poblada durante sync

#### `orders` (Pedidos)
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    external_id VARCHAR(255),
    source VARCHAR(50) NOT NULL,           -- 'relbase', 'shopify', 'mercadolibre'
    customer_id INTEGER,
    channel_id INTEGER,
    total NUMERIC(12,2),
    invoice_status VARCHAR(50),            -- 'accepted', 'accepted_objection', etc.
    order_date TIMESTAMP
);
```

### 2.2 Vista Materializada

#### `sales_facts_mv` (OLAP pre-calculado)
```sql
CREATE MATERIALIZED VIEW sales_facts_mv AS
SELECT
    o.order_date,
    oi.product_sku as original_sku,

    -- Mapeo con 4-path matching
    COALESCE(pc_direct.sku, pc_master.sku, pc_mapped.sku, pc_mapped_master.sku) as catalog_sku,
    COALESCE(pc_direct.sku_primario, pc_master.sku_primario, ...) as sku_primario,
    COALESCE(pc_direct.category, pc_master.category, ...) as category,

    -- Factores de conversión
    COALESCE(pc_direct.units_per_display, ..., 1) as units_per_display,
    COALESCE(pc_master.items_per_master_box, ...) as items_per_master_box,

    -- ⚠️ PROBLEMA: units_sold NO aplica factores de conversión
    (oi.quantity * COALESCE(sm.quantity_multiplier, 1)) as units_sold,

    oi.subtotal as revenue
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN product_catalog pc_direct ON pc_direct.sku = UPPER(oi.product_sku)
LEFT JOIN product_catalog pc_master ON pc_master.sku_master = UPPER(oi.product_sku)
LEFT JOIN sku_mappings sm ON sm.source_pattern = UPPER(oi.product_sku)
                          AND sm.pattern_type = 'exact'
LEFT JOIN product_catalog pc_mapped ON pc_mapped.sku = sm.target_sku
LEFT JOIN product_catalog pc_mapped_master ON pc_mapped_master.sku_master = sm.target_sku
WHERE o.invoice_status IN ('accepted', 'accepted_objection');
```

### 2.3 Tablas Obsoletas/No Usadas

| Tabla | Estado | Problema |
|-------|--------|----------|
| `products` | Obsoleta | Duplica `product_catalog`, mezcla datos de inventario |
| `channel_equivalents` | Sin usar | Vacía, reemplazada por `sku_mappings` |
| `channel_product_equivalents` | Sin usar | Vacía |
| `product_variants` | Parcial | Vista que usa `products` (legacy) |

---

## 3. Archivos y Funciones

### 3.1 Backend

#### `backend/app/api/audit.py`
**Propósito:** Endpoint `/api/v1/audit/data` para vista Desglose de Pedidos

**Funciones clave:**

```python
def load_product_mapping():
    """
    Carga product_catalog en memoria.
    Retorna: (product_map, catalog_skus, catalog_master_skus, conversion_map)
    """

def map_sku_with_quantity(sku, product_name, product_map, catalog_skus, catalog_master_skus, source):
    """
    Mapea SKU raw a SKU del catálogo.

    Prioridad:
    1. Match exacto en catalog_skus
    2. Match en catalog_master_skus (Caja Master)
    3. Regla en sku_mappings (via SKUMappingService)
    4. Fallbacks programáticos (regex)

    Retorna: (official_sku, match_type, pack_quantity, product_info, confidence)
    """

def calculate_units(sku, quantity, conversion_map, source):
    """
    Calcula unidades totales.
    Fórmula: quantity × sku_mappings.multiplier × product_catalog.units_per_display
    Delega a ProductCatalogService.calculate_units()
    """

def get_sku_primario(sku, conversion_map):
    """
    Obtiene SKU base para agrupar variantes.
    Delega a ProductCatalogService.get_sku_primario()
    """
```

**Fallbacks programáticos (líneas 258-298):**
- `trailing_20_to_10`: SKU termina en "20" → "10"
- `extra_digits_removed`: Dígitos extra al final
- `cracker_1ues_variant`: `CRAA1UES` → `CRAA_U13510`
- `language_variant`: `_C02010` → `_C02020`

#### `backend/app/services/product_catalog_service.py`
**Propósito:** Servicio para consultar `product_catalog`

```python
class ProductCatalogService:
    def __init__(self):
        self._catalog_cache = None  # Cache en memoria

    def calculate_units(self, sku: str, quantity: int, source: str = None) -> int:
        """
        Fórmula completa:
        1. Si hay mapping en sku_mappings:
           quantity × mapping.quantity_multiplier × target_sku.units_per_display
        2. Si es SKU directo:
           quantity × units_per_display
        3. Si es Caja Master:
           quantity × items_per_master_box
        """

    def get_sku_primario(self, sku: str) -> str:
        """Retorna el SKU _U04010 (unitario español) si existe"""
```

#### `backend/app/services/sku_mapping_service.py`
**Propósito:** Consultar reglas de `sku_mappings`

```python
class SKUMappingService:
    CACHE_TTL = 300  # 5 minutos

    def map_sku(self, raw_sku: str, source: str = None) -> MappingResult:
        """
        Busca regla activa para el SKU.
        Soporta pattern_type: exact, prefix, suffix, regex, contains
        Retorna: MappingResult(target_sku, quantity_multiplier, match_type, confidence)
        """
```

#### `backend/app/api/sku_mappings.py`
**Propósito:** CRUD de reglas de mapeo + endpoint de análisis

**Endpoints:**
- `GET /api/v1/sku-mappings/order-skus/all` - Lista SKUs de pedidos con estado de mapeo
- `POST /api/v1/sku-mappings/` - Crear regla
- `PUT /api/v1/sku-mappings/{id}` - Actualizar regla
- `DELETE /api/v1/sku-mappings/{id}` - Eliminar regla

**Función importante:**
```python
def refresh_sales_facts_mv():
    """Refresca la MV después de cambios en mapeos"""
    cursor.execute("REFRESH MATERIALIZED VIEW sales_facts_mv")
```

#### `backend/app/api/sales_analytics.py`
**Propósito:** Analytics usando `sales_facts_mv`

```python
# Usa exclusivamente la MV para queries OLAP
SELECT category, SUM(revenue), SUM(units_sold)
FROM sales_facts_mv
WHERE ...
GROUP BY category
```

### 3.2 Frontend

#### `frontend/app/dashboard/sku-mappings/page.tsx`
**Propósito:** Vista de mapeo manual de SKUs

**Datos mostrados:**
- Lista de SKUs en pedidos con estado (mapeado/sin mapear)
- KPIs: Total SKUs, En Catálogo, Con Mapeo, Sin Mapear, % Cobertura
- Modal para crear/editar reglas de mapeo

**API calls:**
- `GET /api/v1/sku-mappings/order-skus/all`
- `POST /api/v1/sku-mappings/`

#### `frontend/app/dashboard/product-catalog/page.tsx`
**Propósito:** Vista de catálogo de productos

**API calls:**
- `GET /api/v1/product-catalog/`

#### `frontend/components/AuditView.tsx`
**Propósito:** Vista de Desglose de Pedidos

**Columnas mostradas:**
- Pedido, Fecha, Cliente, Canal
- SKU (original), SKU Primario, Familia, Producto
- Cantidad, **Unidades** (calculadas), Peso
- Precio, Total

**API calls:**
- `GET /api/v1/audit/data?limit=X&offset=Y&category=X&channel=X&...`
- `GET /api/v1/audit/filters`
- `GET /api/v1/audit/summary`

---

## 4. Flujo de Datos por Vista

### 4.1 Vista Mapeo de SKUs

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    /dashboard/sku-mappings                              │
│                                                                         │
│  Frontend ──► GET /api/v1/sku-mappings/order-skus/all                  │
│                           │                                             │
│                           ▼                                             │
│               ┌───────────────────────┐                                │
│               │   sku_mappings.py     │                                │
│               │   (líneas 766-833)    │                                │
│               └───────────────────────┘                                │
│                           │                                             │
│                           ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ SQL Query:                                                       │   │
│  │ SELECT oi.product_sku, COUNT(*), SUM(quantity)                  │   │
│  │ FROM order_items oi                                              │   │
│  │ JOIN orders o ON o.id = oi.order_id                             │   │
│  │ LEFT JOIN sku_mappings sm ON sm.source_pattern = oi.product_sku │   │
│  │ LEFT JOIN product_catalog pc ON pc.sku = oi.product_sku         │   │
│  │ LEFT JOIN product_catalog pc_m ON pc_m.sku_master = oi.product_sku│  │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Tablas: order_items, orders, sku_mappings, product_catalog            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Vista Catálogo de Productos

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    /dashboard/product-catalog                           │
│                                                                         │
│  Frontend ──► GET /api/v1/product-catalog/                             │
│                           │                                             │
│                           ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ SQL Query:                                                       │   │
│  │ SELECT * FROM product_catalog WHERE is_active = TRUE            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Tablas: product_catalog (única)                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Vista Desglose de Pedidos (AuditView)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    /dashboard/orders (tab Desglose)                     │
│                                                                         │
│  Frontend ──► GET /api/v1/audit/data?...                               │
│                           │                                             │
│                           ▼                                             │
│               ┌───────────────────────┐                                │
│               │      audit.py         │                                │
│               └───────────────────────┘                                │
│                           │                                             │
│           ┌───────────────┼───────────────┐                            │
│           ▼               ▼               ▼                            │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│   │  SQL Query   │ │ Python Cache │ │  MV Query    │                  │
│   │  (datos)     │ │ (mapeo)      │ │  (totales)   │                  │
│   └──────────────┘ └──────────────┘ └──────────────┘                  │
│          │                │                │                           │
│          ▼                ▼                ▼                           │
│   orders          ProductCatalogService   sales_facts_mv              │
│   order_items     SKUMappingService                                    │
│   channels                                                             │
│   customers                                                            │
│                                                                         │
│  ⚠️ INCONSISTENCIA: Filas calculadas con Python, Total con MV         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.4 Vista Sales Analytics

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    /dashboard/sales-analytics                           │
│                                                                         │
│  Frontend ──► GET /api/v1/sales-analytics?...                          │
│                           │                                             │
│                           ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ SQL Query (solo usa MV):                                         │   │
│  │ SELECT category, SUM(revenue), SUM(units_sold)                  │   │
│  │ FROM sales_facts_mv                                              │   │
│  │ WHERE ...                                                        │   │
│  │ GROUP BY category                                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Tablas: sales_facts_mv (única)                                        │
│                                                                         │
│  ⚠️ PROBLEMA: units_sold NO incluye factores de conversión            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Inconsistencias Identificadas

### 5.1 CRÍTICO: `sales_facts_mv.units_sold` No Calcula Unidades Correctamente

**Ubicación:** `backend/migrations/025_fix_caja_master_category.sql` línea 101

**Problema:**
```sql
-- En la MV:
(oi.quantity * COALESCE(sm.quantity_multiplier, 1)) as units_sold
-- ❌ NO multiplica por units_per_display
-- ❌ NO multiplica por items_per_master_box
```

**Fórmula correcta (en Python):**
```python
# ProductCatalogService.calculate_units()
units = quantity × sku_mappings.quantity_multiplier × product_catalog.units_per_display
# O para Caja Master:
units = quantity × items_per_master_box
```

**Impacto:**
| SKU | Cantidad | MV `units_sold` | Python `unidades` | Error |
|-----|----------|-----------------|-------------------|-------|
| BAKC_U04010 (X1) | 10 | 10 | 10 | ✅ 0% |
| BAKC_U20010 (X5) | 10 | 10 | **50** | ❌ -80% |
| BAKC_C02810 (CM 140u) | 2 | 2 | **280** | ❌ -99% |

**Vistas afectadas:** Sales Analytics, Dashboard Ejecutivo (KPIs)

---

### 5.2 CRÍTICO: Total de Desglose Ignora Filtros

**Ubicación:** `backend/app/api/audit.py` líneas 1096-1106

**Problema:**
```python
# Query para total_unidades:
mv_units_query = """
    SELECT SUM(...) as total_units
    FROM sales_facts_mv
    WHERE order_date >= %s AND order_date <= %s
"""
# ❌ NO aplica filtros de: category, channel, customer, source
```

```python
# Query para filas SÍ aplica filtros:
WHERE o.source = 'relbase'
  AND o.invoice_status IN ('accepted', 'accepted_objection')
  AND ... category_filter, channel_filter, customer_filter
```

**Impacto:**
- Si filtras por "BARRAS", las filas muestran solo BARRAS
- Pero el total muestra TODAS las categorías
- El total nunca coincide con la suma de filas visibles

---

### 5.3 MEDIO: Tres Sistemas de Mapeo con Diferente Cobertura

**Sistema 1: audit.py (Python)**
- Prioridad 1: Match directo en `product_catalog.sku`
- Prioridad 2: Match en `product_catalog.sku_master`
- Prioridad 3: Regla en `sku_mappings` (todos los pattern_types)
- Prioridad 4: **Fallbacks programáticos** (regex)
- Prioridad 5: Substring matching

**Sistema 2: sales_facts_mv (SQL)**
- Path 1: Match directo en `product_catalog.sku`
- Path 2: Match en `product_catalog.sku_master`
- Path 3: Regla en `sku_mappings` (**solo pattern_type='exact'**)
- ❌ NO tiene fallbacks programáticos

**Sistema 3: sku_mappings.py (SQL)**
- Similar a MV, solo usa `pattern_type='exact'` en JOINs

**Impacto:**
```
SKU: BAKC_U040120 (typo, tiene "1" extra)

audit.py (Python):
  → Aplica fallback "trailing_20_to_10"
  → Resultado: BAKC_U04010 ✅

sales_facts_mv (SQL):
  → No hay regla exact
  → Resultado: unmapped ❌

Diferencia: Este SKU aparece mapeado en Desglose pero sin mapear en Sales Analytics
```

---

### 5.4 MEDIO: `order_items.sku_primario` Nunca Se Pobla

**Ubicación:** Tabla `order_items`, columna `sku_primario`

**Problema:**
- La columna existe (migración 015)
- Tiene comentario que dice "populated by audit.py mapping logic"
- **Pero NUNCA se pobla durante sync**
- Se calcula dinámicamente en cada consulta

**Impacto:**
- Cada request recalcula el mismo dato
- No se puede indexar para queries eficientes
- La MV debe hacer 4 LEFT JOINs para derivar el mismo dato

---

### 5.5 MEDIO: `order_items.product_id` Siempre NULL

**Ubicación:** Tabla `order_items`, columna `product_id`

**Problema:**
- FK a tabla `products` (legacy)
- Nunca se pobla durante sync de Relbase/Shopify/ML
- La MV original (migración 013) intentaba usarla y fallaba

**Impacto:**
- Columna inútil que confunde
- JOINs a `products` siempre fallan
- Se tuvo que reescribir la MV para usar SKU-based matching

---

### 5.6 BAJO: Dos Tablas de Productos

**Tablas:**
- `products` (legacy, 40+ columnas)
- `product_catalog` (actual, fuente de verdad)

**Problema:**
- `products` mezcla catálogo con inventario (current_stock, min_stock)
- Triggers en `products` que nunca se ejecutan
- Confusión sobre cuál usar

**Recomendación:** Eliminar `products` o migrar completamente a `product_catalog`

---

### 5.7 BAJO: Cache de Python vs Base de Datos

**Ubicación:**
- `ProductCatalogService._catalog_cache`
- `SKUMappingService._mappings_cache` (TTL: 5 min)

**Problema:**
- Si se actualiza `product_catalog` o `sku_mappings`, el cache puede estar desactualizado
- Filas calculadas con cache viejo vs totales de MV actualizada

**Mitigación actual:**
- `refresh_sales_facts_mv()` se llama al crear/modificar mapeos
- TTL de 5 minutos en SKUMappingService

---

## 6. Fórmula de Conversión de Unidades

### Fórmula Correcta (ProductCatalogService)

```python
def calculate_units(sku, quantity, source):
    # Paso 1: Verificar si hay mapping en sku_mappings
    mapping = sku_mapping_service.map_sku(sku, source)

    if mapping:
        multiplier = mapping.quantity_multiplier  # ej: 4 para PACK
        target_sku = mapping.target_sku
        conversion = product_catalog[target_sku].units_per_display
        return quantity * multiplier * conversion

    # Paso 2: Match directo en catálogo
    if sku in product_catalog:
        return quantity * product_catalog[sku].units_per_display

    # Paso 3: Match en Caja Master
    if sku in master_sku_lookup:
        return quantity * master_sku_lookup[sku].items_per_master_box

    # Paso 4: Sin mapear
    return quantity * 1
```

### Ejemplos

| SKU Original | Cantidad | Mapping | Conversión | Unidades |
|--------------|----------|---------|------------|----------|
| BAKC_U04010 (X1) | 10 | - | ×1 | 10 |
| BAKC_U20010 (X5) | 10 | - | ×5 | 50 |
| BAKC_C02810 (CM) | 2 | - | ×140 | 280 |
| PACKGRCA (Pack 4) | 3 | GRCA_U26010 ×4 | ×1 | 12 |
| KEEPERPACK | 7 | KSMC_U03010 ×5 | ×1 | 35 |

---

## 7. Recomendaciones

### 7.1 Corto Plazo (Fixes Urgentes)

1. **Corregir `sales_facts_mv`** para que `units_sold` incluya factores de conversión:
```sql
-- Cambiar de:
(oi.quantity * COALESCE(sm.quantity_multiplier, 1)) as units_sold

-- A:
(oi.quantity * COALESCE(sm.quantity_multiplier, 1) *
 CASE
   WHEN pc_master.sku IS NOT NULL OR pc_mapped_master.sku IS NOT NULL
   THEN COALESCE(items_per_master_box, 1)
   ELSE COALESCE(units_per_display, 1)
 END
) as units_sold
```

2. **Corregir query de totales en audit.py** para respetar filtros:
```python
# Agregar los mismos filtros que la query principal
mv_units_query = """
    SELECT SUM(...) as total_units
    FROM sales_facts_mv
    WHERE order_date >= %s AND order_date <= %s
      AND source = 'relbase'  -- Agregar
      AND category = %s       -- Si hay filtro de categoría
      AND ...
"""
```

### 7.2 Mediano Plazo (Arquitectura)

1. **Poblar `order_items.sku_primario` durante sync:**
   - Mapear SKU una vez al insertar
   - Guardar resultado para no recalcular

2. **Agregar columnas pre-calculadas a `order_items`:**
   ```sql
   ALTER TABLE order_items ADD COLUMN canonical_sku VARCHAR(100);
   ALTER TABLE order_items ADD COLUMN product_catalog_id BIGINT REFERENCES product_catalog(id);
   ALTER TABLE order_items ADD COLUMN units_calculated INTEGER;
   ALTER TABLE order_items ADD COLUMN conversion_factor_applied INTEGER;
   ```

3. **Simplificar `sales_facts_mv`:**
   - Ya no necesita 4 LEFT JOINs
   - Lee columnas pre-calculadas de `order_items`

### 7.3 Largo Plazo (Limpieza)

1. Eliminar tabla `products` (legacy)
2. Eliminar tablas vacías: `channel_equivalents`, `channel_product_equivalents`
3. Consolidar fallbacks programáticos en `sku_mappings`:
   - Crear reglas regex en la BD
   - Eliminar código hardcodeado en audit.py

---

## 8. Archivos Relacionados

### Backend
- `backend/app/api/audit.py` - Desglose de pedidos
- `backend/app/api/sku_mappings.py` - CRUD mapeos
- `backend/app/api/sales_analytics.py` - Analytics (usa MV)
- `backend/app/api/product_catalog.py` - CRUD catálogo
- `backend/app/services/product_catalog_service.py` - Servicio catálogo
- `backend/app/services/sku_mapping_service.py` - Servicio mapeos

### Frontend
- `frontend/app/dashboard/sku-mappings/page.tsx`
- `frontend/app/dashboard/product-catalog/page.tsx`
- `frontend/components/AuditView.tsx`
- `frontend/app/dashboard/sales-analytics/page.tsx`

### Migraciones
- `backend/migrations/013_create_sales_facts_mv.sql`
- `backend/migrations/020_fix_sales_facts_mv_join_by_sku.sql`
- `backend/migrations/025_fix_caja_master_category.sql`
- `backend/migrations/018_create_sku_mappings.sql`
- `backend/migrations/019_add_sku_primario_to_product_catalog.sql`
- `backend/migrations/015_add_sku_primario_to_order_items.sql`

---

## 9. Resumen de Severidad

| Problema | Severidad | Impacto | Esfuerzo Fix |
|----------|-----------|---------|--------------|
| MV `units_sold` incorrecto | 🔴 CRÍTICO | Todas las métricas de unidades | Medio |
| Totales ignoran filtros | 🔴 CRÍTICO | UX confusa, datos inconsistentes | Bajo |
| 3 sistemas de mapeo | 🟡 MEDIO | ~1% SKUs con resultado diferente | Alto |
| `sku_primario` no poblado | 🟡 MEDIO | Performance, redundancia | Medio |
| `product_id` siempre NULL | 🟢 BAJO | Columna inútil | Bajo |
| Tablas duplicadas | 🟢 BAJO | Confusión | Bajo |
