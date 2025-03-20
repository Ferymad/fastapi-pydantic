"""
FastAPI application for AI Output Validation Service.

This service provides enhanced validation for AI-generated outputs,
combining standard Pydantic validation with semantic validation
through PydanticAI integration.
"""

from contextlib import asynccontextmanager
import time
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request, Response, status, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, Field, create_model

from app.config import get_settings
from app.monitoring import configure_monitoring, log_request, log_validation
from app.ai_agent import (
    enhance_validation, 
    ValidationLevel,
    SemanticValidationResult,
    EnhancedValidationResponse
)

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request logging and timing
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Log request details and timing"""
    start_time = time.time()
    
    # Add request ID for tracking
    request_id = request.headers.get("X-Request-ID", None)
    
    # Process the request
    try:
        response = await call_next(request)
        
        # Log successful request
        process_time = (time.time() - start_time) * 1000
        log_request(
            request=request,
            response=response,
            processing_time=process_time,
            request_id=request_id,
        )
        
        # Add processing time header
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        return response
        
    except Exception as e:
        # Log failed request
        process_time = (time.time() - start_time) * 1000
        log_request(
            request=request,
            error=str(e),
            processing_time=process_time,
            request_id=request_id,
        )
        
        # Return error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "error": str(e)}
        )

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
    content: Dict[str, Any] = Field(..., description="Content to validate")
    schema: Dict[str, Any] = Field(..., description="Pydantic schema to validate against")
    validation_type: str = Field(
        "generic", 
        description="Type of validation to perform (generic, recommendation, summary, etc.)"
    )
    validation_level: ValidationLevel = Field(
        ValidationLevel.STANDARD, 
        description="Level of semantic validation strictness"
    )

@app.post(
    "/validate", 
    response_model=EnhancedValidationResponse, 
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
    start_time = time.time()
    
    # Prepare results dictionaries
    standard_results = {}
    structured_errors = []
    
    # Perform standard Pydantic validation
    try:
        # Create dynamic model from schema
        dynamic_model = create_model(
            "DynamicModel",
            **{field_name: (field_type.get("type", Any), ... if field_type.get("required", False) else None) 
               for field_name, field_type in request.schema.items()}
        )
        
        # Validate against dynamic model
        validated_data = dynamic_model(**request.content)
        standard_results = {
            "status": "valid",
            "errors": [],
            "validated_data": validated_data.model_dump()
        }
        
    except ValidationError as e:
        # Handle validation errors
        error_details = e.errors()
        standard_results = {
            "status": "invalid",
            "errors": error_details,
            "validated_data": None
        }
        structured_errors = error_details
    
    # Log validation results
    log_validation(
        content=request.content,
        schema=request.schema,
        validation_type=request.validation_type,
        standard_results=standard_results,
    )
    
    # Enhance validation with semantic checks if API key is configured
    if settings.OPENAI_API_KEY:
        enhanced_results = await enhance_validation(
            data=request.content,
            validation_type=request.validation_type,
            validation_level=request.validation_level,
            standard_validation_result=standard_results,
            structural_errors=structured_errors,
        )
    else:
        processing_time = (time.time() - start_time) * 1000
        enhanced_results = {
            "standard_validation": standard_results,
            "semantic_validation": {
                "is_semantically_valid": False,
                "semantic_score": 0.0,
                "issues": ["OpenAI API key not configured. Semantic validation is disabled."],
                "suggestions": ["Configure OPENAI_API_KEY environment variable to enable semantic validation."]
            },
            "processing_time_ms": processing_time,
        }
    
    return enhanced_results 