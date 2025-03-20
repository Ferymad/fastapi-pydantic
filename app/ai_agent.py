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

from app.config import get_settings

# Get settings
settings = get_settings()

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

# Initialize PydanticAI agent - will only work if OPENAI_API_KEY is provided
validation_agent = None
if settings.OPENAI_API_KEY:
    validation_agent = Agent(
        'openai:gpt-4o',  
        api_key=settings.OPENAI_API_KEY,
        system_prompt=(
            'You are a validation assistant specialized in verifying AI outputs. '
            'Your task is to analyze AI-generated content and determine if it meets both structural '
            'and semantic requirements. You evaluate coherence, relevance, factual accuracy, '
            'and alignment with the expected output type. '
            'Provide detailed feedback on validation failures and specific suggestions for improvements.'
        ),
        instrument=True,  # Enable Logfire monitoring
    )

async def perform_semantic_validation(
    data: Dict[str, Any],
    validation_type: str,
    validation_level: ValidationLevel = ValidationLevel.STANDARD,
    structural_errors: Optional[List[Dict[str, Any]]] = None
) -> SemanticValidationResult:
    """
    Perform semantic validation on AI output data.
    
    Args:
        data: The AI output data to validate
        validation_type: Type of validation (generic, recommendation, etc.)
        validation_level: Level of semantic validation to perform
        structural_errors: Any errors from standard structural validation
        
    Returns:
        SemanticValidationResult with validation details
    """
    # Check if validation agent is initialized
    if validation_agent is None:
        return SemanticValidationResult(
            is_semantically_valid=False,
            semantic_score=0.0,
            issues=["OpenAI API key not configured. Semantic validation is disabled."],
            suggestions=["Configure OPENAI_API_KEY environment variable to enable semantic validation."]
        )
    
    # Create context for the agent
    context = {
        "validation_type": validation_type,
        "validation_level": validation_level,
        "structural_errors": structural_errors or [],
        "data": data,
    }
    
    # Create prompt based on validation type
    validation_prompts = {
        "generic": (
            f"Validate this generic AI output with {validation_level} strictness:\n"
            f"{data}\n\n"
            f"Check if the response is coherent, well-structured, and appropriate."
        ),
        "recommendation": (
            f"Validate this recommendation-type AI output with {validation_level} strictness:\n"
            f"{data}\n\n"
            f"Check if the recommendations are relevant, specific, and actionable."
        ),
        "summary": (
            f"Validate this summary-type AI output with {validation_level} strictness:\n"
            f"{data}\n\n"
            f"Check if the summary accurately captures the key points of the original text."
        ),
        "classification": (
            f"Validate this classification-type AI output with {validation_level} strictness:\n"
            f"{data}\n\n"
            f"Check if the classification is accurate, well-justified, and appropriate."
        ),
    }
    
    prompt = validation_prompts.get(
        validation_type, 
        f"Validate this {validation_type} AI output with {validation_level} strictness:\n{data}"
    )
    
    if structural_errors:
        prompt += (
            f"\n\nNote that structural validation found these errors:\n"
            f"{structural_errors}\n\n"
            f"Consider these when providing semantic validation."
        )
    
    # Run the agent
    result = await validation_agent.run(
        user_prompt=prompt,
        context=context,
        result_type=SemanticValidationResult,
    )
    
    return result

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
            data=data,
            validation_type=validation_type,
            validation_level=validation_level,
            structural_errors=structural_errors,
        )
    
    processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    # Create the enhanced validation response
    return {
        "standard_validation": standard_validation_result,
        "semantic_validation": semantic_result.model_dump() if semantic_result else None,
        "processing_time_ms": processing_time,
    } 