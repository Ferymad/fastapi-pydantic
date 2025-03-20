from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from typing import Dict, Any, Annotated
from pydantic import ValidationError

from app.models import ValidationType, validation_models, ErrorResponse, SuccessResponse
from app.auth import verify_api_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic here (if needed)
    yield
    # Shutdown logic here (if needed)

app = FastAPI(
    title="AI Output Validation Service",
    description="A service to validate AI outputs against predefined schemas",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to index.html"""
    return RedirectResponse(url="/static/index.html")

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """Health check endpoint to verify the service is up."""
    return {"status": "healthy"}

@app.post(
    "/validate/{validation_type}",
    response_model=SuccessResponse | ErrorResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_ai_output(
    data: Dict[str, Any],
    validation_type: ValidationType,
    api_key: Annotated[str, Depends(verify_api_key)]
) -> SuccessResponse | ErrorResponse:
    """
    Validate AI output against a predefined schema.
    
    Args:
        data: The AI output data to validate
        validation_type: The type of validation to perform
        api_key: API key for authentication
        
    Returns:
        SuccessResponse: If validation is successful
        ErrorResponse: If validation fails
    """
    try:
        # Get the appropriate model for the validation type
        validation_model = validation_models.get(validation_type)
        if not validation_model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported validation type: {validation_type}",
            )
        
        # Validate the data against the model
        validated_data = validation_model(**data)
        
        # Return success response with validated data
        return SuccessResponse(
            status="valid",
            validated_data=validated_data.model_dump(),
        )
    
    except ValidationError as e:
        # Return error response with validation errors
        return ErrorResponse(
            status="invalid",
            errors=e.errors(),
        ) 