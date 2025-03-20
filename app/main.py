"""
FastAPI application for AI Output Validation Service.

This service provides enhanced validation for AI-generated outputs,
combining standard Pydantic validation with semantic validation
through PydanticAI integration.
"""

from contextlib import asynccontextmanager
import time
from typing import Dict, Any, List, Optional
import logging

from fastapi import FastAPI, Request, Response, status, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, Field, create_model

from app.config import Settings, get_settings
from app.models import (
    ValidationRequest, 
    ValidationResponse, 
    ValidationLevel,
    StructuralValidationResult, 
    SemanticValidationResult
)
from app.auth import get_optional_api_key
from app.monitoring import configure_monitoring, log_request, log_response
from app.validation import (
    create_model_from_schema,
    perform_structural_validation,
    perform_semantic_validation
)
from app.ai_agent import initialize_validation_agent

# Configure logging
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Configure app startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown events
    """
    # Startup: Configure monitoring
    configure_monitoring()
    
    yield
    
    # Shutdown: Cleanup resources if needed
    pass

# Initialize FastAPI app
app = FastAPI(
    title="AI Output Validation Service", 
    description=(
        "Enhanced validation for AI outputs with semantic checks "
        "to ensure quality beyond structural validation."
    ),
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)

# Configure CORS
def get_cors_origins(settings: Settings) -> List[str]:
    """Convert CORS_ORIGINS to proper format accepting both string and list."""
    if isinstance(settings.CORS_ORIGINS, list):
        return settings.CORS_ORIGINS
    elif settings.CORS_ORIGINS == "*":
        return ["*"]
    elif isinstance(settings.CORS_ORIGINS, str):
        return [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    return []

@app.on_event("startup")
async def startup_event():
    """Initialize application resources."""
    settings = get_settings()
    
    # Configure CORS
    origins = get_cors_origins(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Log startup information
    logger.info(f"Application starting with environment: {settings.ENVIRONMENT}")
    logger.info(f"CORS configured with origins: {origins}")
    
    # Configure monitoring
    try:
        configure_monitoring(settings)
        logger.info("Monitoring configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure monitoring: {str(e)}")
    
    # Initialize validation agent
    try:
        logger.info("Initializing validation agent...")
        initialize_validation_agent()
        from app.ai_agent import get_validation_agent
        agent = get_validation_agent()
        if agent:
            logger.info("Validation agent initialized successfully")
        else:
            logger.warning("Validation agent initialization completed but agent is not available")
    except Exception as e:
        logger.error(f"Failed to initialize validation agent: {str(e)}", exc_info=True)
    
    logger.info(f"Application startup complete")

# Middleware for request logging and timing
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    """
    Middleware for request/response monitoring and logging.
    
    Args:
        request: The incoming request
        call_next: The next middleware or endpoint handler
        
    Returns:
        The response from the endpoint
    """
    # Log the incoming request
    await log_request(request)
    
    # Process the request through the endpoint
    response = await call_next(request)
    
    # Log the response
    await log_response(request, response)
    
    return response

# Health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    """
    Health check endpoint to verify service is running
    """
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION
    }

# API Information endpoint
@app.get("/", tags=["info"])
async def root():
    """
    API information endpoint
    """
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "description": "Enhanced validation for AI outputs with semantic checks",
        "docs_url": "/docs",
    }

class ValidationRequest(BaseModel):
    """Request body for validation endpoint"""
    data: Dict[str, Any] = Field(..., description="Content to validate")
    schema: Dict[str, Any] = Field(..., description="Pydantic schema to validate against")
    type: str = Field(
        "generic", 
        description="Type of validation to perform (generic, recommendation, summary, etc.)"
    )
    level: ValidationLevel = Field(
        ValidationLevel.STANDARD, 
        description="Level of semantic validation strictness"
    )

@app.post(
    "/validate", 
    response_model=ValidationResponse, 
    tags=["validation"],
    status_code=status.HTTP_200_OK,
)
async def validate_ai_output(request: ValidationRequest):
    """
    Validate AI-generated output against provided schema and perform semantic validation.
    
    This endpoint:
    1. Performs standard Pydantic validation using the provided schema
    2. Performs semantic validation to check for coherence and quality
    3. Returns both validation results with detailed feedback
    
    The validation_level parameter determines how strict the semantic validation is:
    - basic: Minimal semantic checks
    - standard: Balanced semantic validation (default)
    - strict: Thorough semantic validation with high standards
    """
    validation_response = ValidationResponse(
        is_valid=False,
        structural_validation=StructuralValidationResult(
            is_structurally_valid=False,
            errors=[]
        ),
        semantic_validation=None
    )
    
    try:
        logger.debug(f"Validation request received - type: {request.type}, level: {request.level}")
        
        # Create a dynamic Pydantic model from the schema
        start_time = time.time()
        try:
            model_class = create_model_from_schema(request.schema)
            logger.debug("Dynamic model created successfully")
        except Exception as e:
            logger.error(f"Schema parsing error: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "detail": f"Invalid schema: {str(e)}",
                    "is_valid": False
                }
            )
        
        # Perform structural validation
        structural_validation_result, data = await perform_structural_validation(
            model_class=model_class,
            data=request.data
        )
        validation_response.structural_validation = structural_validation_result
        
        if not structural_validation_result.is_structurally_valid:
            logger.info(f"Structural validation failed with {len(structural_validation_result.errors)} errors")
            validation_response.is_valid = False
            return validation_response
        
        # If semantic validation is requested, perform it
        if request.level != "structure_only":
            logger.debug(f"Performing semantic validation at level: {request.level}")
            try:
                semantic_validation_result = await perform_semantic_validation(
                    validation_type=request.type,
                    validation_level=request.level,
                    data=data,
                    schema=request.schema,
                    structural_errors=structural_validation_result.errors
                )
                validation_response.semantic_validation = semantic_validation_result
                validation_response.is_valid = (
                    structural_validation_result.is_structurally_valid and 
                    semantic_validation_result.is_semantically_valid
                )
                
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Validation completed in {elapsed_time:.2f}s - "
                    f"structural: {structural_validation_result.is_structurally_valid}, "
                    f"semantic: {semantic_validation_result.is_semantically_valid}"
                )
            except Exception as e:
                logger.error(f"Semantic validation error: {e}", exc_info=True)
                validation_response.semantic_validation = SemanticValidationResult(
                    is_semantically_valid=False,
                    semantic_score=0.0,
                    issues=[f"Error during semantic validation: {str(e)}"],
                    suggestions=["Try a different validation level or check the system configuration."]
                )
                validation_response.is_valid = False
        else:
            # For structure_only validation, only structural validation matters
            validation_response.is_valid = structural_validation_result.is_structurally_valid
            elapsed_time = time.time() - start_time
            logger.info(f"Structural validation completed in {elapsed_time:.2f}s - result: {validation_response.is_valid}")
    
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Validation service error: {str(e)}",
                "is_valid": False
            }
        )
    
    return validation_response 