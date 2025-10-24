"""
Relbase Product Mapping Visualization API
Provides endpoints for auditing and visualizing Relbase product mappings

Author: TM3
Date: 2025-10-22
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
import os

router = APIRouter()

# Database connection
DB_URL = os.getenv('DATABASE_URL',
    "postgresql://postgres.lypuvibmtxjaxmcmahxr:$Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
)


# Response Models
class MappingRecord(BaseModel):
    """Individual product mapping record"""
    relbase_code: str
    relbase_name: Optional[str]
    official_sku: Optional[str]
    match_type: str
    confidence_level: str
    confidence_percentage: int
    total_sales: int
    is_service_item: bool
    is_legacy_code: bool
    needs_manual_review: bool


class TopProductRecord(BaseModel):
    """Top product by sales volume"""
    relbase_code: str
    relbase_name: Optional[str]
    official_sku: Optional[str]
    match_type: str
    confidence_level: str
    confidence_percentage: int
    total_sales: int
    is_mapped: bool


class MappingStats(BaseModel):
    """Summary statistics for mappings"""
    total_products: int
    total_sales: int
    mapped_products: int
    mapped_sales: int
    unmapped_products: int
    unmapped_sales: int
    service_items: int
    service_sales: int
    legacy_codes: int
    legacy_sales: int
    needs_review: int
    by_match_type: dict
    by_confidence: dict


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    total: int
    page: int
    page_size: int
    total_pages: int
    data: List[MappingRecord]


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DB_URL)


def confidence_to_percentage(match_type: str, confidence_level: str) -> int:
    """Convert match type and confidence level to percentage"""
    if match_type == 'no_match':
        return 0
    elif confidence_level == 'high':
        return 100
    elif confidence_level == 'medium':
        return 70
    elif confidence_level == 'low':
        return 40
    else:
        return 0


@router.get("/stats", response_model=MappingStats)
async def get_mapping_stats():
    """
    Get summary statistics for all Relbase product mappings

    Returns counts and totals by mapping status, confidence level, and type
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get overall stats
        cur.execute("""
            SELECT
                COUNT(*) as total_products,
                COALESCE(SUM(total_sales), 0) as total_sales,
                COUNT(*) FILTER (WHERE match_type != 'no_match') as mapped_products,
                COALESCE(SUM(total_sales) FILTER (WHERE match_type != 'no_match'), 0) as mapped_sales,
                COUNT(*) FILTER (WHERE match_type = 'no_match') as unmapped_products,
                COALESCE(SUM(total_sales) FILTER (WHERE match_type = 'no_match'), 0) as unmapped_sales,
                COUNT(*) FILTER (WHERE is_service_item = true) as service_items,
                COALESCE(SUM(total_sales) FILTER (WHERE is_service_item = true), 0) as service_sales,
                COUNT(*) FILTER (WHERE is_legacy_code = true) as legacy_codes,
                COALESCE(SUM(total_sales) FILTER (WHERE is_legacy_code = true), 0) as legacy_sales,
                COUNT(*) FILTER (WHERE needs_manual_review = true) as needs_review
            FROM relbase_product_mappings
        """)

        overall = cur.fetchone()

        # Get by match type
        cur.execute("""
            SELECT
                match_type,
                COUNT(*) as count,
                COALESCE(SUM(total_sales), 0) as sales
            FROM relbase_product_mappings
            GROUP BY match_type
            ORDER BY sales DESC
        """)

        by_match_type = {}
        for row in cur.fetchall():
            by_match_type[row['match_type']] = {
                'count': row['count'],
                'sales': row['sales']
            }

        # Get by confidence
        cur.execute("""
            SELECT
                confidence_level,
                COUNT(*) as count,
                COALESCE(SUM(total_sales), 0) as sales
            FROM relbase_product_mappings
            GROUP BY confidence_level
            ORDER BY sales DESC
        """)

        by_confidence = {}
        for row in cur.fetchall():
            by_confidence[row['confidence_level']] = {
                'count': row['count'],
                'sales': row['sales']
            }

        cur.close()
        conn.close()

        return MappingStats(
            total_products=overall['total_products'],
            total_sales=overall['total_sales'],
            mapped_products=overall['mapped_products'],
            mapped_sales=overall['mapped_sales'],
            unmapped_products=overall['unmapped_products'],
            unmapped_sales=overall['unmapped_sales'],
            service_items=overall['service_items'],
            service_sales=overall['service_sales'],
            legacy_codes=overall['legacy_codes'],
            legacy_sales=overall['legacy_sales'],
            needs_review=overall['needs_review'],
            by_match_type=by_match_type,
            by_confidence=by_confidence
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/top-products", response_model=List[TopProductRecord])
async def get_top_products(
    limit: int = Query(10, ge=1, le=100, description="Number of top products to return"),
    exclude_service: bool = Query(True, description="Exclude service items (shipping, fees)")
):
    """
    Get top N products by sales volume

    Useful for identifying high-volume products that need mapping attention
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                relbase_code,
                relbase_name,
                official_sku,
                match_type,
                confidence_level,
                total_sales,
                CASE WHEN match_type != 'no_match' THEN true ELSE false END as is_mapped
            FROM relbase_product_mappings
            WHERE 1=1
        """

        params = []

        if exclude_service:
            query += " AND is_service_item = false"

        query += " ORDER BY total_sales DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        results = cur.fetchall()

        cur.close()
        conn.close()

        return [
            TopProductRecord(
                relbase_code=row['relbase_code'],
                relbase_name=row['relbase_name'],
                official_sku=row['official_sku'],
                match_type=row['match_type'],
                confidence_level=row['confidence_level'],
                confidence_percentage=confidence_to_percentage(row['match_type'], row['confidence_level']),
                total_sales=row['total_sales'],
                is_mapped=row['is_mapped']
            )
            for row in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/mappings", response_model=PaginatedResponse)
async def get_mappings(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=10, le=500, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in code or name"),
    match_type: Optional[str] = Query(None, description="Filter by match type"),
    confidence: Optional[str] = Query(None, description="Filter by confidence level"),
    needs_review: Optional[bool] = Query(None, description="Filter by needs review flag"),
    exclude_service: bool = Query(False, description="Exclude service items"),
    sort_by: str = Query("sales", description="Sort by: sales, code, confidence"),
    sort_order: str = Query("desc", description="Sort order: asc or desc")
):
    """
    Get all product mappings with pagination, search, and filters

    Supports:
    - Pagination
    - Search by code or name
    - Filter by match type, confidence, review status
    - Sort by sales volume, code, or confidence
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Build base query
        where_clauses = []
        params = []

        if search:
            where_clauses.append("(relbase_code ILIKE %s OR relbase_name ILIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        if match_type:
            where_clauses.append("match_type = %s")
            params.append(match_type)

        if confidence:
            where_clauses.append("confidence_level = %s")
            params.append(confidence)

        if needs_review is not None:
            where_clauses.append("needs_manual_review = %s")
            params.append(needs_review)

        if exclude_service:
            where_clauses.append("is_service_item = false")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM relbase_product_mappings
            WHERE {where_sql}
        """

        cur.execute(count_query, params)
        total = cur.fetchone()['total']

        # Calculate pagination
        offset = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size

        # Determine sort column
        sort_column_map = {
            'sales': 'total_sales',
            'code': 'relbase_code',
            'confidence': 'confidence_level'
        }
        sort_column = sort_column_map.get(sort_by, 'total_sales')
        sort_direction = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

        # Get data
        data_query = f"""
            SELECT
                relbase_code,
                relbase_name,
                official_sku,
                match_type,
                confidence_level,
                total_sales,
                is_service_item,
                is_legacy_code,
                needs_manual_review
            FROM relbase_product_mappings
            WHERE {where_sql}
            ORDER BY {sort_column} {sort_direction}
            LIMIT %s OFFSET %s
        """

        cur.execute(data_query, params + [page_size, offset])
        results = cur.fetchall()

        cur.close()
        conn.close()

        return PaginatedResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            data=[
                MappingRecord(
                    relbase_code=row['relbase_code'],
                    relbase_name=row['relbase_name'],
                    official_sku=row['official_sku'],
                    match_type=row['match_type'],
                    confidence_level=row['confidence_level'],
                    confidence_percentage=confidence_to_percentage(row['match_type'], row['confidence_level']),
                    total_sales=row['total_sales'],
                    is_service_item=row['is_service_item'],
                    is_legacy_code=row['is_legacy_code'],
                    needs_manual_review=row['needs_manual_review']
                )
                for row in results
            ]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/mapping/{relbase_code}")
async def get_mapping_detail(relbase_code: str):
    """
    Get detailed information for a specific Relbase product code

    Includes mapping info, sales volume, and related orders
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get mapping info
        cur.execute("""
            SELECT *
            FROM relbase_product_mappings
            WHERE relbase_code = %s
        """, (relbase_code,))

        mapping = cur.fetchone()

        if not mapping:
            raise HTTPException(status_code=404, detail=f"Mapping not found for code: {relbase_code}")

        # Get sample orders containing this product
        cur.execute("""
            SELECT
                o.id,
                o.order_number,
                o.order_date,
                o.total,
                oi.quantity,
                oi.unit_price
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE oi.product_sku = %s
            ORDER BY o.order_date DESC
            LIMIT 10
        """, (relbase_code,))

        sample_orders = cur.fetchall()

        cur.close()
        conn.close()

        return {
            "mapping": dict(mapping),
            "confidence_percentage": confidence_to_percentage(mapping['match_type'], mapping['confidence_level']),
            "sample_orders": [dict(order) for order in sample_orders]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
