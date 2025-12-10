"""
Initialize Database for Personalized Search
Creates tables for user interactions and search history
"""

import asyncio
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user_interactions import Base
from core.database import get_database_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_personalization_db():
    """Initialize database tables for personalized search"""
    try:
        # Get database URL
        database_url = get_database_url()
        
        # Create synchronous engine for DDL operations
        sync_database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
        engine = create_engine(sync_database_url)
        
        logger.info("Creating personalized search tables...")
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        logger.info("✅ Personalized search tables created successfully!")
        
        # Test connection with sync engine (simpler for DDL operations)
        # Create a simple connection test
        test_conn = engine.connect()
        try:
            result = test_conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection test successful")
        finally:
            test_conn.close()
        
        await async_engine.dispose()
        engine.dispose()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing personalization database: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(init_personalization_db())
