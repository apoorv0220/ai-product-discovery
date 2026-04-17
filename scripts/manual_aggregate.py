import asyncio
import os
import sys
from datetime import datetime

# Add paths dynamically for imports relative to /scripts
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(script_dir, "../backend"))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, 'shared'))
sys.path.insert(0, os.path.join(backend_dir, 'analytics-service'))

from shared.database.base import AsyncSessionLocal, engine
from shared.models.analytics import AnalyticsEvent
from core.aggregator import DataAggregator
from sqlalchemy import select

async def run_manual_aggregation():
    print("Starting manual aggregation of all existing events...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AnalyticsEvent))
        events = result.scalars().all()
        
        events_list = []
        for event in events:
            events_list.append({
                'event_id': str(event.event_id),
                'event_type': event.event_type,
                'merchant_id': event.merchant_id,
                'user_id': event.user_id,
                'session_id': event.session_id,
                'product_id': event.product_id,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                'revenue': event.revenue,
                'properties': event.properties or {}
            })
        
        if not events_list:
            print("No events found to aggregate.")
            return

    print(f"Found {len(events_list)} events. Aggregating...")
    aggregator = DataAggregator()
    success = await aggregator.aggregate_events(events_list)
    print(f"Aggregation {'succeeded' if success else 'failed'}.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_manual_aggregation())
