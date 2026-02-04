from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ExperimentVariantSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    is_control: bool

class ExperimentAssignmentResponse(BaseModel):
    experiment_id: int
    experiment_name: str
    variant_id: int
    variant_name: str
    configuration: Dict[str, Any]

class ExperimentAssignmentsList(BaseModel):
    assignments: List[ExperimentAssignmentResponse]
    user_id: str
    timestamp: datetime

class VariantCreate(BaseModel):
    name: str
    description: Optional[str] = None
    weight: float = 0.5
    configuration: Optional[Dict[str, Any]] = None
    is_control: bool = False

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"
    traffic_allocation: float = 1.0
    variants: List[VariantCreate]

class ExperimentVariantResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    weight: float
    configuration: Optional[Dict[str, Any]] = None
    is_control: bool

class ExperimentResponse(BaseModel):
    id: int
    merchant_id: int
    name: str
    description: Optional[str] = None
    status: str
    traffic_allocation: float
    created_at: datetime
    updated_at: datetime
    variants: List[ExperimentVariantResponse]

class VariantResult(BaseModel):
    variant_id: int
    variant_name: str
    users: int
    conversions: int
    conversion_rate: float
    revenue: float
    avg_revenue_per_user: float
    is_control: bool

class ExperimentResultResponse(BaseModel):
    experiment_id: int
    experiment_name: str
    variants: List[VariantResult]
    statistical_significance: Dict[str, Any]
    winner_variant_id: Optional[int] = None
