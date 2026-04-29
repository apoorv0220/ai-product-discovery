from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from shared.models.analytics import ConversionFunnel, FunnelStep, AnalyticsEvent
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

class FunnelService:
    """Service for managing and analyzing conversion funnels"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_funnel(self, merchant_id: int, data: Dict[str, Any]) -> ConversionFunnel:
        """Create a new funnel with steps"""
        funnel = ConversionFunnel(
            merchant_id=merchant_id,
            name=data['name'],
            description=data.get('description'),
            is_active=data.get('is_active', True)
        )
        self.db.add(funnel)
        await self.db.flush() # Get funnel ID
        
        for i, step_data in enumerate(data.get('steps', [])):
            step = FunnelStep(
                funnel_id=funnel.id,
                name=step_data['name'],
                event_type=step_data['event_type'],
                step_order=i,
                properties_filter=step_data.get('properties_filter')
            )
            self.db.add(step)
        
        await self.db.commit()
        
        # Re-fetch with steps loaded to avoid MissingGreenlet error during serialization
        query = (
            select(ConversionFunnel)
            .where(ConversionFunnel.id == funnel.id)
            .options(selectinload(ConversionFunnel.steps))
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_funnels(self, merchant_id: int) -> List[ConversionFunnel]:
        """Get all funnels for a merchant"""
        query = select(ConversionFunnel).where(
            ConversionFunnel.merchant_id == merchant_id
        ).options(selectinload(ConversionFunnel.steps))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_funnel_analytics(
        self, 
        funnel_id: int, 
        merchant_id: int,
        start_date: datetime, 
        end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate funnel analytics by tracking users through defined steps.
        Uses a sequential sequence tracking approach.
        """
        query = (
            select(ConversionFunnel)
            .where(
                ConversionFunnel.id == funnel_id,
                ConversionFunnel.merchant_id == merchant_id
            )
            .options(selectinload(ConversionFunnel.steps))
        )
        result = await self.db.execute(query)
        funnel = result.scalar_one_or_none()
        
        if not funnel:
            return None

        steps = sorted(funnel.steps, key=lambda s: s.step_order)
        if not steps:
            return {
                "funnel_id": funnel.id,
                "funnel_name": funnel.name,
                "steps": [],
                "overall_conversion": 0.0
            }

        # Build dynamic CTE-based query for sequential steps
        cte_parts = []
        params = {
            "merchant_id": merchant_id,
            "start_date": start_date,
            "end_date": end_date
        }

        for i, step in enumerate(steps):
            step_param = f"step_type_{i}"
            params[step_param] = step.event_type
            
            if i == 0:
                # First step: Initial cohort of users
                part = f"""
                step0 AS (
                    SELECT user_id, MIN(timestamp) as t0
                    FROM analytics_events
                    WHERE merchant_id = :merchant_id
                    AND event_type = :{step_param}
                    AND timestamp BETWEEN :start_date AND :end_date
                    GROUP BY user_id
                )"""
            else:
                # Subsequent steps: Users from previous step who did the next event after
                part = f"""
                step{i} AS (
                    SELECT s.user_id, MIN(e.timestamp) as t{i}
                    FROM step{i-1} s
                    JOIN analytics_events e ON s.user_id = e.user_id
                    WHERE e.merchant_id = :merchant_id
                    AND e.event_type = :{step_param}
                    AND e.timestamp > s.t{i-1}
                    AND e.timestamp <= :end_date
                    GROUP BY s.user_id
                )"""
            cte_parts.append(part)

        # Final select to count users at each step
        select_parts = [f"(SELECT COUNT(*) FROM step{i}) as step{i}_count" for i in range(len(steps))]
        full_query = "WITH " + ", ".join(cte_parts) + " SELECT " + ", ".join(select_parts)
        
        try:
            result = await self.db.execute(text(full_query), params)
            row = result.fetchone()
            
            funnel_results = []
            previous_count = 0
            total_entry = 0
            
            for i, step in enumerate(steps):
                count = row[i] if row else 0
                
                if i == 0:
                    total_entry = count
                    drop_off = 0
                    step_conversion = 100.0 if count > 0 else 0.0
                else:
                    drop_off = previous_count - count
                    step_conversion = (count / previous_count * 100) if previous_count > 0 else 0.0
                
                total_conversion = (count / total_entry * 100) if total_entry > 0 else 0.0
                
                funnel_results.append({
                    "step_order": i,
                    "step_name": step.name,
                    "event_type": step.event_type,
                    "count": count,
                    "drop_off": drop_off,
                    "step_conversion": round(step_conversion, 2),
                    "total_conversion": round(total_conversion, 2)
                })
                previous_count = count

            return {
                "funnel_id": funnel.id,
                "funnel_name": funnel.name,
                "steps": funnel_results,
                "overall_conversion": funnel_results[-1]["total_conversion"] if funnel_results else 0.0,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
        except Exception as e:
            logger.error("Error calculating funnel analytics", error=str(e), funnel_id=funnel_id)
            raise
