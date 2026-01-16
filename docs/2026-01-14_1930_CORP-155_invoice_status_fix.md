# Resolución CORP-155: Invoice Status Filter + UI Redesign

> **Fecha:** 2026-01-14 19:30
> **Issues:** CORP-155, CORP-148, Problema #2 (audit totals ignore filters)
> **Autor:** Claude Code
> **Estado:** Completado

---

## Resumen

Se corrigieron múltiples problemas de filtros y se rediseñó la UI de Desglose Pedido:

1. **CORP-155**: Queries con `OR invoice_status IS NULL` incluían órdenes no válidas
2. **Problema #2**: Totales de audit ignoraban filtros de category/channel/customer
3. **CORP-148**: UI de filtros confusa y extensa

---

## Cambios Realizados

### 1. Backend: order_repository.py

**Problema:** 6 queries usaban `OR invoice_status IS NULL` permitiendo órdenes de Shopify/ML/Lokal.

**Solución:** Removido `OR invoice_status IS NULL` de todas las queries.

```python
# ANTES (incorrecto):
WHERE (invoice_status IN ('accepted', 'accepted_objection') OR invoice_status IS NULL)

# DESPUÉS (correcto):
WHERE invoice_status IN ('accepted', 'accepted_objection')
```

**Líneas modificadas:** 296, 307, 409, 443, 462, 480

### 2. Backend: audit.py /summary endpoint

**Problema:** Queries no tenían filtro `invoice_status`.

**Solución:** Agregado filtro a 6 queries del endpoint `/summary`.

```python
# Agregado a cada query:
AND invoice_status IN ('accepted', 'accepted_objection')
```

**Queries modificadas:**
- Total orders (línea 1168)
- NULL customers (línea 1177)
- NULL channels (línea 1188)
- NULL SKUs (línea 1199)
- Unique SKUs (línea 1211)
- All SKUs for mapping (línea 1224)

### 3. Backend: audit.py mv_units_query (Problema #2)

**Problema:** `mv_units_query` solo filtraba por fechas, ignorando category/channel/customer.

**Solución:** Query dinámica que aplica TODOS los filtros del usuario.

```python
# ANTES (solo fechas):
mv_units_query = """
    SELECT SUM(units_sold) as total_units
    FROM sales_facts_mv
    WHERE order_date >= %s AND order_date <= %s
"""

# DESPUÉS (todos los filtros):
# Construye WHERE dinámico con:
# - order_date (from_date, to_date)
# - category (si está seleccionado)
# - channel_name (si está seleccionado)
# - customer_name (si está seleccionado)
# - sku_primario (si está seleccionado)
# - Búsqueda global (original_sku, product_name, etc.)
```

**Impacto:** Los totales ahora coinciden con los datos filtrados en la tabla.

### 4. Frontend: AuditView.tsx UI Redesign

**Problema:** UI de filtros extensa y confusa (~500 líneas de código de filtros).

**Solución:** Rediseño minimalista y compacto.

**Antes:**
```
┌─────────────────────────────────────────────────────────────┐
│ Filtros                              [Exportar] [Limpiar]  │
├─────────────────────────────────────────────────────────────┤
│ Familia de Producto:                                        │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐│
│ │  📦    │ │  🍫    │ │  🍘    │ │  🥣    │ │  🍪    ││
│ │ Todas  │ │ BARRAS │ │CRACKERS│ │GRANOLAS│ │KEEPERS ││
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘│
├─────────────────────────────────────────────────────────────┤
│ Canal: [MultiSelect]  Cliente: [MultiSelect]                │
│ Búsqueda Global: [_______________]                          │
├─────────────────────────────────────────────────────────────┤
│ ☐ Solo NULLs   ☐ Solo no mapeados                          │
├─────────────────────────────────────────────────────────────┤
│ Agrupar por: [Sin agrupación    ▼]                         │
├─────────────────────────────────────────────────────────────┤
│ Controles de Grupos:                                        │
│ [Expandir/Colapsar] [Alfabético] [Unidades] [Total $]      │
├─────────────────────────────────────────────────────────────┤
│ 📅 Filtros Temporales                                       │
│ Tipo: [Por año ▼]                                          │
│ Año: [2025 ▼] (multi-select 5 filas)                       │
│ Mes: [Enero ▼] (multi-select 6 filas)                      │
└─────────────────────────────────────────────────────────────┘
```

**Después:**
```
┌─────────────────────────────────────────────────────────────┐
│ [🔍 Buscar cliente, producto, SKU...] [2025▼] [Excel][🗑]  │
├─────────────────────────────────────────────────────────────┤
│ Familia: (Todas) (BARRAS) (CRACKERS) (GRANOLAS) (KEEPERS)  │
├─────────────────────────────────────────────────────────────┤
│ Canal:[▼]  Cliente:[▼]  Agrupar:[▼]  ☐NULLs  ☐No mapeados │
└─────────────────────────────────────────────────────────────┘
(Expandible: selector de meses, rango custom, controles grupo)
```

**Beneficios:**
- ~50% menos espacio vertical
- Pills compactos para familias
- Selector de periodo integrado
- Controles condicionales (solo aparecen cuando son relevantes)

---

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `backend/app/repositories/order_repository.py` | Removido `OR invoice_status IS NULL` (6 lugares) |
| `backend/app/api/audit.py` | Agregado invoice_status a /summary, mv_units_query con filtros |
| `frontend/components/AuditView.tsx` | Rediseño minimalista de filtros |

---

## Testing

### Verificar invoice_status fix
```bash
# Antes: incluía ~1,959 órdenes extra de Shopify/ML/Lokal
# Después: solo órdenes SII-accepted

curl "http://localhost:8000/api/v1/audit/summary" | jq '.data.total_orders'
# Debería mostrar ~2,010 (solo Relbase accepted)
```

### Verificar totales con filtros
```bash
# Antes: totales ignoraban filtros
# Después: totales coinciden con datos filtrados

curl "http://localhost:8000/api/v1/audit/data?category=BARRAS&from_date=2025-01-01&to_date=2025-12-31" | jq '.summary'
# total_unidades ahora refleja solo BARRAS
```

### Verificar UI
1. Abrir `/dashboard/audit`
2. Verificar que filtros están compactos
3. Seleccionar una familia → totales deben cambiar
4. Seleccionar un canal → totales deben cambiar

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2026-01-14 19:30 | Fix order_repository.py (6 queries) |
| 2026-01-14 19:30 | Fix audit.py /summary endpoint |
| 2026-01-14 19:30 | Fix mv_units_query con todos los filtros |
| 2026-01-14 19:30 | Rediseño UI de filtros (minimalista) |
