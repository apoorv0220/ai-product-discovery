try:
    import numpy as np
    from scipy import stats
    HAS_STATS = True
except ImportError:
    HAS_STATS = False
    
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
from sqlalchemy import select, func, and_, text
from shared.database.base import AsyncSessionLocal
from shared.models.analytics import AnalyticsEvent
from shared.models.recommendation import ProductAffinity

logger = structlog.get_logger(__name__)


class AffinityCalculator:
    """Calculates product-to-product affinity based on co-occurrence in sessions"""
    
    async def calculate_all_affinities(self, merchant_id: int):
        """Calculate and update all product affinities for a merchant"""
        async with AsyncSessionLocal() as db_session:
            try:
                # 1. Get all session product view co-occurrences
                # Simplified SQL approach for performance
                query = text("""
                    WITH session_products AS (
                        SELECT session_id, product_id
                        FROM analytics_events
                        WHERE merchant_id = :merch_id 
                          AND event_type = 'product_view'
                          AND product_id IS NOT NULL
                          AND timestamp > NOW() - INTERVAL '30 days'
                        GROUP BY session_id, product_id
                    )
                    SELECT 
                        a.product_id as product_a, 
                        b.product_id as product_b, 
                        COUNT(*) as co_occurrence
                    FROM session_products a
                    JOIN session_products b ON a.session_id = b.session_id AND a.product_id < b.product_id
                    GROUP BY a.product_id, b.product_id
                    HAVING COUNT(*) > 1
                """)
                
                result = await db_session.execute(query, {"merch_id": merchant_id})
                co_occurrences = result.fetchall()
                
                # 2. Update ProductAffinity table
                for row in co_occurrences:
                    prod_a, prod_b, count = row
                    
                    # Normalization (simplified: co-occurrence / total sessions for prod_a)
                    # Real enterprise implementation would use Jaccard Similarity or Cosine Similarity
                    affinity = ProductAffinity(
                        merchant_id=merchant_id,
                        product_a_id=prod_a,
                        product_b_id=prod_b,
                        view_co_occurrence=count,
                        affinity_score=min(count / 100.0, 1.0) # Placeholder normalization
                    )
                    
                    # UPSERT logic (simplified here, in production use database-specific upsert)
                    await db_session.merge(affinity)
                
                await db_session.commit()
                logger.info("Product affinities updated", merchant_id=merchant_id, pairs=len(co_occurrences))
                return True
            except Exception as e:
                logger.error("Affinity calculation failed", error=str(e))
                await db_session.rollback()
                return False


