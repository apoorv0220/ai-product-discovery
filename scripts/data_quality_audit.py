import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import select, func
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

load_dotenv()

from shared.database.base import AsyncSessionLocal
from shared.models.analytics import AnalyticsEvent

async def data_quality_audit():
    try:
        async with AsyncSessionLocal() as session:
            # Find sessions with multiple event types
            query = select(
                AnalyticsEvent.session_id,
                func.count(AnalyticsEvent.id).label('event_count'),
                func.array_agg(AnalyticsEvent.event_type).label('event_types')
            ).group_by(
                AnalyticsEvent.session_id
            ).having(
                func.count(func.distinct(AnalyticsEvent.event_type)) >= 2
            ).limit(5)
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            if not rows:
                print("No sessions found with multiple event types.")
                return

            print(f"Found {len(rows)} candidate sessions for audit.")
            
            for row in rows:
                session_id = row.session_id
                print(f"\nAudit for Session ID: {session_id}")
                
                # Get all events for this session ordered by timestamp
                event_query = select(AnalyticsEvent).where(
                    AnalyticsEvent.session_id == session_id
                ).order_by(AnalyticsEvent.timestamp)
                
                event_result = await session.execute(event_query)
                events = event_result.scalars().all()
                
                for e in events:
                    event_id_str = str(e.event_id)
                    print(f"  [{e.timestamp}] {e.event_type:15} | ID: {event_id_str[:8]}... | Product: {e.product_id or 'N/A'}")
                    if e.properties:
                        # Print some key properties
                        props = e.properties
                        if 'search_query' in props:
                            print(f"    Search Query: {props['search_query']}")
                        if 'query' in props:
                            print(f"    Query: {props['query']}")
                        if 'clicked_product_name' in props:
                            print(f"    Clicked Product: {props['clicked_product_name']}")
                        if 'product_name' in props:
                            print(f"    Product Name: {props['product_name']}")

    except Exception as e:
        print(f"Error during audit: {e}")

if __name__ == "__main__":
    asyncio.run(data_quality_audit())
