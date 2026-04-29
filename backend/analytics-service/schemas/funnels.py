from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class FunnelStepCreate(BaseModel):
    name: str
    event_type: str
    properties_filter: Optional[Dict[str, Any]] = None

class FunnelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    steps: List[FunnelStepCreate]

class FunnelStepResponse(BaseModel):
    id: int
    name: str
    event_type: str
    step_order: int
    properties_filter: Optional[Dict[str, Any]] = None

class FunnelResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    steps: List[FunnelStepResponse]
    created_at: datetime
    updated_at: datetime

class FunnelStepAnalytics(BaseModel):
    step_order: int
    step_name: str
    event_type: str
    count: int
    drop_off: int
    step_conversion: float
    total_conversion: float

class FunnelAnalyticsResponse(BaseModel):
    funnel_id: int
    funnel_name: str
    steps: List[FunnelStepAnalytics]
    overall_conversion: float
    period: Dict[str, str]
