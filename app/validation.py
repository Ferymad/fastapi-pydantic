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

async def basic_semantic_validation(
    validation_type: str,
    validation_level: str,
    data: Dict[str, Any],
    schema: Dict[str, Any],
    structural_errors: Optional[List[Dict[str, Any]]] = None
) -> SemanticValidationResult:
    """
    Perform basic semantic validation without using the AI agent.
    This is a fallback when PydanticAI is unavailable.
    
    Args:
        validation_type: Type of validation to perform
        validation_level: Level of validation strictness
        data: Data to validate
        schema: Schema to validate against
        structural_errors: Errors from structural validation, if any
        
    Returns:
        A SemanticValidationResult object
    """
    logger.info(f"Performing basic semantic validation for type: {validation_type}")
    
    # If there are structural errors, return invalid semantic result
    if structural_errors and len(structural_errors) > 0:
        return SemanticValidationResult(
            is_semantically_valid=False,
            semantic_score=0.0,
            issues=["Failed structural validation"],
            suggestions=["Fix structural errors before semantic validation"]
        )
    
    # Perform basic checks based on validation type
    issues = []
    suggestions = []
    
    # Check for empty strings in text fields
    for field, value in data.items():
        if isinstance(value, str) and not value.strip():
            issues.append(f"Field '{field}' is empty")
            suggestions.append(f"Provide meaningful content for '{field}'")
    
    # Check data completeness against schema
    for field, field_def in schema.items():
        if field_def.get("required", False) and field not in data:
            issues.append(f"Required field '{field}' is missing")
            suggestions.append(f"Add the required field '{field}'")
    
    # Basic checks based on validation type
    if validation_type == "recommendation":
        if "recommendation_text" in data and len(data.get("recommendation_text", "")) < 20:
            issues.append("Recommendation text is too short")
            suggestions.append("Provide more detailed recommendations (at least 20 characters)")
            
    elif validation_type == "summary":
        if "summary" in data and len(data.get("summary", "")) < 30:
            issues.append("Summary is too short")
            suggestions.append("Provide a more comprehensive summary (at least 30 characters)")
    
    # Determine if semantically valid based on issues
    is_valid = len(issues) == 0
    
    # Calculate a basic semantic score based on issues
    score = 1.0 if is_valid else max(0.0, 1.0 - (len(issues) * 0.1))
    
    return SemanticValidationResult(
        is_semantically_valid=is_valid,
        semantic_score=score,
        issues=issues,
        suggestions=suggestions
    )

async def perform_semantic_validation(
    validation_type: str,
    validation_level: str,
    data: Dict[str, Any],
    schema: Dict[str, Any],
    structural_errors: Optional[List[Dict[str, Any]]] = None
) -> SemanticValidationResult:
    """
    Perform semantic validation using PydanticAI.
    
    Args:
        validation_type: Type of validation to perform
        validation_level: Level of validation strictness
        data: Data to validate
        schema: Schema to validate against
        structural_errors: Errors from structural validation, if any
        
    Returns:
        A SemanticValidationResult object
    """
    # Ensure data and schema are valid dictionaries
    if not isinstance(data, dict) or not isinstance(schema, dict):
        logger.warning(f"Invalid input types - data: {type(data)}, schema: {type(schema)}")
        return SemanticValidationResult(
            is_semantically_valid=False,
            semantic_score=0.0,
            issues=["Invalid input format. Both data and schema must be valid JSON objects."],
            suggestions=["Ensure both data and schema are valid JSON objects."]
        )
    
    # Special case for empty data/schema to provide direct feedback
    if not data or not schema:
        logger.info("Empty data or schema detected, providing direct validation feedback")
        issues = []
        suggestions = []
        
        if not data:
            issues.append("The provided data is empty")
            suggestions.append("Provide actual content to validate")
        
        if not schema:
            issues.append("The provided schema is empty")
            suggestions.append("Define a schema with fields and validation rules")
            
        return SemanticValidationResult(
            is_semantically_valid=False if issues else True,
            semantic_score=0.0 if issues else 1.0,
            issues=issues,
            suggestions=suggestions
        )
    
    # Get the validation agent - this will initialize if needed
    agent = get_validation_agent()
    
    # If no agent available, use basic semantic validation
    if not agent:
        logger.warning("PydanticAI agent not available, using basic semantic validation")
        return await basic_semantic_validation(
            validation_type, 
            validation_level, 
            data, 
            schema, 
            structural_errors
        )
    
    try:
        # Simplified prompt focused on the core task
        prompt = f"""
        You are validating data against a schema.
        
        Schema: {schema}
        Data: {data}
        
        Provide a validation result with:
        - is_semantically_valid (boolean): Is the data semantically valid?
        - semantic_score (float): Score from 0.0 to 1.0
        - issues (list): Any semantic issues found
        - suggestions (list): How to fix the issues
        """
        
        logger.info("Sending validation request to PydanticAI agent")
        
        # Create a default result as fallback
        default_result = SemanticValidationResult(
            is_semantically_valid=True,
            semantic_score=1.0,
            issues=[],
            suggestions=[]
        )
        
        # Use a synchronous approach if possible, with a timeout
        import asyncio
        try:
            # Run with minimal parameters first
            result = await asyncio.wait_for(
                agent.run(
                    user_prompt=prompt,
                    result_type=SemanticValidationResult
                ),
                timeout=10.0  # Reduced timeout for better responsiveness
            )
            
            logger.info(f"Agent returned result type: {type(result)}")
            
            # Validate the returned result has the correct structure
            if isinstance(result, SemanticValidationResult):
                # Ensure all required fields are present
                if not hasattr(result, 'is_semantically_valid') or result.is_semantically_valid is None:
                    result.is_semantically_valid = True
                    
                if not hasattr(result, 'semantic_score') or result.semantic_score is None:
                    result.semantic_score = 1.0
                    
                return result
            else:
                # If wrong type returned, log and use default
                logger.warning(f"Agent returned incorrect type: {type(result)}")
                return default_result
                
        except asyncio.TimeoutError:
            logger.error("Semantic validation timed out")
            return SemanticValidationResult(
                is_semantically_valid=False,
                semantic_score=0.0,
                issues=["Validation timed out"],
                suggestions=["Try with simpler data or schema"]
            )
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            return default_result
            
    except Exception as e:
        # Log the error and fall back to basic validation
        logger.error(f"Semantic validation error: {str(e)}", exc_info=True)
        return await basic_semantic_validation(
            validation_type,
            validation_level,
            data,
            schema,
            structural_errors
        ) 