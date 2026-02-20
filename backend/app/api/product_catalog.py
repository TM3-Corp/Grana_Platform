"""
Product Catalog API Endpoints
CRUD operations for managing the product catalog

Purpose:
- List, create, update, delete products in product_catalog
- Get product details
- Bulk operations

Author: TM3
Date: 2025-12-22
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

router = APIRouter()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback for local development
    DATABASE_URL = "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


# =====================================================================
# Pydantic Models
# =====================================================================

class ProductCatalogBase(BaseModel):
    """Base model for product catalog"""
    sku: str = Field(..., min_length=1, max_length=100, description="Product SKU (unique identifier)")
    product_name: str = Field(..., min_length=1, description="Product name")
    sku_master: Optional[str] = Field(None, max_length=100, description="Master box SKU (for caja master products)")
    master_box_name: Optional[str] = Field(None, description="Master box name")
    category: Optional[str] = Field(None, max_length=100, description="Product category (BARRAS, CRACKERS, etc.)")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    language: Optional[str] = Field(None, max_length=50, description="Language (ES, EN)")
    package_type: Optional[str] = Field(None, max_length=100, description="Package type")
    units_per_display: Optional[int] = Field(None, ge=1, description="Units per display (conversion factor)")
    units_per_master_box: Optional[int] = Field(None, ge=1, description="Number of packages in master box")
    items_per_master_box: Optional[int] = Field(None, ge=1, description="Total individual items in master box")
    is_master_sku: Optional[bool] = Field(False, description="Is this a master/parent SKU")
    base_code: Optional[str] = Field(None, max_length=50, description="Base product code")
    sku_primario: Optional[str] = Field(None, max_length=100, description="Primary SKU for product family")
    peso_film: Optional[float] = Field(None, ge=0, description="Film weight (kg)")
    peso_display_total: Optional[float] = Field(None, ge=0, description="Display total weight (kg)")
    peso_caja_master_total: Optional[float] = Field(None, ge=0, description="Master box total weight (kg)")
    peso_etiqueta_total: Optional[float] = Field(None, ge=0, description="Label total weight (kg)")
    sku_value: Optional[float] = Field(None, ge=0, description="SKU value (CLP)")
    sku_master_value: Optional[float] = Field(None, ge=0, description="Master SKU value (CLP)")
    is_active: Optional[bool] = Field(True, description="Is product active")
    is_inventory_active: Optional[bool] = Field(True, description="Show in inventory views")


class ProductCatalogCreate(ProductCatalogBase):
    """Request model for creating a new product"""
    pass


class ProductCatalogUpdate(BaseModel):
    """Request model for updating an existing product"""
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    product_name: Optional[str] = Field(None, min_length=1)
    sku_master: Optional[str] = Field(None, max_length=100)
    master_box_name: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=50)
    package_type: Optional[str] = Field(None, max_length=100)
    units_per_display: Optional[int] = Field(None, ge=1)
    units_per_master_box: Optional[int] = Field(None, ge=1)
    items_per_master_box: Optional[int] = Field(None, ge=1)
    is_master_sku: Optional[bool] = None
    base_code: Optional[str] = Field(None, max_length=50)
    sku_primario: Optional[str] = Field(None, max_length=100)
    peso_film: Optional[float] = Field(None, ge=0)
    peso_display_total: Optional[float] = Field(None, ge=0)
    peso_caja_master_total: Optional[float] = Field(None, ge=0)
    peso_etiqueta_total: Optional[float] = Field(None, ge=0)
    sku_value: Optional[float] = Field(None, ge=0)
    sku_master_value: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_inventory_active: Optional[bool] = None


class MasterBoxBase(BaseModel):
    """Base model for master box"""
    sku_master: str = Field(..., min_length=1, max_length=100, description="Master box SKU code")
    master_box_name: Optional[str] = Field(None, description="Master box name")
    items_per_master_box: Optional[int] = Field(None, ge=1, description="Total individual items in master box")
    units_per_master_box: Optional[int] = Field(None, ge=1, description="Number of packages in master box")
    is_active: Optional[bool] = Field(True, description="Is this master box active")


class MasterBoxCreate(MasterBoxBase):
    """Request model for creating a master box"""
    pass


class MasterBoxUpdate(BaseModel):
    """Request model for updating a master box"""
    sku_master: Optional[str] = Field(None, min_length=1, max_length=100)
    master_box_name: Optional[str] = None
    items_per_master_box: Optional[int] = Field(None, ge=1)
    units_per_master_box: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class MasterBoxResponse(BaseModel):
    """Response model for master box"""
    id: int
    product_sku: str
    sku_master: str
    master_box_name: Optional[str]
    items_per_master_box: Optional[int]
    units_per_master_box: Optional[int]
    is_active: Optional[bool]
    created_at: Optional[str]
    updated_at: Optional[str]


class ProductCatalogResponse(BaseModel):
    """Response model for product catalog"""
    id: int
    sku: str
    product_name: str
    sku_master: Optional[str]
    master_box_name: Optional[str]
    category: Optional[str]
    brand: Optional[str]
    language: Optional[str]
    package_type: Optional[str]
    units_per_display: Optional[int]
    units_per_master_box: Optional[int]
    items_per_master_box: Optional[int]
    is_master_sku: Optional[bool]
    base_code: Optional[str]
    sku_primario: Optional[str]
    peso_film: Optional[float]
    peso_display_total: Optional[float]
    peso_caja_master_total: Optional[float]
    peso_etiqueta_total: Optional[float]
    sku_value: Optional[float]
    sku_master_value: Optional[float]
    is_active: Optional[bool]
    is_inventory_active: Optional[bool]
    created_at: Optional[str]
    updated_at: Optional[str]
    master_boxes: Optional[List[dict]] = None


# =====================================================================
# Helper Functions
# =====================================================================

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)


def refresh_sales_facts_mv():
    """
    Refresh the sales_facts_mv materialized view.

    This should be called after any change to product_catalog that affects
    analytics data (category, sku_primario, is_active, etc.).

    Uses CONCURRENTLY to avoid blocking read queries during refresh.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)
        cursor = conn.cursor()
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY sales_facts_mv")
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Warning: Failed to refresh sales_facts_mv: {e}")
        return False


