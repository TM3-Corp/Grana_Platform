"""
Conversion API Endpoints
Unit conversion operations for products

Author: TM3
Date: 2025-10-03
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal
import os

from app.services.conversion_service import ConversionService

router = APIRouter()


# Pydantic models for request/response
class ConversionRequest(BaseModel):
    sku: str = Field(..., description="Product SKU")
    quantity: float = Field(..., gt=0, description="Quantity to convert")
    from_unit: str = Field(..., description="Source unit: unit, display, box, pallet")
    to_unit: str = Field(..., description="Target unit: unit, display, box, pallet")

    class Config:
        json_schema_extra = {
            "example": {
                "sku": "BAR-CHIA-001",
                "quantity": 5,
                "from_unit": "box",
                "to_unit": "unit"
            }
        }


class OrderItem(BaseModel):
    sku: str
    quantity: int
    unit: str = "unit"


class OrderCalculationRequest(BaseModel):
    items: List[OrderItem]

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {"sku": "BAR-CHIA-001", "quantity": 5, "unit": "box"},
                    {"sku": "GRA-250-001", "quantity": 2, "unit": "display"},
                    {"sku": "MIX-FRUTOS-001", "quantity": 50, "unit": "unit"}
                ]
            }
        }


class StockCheckRequest(BaseModel):
    items: List[OrderItem]


class FormatQuantityRequest(BaseModel):
    sku: str
    units: int
    channel_type: str = Field(..., description="b2c, retail, marketplace, or direct")


# Dependency: Get conversion service
def get_conversion_service() -> ConversionService:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    return ConversionService(database_url)


# Endpoints
@router.get("/products/{sku}/conversion-info")
async def get_product_conversion_info(
    sku: str,
    service: ConversionService = Depends(get_conversion_service)
):
    """
    Get conversion information for a product

    Returns all conversion factors and unit names
    """
    try:
        info = service.get_product_conversion_info(sku)
        if not info:
            raise HTTPException(status_code=404, detail=f"Product not found: {sku}")

        return {
            "status": "success",
            "data": dict(info)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert")
async def convert_units(
    request: ConversionRequest,
    service: ConversionService = Depends(get_conversion_service)
):
    """
    Convert quantity between different units

    Supports: unit, display, box, pallet
    """
    try:
        result = service.convert(
            sku=request.sku,
            quantity=request.quantity,
            from_unit=request.from_unit,
            to_unit=request.to_unit
        )

        return {
            "status": "success",
            "data": {
                "sku": request.sku,
                "input": {
                    "quantity": request.quantity,
                    "unit": request.from_unit
                },
                "output": {
                    "quantity": float(result),
                    "unit": request.to_unit
                }
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/calculate")
async def calculate_order_totals(
    request: OrderCalculationRequest,
    service: ConversionService = Depends(get_conversion_service)
):
    """
    Calculate total units from a mixed order

    Accepts items with different units (unit, display, box, pallet)
    Returns total units per SKU
    """
    try:
        items_dict = [item.model_dump() for item in request.items]
        totals = service.calculate_order_total_units(items_dict)

        # Get product names for response
        result = []
        for sku, units in totals.items():
            info = service.get_product_conversion_info(sku)
            result.append({
                "sku": sku,
                "product_name": info['name'] if info else "Unknown",
                "total_units": units
            })

        return {
            "status": "success",
            "data": {
                "items": result,
                "total_items": len(result)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/check-stock")
async def check_stock_availability(
    request: StockCheckRequest,
    service: ConversionService = Depends(get_conversion_service)
):
    """
    Check if there's enough stock for an order

    Returns stock availability status for each SKU
    """
    try:
        items_dict = [item.model_dump() for item in request.items]
        stock_status = service.check_stock_availability(items_dict)

        # Check if all items have sufficient stock
        all_sufficient = all(item['sufficient'] for item in stock_status.values())

        return {
            "status": "success",
            "data": {
                "all_sufficient": all_sufficient,
                "items": stock_status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/format-for-channel")
async def format_quantity_for_channel(
    request: FormatQuantityRequest,
    service: ConversionService = Depends(get_conversion_service)
):
    """
    Format quantity according to channel preferences

    - B2C/Marketplace: Shows units
    - Retail: Shows boxes
    - Direct: Shows mixed (boxes + units)
    """
    try:
        result = service.format_quantity_for_channel(
            sku=request.sku,
            units=request.units,
            channel_type=request.channel_type
        )

        return {
            "status": "success",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{sku}/conversion-summary")
async def get_conversion_summary(
    sku: str,
    units: int,
    service: ConversionService = Depends(get_conversion_service)
):
    """
    Get complete conversion summary for a quantity

    Shows the quantity in all units (unit, display, box, pallet)
    """
    try:
        summary = service.get_conversion_summary(sku, units)

        return {
            "status": "success",
            "data": summary
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def conversion_health():
    """Health check for conversion service"""
    return {
        "status": "healthy",
        "service": "conversion",
        "endpoints": [
            "GET /products/{sku}/conversion-info",
            "POST /convert",
            "POST /orders/calculate",
            "POST /orders/check-stock",
            "POST /format-for-channel",
            "GET /products/{sku}/conversion-summary"
        ]
    }
