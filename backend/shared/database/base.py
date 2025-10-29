"""
AI Product Discovery Suite - Database Base Classes

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import asyncio
import os
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
    logger = structlog.get_logger()
    
    try:
        # Check if we need database initialization (some services like search may not need full models)
        service_name = os.environ.get('SERVICE_NAME', 'unknown')
        logger.info("Initializing database", service=service_name)
        
        async with engine.begin() as conn:
            # Only try to import models if we're in a service that needs them
            models_imported = False
            
            if service_name in ['celery', 'analytics', 'recommendation']:
                # Services that need full model access
                try:
                    from shared.models import product, user, search, recommendation, analytics
                    logger.info("Successfully imported all models")
                    models_imported = True
                except ImportError:
                    # Try alternative import paths
                    try:
                        from shared.models.product import Product
                        from shared.models.user import User
                        from shared.models.search import SearchQuery
                        from shared.models.recommendation import Recommendation
                        from shared.models.analytics import AnalyticsEvent
                        logger.info("Successfully imported individual models")
                        models_imported = True
                    except ImportError as ie:
                        logger.warning("Could not import models", import_error=str(ie), service=service_name)
            else:
                # Services like search that don't need full models
                logger.info("Skipping model imports for service", service=service_name)
            
            # Create all tables (only if models are registered)
            if models_imported or Base.metadata.tables:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created")
            else:
                logger.info("No models to create tables for")
            
        logger.info("Database initialized successfully")
        
    except Exception as e:
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