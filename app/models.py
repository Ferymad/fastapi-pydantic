"""
Data models for the AI Output Validation Service.

This module defines the Pydantic models used for request validation,
response formatting, and internal data structures.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class ValidationLevel(str, Enum):
    """Level of semantic validation to apply."""
    STRUCTURE_ONLY = "structure_only"  # Only perform structural validation
    BASIC = "basic"                    # Basic semantic checks
    STANDARD = "standard"              # Standard level of validation (default)
    STRICT = "strict"                  # Thorough validation with high standards

class StructuralValidationResult(BaseModel):
    """Result of structural validation using Pydantic."""
    is_structurally_valid: bool = Field(
        ..., description="Whether the data passed structural validation"
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of structural validation errors"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Suggestions for fixing issues"
    )

class SemanticValidationResult(BaseModel):
    """Result of semantic validation using PydanticAI."""
    is_semantically_valid: bool = Field(
        ..., description="Whether the data passed semantic validation"
    )
    semantic_score: float = Field(
        ..., description="Confidence score for semantic validation (0.0-1.0)"
    )
    issues: List[str] = Field(
        default_factory=list, description="List of semantic issues found"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Suggestions for fixing issues"
    )

class ValidationRequest(BaseModel):
    """Request body for validation endpoint."""
    data: Dict[str, Any] = Field(
        ..., description="Data to validate"
    )
    schema: Dict[str, Any] = Field(
        ..., description="Schema to validate against"
    )
    type: str = Field(
        "generic", description="Type of validation to perform (generic, recommendation, summary, etc.)"
    )
    level: ValidationLevel = Field(
        ValidationLevel.STANDARD, description="Level of semantic validation strictness"
    )

class ValidationResponse(BaseModel):
    """Response body from validation endpoint."""
    is_valid: bool = Field(
        ..., description="Overall validation result (both structural and semantic if applicable)"
    )
    structural_validation: StructuralValidationResult = Field(
        ..., description="Results of structural validation"
    )
    semantic_validation: Optional[SemanticValidationResult] = Field(
        None, description="Results of semantic validation (if performed)"
    ) 