"""
Debug Mapping API
Visual debugging tool for SKU mapping and unit conversion

Purpose:
- See orders with full mapping breakdown
- Visualize how packs/displays/caja master convert to units
- Identify mapping problems in real-time
"""
from fastapi import APIRouter, Query
from typing import Optional, List
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_mapping_debug(sku: str, quantity: int, source: str = None) -> dict:
    """
    Get detailed mapping debug info for a SKU.
    Shows every step of the mapping process.
    """
    from app.services.product_catalog_service import ProductCatalogService
    from app.services.sku_mapping_service import get_sku_mapping_service

    debug = {
        "original_sku": sku,
        "original_quantity": quantity,
        "source": source,
        "steps": [],
        "final_result": None
    }

    service = ProductCatalogService()
    mapping_service = get_sku_mapping_service()
    catalog = service._get_catalog()
    master_lookup = service._master_sku_lookup or {}

    # Step 1: Check direct catalog match
    if sku in catalog:
        product = catalog[sku]
        debug["steps"].append({
            "step": 1,
            "action": "DIRECT_CATALOG_MATCH",
            "matched": True,
            "details": {
                "sku": sku,
                "product_name": product.get('product_name'),
                "category": product.get('category'),
                "units_per_display": product.get('units_per_display', 1),
                "sku_primario": product.get('primario')
            }
        })
        units = quantity * (product.get('units_per_display', 1) or 1)
        debug["final_result"] = {
            "mapped_sku": sku,
            "match_type": "direct",
            "quantity": quantity,
            "multiplier": 1,
            "conversion_factor": product.get('units_per_display', 1) or 1,
            "total_units": units,
            "formula": f"{quantity} × 1 × {product.get('units_per_display', 1) or 1} = {units}"
        }
        return debug
    else:
        debug["steps"].append({
            "step": 1,
            "action": "DIRECT_CATALOG_MATCH",
            "matched": False,
            "details": {"searched_for": sku}
        })

    # Step 2: Check caja master match
    if sku in master_lookup:
        product = master_lookup[sku]
        items_per_box = product.get('items_per_master_box', 1) or 1
        debug["steps"].append({
            "step": 2,
            "action": "CAJA_MASTER_MATCH",
            "matched": True,
            "details": {
                "sku_master": sku,
                "base_sku": product.get('sku'),
                "product_name": product.get('product_name'),
                "category": product.get('category'),
                "items_per_master_box": items_per_box,
                "sku_primario": product.get('primario')
            }
        })
        units = quantity * items_per_box
        debug["final_result"] = {
            "mapped_sku": product.get('sku'),
            "match_type": "caja_master",
            "quantity": quantity,
            "multiplier": 1,
            "conversion_factor": items_per_box,
            "total_units": units,
            "formula": f"{quantity} × {items_per_box} (items/CM) = {units}"
        }
        return debug
    else:
        debug["steps"].append({
            "step": 2,
            "action": "CAJA_MASTER_MATCH",
            "matched": False,
            "details": {"searched_for": sku}
        })

    # Step 3: Check sku_mappings table
    mapping_result = mapping_service.map_sku(sku, source)
    if mapping_result:
        target_sku = mapping_result.target_sku
        multiplier = mapping_result.quantity_multiplier or 1

        # Get target SKU info
        target_info = catalog.get(target_sku) or master_lookup.get(target_sku) or {}
        is_target_master = target_sku in master_lookup

        if is_target_master:
            conversion = target_info.get('items_per_master_box', 1) or 1
        else:
            conversion = target_info.get('units_per_display', 1) or 1

        debug["steps"].append({
            "step": 3,
            "action": "SKU_MAPPING_RULE",
            "matched": True,
            "details": {
                "rule_id": mapping_result.rule_id,
                "rule_name": mapping_result.rule_name,
                "pattern_type": mapping_result.match_type,
                "source_pattern": sku,
                "target_sku": target_sku,
                "quantity_multiplier": multiplier,
                "confidence": mapping_result.confidence,
                "target_info": {
                    "product_name": target_info.get('product_name'),
                    "category": target_info.get('category'),
                    "is_caja_master": is_target_master,
                    "conversion_factor": conversion
                }
            }
        })

        units = quantity * multiplier * conversion
        debug["final_result"] = {
            "mapped_sku": target_sku,
            "match_type": f"sku_mapping_{mapping_result.match_type}",
            "quantity": quantity,
            "multiplier": multiplier,
            "conversion_factor": conversion,
            "total_units": units,
            "formula": f"{quantity} × {multiplier} (mapping) × {conversion} (conv) = {units}"
        }
        return debug
    else:
        debug["steps"].append({
            "step": 3,
            "action": "SKU_MAPPING_RULE",
            "matched": False,
            "details": {"searched_for": sku, "source": source}
        })

    # Step 4: No match found
    debug["steps"].append({
        "step": 4,
        "action": "NO_MATCH",
        "matched": False,
        "details": {"sku": sku, "status": "UNMAPPED"}
    })

    debug["final_result"] = {
        "mapped_sku": None,
        "match_type": "unmapped",
        "quantity": quantity,
        "multiplier": 1,
        "conversion_factor": 1,
        "total_units": quantity,
        "formula": f"{quantity} × 1 = {quantity} (no mapping)"
    }

    return debug


