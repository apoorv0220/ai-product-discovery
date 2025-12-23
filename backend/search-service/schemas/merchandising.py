"""
Merchandising Rules API Schemas
Pydantic models for rule management endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime


class MerchandisingRuleBase(BaseModel):
    """Base schema for merchandising rules"""
    name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    description: Optional[str] = Field(None, max_length=1000, description="Rule description")
    rule_type: Literal["boost", "pin", "hide"] = Field(..., description="Type of rule")
    priority: int = Field(default=500, ge=1, le=1000, description="Rule priority (1-1000, higher = more important)")
    is_active: bool = Field(default=True, description="Whether the rule is active")
    conditions: Dict[str, Any] = Field(..., description="Rule conditions (JSON)")
    action_config: Dict[str, Any] = Field(..., description="Action configuration (JSON)")
    
    @validator('conditions')
    def validate_conditions(cls, v):
        """Validate condition structure"""
        if not isinstance(v, dict):
            raise ValueError("conditions must be a dictionary")
        
        condition_type = v.get("type")
        if condition_type not in ["query_match", "category", "product_id"]:
            raise ValueError(
                f"Invalid condition type: {condition_type}. "
                f"Must be one of: query_match, category, product_id"
            )
        
        operator = v.get("operator")
        if not operator:
            raise ValueError("conditions must have an 'operator' field")
        
        value = v.get("value")
        if value is None:
            raise ValueError("conditions must have a 'value' field")
        
        # Validate operator based on type
        if condition_type == "query_match":
            if operator not in ["exact", "contains"]:
                raise ValueError(f"query_match operator must be 'exact' or 'contains', got: {operator}")
            if not isinstance(value, str):
                raise ValueError("query_match value must be a string")
        
        elif condition_type == "category":
            if operator not in ["equals", "in"]:
                raise ValueError(f"category operator must be 'equals' or 'in', got: {operator}")
            if operator == "equals" and not isinstance(value, str):
                raise ValueError("category 'equals' value must be a string")
            if operator == "in" and not isinstance(value, list):
                raise ValueError("category 'in' value must be a list")
        
        elif condition_type == "product_id":
            if operator not in ["equals", "in"]:
                raise ValueError(f"product_id operator must be 'equals' or 'in', got: {operator}")
            if operator == "equals" and not isinstance(value, (str, int)):
                raise ValueError("product_id 'equals' value must be a string or integer")
            if operator == "in" and not isinstance(value, list):
                raise ValueError("product_id 'in' value must be a list")
        
        return v
    
    @validator('action_config')
    def validate_action_config(cls, v, values):
        """Validate action configuration based on rule type"""
        if not isinstance(v, dict):
            raise ValueError("action_config must be a dictionary")
        
        rule_type = values.get("rule_type")
        
        if rule_type == "boost":
            boost_factor = v.get("boost_factor")
            if boost_factor is None:
                raise ValueError("boost rule must have 'boost_factor' in action_config")
            if not isinstance(boost_factor, (int, float)):
                raise ValueError("boost_factor must be a number")
            if not (0.1 <= boost_factor <= 10.0):
                raise ValueError("boost_factor must be between 0.1 and 10.0")
        
        elif rule_type == "pin":
            if "position" not in v:
                raise ValueError("pin rule must have 'position' in action_config")
            if "product_id" not in v:
                raise ValueError("pin rule must have 'product_id' in action_config")
            position = v.get("position")
            if not isinstance(position, int) or position < 1:
                raise ValueError("position must be a positive integer (1-based)")
            product_id = v.get("product_id")
            if not product_id:
                raise ValueError("product_id cannot be empty")
        
        elif rule_type == "hide":
            # Hide rules don't need action_config, but we allow empty dict
            pass
        
        return v


class MerchandisingRuleCreate(MerchandisingRuleBase):
    """Schema for creating a new rule"""
    pass


class MerchandisingRuleUpdate(BaseModel):
    """Schema for updating an existing rule"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    rule_type: Optional[Literal["boost", "pin", "hide"]] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None
    conditions: Optional[Dict[str, Any]] = None
    action_config: Optional[Dict[str, Any]] = None


class MerchandisingRuleResponse(MerchandisingRuleBase):
    """Schema for rule response"""
    id: int
    merchant_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RulePreviewRequest(BaseModel):
    """Schema for rule preview request"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query to test")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results to return")


class RulePreviewResponse(BaseModel):
    """Schema for rule preview response"""
    rule_id: int
    rule_name: str
    query: str
    would_match: bool
    matched_products: List[Dict[str, Any]] = Field(default_factory=list, description="Products that would be affected")
    message: str = Field(..., description="Preview result message")


