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

# Create async engine with optimized connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_recycle=getattr(settings, 'DATABASE_POOL_RECYCLE', 3600),  # 1 hour
    pool_pre_ping=getattr(settings, 'DATABASE_POOL_PRE_PING', True),  # Connection health checks
    echo=settings.DATABASE_ECHO,
    future=True,
    # Connection timeout
    connect_args={
        "server_settings": {
            "application_name": "ai_discovery_analytics",
            "tcp_keepalives_idle": "600",
            "tcp_keepalives_interval": "30",
            "tcp_keepalives_count": "3"
        }
    }
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


# Backwards-compatible alias for middleware expecting get_db
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Backwards-compatible alias - directly yields database session"""
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
                # Import all models through shared.models.__init__ to register them with Base.metadata
                try:
                    from shared.models import (
                        Merchant, APIKey, APIKeyUsage,
                        AnalyticsEvent, ProductSimilarity,
                        UserSearchHistory, UserProductViews, UserSearchClicks, PersonalizedSearchWeights
                    )
                    logger.info("Successfully imported models")
                    models_imported = True
                except ImportError as ie:
                    logger.warning("Could not import models", import_error=str(ie), service=service_name)
            else:
                # Services like search that don't need full models
                logger.info("Skipping model imports for service", service=service_name)
            
            # NOTE: Base.metadata.create_all is typically NOT recommended when using Alembic
            # as it bypasses the migration history. We keep it as a fallback but log a warning.
            if models_imported or Base.metadata.tables:
                # await conn.run_sync(Base.metadata.create_all)
                # logger.info("Database tables created via create_all (NOTE: Use alembic instead)")
                logger.info("Database models registered. Skipping create_all in favor of Alembic migrations.")
            else:
                logger.info("No models to register")
            
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
            from sqlalchemy import text
            async with self.session_maker() as session:
                await session.execute(text("SELECT 1"))
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