class StatisticsEngine:
    """Engine for calculating statistical significance and metrics for A/B tests"""
    
    @staticmethod
    async def generate_experiment_report(
        merchant_id: int,
        experiment_id: int,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Generate a full statistical report for an A/B test"""
        from shared.models.analytics import AnalyticsEvent, Experiment
        from sqlalchemy import select, func, and_
        
        # 1. Get experiment details
        exp_result = await db_session.execute(select(Experiment).where(Experiment.id == experiment_id))
        experiment = exp_result.scalar_one_or_none()
        if not experiment:
            return {"error": "Experiment not found"}
            
        # 2. Get variants data
        # In a real system, we'd query variant users and conversions
        # For this POC, we'll aggregate from AnalyticsEvent
        
        query = text("""
            SELECT 
                variant_id, 
                COUNT(DISTINCT user_id) as users,
                COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) as conversions,
                SUM(CASE WHEN event_type = 'purchase' THEN revenue ELSE 0 END) as total_revenue
            FROM analytics_events
            WHERE experiment_id = :exp_id AND merchant_id = :merch_id
            GROUP BY variant_id
        """)
        
        result = await db_session.execute(query, {"exp_id": experiment_id, "merch_id": merchant_id})
        data = result.fetchall()
        
        if len(data) < 2:
            return {"status": "insufficient_data", "message": "At least 2 variants needed for comparison"}
            
        # 3. Identify control and treatment
        # (Assuming the first one is control for now or checking a flag)
        control = data[0]
        treatment = data[1]
        
        # 4. Calculate significance
        sig_results = StatisticsEngine.calculate_conversion_significance(
            control_users=control.users,
            control_conversions=control.conversions,
            variant_users=treatment.users,
            variant_conversions=treatment.conversions
        )
        
        return {
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "control": {
                "variant_id": control.variant_id,
                "users": control.users,
                "conversions": control.conversions,
                "revenue": float(control.total_revenue or 0)
            },
            "treatment": {
                "variant_id": treatment.variant_id,
                "users": treatment.users,
                "conversions": treatment.conversions,
                "revenue": float(treatment.total_revenue or 0)
            },
            "significance": sig_results
        }
    
    @staticmethod
    def calculate_conversion_significance(
        control_users: int, 
        control_conversions: int, 
        variant_users: int, 
        variant_conversions: int,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculates Chi-Square significance for conversion rates.
        """
        if not HAS_STATS:
            return {
                "p_value": 1.0,
                "is_significant": False,
                "confidence": 0.0,
                "lift": 0.0,
                "error": "Statistical libraries (scipy/numpy) not installed"
            }
            
        if control_users <= 0 or variant_users <= 0:
            return {
                "p_value": 1.0,
                "is_significant": False,
                "confidence": 0.0,
                "lift": 0.0,
                "error": "Insufficient data"
            }

        control_rate = control_conversions / control_users
        variant_rate = variant_conversions / variant_users
        
        lift = (variant_rate - control_rate) / control_rate if control_rate > 0 else 0.0
        
        # Contingency table: [[conversions, non-conversions], [conversions, non-conversions]]
        table = [
            [control_conversions, control_users - control_conversions],
            [variant_conversions, variant_users - variant_conversions]
        ]
        
        try:
            chi2, p_value, dof, expected = stats.chi2_contingency(table)
            is_significant = p_value < (1 - confidence_level)
            
            return {
                "p_value": float(p_value),
                "is_significant": bool(is_significant),
                "confidence": float((1 - p_value) * 100),
                "lift": float(lift * 100), # Percentage
                "control_rate": float(control_rate * 100),
                "variant_rate": float(variant_rate * 100)
            }
        except Exception as e:
            logger.error("Error calculating chi-square", error=str(e))
            return {
                "p_value": 1.0,
                "is_significant": False,
                "confidence": 0.0,
                "lift": float(lift * 100),
                "error": str(e)
            }

    @staticmethod
    def calculate_continuous_significance(
        control_values: List[float], 
        variant_values: List[float],
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculates Welch's T-test for continuous metrics (e.g., revenue per user).
        """
        if not HAS_STATS:
            return {
                "p_value": 1.0,
                "is_significant": False,
                "confidence": 0.0,
                "lift": 0.0,
                "error": "Statistical libraries (scipy/numpy) not installed"
            }
            
        if not control_values or not variant_values:
            return {
                "p_value": 1.0,
                "is_significant": False,
                "confidence": 0.0,
                "lift": 0.0,
                "error": "Insufficient data"
            }

        control_mean = np.mean(control_values)
        variant_mean = np.mean(variant_values)
        
        lift = (variant_mean - control_mean) / control_mean if control_mean > 0 else 0.0
        
        try:
            # Using Welch's t-test (equal_var=False) as groups may have different variances
            t_stat, p_value = stats.ttest_ind(control_values, variant_values, equal_var=False)
            is_significant = p_value < (1 - confidence_level)
            
            return {
                "p_value": float(p_value),
                "is_significant": bool(is_significant),
                "confidence": float((1 - p_value) * 100),
                "lift": float(lift * 100),
                "control_mean": float(control_mean),
                "variant_mean": float(variant_mean),
                "t_stat": float(t_stat)
            }
        except Exception as e:
            logger.error("Error calculating t-test", error=str(e))
            return {
                "p_value": 1.0,
                "is_significant": False,
                "confidence": 0.0,
                "lift": float(lift * 100),
                "error": str(e)
            }
