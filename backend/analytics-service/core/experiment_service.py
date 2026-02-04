import hashlib
import structlog
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from shared.models.analytics import Experiment, ExperimentVariant

logger = structlog.get_logger(__name__)

class ExperimentService:
    """Service for managing A/B testing experiments and variant assignments"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_experiments(self, merchant_id: int) -> List[Experiment]:
        """Fetch all active experiments for a merchant with their variants"""
        query = (
            select(Experiment)
            .where(
                Experiment.merchant_id == merchant_id,
                Experiment.status == 'active'
            )
            .options(selectinload(Experiment.variants))
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    def _get_hash(self, key: str) -> float:
        """
        Returns a stable float between 0 and 1 for a given key.
        Uses SHA-256 for cross-platform consistency.
        """
        hash_hex = hashlib.sha256(key.encode()).hexdigest()
        # Use first 8 chars (32 bits) for precision
        return int(hash_hex[:8], 16) / 0xFFFFFFFF

    def assign_variant(self, user_id: str, experiment: Experiment) -> Optional[ExperimentVariant]:
        """
        Assigns a variant to a user based on consistent hashing.
        
        Args:
            user_id: Unique identifier for the user (or session_id for anonymous)
            experiment: The Experiment model instance with variants loaded
            
        Returns:
            The assigned ExperimentVariant or None if the user is not in the test group
        """
        if not experiment.variants:
            return None

        # 1. Determine if user is in the test group (Traffic Allocation)
        # Use a salt for traffic hash to separate it from variant hash
        traffic_hash = self._get_hash(f"traffic:{experiment.id}:{user_id}")
        if traffic_hash > experiment.traffic_allocation:
            return None

        # 2. Determine which variant to assign
        variant_hash = self._get_hash(f"variant:{experiment.id}:{user_id}")
        
        # Ensure variants are sorted consistently
        sorted_variants = sorted(experiment.variants, key=lambda v: v.id)
        
        total_weight = sum(v.weight for v in sorted_variants)
        if total_weight <= 0:
            logger.warning("Experiment has zero total weight", experiment_id=experiment.id)
            return None

        cumulative_weight = 0.0
        for variant in sorted_variants:
            normalized_weight = variant.weight / total_weight
            cumulative_weight += normalized_weight
            if variant_hash <= cumulative_weight:
                return variant
        
        # Fallback to last variant due to float precision
        return sorted_variants[-1]

    async def get_assignments(self, merchant_id: int, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all variant assignments for a user across all active experiments.
        """
        active_experiments = await self.get_active_experiments(merchant_id)
        assignments = []
        
        for exp in active_experiments:
            variant = self.assign_variant(user_id, exp)
            if variant:
                assignments.append({
                    "experiment_id": exp.id,
                    "experiment_name": exp.name,
                    "variant_id": variant.id,
                    "variant_name": variant.name,
                    "configuration": variant.configuration or {}
                })
        
        return assignments

    async def create_experiment(self, merchant_id: int, data: Dict[str, Any]) -> Experiment:
        """Create a new experiment with variants"""
        experiment = Experiment(
            merchant_id=merchant_id,
            name=data['name'],
            description=data.get('description'),
            status=data.get('status', 'active'),
            traffic_allocation=data.get('traffic_allocation', 1.0)
        )
        self.db.add(experiment)
        await self.db.flush()
        
        for v_data in data.get('variants', []):
            variant = ExperimentVariant(
                experiment_id=experiment.id,
                name=v_data['name'],
                description=v_data.get('description'),
                weight=v_data.get('weight', 0.5),
                configuration=v_data.get('configuration'),
                is_control=v_data.get('is_control', False)
            )
            self.db.add(variant)
        
        await self.db.commit()
        
        # Re-fetch with variants loaded to avoid MissingGreenlet error during serialization
        query = (
            select(Experiment)
            .where(Experiment.id == experiment.id)
            .options(selectinload(Experiment.variants))
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_experiments(self, merchant_id: int) -> List[Experiment]:
        """List all experiments for a merchant"""
        query = (
            select(Experiment)
            .where(Experiment.merchant_id == merchant_id)
            .options(selectinload(Experiment.variants))
            .order_by(Experiment.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_experiment_results(self, experiment_id: int, merchant_id: int) -> Dict[str, Any]:
        """Calculate and return A/B test results with statistical significance"""
        from core.stats_engine import StatisticsEngine
        
        # 1. Fetch experiment
        query = (
            select(Experiment)
            .where(Experiment.id == experiment_id, Experiment.merchant_id == merchant_id)
            .options(selectinload(Experiment.variants))
        )
        result = await self.db.execute(query)
        experiment = result.scalar_one_or_none()
        
        if not experiment:
            return None

        # 2. Get metrics per variant
        metrics_query = text("""
            SELECT 
                variant_id, 
                COUNT(DISTINCT user_id) as users,
                COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) as conversions,
                COALESCE(SUM(revenue), 0) as total_revenue
            FROM analytics_events
            WHERE experiment_id = :exp_id AND merchant_id = :m_id
            GROUP BY variant_id
        """)
        
        metrics_result = await self.db.execute(metrics_query, {"exp_id": experiment_id, "m_id": merchant_id})
        variant_metrics = {row.variant_id: row for row in metrics_result.fetchall()}

        # 3. Format results and prepare for significance testing
        variant_results = []
        control_variant = None
        
        for variant in experiment.variants:
            m = variant_metrics.get(variant.id)
            users = m.users if m else 0
            conversions = m.conversions if m else 0
            revenue = float(m.total_revenue) if m else 0.0
            
            res = {
                "variant_id": variant.id,
                "variant_name": variant.name,
                "users": users,
                "conversions": conversions,
                "conversion_rate": (conversions / users * 100) if users > 0 else 0.0,
                "revenue": revenue,
                "avg_revenue_per_user": (revenue / users) if users > 0 else 0.0,
                "is_control": variant.is_control
            }
            variant_results.append(res)
            if variant.is_control:
                control_variant = res

        # 4. Calculate significance if we have a control and at least one other variant
        stats = {}
        winner_id = None
        
        if control_variant and len(variant_results) > 1:
            for v in variant_results:
                if v["is_control"]:
                    continue
                
                # Significance for conversion rate
                sig = StatisticsEngine.calculate_conversion_significance(
                    control_variant["users"], 
                    control_conversions=control_variant["conversions"],
                    variant_users=v["users"],
                    variant_conversions=v["conversions"]
                )
                stats[str(v["variant_id"])] = sig
                
                if sig.get("is_significant") and sig.get("lift", 0) > 0:
                    winner_id = v["variant_id"]

        return {
            "experiment_id": experiment.id,
            "experiment_name": experiment.name,
            "variants": variant_results,
            "statistical_significance": stats,
            "winner_variant_id": winner_id
        }
