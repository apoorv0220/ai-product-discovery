"""
Database connection and session management for search service
"""

import os
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = None
async_engine = None
AsyncSessionLocal = None

def get_database_url() -> str:
    """Get database URL from environment variables"""
    global DATABASE_URL
    
    if DATABASE_URL:
        return DATABASE_URL
    
    # Try different environment variable names
    db_url = (
        os.getenv('DATABASE_URL') or
        os.getenv('POSTGRES_URL') or
        os.getenv('DB_URL') or
        os.getenv('POSTGRESQL_URL')
    )
    
    if not db_url:
        # Construct from individual components
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'ai_discovery')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'postgres')
        
        db_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Ensure it's async
    if 'postgresql://' in db_url and 'postgresql+asyncpg://' not in db_url:
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    DATABASE_URL = db_url
    logger.info(f"Using database URL: {db_url.split('@')[0]}@[HIDDEN]")
    return DATABASE_URL

def init_database():
    """Initialize database connection"""
    global async_engine, AsyncSessionLocal
    
    if async_engine is not None:
        return
    
    database_url = get_database_url()
    
    # Create async engine
    async_engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True
    )
    
    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    logger.info("Database connection initialized")

@asynccontextmanager
async def get_async_session():
    """Get async database session"""
    if AsyncSessionLocal is None:
        init_database()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

async def test_database_connection():
    """Test database connection"""
    try:
        async with get_async_session() as session:
            result = await session.execute("SELECT 1")
            logger.info("✅ Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {str(e)}")
        return False

# Initialize on import
init_database()
