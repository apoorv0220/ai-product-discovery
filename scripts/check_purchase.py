import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    db_url = 'postgresql+asyncpg://ai_user:ai_password@localhost:7010/ai_discovery'
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT event_type, revenue, properties FROM analytics_events WHERE session_id = 'funnel_test_973b7b40' AND event_type = 'purchase'"))
        row = res.fetchone()
        if row:
            print(f"Type: {row[0]}, Revenue: {row[1]}, Props: {row[2]}")
        else:
            print("No purchase event found for funnel_test_973b7b40")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
