"""
Inventory Planning API Endpoints
Provides production recommendations based on sales projections and inventory levels

Author: TM3
Date: 2025-12-28
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db_connection_dict_with_retry

router = APIRouter(prefix="/api/v1/inventory-planning", tags=["inventory-planning"])


@router.get("/production-recommendations")
async def get_production_recommendations(
    category: Optional[str] = Query(None, description="Filter by category"),
    urgency: Optional[str] = Query(None, description="Filter by urgency: critical, high, medium, low"),
    only_needing_production: bool = Query(True, description="Only show products that need production"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Get production recommendations for inventory planning.

    Returns products sorted by urgency with production recommendations based on:
    - Current usable stock (excluding expired and expiring soon)
    - Sales projections (based on configurable estimation period)
    - Days of coverage remaining
    - Production needed to meet target stock

    Urgency levels:
    - critical: < 15 days coverage
    - high: 15-30 days coverage
    - medium: 30-60 days coverage
    - low: > 60 days coverage

    Returns:
        {
            "status": "success",
            "summary": {
                "products_needing_production": 15,
                "total_units_needed": 5000,
                "critical_count": 3,
                "high_count": 5,
                "expiring_units": 500
            },
            "data": [...]
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Build filter conditions
        filter_conditions = ["is_inventory_active = true", "stock_total > 0"]
        params = []

        if category:
            filter_conditions.append("category = %s")
            params.append(category)

        if only_needing_production:
            filter_conditions.append("production_needed > 0")

        if urgency:
            urgency_map = {
                "critical": "days_of_coverage < 15",
                "high": "days_of_coverage >= 15 AND days_of_coverage < 30",
                "medium": "days_of_coverage >= 30 AND days_of_coverage < 60",
                "low": "days_of_coverage >= 60"
            }
            if urgency in urgency_map:
                filter_conditions.append(urgency_map[urgency])

        filter_clause = " AND ".join(filter_conditions)

        # Main query - similar to warehouse-inventory but optimized for production planning
        query = f"""
            WITH inventory_data AS (
                SELECT
                    at.sku,
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
                    COALESCE(at.stock_total, 0) as stock_total,
                    COALESCE(pis.estimation_months, 6) as estimation_months,
                    COALESCE(
                        (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                         FROM sales_facts_mv sfm
                         WHERE sfm.original_sku = at.sku
                           AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))),
                        0
                    ) as avg_monthly_sales,
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
                FROM (
                    -- Get aggregated stock per SKU
                    SELECT
                        COALESCE(sm.target_sku, p.sku) as sku,
                        SUM(ws.quantity * COALESCE(sm.quantity_multiplier, 1)) as stock_total
                    FROM warehouse_stock ws
                    JOIN products p ON p.id = ws.product_id AND p.is_active = true
                    JOIN warehouses w ON w.id = ws.warehouse_id
                        AND w.is_active = true
                        AND w.source = 'relbase'
                        AND w.external_id IS NOT NULL
                    LEFT JOIN sku_mappings sm
                        ON sm.source_pattern = UPPER(p.sku)
                        AND sm.pattern_type = 'exact'
                        AND sm.is_active = TRUE
                    GROUP BY COALESCE(sm.target_sku, p.sku)
                ) at
                LEFT JOIN product_catalog pc ON pc.sku = at.sku AND pc.is_active = TRUE
                LEFT JOIN product_catalog pc_master ON pc_master.sku_master = at.sku AND pc_master.is_active = TRUE AND pc.sku IS NULL
                LEFT JOIN product_inventory_settings pis ON pis.sku = at.sku
                LEFT JOIN inventory_planning_facts ipf ON ipf.sku = at.sku
            )
            SELECT
                sku,
                name,
                category,
                stock_total,
                estimation_months,
                avg_monthly_sales,
                stock_usable,
                stock_expiring_30d,
                stock_expired,
                earliest_expiration,
                days_to_earliest_expiration,
                days_of_coverage,
                production_needed,
                -- Coverage type: distinguishes between calculated coverage and no sales data
                CASE
                    WHEN avg_monthly_sales = 0 THEN 'no_sales_data'
                    ELSE 'calculated'
                END as coverage_type,
                -- Urgency classification
                CASE
                    WHEN days_of_coverage < 15 THEN 'critical'
                    WHEN days_of_coverage < 30 THEN 'high'
                    WHEN days_of_coverage < 60 THEN 'medium'
                    ELSE 'low'
                END as urgency
            FROM inventory_data
            WHERE {filter_clause}
            ORDER BY
                CASE
                    WHEN days_of_coverage < 15 THEN 1
                    WHEN days_of_coverage < 30 THEN 2
                    WHEN days_of_coverage < 60 THEN 3
                    ELSE 4
                END,
                production_needed DESC
            LIMIT %s OFFSET %s
        """

        params.extend([limit, offset])

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        products = cursor.fetchall()

        # Get summary statistics
        summary_query = """
            WITH inventory_data AS (
                SELECT
                    COALESCE(ipf.stock_usable, at.stock_total, 0) as stock_usable,
                    COALESCE(ipf.stock_expiring_30d, 0) as stock_expiring_30d,
                    GREATEST(0,
                        ROUND(COALESCE(
                            (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                             FROM sales_facts_mv sfm
                             WHERE sfm.original_sku = at.sku
                               AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))),
                            0
                        ) * 1.2 - COALESCE(ipf.stock_usable, at.stock_total, 0))::INTEGER
                    ) as production_needed,
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
                    END as days_of_coverage
                FROM (
                    SELECT
                        COALESCE(sm.target_sku, p.sku) as sku,
                        SUM(ws.quantity * COALESCE(sm.quantity_multiplier, 1)) as stock_total
                    FROM warehouse_stock ws
                    JOIN products p ON p.id = ws.product_id AND p.is_active = true
                    JOIN warehouses w ON w.id = ws.warehouse_id
                        AND w.is_active = true AND w.source = 'relbase' AND w.external_id IS NOT NULL
                    LEFT JOIN sku_mappings sm ON sm.source_pattern = UPPER(p.sku)
                        AND sm.pattern_type = 'exact' AND sm.is_active = TRUE
                    GROUP BY COALESCE(sm.target_sku, p.sku)
                ) at
                LEFT JOIN product_catalog pc ON pc.sku = at.sku AND pc.is_active = TRUE
                LEFT JOIN product_inventory_settings pis ON pis.sku = at.sku
                LEFT JOIN inventory_planning_facts ipf ON ipf.sku = at.sku
                WHERE COALESCE(pc.is_inventory_active, true) = true
                  AND at.stock_total > 0
            )
            SELECT
                COUNT(CASE WHEN production_needed > 0 THEN 1 END) as products_needing_production,
                COALESCE(SUM(CASE WHEN production_needed > 0 THEN production_needed END), 0) as total_units_needed,
                COUNT(CASE WHEN days_of_coverage < 15 THEN 1 END) as critical_count,
                COUNT(CASE WHEN days_of_coverage >= 15 AND days_of_coverage < 30 THEN 1 END) as high_count,
                COUNT(CASE WHEN days_of_coverage >= 30 AND days_of_coverage < 60 THEN 1 END) as medium_count,
                COALESCE(SUM(stock_expiring_30d), 0) as expiring_units
            FROM inventory_data
        """

        cursor.execute(summary_query)
        summary = cursor.fetchone()

        return {
            "status": "success",
            "summary": {
                "products_needing_production": summary['products_needing_production'] or 0,
                "total_units_needed": summary['total_units_needed'] or 0,
                "critical_count": summary['critical_count'] or 0,
                "high_count": summary['high_count'] or 0,
                "medium_count": summary['medium_count'] or 0,
                "expiring_units": summary['expiring_units'] or 0
            },
            "count": len(products),
            "limit": limit,
            "offset": offset,
            "data": products
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching production recommendations: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/categories")
async def get_inventory_categories():
    """
    Get list of categories for filtering in production planning.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT category
            FROM product_catalog
            WHERE is_active = true AND category IS NOT NULL
            ORDER BY category
        """)

        categories = [row['category'] for row in cursor.fetchall()]

        return {
            "status": "success",
            "data": categories
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/lot-breakdown/{sku}")
async def get_lot_breakdown(sku: str):
    """
    Get detailed lot breakdown for a specific SKU.

    Returns all lots with expiration dates, quantities, and risk analysis.
    Used for the expandable row detail view in production planning.

    Returns:
        {
            "status": "success",
            "sku": "BABE_U04010",
            "name": "Barra Low Carb Berries X1",
            "total_stock": 12023,
            "stock_usable": 12023,
            "avg_monthly_sales": 8913,
            "days_of_coverage": 40,
            "lots": [
                {
                    "lot_number": "222",
                    "warehouse_code": "amplifica_centro",
                    "warehouse_name": "AMPLIFICA SANTIAGO CENTRO",
                    "quantity": 5000,
                    "expiration_date": "2026-06-30",
                    "days_to_expiration": 167,
                    "status": "Valid",
                    "at_risk": false
                }
            ],
            "expiration_schedule": [
                { "date": "2026-06-30", "units": 5000, "cumulative": 5000 }
            ],
            "risk_analysis": {
                "units_at_risk": 0,
                "risk_message": "Al ritmo actual, todo el stock se vendera antes de vencer"
            }
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Get product info and sales data
        product_query = """
            WITH product_sales AS (
                SELECT
                    COALESCE(
                        (SELECT ROUND(SUM(sfm.units_sold)::NUMERIC / COALESCE(pis.estimation_months, 6))::INTEGER
                         FROM sales_facts_mv sfm
                         WHERE sfm.original_sku = %s
                           AND sfm.order_date >= CURRENT_DATE - MAKE_INTERVAL(months => COALESCE(pis.estimation_months, 6))),
                        0
                    ) as avg_monthly_sales,
                    COALESCE(pis.estimation_months, 6) as estimation_months
                FROM (SELECT 1) dummy
                LEFT JOIN product_inventory_settings pis ON pis.sku = %s
            )
            SELECT
                COALESCE(pc.product_name, p.name, %s) as name,
                COALESCE(pc.category, p.category) as category,
                ps.avg_monthly_sales,
                ps.estimation_months
            FROM product_sales ps
            LEFT JOIN product_catalog pc ON pc.sku = %s AND pc.is_active = TRUE
            LEFT JOIN products p ON p.sku = %s AND p.is_active = TRUE
        """
        cursor.execute(product_query, (sku, sku, sku, sku, sku))
        product_info = cursor.fetchone()

        if not product_info:
            raise HTTPException(status_code=404, detail=f"Product {sku} not found")

        avg_monthly_sales = product_info['avg_monthly_sales'] or 0

        # Get lot-level inventory data
        lots_query = """
            SELECT
                ws.lot_number,
                w.code as warehouse_code,
                w.name as warehouse_name,
                ws.quantity,
                ws.expiration_date,
                CASE
                    WHEN ws.expiration_date IS NOT NULL
                    THEN ws.expiration_date - CURRENT_DATE
                    ELSE NULL
                END as days_to_expiration,
                CASE
                    WHEN ws.expiration_date IS NULL THEN 'Sin fecha'
                    WHEN ws.expiration_date < CURRENT_DATE THEN 'Vencido'
                    WHEN ws.expiration_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'Por vencer'
                    WHEN ws.expiration_date <= CURRENT_DATE + INTERVAL '60 days' THEN 'Proximo'
                    ELSE 'Vigente'
                END as status
            FROM warehouse_stock ws
            JOIN products p ON p.id = ws.product_id AND p.is_active = true
            JOIN warehouses w ON w.id = ws.warehouse_id AND w.is_active = true
            LEFT JOIN sku_mappings sm ON sm.source_pattern = UPPER(p.sku)
                AND sm.pattern_type = 'exact' AND sm.is_active = TRUE
            WHERE (COALESCE(sm.target_sku, p.sku) = %s OR p.sku = %s)
              AND ws.lot_number IS NOT NULL
              AND ws.quantity > 0
            ORDER BY ws.expiration_date NULLS LAST, ws.lot_number
        """
        cursor.execute(lots_query, (sku, sku))
        lots_data = cursor.fetchall()

        # Calculate totals
        total_stock = sum(lot['quantity'] for lot in lots_data)

        # Calculate stock_usable (excluding expired and expiring soon)
        stock_usable = sum(
            lot['quantity'] for lot in lots_data
            if lot['status'] not in ('Vencido', 'Por vencer')
        )

        # Calculate days of coverage
        days_of_coverage = None
        if avg_monthly_sales > 0:
            days_of_coverage = round(stock_usable * 30 / avg_monthly_sales)

        # Calculate sell-through date (when current stock will be sold out at current rate)
        sell_through_days = None
        if avg_monthly_sales > 0:
            sell_through_days = round(stock_usable * 30 / avg_monthly_sales)

        # Build lots response with at_risk flag
        lots_response = []
        cumulative_sold = 0
        daily_sales = avg_monthly_sales / 30 if avg_monthly_sales > 0 else 0

        for lot in lots_data:
            lot_dict = dict(lot)

            # Calculate if this lot is at risk of expiring before being sold
            # Based on FIFO - we sell oldest lots first
            if daily_sales > 0 and lot['days_to_expiration'] is not None:
                # Days until we start selling this lot (after selling previous lots)
                days_to_reach_lot = cumulative_sold / daily_sales if daily_sales > 0 else 0
                # Days to sell through this lot
                days_to_sell_lot = lot['quantity'] / daily_sales if daily_sales > 0 else 0

                # Lot is at risk if it will expire before we finish selling it
                lot_dict['at_risk'] = (days_to_reach_lot + days_to_sell_lot) > lot['days_to_expiration']
            else:
                lot_dict['at_risk'] = False

            # Convert date to string for JSON
            if lot_dict['expiration_date']:
                lot_dict['expiration_date'] = lot_dict['expiration_date'].isoformat()

            lots_response.append(lot_dict)
            cumulative_sold += lot['quantity']

        # Build expiration schedule (grouped by date)
        expiration_schedule = []
        schedule_by_date = {}
        for lot in lots_data:
            if lot['expiration_date']:
                date_str = lot['expiration_date'].isoformat()
                if date_str not in schedule_by_date:
                    schedule_by_date[date_str] = 0
                schedule_by_date[date_str] += lot['quantity']

        cumulative = 0
        for date_str in sorted(schedule_by_date.keys()):
            units = schedule_by_date[date_str]
            cumulative += units
            expiration_schedule.append({
                "date": date_str,
                "units": units,
                "cumulative": cumulative
            })

        # Risk analysis
        units_at_risk = sum(lot['quantity'] for lot in lots_response if lot.get('at_risk', False))

        if avg_monthly_sales == 0:
            risk_message = "Sin datos de venta - no se puede calcular riesgo de vencimiento"
        elif units_at_risk > 0:
            risk_message = f"{units_at_risk:,} unidades podrian vencer antes de venderse al ritmo actual"
        else:
            risk_message = "Al ritmo actual, todo el stock se vendera antes de vencer"

        return {
            "status": "success",
            "sku": sku,
            "name": product_info['name'],
            "category": product_info['category'],
            "total_stock": total_stock,
            "stock_usable": stock_usable,
            "avg_monthly_sales": avg_monthly_sales,
            "estimation_months": product_info['estimation_months'],
            "days_of_coverage": days_of_coverage,
            "lots": lots_response,
            "expiration_schedule": expiration_schedule,
            "risk_analysis": {
                "units_at_risk": units_at_risk,
                "risk_message": risk_message
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching lot breakdown: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
