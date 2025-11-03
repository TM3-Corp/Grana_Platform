"""
API endpoints for inventory management.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, List
from datetime import datetime

from app.services.inventory_service import InventoryService


router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("/template")
async def download_inventory_template():
    """
    Download Excel template with all SKUs and current stock

    Returns:
        Excel file ready for editing
    """
    try:
        service = InventoryService()
        excel_file = service.generate_inventory_template()

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Inventario_Grana_{timestamp}.xlsx"

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando plantilla: {str(e)}")


@router.post("/preview")
async def preview_inventory_file(file: UploadFile = File(...)):
    """
    Preview Excel file content WITHOUT updating database

    Returns:
        Dictionary with Excel data for display
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="El archivo debe ser un Excel (.xlsx o .xls)"
            )

        # Read file content
        contents = await file.read()

        # Preview file (NO database update)
        service = InventoryService()
        preview_data = service.preview_inventory_file(
            file_content=contents,
            filename=file.filename
        )

        if preview_data.get("status") == "error":
            raise HTTPException(status_code=400, detail=preview_data.get("message"))

        return preview_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error leyendo archivo: {str(e)}"
        )


@router.post("/bulk-update")
async def bulk_update_inventory(file: UploadFile = File(...)):
    """
    Upload Excel file with inventory updates

    Expected Excel format:
    - Column: Artículo/SKU (SKU code)
    - Column: Cantidad/Nueva Cantidad (New quantity)

    Returns:
        Dictionary with update results
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="El archivo debe ser un Excel (.xlsx o .xls)"
            )

        # Read file content
        contents = await file.read()

        # Process file
        service = InventoryService()
        results = service.process_inventory_upload(
            file_content=contents,
            filename=file.filename
        )

        if results.get("status") == "error":
            raise HTTPException(status_code=400, detail=results.get("message"))

        return {
            "status": "success",
            "data": results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando archivo: {str(e)}"
        )


@router.get("/summary")
async def get_inventory_summary() -> Dict:
    """
    Get inventory summary statistics

    Returns:
        Dictionary with inventory metrics
    """
    try:
        service = InventoryService()
        summary = service.get_stock_summary()

        return {
            "status": "success",
            "data": summary
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo resumen de inventario: {str(e)}"
        )


@router.get("/products")
async def get_all_products_stock() -> Dict:
    """
    Get all products with their current stock levels

    Returns:
        List of products with stock information
    """
    try:
        service = InventoryService()
        products = service.get_all_products_with_stock()

        return {
            "status": "success",
            "data": products,
            "count": len(products)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo productos: {str(e)}"
        )
