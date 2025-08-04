"""
AI Product Discovery Suite - Search Schemas

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator


class SearchRequest(BaseModel):
    """Search request schema"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    store_id: int = Field(..., ge=1, description="Store ID")
    limit: int = Field(default=20, ge=1, le=100, description="Result limit")
    offset: int = Field(default=0, ge=0, description="Result offset")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    sort_order: Optional[str] = Field(default=None, description="Sort order")
    user_id: Optional[int] = Field(default=None, description="User ID for personalization")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v is not None:
            allowed_sorts = ['relevance', 'price_asc', 'price_desc', 'name_asc', 'name_desc', 'newest', 'popularity']
            if v not in allowed_sorts:
                raise ValueError(f'Sort order must be one of: {", ".join(allowed_sorts)}')
        return v


class SearchResult(BaseModel):
    """Individual search result schema"""
    id: int = Field(..., description="Product ID")
    magento_product_id: int = Field(..., description="Magento Product ID")
    sku: str = Field(..., description="Product SKU")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(default=None, description="Product description")
    short_description: Optional[str] = Field(default=None, description="Short description")
    price: Optional[float] = Field(default=None, description="Product price")
    special_price: Optional[float] = Field(default=None, description="Special price")
    image_url: Optional[str] = Field(default=None, description="Product image URL")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail URL")
    url_key: Optional[str] = Field(default=None, description="URL key")
    category_ids: List[int] = Field(default_factory=list, description="Category IDs")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Product attributes")
    ai_tags: List[str] = Field(default_factory=list, description="AI-generated tags")
    quality_score: Optional[float] = Field(default=None, description="AI quality score")
    relevance_score: float = Field(..., description="Search relevance score")
    position: int = Field(..., description="Position in results")
    is_in_stock: bool = Field(default=True, description="Stock status")
    qty: Optional[float] = Field(default=None, description="Available quantity")
    avg_rating: Optional[float] = Field(default=None, description="Average rating")
    review_count: int = Field(default=0, description="Number of reviews")


class SearchFacet(BaseModel):
    """Search facet/filter schema"""
    field: str = Field(..., description="Facet field name")
    label: str = Field(..., description="Display label")
    values: List[Dict[str, Union[str, int]]] = Field(..., description="Facet values")
    type: str = Field(default="terms", description="Facet type")


class SearchResponse(BaseModel):
    """Search response schema"""
    products: List[SearchResult] = Field(default_factory=list, description="Search results")
    total_count: int = Field(default=0, description="Total number of results")
    facets: List[SearchFacet] = Field(default_factory=list, description="Available facets")
    suggestions: List[str] = Field(default_factory=list, description="Search suggestions")
    spell_correction: Optional[str] = Field(default=None, description="Spell correction")
    query_id: str = Field(..., description="Unique query ID for tracking")
    search_time_ms: Optional[int] = Field(default=None, description="Search execution time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AutocompleteItem(BaseModel):
    """Autocomplete suggestion item"""
    text: str = Field(..., description="Suggestion text")
    type: str = Field(..., description="Suggestion type (query, product, category)")
    count: Optional[int] = Field(default=None, description="Result count")
    boost: float = Field(default=1.0, description="Boost score")


class AutocompleteProduct(BaseModel):
    """Autocomplete product result"""
    id: int = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    price: Optional[float] = Field(default=None, description="Product price")
    image_url: Optional[str] = Field(default=None, description="Product image")
    url: str = Field(..., description="Product URL")


class AutocompleteCategory(BaseModel):
    """Autocomplete category result"""
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    product_count: int = Field(default=0, description="Number of products")
    url: str = Field(..., description="Category URL")


class AutocompleteResponse(BaseModel):
    """Autocomplete response schema"""
    suggestions: List[AutocompleteItem] = Field(default_factory=list, description="Query suggestions")
    products: List[AutocompleteProduct] = Field(default_factory=list, description="Product results")
    categories: List[AutocompleteCategory] = Field(default_factory=list, description="Category results")
    query: str = Field(..., description="Original query")
    search_time_ms: Optional[int] = Field(default=None, description="Response time")


class SuggestionsResponse(BaseModel):
    """Search suggestions response"""
    suggestions: List[str] = Field(default_factory=list, description="Related queries")
    spell_correction: Optional[str] = Field(default=None, description="Spell correction")
    synonyms: List[str] = Field(default_factory=list, description="Synonym suggestions")
    related_queries: List[str] = Field(default_factory=list, description="Related queries")


class SpellCorrectionResponse(BaseModel):
    """Spell correction response"""
    original_query: str = Field(..., description="Original query")
    corrected_query: Optional[str] = Field(default=None, description="Corrected query")
    confidence: float = Field(default=0.0, description="Correction confidence")
    suggestions: List[str] = Field(default_factory=list, description="Alternative suggestions")


class SearchAnalytics(BaseModel):
    """Search analytics schema"""
    total_searches: int = Field(default=0, description="Total search count")
    unique_queries: int = Field(default=0, description="Unique query count")
    zero_result_queries: int = Field(default=0, description="Queries with no results")
    avg_results_per_query: float = Field(default=0.0, description="Average results per query")
    avg_search_time_ms: float = Field(default=0.0, description="Average search time")
    top_queries: List[Dict[str, Any]] = Field(default_factory=list, description="Most popular queries")
    top_zero_result_queries: List[str] = Field(default_factory=list, description="Top queries with no results")
    conversion_rate: float = Field(default=0.0, description="Search to purchase conversion rate")
    click_through_rate: float = Field(default=0.0, description="Search click-through rate")


class IndexRequest(BaseModel):
    """Product index request schema"""
    products: List[Dict[str, Any]] = Field(..., description="Products to index")
    store_id: int = Field(..., description="Store ID")
    full_reindex: bool = Field(default=False, description="Whether to perform full reindex")


class IndexResponse(BaseModel):
    """Index operation response"""
    success: bool = Field(..., description="Operation success status")
    indexed_count: int = Field(default=0, description="Number of products indexed")
    failed_count: int = Field(default=0, description="Number of failed products")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    execution_time_ms: int = Field(default=0, description="Execution time")