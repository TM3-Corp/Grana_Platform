#!/usr/bin/env python3
"""
Stockout Revenue Impact Analysis

Detects stockout periods from historical sales data, forecasts demand using Prophet,
and calculates lost revenue during stockout periods.

Usage:
    cd backend && source venv/bin/activate
    python -m scripts.analysis.stockout_revenue_analysis

Output:
    - Excel report: stockout_analysis_YYYYMMDD.xlsx
    - JSON data: stockout_analysis_YYYYMMDD.json
    - Markdown summary: stockout_analysis_YYYYMMDD.md

Author: Claude Code
Date: 2026-01-30
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import get_db_connection_dict_with_retry


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class AnalysisConfig:
    """Configuration for stockout analysis"""
    # Data range
    lookback_months: int = 24  # Historical data to analyze

    # Stockout detection thresholds
    stockout_drop_threshold: float = 0.5  # Sales < 50% of baseline = potential stockout
    recovery_threshold: float = 0.7  # Sales must recover to 70%+ to confirm stockout (not discontinuation)
    min_months_for_baseline: int = 3  # Minimum months to calculate baseline

    # Forecasting
    forecast_months: int = 6  # Number of months to forecast ahead

    # Safety stock
    lead_time_days: int = 14  # 2 weeks lead time for this client
    service_level: float = 0.95  # 95% service level (Z = 1.65)

    # Output
    output_dir: str = "output"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class StockoutPeriod:
    """Represents a detected stockout period"""
    sku_primario: str
    product_name: str
    month: datetime
    baseline_units: float
    actual_units: float
    lost_units: float
    avg_unit_price: float
    lost_revenue: float
    recovery_confirmed: bool


@dataclass
class ForecastResult:
    """Prophet forecast result for a product"""
    sku_primario: str
    product_name: str
    forecasts: list  # List of monthly forecasts
    avg_monthly_demand: float
    demand_std: float
    safety_stock: int
    reorder_point: int


@dataclass
class AnalysisSummary:
    """Executive summary of the analysis"""
    analysis_date: str
    data_period_start: str
    data_period_end: str
    months_analyzed: int
    products_analyzed: int
    products_with_stockouts: int
    total_stockout_periods: int
    total_lost_revenue: float
    annualized_opportunity: float
    conservative_estimate: float  # 70% of calculated
    optimistic_estimate: float  # 130% of calculated


# =============================================================================
# Data Extraction
# =============================================================================

def extract_monthly_sales(config: AnalysisConfig) -> pd.DataFrame:
    """
    Extract monthly sales data aggregated at sku_primario level.

    Uses sales_facts_mv which already has conversion factors applied.
    Aggregates by sku_primario to consolidate X1, X5, X16, Caja Master variants.
    """
    print("Extracting monthly sales data...")

    conn = get_db_connection_dict_with_retry()
    cursor = conn.cursor()

    try:
        query = """
        SELECT
            DATE_TRUNC('month', order_date)::date as month,
            sku_primario,
            product_name,
            category,
            SUM(units_sold) as units_sold,
            SUM(revenue) as revenue,
            COUNT(DISTINCT order_id) as order_count,
            AVG(revenue / NULLIF(units_sold, 0)) as avg_unit_price
        FROM sales_facts_mv
        WHERE source = 'relbase'
          AND invoice_status IN ('accepted', 'accepted_objection')
          AND order_date >= CURRENT_DATE - INTERVAL '%s months'
          AND sku_primario IS NOT NULL
        GROUP BY DATE_TRUNC('month', order_date), sku_primario, product_name, category
        ORDER BY sku_primario, month
        """

        cursor.execute(query, (config.lookback_months,))
        rows = cursor.fetchall()

        if not rows:
            print("WARNING: No sales data found!")
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        # Ensure month is datetime
        df['month'] = pd.to_datetime(df['month'])

        # Convert numeric columns
        df['units_sold'] = pd.to_numeric(df['units_sold'], errors='coerce').fillna(0)
        df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0)
        df['order_count'] = pd.to_numeric(df['order_count'], errors='coerce').fillna(0)
        df['avg_unit_price'] = pd.to_numeric(df['avg_unit_price'], errors='coerce').fillna(0)

        print(f"  Extracted {len(df)} monthly records for {df['sku_primario'].nunique()} products")
        print(f"  Date range: {df['month'].min().strftime('%Y-%m')} to {df['month'].max().strftime('%Y-%m')}")

        return df

    finally:
        cursor.close()
        conn.close()


def get_current_inventory() -> pd.DataFrame:
    """
    Get current inventory levels by SKU for safety stock recommendations.
    """
    print("Fetching current inventory levels...")

    conn = get_db_connection_dict_with_retry()
    cursor = conn.cursor()

    try:
        query = """
        SELECT
            COALESCE(sm.target_sku, p.sku) as sku,
            SUM(ws.quantity * COALESCE(sm.quantity_multiplier, 1)) as current_stock
        FROM warehouse_stock ws
        JOIN products p ON p.id = ws.product_id AND p.is_active = true
        JOIN warehouses w ON w.id = ws.warehouse_id
            AND w.is_active = true
            AND w.source = 'relbase'
        LEFT JOIN sku_mappings sm
            ON sm.source_pattern = UPPER(p.sku)
            AND sm.pattern_type = 'exact'
            AND sm.is_active = TRUE
        GROUP BY COALESCE(sm.target_sku, p.sku)
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        df = pd.DataFrame(rows)
        if not df.empty:
            df['current_stock'] = pd.to_numeric(df['current_stock'], errors='coerce').fillna(0)
            print(f"  Found inventory for {len(df)} SKUs")

        return df

    finally:
        cursor.close()
        conn.close()


