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
import os

from fastapi import FastAPI, Request, Response, status, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
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

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
        logger.info("Initializing validation agent on startup (optional)...")
        # We'll just check if the API key is valid and log it,
        # but we won't force initialization - this will happen on first use
        if settings.OPENAI_API_KEY:
            from app.ai_agent import verify_openai_api_key
            key_valid = verify_openai_api_key(settings.OPENAI_API_KEY)
            if key_valid:
                logger.info("OpenAI API key is valid")
            else:
                logger.warning("OpenAI API key validation failed - semantic validation may not work")
        else:
            logger.warning("No OpenAI API key provided - semantic validation will be disabled")
    except Exception as e:
        logger.error(f"OpenAI API key validation error: {str(e)}", exc_info=True)
    
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
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time()
    }

@app.get("/diagnostic", include_in_schema=False)
async def diagnostic():
    """
    Diagnostic endpoint providing detailed information about the service status,
    particularly the PydanticAI agent initialization.
    
    This endpoint is useful for troubleshooting when the agent fails to initialize.
    """
    from app.ai_agent import get_validation_agent
    
    # Get settings
    settings = get_settings()
    
    # Check PydanticAI version
    try:
        import importlib.metadata
        pydantic_ai_version = importlib.metadata.version("pydantic-ai")
    except Exception as e:
        pydantic_ai_version = f"Error getting version: {str(e)}"
    
    # Check if OpenAI API key is provided
    openai_api_key_provided = bool(settings.OPENAI_API_KEY)
    
    # Check environment variable
    openai_api_key_env_provided = bool(os.environ.get("OPENAI_API_KEY"))
    
    # Check if agent is initialized
    agent = get_validation_agent()
    agent_initialized = agent is not None
    
    # Verify OpenAI API key validity without exposing the key
    key_valid = False
    if openai_api_key_provided:
        try:
            from app.ai_agent import verify_openai_api_key
            key_valid = verify_openai_api_key(settings.OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"Error verifying OpenAI API key: {str(e)}")
    
    return {
        "service_status": "healthy",
        "service_name": settings.SERVICE_NAME,
        "service_version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "pydantic_ai_version": pydantic_ai_version,
        "agent_status": {
            "api_key_provided": openai_api_key_provided,
            "api_key_env_provided": openai_api_key_env_provided,
            "api_key_valid": key_valid,
            "agent_initialized": agent_initialized
        },
        "timestamps": {
            "current": time.time()
        }
    }

