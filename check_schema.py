import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from shared.database.base import get_database_session
from sqlalchemy import text

async def check_schema():
    async for session in get_database_session():
        result = await session.execute(text("""
            SELECT column_name, is_nullable, data_type
            FROM information_schema.columns
            WHERE table_name = 'merchandising_rules'
            AND column_name IN ('conditions', 'trigger_conditions', 'target_conditions')
            ORDER BY column_name
        """))
        rows = result.fetchall()
        for row in rows:
            print(f'{row[0]}: nullable={row[1]}, type={row[2]}')

if __name__ == "__main__":
    asyncio.run(check_schema())
