"""
Validation utilities for the AI Output Validation Service.

This module provides functions for both structural and semantic validation
of AI outputs against predefined schemas.
"""

from typing import Dict, Any, List, Tuple, Type, Optional
import logging
from pydantic import BaseModel, ValidationError, create_model

from app.models import StructuralValidationResult, SemanticValidationResult
from app.ai_agent import get_validation_agent

logger = logging.getLogger(__name__)

def create_model_from_schema(schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Create a dynamic Pydantic model from a schema definition.
    
    Args:
        schema: A dictionary defining the schema structure
        
    Returns:
        A dynamically created Pydantic model class
    
    Raises:
        ValueError: If the schema is invalid or cannot be parsed
    """
    try:
        field_definitions = {}
        
        for field_name, field_def in schema.items():
            # Extract field type and required status
            field_type = field_def.get("type", Any)
            is_required = field_def.get("required", False)
            
            # Map schema types to Python types
            if field_type == "string":
                py_type = str
            elif field_type == "number":
                py_type = float
            elif field_type == "integer":
                py_type = int
            elif field_type == "boolean":
                py_type = bool
            elif field_type == "array":
                py_type = List[Any]
            elif field_type == "object":
                py_type = Dict[str, Any]
            else:
                py_type = Any
                
            # Set default as ... for required fields, None for optional
            default = ... if is_required else None
            field_definitions[field_name] = (py_type, default)
        
        # Create the dynamic model
        return create_model("DynamicModel", **field_definitions)
    
    except Exception as e:
        logger.error(f"Failed to create model from schema: {e}")
        raise ValueError(f"Invalid schema: {str(e)}")

async def perform_structural_validation(
    model_class: Type[BaseModel],
    data: Dict[str, Any]
) -> Tuple[StructuralValidationResult, Dict[str, Any]]:
    """
    Perform structural validation using a Pydantic model.
    
    Args:
        model_class: The Pydantic model class to validate against
        data: The data to validate
        
    Returns:
        A tuple containing the validation result and the validated data (if valid)
    """
    try:
        # Validate data against the model
        validated_instance = model_class(**data)
        validated_data = validated_instance.model_dump()
        
        # Return successful validation result
        result = StructuralValidationResult(
            is_structurally_valid=True,
            errors=[]
        )
        return result, validated_data
        
    except ValidationError as e:
        # Process validation errors
        error_details = []
        for error in e.errors():
            error_details.append({
                "loc": ".".join(str(loc) for loc in error["loc"]),
                "type": error["type"],
                "msg": error["msg"]
            })
        
        # Return validation error result
        result = StructuralValidationResult(
            is_structurally_valid=False,
            errors=error_details
        )
        return result, data

async def perform_semantic_validation(
    validation_type: str,
    validation_level: str,
    data: Dict[str, Any],
    schema: Dict[str, Any],
    structural_errors: Optional[List[Dict[str, Any]]] = None
) -> SemanticValidationResult:
    """
    Perform semantic validation using the AI agent.
    
    Args:
        validation_type: The type of validation to perform
        validation_level: The level of validation strictness
        data: The data to validate
        schema: The schema used for validation
        structural_errors: List of structural validation errors (if any)
        
    Returns:
        A SemanticValidationResult with validation findings
    """
    # Get validation agent (initialized on app startup)
    validation_agent = get_validation_agent()
    
    if not validation_agent:
        logger.warning("Semantic validation requested but validation agent not initialized")
        return SemanticValidationResult(
            is_semantically_valid=False,
            semantic_score=0.0,
            issues=["Validation agent not initialized. Semantic validation is disabled."],
            suggestions=["Check OpenAI API key configuration."]
        )
    
    # Construct a prompt for the validation
    prompt = f"""
    Validate the following data against the provided schema for {validation_type} validation at {validation_level} level.
    
    SCHEMA:
    {schema}
    
    DATA:
    {data}
    
    Validation Instructions:
    1. Check if the data aligns with the schema's intent and purpose
    2. Validate that field values make logical sense in context
    3. Identify inconsistencies or contradictions in the data
    4. Apply {validation_level} level of scrutiny
    """
    
    try:
        # Use the AI agent for validation
        result = await validation_agent.run(
            user_prompt=prompt,
            result_type=SemanticValidationResult,
        )
        return result
    except Exception as e:
        # Fallback in case of any errors with the agent
        logger.error(f"Error during semantic validation: {e}")
        return SemanticValidationResult(
            is_semantically_valid=False,
            semantic_score=0.0,
            issues=[f"Error during semantic validation: {str(e)}"],
            suggestions=["Try a different validation level or check the API configuration."]
        ) 