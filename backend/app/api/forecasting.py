"""
Demand Forecasting API Endpoints

Provides demand forecasts, stockout risk assessment, and lost revenue analysis
for inventory planning and business intelligence.

Author: Claude Code
Date: 2026-01-30
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from dataclasses import asdict

from app.services.demand_forecasting_service import (
    get_forecasting_service,
    DemandForecast,
    StockoutRisk,
    LostRevenueSummary
)

router = APIRouter(prefix="/api/v1/forecasting", tags=["forecasting"])


# =============================================================================
# Pydantic Response Models
# =============================================================================

class ForecastMonth(BaseModel):
    month: str
    yhat: float
    yhat_lower: float
    yhat_upper: float


class DemandForecastResponse(BaseModel):
    sku_primario: str
    product_name: str
    category: str
    forecasts: List[ForecastMonth]
    avg_monthly_demand: float
    demand_std: float
    safety_stock: int
    reorder_point: int
    current_stock: int
    days_of_coverage: float
    forecast_method: str


class StockoutRiskResponse(BaseModel):
    sku_primario: str
    product_name: str
    category: str
    current_stock: int
    avg_monthly_demand: float
    days_of_coverage: float
    safety_stock: int
    reorder_point: int
    risk_level: str
    forecasted_stockout_date: Optional[str]
    units_needed: int


class TopProductLoss(BaseModel):
    sku: str
    name: str
    stockout_count: int
    lost_revenue: float


class LostRevenueSummaryResponse(BaseModel):
    analysis_date: str
    data_period_start: str
    data_period_end: str
    months_analyzed: int
    products_analyzed: int
    products_with_stockouts: int
    total_stockout_periods: int
    total_lost_revenue: float
    annualized_opportunity: float
    conservative_estimate: float
    optimistic_estimate: float
    top_products: List[TopProductLoss]


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/demand/{sku}", response_model=DemandForecastResponse)
async def get_demand_forecast(sku: str):
    """
    Get demand forecast for a specific SKU.

    Uses Prophet time series forecasting with yearly seasonality to predict
    demand for the next 6 months. Includes confidence intervals and safety
    stock recommendations.

    Args:
        sku: The sku_primario to forecast (e.g., BABE_U04010)

    Returns:
        DemandForecastResponse with:
        - forecasts: 6-month forecast with confidence intervals
        - avg_monthly_demand: Average forecasted monthly demand
        - safety_stock: Recommended safety stock level
        - reorder_point: Recommended reorder point
        - current_stock: Current inventory level
        - days_of_coverage: Days until stockout at current rate

    Raises:
        404: SKU not found or insufficient data for forecasting
    """
    service = get_forecasting_service()
    forecast = service.get_demand_forecast(sku)

    if forecast is None:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast available for SKU '{sku}'. Either the SKU doesn't exist or there is insufficient historical data."
        )

    return DemandForecastResponse(
        sku_primario=forecast.sku_primario,
        product_name=forecast.product_name,
        category=forecast.category,
        forecasts=[ForecastMonth(**f) for f in forecast.forecasts],
        avg_monthly_demand=forecast.avg_monthly_demand,
        demand_std=forecast.demand_std,
        safety_stock=forecast.safety_stock,
        reorder_point=forecast.reorder_point,
        current_stock=forecast.current_stock,
        days_of_coverage=forecast.days_of_coverage,
        forecast_method=forecast.forecast_method
    )


@router.get("/stockout-risk", response_model=List[StockoutRiskResponse])
async def get_stockout_risk(
    risk_level: Optional[str] = Query(
        None,
        description="Filter by risk level: critical, high, medium, low"
    ),
    category: Optional[str] = Query(
        None,
        description="Filter by product category"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of products to return")
):
    """
    Get products at risk of stockout, sorted by urgency.

    Analyzes current inventory levels against forecasted demand to identify
    products that may run out of stock before the next replenishment cycle.

    Risk levels:
    - critical: < 15 days of coverage
    - high: 15-30 days of coverage
    - medium: 30-60 days of coverage
    - low: > 60 days of coverage

    Args:
        risk_level: Optional filter for specific risk level
        category: Optional filter for product category
        limit: Maximum number of products to return (default: 50)

    Returns:
        List of StockoutRiskResponse sorted by days_of_coverage (lowest first)
    """
    service = get_forecasting_service()
    risks = service.get_stockout_risk_products(limit=limit * 2)  # Get more to allow filtering

    # Apply filters
    if risk_level:
        risks = [r for r in risks if r.risk_level == risk_level.lower()]

    if category:
        risks = [r for r in risks if r.category and r.category.upper() == category.upper()]

    # Limit results
    risks = risks[:limit]

    return [
        StockoutRiskResponse(
            sku_primario=r.sku_primario,
            product_name=r.product_name,
            category=r.category,
            current_stock=r.current_stock,
            avg_monthly_demand=r.avg_monthly_demand,
            days_of_coverage=r.days_of_coverage,
            safety_stock=r.safety_stock,
            reorder_point=r.reorder_point,
            risk_level=r.risk_level,
            forecasted_stockout_date=r.forecasted_stockout_date,
            units_needed=r.units_needed
        )
        for r in risks
    ]


@router.get("/lost-revenue-summary", response_model=LostRevenueSummaryResponse)
async def get_lost_revenue_summary():
    """
    Get summary of lost revenue from historical stockouts.

    Analyzes sales data to detect periods where sales dropped significantly
    (below 50% of baseline) and later recovered, indicating potential stockouts.
    Calculates the revenue that could have been earned if stock was available.

    Returns:
        LostRevenueSummaryResponse with:
        - total_lost_revenue: Total estimated lost revenue in the analysis period
        - annualized_opportunity: Projected annual revenue opportunity
        - conservative_estimate: 70% of annualized (lower bound)
        - optimistic_estimate: 130% of annualized (upper bound)
        - top_products: Top 5 products by lost revenue
    """
    service = get_forecasting_service()
    summary = service.get_lost_revenue_summary()

    return LostRevenueSummaryResponse(
        analysis_date=summary.analysis_date,
        data_period_start=summary.data_period_start,
        data_period_end=summary.data_period_end,
        months_analyzed=summary.months_analyzed,
        products_analyzed=summary.products_analyzed,
        products_with_stockouts=summary.products_with_stockouts,
        total_stockout_periods=summary.total_stockout_periods,
        total_lost_revenue=summary.total_lost_revenue,
        annualized_opportunity=summary.annualized_opportunity,
        conservative_estimate=summary.conservative_estimate,
        optimistic_estimate=summary.optimistic_estimate,
        top_products=[
            TopProductLoss(
                sku=p['sku'],
                name=p['name'],
                stockout_count=p['stockout_count'],
                lost_revenue=p['lost_revenue']
            )
            for p in summary.top_products
        ]
    )


@router.get("/all-forecasts")
async def get_all_forecasts(
    category: Optional[str] = Query(None, description="Filter by product category"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of products")
):
    """
    Get demand forecasts for all products with sufficient data.

    Returns forecasts for all products that have at least 6 months of
    historical sales data. Useful for batch analysis and dashboard displays.

    Args:
        category: Optional filter for product category
        limit: Maximum number of products to return

    Returns:
        {
            "status": "success",
            "count": 45,
            "data": [DemandForecastResponse, ...]
        }
    """
    service = get_forecasting_service()
    forecasts = service.get_all_forecasts()

    # Apply category filter
    if category:
        forecasts = [f for f in forecasts if f.category and f.category.upper() == category.upper()]

    # Limit and convert
    forecasts = forecasts[:limit]

    return {
        "status": "success",
        "count": len(forecasts),
        "data": [
            {
                "sku_primario": f.sku_primario,
                "product_name": f.product_name,
                "category": f.category,
                "forecasts": f.forecasts,
                "avg_monthly_demand": f.avg_monthly_demand,
                "demand_std": f.demand_std,
                "safety_stock": f.safety_stock,
                "reorder_point": f.reorder_point,
                "current_stock": f.current_stock,
                "days_of_coverage": f.days_of_coverage,
                "forecast_method": f.forecast_method
            }
            for f in forecasts
        ]
    }


@router.post("/invalidate-cache")
async def invalidate_forecasting_cache():
    """
    Invalidate the forecasting service cache.

    Use this endpoint after data syncs or when you need fresh calculations.
    The cache automatically expires after 15 minutes, but this forces
    immediate invalidation.

    Returns:
        {"status": "success", "message": "Cache invalidated"}
    """
    service = get_forecasting_service()
    service.invalidate_cache()

    return {
        "status": "success",
        "message": "Forecasting cache invalidated"
    }
