"""
Schema repository models for storing and managing validation schemas.

This module defines the Pydantic models used for schema storage, retrieval,
and management in the repository.
"""

from typing import Any, Dict, List, Optional, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class SchemaField(BaseModel):
    """Definition of a field in a validation schema."""
    type: str
    required: bool = False
    description: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum: Optional[List[Any]] = None
    gt: Optional[float] = None
    lt: Optional[float] = None
    items: Optional[Dict[str, Any]] = None
    
    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "type": "string",
                    "required": True,
                    "description": "Customer's full name",
                    "min_length": 2,
                    "max_length": 100
                }
            ]
        }
    }

class SchemaCreate(BaseModel):
    """Model for creating a new schema."""
    name: str = Field(..., min_length=3, pattern=r"^[a-z0-9_]+$")
    description: str
    schema: Dict[str, SchemaField]
    validation_level: Literal["structure_only", "basic", "standard", "strict"] = "standard"
    example: Optional[Dict[str, Any]] = None
    
    @field_validator('name')
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        if not all(c.islower() or c.isdigit() or c == '_' for c in v):
            raise ValueError('Schema name must contain only lowercase letters, numbers, and underscores')
        return v
    
    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "name": "customer_order",
                    "description": "Schema for validating customer order data",
                    "schema": {
                        "customer_name": {
                            "type": "string",
                            "required": True,
                            "min_length": 2
                        },
                        "order_total": {
                            "type": "number",
                            "required": True,
                            "gt": 0
                        }
                    },
                    "validation_level": "standard",
                    "example": {
                        "customer_name": "John Doe",
                        "order_total": 99.99
                    }
                }
            ]
        }
    }

class SchemaMetadata(BaseModel):
    """Metadata about a schema stored in the repository."""
    name: str
    description: str
    current_version: str
    created_at: datetime
    updated_at: datetime
    versions: List[str]
    
    model_config = {
        "extra": "forbid"
    }

class SchemaDefinition(BaseModel):
    """Schema definition stored in the repository."""
    name: str
    description: str
    version: str
    created_at: datetime
    updated_at: datetime
    schema: Dict[str, SchemaField]
    validation_level: Literal["structure_only", "basic", "standard", "strict"]
    example: Optional[Dict[str, Any]] = None
    version_notes: Optional[str] = None
    
    model_config = {
        "extra": "forbid"
    }

class SchemaUpdate(BaseModel):
    """Model for updating an existing schema."""
    description: Optional[str] = None
    schema: Optional[Dict[str, SchemaField]] = None
    validation_level: Optional[Literal["structure_only", "basic", "standard", "strict"]] = None
    example: Optional[Dict[str, Any]] = None
    version_notes: Optional[str] = None
    
    model_config = {
        "extra": "forbid"
    }

class SchemaVersionInfo(BaseModel):
    """Information about a schema version."""
    version: str
    created_at: datetime
    version_notes: Optional[str] = None
    url: str
    
    model_config = {
        "extra": "forbid"
    }

class SchemaVersionHistory(BaseModel):
    """History of schema versions."""
    name: str
    current_version: str
    versions: List[SchemaVersionInfo]
    
    model_config = {
        "extra": "forbid"
    }

class SchemaListItem(BaseModel):
    """Summary information about a schema in the repository."""
    name: str
    description: str
    current_version: str
    created_at: datetime
    updated_at: datetime
    url: str
    
    model_config = {
        "extra": "forbid"
    }

class SchemaList(BaseModel):
    """List of schemas in the repository."""
    schemas: List[SchemaListItem]
    
    model_config = {
        "extra": "forbid"
    }

class SchemaResponse(BaseModel):
    """Response model for schema operations."""
    name: str
    description: str
    version: str
    created_at: datetime
    updated_at: datetime
    schema: Dict[str, SchemaField]
    validation_level: Literal["structure_only", "basic", "standard", "strict"]
    example: Optional[Dict[str, Any]] = None
    usage_url: str
    
    model_config = {
        "extra": "forbid"
    }

class SchemaDeleteResponse(BaseModel):
    """Response for schema deletion operation."""
    name: str
    deleted: bool
    message: str
    
    model_config = {
        "extra": "forbid"
    }
