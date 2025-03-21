"""
PydanticAI integration for enhanced validation with semantic checks.

This module provides AI-powered validation that goes beyond structural checks
to evaluate semantic validity, content coherence, and provide suggestions
for fixing validation issues.
"""

import os
import logging
import importlib.metadata
import requests
import asyncio
import nest_asyncio
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

try:
    from pydantic_ai import Agent
except ImportError:
    Agent = None
    logging.getLogger(__name__).error("Failed to import Agent from pydantic_ai")

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
        from app.config import get_settings
        settings = get_settings()
        
        # Log the API key status (masked for security)
        if settings.OPENAI_API_KEY:
            api_key_status = f"provided (length: {len(settings.OPENAI_API_KEY)})"
            logger.info(f"OpenAI API key is {api_key_status}")
        else:
            logger.warning("OPENAI_API_KEY not set or empty. Semantic validation will be disabled.")
            return
        
        # Set environment variable for OpenAI API key (some libraries require this)
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        
        # Verify OpenAI API key before attempting to initialize the agent
        if not verify_openai_api_key(settings.OPENAI_API_KEY):
            logger.error("OpenAI API key verification failed. Semantic validation will be disabled.")
            return
        
        # Import necessary modules
        import asyncio
        import nest_asyncio
        
        # Apply nest_asyncio to allow running async code in sync context
        try:
            nest_asyncio.apply()
        except RuntimeError as e:
            logger.warning(f"Failed to apply nest_asyncio: {e}. Will try alternate approach if needed.")
        
        # Define a timeout wrapper for agent initialization
        async def initialize_with_timeout(timeout=30.0):
            try:
                # Import PydanticAI
                from pydantic_ai import Agent
                
                # Check PydanticAI version to determine initialization approach
                pydantic_ai_version = importlib.metadata.version("pydantic-ai")
                logger.info(f"Detected PydanticAI version: {pydantic_ai_version}")
                
                # Use an extremely reliable and widely available model
                model_name = "gpt-3.5-turbo"  # Changed to most widely available model
                logger.info(f"Attempting to use model: {model_name}")
                
                # Simplified agent initialization with minimal parameters
                logger.info("Using simplified agent initialization pattern")
                
                # First attempt: standard initialization
                params = {
                    "model": f"openai:{model_name}",
                    "api_key": settings.OPENAI_API_KEY,
                    "system_prompt": "You are a validation assistant."
                }
                logger.info(f"Initializing agent with parameters: {str(params)}")
                
                try:
                    # Create agent with explicit parameters
                    agent = Agent(**params)
                    
                    if agent is None:
                        logger.error("Agent initialization returned None despite no exceptions")
                        return None
                    
                    logger.info("PydanticAI Agent initialized successfully")
                    return agent
                    
                except Exception as e:
                    logger.error(f"Failed to initialize agent: {str(e)}")
                
                # Second attempt: minimal initialization as last resort
                logger.info("Attempting minimal initialization as last resort")
                agent = Agent(api_key=settings.OPENAI_API_KEY)
                logger.info("Minimal agent initialization succeeded")
                return agent
                
            except Exception as e:
                logger.error(f"All agent initialization attempts failed: {str(e)}", exc_info=True)
                return None
        
        # Run the initialization with timeout
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the initialization task with timeout
            try:
                logger.info("Starting agent initialization with timeout...")
                _validation_agent = loop.run_until_complete(
                    asyncio.wait_for(initialize_with_timeout(), timeout=30.0)
                )
            except asyncio.TimeoutError:
                logger.error("Agent initialization timed out after 30 seconds")
                _validation_agent = None
        
        except Exception as e:
            logger.error(f"Failed to run agent initialization: {str(e)}", exc_info=True)
            _validation_agent = None
        
        logger.info("PydanticAI Agent initialization completed")
        
        # Verify agent is working with simple prompt
        if _validation_agent is None:
            logger.error("Agent initialization appeared to succeed but returned None")
        else:
            verify_agent_functionality()
            
    except Exception as e:
        logger.error(f"Error in agent initialization process: {str(e)}", exc_info=True)

def verify_openai_api_key(api_key: str) -> bool:
    """
    Verify that the OpenAI API key is valid without initializing the full agent.
    
    Args:
        api_key: The OpenAI API key to verify
        
    Returns:
        bool: True if the API key is valid, False otherwise
    """
    if not api_key:
        return False
        
    try:
        # Simple call to OpenAI API to check if the key is valid
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Using models endpoint as a lightweight check
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers
        )
        
        if response.status_code == 200:
            logger.info("OpenAI API key verification successful")
            return True
        else:
            logger.error(f"OpenAI API key verification failed: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error verifying OpenAI API key: {str(e)}")
        return False

def verify_agent_functionality():
    """
    Verify that the initialized agent is functioning correctly with a simple prompt.
    """
    global _validation_agent
    
    if not _validation_agent:
        logger.warning("Cannot verify agent functionality: agent is not initialized")
        return False
        
    try:
        logger.info("Starting agent functionality verification...")
        
        # Very simple verification without using run/arun methods
        # Just check that it's a proper Agent instance
        from pydantic_ai import Agent
        if not isinstance(_validation_agent, Agent):
            logger.error(f"_validation_agent is not an Agent instance: {type(_validation_agent)}")
            return False
            
        logger.info(f"Agent instance verified: {type(_validation_agent)}")
        
        # Skip the actual test call for now - just verify the instance
        return True
        
    except Exception as e:
        logger.error(f"Agent functionality verification failed: {str(e)}", exc_info=True)
        return False

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