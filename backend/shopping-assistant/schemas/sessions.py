"""
AI Product Discovery Suite - Shopping Assistant Session Schemas

@category    Backend
@package     Shopping Assistant
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from .chat import ChatMessage


class SessionData(BaseModel):
    """Session data schema"""
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    store_id: Optional[str] = Field(None, description="Store identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation timestamp")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    message_count: int = Field(0, description="Number of messages in session")
    status: str = Field("active", description="Session status")
    context: Dict[str, Any] = Field(default_factory=dict, description="Session context")
    messages: List[ChatMessage] = Field(default_factory=list, description="Session messages")


class SessionRequest(BaseModel):
    """Request schema for session operations"""
    user_id: Optional[str] = Field(None, description="User identifier")
    store_id: Optional[str] = Field(None, description="Store identifier")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Initial session context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_456",
                "store_id": "store_1",
                "context": {
                    "page": "homepage",
                    "user_preferences": {
                        "categories": ["electronics", "clothing"]
                    }
                }
            }
        }


class SessionResponse(BaseModel):
    """Response schema for session operations"""
    success: bool = Field(..., description="Whether the operation was successful")
    session: Optional[SessionData] = Field(None, description="Session data")
    message: Optional[str] = Field(None, description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session": {
                    "session_id": "session_123",
                    "user_id": "user_456",
                    "store_id": "store_1",
                    "created_at": "2024-01-30T10:00:00Z",
                    "last_activity": "2024-01-30T10:15:00Z",
                    "message_count": 3,
                    "status": "active",
                    "context": {
                        "page": "homepage"
                    },
                    "messages": []
                },
                "message": "Session created successfully"
            }
        }