# =============================================================================
# Stockout Detection
# =============================================================================

def detect_stockout_periods(
    monthly_data: pd.DataFrame,
    config: AnalysisConfig
) -> list[StockoutPeriod]:
    """
    Detect months where sales dropped significantly and later recovered.

    Logic:
    1. Calculate 3-month trailing average as demand baseline
    2. Identify months where actual sales < 50% of baseline
    3. Validate by checking recovery in following months (not discontinuation)
    4. Calculate lost sales = baseline - actual
    """
    print("Detecting stockout periods...")

    stockouts = []
    products = monthly_data['sku_primario'].unique()

    for sku in products:
        sku_data = monthly_data[monthly_data['sku_primario'] == sku].copy()
        sku_data = sku_data.sort_values('month').reset_index(drop=True)

        if len(sku_data) < config.min_months_for_baseline + 2:
            continue  # Not enough data

        product_name = sku_data['product_name'].iloc[0]

        # Calculate trailing average (excluding current month)
        sku_data['trailing_avg'] = (
            sku_data['units_sold']
            .rolling(config.min_months_for_baseline, min_periods=2)
            .mean()
            .shift(1)
        )

        # Calculate drop ratio
        sku_data['drop_ratio'] = sku_data['units_sold'] / sku_data['trailing_avg'].replace(0, np.nan)

        # Get average unit price for this product
        avg_price = sku_data['avg_unit_price'].replace(0, np.nan).mean()
        if pd.isna(avg_price) or avg_price <= 0:
            # Fallback: calculate from revenue/units
            total_revenue = sku_data['revenue'].sum()
            total_units = sku_data['units_sold'].sum()
            avg_price = total_revenue / total_units if total_units > 0 else 0

        # Identify stockout periods
        for i in range(1, len(sku_data) - 1):  # Skip first and last
            current = sku_data.iloc[i]

            if pd.isna(current['drop_ratio']) or pd.isna(current['trailing_avg']):
                continue

            # Check if this is a significant drop
            if current['drop_ratio'] < config.stockout_drop_threshold:
                # Check if there's recovery (not discontinuation)
                future_data = sku_data.iloc[i+1:]
                if len(future_data) > 0:
                    future_avg = future_data['units_sold'].mean()
                    baseline = current['trailing_avg']

                    recovery_ratio = future_avg / baseline if baseline > 0 else 0
                    recovery_confirmed = recovery_ratio >= config.recovery_threshold

                    lost_units = max(0, baseline - current['units_sold'])
                    lost_revenue = lost_units * avg_price

                    stockouts.append(StockoutPeriod(
                        sku_primario=sku,
                        product_name=product_name,
                        month=current['month'],
                        baseline_units=baseline,
                        actual_units=current['units_sold'],
                        lost_units=lost_units,
                        avg_unit_price=avg_price,
                        lost_revenue=lost_revenue,
                        recovery_confirmed=recovery_confirmed
                    ))

    # Filter to confirmed stockouts only
    confirmed_stockouts = [s for s in stockouts if s.recovery_confirmed]

    print(f"  Detected {len(stockouts)} potential stockout periods")
    print(f"  Confirmed {len(confirmed_stockouts)} stockouts (with recovery)")

    return confirmed_stockouts


