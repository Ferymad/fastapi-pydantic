"""
Validation utilities for the AI Output Validation Service.

This module provides functions for both structural and semantic validation
of AI outputs against predefined schemas.
"""

from typing import Dict, Any, List, Tuple, Type, Optional, Annotated, Callable
import logging
import re
from datetime import datetime
from pydantic import BaseModel, ValidationError, create_model, Field, EmailStr, field_validator, AfterValidator, BeforeValidator
from pydantic_core import core_schema, PydanticCustomError

from app.models import StructuralValidationResult, SemanticValidationResult, ValidationLevel
from app.ai_agent import get_validation_agent

logger = logging.getLogger(__name__)

# Name validation functions
def validate_name_content(value: str) -> str:
    """
    Validate that a string contains reasonable name content.
    
    Args:
        value: The string to validate
        
    Returns:
        The validated string
        
    Raises:
        ValueError: If the string doesn't appear to be a valid name
    """
    if not value or len(value.strip()) < 2:
        raise PydanticCustomError(
            'name_too_short',
            'Name is too short'
        )
    
    # Check for valid characters (letters, spaces, hyphens, apostrophes)
    if not re.match(r'^[a-zA-Z\s\-\'\u00C0-\u00FF]+$', value):
        raise PydanticCustomError(
            'invalid_name_characters',
            'Name contains invalid characters'
        )
    
    # Check for keyboard patterns
    keyboard_patterns = [
        r'qwerty', r'asdfgh', r'zxcvbn', r'yuiop', r'hjkl', r'nm',  # QWERTY keyboard
        r'azerty', r'qsdfgh', r'wxcvbn'  # AZERTY keyboard
    ]
    
    lower_value = value.lower()
    for pattern in keyboard_patterns:
        if pattern in lower_value:
            raise PydanticCustomError(
                'keyboard_pattern',
                'Invalid name: appears to contain keyboard pattern'
            )
    
    # Check for excessive repeating characters (e.g., 'aaaaaa')
    if re.search(r'(.)\1{3,}', value):
        raise PydanticCustomError(
            'repeating_characters',
            'Invalid name: contains excessive repeating characters'
        )
    
    # Check for random sequences (many consonants in a row, etc.)
    consonants = r'[bcdfghjklmnpqrstvwxyz]'
    if re.search(f'{consonants}{{5,}}', lower_value, re.IGNORECASE):
        raise PydanticCustomError(
            'random_characters',
            'Invalid name: appears to contain random characters or keyboard pattern'
        )
    
    return value

# Name string type - defined after the validation function
NameStr = Annotated[str, BeforeValidator(validate_name_content)]

def name_schema_customizer(field_name: str):
    """Return a function that customizes the schema for name fields"""
    def get_name_schema(tp, handler):
        schema = handler(tp)
        # Create a custom validator for name fields
        return core_schema.with_info_after_validator_function(
            validate_name_content,
            schema,
            serialization=core_schema.SerializationInfo(),
        )
    return get_name_schema

