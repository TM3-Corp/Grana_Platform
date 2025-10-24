"""
Product Mapping API Endpoints
Manages product variants and cross-channel equivalents

Author: TM3
Date: 2025-10-14
Updated: 2025-10-17 (Added catalog endpoint)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.product_mapping_service import ProductMappingService
from app.domain import catalog

router = APIRouter()
service = ProductMappingService()


# Request/Response Models
class VariantMappingCreate(BaseModel):
    """Request to create a product variant mapping"""
    base_product_id: int = Field(..., description="ID of the base product (1 unit)")
    variant_product_id: int = Field(..., description="ID of the variant product (display)")
    quantity_multiplier: int = Field(..., gt=0, description="Number of base units in variant")
    packaging_type: str = Field(..., description="Type: individual, display_5, display_16, etc")
    is_active: bool = Field(True, description="Whether mapping is active")


class ChannelEquivalentCreate(BaseModel):
    """Request to create a cross-channel equivalent"""
    shopify_product_id: int = Field(..., description="Shopify product ID")
    mercadolibre_product_id: int = Field(..., description="MercadoLibre product ID")
    equivalence_confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    verified: bool = Field(False, description="Manually verified")
    notes: Optional[str] = Field(None, description="Additional notes")


class VariantDetectionResult(BaseModel):
    """Detected variant suggestion"""
    variant_product_id: int
    variant_sku: str
    variant_name: str
    quantity_multiplier: int
    packaging_type: str
    confidence: float
    current_stock: int
    sale_price: Optional[float]


class ChannelEquivalentResult(BaseModel):
    """Detected cross-channel equivalent"""
    target_product_id: int
    target_sku: str
    target_name: str
    target_source: str
    confidence: float
    name_similarity: float
    term_overlap: float
    price_similarity: float
    current_stock: int
    sale_price: Optional[float]


class ConsolidatedInventory(BaseModel):
    """Consolidated inventory record"""
    base_product_id: int
    base_sku: str
    base_name: str
    base_source: Optional[str]
    base_unit_price: Optional[float]
    base_direct_stock: int
    num_variants: int
    variant_stock_as_units: int
    total_units_available: int
    stock_status: str
    inventory_value: Optional[float]


class ProductFamily(BaseModel):
    """Product family with variants"""
    base_product_id: int
    base_sku: str
    base_name: str
    variant_product_id: int
    variant_sku: str
    variant_name: str
    quantity_multiplier: int
    packaging_type: str
    variant_stock: int
    variant_stock_as_base_units: int
    variant_price: Optional[float]
    base_unit_price: Optional[float]
    variant_unit_price: Optional[float]
    discount_percentage: Optional[float]


# Endpoints
@router.get("/consolidated-inventory", response_model=List[ConsolidatedInventory])
async def get_consolidated_inventory(
    base_product_id: Optional[int] = Query(None, description="Filter by specific product")
):
    """
    Get consolidated inventory showing real stock in base units
    Accounts for all packaging variants
    """
    try:
        results = service.get_consolidated_inventory(base_product_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product-families", response_model=List[ProductFamily])
async def get_product_families(
    base_product_id: Optional[int] = Query(None, description="Filter by specific product family")
):
    """
    Get complete product families showing all packaging variants
    """
    try:
        results = service.get_product_families(base_product_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect-variants/{product_id}", response_model=List[VariantDetectionResult])
async def detect_packaging_variants(product_id: int):
    """
    Auto-detect potential packaging variants for a product
    Uses SKU pattern matching and name similarity
    """
    try:
        results = service.detect_packaging_variants(product_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect-equivalents/{product_id}", response_model=List[ChannelEquivalentResult])
async def detect_channel_equivalents(
    product_id: int,
    min_confidence: float = Query(0.7, ge=0, le=1, description="Minimum confidence threshold")
):
    """
    Auto-detect potential cross-channel equivalents for a product
    Uses name similarity, term overlap, and price comparison
    """
    try:
        results = service.detect_channel_equivalents(product_id, min_confidence)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/variants", status_code=201)
async def create_variant_mapping(mapping: VariantMappingCreate):
    """
    Create a new product variant mapping
    Links a display/pack to its base unit product
    """
    try:
        result = service.create_variant_mapping(
            base_product_id=mapping.base_product_id,
            variant_product_id=mapping.variant_product_id,
            quantity_multiplier=mapping.quantity_multiplier,
            packaging_type=mapping.packaging_type,
            is_active=mapping.is_active
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to create mapping'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/equivalents", status_code=201)
async def create_channel_equivalent(equivalent: ChannelEquivalentCreate):
    """
    Create a new cross-channel equivalent mapping
    Links the same product across Shopify and MercadoLibre
    """
    try:
        result = service.create_channel_equivalent(
            shopify_product_id=equivalent.shopify_product_id,
            mercadolibre_product_id=equivalent.mercadolibre_product_id,
            equivalence_confidence=equivalent.equivalence_confidence,
            verified=equivalent.verified,
            notes=equivalent.notes
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to create equivalent'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/variants/{variant_id}")
async def delete_variant_mapping(variant_id: int):
    """Delete a product variant mapping"""
    try:
        result = service.delete_variant_mapping(variant_id)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to delete mapping'))

        return {"message": "Variant mapping deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/equivalents/{equivalent_id}")
async def delete_channel_equivalent(equivalent_id: int):
    """Delete a cross-channel equivalent mapping"""
    try:
        result = service.delete_channel_equivalent(equivalent_id)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to delete equivalent'))

        return {"message": "Channel equivalent deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parse-sku/{sku}")
async def parse_shopify_sku(sku: str):
    """
    Parse a Shopify SKU to extract product information
    Useful for understanding SKU structure
    """
    try:
        parsed = service.parse_shopify_sku(sku)

        if not parsed:
            raise HTTPException(status_code=400, detail="Invalid Shopify SKU format")

        return parsed

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channel-equivalents")
async def get_channel_equivalents():
    """
    Get all cross-channel equivalents with product details
    Shows Shopify ↔ MercadoLibre product mappings
    """
    try:
        results = service.get_channel_equivalents()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog")
async def get_official_catalog(
    category: Optional[str] = Query(None, description="Filter by category (BARRAS, GRANOLAS, etc.)"),
    base_code: Optional[str] = Query(None, description="Filter by base code (BAKC, GRAL, etc.)")
):
    """
    Get the official Grana product catalog

    This is the single source of truth for all Grana products.
    Includes official SKUs, categories, and packaging information.

    **Use this instead of hardcoding products in the frontend!**
    """
    try:
        # Get all products
        if base_code:
            products = catalog.get_products_by_base_code(base_code)
        elif category:
            try:
                cat_enum = catalog.ProductCategory(category.upper())
                products = catalog.get_products_by_category(cat_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category. Must be one of: {[c.value for c in catalog.ProductCategory]}"
                )
        else:
            products = catalog.get_all_products()

        # Convert to dicts for JSON response
        return {
            "status": "success",
            "total": len(products),
            "data": [p.to_dict() for p in products]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/stats")
async def get_catalog_stats():
    """
    Get statistics about the official product catalog

    Returns counts by category and total unique base codes
    """
    try:
        stats = catalog.get_catalog_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/{sku}")
async def get_catalog_product(sku: str):
    """
    Get a single product from the official catalog by SKU

    Returns 404 if the SKU is not in the official catalog
    """
    try:
        product = catalog.get_product_by_sku(sku)

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"SKU '{sku}' not found in official catalog"
            )

        return {
            "status": "success",
            "data": product.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/families/hierarchical")
async def get_hierarchical_families():
    """
    Get product families in hierarchical structure

    Returns:
    - Familia (Category): GRANOLAS, BARRAS, CRACKERS, KEEPERS
    - Subfamilia (Product variant): e.g., "Granola Low Carb Almendras"
    - Formato (Format): e.g., "260g", "X1", "X5"
    - Aggregated stock and sales data
    """
    try:
        results = service.get_hierarchical_families()
        return {
            "status": "success",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
