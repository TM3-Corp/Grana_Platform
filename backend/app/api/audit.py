"""
API endpoint for data auditing
Provides comprehensive data validation and integrity checking
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from app.services.product_catalog_service import ProductCatalogService

router = APIRouter()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize Product Catalog Service (replaces CSV dependency)
_product_catalog_service = None

def get_product_catalog_service() -> ProductCatalogService:
    """Get or initialize the ProductCatalogService singleton"""
    global _product_catalog_service
    if _product_catalog_service is None:
        _product_catalog_service = ProductCatalogService()
    return _product_catalog_service

# Load product mapping from database (replaces CSV dependency)
def load_product_mapping():
    """
    Load product catalog from database via ProductCatalogService.

    This replaces the CSV-based approach with database queries.
    Railway doesn't have access to the CSV file, so we must use the database.

    Returns: (product_map, catalog_skus, catalog_master_skus, conversion_map)
    """
    product_map = {}
    catalog_skus = set()
    catalog_master_skus = set()
    conversion_map = {}

    try:
        # Get product catalog from database
        service = get_product_catalog_service()
        all_products = service.get_all_products()

        # Build product map and catalog sets
        for sku, product_data in all_products.items():
            # Add to catalog SKUs
            catalog_skus.add(sku)

            # Check if it's a master SKU
            if product_data.get('is_master_sku'):
                catalog_master_skus.add(sku)

            # Get conversion factor
            # Normal SKUs use units_per_display, master SKUs use items_per_master_box
            if product_data.get('is_master_sku'):
                conversion_factor = product_data.get('items_per_master_box', 1) or 1
            else:
                conversion_factor = product_data.get('units_per_display', 1) or 1

            # Get SKU Primario
            sku_primario = product_data.get('primario', sku)

            # Build product map entry
            product_map[sku] = {
                'category': product_data.get('category', ''),
                'family': product_data.get('product_name', ''),
                'format': 'CAJA MASTER' if product_data.get('is_master_sku') else product_data.get('format', ''),
                'product_name': product_data.get('product_name', ''),
                'in_catalog': True,
                'tipo': 'Caja Master' if product_data.get('is_master_sku') else 'Normal',
                'conversion_factor': conversion_factor,
                'sku_primario': sku_primario
            }

            # Build conversion map entry
            base_code = product_data.get('base_code', sku.split('_')[0] if '_' in sku else sku)
            conversion_map[sku] = {
                'factor': conversion_factor,
                'primario': sku_primario,
                'base_code': base_code
            }

        print(f"✅ Loaded {len(product_map)} products from database")

    except Exception as e:
        print(f"❌ Error loading product catalog from database: {e}")
        # Return empty catalogs if database fails
        pass

    return product_map, catalog_skus, catalog_master_skus, conversion_map


def get_sku_primario(sku: str, conversion_map: dict = None) -> str:
    """
    Get the SKU Primario (base/primary SKU) for any SKU variant.
    Returns the X1 variant (_U04010 for Spanish, _U04020 for English) if it exists.
    If it doesn't exist in the catalog, returns the SKU itself.

    CRITICAL: We NEVER invent SKU codes that don't exist in the catalog.

    Phase 3: Now uses ProductCatalogService (database) instead of CSV.
    The conversion_map parameter is kept for backward compatibility but is ignored.

    Example:
        BAKC_U20010 → BAKC_U04010 (primary exists in catalog)
        GRAL_U26010 → GRAL_U26010 (GRAL_U04010 doesn't exist, so use itself)
    """
    if not sku:
        return None

    # Phase 3: Use ProductCatalogService (database query)
    service = get_product_catalog_service()
    return service.get_sku_primario(sku)


def calculate_units(sku: str, quantity: int, conversion_map: dict = None) -> int:
    """
    Calculate total units based on SKU and quantity.

    Formula: Units = Quantity × Conversion Factor

    Phase 3: Now uses ProductCatalogService (database) instead of CSV.
    The conversion_map parameter is kept for backward compatibility but is ignored.

    Examples:
        - BAKC_U04010 (X1): 10 × 1 = 10 units
        - BAKC_U20010 (X5): 10 × 5 = 50 units
        - BAKC_C02810 (CM X5): 17 × 140 = 2,380 units
    """
    if not sku or quantity is None:
        return 0

    # Phase 3: Use ProductCatalogService (database query)
    service = get_product_catalog_service()
    return service.calculate_units(sku, quantity)


def map_sku_with_quantity(sku, product_name, product_map, catalog_skus, catalog_master_skus, source=None):
    """
    Conservative mapping strategy with Pack quantity extraction
    Returns: (official_sku, match_type, pack_quantity, product_info, confidence)
    """
    import re

    sku = (sku or '').strip()
    product_name = product_name or ''
    source = (source or '').strip()

    # Rule 1: Exact match in normal SKU
    if sku in catalog_skus:
        return sku, 'exact_match', 1, product_map[sku], 100

    # Rule 2: Exact match in CAJA MÁSTER
    if sku in catalog_master_skus:
        return sku, 'caja_master', 1, product_map[sku], 100

    # Rule 3: ANU- prefix removal (with chained _WEB suffix handling)
    if sku.startswith('ANU-'):
        clean_sku = sku[4:]

        # Try direct match first
        if clean_sku in catalog_skus:
            return clean_sku, 'anu_prefix_removed', 1, product_map[clean_sku], 95
        if clean_sku in catalog_master_skus:
            return clean_sku, 'anu_prefix_removed+caja_master', 1, product_map[clean_sku], 95

        # Try removing _WEB suffix from cleaned SKU (chained transformation)
        if clean_sku.endswith('_WEB'):
            clean_sku_no_web = clean_sku[:-4]
            if clean_sku_no_web in catalog_skus:
                return clean_sku_no_web, 'anu_prefix_removed+web_suffix', 1, product_map[clean_sku_no_web], 93
            if clean_sku_no_web in catalog_master_skus:
                return clean_sku_no_web, 'anu_prefix_removed+web_suffix+caja_master', 1, product_map[clean_sku_no_web], 93

    # Rule 4: PACK prefix removal with quantity extraction
    if sku.startswith('PACK'):
        clean_sku = sku[4:]

        # Extract quantity from product name using pattern "Pack N"
        pack_quantity = 1  # Default
        pack_match = re.search(r'Pack\s+(\d+)', product_name, re.IGNORECASE)
        if pack_match:
            pack_quantity = int(pack_match.group(1))

        if clean_sku in catalog_skus:
            return clean_sku, f'pack_prefix_removed', pack_quantity, product_map[clean_sku], 90
        if clean_sku in catalog_master_skus:
            return clean_sku, f'pack_prefix_removed+caja_master', pack_quantity, product_map[clean_sku], 90

    # Rule 5: "_WEB" suffix removal (96-100% confidence from analysis)
    if sku.endswith('_WEB'):
        clean_sku = sku[:-4]  # Remove "_WEB"
        if clean_sku in catalog_skus:
            return clean_sku, 'web_suffix_removed', 1, product_map[clean_sku], 96
        if clean_sku in catalog_master_skus:
            return clean_sku, 'web_suffix_removed+caja_master', 1, product_map[clean_sku], 96

    # Rule 6: Trailing "20" → "10" pattern (90% confidence)
    if sku.endswith('20') and not sku.endswith('010') and not sku.endswith('020'):
        clean_sku = sku[:-2] + '10'  # Replace last "20" with "10"
        if clean_sku in catalog_skus:
            return clean_sku, 'trailing_20_to_10', 1, product_map[clean_sku], 90
        if clean_sku in catalog_master_skus:
            return clean_sku, 'trailing_20_to_10+caja_master', 1, product_map[clean_sku], 90

    # Rule 7: Extra digits pattern (e.g., BABE_C028220 → BABE_C02810)
    # Pattern: ends with extra "0" like "28220" → "2810"
    extra_digit_match = re.match(r'^(.+)([0-9]{3})([0-9]{2})0$', sku)
    if extra_digit_match:
        clean_sku = extra_digit_match.group(1) + extra_digit_match.group(2) + '10'
        if clean_sku in catalog_skus:
            return clean_sku, 'extra_digits_removed', 1, product_map[clean_sku], 90
        if clean_sku in catalog_master_skus:
            return clean_sku, 'extra_digits_removed+caja_master', 1, product_map[clean_sku], 90

    # Rule 8: Cracker "1UES" variants (e.g., CRAA1UES → CRAA_U13510)
    cracker_match = re.match(r'^CR([A-Z]{2})1UES$', sku)
    if cracker_match:
        base_code = cracker_match.group(1)
        suggested_sku = f'CR{base_code}_U13510'
        if suggested_sku in catalog_skus:
            return suggested_sku, 'cracker_1ues_variant', 1, product_map[suggested_sku], 90
        if suggested_sku in catalog_master_skus:
            return suggested_sku, 'cracker_1ues_variant+caja_master', 1, product_map[suggested_sku], 90

    # Rule 8b: Lokal-specific cracker abbreviations (e.g., CRSA1UES → CRSM_U13510)
    # Lokal uses different abbreviations: SA=Sal de Mar (SM), PI=Pimienta (PM)
    lokal_cracker_mappings = {
        'CRSA1UES': 'CRSM_U13510',  # SA (Sal) → SM (Sal de Mar)
        'CRPI1UES': 'CRPM_U13510',  # PI (Pimienta) → PM (Pimienta)
    }
    if sku in lokal_cracker_mappings:
        target_sku = lokal_cracker_mappings[sku]
        if target_sku in catalog_skus:
            return target_sku, 'lokal_cracker_variant', 1, product_map[target_sku], 95
        if target_sku in catalog_master_skus:
            return target_sku, 'lokal_cracker_variant+caja_master', 1, product_map[target_sku], 95

    # Rule 9: Special case CRSM_U1000 → CRSM_U1000H (95% confidence)
    if sku == 'CRSM_U1000':
        target_sku = 'CRSM_U1000H'
        if target_sku in catalog_skus:
            return target_sku, 'special_crsm_bandeja', 1, product_map[target_sku], 95
        if target_sku in catalog_master_skus:
            return target_sku, 'special_crsm_bandeja+caja_master', 1, product_map[target_sku], 95

    # Rule 10: KEEPER_PIONEROS → KPMC_U30010 (95% confidence)
    if sku == 'KEEPER_PIONEROS':
        target_sku = 'KPMC_U30010'
        if target_sku in catalog_skus:
            return target_sku, 'keeper_pioneros_mapped', 1, product_map[target_sku], 95
        if target_sku in catalog_master_skus:
            return target_sku, 'keeper_pioneros_mapped+caja_master', 1, product_map[target_sku], 95

    # Rule 11: Language variant suffix (_C02010 → _C02020 for English variants)
    # Pattern: Some products have Spanish suffix *_C02010 but catalog has English *_C02020
    if '_C02010' in sku:
        variant_sku = sku.replace('_C02010', '_C02020')
        if variant_sku in catalog_skus:
            return variant_sku, 'language_variant_c02010_to_c02020', 1, product_map[variant_sku], 90
        if variant_sku in catalog_master_skus:
            return variant_sku, 'language_variant_c02010_to_c02020+caja_master', 1, product_map[variant_sku], 90

    # Rule 12: General substring matching (85% confidence)
    # If a catalog SKU appears as a substring in the original SKU, it's likely a match
    # Example: ANU-GRAL_C02020 contains GRAL_C02020 from catalog
    # This catches prefixes/suffixes we haven't explicitly handled
    for catalog_sku in sorted(catalog_skus, key=len, reverse=True):  # Check longest SKUs first to avoid partial matches
        if len(catalog_sku) >= 8 and catalog_sku in sku:  # Require minimum length to avoid false positives
            return catalog_sku, 'substring_match_unitary', 1, product_map[catalog_sku], 85

    for catalog_master_sku in sorted(catalog_master_skus, key=len, reverse=True):
        if len(catalog_master_sku) >= 8 and catalog_master_sku in sku:
            return catalog_master_sku, 'substring_match_master', 1, product_map[catalog_master_sku], 85

    # Rule 13: MercadoLibre product name matching (85% confidence)
    # Maps MLC publication IDs to Grana SKUs based on smart keyword analysis
    # Generated using product name similarity algorithm + manual verification
    mercadolibre_mappings = {
        'MLC1630337051': 'BABE_U20010',   # 80% - Barra Cereal Grana Sour Berries 5 Un
        'MLC1630349929': 'BACM_U04010',   # 90% - Barra Low Carb Grana Vegana De Cacao Y Maní
        'MLC1630349931': 'GRCA_U26010',   # 100% - Granola Keto Cacao 260g (marketed as Keto but is Low Carb)
        'MLC1630369169': 'CRPM_U13510',   # 95% - Galletas Crackers Grana Keto Sabor Pimienta 135g
        'MLC1630416135': 'BAMC_U04010',   # 70% - Barritas Grana Manzana Canela Display 5 Uds Vegana
        'MLC1644022833': 'GRCA_U26010',   # 90% - Granola Grana Low Carb Cacao Y Semillas
        'MLC2929973548': 'BAKC_U04010',   # 70% - Barras Keto Chocolate Nuez Grana 35g x16
        'MLC2930070644': 'GRCA_U26020',   # 75% - Granola Grana Cacao 260g
        'MLC2930199094': 'BAKC_U04010',   # 90% - Barritas Grana Keto Nuez Display 5 Uds
        'MLC2930200766': 'CRAA_U13510',   # 95% - Galletas Crackers Grana Keto Ajo Albahaca
        'MLC2930215860': 'CRSM_U13510',   # 95% - Galletas Crackers Grana Keto Sal De Mar
        'MLC2930238714': 'CRRO_U13510',   # 95% - Galletas Crackers Grana Keto Romero 135g
        'MLC2930251054': 'KSMC_U03010',   # 100% - Keeper Maní 30g X1 (individual units)
        'MLC2933751572': 'CRRO_U13510',   # 95% - Galletas Crackers Grana Keto Romero 135g
        'MLC2978631042': 'BACM_U04010',   # 90% - Barritas Grana Low Carb Cacao Maní Disp 5 Uds
        'MLC2978641268': 'GRBE_U26010',   # 90% - Granola Grana Low Carb Berries Y Semillas
        'MLC3016921654': 'KSMC_U03010',   # 100% - Keeper Maní 30g X1 (duplicate listing)
    }

    if source == 'mercadolibre' and sku in mercadolibre_mappings:
        target_sku = mercadolibre_mappings[sku]
        if target_sku in catalog_skus:
            return target_sku, 'ml_product_name_match', 1, product_map[target_sku], 85
        if target_sku in catalog_master_skus:
            return target_sku, 'ml_product_name_match+caja_master', 1, product_map[target_sku], 85

    # No match found
    return None, 'no_match', 1, None, 0


@router.get("/data")
async def get_audit_data(
    source: Optional[List[str]] = Query(None, description="Filter by source (relbase, shopify, mercadolibre) - supports multiple"),
    category: Optional[List[str]] = Query(None, description="Filter by product category/familia (BARRAS, CRACKERS, GRANOLAS, KEEPERS) - supports multiple"),
    channel: Optional[List[str]] = Query(None, description="Filter by channel name - supports multiple"),
    customer: Optional[List[str]] = Query(None, description="Filter by customer name - supports multiple"),
    sku: Optional[str] = Query(None, description="Search in multiple fields: Cliente, Producto, Pedido, Canal, Formato, SKU Original, SKU Primario"),
    sku_primario: Optional[List[str]] = Query(None, description="Filter by SKU Primario (mapped database column) - supports multiple"),
    has_nulls: Optional[bool] = Query(None, description="Show only records with NULL values"),
    not_in_catalog: Optional[bool] = Query(None, description="Show only SKUs not in catalog"),
    from_date: Optional[str] = Query(None, description="Start date for filtering (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date for filtering (YYYY-MM-DD format)"),
    group_by: Optional[str] = Query(None, description="Server-side aggregation: customer_name, sku_primario, category, channel_name, order_date"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows/groups to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get comprehensive audit data with all fields for validation.

    Returns order items with:
    - Order info (ID, date, total, source)
    - Customer info (ID, name, RUT)
    - Channel info (with priority: assigned > RelBase > NULL)
    - Product info (SKU, name, category, family, format)
    - Validation flags (NULL checks, catalog checks)

    The 'sku' parameter now searches across multiple fields:
    - Customer name (Cliente)
    - Product name (Producto)
    - Order number (Pedido)
    - Channel name (Canal)
    - Product SKU (SKU Original)
    - Format and SKU Primario (filtered post-enrichment)
    """

    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    # Load product catalog with CAJA MÁSTER support
    product_catalog, catalog_skus, catalog_master_skus, conversion_map = load_product_mapping()

    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:

                # Build WHERE clause based on filters
                where_clauses = []
                params = []

                # ✅ BASE FILTER: Only show RelBase data to avoid duplication
                where_clauses.append("o.source = 'relbase'")

                # ✅ INVOICE STATUS FILTER: Only show accepted invoices (exclude cancelled, declined, NULL)
                # This aligns with Sales Analytics endpoint and ensures data consistency
                where_clauses.append("o.invoice_status IN ('accepted', 'accepted_objection')")

                # Multi-value filters using IN operator
                if source:
                    placeholders = ','.join(['%s'] * len(source))
                    where_clauses.append(f"o.source IN ({placeholders})")
                    params.extend(source)

                # Category filter: Use CSV as source of truth instead of products table
                # This ensures consistency between filtering and enrichment
                # IMPORTANT: We need to get ALL unique SKUs from DB first, map them,
                # then filter by category to handle SKU variants (ANU- prefix, _WEB suffix, etc.)
                category_filter_skus = None
                if category:
                    # Step 1: Get all unique SKUs from DB
                    cursor.execute("""
                        SELECT DISTINCT oi.product_sku, oi.product_name, o.source
                        FROM orders o
                        JOIN order_items oi ON oi.order_id = o.id
                        WHERE oi.product_sku IS NOT NULL
                          AND oi.product_sku != ''
                    """)
                    all_db_skus = cursor.fetchall()

                    # Step 2: Map each SKU and filter by category
                    category_filter_skus = set()
                    for row in all_db_skus:
                        db_sku = row['product_sku']
                        product_name = row['product_name'] or ''
                        sku_source = row.get('source', '')

                        # Map SKU using same logic as enrichment
                        official_sku, _, _, product_info, _ = map_sku_with_quantity(
                            db_sku, product_name, product_catalog, catalog_skus, catalog_master_skus, sku_source
                        )

                        # Check if mapped SKU belongs to selected categories
                        if official_sku and product_info:
                            sku_category = product_info.get('category', '')
                            if sku_category in category:
                                category_filter_skus.add(db_sku)  # Add DB SKU (not official SKU)

                    # Step 3: Apply filter
                    if category_filter_skus:
                        placeholders = ','.join(['%s'] * len(category_filter_skus))
                        where_clauses.append(f"oi.product_sku IN ({placeholders})")
                        params.extend(list(category_filter_skus))
                    else:
                        # No SKUs found for these categories, return empty results
                        where_clauses.append("1=0")  # Always false condition

                if channel:
                    # For channel, use OR with ILIKE for partial matching
                    channel_conditions = ' OR '.join(['ch.name ILIKE %s'] * len(channel))
                    where_clauses.append(f"({channel_conditions})")
                    for ch in channel:
                        params.append(f"%{ch}%")

                if customer:
                    # For customer, use OR with ILIKE for partial matching
                    customer_conditions = ' OR '.join(['(cust_direct.name ILIKE %s OR cust_channel.name ILIKE %s)'] * len(customer))
                    where_clauses.append(f"({customer_conditions})")
                    for cust in customer:
                        params.append(f"%{cust}%")
                        params.append(f"%{cust}%")

                # SKU Primario filter (now using database column)
                if sku_primario:
                    placeholders = ','.join(['%s'] * len(sku_primario))
                    where_clauses.append(f"oi.sku_primario IN ({placeholders})")
                    params.extend(sku_primario)

                # Multi-field search: Cliente, Producto, Pedido, Canal, SKU Original
                if sku:
                    search_conditions = [
                        "COALESCE(cust_direct.name, cust_channel.name, '') ILIKE %s",  # Cliente
                        "oi.product_name ILIKE %s",                                     # Producto
                        "o.external_id ILIKE %s",                                       # Pedido
                        "ch.name ILIKE %s",                                             # Canal
                        "oi.product_sku ILIKE %s"                                       # SKU Original
                    ]
                    where_clauses.append(f"({' OR '.join(search_conditions)})")
                    # Add the same search term for each condition
                    for _ in range(len(search_conditions)):
                        params.append(f"%{sku}%")

                # Add has_nulls filter to SQL query
                if has_nulls:
                    where_clauses.append("""(
                        (cust_direct.id IS NULL AND cust_channel.id IS NULL) OR
                        o.channel_id IS NULL OR
                        oi.product_sku IS NULL OR
                        oi.product_sku = ''
                    )""")

                # Add date range filters
                if from_date and to_date:
                    where_clauses.append("o.order_date >= %s AND o.order_date <= %s")
                    params.append(from_date)
                    params.append(to_date)
                elif from_date:
                    where_clauses.append("o.order_date >= %s")
                    params.append(from_date)
                elif to_date:
                    where_clauses.append("o.order_date <= %s")
                    params.append(to_date)
                # No else clause - show ALL data when no date filter applied

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                # ===== SERVER-SIDE AGGREGATION MODE =====
                # When group_by is provided, return pre-aggregated groups instead of detail items
                # This ensures group totals are accurate across ALL data, not just current page

                # ===== SPECIAL CASE: SKU PRIMARIO AGGREGATION WITH CSV MAPPING =====
                # SKU Primario requires CSV-based mapping which can't be done in SQL
                # We fetch all filtered items, apply mapping, then aggregate in Python
                if group_by == 'sku_primario':
                    # Fetch all filtered items (reasonable limit to prevent memory issues)
                    fetch_query = f"""
                        SELECT
                            o.external_id as order_external_id,
                            oi.product_sku,
                            oi.product_name,
                            o.source as order_source,
                            oi.quantity,
                            oi.subtotal
                        FROM orders o
                        LEFT JOIN order_items oi ON oi.order_id = o.id
                        LEFT JOIN products p ON p.sku = oi.product_sku
                        LEFT JOIN channels ch ON ch.id = o.channel_id
                        LEFT JOIN customers cust_direct
                            ON cust_direct.id = o.customer_id
                            AND cust_direct.source = o.source
                        LEFT JOIN LATERAL (
                            SELECT customer_external_id
                            FROM customer_channel_rules ccr
                            WHERE ccr.channel_external_id::text = (
                                CASE
                                    WHEN o.customer_notes ~ '^\s*\\{{'
                                    THEN o.customer_notes::json->>'channel_id_relbase'
                                    ELSE NULL
                                END
                            )
                            AND ccr.is_active = TRUE
                            LIMIT 1
                        ) ccr_match ON true
                        LEFT JOIN customers cust_channel
                            ON cust_channel.external_id = ccr_match.customer_external_id
                            AND cust_channel.source = 'relbase'
                        WHERE {where_sql}
                        LIMIT 50000
                    """

                    cursor.execute(fetch_query, params)
                    all_items = cursor.fetchall()

                    # Apply CSV mapping and group in Python
                    from collections import defaultdict
                    groups = defaultdict(lambda: {
                        'pedidos': set(),
                        'cantidad': 0,
                        'total_revenue': 0
                    })

                    for item in all_items:
                        sku = item['product_sku']
                        product_name = item['product_name']
                        order_source = item['order_source']

                        # Map SKU to primario using same logic as enrichment
                        official_sku, _, _, _, _ = map_sku_with_quantity(
                            sku, product_name, product_catalog, catalog_skus, catalog_master_skus, order_source
                        )

                        # Get sku_primario
                        if official_sku:
                            sku_primario = get_sku_primario(official_sku, conversion_map)
                        else:
                            sku_primario = None

                        # Use 'SIN CLASIFICAR' for unmapped SKUs
                        group_key = sku_primario if sku_primario else 'SIN CLASIFICAR'

                        # Aggregate
                        groups[group_key]['pedidos'].add(item['order_external_id'])
                        groups[group_key]['cantidad'] += item['quantity'] or 0
                        groups[group_key]['total_revenue'] += float(item['subtotal'] or 0)

                    # Convert to list format
                    aggregated_data = []
                    service = get_product_catalog_service()
                    for group_value, stats in groups.items():
                        # Get product name for this SKU Primario
                        sku_primario_name = service.get_product_name_for_sku_primario(group_value) if group_value != 'SIN CLASIFICAR' else None

                        aggregated_data.append({
                            'group_value': group_value,
                            'sku_primario_name': sku_primario_name,
                            'pedidos': len(stats['pedidos']),
                            'cantidad': stats['cantidad'],
                            'total_revenue': stats['total_revenue']
                        })

                    # Sort by revenue descending
                    aggregated_data.sort(key=lambda x: x['total_revenue'], reverse=True)

                    # Apply pagination to groups
                    total_groups = len(aggregated_data)
                    paginated_groups = aggregated_data[offset:offset+limit]

                    # Calculate summary totals
                    total_pedidos = len(set(item['order_external_id'] for item in all_items))
                    total_quantity = sum(item['quantity'] or 0 for item in all_items)
                    total_revenue = sum(float(item['subtotal'] or 0) for item in all_items)

                    # Return aggregated response
                    return {
                        "status": "success",
                        "mode": "aggregated",
                        "group_by": "sku_primario",
                        "data": paginated_groups,
                        "summary": {
                            "total_pedidos": total_pedidos,
                            "total_unidades": total_quantity,
                            "total_revenue": total_revenue,
                            "total_groups": total_groups
                        },
                        "pagination": {
                            "limit": limit,
                            "offset": offset,
                            "total_items": total_groups,
                            "total_pages": (total_groups + limit - 1) // limit
                        }
                    }

                # Map frontend groupBy values to SQL group fields
                # sku_primario is handled above as a special case
                group_field_map = {
                    'customer_name': "COALESCE(cust_direct.name, cust_channel.name, 'SIN NOMBRE')",
                    'category': 'p.category',
                    'channel_name': "COALESCE(ch.name, 'SIN CANAL')",
                    'order_date': 'o.order_date::date'
                }

                if group_by and group_by in group_field_map:
                    # === AGGREGATED MODE ===
                    group_field = group_field_map[group_by]

                    # Aggregation query: GROUP BY first, then paginate
                    agg_query = f"""
                        SELECT
                            {group_field} as group_value,
                            COUNT(DISTINCT o.external_id) as pedidos,
                            SUM(oi.quantity) as cantidad,
                            SUM(oi.subtotal) as total_revenue
                        FROM orders o
                        LEFT JOIN order_items oi ON oi.order_id = o.id
                        LEFT JOIN products p ON p.sku = oi.product_sku
                        LEFT JOIN channels ch ON ch.id = o.channel_id
                        LEFT JOIN customers cust_direct
                            ON cust_direct.id = o.customer_id
                            AND cust_direct.source = o.source
                        LEFT JOIN LATERAL (
                            SELECT customer_external_id
                            FROM customer_channel_rules ccr
                            WHERE ccr.channel_external_id::text = (
                                CASE
                                    WHEN o.customer_notes ~ '^\s*\\{{'
                                    THEN o.customer_notes::json->>'channel_id_relbase'
                                    ELSE NULL
                                END
                            )
                            AND ccr.is_active = TRUE
                            LIMIT 1
                        ) ccr_match ON true
                        LEFT JOIN customers cust_channel
                            ON cust_channel.external_id = ccr_match.customer_external_id
                            AND cust_channel.source = 'relbase'
                        WHERE {where_sql}
                        GROUP BY {group_field}
                        HAVING {group_field} IS NOT NULL
                        ORDER BY total_revenue DESC
                        LIMIT %s OFFSET %s
                    """

                    # Execute aggregation query
                    params.extend([limit, offset])
                    cursor.execute(agg_query, params)
                    agg_rows = cursor.fetchall()

                    # Count total groups (not items!)
                    count_query = f"""
                        SELECT COUNT(*) as count FROM (
                            SELECT {group_field}
                            FROM orders o
                            LEFT JOIN order_items oi ON oi.order_id = o.id
                            LEFT JOIN products p ON p.sku = oi.product_sku
                            LEFT JOIN channels ch ON ch.id = o.channel_id
                            LEFT JOIN customers cust_direct
                                ON cust_direct.id = o.customer_id
                                AND cust_direct.source = o.source
                            LEFT JOIN LATERAL (
                                SELECT customer_external_id
                                FROM customer_channel_rules ccr
                                WHERE ccr.channel_external_id::text = (
                                    CASE
                                        WHEN o.customer_notes ~ '^\s*\\{{'
                                        THEN o.customer_notes::json->>'channel_id_relbase'
                                        ELSE NULL
                                    END
                                )
                                AND ccr.is_active = TRUE
                                LIMIT 1
                            ) ccr_match ON true
                            LEFT JOIN customers cust_channel
                                ON cust_channel.external_id = ccr_match.customer_external_id
                                AND cust_channel.source = 'relbase'
                            WHERE {where_sql}
                            GROUP BY {group_field}
                            HAVING {group_field} IS NOT NULL
                        ) subquery
                    """

                    cursor.execute(count_query, params[:-2])  # Exclude limit/offset
                    total_groups = cursor.fetchone()['count']

                    # Summary totals (same across ALL filtered data)
                    summary_query = f"""
                        SELECT
                            COUNT(DISTINCT o.external_id) as total_pedidos,
                            SUM(oi.quantity) as total_quantity,
                            SUM(oi.subtotal) as total_revenue
                        FROM orders o
                        LEFT JOIN order_items oi ON oi.order_id = o.id
                        LEFT JOIN products p ON p.sku = oi.product_sku
                        LEFT JOIN channels ch ON ch.id = o.channel_id
                        LEFT JOIN customers cust_direct
                            ON cust_direct.id = o.customer_id
                            AND cust_direct.source = o.source
                        LEFT JOIN LATERAL (
                            SELECT customer_external_id
                            FROM customer_channel_rules ccr
                            WHERE ccr.channel_external_id::text = (
                                CASE
                                    WHEN o.customer_notes ~ '^\s*\\{{'
                                    THEN o.customer_notes::json->>'channel_id_relbase'
                                    ELSE NULL
                                END
                            )
                            AND ccr.is_active = TRUE
                            LIMIT 1
                        ) ccr_match ON true
                        LEFT JOIN customers cust_channel
                            ON cust_channel.external_id = ccr_match.customer_external_id
                            AND cust_channel.source = 'relbase'
                        WHERE {where_sql}
                    """

                    cursor.execute(summary_query, params[:-2])  # Exclude limit/offset
                    summary_row = cursor.fetchone()

                    # Convert aggregated rows to dicts
                    aggregated_data = []
                    for row in agg_rows:
                        row_dict = dict(row)
                        # Convert Decimal to float for JSON serialization
                        row_dict['total_revenue'] = float(row_dict['total_revenue'] or 0)
                        aggregated_data.append(row_dict)

                    # Return aggregated response
                    return {
                        "status": "success",
                        "mode": "aggregated",
                        "group_by": group_by,
                        "data": aggregated_data,
                        "summary": {
                            "total_pedidos": summary_row['total_pedidos'] or 0,
                            "total_unidades": summary_row['total_quantity'] or 0,  # Note: approximation
                            "total_revenue": float(summary_row['total_revenue'] or 0),
                            "total_groups": total_groups
                        },
                        "pagination": {
                            "limit": limit,
                            "offset": offset,
                            "total_items": total_groups,  # Total groups, not items
                            "total_pages": (total_groups + limit - 1) // limit
                        }
                    }

                # ===== DETAIL MODE (No grouping) =====
                # Continue with existing logic for individual items

                # Pre-determine mapped SKUs if not_in_catalog filter is active
                mapped_skus_set = None
                if not_in_catalog:
                    # Get all unique SKUs with their product names and source
                    cursor.execute(f"""
                        SELECT DISTINCT oi.product_sku as sku, oi.product_name, o.source
                        FROM orders o
                        LEFT JOIN order_items oi ON oi.order_id = o.id
                        LEFT JOIN channels ch ON ch.id = o.channel_id
                        LEFT JOIN customers cust_direct
                            ON cust_direct.id = o.customer_id
                            AND cust_direct.source = o.source
                        LEFT JOIN LATERAL (
                            SELECT customer_external_id
                            FROM customer_channel_rules ccr
                            WHERE ccr.channel_external_id::text = (
                                CASE
                                    WHEN o.customer_notes ~ '^\\s*\\{{'
                                    THEN o.customer_notes::json->>'channel_id_relbase'
                                    ELSE NULL
                                END
                            )
                            AND ccr.is_active = TRUE
                            LIMIT 1
                        ) ccr_match ON true
                        LEFT JOIN customers cust_channel
                            ON cust_channel.external_id = ccr_match.customer_external_id
                            AND cust_channel.source = 'relbase'
                        WHERE {where_sql}
                          AND oi.product_sku IS NOT NULL
                          AND oi.product_sku != ''
                    """, params)
                    all_skus = cursor.fetchall()

                    # Determine which SKUs are mapped
                    mapped_skus_set = set()
                    unmapped_skus_set = set()
                    for row in all_skus:
                        sku_val = row['sku']
                        product_name = row['product_name'] or ''
                        sku_source = row.get('source', '')
                        official_sku, _, _, _, _ = map_sku_with_quantity(
                            sku_val, product_name, product_catalog, catalog_skus, catalog_master_skus, sku_source
                        )
                        if official_sku:
                            mapped_skus_set.add(sku_val)
                        else:
                            unmapped_skus_set.add(sku_val)

                    # Add filter to WHERE clause for unmapped SKUs only
                    if unmapped_skus_set:
                        # Use SQL IN clause for unmapped SKUs
                        placeholders = ','.join(['%s'] * len(unmapped_skus_set))
                        where_clauses.append(f"oi.product_sku IN ({placeholders})")
                        params.extend(list(unmapped_skus_set))
                        where_sql = " AND ".join(where_clauses)
                    else:
                        # No unmapped SKUs, return empty result
                        return {
                            "status": "success",
                            "data": [],
                            "meta": {
                                "total": 0,
                                "limit": limit,
                                "offset": offset,
                                "returned": 0,
                                "filters": {
                                    "source": source,
                                    "channel": channel,
                                    "customer": customer,
                                    "sku": sku,
                                    "has_nulls": has_nulls,
                                    "not_in_catalog": not_in_catalog,
                                    "from_date": from_date,
                                    "to_date": to_date
                                }
                            }
                        }

                # Main query with filters applied in SQL
                query = f"""
                    SELECT
                        -- Order info
                        o.id as order_id,
                        o.external_id as order_external_id,
                        o.order_date,
                        o.total as order_total,
                        o.source as order_source,

                        -- Customer info (improved with channel-based mapping)
                        COALESCE(
                            cust_direct.id::text,
                            cust_channel.id::text,
                            'NULL'
                        ) as customer_id,
                        COALESCE(
                            cust_direct.external_id,
                            cust_channel.external_id,
                            'NULL'
                        ) as customer_external_id,
                        COALESCE(
                            cust_direct.name,
                            cust_channel.name,
                            'SIN NOMBRE'
                        ) as customer_name,
                        CASE
                            WHEN cust_direct.id IS NOT NULL THEN 'direct'
                            WHEN cust_channel.id IS NOT NULL THEN 'channel_mapped'
                            ELSE 'null'
                        END as customer_source,

                        -- Channel info (enriched with channel names from channels table)
                        COALESCE(
                            ch.name,
                            'SIN CANAL'
                        ) as channel_name,
                        COALESCE(
                            o.channel_id::text,
                            'NULL'
                        ) as channel_id,
                        CASE
                            WHEN ch.name IS NOT NULL THEN 'relbase'
                            ELSE 'null'
                        END as channel_source,

                        -- Order Item info
                        oi.id as item_id,
                        oi.product_sku as sku,
                        oi.product_name,
                        oi.quantity,
                        ROUND(oi.subtotal / NULLIF(oi.quantity, 0), 2) as unit_price,  -- Real net unit price (after discounts, without IVA)
                        oi.subtotal as item_subtotal,

                        -- Product Mapping (will be enriched with CSV data)
                        p.category,
                        p.subfamily as family,
                        p.format,

                        -- Flags
                        CASE WHEN cust_direct.id IS NULL AND cust_channel.id IS NULL THEN true ELSE false END as customer_null,
                        CASE WHEN o.channel_id IS NULL THEN true ELSE false END as channel_null,
                        CASE WHEN oi.product_sku IS NULL OR oi.product_sku = '' THEN true ELSE false END as sku_null

                    FROM orders o
                    LEFT JOIN order_items oi ON oi.order_id = o.id
                    LEFT JOIN products p ON p.sku = oi.product_sku
                    LEFT JOIN channels ch ON ch.id = o.channel_id

                    -- Customer Joins (Direct + Channel-based mapping)
                    LEFT JOIN customers cust_direct
                        ON cust_direct.id = o.customer_id
                        AND cust_direct.source = o.source

                    -- Channel-based customer mapping via customer_channel_rules
                    LEFT JOIN LATERAL (
                        SELECT customer_external_id
                        FROM customer_channel_rules ccr
                        WHERE ccr.channel_external_id::text = (
                            CASE
                                WHEN o.customer_notes ~ '^\s*\{{'
                                THEN o.customer_notes::json->>'channel_id_relbase'
                                ELSE NULL
                            END
                        )
                        AND ccr.is_active = TRUE
                        LIMIT 1
                    ) ccr_match ON true

                    LEFT JOIN customers cust_channel
                        ON cust_channel.external_id = ccr_match.customer_external_id
                        AND cust_channel.source = 'relbase'

                    WHERE {where_sql}
                    ORDER BY o.order_date DESC, o.id, oi.id
                    LIMIT %s OFFSET %s
                """

                params.extend([limit, offset])
                cursor.execute(query, params)
                rows = cursor.fetchall()

                # Get total count for pagination with filters applied
                count_query = f"""
                    SELECT COUNT(DISTINCT oi.id)
                    FROM orders o
                    LEFT JOIN order_items oi ON oi.order_id = o.id
                    LEFT JOIN products p ON p.sku = oi.product_sku
                    LEFT JOIN channels ch ON ch.id = o.channel_id
                    LEFT JOIN customers cust_direct
                        ON cust_direct.id = o.customer_id
                        AND cust_direct.source = o.source
                    LEFT JOIN LATERAL (
                        SELECT customer_external_id
                        FROM customer_channel_rules ccr
                        WHERE ccr.channel_external_id::text = (
                            CASE
                                WHEN o.customer_notes ~ '^\s*\{{'
                                THEN o.customer_notes::json->>'channel_id_relbase'
                                ELSE NULL
                            END
                        )
                        AND ccr.is_active = TRUE
                        LIMIT 1
                    ) ccr_match ON true
                    LEFT JOIN customers cust_channel
                        ON cust_channel.external_id = ccr_match.customer_external_id
                        AND cust_channel.source = 'relbase'
                    WHERE {where_sql}
                """

                cursor.execute(count_query, params[:-2])  # Exclude limit/offset
                total_count = cursor.fetchone()['count']

                # ===== SUMMARY TOTALS QUERY =====
                # Calculate totals for ALL filtered data (not just current page)
                # This provides accurate totals for summary cards regardless of pagination
                summary_query = f"""
                    SELECT
                        COUNT(DISTINCT o.external_id) as total_pedidos,
                        SUM(oi.quantity) as total_quantity,
                        SUM(oi.subtotal) as total_revenue
                    FROM orders o
                    LEFT JOIN order_items oi ON oi.order_id = o.id
                    LEFT JOIN products p ON p.sku = oi.product_sku
                    LEFT JOIN channels ch ON ch.id = o.channel_id
                    LEFT JOIN customers cust_direct
                        ON cust_direct.id = o.customer_id
                        AND cust_direct.source = o.source
                    LEFT JOIN LATERAL (
                        SELECT customer_external_id
                        FROM customer_channel_rules ccr
                        WHERE ccr.channel_external_id::text = (
                            CASE
                                WHEN o.customer_notes ~ '^\s*\{{'
                                THEN o.customer_notes::json->>'channel_id_relbase'
                                ELSE NULL
                            END
                        )
                        AND ccr.is_active = TRUE
                        LIMIT 1
                    ) ccr_match ON true
                    LEFT JOIN customers cust_channel
                        ON cust_channel.external_id = ccr_match.customer_external_id
                        AND cust_channel.source = 'relbase'
                    WHERE {where_sql}
                """

                cursor.execute(summary_query, params[:-2])  # Exclude limit/offset
                summary_row = cursor.fetchone()

                # Extract summary values (will be refined with product mapping)
                filtered_totals = {
                    "total_pedidos": summary_row['total_pedidos'] or 0,
                    "total_quantity": summary_row['total_quantity'] or 0,  # Raw quantity (will adjust for unidades)
                    "total_revenue": float(summary_row['total_revenue'] or 0)
                }

                # Enrich with product catalog data using conservative mapping
                enriched_rows = []
                for row in rows:
                    row_dict = dict(row)
                    sku = row_dict.get('sku', '')
                    product_name = row_dict.get('product_name', '')
                    order_source = row_dict.get('order_source', '')
                    quantity = row_dict.get('quantity', 0)

                    # Apply conservative mapping with quantity extraction
                    official_sku, match_type, pack_qty, product_info, confidence = map_sku_with_quantity(
                        sku, product_name, product_catalog, catalog_skus, catalog_master_skus, order_source
                    )

                    if official_sku:
                        # Product successfully mapped
                        # Get SKU Primario
                        sku_primario = get_sku_primario(official_sku, conversion_map)

                        # Get SKU Primario Name (formatted)
                        service = get_product_catalog_service()
                        sku_primario_name = service.get_product_name_for_sku_primario(sku_primario) if sku_primario else None

                        # Calculate total units
                        unidades = calculate_units(official_sku, quantity, conversion_map)

                        row_dict['sku_primario'] = sku_primario
                        row_dict['sku_primario_name'] = sku_primario_name
                        row_dict['unidades'] = unidades
                        row_dict['pack_quantity'] = pack_qty
                        row_dict['match_type'] = match_type
                        row_dict['confidence'] = confidence
                        row_dict['category'] = product_info['category'] or row_dict.get('category')
                        row_dict['family'] = product_info['family'] or row_dict.get('family')
                        row_dict['format'] = product_info['format'] or row_dict.get('format')
                        row_dict['in_catalog'] = True

                        # Also include conversion factor for reference
                        # Phase 3: Get from ProductCatalogService
                        service = get_product_catalog_service()
                        catalog_product = service.get_product_info(official_sku)
                        if catalog_product:
                            # Use units_per_display for conversion factor
                            row_dict['conversion_factor'] = catalog_product.get('units_per_display', 1) or 1
                        else:
                            row_dict['conversion_factor'] = 1
                    else:
                        # Not mapped
                        row_dict['sku_primario'] = None
                        row_dict['sku_primario_name'] = None
                        row_dict['unidades'] = quantity  # Default to quantity if not mapped
                        row_dict['pack_quantity'] = 1
                        row_dict['match_type'] = 'no_match'
                        row_dict['confidence'] = 0
                        row_dict['in_catalog'] = False
                        row_dict['conversion_factor'] = 1

                    enriched_rows.append(row_dict)

                # NOTE: total_unidades uses quantity as approximation
                # TODO: For 100% accuracy, pre-compute conversion factors in database
                # Currently uses raw quantity which is conservative for multi-pack products
                filtered_totals["total_unidades"] = filtered_totals["total_quantity"]

                return {
                    "status": "success",
                    "data": enriched_rows,
                    "meta": {
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "returned": len(enriched_rows),
                        "filters": {
                            "source": source,
                            "category": category,
                            "channel": channel,
                            "customer": customer,
                            "sku": sku,
                            "has_nulls": has_nulls,
                            "not_in_catalog": not_in_catalog,
                            "from_date": from_date,
                            "to_date": to_date
                        }
                    },
                    "summary": {
                        "total_pedidos": filtered_totals["total_pedidos"],
                        "total_unidades": filtered_totals["total_unidades"],
                        "total_revenue": filtered_totals["total_revenue"]
                    }
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching audit data: {str(e)}")


@router.get("/filters")
async def get_available_filters():
    """
    Get available filter values (unique values for dropdowns).
    Returns unique sources, channels, customers, SKUs for filtering.
    """

    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:

                # Get unique sources
                cursor.execute("""
                    SELECT DISTINCT source
                    FROM orders
                    WHERE EXTRACT(YEAR FROM order_date) = 2025
                    ORDER BY source
                """)
                sources = [row['source'] for row in cursor.fetchall() if row['source']]

                # Get official Relbase channels that have 2025 data
                # Exclude channels with no orders in 2025 (EXPORTACIÓN, HORECA, MARKETPLACES)
                cursor.execute("""
                    SELECT DISTINCT ch.name as channel_name
                    FROM channels ch
                    INNER JOIN orders o ON o.channel_id = ch.id
                    WHERE ch.external_id IS NOT NULL
                      AND ch.source = 'relbase'
                      AND ch.is_active = true
                      AND o.source = 'relbase'
                      AND o.invoice_status IN ('accepted', 'accepted_objection')
                      AND EXTRACT(YEAR FROM o.order_date) = 2025
                    ORDER BY ch.name
                """)
                channels = [row['channel_name'] for row in cursor.fetchall()]

                # Always add "Sin Canal Asignado" as default for orders without channel
                channels.append('Sin Canal Asignado')

                # Get unique customers (limit to top 100 by order count)
                cursor.execute("""
                    SELECT cust.name as customer_name
                    FROM orders o
                    LEFT JOIN customers cust ON cust.id = o.customer_id
                    WHERE EXTRACT(YEAR FROM order_date) = 2025
                      AND cust.name IS NOT NULL
                    GROUP BY cust.name
                    ORDER BY COUNT(*) DESC
                    LIMIT 100
                """)
                customers = [row['customer_name'] for row in cursor.fetchall()]

                # Get unique SKUs (limit to top 100 by quantity sold)
                cursor.execute("""
                    SELECT oi.product_sku as sku
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE EXTRACT(YEAR FROM o.order_date) = 2025
                      AND oi.product_sku IS NOT NULL
                      AND oi.product_sku != ''
                    GROUP BY oi.product_sku
                    ORDER BY SUM(oi.quantity) DESC
                    LIMIT 100
                """)
                skus = [row['sku'] for row in cursor.fetchall()]

                return {
                    "status": "success",
                    "data": {
                        "sources": sources,
                        "channels": channels,
                        "customers": customers,
                        "skus": skus
                    }
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching filters: {str(e)}")


@router.get("/summary")
async def get_audit_summary():
    """
    Get audit summary statistics.
    Returns counts of NULL values, unmapped products, data quality metrics.
    Uses conservative mapping strategy to calculate actual coverage.
    """

    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    # Load product catalog with CAJA MÁSTER support
    product_catalog, catalog_skus, catalog_master_skus, conversion_map = load_product_mapping()

    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:

                # Total orders
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM orders
                    WHERE EXTRACT(YEAR FROM order_date) = 2025
                """)
                total_orders = cursor.fetchone()['total']

                # Orders with NULL customer
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM orders
                    WHERE EXTRACT(YEAR FROM order_date) = 2025
                      AND customer_id IS NULL
                """)
                null_customers = cursor.fetchone()['total']

                # Orders with NULL channel
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM orders o
                    WHERE EXTRACT(YEAR FROM order_date) = 2025
                      AND o.channel_id IS NULL
                """)
                null_channels = cursor.fetchone()['total']

                # Order items with NULL or empty SKU
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE EXTRACT(YEAR FROM o.order_date) = 2025
                      AND (oi.product_sku IS NULL OR oi.product_sku = '')
                """)
                null_skus = cursor.fetchone()['total']

                # Unique SKUs
                cursor.execute("""
                    SELECT COUNT(DISTINCT oi.product_sku) as total
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE EXTRACT(YEAR FROM o.order_date) = 2025
                      AND oi.product_sku IS NOT NULL
                      AND oi.product_sku != ''
                """)
                unique_skus = cursor.fetchone()['total']

                # Get all SKUs with product names and source for mapping
                cursor.execute("""
                    SELECT DISTINCT oi.product_sku as sku, oi.product_name, o.source
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE EXTRACT(YEAR FROM o.order_date) = 2025
                      AND oi.product_sku IS NOT NULL
                      AND oi.product_sku != ''
                """)
                all_skus = cursor.fetchall()

                # Apply conservative mapping to determine which SKUs are actually unmapped
                unmapped_skus = []
                mapped_skus = []
                for row in all_skus:
                    sku = row['sku']
                    product_name = row['product_name'] or ''
                    sku_source = row.get('source', '')

                    official_sku, match_type, pack_qty, product_info, confidence = map_sku_with_quantity(
                        sku, product_name, product_catalog, catalog_skus, catalog_master_skus, sku_source
                    )

                    if official_sku:
                        mapped_skus.append(sku)
                    else:
                        unmapped_skus.append(sku)

                return {
                    "status": "success",
                    "data": {
                        "total_orders": total_orders,
                        "data_quality": {
                            "null_customers": null_customers,
                            "null_channels": null_channels,
                            "null_skus": null_skus,
                            "completeness_pct": round((1 - (null_customers + null_channels + null_skus) / (total_orders * 3)) * 100, 2) if total_orders > 0 else 0
                        },
                        "product_mapping": {
                            "unique_skus": unique_skus,
                            "mapped_skus": len(mapped_skus),
                            "not_in_catalog": len(unmapped_skus),
                            "catalog_coverage_pct": round((len(mapped_skus) / unique_skus) * 100, 2) if unique_skus > 0 else 0,
                            "unmapped_skus_sample": unmapped_skus[:20]  # First 20 unmapped SKUs
                        }
                    }
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching audit summary: {str(e)}")
