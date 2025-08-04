"""
DiscoverySuite Test Configuration

@category    Backend
@package     Tests
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.shared.database.base import Base, get_db
from backend.shared.config.settings import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Test settings with test database configuration"""
    settings = get_settings()
    settings.DATABASE_URL = "sqlite:///./test.db"
    settings.REDIS_URL = "redis://localhost:6379/1"  # Use different Redis DB for tests
    settings.ELASTICSEARCH_HOST = "localhost"
    settings.ELASTICSEARCH_PORT = 9200
    return settings


@pytest.fixture(scope="session")
def test_engine(test_settings):
    """Create test database engine"""
    engine = create_engine(
        test_settings.DATABASE_URL,
        connect_args={"check_same_thread": False}  # SQLite specific
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up
    Base.metadata.drop_all(bind=engine)
    
    # Remove test database file
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture
def test_db_session(test_engine):
    """Create test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    yield session
    
    session.rollback()
    session.close()


@pytest.fixture
def override_get_db(test_db_session):
    """Override get_db dependency for testing"""
    def _override_get_db():
        try:
            yield test_db_session
        finally:
            test_db_session.close()
    
    return _override_get_db


@pytest.fixture
def mock_elasticsearch():
    """Mock Elasticsearch client"""
    with patch('elasticsearch.Elasticsearch') as mock:
        mock_instance = Mock()
        mock_instance.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            },
            "took": 1
        }
        mock_instance.index.return_value = {"result": "created"}
        mock_instance.delete.return_value = {"result": "deleted"}
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('redis.Redis') as mock:
        mock_instance = Mock()
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = 1
        mock_instance.exists.return_value = False
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_weaviate():
    """Mock Weaviate client"""
    with patch('weaviate.Client') as mock:
        mock_instance = Mock()
        mock_instance.query.get.return_value.with_limit.return_value.do.return_value = {
            "data": {"Get": {"Product": []}}
        }
        mock_instance.data_object.create.return_value = {"id": "test-id"}
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_product_data():
    """Sample product data for testing"""
    return {
        "id": 1,
        "magento_product_id": 123,
        "store_id": 1,
        "sku": "TEST-PRODUCT-001",
        "name": "Test Product",
        "description": "This is a test product description",
        "price": 99.99,
        "special_price": 79.99,
        "status": 1,
        "visibility": 4,
        "is_in_stock": True,
        "qty": 100,
        "category_ids": [1, 2, 3],
        "attributes": {
            "color": "red",
            "size": "large",
            "brand": "test-brand"
        },
        "url_key": "test-product",
        "image_url": "https://example.com/test-product.jpg"
    }


@pytest.fixture
def sample_search_request():
    """Sample search request data"""
    return {
        "query": "test product",
        "store_id": 1,
        "limit": 10,
        "offset": 0,
        "filters": {},
        "sort": "relevance"
    }


@pytest.fixture
def sample_analytics_event():
    """Sample analytics event data"""
    return {
        "event_type": "search",
        "event_data": {
            "query": "test search",
            "results_count": 5,
            "clicked_position": 1
        },
        "user_id": 123,
        "session_id": "test-session-123",
        "store_id": 1,
        "ip_address": "127.0.0.1",
        "user_agent": "Test Browser 1.0"
    }


@pytest.fixture
def sample_recommendation_request():
    """Sample recommendation request data"""
    return {
        "context": "homepage",
        "user_id": 123,
        "store_id": 1,
        "limit": 12,
        "product_id": None,
        "category_id": None
    }


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test"""
    yield
    # This runs after each test
    # Add any cleanup logic here if needed


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_product(**kwargs):
        """Create test product data"""
        default_data = {
            "id": 1,
            "magento_product_id": 123,
            "store_id": 1,
            "sku": "TEST-001",
            "name": "Test Product",
            "description": "Test description",
            "price": 99.99,
            "status": 1,
            "visibility": 4,
            "is_in_stock": True,
            "category_ids": [1, 2]
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_search_query(**kwargs):
        """Create test search query"""
        default_data = {
            "query": "test",
            "store_id": 1,
            "limit": 10,
            "offset": 0
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_analytics_event(**kwargs):
        """Create test analytics event"""
        default_data = {
            "event_type": "page_view",
            "event_data": {},
            "user_id": 1,
            "session_id": "test-session",
            "store_id": 1
        }
        default_data.update(kwargs)
        return default_data


@pytest.fixture
def test_data_factory():
    """Test data factory fixture"""
    return TestDataFactory


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Async testing helpers
@pytest.fixture
async def async_client():
    """Async test client"""
    from httpx import AsyncClient
    from backend.search_service.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# Environment setup
@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Setup test environment"""
    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Cleanup
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Skip tests if dependencies are not available
def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip tests with missing dependencies"""
    import redis
    import elasticsearch
    
    # Check if Redis is available
    try:
        r = redis.Redis(host='localhost', port=6379, db=1)
        r.ping()
        redis_available = True
    except:
        redis_available = False
    
    # Check if Elasticsearch is available
    try:
        es = elasticsearch.Elasticsearch([{'host': 'localhost', 'port': 9200}])
        es.ping()
        elasticsearch_available = True
    except:
        elasticsearch_available = False
    
    skip_redis = pytest.mark.skip(reason="Redis not available")
    skip_elasticsearch = pytest.mark.skip(reason="Elasticsearch not available")
    
    for item in items:
        if "redis" in item.keywords and not redis_available:
            item.add_marker(skip_redis)
        if "elasticsearch" in item.keywords and not elasticsearch_available:
            item.add_marker(skip_elasticsearch)