"""
OpenAI NLP Schemas for AI Product Discovery Suite
Schemas for OpenAI-powered natural language processing

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryEntity(BaseModel):
    """Extracted entity from search query"""
    text: str = Field(..., description="Entity text")
    type: str = Field(..., description="Entity type: 'product', 'brand', 'color', 'size', 'material'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "hoodie",
                "type": "product",
                "confidence": 0.95
            }
        }


class SearchIntent(BaseModel):
    """Detected search intent from user query"""
    intent_type: str = Field(..., description="Intent type: 'buy', 'compare', 'browse', 'specific', 'question'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Intent detection confidence")
    entities: List[QueryEntity] = Field(default_factory=list, description="Extracted entities")
    keywords: List[str] = Field(default_factory=list, description="Key terms from query")
    original_query: str = Field(..., description="Original user query")
    processed_query: str = Field(..., description="Cleaned and processed query")
    corrections: List[str] = Field(default_factory=list, description="Applied corrections")

    class Config:
        json_schema_extra = {
            "example": {
                "intent_type": "buy",
                "confidence": 0.85,
                "entities": [
                    {
                        "text": "hoodie",
                        "type": "product",
                        "confidence": 0.95
                    },
                    {
                        "text": "comfortable",
                        "type": "attribute",
                        "confidence": 0.8
                    }
                ],
                "keywords": ["comfortable", "hoodie"],
                "original_query": "I want to buy a comfortable hoodie",
                "processed_query": "comfortable hoodie",
                "corrections": []
            }
        }


class QueryCorrection(BaseModel):
    """Query correction applied by OpenAI"""
    original: str = Field(..., description="Original text with typo")
    corrected: str = Field(..., description="Corrected text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Correction confidence")
    correction_type: str = Field(..., description="Type of correction applied")

    class Config:
        json_schema_extra = {
            "example": {
                "original": "Hro Hoodie",
                "corrected": "Hero Hoodie",
                "confidence": 0.9,
                "correction_type": "openai_correction"
            }
        }


class OpenAIProcessingResult(BaseModel):
    """Result of OpenAI query processing"""
    intent: SearchIntent = Field(..., description="Detected search intent")
    corrections: List[QueryCorrection] = Field(default_factory=list, description="Applied corrections")
    processing_time: float = Field(..., ge=0.0, description="Processing time in seconds")
    success: bool = Field(..., description="Whether processing was successful")
    error: Optional[str] = Field(default=None, description="Error message if processing failed")

    class Config:
        json_schema_extra = {
            "example": {
                "intent": {
                    "intent_type": "buy",
                    "confidence": 0.85,
                    "entities": [
                        {
                            "text": "hoodie",
                            "type": "product",
                            "confidence": 0.95
                        }
                    ],
                    "keywords": ["comfortable", "hoodie"],
                    "original_query": "I want to buy a comfortable hoodie",
                    "processed_query": "comfortable hoodie",
                    "corrections": []
                },
                "corrections": [],
                "processing_time": 0.8,
                "success": True
            }
        }


class OpenAIAPIRequest(BaseModel):
    """Request to OpenAI API"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query to process")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "I want to buy a comfortable hoodie",
                "context": {
                    "user_preferences": ["casual wear"],
                    "session_id": "sess_123"
                }
            }
        }


class OpenAIAPIResponse(BaseModel):
    """Response from OpenAI API"""
    corrected_query: str = Field(..., description="Query with typos corrected")
    product_keywords: List[str] = Field(default_factory=list, description="Extracted product keywords")
    search_intent: str = Field(..., description="Detected search intent")
    intent_confidence: float = Field(..., ge=0.0, le=1.0, description="Intent confidence")
    typo_corrections: List[Dict[str, Any]] = Field(default_factory=list, description="Typo corrections made")
    semantic_keywords: List[str] = Field(default_factory=list, description="Related semantic terms")
    explanation: str = Field(..., description="Explanation of what user is looking for")

    class Config:
        json_schema_extra = {
            "example": {
                "corrected_query": "comfortable hoodie",
                "product_keywords": ["comfortable", "hoodie"],
                "search_intent": "buy",
                "intent_confidence": 0.8,
                "typo_corrections": [],
                "semantic_keywords": ["cozy", "warm", "soft"],
                "explanation": "User wants to purchase a comfortable hoodie"
            }
        }


class OpenAIConfig(BaseModel):
    """OpenAI API configuration"""
    api_key: str = Field(..., description="OpenAI API key")
    model: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=500, ge=1, le=4000, description="Maximum tokens in response")
    timeout: float = Field(default=10.0, ge=1.0, le=60.0, description="Request timeout in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "api_key": "sk-...",
                "model": "gpt-3.5-turbo",
                "temperature": 0.3,
                "max_tokens": 500,
                "timeout": 10.0
            }
        }