@router.get("/debug/sku/{sku}")
async def debug_single_sku(
    sku: str,
    quantity: int = Query(default=1, description="Test quantity"),
    source: str = Query(default=None, description="Order source (relbase, shopify, etc.)")
):
    """
    Debug a single SKU mapping.
    Shows step-by-step how the SKU is mapped and units calculated.
    """
    debug = get_mapping_debug(sku.upper(), quantity, source)
    return {
        "status": "success",
        "debug": debug
    }


@router.get("/debug/orders")
async def debug_recent_orders(
    limit: int = Query(default=10, le=50),
    days: int = Query(default=7, le=30),
    source: str = Query(default="relbase"),
    show_mapped_only: bool = Query(default=False),
    show_unmapped_only: bool = Query(default=False)
):
    """
    Get recent orders with full mapping debug for each item.
    Perfect for visualizing how orders are being processed.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        from_date = datetime.now() - timedelta(days=days)

        # Get recent orders
        cursor.execute("""
            SELECT
                o.id,
                o.external_id,
                o.order_date,
                o.source,
                o.total,
                o.invoice_status,
                c.name as customer_name,
                ch.name as channel_name
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            LEFT JOIN channels ch ON ch.id = o.channel_id
            WHERE o.source = %s
              AND o.order_date >= %s
              AND o.invoice_status IN ('accepted', 'accepted_objection')
            ORDER BY o.order_date DESC
            LIMIT %s
        """, (source, from_date, limit))

        orders = cursor.fetchall()

        result = []
        for order in orders:
            # Get order items
            cursor.execute("""
                SELECT
                    id,
                    product_sku,
                    product_name,
                    quantity,
                    unit_price,
                    subtotal
                FROM order_items
                WHERE order_id = %s
            """, (order['id'],))

            items = cursor.fetchall()

            order_debug = {
                "order": {
                    "id": order['id'],
                    "external_id": order['external_id'],
                    "date": order['order_date'].isoformat() if order['order_date'] else None,
                    "customer": order['customer_name'],
                    "channel": order['channel_name'],
                    "total": float(order['total'] or 0),
                    "status": order['invoice_status']
                },
                "items": [],
                "summary": {
                    "total_items": len(items),
                    "mapped_items": 0,
                    "unmapped_items": 0,
                    "total_quantity": 0,
                    "total_units": 0
                }
            }

            for item in items:
                sku = item['product_sku'] or ''
                quantity = item['quantity'] or 0

                # Get mapping debug
                mapping_debug = get_mapping_debug(sku.upper(), quantity, source)

                is_mapped = mapping_debug["final_result"]["match_type"] != "unmapped"

                # Filter logic
                if show_mapped_only and not is_mapped:
                    continue
                if show_unmapped_only and is_mapped:
                    continue

                item_debug = {
                    "item_id": item['id'],
                    "sku": sku,
                    "product_name": item['product_name'],
                    "quantity": quantity,
                    "unit_price": float(item['unit_price'] or 0),
                    "subtotal": float(item['subtotal'] or 0),
                    "mapping": mapping_debug
                }

                order_debug["items"].append(item_debug)
                order_debug["summary"]["total_quantity"] += quantity
                order_debug["summary"]["total_units"] += mapping_debug["final_result"]["total_units"]

                if is_mapped:
                    order_debug["summary"]["mapped_items"] += 1
                else:
                    order_debug["summary"]["unmapped_items"] += 1

            # Update total items count based on filters
            order_debug["summary"]["total_items"] = len(order_debug["items"])

            if order_debug["items"]:  # Only add if has items after filtering
                result.append(order_debug)

        cursor.close()
        conn.close()

        # Global summary
        global_summary = {
            "orders_count": len(result),
            "total_items": sum(o["summary"]["total_items"] for o in result),
            "mapped_items": sum(o["summary"]["mapped_items"] for o in result),
            "unmapped_items": sum(o["summary"]["unmapped_items"] for o in result),
            "mapping_coverage": 0
        }

        if global_summary["total_items"] > 0:
            global_summary["mapping_coverage"] = round(
                global_summary["mapped_items"] / global_summary["total_items"] * 100, 1
            )

        return {
            "status": "success",
            "filters": {
                "source": source,
                "days": days,
                "limit": limit,
                "from_date": from_date.isoformat()
            },
            "global_summary": global_summary,
            "orders": result
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/debug/unmapped-skus")
async def get_unmapped_skus(
    days: int = Query(default=30, le=90),
    source: str = Query(default="relbase"),
    limit: int = Query(default=50, le=200)
):
    """
    Get list of unmapped SKUs sorted by revenue impact.
    Helps prioritize which SKUs to map first.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        from_date = datetime.now() - timedelta(days=days)

        # Get all unique SKUs from recent orders
        cursor.execute("""
            SELECT
                oi.product_sku as sku,
                oi.product_name,
                COUNT(DISTINCT o.id) as order_count,
                SUM(oi.quantity) as total_quantity,
                SUM(oi.subtotal) as total_revenue
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.source = %s
              AND o.order_date >= %s
              AND o.invoice_status IN ('accepted', 'accepted_objection')
            GROUP BY oi.product_sku, oi.product_name
            ORDER BY total_revenue DESC
        """, (source, from_date))

        all_skus = cursor.fetchall()
        cursor.close()
        conn.close()

        # Check mapping status for each
        unmapped = []
        for sku_row in all_skus:
            sku = sku_row['sku'] or ''
            debug = get_mapping_debug(sku.upper(), 1, source)

            if debug["final_result"]["match_type"] == "unmapped":
                unmapped.append({
                    "sku": sku,
                    "product_name": sku_row['product_name'],
                    "order_count": sku_row['order_count'],
                    "total_quantity": sku_row['total_quantity'],
                    "total_revenue": float(sku_row['total_revenue'] or 0),
                    "mapping_steps": debug["steps"]
                })

            if len(unmapped) >= limit:
                break

        return {
            "status": "success",
            "filters": {
                "source": source,
                "days": days,
                "from_date": from_date.isoformat()
            },
            "summary": {
                "total_unmapped": len(unmapped),
                "total_revenue_unmapped": sum(s["total_revenue"] for s in unmapped)
            },
            "unmapped_skus": unmapped
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/debug/catalog-coverage")
async def get_catalog_coverage():
    """
    Overview of product catalog coverage.
    Shows stats about the catalog and mapping rules.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Catalog stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_products,
                COUNT(CASE WHEN sku_master IS NOT NULL THEN 1 END) as products_with_master,
                COUNT(DISTINCT category) as categories,
                COUNT(CASE WHEN units_per_display > 1 THEN 1 END) as display_products,
                COUNT(CASE WHEN items_per_master_box IS NOT NULL THEN 1 END) as master_box_products
            FROM product_catalog
            WHERE is_active = TRUE
        """)
        catalog_stats = cursor.fetchone()

        # Category breakdown
        cursor.execute("""
            SELECT
                category,
                COUNT(*) as count,
                COUNT(CASE WHEN sku_master IS NOT NULL THEN 1 END) as with_master
            FROM product_catalog
            WHERE is_active = TRUE
            GROUP BY category
            ORDER BY count DESC
        """)
        categories = cursor.fetchall()

        # SKU mappings stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_rules,
                COUNT(CASE WHEN pattern_type = 'exact' THEN 1 END) as exact_rules,
                COUNT(CASE WHEN quantity_multiplier > 1 THEN 1 END) as pack_rules,
                COUNT(DISTINCT source_filter) as source_filters
            FROM sku_mappings
            WHERE is_active = TRUE
        """)
        mapping_stats = cursor.fetchone()

        # Pack rules detail
        cursor.execute("""
            SELECT
                source_pattern,
                target_sku,
                quantity_multiplier,
                rule_name
            FROM sku_mappings
            WHERE is_active = TRUE
              AND quantity_multiplier > 1
            ORDER BY quantity_multiplier DESC
            LIMIT 20
        """)
        pack_rules = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "catalog": {
                "total_products": catalog_stats['total_products'],
                "products_with_caja_master": catalog_stats['products_with_master'],
                "display_products": catalog_stats['display_products'],
                "master_box_products": catalog_stats['master_box_products'],
                "categories_count": catalog_stats['categories']
            },
            "categories": [dict(c) for c in categories],
            "sku_mappings": {
                "total_rules": mapping_stats['total_rules'],
                "exact_match_rules": mapping_stats['exact_rules'],
                "pack_rules": mapping_stats['pack_rules'],
                "source_filters": mapping_stats['source_filters']
            },
            "pack_rules": [dict(p) for p in pack_rules]
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
