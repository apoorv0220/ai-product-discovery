"""
Pytest Configuration and Shared Fixtures

@category    Tests
@package     Configuration
@license     MIT License
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import redis.asyncio as redis_async
from faker import Faker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config.settings import get_settings
from shared.auth.api_key_manager import APIKeyManager

settings = get_settings()
fake = Faker()


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (require services)")
    config.addinivalue_line("markers", "regression: Regression tests (prevent breaking changes)")
    config.addinivalue_line("markers", "slow: Slow tests (skip in quick runs)")
    config.addinivalue_line("markers", "performance: Performance tests (may be slow in test environments)")
    config.addinivalue_line("markers", "slow_environment: Tests that may be slow in test environments")
    config.addinivalue_line("markers", "requires_redis: Requires Redis connection")
    config.addinivalue_line("markers", "requires_elasticsearch: Requires Elasticsearch")
    config.addinivalue_line("markers", "requires_qdrant: Requires Qdrant")


# ============================================================================
# PERFORMANCE TEST HELPERS
# ============================================================================

def get_performance_threshold(production_threshold: float, test_multiplier: float = 10.0) -> float:
    """
    Get performance threshold based on environment.
    
    In test environments (CI, local development), Elasticsearch may be slow due to:
    - Cold indices (no warm-up)
    - Limited resources (512MB heap)
    - GC pauses
    - Segment merging
    
    Args:
        production_threshold: Expected threshold in production (ms)
        test_multiplier: Multiplier for test environments (default 10x)
    
    Returns:
        Threshold appropriate for current environment
    """
    # Check if we're in a test environment
    is_test_env = (
        os.getenv("TEST_ENV") == "true" or
        os.getenv("CI") == "true" or
        os.getenv("ENVIRONMENT", "").lower() in ["test", "testing", "development"]
    )
    
    if is_test_env:
        return production_threshold * test_multiplier
    return production_threshold


# ============================================================================
# FUNCTION SCOPE FIXTURES (Setup for each test - database engine)
# ============================================================================

@pytest_asyncio.fixture
async def db_engine():
    """Create database engine for testing
    
    Note: Function-scoped to avoid pytest-asyncio fixture scope conflicts.
    Database connections are pooled, so this is efficient.
    """
    # Use the main development database to avoid creating a separate test DB
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    yield engine
    
    await engine.dispose()


# ============================================================================
# FUNCTION SCOPE FIXTURES (Setup for each test)
# ============================================================================

@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with session_factory() as session:
        try:
            yield session
            # Commit at end if no errors
            await session.commit()
        except Exception:
            # Rollback on error
            await session.rollback()
            raise
        finally:
            # Ensure cleanup
            await session.close()


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[redis_async.Redis, None]:
    """Create Redis client for testing"""
    client = await redis_async.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    
    # Use a test database number
    await client.select(15)  # Use DB 15 for tests
    
    # Clear test keys before test
    await client.flushdb()
    
    yield client
    
    # Clear test keys after test
    await client.flushdb()
    await client.close()


@pytest_asyncio.fixture
async def api_key_manager(db_session) -> APIKeyManager:
    """Create API key manager instance"""
    return APIKeyManager(db_session)


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def test_merchant(db_session) -> dict:
    """Create a test merchant using ORM"""
    from shared.models import Merchant
    
    merchant = Merchant(
        name=fake.company(),
        email=fake.email(),
        company_name=fake.company(),
        tier="pro",
        status="active"
    )
    
    db_session.add(merchant)
    await db_session.flush()  # Flush to DB but don't commit yet
    
    return {
        "id": merchant.id,
        "name": merchant.name,
        "email": merchant.email,
        "tier": merchant.tier,
        "status": merchant.status
    }


@pytest_asyncio.fixture
async def test_api_key(db_session, test_merchant, api_key_manager) -> tuple[str, dict]:
    """Create a test API key"""
    api_key, key_record = await api_key_manager.create_api_key(
        merchant_id=test_merchant["id"],
        name="Test API Key",
        description="Key for testing"
    )
    
    return api_key, key_record


@pytest.fixture
def test_product_data() -> dict:
    """Generate test product data"""
    return {
        "sku": fake.uuid4(),
        "name": fake.catch_phrase(),
        "description": fake.text(max_nb_chars=200),
        "category_name": fake.word().capitalize(),
        "price": float(fake.random_int(min=10, max=1000)),
        "is_in_stock": True
    }


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_elasticsearch(mocker):
    """Mock Elasticsearch client"""
    mock_es = mocker.Mock()
    mock_es.search = mocker.AsyncMock(return_value={
        "hits": {
            "hits": [],
            "total": {"value": 0}
        }
    })
    mock_es.index = mocker.AsyncMock(return_value={"result": "created"})
    mock_es.delete = mocker.AsyncMock(return_value={"result": "deleted"})
    return mock_es


@pytest.fixture
def mock_qdrant(mocker):
    """Mock Qdrant client"""
    mock_qdrant = mocker.Mock()
    mock_qdrant.search = mocker.AsyncMock(return_value=[])
    mock_qdrant.upsert = mocker.AsyncMock(return_value=True)
    mock_qdrant.delete = mocker.AsyncMock(return_value=True)
    return mock_qdrant


# ============================================================================
# HTTP CLIENT FIXTURES
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def initialized_search_app():
    """Initialize FastAPI app with all required state for search service tests"""
    import sys
    import os
    from fastapi import FastAPI
    
    # Add search-service to path
    search_service_path = os.path.join(os.path.dirname(__file__), '..', 'search-service')
    if search_service_path not in sys.path:
        sys.path.insert(0, search_service_path)
    
    from main import app
    from core.elasticsearch_client import ElasticsearchManager
    from core.cache import SearchCache
    from core.ml_engine import MLEngine
    import redis.asyncio as redis_async
    
    # Initialize app state (simulating lifespan startup)
    try:
        # Initialize Elasticsearch
        es_manager = ElasticsearchManager()
        await es_manager.initialize()
        app.state.elasticsearch = es_manager
        
        # Initialize Redis cache
        try:
            redis_client = await redis_async.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            app.state.search_cache = SearchCache(redis_client)
        except Exception:
            app.state.search_cache = None
        
        # Initialize ML Engine (optional - not critical for Phase 1)
        try:
            ml_engine = MLEngine()
            await ml_engine.initialize()
            app.state.ml_engine = ml_engine
        except Exception as e:
            logger.warning("ML Engine initialization failed, continuing without it", error=str(e))
            app.state.ml_engine = None
        
        yield app
        
    finally:
        # Cleanup (simulating lifespan shutdown)
        try:
            if hasattr(app.state, 'ml_engine'):
                await app.state.ml_engine.cleanup()
        except Exception:
            pass
        
        try:
            if hasattr(app.state, 'elasticsearch'):
                await app.state.elasticsearch.close()
        except Exception:
            pass
        
        try:
            if hasattr(app.state, 'search_cache') and app.state.search_cache:
                await app.state.search_cache.redis.close()
        except Exception:
            pass


@pytest_asyncio.fixture
async def search_client(initialized_search_app):
    """Create async HTTP client for search service with initialized app state
    
    Uses httpx.AsyncClient with ASGITransport to properly handle async operations
    that TestClient cannot handle (like asyncio.timeout context managers).
    """
    import httpx
    from httpx import ASGITransport
    
    # Use ASGITransport to properly handle async operations
    transport = ASGITransport(app=initialized_search_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def http_client():
    """Create async HTTP client for API testing"""
    import httpx
    
    async with httpx.AsyncClient(
        base_url="http://localhost:7001",
        timeout=30.0
    ) as client:
        yield client


@pytest.fixture
def auth_headers(test_api_key) -> dict:
    """Create authorization headers"""
    api_key, _ = test_api_key
    return {"Authorization": f"Bearer {api_key}"}


# ============================================================================
# SKIP CONDITION FIXTURES
# ============================================================================

@pytest.fixture
def requires_redis(redis_client):
    """Marker fixture that requires Redis"""
    return redis_client


@pytest.fixture
def requires_elasticsearch():
    """Marker fixture that requires Elasticsearch"""
    import httpx
    try:
        response = httpx.get("http://localhost:9200/_cluster/health", timeout=1)
        if response.status_code != 200:
            pytest.skip("Elasticsearch not available")
    except Exception:
        pytest.skip("Elasticsearch not available")


@pytest.fixture
def requires_qdrant():
    """Marker fixture that requires Qdrant"""
    import httpx
    try:
        response = httpx.get("http://localhost:6333/", timeout=1)
        if response.status_code != 200:
            pytest.skip("Qdrant not available")
    except Exception:
        pytest.skip("Qdrant not available")


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest_asyncio.fixture(autouse=True)
async def cleanup_after_test():
    """Auto cleanup after each test"""
    yield
    
    # Add any global cleanup logic here
    # For example, clearing caches, resetting mocks, etc.
