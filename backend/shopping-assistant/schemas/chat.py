"""
AI Product Discovery Suite - Shopping Assistant Chat Schemas

@category    Backend
@package     Shopping Assistant
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    """Message type enumeration"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Chat message schema"""
    message_id: Optional[str] = Field(None, description="Message identifier")
    message_type: MessageType = Field(..., description="Type of message")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional message metadata")


class ChatRequest(BaseModel):
    """Request schema for chat interaction"""
    session_id: str = Field(..., description="Session identifier")
    message: str = Field(..., description="User message")
    user_id: Optional[str] = Field(None, description="User identifier")
    store_id: Optional[str] = Field(None, description="Store identifier")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_123",
                "message": "I'm looking for running shoes under $100",
                "user_id": "user_456",
                "store_id": "store_1",
                "context": {
                    "page": "category",
                    "category_id": "footwear"
                }
            }
        }


class ChatResponse(BaseModel):
    """Response schema for chat interaction"""
    success: bool = Field(..., description="Whether the chat was processed successfully")
    message: str = Field(..., description="Assistant response message")
    session_id: str = Field(..., description="Session identifier")
    suggestions: Optional[List[str]] = Field(default_factory=list, description="Suggested responses or actions")
    products: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Recommended products")
    actions: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Suggested actions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "I found several great running shoes under $100. Here are my top recommendations:",
                "session_id": "session_123",
                "suggestions": [
                    "Show me more options",
                    "Filter by brand",
                    "Find similar products"
                ],
                "products": [
                    {
                        "id": "product_123",
                        "name": "Nike Air Zoom",
                        "price": 89.99,
                        "rating": 4.5
                    }
                ],
                "actions": [
                    {
                        "type": "search",
                        "query": "running shoes under 100",
                        "filters": {"price_max": 100}
                    }
                ]
            }
        }