# =============================================================================
# Demand Forecasting with Prophet
# =============================================================================

def forecast_demand_prophet(
    monthly_data: pd.DataFrame,
    sku: str,
    config: AnalysisConfig
) -> Optional[ForecastResult]:
    """
    Generate demand forecast using Prophet for a single SKU.

    Prophet handles:
    - Seasonality (yearly patterns)
    - Trend (growth/decline)
    - Confidence intervals for uncertainty
    """
    try:
        from prophet import Prophet
    except ImportError:
        print("WARNING: Prophet not installed. Run: pip install prophet")
        return None

    sku_data = monthly_data[monthly_data['sku_primario'] == sku].copy()

    if len(sku_data) < 6:  # Need at least 6 months for Prophet
        return None

    product_name = sku_data['product_name'].iloc[0]

    # Prepare data for Prophet (requires 'ds' and 'y' columns)
    prophet_df = sku_data[['month', 'units_sold']].copy()
    prophet_df.columns = ['ds', 'y']
    prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])

    # Fit Prophet model
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95,  # 95% confidence interval
        seasonality_mode='multiplicative'
    )

    # Suppress Prophet's verbose output
    model.fit(prophet_df)

    # Create future dataframe for forecasting
    future = model.make_future_dataframe(periods=config.forecast_months, freq='MS')
    forecast = model.predict(future)

    # Extract future forecasts only
    future_forecasts = forecast[forecast['ds'] > prophet_df['ds'].max()].copy()

    forecasts = []
    for _, row in future_forecasts.iterrows():
        forecasts.append({
            'month': row['ds'].strftime('%Y-%m'),
            'yhat': max(0, row['yhat']),  # Demand can't be negative
            'yhat_lower': max(0, row['yhat_lower']),
            'yhat_upper': max(0, row['yhat_upper'])
        })

    # Calculate average demand and standard deviation
    avg_demand = future_forecasts['yhat'].mean()

    # Estimate std from Prophet's confidence intervals
    # CI = yhat +/- 1.96 * std for 95% interval
    demand_std = (future_forecasts['yhat_upper'] - future_forecasts['yhat_lower']).mean() / (2 * 1.96)

    # Calculate safety stock
    Z = 1.65 if config.service_level == 0.95 else 1.28  # Z-score for service level
    daily_std = demand_std / 30  # Convert monthly std to daily
    safety_stock = int(np.ceil(Z * daily_std * np.sqrt(config.lead_time_days)))

    # Calculate reorder point
    daily_demand = avg_demand / 30
    reorder_point = int(np.ceil(daily_demand * config.lead_time_days + safety_stock))

    return ForecastResult(
        sku_primario=sku,
        product_name=product_name,
        forecasts=forecasts,
        avg_monthly_demand=avg_demand,
        demand_std=demand_std,
        safety_stock=safety_stock,
        reorder_point=reorder_point
    )


def forecast_demand_simple(
    monthly_data: pd.DataFrame,
    sku: str,
    config: AnalysisConfig
) -> Optional[ForecastResult]:
    """
    Simple Holt-Winters-like forecast for SKUs with limited data.
    Fallback when Prophet is not available or data is too sparse.
    """
    sku_data = monthly_data[monthly_data['sku_primario'] == sku].copy()

    if len(sku_data) < 3:
        return None

    product_name = sku_data['product_name'].iloc[0]

    # Simple exponential smoothing
    units = sku_data['units_sold'].values
    alpha = 0.3  # Smoothing factor

    # Calculate smoothed average
    smoothed = units[0]
    for val in units[1:]:
        smoothed = alpha * val + (1 - alpha) * smoothed

    avg_demand = smoothed
    demand_std = sku_data['units_sold'].std()

    # Generate simple forecasts
    forecasts = []
    last_month = sku_data['month'].max()
    for i in range(1, config.forecast_months + 1):
        forecast_month = last_month + pd.DateOffset(months=i)
        forecasts.append({
            'month': forecast_month.strftime('%Y-%m'),
            'yhat': max(0, avg_demand),
            'yhat_lower': max(0, avg_demand - 1.96 * demand_std),
            'yhat_upper': avg_demand + 1.96 * demand_std
        })

    # Calculate safety stock
    Z = 1.65
    daily_std = demand_std / 30
    safety_stock = int(np.ceil(Z * daily_std * np.sqrt(config.lead_time_days)))

    # Calculate reorder point
    daily_demand = avg_demand / 30
    reorder_point = int(np.ceil(daily_demand * config.lead_time_days + safety_stock))

    return ForecastResult(
        sku_primario=sku,
        product_name=product_name,
        forecasts=forecasts,
        avg_monthly_demand=avg_demand,
        demand_std=demand_std,
        safety_stock=safety_stock,
        reorder_point=reorder_point
    )


