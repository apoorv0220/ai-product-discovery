"""
Shared SQLAlchemy models for the AI Product Discovery Suite.

This package exposes a single declarative Base and all ORM models
used across services (merchants, API keys, personalization, etc.).

All models are imported here to ensure they are registered with
Base.metadata for Alembic migrations.
"""

from shared.database.base import Base

# Import all models - order matters to avoid circular dependencies
# Import core models first (no dependencies)
from shared.models.merchant import Merchant  # noqa: F401

# Import models that depend on core models
from shared.models.api_key import APIKey  # noqa: F401
from shared.models.api_key_usage import APIKeyUsage  # noqa: F401
from shared.models.analytics import (  # noqa: F401
    AnalyticsEvent,
    AnalyticsAggregation,
    UserBehaviorAggregation,
    SessionAnalytics,
    AnalyticsEventArchive,
    Experiment,
    ExperimentVariant,
    ConversionFunnel,
    FunnelStep,
)
from shared.models.recommendation import ProductSimilarity  # noqa: F401

# Import personalization models
from shared.models.personalization import (  # noqa: F401
    UserSearchHistory,
    UserProductViews,
    UserSearchClicks,
    PersonalizedSearchWeights,
)

# Import merchandising models
from shared.models.merchandising import MerchandisingRule  # noqa: F401

__all__ = [
    "Base",
    # Core models
    "Merchant",
    # Dependent models
    "APIKey",
    "APIKeyUsage",
    "AnalyticsEvent",
    "AnalyticsAggregation",
    "UserBehaviorAggregation",
    "SessionAnalytics",
    "AnalyticsEventArchive",
    "Experiment",
    "ExperimentVariant",
    "ConversionFunnel",
    "FunnelStep",
    "ProductSimilarity",
    # Personalization models
    "UserSearchHistory",
    "UserProductViews",
    "UserSearchClicks",
    "PersonalizedSearchWeights",
    # Merchandising models
    "MerchandisingRule",
]

