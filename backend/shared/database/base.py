"""
AI Product Discovery Suite - Database Base Classes

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
import structlog

from shared.config.settings import get_settings

settings = get_settings()

# Create metadata with naming convention
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DATABASE_ECHO,
    future=True
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for all models using traditional declarative_base
Base = declarative_base(metadata=metadata)


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they are registered
            from shared.models import product, user, search, recommendation, analytics
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger = structlog.get_logger()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger = structlog.get_logger()
        logger.warning("Database initialization failed", error=str(e))
        # Don't raise the exception - allow the service to start without database
        pass


async def close_database():
    """Close database connections"""
    await engine.dispose()


# Database utilities
class DatabaseManager:
    """Database manager for handling connections and sessions"""
    
    def __init__(self):
        self.engine = engine
        self.session_maker = AsyncSessionLocal
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.session_maker() as session:
                await session.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session"""
        return self.session_maker()
    
    async def close(self):
        """Close all database connections"""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()