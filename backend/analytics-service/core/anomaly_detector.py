try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from shared.models.analytics import AnalyticsAggregation
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)

class AnomalyDetector:
    """Service for detecting anomalies in business metrics using Z-Score analysis"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_metric_history(
        self, 
        merchant_id: int, 
        metric_name: str, 
        days: int = 30
    ) -> List[float]:
        """Fetch historical daily values for a specific metric"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Mapping metric names to column names
        metric_map = {
            "searches": AnalyticsAggregation.searches,
            "purchases": AnalyticsAggregation.purchases,
            "revenue": AnalyticsAggregation.revenue,
            "page_views": AnalyticsAggregation.page_views,
            "product_views": AnalyticsAggregation.product_views,
            "conversions": AnalyticsAggregation.purchases # Using purchases as conversion proxy
        }
        
        if metric_name not in metric_map:
            raise ValueError(f"Unknown metric: {metric_name}")
            
        column = metric_map[metric_name]
        
        query = (
            select(column)
            .where(
                AnalyticsAggregation.merchant_id == merchant_id,
                AnalyticsAggregation.aggregation_type == 'daily',
                AnalyticsAggregation.time_window_start >= start_date
            )
            .order_by(AnalyticsAggregation.time_window_start.asc())
        )
        
        result = await self.db.execute(query)
        return [float(val) for val in result.scalars().all() if val is not None]

    async def detect_anomalies(
        self, 
        merchant_id: int, 
        metric_name: str, 
        current_value: float,
        threshold: float = 2.0
    ) -> Dict[str, Any]:
        """
        Detect if the current value is an anomaly based on historical data.
        """
        if not HAS_NUMPY:
            return {
                "is_anomaly": False,
                "z_score": 0.0,
                "status": "error",
                "message": "Numpy not installed"
            }
            
        history = await self.get_metric_history(merchant_id, metric_name)
        
        if len(history) < 7:
            # Need at least a week of data for meaningful baseline
            return {
                "is_anomaly": False,
                "z_score": 0.0,
                "status": "insufficient_data",
                "message": f"Only {len(history)} days of history available. Need at least 7 days."
            }

        mean = np.mean(history)
        std_dev = np.std(history)
        
        if std_dev == 0:
            # If there's no variation, any difference is technically an infinite z-score,
            # but we'll treat it as normal if it's the same or zero.
            z_score = 0.0 if current_value == mean else 10.0 # Arbitrary high z-score
        else:
            z_score = (current_value - mean) / std_dev
            
        is_anomaly = abs(z_score) > threshold
        
        return {
            "is_anomaly": bool(is_anomaly),
            "z_score": float(z_score),
            "mean": float(mean),
            "std_dev": float(std_dev),
            "current_value": float(current_value),
            "threshold": threshold,
            "severity": "high" if abs(z_score) > 3.0 else "medium" if is_anomaly else "low",
            "direction": "up" if z_score > 0 else "down"
        }

    async def check_all_core_metrics(self, merchant_id: int) -> Dict[str, Any]:
        """Check all core business metrics for anomalies"""
        metrics = ["searches", "purchases", "revenue"]
        results = {}
        
        # Get current daily values (today so far)
        # Note: In a real system, we'd compare today's current partial count 
        # against historical partial counts for the same time of day.
        # For this implementation, we'll fetch the most recent completed daily aggregation.
        
        for metric in metrics:
            try:
                # Get the most recent daily aggregation value
                query = (
                    select(AnalyticsAggregation)
                    .where(
                        AnalyticsAggregation.merchant_id == merchant_id,
                        AnalyticsAggregation.aggregation_type == 'daily'
                    )
                    .order_by(AnalyticsAggregation.time_window_start.desc())
                    .limit(1)
                )
                res = await self.db.execute(query)
                latest_agg = res.scalar_one_or_none()
                
                if not latest_agg:
                    continue
                    
                val_attr = metric if metric != 'conversions' else 'purchases'
                current_val = float(getattr(latest_agg, val_attr, 0))
                
                results[metric] = await self.detect_anomalies(merchant_id, metric, current_val)
            except Exception as e:
                logger.error(f"Error checking anomalies for {metric}", error=str(e))
                
        return results