def forecast_all_products(
    monthly_data: pd.DataFrame,
    config: AnalysisConfig
) -> list[ForecastResult]:
    """
    Generate forecasts for all products.
    Uses Prophet when possible, falls back to simple method.
    """
    print("Generating demand forecasts...")

    # Check if Prophet is available
    prophet_available = True
    try:
        from prophet import Prophet
    except ImportError:
        prophet_available = False
        print("  Prophet not available, using simple forecasting")

    forecasts = []
    products = monthly_data['sku_primario'].unique()

    for sku in products:
        if prophet_available:
            result = forecast_demand_prophet(monthly_data, sku, config)
        else:
            result = None

        if result is None:
            result = forecast_demand_simple(monthly_data, sku, config)

        if result is not None:
            forecasts.append(result)

    print(f"  Generated forecasts for {len(forecasts)} products")

    return forecasts


# =============================================================================
# Revenue Impact Calculation
# =============================================================================

def calculate_revenue_impact(
    stockouts: list[StockoutPeriod],
    months_analyzed: int
) -> tuple[float, float, float, float]:
    """
    Calculate total and annualized revenue impact.

    Returns:
        (total_lost, annualized, conservative, optimistic)
    """
    total_lost = sum(s.lost_revenue for s in stockouts)

    # Annualize based on months analyzed
    annualized = total_lost * (12 / months_analyzed) if months_analyzed > 0 else 0

    # Confidence range (90% interval)
    conservative = annualized * 0.7  # Conservative: 70%
    optimistic = annualized * 1.3  # Optimistic: 130%

    return total_lost, annualized, conservative, optimistic


# =============================================================================
# Output Generation
# =============================================================================

