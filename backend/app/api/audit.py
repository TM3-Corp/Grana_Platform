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
    """Load Códigos_Grana_Final.csv for product validation"""
    csv_path = Path(__file__).parent.parent.parent.parent / 'public/Archivos_Compartidos/Códigos_Grana_Final.csv'

    product_map = {}

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row.get('SKU') or row.get('Código')
                if sku:
                    product_map[sku] = {
                        'category': row.get('Categoría', ''),
                        'family': row.get('Familia', ''),
                        'format': row.get('Formato', ''),
                        'product_name': row.get('Producto', row.get('Nombre', '')),
                        'in_catalog': True
                    }
    except FileNotFoundError:
        print(f"Warning: Product catalog CSV not found at {csv_path}")

    return product_map


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

    # Load product catalog
    product_catalog = load_product_mapping()

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
                    where_clauses.append("(COALESCE(c.assigned_channel_name, o.channel_name) ILIKE %s)")
                    params.append(f"%{channel}%")

                if customer:
                    where_clauses.append("cust.name ILIKE %s")
                    params.append(f"%{customer}%")

                if sku:
                    where_clauses.append("oi.sku ILIKE %s")
                    params.append(f"%{sku}%")

                # Add 2025 filter
                where_clauses.append("EXTRACT(YEAR FROM o.order_date) = 2025")

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                # Main query
                query = f"""
                    SELECT
                        -- Order info
                        o.id as order_id,
                        o.external_id as order_external_id,
                        o.order_date,
                        o.total as order_total,
                        o.source as order_source,

                        -- Customer info (with priority logic)
                        COALESCE(cust.id::text, 'NULL') as customer_id,
                        COALESCE(cust.external_id, 'NULL') as customer_external_id,
                        COALESCE(cust.name, 'SIN NOMBRE') as customer_name,
                        COALESCE(cust.rut, 'NULL') as customer_rut,

                        -- Channel info (with priority: assigned > relbase > NULL)
                        COALESCE(
                            c.assigned_channel_name,
                            o.channel_name,
                            'SIN CANAL'
                        ) as channel_name,
                        COALESCE(
                            c.assigned_channel_id::text,
                            o.channel_id::text,
                            'NULL'
                        ) as channel_id,
                        CASE
                            WHEN c.assigned_channel_name IS NOT NULL THEN 'assigned'
                            WHEN o.channel_name IS NOT NULL THEN 'relbase'
                            ELSE 'null'
                        END as channel_source,

                        -- Order Item info
                        oi.id as item_id,
                        oi.sku,
                        oi.product_name,
                        oi.quantity,
                        oi.unit_price,
                        oi.subtotal as item_subtotal,

                        -- Product Mapping (will be enriched with CSV data)
                        p.category,
                        p.family,
                        p.format,

                        -- Flags
                        CASE WHEN cust.id IS NULL THEN true ELSE false END as customer_null,
                        CASE WHEN o.channel_id IS NULL AND c.assigned_channel_id IS NULL THEN true ELSE false END as channel_null,
                        CASE WHEN oi.sku IS NULL OR oi.sku = '' THEN true ELSE false END as sku_null

                    FROM orders o
                    LEFT JOIN customers cust ON cust.id = o.customer_id AND cust.source = o.source
                    LEFT JOIN customers c ON c.id = o.customer_id
                    LEFT JOIN order_items oi ON oi.order_id = o.id
                    LEFT JOIN products p ON p.sku = oi.sku
                    WHERE {where_sql}
                    ORDER BY o.order_date DESC, o.id, oi.id
                    LIMIT %s OFFSET %s
                """

                params.extend([limit, offset])
                cursor.execute(query, params)
                rows = cursor.fetchall()

                # Get total count for pagination
                count_query = f"""
                    SELECT COUNT(DISTINCT oi.id)
                    FROM orders o
                    LEFT JOIN customers cust ON cust.id = o.customer_id AND cust.source = o.source
                    LEFT JOIN customers c ON c.id = o.customer_id
                    LEFT JOIN order_items oi ON oi.order_id = o.id
                    WHERE {where_sql}
                """

                cursor.execute(count_query, params[:-2])  # Exclude limit/offset
                total_count = cursor.fetchone()['count']

                # Enrich with product catalog data
                enriched_rows = []
                for row in rows:
                    row_dict = dict(row)
                    sku = row_dict.get('sku', '')

                    # Check if SKU exists in catalog
                    if sku and sku in product_catalog:
                        catalog_data = product_catalog[sku]
                        # Update with catalog data (override database if available)
                        row_dict['category'] = catalog_data['category'] or row_dict.get('category')
                        row_dict['family'] = catalog_data['family'] or row_dict.get('family')
                        row_dict['format'] = catalog_data['format'] or row_dict.get('format')
                        row_dict['in_catalog'] = True
                    else:
                        row_dict['in_catalog'] = False

                    # Post-filter for has_nulls
                    if has_nulls:
                        if not (row_dict['customer_null'] or row_dict['channel_null'] or row_dict['sku_null']):
                            continue

                    # Post-filter for not_in_catalog
                    if not_in_catalog:
                        if row_dict['in_catalog']:
                            continue

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

                # Get unique channels (with priority logic)
                cursor.execute("""
                    SELECT DISTINCT
                        COALESCE(c.assigned_channel_name, o.channel_name, 'SIN CANAL') as channel_name
                    FROM orders o
                    LEFT JOIN customers c ON c.id = o.customer_id
                    WHERE EXTRACT(YEAR FROM order_date) = 2025
                    ORDER BY channel_name
                """)
                channels = [row['channel_name'] for row in cursor.fetchall()]

                # Get unique customers (limit to top 100 by order count)
                cursor.execute("""
                    SELECT DISTINCT cust.name as customer_name
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
                    SELECT DISTINCT oi.sku
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE EXTRACT(YEAR FROM o.order_date) = 2025
                      AND oi.sku IS NOT NULL
                      AND oi.sku != ''
                    GROUP BY oi.sku
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
    """

    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    product_catalog = load_product_mapping()

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
                    LEFT JOIN customers c ON c.id = o.customer_id
                    WHERE EXTRACT(YEAR FROM order_date) = 2025
                      AND o.channel_id IS NULL
                      AND c.assigned_channel_id IS NULL
                """)
                null_channels = cursor.fetchone()['total']

                # Order items with NULL or empty SKU
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE EXTRACT(YEAR FROM o.order_date) = 2025
                      AND (oi.sku IS NULL OR oi.sku = '')
                """)
                null_skus = cursor.fetchone()['total']

                # Unique SKUs
                cursor.execute("""
                    SELECT COUNT(DISTINCT oi.sku) as total
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE EXTRACT(YEAR FROM o.order_date) = 2025
                      AND oi.sku IS NOT NULL
                      AND oi.sku != ''
                """)
                unique_skus = cursor.fetchone()['total']

                # SKUs not in catalog
                cursor.execute("""
                    SELECT DISTINCT oi.sku
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE EXTRACT(YEAR FROM o.order_date) = 2025
                      AND oi.sku IS NOT NULL
                      AND oi.sku != ''
                """)
                all_skus = cursor.fetchall()
                unmapped_skus = [row['sku'] for row in all_skus if row['sku'] not in product_catalog]

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
                            "in_catalog": len(product_catalog),
                            "not_in_catalog": len(unmapped_skus),
                            "catalog_coverage_pct": round((1 - len(unmapped_skus) / unique_skus) * 100, 2) if unique_skus > 0 else 0,
                            "unmapped_skus_sample": unmapped_skus[:20]  # First 20 unmapped SKUs
                        }
                    }
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching audit summary: {str(e)}")
