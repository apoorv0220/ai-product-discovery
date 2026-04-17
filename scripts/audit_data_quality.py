import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Helper to check data quality
async def audit_data_quality():
    print("🔍 Starting Data Quality Audit...")
    
    # Try to get from env, or use the one we found
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        db_url = "postgresql+asyncpg://ai_user:ai_password@localhost:7010/ai_discovery"
    
    if "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    print(f"📡 Connecting to database on {db_url.split('@')[-1]}...")
    
    engine = create_async_engine(db_url)
    
    async with engine.connect() as conn:
        # 1. Check Event Counts
        print("\n--- 1. Event Counts (Raw Table) ---")
        res = await conn.execute(text("SELECT event_type, COUNT(*) FROM analytics_events GROUP BY event_type ORDER BY count DESC"))
        counts = res.fetchall()
        if not counts:
            print("❌ No events found in analytics_events table.")
        for row in counts:
            print(f"  {row[0]:<20}: {row[1]}")

        # 2. Check Recent Funnel Tests
        print("\n--- 2. Recent Funnel Test Sessions ---")
        res = await conn.execute(text("SELECT session_id, event_type, timestamp FROM analytics_events WHERE session_id LIKE 'funnel_test_%' ORDER BY timestamp DESC LIMIT 10"))
        funnel_events = res.fetchall()
        if not funnel_events:
            print("❌ No 'funnel_test_%' sessions found.")
        else:
            for row in funnel_events:
                print(f"  {row[0]:<25} | {row[1]:<15} | {row[2]}")

        # 3. Check Aggregations
        print("\n--- 3. Aggregation Table Status ---")
        res = await conn.execute(text("SELECT aggregation_type, COUNT(*) FROM analytics_aggregations GROUP BY aggregation_type"))
        agg_counts = res.fetchall()
        if not agg_counts:
            print("❌ No data in analytics_aggregations table.")
        for row in agg_counts:
            print(f"  {row[0]:<15}: {row[1]} records")

        # 4. Check specific funnel aggregation
        print("\n--- 4. Latest Real-Time Aggregation Data ---")
        res = await conn.execute(text("""
            SELECT searches, product_views, add_to_carts, purchases, revenue, metrics 
            FROM analytics_aggregations 
            WHERE aggregation_type = 'real_time' 
            ORDER BY time_window_start DESC LIMIT 1
        """))
        latest_agg = res.fetchone()
        if latest_agg:
            print(f"  Searches     : {latest_agg[0]}")
            print(f"  Views        : {latest_agg[1]}")
            print(f"  Add to Carts : {latest_agg[2]}")
            print(f"  Purchases    : {latest_agg[3]}")
            print(f"  Revenue      : {latest_agg[4]}")
            print(f"  Other Metrics: {latest_agg[5]}")
        else:
            print("❌ No recent real-time aggregation found.")

        # 5. Total Business Metrics
        print("\n--- 5. Total Aggregated Business Metrics ---")
        res = await conn.execute(text("SELECT SUM(searches), SUM(product_views), SUM(add_to_carts), SUM(purchases), SUM(revenue) FROM analytics_aggregations WHERE aggregation_type = 'daily'"))
        totals = res.fetchone()
        if totals:
            print(f"  Total Searches     : {totals[0]}")
            print(f"  Total Views        : {totals[1]}")
            print(f"  Total Add to Carts : {totals[2]}")
            print(f"  Total Purchases    : {totals[3]}")
            print(f"  Total Revenue      : {totals[4]}")

    await engine.dispose()
    print("\n✅ Audit Complete.")

if __name__ == "__main__":
    asyncio.run(audit_data_quality())
