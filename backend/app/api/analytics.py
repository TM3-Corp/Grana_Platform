"""
Analytics API Endpoints
Provides quarterly breakdown data for dashboard visualizations

Author: TM3
Date: 2025-12-11
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.core.database import get_db_connection_dict_with_retry

router = APIRouter()

# Product family icons mapping
PRODUCT_FAMILY_ICONS = {
    'BARRAS': '🍫',
    'GRANOLAS': '🥣',
    'CRACKERS': '🍘',
    'KEEPERS': '🍪',
    'OTROS': '📦'
}

# Channel icons mapping
CHANNEL_ICONS = {
    'ECOMMERCE': '🛒',
    'RETAIL': '🏪',
    'CORPORATIVO': '🏢',
    'DISTRIBUIDOR': '🚚',
    'EMPORIOS Y CAFETERIAS': '☕',
    'OTROS': '📦'
}


@router.get("/quarterly-breakdown")
async def get_quarterly_breakdown(
    year: Optional[int] = Query(None, description="Year to analyze (default: current year)")
):
    """
    Get quarterly breakdown of sales by:
    - Product Family (Barras, Granolas, Crackers, Keepers)
    - Channel (Retail, Ecommerce, Corporativo, etc.)
    - Top 10 Customers by revenue

    Each breakdown includes revenue, units, and orders per quarter.

    For incomplete quarters (e.g., Q4 when December is not finished),
    includes MTD metadata and estimated full quarter values.
    """
    try:
        # Default to current year if not specified
        if year is None:
            year = datetime.now().year

        # Check if we're in an incomplete quarter for this year
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_day = now.day

        # Determine if Q4 is incomplete (we're in Oct, Nov, or Dec of the requested year)
        is_current_year = (year == current_year)
        is_q4_incomplete = is_current_year and current_month in [10, 11, 12]

        # MTD metadata for incomplete quarters
        mtd_metadata = None
        if is_q4_incomplete:
            mtd_metadata = {
                'is_incomplete': True,
                'current_month': current_month,
                'current_day': current_day,
                'incomplete_quarter': 'Q4',
                'message': f'Q4 incluye datos hasta el {current_day} de {"octubre" if current_month == 10 else "noviembre" if current_month == 11 else "diciembre"}'
            }

        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        # Query 1: Quarterly breakdown by Product Family
        # Uses sales_facts_mv for consistent category data aligned with Desglose Pedidos
        query_product_families = """
            SELECT
                COALESCE(category, 'OTROS') as product_family,
                EXTRACT(QUARTER FROM order_date)::int as quarter,
                COALESCE(SUM(revenue), 0) as revenue,
                COALESCE(SUM(units_sold), 0) as units,
                COUNT(DISTINCT order_id) as orders
            FROM sales_facts_mv
            WHERE source = 'relbase'
            AND EXTRACT(YEAR FROM order_date) = %s
            GROUP BY COALESCE(category, 'OTROS'), EXTRACT(QUARTER FROM order_date)
            ORDER BY product_family, quarter
        """

        cursor.execute(query_product_families, (year,))
        product_family_data = cursor.fetchall()

        # Query 2: Quarterly breakdown by Channel
        # Uses sales_facts_mv for consistent data aligned with Desglose Pedidos
        query_channels = """
            SELECT
                COALESCE(UPPER(channel_name), 'OTROS') as channel_name,
                EXTRACT(QUARTER FROM order_date)::int as quarter,
                COALESCE(SUM(revenue), 0) as revenue,
                COALESCE(SUM(units_sold), 0) as units,
                COUNT(DISTINCT order_id) as orders
            FROM sales_facts_mv
            WHERE source = 'relbase'
            AND EXTRACT(YEAR FROM order_date) = %s
            GROUP BY COALESCE(UPPER(channel_name), 'OTROS'), EXTRACT(QUARTER FROM order_date)
            ORDER BY channel_name, quarter
        """

        cursor.execute(query_channels, (year,))
        channel_data = cursor.fetchall()

        # Query 3: Top 10 Customers by revenue with quarterly breakdown
        # Uses sales_facts_mv for consistent data aligned with Desglose Pedidos
        query_top_customers = """
            WITH customer_totals AS (
                SELECT
                    customer_id,
                    customer_name,
                    SUM(revenue) as total_revenue
                FROM sales_facts_mv
                WHERE source = 'relbase'
                AND EXTRACT(YEAR FROM order_date) = %s
                AND customer_name IS NOT NULL
                GROUP BY customer_id, customer_name
                ORDER BY total_revenue DESC
                LIMIT 10
            ),
            quarterly_data AS (
                SELECT
                    customer_id,
                    customer_name,
                    EXTRACT(QUARTER FROM order_date) as quarter,
                    COALESCE(SUM(revenue), 0) as revenue,
                    COALESCE(SUM(units_sold), 0) as units,
                    COUNT(DISTINCT order_id) as orders
                FROM sales_facts_mv
                WHERE source = 'relbase'
                AND EXTRACT(YEAR FROM order_date) = %s
                AND customer_id IN (SELECT customer_id FROM customer_totals)
                GROUP BY customer_id, customer_name, EXTRACT(QUARTER FROM order_date)
            )
            SELECT
                ct.customer_id,
                ct.customer_name,
                ct.total_revenue,
                qd.quarter::int,
                COALESCE(qd.revenue, 0) as revenue,
                COALESCE(qd.units, 0) as units,
                COALESCE(qd.orders, 0) as orders
            FROM customer_totals ct
            LEFT JOIN quarterly_data qd ON qd.customer_id = ct.customer_id
            ORDER BY ct.total_revenue DESC, ct.customer_name, qd.quarter
        """

        cursor.execute(query_top_customers, (year, year))
        customer_data = cursor.fetchall()

        cursor.close()
        conn.close()

        # Process Product Family data
        product_families = {}
        for row in product_family_data:
            family = row['product_family']
            quarter = row['quarter']

            if family not in product_families:
                product_families[family] = {
                    'name': family,
                    'icon': PRODUCT_FAMILY_ICONS.get(family, '📦'),
                    'quarters': {
                        'Q1': {'revenue': 0, 'units': 0, 'orders': 0},
                        'Q2': {'revenue': 0, 'units': 0, 'orders': 0},
                        'Q3': {'revenue': 0, 'units': 0, 'orders': 0},
                        'Q4': {'revenue': 0, 'units': 0, 'orders': 0}
                    },
                    'totals': {'revenue': 0, 'units': 0, 'orders': 0}
                }

            q_key = f'Q{quarter}'
            product_families[family]['quarters'][q_key] = {
                'revenue': float(row['revenue']),
                'units': int(row['units']),
                'orders': int(row['orders'])
            }
            product_families[family]['totals']['revenue'] += float(row['revenue'])
            product_families[family]['totals']['units'] += int(row['units'])
            product_families[family]['totals']['orders'] += int(row['orders'])

        # Sort product families by total revenue descending
        sorted_families = sorted(
            product_families.values(),
            key=lambda x: x['totals']['revenue'],
            reverse=True
        )

        # Process Channel data
        channels = {}
        for row in channel_data:
            channel = row['channel_name']
            quarter = row['quarter']

            if channel not in channels:
                channels[channel] = {
                    'name': channel,
                    'icon': CHANNEL_ICONS.get(channel, '📦'),
                    'quarters': {
                        'Q1': {'revenue': 0, 'units': 0, 'orders': 0},
                        'Q2': {'revenue': 0, 'units': 0, 'orders': 0},
                        'Q3': {'revenue': 0, 'units': 0, 'orders': 0},
                        'Q4': {'revenue': 0, 'units': 0, 'orders': 0}
                    },
                    'totals': {'revenue': 0, 'units': 0, 'orders': 0}
                }

            q_key = f'Q{quarter}'
            channels[channel]['quarters'][q_key] = {
                'revenue': float(row['revenue']),
                'units': int(row['units']),
                'orders': int(row['orders'])
            }
            channels[channel]['totals']['revenue'] += float(row['revenue'])
            channels[channel]['totals']['units'] += int(row['units'])
            channels[channel]['totals']['orders'] += int(row['orders'])

        # Sort channels by total revenue descending
        sorted_channels = sorted(
            channels.values(),
            key=lambda x: x['totals']['revenue'],
            reverse=True
        )

        # Process Customer data
        customers = {}
        for row in customer_data:
            customer_id = row['customer_id']
            customer_name = row['customer_name']
            quarter = row['quarter']

            if customer_id not in customers:
                customers[customer_id] = {
                    'id': customer_id,
                    'name': customer_name,
                    'quarters': {
                        'Q1': {'revenue': 0, 'units': 0, 'orders': 0},
                        'Q2': {'revenue': 0, 'units': 0, 'orders': 0},
                        'Q3': {'revenue': 0, 'units': 0, 'orders': 0},
                        'Q4': {'revenue': 0, 'units': 0, 'orders': 0}
                    },
                    'totals': {'revenue': float(row['total_revenue']), 'units': 0, 'orders': 0}
                }

            if quarter:
                q_key = f'Q{quarter}'
                customers[customer_id]['quarters'][q_key] = {
                    'revenue': float(row['revenue']),
                    'units': int(row['units']),
                    'orders': int(row['orders'])
                }
                customers[customer_id]['totals']['units'] += int(row['units'])
                customers[customer_id]['totals']['orders'] += int(row['orders'])

        # Sort customers by total revenue descending (already sorted but ensure order)
        sorted_customers = sorted(
            customers.values(),
            key=lambda x: x['totals']['revenue'],
            reverse=True
        )

        # Get available years for the year selector
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT EXTRACT(YEAR FROM order_date)::int as year
            FROM orders
            WHERE source = 'relbase'
            AND order_date IS NOT NULL
            ORDER BY year DESC
        """)
        available_years = [row['year'] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        return {
            'status': 'success',
            'data': {
                'year': year,
                'available_years': available_years,
                'product_families': sorted_families,
                'channels': sorted_channels,
                'top_customers': sorted_customers,
                'mtd_metadata': mtd_metadata
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quarterly breakdown: {str(e)}")