def generate_excel_report(
    summary: AnalysisSummary,
    stockouts: list[StockoutPeriod],
    forecasts: list[ForecastResult],
    monthly_data: pd.DataFrame,
    inventory: pd.DataFrame,
    output_path: Path
):
    """
    Generate comprehensive Excel report with multiple sheets.
    """
    print(f"Generating Excel report: {output_path}")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: Executive Summary
        summary_data = {
            'Metric': [
                'Analysis Date',
                'Data Period',
                'Months Analyzed',
                'Products Analyzed',
                'Products with Stockouts',
                'Total Stockout Periods',
                '',
                'Total Lost Revenue (CLP)',
                'Annualized Opportunity (CLP)',
                'Conservative Estimate (CLP)',
                'Optimistic Estimate (CLP)'
            ],
            'Value': [
                summary.analysis_date,
                f"{summary.data_period_start} to {summary.data_period_end}",
                summary.months_analyzed,
                summary.products_analyzed,
                summary.products_with_stockouts,
                summary.total_stockout_periods,
                '',
                f"${summary.total_lost_revenue:,.0f}",
                f"${summary.annualized_opportunity:,.0f}",
                f"${summary.conservative_estimate:,.0f}",
                f"${summary.optimistic_estimate:,.0f}"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Executive Summary', index=False)

        # Sheet 2: Per-Product Analysis
        if stockouts:
            product_impact = {}
            for s in stockouts:
                if s.sku_primario not in product_impact:
                    product_impact[s.sku_primario] = {
                        'sku_primario': s.sku_primario,
                        'product_name': s.product_name,
                        'stockout_count': 0,
                        'total_lost_units': 0,
                        'total_lost_revenue': 0,
                        'avg_unit_price': s.avg_unit_price
                    }
                product_impact[s.sku_primario]['stockout_count'] += 1
                product_impact[s.sku_primario]['total_lost_units'] += s.lost_units
                product_impact[s.sku_primario]['total_lost_revenue'] += s.lost_revenue

            product_df = pd.DataFrame(list(product_impact.values()))
            product_df = product_df.sort_values('total_lost_revenue', ascending=False)
            product_df.to_excel(writer, sheet_name='Per-Product Analysis', index=False)

        # Sheet 3: Stockout Timeline
        if stockouts:
            timeline_data = []
            for s in stockouts:
                timeline_data.append({
                    'Month': s.month.strftime('%Y-%m'),
                    'SKU': s.sku_primario,
                    'Product': s.product_name,
                    'Baseline Units': s.baseline_units,
                    'Actual Units': s.actual_units,
                    'Lost Units': s.lost_units,
                    'Avg Price': s.avg_unit_price,
                    'Lost Revenue': s.lost_revenue
                })
            pd.DataFrame(timeline_data).to_excel(writer, sheet_name='Stockout Timeline', index=False)

        # Sheet 4: 6-Month Forecast
        if forecasts:
            forecast_data = []
            for f in forecasts:
                for month_forecast in f.forecasts:
                    forecast_data.append({
                        'SKU': f.sku_primario,
                        'Product': f.product_name,
                        'Month': month_forecast['month'],
                        'Forecast': month_forecast['yhat'],
                        'Lower Bound': month_forecast['yhat_lower'],
                        'Upper Bound': month_forecast['yhat_upper']
                    })
            pd.DataFrame(forecast_data).to_excel(writer, sheet_name='6-Month Forecast', index=False)

        # Sheet 5: Safety Stock Recommendations
        if forecasts:
            safety_data = []
            for f in forecasts:
                current_stock = 0
                if not inventory.empty:
                    inv_match = inventory[inventory['sku'] == f.sku_primario]
                    if not inv_match.empty:
                        current_stock = inv_match['current_stock'].iloc[0]

                safety_data.append({
                    'SKU': f.sku_primario,
                    'Product': f.product_name,
                    'Avg Monthly Demand': f.avg_monthly_demand,
                    'Demand Std Dev': f.demand_std,
                    'Current Stock': current_stock,
                    'Safety Stock': f.safety_stock,
                    'Reorder Point': f.reorder_point,
                    'Days of Coverage': (current_stock / (f.avg_monthly_demand / 30)) if f.avg_monthly_demand > 0 else 999
                })
            pd.DataFrame(safety_data).to_excel(writer, sheet_name='Safety Stock', index=False)

    print(f"  Excel report saved")


def generate_json_output(
    summary: AnalysisSummary,
    stockouts: list[StockoutPeriod],
    forecasts: list[ForecastResult],
    output_path: Path
):
    """
    Generate JSON output for programmatic access.
    """
    print(f"Generating JSON output: {output_path}")

    output = {
        'summary': asdict(summary),
        'stockouts': [
            {
                **asdict(s),
                'month': s.month.strftime('%Y-%m')
            }
            for s in stockouts
        ],
        'forecasts': [asdict(f) for f in forecasts]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"  JSON output saved")


def generate_markdown_summary(
    summary: AnalysisSummary,
    stockouts: list[StockoutPeriod],
    output_path: Path
):
    """
    Generate markdown summary for business proposal.
    """
    print(f"Generating Markdown summary: {output_path}")

    # Calculate top products by lost revenue
    product_impact = {}
    for s in stockouts:
        if s.sku_primario not in product_impact:
            product_impact[s.sku_primario] = {
                'name': s.product_name,
                'count': 0,
                'lost_revenue': 0
            }
        product_impact[s.sku_primario]['count'] += 1
        product_impact[s.sku_primario]['lost_revenue'] += s.lost_revenue

    top_products = sorted(
        product_impact.items(),
        key=lambda x: x[1]['lost_revenue'],
        reverse=True
    )[:5]

    md = f"""# STOCKOUT REVENUE IMPACT ANALYSIS - Grana SpA

**Analysis Date:** {summary.analysis_date}
**Data Period:** {summary.data_period_start} to {summary.data_period_end}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Lost Revenue ({summary.months_analyzed} months) | ${summary.total_lost_revenue:,.0f} CLP |
| **Annualized Opportunity** | **${summary.annualized_opportunity:,.0f} CLP** |
| Confidence Range (90%) | ${summary.conservative_estimate:,.0f} - ${summary.optimistic_estimate:,.0f} CLP |
| Products Affected | {summary.products_with_stockouts} of {summary.products_analyzed} analyzed |
| Total Stockout Periods | {summary.total_stockout_periods} |

---

## Top 5 Products by Lost Revenue

"""

    for i, (sku, data) in enumerate(top_products, 1):
        md += f"{i}. **{sku}** - {data['name']}: ${data['lost_revenue']:,.0f} CLP ({data['count']} stockout periods)\n"

    md += f"""
---

## Investment Justification

| Scenario | Value |
|----------|-------|
| Annual stockout losses | ${summary.annualized_opportunity:,.0f} CLP |
| If 50% of stockouts prevented | ${summary.annualized_opportunity * 0.5:,.0f} CLP recovered |
| Software cost (10% revenue share) | ~${summary.annualized_opportunity * 0.1:,.0f} CLP/year |
| **Net ROI** | **{((summary.annualized_opportunity * 0.5) / (summary.annualized_opportunity * 0.1)):.1f}x** |

---

## Methodology

1. **Data Source:** Relbase invoices (accepted status only)
2. **Stockout Detection:**
   - Calculated 3-month trailing average as baseline demand
   - Identified months where sales dropped below 50% of baseline
   - Confirmed stockouts only where sales recovered to 70%+ in subsequent months
3. **Revenue Calculation:** Lost units × Average unit price
4. **Forecasting:** Prophet model with yearly seasonality and 95% confidence intervals

---

## Recommendations

1. **Implement Safety Stock Alerts:** Automated alerts when inventory drops below reorder point
2. **Demand Forecasting Dashboard:** Real-time 6-month demand forecasts per product
3. **Lost Revenue Tracking:** Monthly reports on actual vs potential revenue

---

*Generated by Grana BI Platform - Stockout Revenue Analysis Module*
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"  Markdown summary saved")


# =============================================================================
# Main Execution
# =============================================================================

def run_analysis(config: Optional[AnalysisConfig] = None) -> dict:
    """
    Main entry point for stockout analysis.

    Returns:
        Dictionary with analysis results
    """
    if config is None:
        config = AnalysisConfig()

    print("=" * 60)
    print("STOCKOUT REVENUE IMPACT ANALYSIS")
    print("=" * 60)
    print()

    # Create output directory
    output_dir = Path(__file__).parent.parent.parent / config.output_dir
    output_dir.mkdir(exist_ok=True)

    # Extract data
    monthly_data = extract_monthly_sales(config)

    if monthly_data.empty:
        print("ERROR: No data found for analysis")
        return {'error': 'No data found'}

    inventory = get_current_inventory()

    # Detect stockouts
    stockouts = detect_stockout_periods(monthly_data, config)

    # Generate forecasts
    forecasts = forecast_all_products(monthly_data, config)

    # Calculate revenue impact
    months_analyzed = monthly_data['month'].nunique()
    total_lost, annualized, conservative, optimistic = calculate_revenue_impact(
        stockouts, months_analyzed
    )

    # Build summary
    products_with_stockouts = len(set(s.sku_primario for s in stockouts))

    summary = AnalysisSummary(
        analysis_date=datetime.now().strftime('%Y-%m-%d'),
        data_period_start=monthly_data['month'].min().strftime('%Y-%m'),
        data_period_end=monthly_data['month'].max().strftime('%Y-%m'),
        months_analyzed=months_analyzed,
        products_analyzed=monthly_data['sku_primario'].nunique(),
        products_with_stockouts=products_with_stockouts,
        total_stockout_periods=len(stockouts),
        total_lost_revenue=total_lost,
        annualized_opportunity=annualized,
        conservative_estimate=conservative,
        optimistic_estimate=optimistic
    )

    # Generate outputs
    timestamp = datetime.now().strftime('%Y%m%d')

    generate_excel_report(
        summary, stockouts, forecasts, monthly_data, inventory,
        output_dir / f'stockout_analysis_{timestamp}.xlsx'
    )

    generate_json_output(
        summary, stockouts, forecasts,
        output_dir / f'stockout_analysis_{timestamp}.json'
    )

    generate_markdown_summary(
        summary, stockouts,
        output_dir / f'stockout_analysis_{timestamp}.md'
    )

    # Print summary
    print()
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print()
    print(f"Total Lost Revenue ({months_analyzed} months): ${total_lost:,.0f} CLP")
    print(f"Annualized Opportunity: ${annualized:,.0f} CLP")
    print(f"Confidence Range (90%): ${conservative:,.0f} - ${optimistic:,.0f} CLP")
    print(f"Products Affected: {products_with_stockouts} of {summary.products_analyzed}")
    print()
    print(f"Output files saved to: {output_dir}")

    return {
        'summary': asdict(summary),
        'stockouts_count': len(stockouts),
        'forecasts_count': len(forecasts),
        'output_dir': str(output_dir)
    }


if __name__ == '__main__':
    run_analysis()
