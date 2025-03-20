"""
PydanticAI integration for enhanced validation with semantic checks.

This module provides AI-powered validation that goes beyond structural checks
to evaluate semantic validity, content coherence, and provide suggestions
for fixing validation issues.
"""

from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum
import os
import logging

from app.config import get_settings

# Get settings
settings = get_settings()

# Global agent instance
_validation_agent = None

# Logger
logger = logging.getLogger(__name__)

class ValidationLevel(str, Enum):
    """Validation levels for semantic checks"""
    BASIC = "basic"       # Basic structure and content checks
    STANDARD = "standard" # More thorough semantic validation
    STRICT = "strict"     # Rigorous validation with comprehensive checks

class SemanticValidationResult(BaseModel):
    """Results of semantic validation"""
    is_semantically_valid: bool = Field(
        ..., 
        description="Whether the content is semantically valid"
    )
    semantic_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score for semantic validity"
    )
    issues: List[str] = Field(
        default_factory=list, 
        description="List of semantic issues found"
    )
    suggestions: List[str] = Field(
        default_factory=list, 
        description="Suggestions to fix semantic issues"
    )

class EnhancedValidationResponse(BaseModel):
    """Complete enhanced validation response"""
    standard_validation: Dict[str, Any] = Field(
        ..., 
        description="Results from standard Pydantic validation"
    )
    semantic_validation: Optional[SemanticValidationResult] = Field(
        None, 
        description="Results from semantic validation"
    )
    processing_time_ms: float = Field(
        ..., 
        description="Processing time in milliseconds"
    )

def initialize_validation_agent():
    """
    Initialize the validation agent with PydanticAI.
    
    This should be called at application startup.
    """
    global _validation_agent
    
    try:
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set. Semantic validation will be disabled.")
            return
        
        try:
            # Import PydanticAI
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                # First attempt: Try without api_key parameter (newer versions)
                _validation_agent = Agent()
                logger.info("PydanticAI Agent initialized successfully without api_key parameter")
            except TypeError as e:
                # Second attempt: Try with api_key parameter (older versions)
                logger.info("Trying to initialize Agent with api_key parameter")
                _validation_agent = Agent(api_key=settings.OPENAI_API_KEY)
                logger.info("PydanticAI Agent initialized successfully with api_key parameter")
            
            logger.info("Validation agent initialized successfully")
        except ImportError:
            logger.error("pydantic_ai package not installed. Semantic validation will be disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize validation agent: {e}")
    except Exception as e:
        logger.error(f"Error initializing validation agent: {e}")

def get_validation_agent():
    """
    Get the singleton validation agent instance.
    
    Returns:
        The initialized validation agent or None if not initialized
    """
    return _validation_agent

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
        structural_errors: List of structural validation errors if any
        
    Returns:
        Semantic validation result
    """
    # Get the validation agent
    validation_agent = get_validation_agent()
    
    if not validation_agent:
        return SemanticValidationResult(
            is_semantically_valid=False,
            semantic_score=0.0,
            issues=["Validation agent not initialized. Semantic validation is disabled."],
            suggestions=["Check OpenAI API key configuration."]
        )
    
    # Construct prompt for validation
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
    
    # Run the agent with updated parameters (removed context)
    try:
        logger = logging.getLogger(__name__)
        
        try:
            # First attempt: Just the user_prompt and result_type
            result = await validation_agent.run(
                user_prompt=prompt,
                result_type=SemanticValidationResult,
            )
            logger.info("Agent.run executed successfully with basic parameters")
        except TypeError as e:
            if "context" in str(e):
                # Second attempt: Try with context parameter if that's the error
                logger.info("Trying Agent.run with context parameter")
                context = {
                    "validation_type": validation_type,
                    "validation_level": validation_level,
                    "structural_errors": structural_errors or [],
                    "data": data,
                }
                result = await validation_agent.run(
                    user_prompt=prompt,
                    context=context,
                    result_type=SemanticValidationResult,
                )
                logger.info("Agent.run executed successfully with context parameter")
            else:
                # If it's some other TypeError, re-raise
                raise
        
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

async def enhance_validation(
    data: Dict[str, Any],
    validation_type: str,
    validation_level: ValidationLevel = ValidationLevel.STANDARD,
    standard_validation_result: Dict[str, Any] = None,
    structural_errors: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Enhance validation with semantic checks.
    
    Args:
        data: The AI output data to validate
        validation_type: Type of validation to perform
        validation_level: Level of semantic validation to perform
        standard_validation_result: Results from standard Pydantic validation
        structural_errors: Any errors from standard validation
        
    Returns:
        Enhanced validation results with semantic checks
    """
    import time
    start_time = time.time()
    
    # Check if OPENAI_API_KEY is configured
    if not settings.OPENAI_API_KEY:
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        return {
            "standard_validation": standard_validation_result,
            "semantic_validation": {
                "is_semantically_valid": False,
                "semantic_score": 0.0,
                "issues": ["OpenAI API key not configured. Semantic validation is disabled."],
                "suggestions": ["Configure OPENAI_API_KEY environment variable to enable semantic validation."]
            },
            "processing_time_ms": processing_time,
        }
    
    # Only perform semantic validation if structural validation passed
    # or if specifically requested for failed validation
    semantic_result = None
    if standard_validation_result.get("status") == "valid" or validation_level == ValidationLevel.STRICT:
        semantic_result = await perform_semantic_validation(
            validation_type=validation_type,
            validation_level=validation_level,
            data=data,
            schema=standard_validation_result.get("schema", {}),
            structural_errors=structural_errors,
        )
    
    processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    # Create the enhanced validation response
    return {
        "standard_validation": standard_validation_result,
        "semantic_validation": semantic_result.model_dump() if semantic_result else None,
        "processing_time_ms": processing_time,
    } 