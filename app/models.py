"""
Pydantic models for data validation in the AI Output Validation Service.

This module defines the models used for validating different types of AI outputs
as well as standard response models.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Any, Optional, Literal, Annotated
from enum import Enum

# Common validation models
class GenericAIOutput(BaseModel):
    """Base model for generic AI outputs"""
    response_text: str = Field(..., min_length=1)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }

class RecommendationOutput(BaseModel):
    """Model for recommendation type AI outputs"""
    recommendations: List[Dict[str, Any]] = Field(..., min_length=1)
    user_context: Optional[Dict[str, Any]] = None
    
    @field_validator('recommendations')
    @classmethod
    def validate_recommendations(cls, v):
        if not v:
            raise ValueError("Recommendations list cannot be empty")
        for item in v:
            if not isinstance(item, dict):
                raise ValueError("Each recommendation must be a dictionary")
            if "id" not in item:
                raise ValueError("Each recommendation must have an id field")
        return v
    
    model_config = {
        "extra": "forbid"
    }

class SummaryOutput(BaseModel):
    """Model for summary type AI outputs"""
    original_text: str = Field(..., min_length=10)
    summary: str = Field(..., min_length=1)
    key_points: Optional[List[str]] = None
    
    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }

class ClassificationOutput(BaseModel):
    """Model for classification type AI outputs"""
    text: str = Field(..., min_length=1)
    categories: List[str] = Field(..., min_length=1)
    probabilities: Optional[Dict[str, float]] = None
    
    @field_validator('probabilities')
    @classmethod
    def validate_probabilities(cls, v, values):
        if v is None:
            return v
        
        categories = values.data.get('categories', [])
        if not all(category in v for category in categories):
            raise ValueError("All categories must have corresponding probabilities")
        
        for prob in v.values():
            if not 0 <= prob <= 1:
                raise ValueError("Probabilities must be between 0 and 1")
        
        return v
    
    model_config = {
        "extra": "forbid"
    }

# Response models
class ErrorResponse(BaseModel):
    """Standard error response model"""
    status: Literal["invalid"] = "invalid"
    errors: List[Dict[str, Any]]

class SuccessResponse(BaseModel):
    """Standard success response model"""
    status: Literal["valid"] = "valid"
    validated_data: Dict[str, Any]

# Example validation models mapping
example_validation_models = {
    "generic": GenericAIOutput,
    "recommendation": RecommendationOutput,
    "summary": SummaryOutput,
    "classification": ClassificationOutput,
} 