def refresh_product_catalog_cache(also_refresh_mv: bool = True):
    """
    Invalidate ProductCatalogService cache after changes.
    Also refresh sales_facts_mv to sync analytics data.

    Args:
        also_refresh_mv: If True, also refresh the materialized view (default: True)
    """
    cache_refreshed = False
    mv_refreshed = False

    try:
        from app.services.product_catalog_service import get_product_catalog_service
        service = get_product_catalog_service()
        service.invalidate_cache()
        cache_refreshed = True
    except Exception as e:
        print(f"Warning: Failed to refresh product catalog cache: {e}")

    if also_refresh_mv:
        mv_refreshed = refresh_sales_facts_mv()

    return cache_refreshed, mv_refreshed


# =====================================================================
# API Endpoints
# =====================================================================

@router.get("/")
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in SKU and product name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    sort_by: str = Query("sku", description="Sort field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)")
):
    """
    List all products in the catalog with pagination and filtering.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build WHERE clause
        where_clauses = []
        params = []

        if search:
            where_clauses.append("(sku ILIKE %s OR product_name ILIKE %s OR sku_primario ILIKE %s)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        if category:
            where_clauses.append("category = %s")
            params.append(category)

        if is_active is not None:
            where_clauses.append("is_active = %s")
            params.append(is_active)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Validate sort field
        valid_sort_fields = ['sku', 'product_name', 'category', 'brand', 'units_per_display', 'created_at', 'updated_at']
        if sort_by not in valid_sort_fields:
            sort_by = 'sku'
        sort_order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM product_catalog WHERE {where_sql}", params)
        total_count = cursor.fetchone()['count']

        # Get products with pagination
        offset = (page - 1) * page_size
        cursor.execute(f"""
            SELECT
                id, sku, product_name, sku_master, master_box_name,
                category, brand, language, package_type,
                units_per_display, units_per_master_box, items_per_master_box,
                is_master_sku, base_code, sku_primario,
                peso_film, peso_display_total, peso_caja_master_total, peso_etiqueta_total,
                sku_value, sku_master_value,
                is_active, is_inventory_active,
                created_at, updated_at
            FROM product_catalog
            WHERE {where_sql}
            ORDER BY {sort_by} {sort_order}
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])

        products = cursor.fetchall()

        # Fetch all master boxes in one query (batch for efficiency)
        product_skus = [p['sku'] for p in products]
        master_boxes_map = {}
        if product_skus:
            placeholders = ','.join(['%s'] * len(product_skus))
            cursor.execute(f"""
                SELECT id, product_sku, sku_master, master_box_name,
                       items_per_master_box, units_per_master_box, is_active,
                       created_at, updated_at
                FROM product_master_boxes
                WHERE product_sku IN ({placeholders})
                ORDER BY sku_master
            """, product_skus)
            for mb in cursor.fetchall():
                mb_dict = dict(mb)
                if mb_dict.get('created_at'):
                    mb_dict['created_at'] = mb_dict['created_at'].isoformat()
                if mb_dict.get('updated_at'):
                    mb_dict['updated_at'] = mb_dict['updated_at'].isoformat()
                master_boxes_map.setdefault(mb_dict['product_sku'], []).append(mb_dict)

        # Convert to list of dicts with proper serialization
        result = []
        for p in products:
            product_dict = dict(p)
            # Convert datetime to string
            if product_dict.get('created_at'):
                product_dict['created_at'] = product_dict['created_at'].isoformat()
            if product_dict.get('updated_at'):
                product_dict['updated_at'] = product_dict['updated_at'].isoformat()
            # Convert Decimal to float
            for key in ['peso_film', 'peso_display_total', 'peso_caja_master_total', 'peso_etiqueta_total', 'sku_value', 'sku_master_value']:
                if product_dict.get(key) is not None:
                    product_dict[key] = float(product_dict[key])
            # Attach master boxes from junction table
            product_dict['master_boxes'] = master_boxes_map.get(product_dict['sku'], [])
            result.append(product_dict)

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": result,
            "meta": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")