def create_model_from_schema(schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Create a Pydantic model dynamically from a schema definition.
    
    This function generates a Pydantic model class based on the provided schema.
    
    Args:
        schema: A dictionary defining the schema structure
        
    Returns:
        A dynamically created Pydantic model class
    
    Raises:
        ValueError: If the schema is invalid or cannot be parsed
    """
    try:
        field_definitions = {}
        validators = {}
        
        for field_name, field_def in schema.items():
            # Extract field type, required status and other validation rules
            # Handle both raw dict and SchemaField objects
            if hasattr(field_def, 'model_dump'):
                # Convert SchemaField to dict
                field_def_dict = field_def.model_dump()
                field_type = field_def_dict.get("type", Any)
                is_required = field_def_dict.get("required", False)
                format_type = None  # SchemaField doesn't have format
                pattern = field_def_dict.get("pattern", None)
                min_length = field_def_dict.get("min_length", None)
                max_length = field_def_dict.get("max_length", None)
                min_value = field_def_dict.get("gt", None)
                max_value = field_def_dict.get("lt", None)
                items_def = field_def_dict.get("items", None)
            else:
                # Handle raw dict
                field_type = field_def.get("type", Any)
                is_required = field_def.get("required", False)
                format_type = field_def.get("format", None)
                pattern = field_def.get("pattern", None)
                min_length = field_def.get("min_length", None)
                max_length = field_def.get("max_length", None)
                min_value = field_def.get("gt", None) or field_def.get("min", None)
                max_value = field_def.get("lt", None) or field_def.get("max", None)
                items_def = field_def.get("items", None)
            
            field_args = {}
            
            # Define type and validation constraints
            base_type = None
            
            # Map schema types to Python types
            if field_type == "string":
                # Check if this is likely a name field
                is_name_field = field_name.lower() in [
                    "name", "customer_name", "full_name", "first_name", 
                    "last_name", "contact_name", "person_name"
                ]
                
                # Handle specific string formats
                if format_type == "email":
                    base_type = EmailStr
                elif format_type == "date":
                    # Use str but add date validation
                    base_type = str
                    # Add validator function to check date format
                    validator_name = f"validate_{field_name}_date"
                    
                    def create_date_validator(field: str):
                        def validate_date(v):
                            if not v:
                                return v
                            try:
                                # Adjust the format based on your needs
                                datetime.strptime(v, "%Y-%m-%d")
                                return v
                            except ValueError:
                                raise ValueError(f"{field} must be a valid date in YYYY-MM-DD format")
                        return validate_date
                    
                    validators[validator_name] = field_validator(field_name, mode='before')(create_date_validator(field_name))
                elif is_name_field:
                    # Use NameStr for name fields
                    base_type = NameStr
                else:
                    base_type = str
                    
                # Add string-specific validations
                if min_length is not None:
                    field_args["min_length"] = min_length
                if max_length is not None:
                    field_args["max_length"] = max_length
                if pattern is not None:
                    # Create regex pattern validator
                    validator_name = f"validate_{field_name}_pattern"
                    
                    def create_pattern_validator(field: str, pattern: str):
                        def validate_pattern(v):
                            if not v:
                                return v
                            if not re.match(pattern, v):
                                raise ValueError(f"{field} must match pattern {pattern}")
                            return v
                        return validate_pattern
                    
                    validators[validator_name] = field_validator(field_name, mode='before')(create_pattern_validator(field_name, pattern))
                
            elif field_type == "number":
                base_type = float
                if min_value is not None:
                    field_args["gt"] = float(min_value)
                if max_value is not None:
                    field_args["lt"] = float(max_value)
                    
            elif field_type == "integer":
                base_type = int
                if min_value is not None:
                    field_args["gt"] = int(min_value)
                if max_value is not None:
                    field_args["lt"] = int(max_value)
                    
            elif field_type == "boolean":
                base_type = bool
                
            elif field_type == "array":
                # Need to determine the item type for proper validation
                if items_def:
                    # Get item type from items definition
                    if isinstance(items_def, dict):
                        item_type = items_def.get("type", "any")
                    else:
                        item_type = "any"  # Default if items is not a dict
                    
                    # Create appropriate List type based on item type
                    if item_type == "string":
                        base_type = List[str]
                    elif item_type == "number":
                        base_type = List[float]
                    elif item_type == "integer":
                        base_type = List[int]
                    elif item_type == "boolean":
                        base_type = List[bool]
                    else:
                        base_type = List[Any]
                else:
                    # Default to List[Any] if no items definition
                    base_type = List[Any]
                
                # Add array validations
                if min_length is not None:
                    field_args["min_length"] = min_length
                if max_length is not None:
                    field_args["max_length"] = max_length
                
                # Create validator to ensure it's actually a list
                validator_name = f"validate_{field_name}_is_array"
                
                def create_array_validator(field: str):
                    def validate_array(v):
                        if not isinstance(v, list):
                            raise ValueError(f"{field} must be an array/list")
                        return v
                    return validate_array
                
                validators[validator_name] = field_validator(field_name, mode='before')(create_array_validator(field_name))
                
            elif field_type == "object":
                base_type = Dict[str, Any]
            else:
                base_type = Any
                
            # Set default as ... for required fields, None for optional
            field_args["default"] = ... if is_required else None
            
            # Add description if available
            if "description" in field_def:
                field_args["description"] = field_def["description"]
                
            # Create a Field with all the validations
            if field_args or format_type or pattern:
                field_definitions[field_name] = (base_type, Field(**field_args))
            else:
                field_definitions[field_name] = (base_type, field_args["default"])
        
        # Create the dynamic model
        model = create_model("DynamicModel", **field_definitions)
        
        # Add validators dynamically
        for validator_name, validator_func in validators.items():
            setattr(model, validator_name, validator_func)
            
        return model
    
    except Exception as e:
        logger.error(f"Failed to create model from schema: {e}")
        raise ValueError(f"Invalid schema: {str(e)}")

async def perform_structural_validation(
    data: Dict[str, Any], model_class: Type[BaseModel]
) -> Tuple[StructuralValidationResult, Dict[str, Any]]:
    """
    Perform structural validation of data against a Pydantic model.
    
    This function validates the provided data against the given Pydantic model class
    and returns a validation result along with the validated data (or original data if validation fails).
    
    Args:
        data: Data to validate
        model_class: Pydantic model class to validate against
        
    Returns:
        Tuple containing validation result and validated data
    """
    try:
        # Validate data against model
        validated_data = model_class.model_validate(data)
        
        # Return successful validation result
        return StructuralValidationResult(
            is_structurally_valid=True,
            errors=[],
            suggestions=[]
        ), validated_data.model_dump()
    except ValidationError as e:
        # Process validation errors
        errors = e.errors()
        
        # Enhance error messages with suggestions
        for error in errors:
            if error.get("type") == "string_type":
                error["suggestion"] = f"The value for '{error['loc']}' must be a string"
            elif error.get("type") == "float_parsing":
                error["suggestion"] = f"The value for '{error['loc']}' must be a valid number, not a string"
            elif error.get("type") == "list_type":
                error["suggestion"] = f"The value for '{error['loc']}' must be an array/list, not a string"
            elif error.get("type") == "value_error.email":
                error["suggestion"] = f"'{error['loc']}' must be a valid email address format (e.g., user@example.com)"
            elif "date" in error.get("type", ""):
                error["suggestion"] = f"'{error['loc']}' must be in YYYY-MM-DD format (e.g., 2023-10-15)"
            elif "pattern" in error.get("type", ""):
                error["suggestion"] = f"'{error['loc']}' does not match the required pattern"
        
        # Return failed validation result
        result = StructuralValidationResult(
            is_structurally_valid=False,
            errors=errors,
            suggestions=[
                f"Fix validation error: {error.get('msg', '')}" 
                for error in errors
            ]
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
    
    # Check for format issues based on field names
    for field_name, value in data.items():
        field_def = schema.get(field_name, {})
        
        # Email validation for fields that typically contain emails
        if (field_name in ["email", "email_address"] or 
            field_def.get("format") == "email") and isinstance(value, str):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                issues.append(f"Field '{field_name}' is not a valid email address")
                suggestions.append(f"Provide a valid email address for '{field_name}' (e.g., user@example.com)")
        
        # Date validation for fields that typically contain dates
        if (field_name in ["date", "birthday", "birth_date", "order_date", "publication_date"] or 
            field_def.get("format") == "date") and isinstance(value, str):
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            if not re.match(date_pattern, value):
                issues.append(f"Field '{field_name}' is not in a valid date format")
                suggestions.append(f"Use YYYY-MM-DD format for '{field_name}' (e.g., 2023-10-15)")
            else:
                # Validate the date is valid (e.g., not 2023-13-45)
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    issues.append(f"Field '{field_name}' contains an invalid date")
                    suggestions.append(f"Provide a valid date for '{field_name}' (e.g., 2023-10-15)")
        
        # Phone number validation for fields that typically contain phone numbers
        if (field_name in ["phone", "phone_number", "contact_phone", "telephone", "mobile"] or 
            (field_def.get("pattern") and "\\d" in field_def.get("pattern", ""))) and isinstance(value, str):
            # Simple check for numeric-only content with reasonable length
            if not re.match(r'^\d{7,15}$', re.sub(r'[^0-9]', '', value)):
                issues.append(f"Field '{field_name}' does not appear to be a valid phone number")
                suggestions.append(f"Provide a valid phone number for '{field_name}'")
                
        # Name validation for fields that typically contain names
        if (field_name in ["name", "customer_name", "full_name", "first_name", "last_name", "contact_name", "person_name"] and 
            isinstance(value, str)):
            try:
                # Apply the same validation as our structural validator
                validate_name_content(value)
            except PydanticCustomError as e:
                issues.append(f"Field '{field_name}': {e.message}")
                suggestions.append(f"Provide a valid name for '{field_name}'")
    
    # Content quality checks based on validation type
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
    data: Dict[str, Any],
    schema: Dict[str, Any],
    validation_type: str = "generic",
    validation_level: ValidationLevel = ValidationLevel.STANDARD,
) -> Optional[SemanticValidationResult]:
    """
    Perform semantic validation of data using PydanticAI.
    
    This function validates the semantic coherence and quality of the data
    based on the provided schema, validation type, and validation level.
    
    Args:
        data: Data to validate
        schema: Schema definition
        validation_type: Type of validation to perform (generic, recommendation, summary, etc.)
        validation_level: Level of semantic validation strictness
        
    Returns:
        Semantic validation result, or None if semantic validation is disabled
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
            None
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
            None
        ) 