"""
AI Product Discovery Suite - Search Service Schemas

This package contains all Pydantic schemas used by the Search Service API endpoints.

@category    Backend
@package     SearchService/Schemas
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

# Import all schema classes for easy access
from .search import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SearchMetadata,
    SearchCorrection,
    SearchErrorResponse
)
from .autocomplete import (
    AutocompleteRequest,
    AutocompleteResponse,
    AutocompleteSuggestion,
    AutocompleteMetadata,
    AutocompleteErrorResponse
)
from .product import (
    ProductData,
    ProductStock,
    ProductAttributes,
    DataQualityMetrics
)
from .tracking import (
    ProductViewRequest,
    SearchQueryRequest,
    SearchClickRequest,
    BulkTrackingRequest,
    BulkTrackingResponse,
    TrackingResponse,
    UserHistoryResponse,
    PersonalizationWeightsResponse
)
from .index import (
    IndexRequest,
    IndexResponse,
    IndexStatusResponse,
    EnsureIndexResponse,
    DeleteProductResponse
)
from .semantic_search import (
    SemanticSearchRequest,
    SemanticSearchResult,
    SemanticSearchResponse
)
from .openai_nlp import (
    QueryEntity,
    SearchIntent,
    QueryCorrection,
    OpenAIProcessingResult
)

__all__ = [
    # Search schemas
    "SearchRequest",
    "SearchResponse",
    "SearchResultItem",
    "SearchMetadata",
    "SearchCorrection",
    "SearchErrorResponse",

    # Autocomplete schemas
    "AutocompleteRequest",
    "AutocompleteResponse",
    "AutocompleteSuggestion",
    "AutocompleteMetadata",
    "AutocompleteErrorResponse",

    # Product schemas
    "ProductData",
    "ProductStock",
    "ProductAttributes",
    "DataQualityMetrics",

    # Tracking schemas
    "ProductViewRequest",
    "SearchQueryRequest",
    "SearchClickRequest",
    "BulkTrackingRequest",
    "BulkTrackingResponse",
    "TrackingResponse",
    "UserHistoryResponse",
    "PersonalizationWeightsResponse",

    # Index schemas
    "IndexRequest",
    "IndexResponse",
    "IndexStatusResponse",
    "EnsureIndexResponse",
    "DeleteProductResponse",

    # Semantic search schemas
    "SemanticSearchRequest",
    "SemanticSearchResult",
    "SemanticSearchResponse",

    # OpenAI NLP schemas
    "QueryEntity",
    "SearchIntent",
    "QueryCorrection",
    "OpenAIProcessingResult"
]