# API Information endpoint
@app.get("/", tags=["info"])
async def root():
    """
    API information endpoint that redirects to the index page
    """
    return RedirectResponse(url="/static/index.html")

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
async def validate_ai_output(request: Request):
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
    
    Schema Format Support:
    - You can specify field formats using the 'format' attribute (e.g., "format": "email")
    - Supported formats: email, date, url, etc.
    - You can provide regex patterns with the 'pattern' attribute
    - You can specify min_length, max_length for strings and arrays
    - You can specify min, max for numbers and integers
    
    Example Schema with Format Validation:
    ```json
    {
      "email": {"type": "string", "required": true, "format": "email"},
      "date": {"type": "string", "required": true, "format": "date"},
      "phone": {"type": "string", "required": true, "pattern": "^\\d{10}$"}
    }
    ```
    """
    # Handle JSON parsing first to avoid complex errors
    try:
        json_body = await request.json()
    except Exception as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "detail": [{
                    "type": "json_invalid",
                    "loc": ["body"],
                    "msg": f"JSON decode error: {str(e)}",
                    "input": {},
                    "ctx": {"error": str(e)}
                }]
            }
        )
    
    # Validate the request with Pydantic
    try:
        validation_request = ValidationRequest(**json_body)
    except ValidationError as e:
        logger.error(f"Validation request validation error: {str(e)}")
        return JSONResponse(
            status_code=422,
            content={"detail": e.errors()}
        )
        
    validation_response = ValidationResponse(
        is_valid=False,
        structural_validation=StructuralValidationResult(
            is_structurally_valid=False,
            errors=[]
        ),
        semantic_validation=None
    )
    
    try:
        logger.debug(f"Validation request received - type: {validation_request.type}, level: {validation_request.level}")
        
        # Enrich schema with format information if missing
        enriched_schema = validation_request.schema.copy()
        type_format_enrichment = {}
        
        # Common enrichment patterns based on field names
        if validation_request.type == "order" or validation_request.type == "user" or validation_request.type == "personal":
            type_format_enrichment = {
                "email": {"format": "email"},
                "birth_date": {"format": "date"},
                "date_of_birth": {"format": "date"},
                "order_date": {"format": "date"}, 
                "registration_date": {"format": "date"},
                "phone": {"pattern": r"^\d{10}$"},
                "phone_number": {"pattern": r"^\d{10}$"},
                "contact_phone": {"pattern": r"^\d{10}$"},
                "zipcode": {"pattern": r"^\d{5}(-\d{4})?$"},
                "postal_code": {"pattern": r"^\d{5}(-\d{4})?$"}
            }
            
            # Apply enrichment where applicable
            for field_name, field_def in enriched_schema.items():
                if field_name in type_format_enrichment and field_def.get("type") == "string":
                    # Only add format if not already specified
                    for key, value in type_format_enrichment[field_name].items():
                        if key not in field_def:
                            field_def[key] = value
        
        # Create a dynamic Pydantic model from the schema
        start_time = time.time()
        try:
            model_class = create_model_from_schema(enriched_schema)
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
            data=validation_request.data
        )
        validation_response.structural_validation = structural_validation_result
        
        if not structural_validation_result.is_structurally_valid:
            logger.info(f"Structural validation failed with {len(structural_validation_result.errors)} errors")
            
            # Enhance error messages for common validation failures
            for error in validation_response.structural_validation.errors:
                if error["type"] == "string_type":
                    error["suggestion"] = f"The value for '{error['loc']}' must be a string"
                elif error["type"] == "float_parsing":
                    error["suggestion"] = f"The value for '{error['loc']}' must be a valid number, not a string"
                elif error["type"] == "list_type":
                    error["suggestion"] = f"The value for '{error['loc']}' must be an array/list, not a string"
                elif error["type"] == "value_error.email":
                    error["suggestion"] = f"'{error['loc']}' must be a valid email address format (e.g., user@example.com)"
                elif "date" in error["type"]:
                    error["suggestion"] = f"'{error['loc']}' must be in YYYY-MM-DD format (e.g., 2023-10-15)"
                elif "pattern" in error["type"]:
                    error["suggestion"] = f"'{error['loc']}' does not match the required pattern"
                
            validation_response.is_valid = False
            return validation_response
        
        # If semantic validation is requested, perform it
        if validation_request.level != "structure_only":
            logger.debug(f"Performing semantic validation at level: {validation_request.level}")
            try:
                semantic_validation_result = await perform_semantic_validation(
                    validation_type=validation_request.type,
                    validation_level=validation_request.level,
                    data=data,
                    schema=enriched_schema,  # Use enriched schema for semantic validation
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

@app.post("/test-validation", response_model=ValidationResponse, tags=["validation"])
async def test_validation(
    request: ValidationRequest,
    auth_header: Optional[str] = Header(None, alias="X-API-Key"),
) -> ValidationResponse:
    """
    Validate AI output directly using a ValidationRequest model.
    
    This endpoint is designed for testing validation and debugging validation issues.
    It accepts a ValidationRequest body with data, schema, validation type and level.
    
    - **data**: The AI output to validate as JSON object
    - **schema**: Schema definition with type information and constraints
    - **type**: The type of content being validated (e.g., "product", "order", "user")
    - **level**: Validation level (basic, standard, strict)
    
    The endpoint supports enhanced schema definition with:
    - Format validation (email, date)
    - Pattern validation (regex)
    - Length constraints (min_length, max_length)
    - Value constraints (min, max)
    
    Returns a ValidationResponse with detailed structural and semantic validation results.
    """
    # Initialize validation response with invalid status
    validation_response = ValidationResponse(
        is_valid=False,
        structural_validation=StructuralValidationResult(
            is_structurally_valid=False,
            errors=[],
            suggestions=[],
        ),
        semantic_validation=None,
    )
    
    try:
        logger.debug(f"Test validation request received - type: {request.type}, level: {request.level}")
        
        # Enrich schema with format information if missing
        enriched_schema = request.schema.copy()
        type_format_enrichment = {}
        
        # Common enrichment patterns based on field names
        if request.type == "order" or request.type == "user" or request.type == "personal":
            type_format_enrichment = {
                "email": {"format": "email"},
                "birth_date": {"format": "date"},
                "date_of_birth": {"format": "date"},
                "order_date": {"format": "date"}, 
                "registration_date": {"format": "date"},
                "phone": {"pattern": r"^\d{10}$"},
                "phone_number": {"pattern": r"^\d{10}$"},
                "contact_phone": {"pattern": r"^\d{10}$"},
                "zipcode": {"pattern": r"^\d{5}(-\d{4})?$"},
                "postal_code": {"pattern": r"^\d{5}(-\d{4})?$"}
            }
            
            # Apply enrichment where applicable
            for field_name, field_def in enriched_schema.items():
                if field_name in type_format_enrichment and field_def.get("type") == "string":
                    # Only add format if not already specified
                    for key, value in type_format_enrichment[field_name].items():
                        if key not in field_def:
                            field_def[key] = value
        
        # Create a dynamic Pydantic model from the schema
        start_time = time.time()
        try:
            model_class = create_model_from_schema(enriched_schema)
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
            
            # Enhance error messages for common validation failures
            for error in validation_response.structural_validation.errors:
                if error["type"] == "string_type":
                    error["suggestion"] = f"The value for '{error['loc']}' must be a string"
                elif error["type"] == "float_parsing":
                    error["suggestion"] = f"The value for '{error['loc']}' must be a valid number, not a string"
                elif error["type"] == "list_type":
                    error["suggestion"] = f"The value for '{error['loc']}' must be an array/list, not a string"
                elif error["type"] == "value_error.email":
                    error["suggestion"] = f"'{error['loc']}' must be a valid email address format (e.g., user@example.com)"
                elif "date" in error["type"]:
                    error["suggestion"] = f"'{error['loc']}' must be in YYYY-MM-DD format (e.g., 2023-10-15)"
                elif "pattern" in error["type"]:
                    error["suggestion"] = f"'{error['loc']}' does not match the required pattern"
                
            validation_response.is_valid = False
            return validation_response
        
        # Always perform semantic validation for test endpoint
        logger.debug(f"Performing semantic validation at level: {request.level}")
        try:
            semantic_validation_result = await perform_semantic_validation(
                validation_type=request.type,
                validation_level=request.level,
                data=data,
                schema=enriched_schema,  # Use enriched schema for semantic validation
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

@app.get("/v1/capabilities", tags=["info"])
async def validation_capabilities():
    """
    Get information about the validation capabilities of the service.
    
    Returns details about:
    - Supported schema formats
    - Validation constraints
    - Available validation types and levels
    """
    return {
        "version": "1.2.0",
        "supported_formats": {
            "string": ["email", "date", "uri", "regex"],
            "number": ["min", "max"],
            "integer": ["min", "max"],
            "array": ["min_items", "max_items"],
            "object": ["required_properties"]
        },
        "validation_types": ["generic", "product", "order", "user", "article", "recommendation", "summary"],
        "validation_levels": ["basic", "standard", "strict"],
        "schema_constraints": {
            "string": {
                "format": "Validates specific formats (email, date)",
                "pattern": "Regular expression pattern for validation",
                "min_length": "Minimum string length",
                "max_length": "Maximum string length"
            },
            "number/integer": {
                "min": "Minimum allowed value",
                "max": "Maximum allowed value"
            },
            "array": {
                "min_items": "Minimum number of items",
                "max_items": "Maximum number of items"
            }
        },
        "examples": {
            "email_validation": {
                "email": {"type": "string", "required": True, "format": "email"}
            },
            "date_validation": {
                "date": {"type": "string", "required": True, "format": "date"}
            },
            "regex_validation": {
                "phone": {"type": "string", "required": True, "pattern": "^\\d{10}$"}
            }
        }
    } 