@router.get("/categories")
async def get_categories():
    """
    Get list of unique categories for filtering.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT DISTINCT category
            FROM product_catalog
            WHERE category IS NOT NULL
            ORDER BY category
        """)
        categories = [row['category'] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": categories
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")


@router.get("/stats")
async def get_stats():
    """
    Get statistics about the product catalog.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                COUNT(*) as total_products,
                COUNT(*) FILTER (WHERE is_active = true) as active_products,
                COUNT(*) FILTER (WHERE is_active = false OR is_active IS NULL) as inactive_products,
                COUNT(*) FILTER (WHERE is_active = true AND is_inventory_active = true) as inventory_active,
                COUNT(DISTINCT category) as total_categories,
                (SELECT COUNT(DISTINCT product_sku) FROM product_master_boxes WHERE is_active = TRUE) as has_master_box
            FROM product_catalog
        """)
        stats = dict(cursor.fetchone())

        # Get category breakdown
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM product_catalog
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """)
        category_breakdown = [dict(row) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": {
                **stats,
                "category_breakdown": category_breakdown
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/{product_id}")
async def get_product(product_id: int):
    """
    Get a single product by ID.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                id, sku, product_name, sku_master, master_box_name,
                category, brand, language, package_type,
                units_per_display, units_per_master_box, items_per_master_box,
                is_master_sku, base_code, sku_primario,
                peso_film, peso_display_total, peso_caja_master_total, peso_etiqueta_total,
                sku_value, sku_master_value,
                is_active, is_inventory_active,
                created_at, updated_at
            FROM product_catalog
            WHERE id = %s
        """, [product_id])

        product = cursor.fetchone()

        if not product:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

        product_dict = dict(product)
        if product_dict.get('created_at'):
            product_dict['created_at'] = product_dict['created_at'].isoformat()
        if product_dict.get('updated_at'):
            product_dict['updated_at'] = product_dict['updated_at'].isoformat()
        for key in ['peso_film', 'peso_display_total', 'peso_caja_master_total', 'peso_etiqueta_total', 'sku_value', 'sku_master_value']:
            if product_dict.get(key) is not None:
                product_dict[key] = float(product_dict[key])

        # Fetch master boxes for this product
        cursor.execute("""
            SELECT id, product_sku, sku_master, master_box_name,
                   items_per_master_box, units_per_master_box, is_active,
                   created_at, updated_at
            FROM product_master_boxes
            WHERE product_sku = %s
            ORDER BY sku_master
        """, [product_dict['sku']])
        master_boxes = []
        for mb in cursor.fetchall():
            mb_dict = dict(mb)
            if mb_dict.get('created_at'):
                mb_dict['created_at'] = mb_dict['created_at'].isoformat()
            if mb_dict.get('updated_at'):
                mb_dict['updated_at'] = mb_dict['updated_at'].isoformat()
            master_boxes.append(mb_dict)
        product_dict['master_boxes'] = master_boxes

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": product_dict
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product: {str(e)}")


@router.post("/")
async def create_product(product: ProductCatalogCreate):
    """
    Create a new product in the catalog.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if SKU already exists
        cursor.execute("SELECT id FROM product_catalog WHERE sku = %s", [product.sku])
        if cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail=f"SKU '{product.sku}' already exists")

        # Insert new product
        cursor.execute("""
            INSERT INTO product_catalog (
                sku, product_name, sku_master, master_box_name,
                category, brand, language, package_type,
                units_per_display, units_per_master_box, items_per_master_box,
                is_master_sku, base_code, sku_primario,
                peso_film, peso_display_total, peso_caja_master_total, peso_etiqueta_total,
                sku_value, sku_master_value,
                is_active, is_inventory_active,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
            RETURNING id
        """, [
            product.sku, product.product_name, product.sku_master, product.master_box_name,
            product.category, product.brand, product.language, product.package_type,
            product.units_per_display, product.units_per_master_box, product.items_per_master_box,
            product.is_master_sku, product.base_code, product.sku_primario,
            product.peso_film, product.peso_display_total, product.peso_caja_master_total, product.peso_etiqueta_total,
            product.sku_value, product.sku_master_value,
            product.is_active, product.is_inventory_active
        ])

        new_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()

        # Refresh cache and materialized view
        cache_refreshed, mv_refreshed = refresh_product_catalog_cache()

        return {
            "status": "success",
            "message": f"Product '{product.sku}' created successfully",
            "data": {"id": new_id, "sku": product.sku},
            "cache_refreshed": cache_refreshed,
            "mv_refreshed": mv_refreshed
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


@router.put("/{product_id}")
async def update_product(product_id: int, product: ProductCatalogUpdate):
    """
    Update an existing product.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if product exists
        cursor.execute("SELECT id, sku FROM product_catalog WHERE id = %s", [product_id])
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

        # If updating SKU, check it doesn't conflict
        if product.sku and product.sku != existing['sku']:
            cursor.execute("SELECT id FROM product_catalog WHERE sku = %s AND id != %s", [product.sku, product_id])
            if cursor.fetchone():
                cursor.close()
                conn.close()
                raise HTTPException(status_code=400, detail=f"SKU '{product.sku}' already exists")

        # Build dynamic UPDATE query
        update_fields = []
        update_values = []

        update_data = product.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            update_fields.append(f"{field} = %s")
            update_values.append(value)

        if not update_fields:
            cursor.close()
            conn.close()
            return {"status": "success", "message": "No fields to update"}

        # Add updated_at
        update_fields.append("updated_at = NOW()")

        cursor.execute(f"""
            UPDATE product_catalog
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, update_values + [product_id])

        conn.commit()
        cursor.close()
        conn.close()

        # Refresh cache and materialized view
        cache_refreshed, mv_refreshed = refresh_product_catalog_cache()

        return {
            "status": "success",
            "message": f"Product updated successfully",
            "cache_refreshed": cache_refreshed,
            "mv_refreshed": mv_refreshed
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")


@router.delete("/{product_id}")
async def delete_product(product_id: int):
    """
    Delete a product from the catalog.
    Note: This is a hard delete. Consider using soft delete (is_active=false) instead.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if product exists
        cursor.execute("SELECT id, sku FROM product_catalog WHERE id = %s", [product_id])
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

        # Check if SKU is referenced in sku_mappings
        cursor.execute("SELECT COUNT(*) FROM sku_mappings WHERE target_sku = %s", [existing['sku']])
        mapping_count = cursor.fetchone()['count']
        if mapping_count > 0:
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete: SKU '{existing['sku']}' is referenced by {mapping_count} SKU mapping(s). Delete those mappings first or deactivate the product instead."
            )

        # Delete product
        cursor.execute("DELETE FROM product_catalog WHERE id = %s", [product_id])
        conn.commit()
        cursor.close()
        conn.close()

        # Refresh cache and materialized view
        cache_refreshed, mv_refreshed = refresh_product_catalog_cache()

        return {
            "status": "success",
            "message": f"Product '{existing['sku']}' deleted successfully",
            "cache_refreshed": cache_refreshed,
            "mv_refreshed": mv_refreshed
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")


@router.post("/{product_id}/toggle-active")
async def toggle_product_active(product_id: int):
    """
    Toggle the is_active status of a product.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            UPDATE product_catalog
            SET is_active = NOT COALESCE(is_active, true), updated_at = NOW()
            WHERE id = %s
            RETURNING id, sku, is_active
        """, [product_id])

        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

        conn.commit()
        cursor.close()
        conn.close()

        # Refresh cache and materialized view
        cache_refreshed, mv_refreshed = refresh_product_catalog_cache()

        return {
            "status": "success",
            "message": f"Product '{result['sku']}' is now {'active' if result['is_active'] else 'inactive'}",
            "data": {"is_active": result['is_active']},
            "cache_refreshed": cache_refreshed,
            "mv_refreshed": mv_refreshed
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle product status: {str(e)}")


@router.post("/bulk-update-category")
async def bulk_update_category(
    product_ids: List[int],
    category: str = Query(..., description="New category to assign")
):
    """
    Update category for multiple products at once.
    """
    try:
        if not product_ids:
            raise HTTPException(status_code=400, detail="No product IDs provided")

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            UPDATE product_catalog
            SET category = %s, updated_at = NOW()
            WHERE id = ANY(%s)
        """, [category, product_ids])

        updated_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        # Refresh cache and materialized view
        cache_refreshed, mv_refreshed = refresh_product_catalog_cache()

        return {
            "status": "success",
            "message": f"Updated category to '{category}' for {updated_count} product(s)",
            "updated_count": updated_count,
            "cache_refreshed": cache_refreshed,
            "mv_refreshed": mv_refreshed
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk update category: {str(e)}")


@router.post("/bulk-deactivate-by-language")
async def bulk_deactivate_by_language(
    language: str = Query(..., description="Language to deactivate (e.g., 'EN')"),
    dry_run: bool = Query(False, description="If true, only return count without making changes")
):
    """
    Bulk deactivate all products with the specified language.

    This is used to hide English products from analytics dropdowns while
    preserving the data in the database. Products can be reactivated later.

    Args:
        language: Language code to deactivate (EN, ES)
        dry_run: If True, only return count of affected products without deactivating

    Returns:
        Count of deactivated products and cache refresh status
    """
    try:
        # Validate language
        language = language.upper()
        if language not in ['EN', 'ES']:
            raise HTTPException(status_code=400, detail="Language must be 'EN' or 'ES'")

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get count of affected products
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM product_catalog
            WHERE language = %s AND is_active = TRUE
        """, [language])
        affected_count = cursor.fetchone()['count']

        if affected_count == 0:
            cursor.close()
            conn.close()
            return {
                "status": "success",
                "message": f"No active products found with language '{language}'",
                "deactivated_count": 0,
                "dry_run": dry_run
            }

        # Get sample of affected SKUs for confirmation
        cursor.execute("""
            SELECT sku, product_name
            FROM product_catalog
            WHERE language = %s AND is_active = TRUE
            ORDER BY sku
            LIMIT 10
        """, [language])
        sample_products = [dict(row) for row in cursor.fetchall()]

        if dry_run:
            cursor.close()
            conn.close()
            return {
                "status": "preview",
                "message": f"Would deactivate {affected_count} products with language '{language}'",
                "affected_count": affected_count,
                "sample_products": sample_products,
                "dry_run": True
            }

        # Perform bulk deactivation
        cursor.execute("""
            UPDATE product_catalog
            SET is_active = FALSE, updated_at = NOW()
            WHERE language = %s AND is_active = TRUE
        """, [language])

        conn.commit()
        cursor.close()
        conn.close()

        # Refresh cache and materialized view
        cache_refreshed, mv_refreshed = refresh_product_catalog_cache()

        return {
            "status": "success",
            "message": f"Deactivated {affected_count} products with language '{language}'",
            "deactivated_count": affected_count,
            "sample_products": sample_products,
            "cache_refreshed": cache_refreshed,
            "mv_refreshed": mv_refreshed,
            "dry_run": False
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk deactivate: {str(e)}")


# =====================================================================
# Master Box CRUD Endpoints
# =====================================================================

@router.get("/{sku}/master-boxes")
async def list_master_boxes(sku: str):
    """List all master boxes for a product."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verify product exists
        cursor.execute("SELECT sku FROM product_catalog WHERE sku = %s", [sku])
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product '{sku}' not found")

        cursor.execute("""
            SELECT id, product_sku, sku_master, master_box_name,
                   items_per_master_box, units_per_master_box, is_active,
                   created_at, updated_at
            FROM product_master_boxes
            WHERE product_sku = %s
            ORDER BY sku_master
        """, [sku])

        master_boxes = []
        for mb in cursor.fetchall():
            mb_dict = dict(mb)
            if mb_dict.get('created_at'):
                mb_dict['created_at'] = mb_dict['created_at'].isoformat()
            if mb_dict.get('updated_at'):
                mb_dict['updated_at'] = mb_dict['updated_at'].isoformat()
            master_boxes.append(mb_dict)

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "data": master_boxes,
            "count": len(master_boxes)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list master boxes: {str(e)}")


@router.post("/{sku}/master-boxes")
async def create_master_box(sku: str, master_box: MasterBoxCreate):
    """Add a master box to a product."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verify product exists
        cursor.execute("SELECT sku FROM product_catalog WHERE sku = %s", [sku])
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Product '{sku}' not found")

        # Check sku_master doesn't already exist
        cursor.execute("SELECT id FROM product_master_boxes WHERE sku_master = %s", [master_box.sku_master])
        if cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail=f"Master box SKU '{master_box.sku_master}' already exists")

        cursor.execute("""
            INSERT INTO product_master_boxes (
                product_sku, sku_master, master_box_name,
                items_per_master_box, units_per_master_box, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, [
            sku, master_box.sku_master, master_box.master_box_name,
            master_box.items_per_master_box, master_box.units_per_master_box,
            master_box.is_active if master_box.is_active is not None else True
        ])

        new_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()

        cache_refreshed, mv_refreshed = refresh_product_catalog_cache()

        return {
            "status": "success",
            "message": f"Master box '{master_box.sku_master}' added to product '{sku}'",
            "data": {"id": new_id, "sku_master": master_box.sku_master},
            "cache_refreshed": cache_refreshed,
            "mv_refreshed": mv_refreshed
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create master box: {str(e)}")


@router.put("/master-boxes/{master_box_id}")
async def update_master_box(master_box_id: int, master_box: MasterBoxUpdate):
    """Update a master box."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT id FROM product_master_boxes WHERE id = %s", [master_box_id])
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Master box with ID {master_box_id} not found")

        # If updating sku_master, check uniqueness
        if master_box.sku_master:
            cursor.execute(
                "SELECT id FROM product_master_boxes WHERE sku_master = %s AND id != %s",
                [master_box.sku_master, master_box_id]
            )
            if cursor.fetchone():
                cursor.close()
                conn.close()
                raise HTTPException(status_code=400, detail=f"Master box SKU '{master_box.sku_master}' already exists")

        update_fields = []
        update_values = []
        update_data = master_box.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            update_fields.append(f"{field} = %s")
            update_values.append(value)

        if not update_fields:
            cursor.close()
            conn.close()
            return {"status": "success", "message": "No fields to update"}

        update_fields.append("updated_at = NOW()")

        cursor.execute(f"""
            UPDATE product_master_boxes
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, update_values + [master_box_id])

        conn.commit()
        cursor.close()
        conn.close()

        cache_refreshed, mv_refreshed = refresh_product_catalog_cache()

        return {
            "status": "success",
            "message": "Master box updated successfully",
            "cache_refreshed": cache_refreshed,
            "mv_refreshed": mv_refreshed
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update master box: {str(e)}")


@router.delete("/master-boxes/{master_box_id}")
async def delete_master_box(master_box_id: int):
    """Deactivate a master box (soft delete)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            UPDATE product_master_boxes
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = %s
            RETURNING id, sku_master, product_sku
        """, [master_box_id])

        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Master box with ID {master_box_id} not found")

        conn.commit()
        cursor.close()
        conn.close()

        cache_refreshed, mv_refreshed = refresh_product_catalog_cache()

        return {
            "status": "success",
            "message": f"Master box '{result['sku_master']}' deactivated",
            "cache_refreshed": cache_refreshed,
            "mv_refreshed": mv_refreshed
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete master box: {str(e)}")
