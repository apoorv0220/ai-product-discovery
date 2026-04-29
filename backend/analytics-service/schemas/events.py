"""
AI Product Discovery Suite - Analytics Events Schemas

@category    Backend
@package     Analytics Service
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class EventData(BaseModel):
    """Event data schema"""
    event_type: str = Field(..., description="Type of event")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    product_id: Optional[str] = Field(None, description="Product identifier")
    category_id: Optional[str] = Field(None, description="Category identifier")
    query: Optional[str] = Field(None, description="Search query")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional event properties")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Event timestamp")


class EventRequest(BaseModel):
    """Request schema for event tracking"""
    events: List[EventData] = Field(..., description="List of events to track")
    store_id: Optional[str] = Field(None, description="Store identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "event_type": "search",
                        "user_id": "user_123",
                        "session_id": "session_456",
                        "query": "running shoes",
                        "properties": {
                            "results_count": 25,
                            "page": 1
                        }
                    }
                ],
                "store_id": "store_1"
            }
        }


class EventResponse(BaseModel):
    """Response schema for event tracking"""
    success: bool = Field(..., description="Whether the events were processed successfully")
    processed_count: int = Field(..., description="Number of events processed")
    errors: List[str] = Field(default_factory=list, description="List of errors if any")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "processed_count": 1,
                "errors": []
            }
        }