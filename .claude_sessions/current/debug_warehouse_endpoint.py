#!/usr/bin/env python3
"""Debug script to trace the exact source of 'list index out of range' error"""

import sys
sys.path.insert(0, '/home/paul/projects/Grana/Grana_Platform/backend')

import os
os.chdir('/home/paul/projects/Grana/Grana_Platform/backend')

from app.core.database import get_db_connection_dict_with_retry

def test_step_by_step():
    conn = None
    cursor = None

    try:
        print("Step 1: Getting connection...")
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()
        print(f"  Cursor type: {type(cursor)}")

        # Step 2: Check if tables/views exist
        print("\nStep 2: Checking if tables/views exist...")
        cursor.execute("""
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_name IN ('product_inventory_settings', 'inventory_planning_facts', 'sales_facts_mv')
              AND table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print(f"  Found: {tables}")

        # Step 3: Test minimal query
        print("\nStep 3: Testing minimal main query (first 5 rows)...")
        cursor.execute("""
            WITH raw_inventory AS (
                SELECT
                    p.sku as original_sku,
                    p.name as original_name,
                    w.code as warehouse_code,
                    SUM(ws.quantity) as raw_quantity
                FROM warehouse_stock ws
                JOIN products p ON p.id = ws.product_id
                JOIN warehouses w ON w.id = ws.warehouse_id
                WHERE w.is_active = true
                  AND w.source = 'relbase'
                  AND w.external_id IS NOT NULL
                  AND p.is_active = true
                GROUP BY p.sku, p.name, w.code
            )
            SELECT * FROM raw_inventory LIMIT 5
        """)
        raw = cursor.fetchall()
        print(f"  Raw inventory rows: {len(raw)}")

        # Step 4: Test the main query from warehouses.py
        print("\nStep 4: Testing FULL main query...")
        query = """
            WITH raw_inventory AS (
                SELECT
                    p.sku as original_sku,
                    p.name as original_name,
                    w.code as warehouse_code,
                    SUM(ws.quantity) as raw_quantity,
                    COUNT(ws.id) as lot_count,
                    MAX(ws.last_updated) as last_updated
                FROM warehouse_stock ws
                JOIN products p ON p.id = ws.product_id
                JOIN warehouses w ON w.id = ws.warehouse_id
                WHERE w.is_active = true
                  AND w.source = 'relbase'
                  AND w.external_id IS NOT NULL
                  AND p.is_active = true
                GROUP BY p.sku, p.name, w.code
            ),
            mapped_inventory AS (
                SELECT
                    ri.original_sku,
                    ri.original_name,
                    ri.warehouse_code,
                    ri.raw_quantity,
                    ri.lot_count,
                    ri.last_updated,
                    COALESCE(sm.target_sku, ri.original_sku) as mapped_sku,
                    COALESCE(sm.quantity_multiplier, 1) as multiplier,
                    sm.rule_name as mapping_rule
                FROM raw_inventory ri
                LEFT JOIN sku_mappings sm
                    ON sm.source_pattern = UPPER(ri.original_sku)
                    AND sm.pattern_type = 'exact'
                    AND sm.is_active = TRUE
            ),
            aggregated_per_warehouse AS (
                SELECT
                    mapped_sku as sku,
                    warehouse_code,
                    SUM(raw_quantity * multiplier) as adjusted_quantity,
                    SUM(lot_count) as lot_count,
                    MAX(last_updated) as last_updated,
                    array_agg(DISTINCT original_sku ORDER BY original_sku) as original_skus
                FROM mapped_inventory
                GROUP BY mapped_sku, warehouse_code
            ),
            sku_mapping_details AS (
                SELECT
                    mapped_sku as sku,
                    original_sku,
                    MAX(original_name) as original_name,
                    bool_or(mapping_rule IS NOT NULL) as is_mapped,
                    MAX(CASE WHEN mapping_rule IS NOT NULL THEN mapped_sku ELSE NULL END) as target_sku,
                    MAX(CASE WHEN mapping_rule IS NOT NULL THEN multiplier ELSE NULL END) as multiplier,
                    MAX(mapping_rule) as rule_name,
                    SUM(raw_quantity) as raw_quantity,
                    SUM(raw_quantity * multiplier) as adjusted_quantity
                FROM mapped_inventory
                GROUP BY mapped_sku, original_sku
            ),
            aggregated_total AS (
                SELECT
                    sku,
                    json_object_agg(warehouse_code, adjusted_quantity) as warehouses,
                    SUM(adjusted_quantity) as stock_total,
                    SUM(lot_count) as lot_count,
                    MAX(last_updated) as last_updated,
                    (SELECT array_agg(DISTINCT os ORDER BY os)
                     FROM aggregated_per_warehouse apw2,
                          unnest(apw2.original_skus) as os
                     WHERE apw2.sku = aggregated_per_warehouse.sku) as original_skus,
                    (SELECT json_agg(
                        json_build_object(
                            'sku', smd.original_sku,
                            'name', smd.original_name,
                            'is_mapped', smd.is_mapped,
                            'target_sku', smd.target_sku,
                            'multiplier', smd.multiplier,
                            'rule_name', smd.rule_name,
                            'raw_quantity', smd.raw_quantity,
                            'adjusted_quantity', smd.adjusted_quantity
                        ) ORDER BY smd.original_sku
                     )
                     FROM sku_mapping_details smd
                     WHERE smd.sku = aggregated_per_warehouse.sku) as original_skus_detail
                FROM aggregated_per_warehouse
                GROUP BY sku
            ),
            final AS (
                SELECT
                    at.sku,
                    at.original_skus,
                    at.original_skus_detail,
                    COALESCE(
                        pc.product_name,
                        pc_master.master_box_name,
                        (SELECT name FROM products WHERE sku = at.sku LIMIT 1),
                        at.sku
                    ) as name,
                    COALESCE(
                        pc.category,
                        CASE WHEN pc_master.sku IS NOT NULL THEN 'CAJA MASTER' END,
                        (SELECT category FROM products WHERE sku = at.sku LIMIT 1)
                    ) as category,
                    NULL as subfamily,
                    COALESCE(at.warehouses, '{}'::json) as warehouses,
                    COALESCE(at.stock_total, 0) as stock_total,
                    COALESCE(at.lot_count, 0) as lot_count,
                    at.last_updated,
                    COALESCE(pc.sku_value, pc_master.sku_value, 0) as sku_value,
                    COALESCE(at.stock_total, 0) * COALESCE(pc.sku_value, pc_master.sku_value, 0) as valor,
                    COALESCE(
                        (SELECT min_stock FROM products WHERE sku = at.sku AND is_active = true LIMIT 1),
                        0
                    ) as min_stock,
                    COALESCE(pis.estimation_months, 6) as estimation_months,
                    COALESCE(
                        (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                         FROM sales_facts_mv sfm
                         WHERE sfm.original_sku = at.sku
                           AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))),
                        0
                    ) as recommended_min_stock,
                    COALESCE(ipf.stock_usable, at.stock_total, 0) as stock_usable,
                    COALESCE(ipf.stock_expiring_30d, 0) as stock_expiring_30d,
                    COALESCE(ipf.stock_expired, 0) as stock_expired,
                    ipf.earliest_expiration,
                    ipf.days_to_earliest_expiration,
                    CASE
                        WHEN COALESCE(
                            (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                             FROM sales_facts_mv sfm
                             WHERE sfm.original_sku = at.sku
                               AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))),
                            0
                        ) > 0 THEN
                            ROUND(COALESCE(ipf.stock_usable, at.stock_total, 0)::NUMERIC * 30 /
                                  (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                                   FROM sales_facts_mv sfm
                                   WHERE sfm.original_sku = at.sku
                                     AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))))::INTEGER
                        ELSE 999
                    END as days_of_coverage,
                    GREATEST(0,
                        ROUND(COALESCE(
                            (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                             FROM sales_facts_mv sfm
                             WHERE sfm.original_sku = at.sku
                               AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))),
                            0
                        ) * 1.2 - COALESCE(ipf.stock_usable, at.stock_total, 0))::INTEGER
                    ) as production_needed,
                    CASE WHEN pc.sku IS NOT NULL OR pc_master.sku IS NOT NULL THEN true ELSE false END as in_catalog,
                    COALESCE(pc.is_inventory_active, pc_master.is_inventory_active, true) as is_inventory_active
                FROM aggregated_total at
                LEFT JOIN product_catalog pc
                    ON pc.sku = at.sku
                    AND pc.is_active = TRUE
                LEFT JOIN product_catalog pc_master
                    ON pc_master.sku_master = at.sku
                    AND pc_master.is_active = TRUE
                    AND pc.sku IS NULL
                LEFT JOIN product_inventory_settings pis
                    ON pis.sku = at.sku
                LEFT JOIN inventory_planning_facts ipf
                    ON ipf.sku = at.sku
            )
            SELECT *
            FROM final
            WHERE is_inventory_active = true
              AND stock_total > 0
            ORDER BY category NULLS LAST, name
        """
        cursor.execute(query)
        products = cursor.fetchall()
        print(f"  Products returned: {len(products)}")
        print(f"  Products type: {type(products)}")
        if products:
            print(f"  First product type: {type(products[0])}")
            print(f"  First product keys: {list(products[0].keys()) if hasattr(products[0], 'keys') else 'NO KEYS'}")

        # Step 5: Test the summary query
        print("\nStep 5: Testing summary query...")
        cursor.execute("""
            WITH mapped_stock AS (
                SELECT
                    COALESCE(sm.target_sku, p.sku) as mapped_sku,
                    ws.quantity * COALESCE(sm.quantity_multiplier, 1) as adjusted_qty,
                    pc.sku_value
                FROM warehouse_stock ws
                JOIN products p ON p.id = ws.product_id
                JOIN warehouses w ON w.id = ws.warehouse_id
                LEFT JOIN sku_mappings sm ON sm.source_pattern = UPPER(p.sku)
                    AND sm.pattern_type = 'exact' AND sm.is_active = TRUE
                LEFT JOIN product_catalog pc ON pc.sku = COALESCE(sm.target_sku, p.sku)
                    AND pc.is_active = TRUE
                WHERE w.is_active = true AND w.source = 'relbase' AND p.is_active = true
            )
            SELECT
                COUNT(DISTINCT mapped_sku) as total_products,
                COALESCE(SUM(adjusted_qty), 0) as total_stock,
                COUNT(DISTINCT CASE WHEN adjusted_qty > 0 THEN mapped_sku END) as products_with_stock,
                (SELECT COUNT(DISTINCT id) FROM warehouses WHERE is_active = true AND source = 'relbase') as active_warehouses,
                COALESCE(SUM(adjusted_qty * COALESCE(sku_value, 0)), 0) as total_valor
            FROM mapped_stock
        """)
        summary = cursor.fetchone()
        print(f"  Summary: {summary}")
        print(f"  Summary type: {type(summary)}")

        # Step 6: Test expiration stats query
        print("\nStep 6: Testing expiration stats query...")
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN expiration_status = 'Expired' THEN 1 END) as expired_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expired' THEN quantity ELSE 0 END), 0) as expired_units,
                COUNT(CASE WHEN expiration_status = 'Expiring Soon' THEN 1 END) as expiring_soon_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Expiring Soon' THEN quantity ELSE 0 END), 0) as expiring_soon_units,
                COUNT(CASE WHEN expiration_status = 'Valid' THEN 1 END) as valid_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'Valid' THEN quantity ELSE 0 END), 0) as valid_units,
                COUNT(CASE WHEN expiration_status = 'No Date' THEN 1 END) as no_date_lots,
                COALESCE(SUM(CASE WHEN expiration_status = 'No Date' THEN quantity ELSE 0 END), 0) as no_date_units
            FROM warehouse_stock_by_lot
            WHERE warehouse_code IN (
                SELECT code FROM warehouses
                WHERE is_active = true
                  AND source = 'relbase'
                  AND external_id IS NOT NULL
            )
        """)
        expiration_stats = cursor.fetchone()
        print(f"  Expiration stats: {expiration_stats}")
        print(f"  Expiration stats type: {type(expiration_stats)}")

        # Step 7: Build the response like the endpoint does
        print("\nStep 7: Building response...")
        try:
            response = {
                "status": "success",
                "data": products,
                "summary": {
                    **summary,
                    "expiration": expiration_stats
                }
            }
            print(f"  Response built successfully!")
            print(f"  Response summary keys: {list(response['summary'].keys())}")
        except Exception as e:
            print(f"  ERROR building response: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "="*60)
        print("ALL STEPS COMPLETED SUCCESSFULLY!")
        print("="*60)

    except Exception as e:
        print(f"\n!!! ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    test_step_by_step()
