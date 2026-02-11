"""
Demand Forecasting Service

Provides demand forecasting, stockout detection, and safety stock calculations
for inventory planning and revenue impact analysis.

Uses Prophet for time series forecasting with fallback to simple exponential smoothing.

Author: Claude Code
Date: 2026-01-30
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd

from app.core.database import get_db_connection_dict_with_retry

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MonthlyForecast:
    """Single month forecast with confidence interval"""
    month: str
    yhat: float
    yhat_lower: float
    yhat_upper: float


@dataclass
class DemandForecast:
    """Complete demand forecast for a product"""
    sku_primario: str
    product_name: str
    category: str
    forecasts: List[Dict[str, Any]]
    avg_monthly_demand: float
    demand_std: float
    safety_stock: int
    reorder_point: int
    current_stock: int
    days_of_coverage: float
    forecast_method: str  # 'prophet' or 'simple'


@dataclass
class StockoutRisk:
    """Product at risk of stockout"""
    sku_primario: str
    product_name: str
    category: str
    current_stock: int
    avg_monthly_demand: float
    days_of_coverage: float
    safety_stock: int
    reorder_point: int
    risk_level: str  # 'critical', 'high', 'medium', 'low'
    forecasted_stockout_date: Optional[str]
    units_needed: int


@dataclass
class StockoutPeriod:
    """Detected historical stockout period"""
    sku_primario: str
    product_name: str
    month: str
    baseline_units: float
    actual_units: float
    lost_units: float
    avg_unit_price: float
    lost_revenue: float


@dataclass
class LostRevenueSummary:
    """Summary of lost revenue from stockouts"""
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
    top_products: List[Dict[str, Any]]


# =============================================================================
# Service Configuration
# =============================================================================

@dataclass
class ForecastConfig:
    """Configuration for forecasting service"""
    lookback_months: int = 24
    forecast_months: int = 6
    stockout_drop_threshold: float = 0.5
    recovery_threshold: float = 0.7
    min_months_for_baseline: int = 3
    lead_time_days: int = 14
    service_level: float = 0.95  # 95% service level (Z = 1.65)


# =============================================================================
# Demand Forecasting Service
# =============================================================================

class DemandForecastingService:
    """
    Service for demand forecasting and stockout analysis.

    Provides:
    - Per-SKU demand forecasts using Prophet
    - Stockout risk assessment
    - Lost revenue calculations
    - Safety stock recommendations
    """

    def __init__(self, config: Optional[ForecastConfig] = None):
        """Initialize service with optional configuration"""
        self.config = config or ForecastConfig()
        self._monthly_sales_cache: Optional[pd.DataFrame] = None
        self._inventory_cache: Optional[pd.DataFrame] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_minutes = 15  # Cache expires after 15 minutes

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self._cache_timestamp is None:
            return False
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds() / 60
        return elapsed < self._cache_ttl_minutes

    def invalidate_cache(self):
        """Force cache invalidation"""
        self._monthly_sales_cache = None
        self._inventory_cache = None
        self._cache_timestamp = None
        logger.info("Forecasting cache invalidated")

    # =========================================================================
    # Data Loading
    # =========================================================================

    def _load_monthly_sales(self) -> pd.DataFrame:
        """Load monthly sales data from sales_facts_mv"""
        if self._monthly_sales_cache is not None and self._is_cache_valid():
            return self._monthly_sales_cache

        logger.info("Loading monthly sales data...")

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

            cursor.execute(query, (self.config.lookback_months,))
            rows = cursor.fetchall()

            if not rows:
                logger.warning("No sales data found")
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            df['month'] = pd.to_datetime(df['month'])
            df['units_sold'] = pd.to_numeric(df['units_sold'], errors='coerce').fillna(0)
            df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0)
            df['avg_unit_price'] = pd.to_numeric(df['avg_unit_price'], errors='coerce').fillna(0)

            self._monthly_sales_cache = df
            self._cache_timestamp = datetime.now()

            logger.info(f"Loaded {len(df)} monthly records for {df['sku_primario'].nunique()} products")
            return df

        finally:
            cursor.close()
            conn.close()

    def _load_current_inventory(self) -> pd.DataFrame:
        """Load current inventory levels"""
        if self._inventory_cache is not None and self._is_cache_valid():
            return self._inventory_cache

        logger.info("Loading current inventory...")

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

            self._inventory_cache = df
            return df

        finally:
            cursor.close()
            conn.close()

    def _get_current_stock(self, sku: str) -> int:
        """Get current stock for a SKU"""
        inventory = self._load_current_inventory()
        if inventory.empty:
            return 0

        match = inventory[inventory['sku'] == sku]
        if match.empty:
            return 0

        return int(match['current_stock'].iloc[0])

    # =========================================================================
    # Forecasting Methods
    # =========================================================================

    def _forecast_prophet(self, sku_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Generate forecast using Prophet"""
        try:
            from prophet import Prophet
        except ImportError:
            logger.warning("Prophet not available")
            return None

        if len(sku_data) < 6:
            return None

        # Prepare data for Prophet
        prophet_df = sku_data[['month', 'units_sold']].copy()
        prophet_df.columns = ['ds', 'y']
        prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])

        # Suppress Prophet output
        import logging as log
        log.getLogger('prophet').setLevel(log.WARNING)
        log.getLogger('cmdstanpy').setLevel(log.WARNING)

        # Fit model
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.95,
            seasonality_mode='multiplicative'
        )
        model.fit(prophet_df)

        # Generate future dates
        future = model.make_future_dataframe(periods=self.config.forecast_months, freq='MS')
        forecast = model.predict(future)

        # Extract future forecasts only
        future_forecasts = forecast[forecast['ds'] > prophet_df['ds'].max()].copy()

        forecasts = []
        for _, row in future_forecasts.iterrows():
            forecasts.append({
                'month': row['ds'].strftime('%Y-%m'),
                'yhat': max(0, float(row['yhat'])),
                'yhat_lower': max(0, float(row['yhat_lower'])),
                'yhat_upper': max(0, float(row['yhat_upper']))
            })

        avg_demand = float(future_forecasts['yhat'].mean())
        demand_std = float((future_forecasts['yhat_upper'] - future_forecasts['yhat_lower']).mean() / (2 * 1.96))

        return {
            'forecasts': forecasts,
            'avg_demand': avg_demand,
            'demand_std': demand_std,
            'method': 'prophet'
        }

    def _forecast_simple(self, sku_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Simple exponential smoothing forecast as fallback"""
        if len(sku_data) < 3:
            return None

        units = sku_data['units_sold'].values
        alpha = 0.3

        # Exponential smoothing
        smoothed = units[0]
        for val in units[1:]:
            smoothed = alpha * val + (1 - alpha) * smoothed

        avg_demand = float(smoothed)
        demand_std = float(sku_data['units_sold'].std())

        # Generate forecasts
        forecasts = []
        last_month = sku_data['month'].max()
        for i in range(1, self.config.forecast_months + 1):
            forecast_month = last_month + pd.DateOffset(months=i)
            forecasts.append({
                'month': forecast_month.strftime('%Y-%m'),
                'yhat': max(0, avg_demand),
                'yhat_lower': max(0, avg_demand - 1.96 * demand_std),
                'yhat_upper': avg_demand + 1.96 * demand_std
            })

        return {
            'forecasts': forecasts,
            'avg_demand': avg_demand,
            'demand_std': demand_std,
            'method': 'simple'
        }

    def _calculate_safety_stock(self, demand_std: float) -> int:
        """Calculate safety stock using classical formula"""
        Z = 1.65 if self.config.service_level == 0.95 else 1.28
        daily_std = demand_std / 30
        safety_stock = Z * daily_std * np.sqrt(self.config.lead_time_days)
        return int(np.ceil(safety_stock))

    def _calculate_reorder_point(self, avg_demand: float, safety_stock: int) -> int:
        """Calculate reorder point"""
        daily_demand = avg_demand / 30
        return int(np.ceil(daily_demand * self.config.lead_time_days + safety_stock))

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def get_demand_forecast(self, sku: str) -> Optional[DemandForecast]:
        """
        Get demand forecast for a specific SKU.

        Args:
            sku: The sku_primario to forecast

        Returns:
            DemandForecast object or None if insufficient data
        """
        monthly_data = self._load_monthly_sales()
        if monthly_data.empty:
            return None

        sku_data = monthly_data[monthly_data['sku_primario'] == sku].copy()
        if sku_data.empty:
            return None

        sku_data = sku_data.sort_values('month').reset_index(drop=True)
        product_name = str(sku_data['product_name'].iloc[0])
        category = str(sku_data['category'].iloc[0]) if sku_data['category'].iloc[0] else 'Unknown'

        # Try Prophet first, fall back to simple
        result = self._forecast_prophet(sku_data)
        if result is None:
            result = self._forecast_simple(sku_data)

        if result is None:
            return None

        safety_stock = self._calculate_safety_stock(result['demand_std'])
        reorder_point = self._calculate_reorder_point(result['avg_demand'], safety_stock)
        current_stock = self._get_current_stock(sku)

        # Calculate days of coverage
        daily_demand = result['avg_demand'] / 30 if result['avg_demand'] > 0 else 0
        days_of_coverage = current_stock / daily_demand if daily_demand > 0 else 999

        return DemandForecast(
            sku_primario=sku,
            product_name=product_name,
            category=category,
            forecasts=result['forecasts'],
            avg_monthly_demand=result['avg_demand'],
            demand_std=result['demand_std'],
            safety_stock=safety_stock,
            reorder_point=reorder_point,
            current_stock=current_stock,
            days_of_coverage=days_of_coverage,
            forecast_method=result['method']
        )

    def get_stockout_risk_products(self, limit: int = 50) -> List[StockoutRisk]:
        """
        Get products at risk of stockout, sorted by risk level.

        Returns:
            List of StockoutRisk objects sorted by days_of_coverage ascending
        """
        monthly_data = self._load_monthly_sales()
        inventory = self._load_current_inventory()

        if monthly_data.empty:
            return []

        products = monthly_data['sku_primario'].unique()
        risks = []

        for sku in products:
            forecast = self.get_demand_forecast(sku)
            if forecast is None:
                continue

            # Determine risk level
            if forecast.days_of_coverage < 15:
                risk_level = 'critical'
            elif forecast.days_of_coverage < 30:
                risk_level = 'high'
            elif forecast.days_of_coverage < 60:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            # Calculate forecasted stockout date
            stockout_date = None
            if forecast.avg_monthly_demand > 0 and forecast.current_stock > 0:
                days_until_stockout = forecast.current_stock / (forecast.avg_monthly_demand / 30)
                stockout_date = (datetime.now() + timedelta(days=days_until_stockout)).strftime('%Y-%m-%d')

            # Calculate units needed to reach reorder point
            units_needed = max(0, forecast.reorder_point - forecast.current_stock)

            risks.append(StockoutRisk(
                sku_primario=sku,
                product_name=forecast.product_name,
                category=forecast.category,
                current_stock=forecast.current_stock,
                avg_monthly_demand=forecast.avg_monthly_demand,
                days_of_coverage=forecast.days_of_coverage,
                safety_stock=forecast.safety_stock,
                reorder_point=forecast.reorder_point,
                risk_level=risk_level,
                forecasted_stockout_date=stockout_date,
                units_needed=units_needed
            ))

        # Sort by days of coverage (lowest first)
        risks.sort(key=lambda x: x.days_of_coverage)

        return risks[:limit]

    def detect_stockout_periods(self) -> List[StockoutPeriod]:
        """
        Detect historical stockout periods from sales data.

        Uses 3-month trailing average as baseline, identifies months where
        sales dropped below 50% of baseline and later recovered.
        """
        monthly_data = self._load_monthly_sales()
        if monthly_data.empty:
            return []

        stockouts = []
        products = monthly_data['sku_primario'].unique()

        for sku in products:
            sku_data = monthly_data[monthly_data['sku_primario'] == sku].copy()
            sku_data = sku_data.sort_values('month').reset_index(drop=True)

            if len(sku_data) < self.config.min_months_for_baseline + 2:
                continue

            product_name = str(sku_data['product_name'].iloc[0])

            # Calculate trailing average
            sku_data['trailing_avg'] = (
                sku_data['units_sold']
                .rolling(self.config.min_months_for_baseline, min_periods=2)
                .mean()
                .shift(1)
            )

            sku_data['drop_ratio'] = sku_data['units_sold'] / sku_data['trailing_avg'].replace(0, np.nan)

            # Get average unit price
            avg_price = sku_data['avg_unit_price'].replace(0, np.nan).mean()
            if pd.isna(avg_price) or avg_price <= 0:
                total_revenue = sku_data['revenue'].sum()
                total_units = sku_data['units_sold'].sum()
                avg_price = total_revenue / total_units if total_units > 0 else 0

            # Identify stockout periods
            for i in range(1, len(sku_data) - 1):
                current = sku_data.iloc[i]

                if pd.isna(current['drop_ratio']) or pd.isna(current['trailing_avg']):
                    continue

                if current['drop_ratio'] < self.config.stockout_drop_threshold:
                    future_data = sku_data.iloc[i+1:]
                    if len(future_data) > 0:
                        future_avg = future_data['units_sold'].mean()
                        baseline = current['trailing_avg']
                        recovery_ratio = future_avg / baseline if baseline > 0 else 0

                        if recovery_ratio >= self.config.recovery_threshold:
                            lost_units = max(0, baseline - current['units_sold'])
                            lost_revenue = lost_units * avg_price

                            stockouts.append(StockoutPeriod(
                                sku_primario=sku,
                                product_name=product_name,
                                month=current['month'].strftime('%Y-%m'),
                                baseline_units=float(baseline),
                                actual_units=float(current['units_sold']),
                                lost_units=float(lost_units),
                                avg_unit_price=float(avg_price),
                                lost_revenue=float(lost_revenue)
                            ))

        return stockouts

    def get_lost_revenue_summary(self) -> LostRevenueSummary:
        """
        Get summary of lost revenue from stockouts.

        Returns:
            LostRevenueSummary with totals and top affected products
        """
        monthly_data = self._load_monthly_sales()
        stockouts = self.detect_stockout_periods()

        if monthly_data.empty:
            return LostRevenueSummary(
                analysis_date=datetime.now().strftime('%Y-%m-%d'),
                data_period_start='N/A',
                data_period_end='N/A',
                months_analyzed=0,
                products_analyzed=0,
                products_with_stockouts=0,
                total_stockout_periods=0,
                total_lost_revenue=0,
                annualized_opportunity=0,
                conservative_estimate=0,
                optimistic_estimate=0,
                top_products=[]
            )

        months_analyzed = monthly_data['month'].nunique()
        total_lost = sum(s.lost_revenue for s in stockouts)
        annualized = total_lost * (12 / months_analyzed) if months_analyzed > 0 else 0

        # Aggregate by product
        product_impact = {}
        for s in stockouts:
            if s.sku_primario not in product_impact:
                product_impact[s.sku_primario] = {
                    'sku': s.sku_primario,
                    'name': s.product_name,
                    'stockout_count': 0,
                    'lost_revenue': 0
                }
            product_impact[s.sku_primario]['stockout_count'] += 1
            product_impact[s.sku_primario]['lost_revenue'] += s.lost_revenue

        # Get top 5 by lost revenue
        top_products = sorted(
            product_impact.values(),
            key=lambda x: x['lost_revenue'],
            reverse=True
        )[:5]

        return LostRevenueSummary(
            analysis_date=datetime.now().strftime('%Y-%m-%d'),
            data_period_start=monthly_data['month'].min().strftime('%Y-%m'),
            data_period_end=monthly_data['month'].max().strftime('%Y-%m'),
            months_analyzed=months_analyzed,
            products_analyzed=monthly_data['sku_primario'].nunique(),
            products_with_stockouts=len(product_impact),
            total_stockout_periods=len(stockouts),
            total_lost_revenue=total_lost,
            annualized_opportunity=annualized,
            conservative_estimate=annualized * 0.7,
            optimistic_estimate=annualized * 1.3,
            top_products=top_products
        )

    def get_all_forecasts(self) -> List[DemandForecast]:
        """Get forecasts for all products with sufficient data"""
        monthly_data = self._load_monthly_sales()
        if monthly_data.empty:
            return []

        forecasts = []
        for sku in monthly_data['sku_primario'].unique():
            forecast = self.get_demand_forecast(sku)
            if forecast:
                forecasts.append(forecast)

        return forecasts


# =============================================================================
# Singleton Factory
# =============================================================================

_forecasting_service: Optional[DemandForecastingService] = None


def get_forecasting_service() -> DemandForecastingService:
    """Get or create the DemandForecastingService singleton"""
    global _forecasting_service
    if _forecasting_service is None:
        _forecasting_service = DemandForecastingService()
    return _forecasting_service
