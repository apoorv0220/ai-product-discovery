"""
Updated Autocomplete Schemas for AI Product Discovery Suite
Reflects actual API response formats with OpenAI integration

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AutocompleteSuggestion(BaseModel):
    """Individual autocomplete suggestion with all Magento-required fields"""
    suggestion: str = Field(..., description="The suggestion text")
    title: str = Field(..., description="Product title (same as suggestion for products)")
    type: str = Field(..., description="Type of suggestion: 'product', 'category', 'brand'")
    count: int = Field(default=1, description="Number of results for this suggestion")
    image: str = Field(default="", description="Product image URL")
    price: str = Field(default="$0.00", description="Formatted price string")
    url: str = Field(default="#", description="Product or category URL")
    category: str = Field(default="General", description="Category name (not ID)")
    sku: str = Field(default="", description="Product SKU")
    id: int = Field(default=0, description="Product ID")
    
    # AI Enhancement Fields
    nlp_enhanced: bool = Field(default=False, description="Whether NLP processing was used")
    is_corrected: bool = Field(default=False, description="Whether typo correction was applied")
    corrected_from: str = Field(default="", description="Original text before correction")
    corrected_to: str = Field(default="", description="Corrected text")
    correction_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Typo correction confidence score")
    correction_type: str = Field(default="", description="Type of correction: 'openai_correction', 'basic_correction'")
    intent_type: str = Field(default="", description="Detected search intent: 'buy', 'compare', 'browse', 'specific'")
    intent_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Intent detection confidence")

    class Config:
        json_schema_extra = {
            "example": {
                "suggestion": "Hero Hoodie",
                "title": "Hero Hoodie",
                "type": "product",
                "count": 1,
                "image": "https://magento-test.softdemonew.info/media/catalog/product/m/h/mh07-blue_main_2.jpg",
                "price": "$59.99",
                "url": "https://magento-test.softdemonew.info/hero-hoodie.html",
                "category": "Hoodies & Sweatshirts",
                "sku": "MH07",
                "id": 158,
                "nlp_enhanced": True,
                "is_corrected": True,
                "corrected_from": "Hro Hoodie",
                "corrected_to": "Hero Hoodie",
                "correction_confidence": 0.9,
                "correction_type": "openai_correction",
                "intent_type": "buy",
                "intent_confidence": 0.8
            }
        }


class AutocompleteMetadata(BaseModel):
    """Metadata about the autocomplete processing"""
    nlp_processing: bool = Field(default=False, description="Whether NLP was used")
    typo_corrections: int = Field(default=0, ge=0, description="Number of typo corrections made")
    intent_detection: bool = Field(default=False, description="Whether intent was detected")
    semantic_search: bool = Field(default=False, description="Whether semantic search was used")
    total_suggestions: int = Field(default=0, ge=0, description="Total number of suggestions returned")

    class Config:
        json_schema_extra = {
            "example": {
                "nlp_processing": True,
                "typo_corrections": 1,
                "intent_detection": True,
                "semantic_search": True,
                "total_suggestions": 5
            }
        }


class AutocompleteResponse(BaseModel):
    """Complete autocomplete response format"""
    suggestions: List[AutocompleteSuggestion] = Field(default_factory=list, description="List of autocomplete suggestions")
    query: str = Field(..., description="Original search query")
    autocomplete_metadata: AutocompleteMetadata = Field(description="Processing metadata")
    error: Optional[str] = Field(default=None, description="Error message if processing failed")

    class Config:
        json_schema_extra = {
            "example": {
                "suggestions": [
                    {
                        "suggestion": "Hero Hoodie",
                        "title": "Hero Hoodie",
                        "type": "product",
                        "count": 1,
                        "image": "https://magento-test.softdemonew.info/media/catalog/product/m/h/mh07-blue_main_2.jpg",
                        "price": "$59.99",
                        "url": "https://magento-test.softdemonew.info/hero-hoodie.html",
                        "category": "Hoodies & Sweatshirts",
                        "sku": "MH07",
                        "id": 158,
                        "nlp_enhanced": True,
                        "is_corrected": True,
                        "corrected_from": "Hro Hoodie",
                        "corrected_to": "Hero Hoodie",
                        "correction_confidence": 0.9,
                        "correction_type": "openai_correction",
                        "intent_type": "buy",
                        "intent_confidence": 0.8
                    }
                ],
                "query": "Hro Hoodie",
                "autocomplete_metadata": {
                    "nlp_processing": True,
                    "typo_corrections": 1,
                    "intent_detection": True,
                    "semantic_search": True,
                    "total_suggestions": 1
                }
            }
        }


class AutocompleteRequest(BaseModel):
    """Autocomplete request schema"""
    q: Optional[str] = Field(None, description="Search query (for GET requests)")
    query: Optional[str] = Field(None, description="Search query (alternative field)")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of suggestions")

    def get_query(self) -> str:
        """Get the query string from either field"""
        return self.q or self.query or ""

    class Config:
        json_schema_extra = {
            "example": {
                "q": "Hro Hoodie",
                "limit": 10
            }
        }


class AutocompleteErrorResponse(BaseModel):
    """Error response for autocomplete API"""
    suggestions: List[AutocompleteSuggestion] = Field(default_factory=list, description="Empty suggestions list")
    query: str = Field(..., description="Original query")
    autocomplete_metadata: AutocompleteMetadata = Field(description="Metadata indicating failure")
    error: str = Field(..., description="Error description")

    class Config:
        json_schema_extra = {
            "example": {
                "suggestions": [],
                "query": "search term",
                "autocomplete_metadata": {
                    "nlp_processing": False,
                    "typo_corrections": 0,
                    "intent_detection": False,
                    "semantic_search": False,
                    "total_suggestions": 0
                },
                "error": "OpenAI API request failed: Invalid API key"
            }
        }
