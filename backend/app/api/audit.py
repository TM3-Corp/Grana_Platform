"""
API endpoint for data auditing
Provides comprehensive data validation and integrity checking
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import os
from pathlib import Path
import csv
import psycopg2
from psycopg2.extras import RealDictCursor

router = APIRouter()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

# Load product mapping from CSV
def load_product_mapping():
    """Load Codigos_Grana_Ingles.csv for product validation (includes CAJA MÁSTER and bilingual SKUs)"""
    csv_path = Path(__file__).parent.parent.parent.parent / 'public/Archivos_Compartidos/Codigos_Grana_Ingles.csv'

    product_map = {}
    catalog_skus = set()
    catalog_master_skus = set()

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normal SKU
                sku = row.get('SKU', '').strip()
                if sku:
                    catalog_skus.add(sku)
                    product_map[sku] = {
                        'category': row.get('CATEGORÍA', ''),
                        'family': row.get('PRODUCTO', ''),
                        'format': row.get('TIPO ENVASE UNID', ''),
                        'product_name': row.get('PRODUCTO', ''),
                        'in_catalog': True,
                        'tipo': 'Normal'
                    }

                # CAJA MÁSTER SKU
                master_sku = row.get('SKU CAJA MÁSTER', '').strip()
                if master_sku:
                    catalog_master_skus.add(master_sku)
                    product_map[master_sku] = {
                        'category': row.get('CATEGORÍA', ''),
                        'family': row.get('NOMBRE CAJA MÁSTER', ''),
                        'format': 'CAJA MASTER',
                        'product_name': row.get('NOMBRE CAJA MÁSTER', ''),
                        'in_catalog': True,
                        'tipo': 'Caja Master'
                    }
    except FileNotFoundError:
        print(f"Warning: Product catalog CSV not found at {csv_path}")

    return product_map, catalog_skus, catalog_master_skus


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
    source: Optional[str] = Query(None, description="Filter by source (relbase, shopify, mercadolibre)"),
    channel: Optional[str] = Query(None, description="Filter by channel name"),
    customer: Optional[str] = Query(None, description="Filter by customer name"),
    sku: Optional[str] = Query(None, description="Filter by SKU"),
    has_nulls: Optional[bool] = Query(None, description="Show only records with NULL values"),
    not_in_catalog: Optional[bool] = Query(None, description="Show only SKUs not in catalog"),
    limit: int = Query(1000, ge=1, le=10000, description="Max rows to return"),
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
    """

    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    # Load product catalog with CAJA MÁSTER support
    product_catalog, catalog_skus, catalog_master_skus = load_product_mapping()

    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:

                # Build WHERE clause based on filters
                where_clauses = []
                params = []

                if source:
                    where_clauses.append("o.source = %s")
                    params.append(source)

                if channel:
                    where_clauses.append("(ch.name ILIKE %s)")
                    params.append(f"%{channel}%")

                if customer:
                    where_clauses.append("(cust_direct.name ILIKE %s OR cust_channel.name ILIKE %s)")
                    params.append(f"%{customer}%")
                    params.append(f"%{customer}%")

                if sku:
                    where_clauses.append("oi.product_sku ILIKE %s")
                    params.append(f"%{sku}%")

                # Add has_nulls filter to SQL query
                if has_nulls:
                    where_clauses.append("""(
                        (cust_direct.id IS NULL AND cust_channel.id IS NULL) OR
                        o.channel_id IS NULL OR
                        oi.product_sku IS NULL OR
                        oi.product_sku = ''
                    )""")

                # Add 2025 filter
                where_clauses.append("EXTRACT(YEAR FROM o.order_date) = 2025")

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

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
                                    "not_in_catalog": not_in_catalog
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
                        oi.unit_price,
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

                # Enrich with product catalog data using conservative mapping
                enriched_rows = []
                for row in rows:
                    row_dict = dict(row)
                    sku = row_dict.get('sku', '')
                    product_name = row_dict.get('product_name', '')
                    order_source = row_dict.get('order_source', '')

                    # Apply conservative mapping with quantity extraction
                    official_sku, match_type, pack_qty, product_info, confidence = map_sku_with_quantity(
                        sku, product_name, product_catalog, catalog_skus, catalog_master_skus, order_source
                    )

                    if official_sku:
                        # Product successfully mapped
                        row_dict['sku_primario'] = official_sku
                        row_dict['pack_quantity'] = pack_qty
                        row_dict['match_type'] = match_type
                        row_dict['confidence'] = confidence
                        row_dict['category'] = product_info['category'] or row_dict.get('category')
                        row_dict['family'] = product_info['family'] or row_dict.get('family')
                        row_dict['format'] = product_info['format'] or row_dict.get('format')
                        row_dict['in_catalog'] = True
                    else:
                        # Not mapped
                        row_dict['sku_primario'] = None
                        row_dict['pack_quantity'] = 1
                        row_dict['match_type'] = 'no_match'
                        row_dict['confidence'] = 0
                        row_dict['in_catalog'] = False

                    enriched_rows.append(row_dict)

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
                            "channel": channel,
                            "customer": customer,
                            "sku": sku,
                            "has_nulls": has_nulls,
                            "not_in_catalog": not_in_catalog
                        }
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

                # Get unique channels
                cursor.execute("""
                    SELECT DISTINCT
                        COALESCE(ch.name, 'SIN CANAL') as channel_name
                    FROM orders o
                    LEFT JOIN channels ch ON ch.id = o.channel_id
                    WHERE EXTRACT(YEAR FROM order_date) = 2025
                    ORDER BY channel_name
                """)
                channels = [row['channel_name'] for row in cursor.fetchall()]

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
    product_catalog, catalog_skus, catalog_master_skus = load_product_mapping()

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
