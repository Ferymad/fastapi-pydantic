"""
Schema repository API routes.

This module provides the API routes for managing validation schemas.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Path, Query, HTTPException, status
import logging

from app.auth import verify_api_key
from app.repository import (
    SchemaRepository,
    SchemaCreate,
    SchemaUpdate,
    SchemaResponse,
    SchemaList,
    SchemaVersionHistory,
    SchemaDeleteResponse,
    get_schema_repository
)
from app.models import ValidationResponse, StructuralValidationResult, ValidationLevel
from app.validation import create_model_from_schema, perform_structural_validation, perform_semantic_validation
from app.config import get_settings

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=SchemaList, summary="List schemas")
async def list_schemas(
    api_key: str = Depends(verify_api_key),
    repository: SchemaRepository = Depends(get_schema_repository)
):
    """List all available schemas in the repository.
    
    Returns a list of schemas with their metadata, including name, description,
    current version, and URLs for accessing them.
    
    Args:
        api_key: API key for authentication.
        repository: Schema repository service.
        
    Returns:
        List of schemas.
        
    Raises:
        HTTPException: If there is an error listing schemas.
    """
    try:
        return await repository.list_schemas()
    except Exception as e:
        logger.error(f"Error listing schemas: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing schemas: {str(e)}"
        )

@router.post("/", response_model=SchemaResponse, status_code=status.HTTP_201_CREATED, summary="Create schema")
async def create_schema(
    schema: SchemaCreate,
    api_key: str = Depends(verify_api_key),
    repository: SchemaRepository = Depends(get_schema_repository)
):
    """Create a new validation schema.
    
    Creates a new schema in the repository with the specified definition.
    
    Args:
        schema: Schema to create.
        api_key: API key for authentication.
        repository: Schema repository service.
        
    Returns:
        Created schema.
        
    Raises:
        HTTPException: If the schema already exists or if there's an error during creation.
    """
    try:
        logger.info(f"Creating schema: {schema.name}")
        return await repository.create_schema(schema)
    except HTTPException:
        # Re-raise HTTPExceptions from the repository
        raise
    except Exception as e:
        logger.error(f"Error creating schema {schema.name}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating schema: {str(e)}"
        )

@router.get("/_debug", summary="Debug endpoint")
async def debug_schemas(
    api_key: str = Depends(verify_api_key)
):
    """Debug endpoint for schema repository.
    
    This endpoint returns information about the schema repository setup
    to help diagnose issues.
    
    Args:
        api_key: API key for authentication.
        
    Returns:
        Debug information.
    """
    import os
    from pathlib import Path
    
    base_dir = Path("data/schemas")
    
    # Get information about the directory
    debug_info = {
        "base_dir_exists": base_dir.exists(),
        "base_dir_is_dir": base_dir.is_dir() if base_dir.exists() else False,
        "base_dir_abs_path": str(base_dir.absolute()),
        "base_dir_permissions": {
            "readable": os.access(base_dir, os.R_OK) if base_dir.exists() else False,
            "writable": os.access(base_dir, os.W_OK) if base_dir.exists() else False,
            "executable": os.access(base_dir, os.X_OK) if base_dir.exists() else False
        } if base_dir.exists() else None,
        "contents": [str(p) for p in base_dir.iterdir()] if base_dir.exists() and base_dir.is_dir() else []
    }
    
    return {
        "debug_info": debug_info
    }

@router.get("/{schema_name}", response_model=SchemaResponse, summary="Get schema")
async def get_schema(
    schema_name: str = Path(..., description="Name of the schema to retrieve"),
    version: Optional[str] = Query(None, description="Version of the schema to retrieve"),
    api_key: str = Depends(verify_api_key),
    repository: SchemaRepository = Depends(get_schema_repository)
):
    """Get a schema by name and optional version.
    
    Retrieves a schema from the repository by its name. If a version is specified,
    that specific version is returned, otherwise the latest version is returned.
    
    Args:
        schema_name: Name of the schema.
        version: Version of the schema. If None, the latest version is returned.
        api_key: API key for authentication.
        repository: Schema repository service.
        
    Returns:
        Schema definition.
        
    Raises:
        HTTPException: If the schema does not exist or the version does not exist.
    """
    return await repository.get_schema(schema_name, version)

@router.put("/{schema_name}", response_model=SchemaResponse, summary="Update schema")
async def update_schema(
    schema_update: SchemaUpdate,
    schema_name: str = Path(..., description="Name of the schema to update"),
    api_key: str = Depends(verify_api_key),
    repository: SchemaRepository = Depends(get_schema_repository)
):
    """Update an existing schema.
    
    Updates an existing schema in the repository with the specified definition.
    This creates a new version of the schema.
    
    Args:
        schema_update: Schema update data.
        schema_name: Name of the schema to update.
        api_key: API key for authentication.
        repository: Schema repository service.
        
    Returns:
        Updated schema.
        
    Raises:
        HTTPException: If the schema does not exist.
    """
    return await repository.update_schema(schema_name, schema_update)

@router.delete("/{schema_name}", response_model=SchemaDeleteResponse, summary="Delete schema")
async def delete_schema(
    schema_name: str = Path(..., description="Name of the schema to delete"),
    api_key: str = Depends(verify_api_key),
    repository: SchemaRepository = Depends(get_schema_repository)
):
    """Delete a schema.
    
    Deletes a schema from the repository.
    
    Args:
        schema_name: Name of the schema to delete.
        api_key: API key for authentication.
        repository: Schema repository service.
        
    Returns:
        Deletion response.
    """
    return await repository.delete_schema(schema_name)

@router.get("/{schema_name}/versions", response_model=SchemaVersionHistory, summary="Get schema versions")
async def get_schema_versions(
    schema_name: str = Path(..., description="Name of the schema to get versions for"),
    api_key: str = Depends(verify_api_key),
    repository: SchemaRepository = Depends(get_schema_repository)
):
    """Get the version history of a schema.
    
    Retrieves the version history of a schema, including the creation date,
    version notes, and URLs for accessing each version.
    
    Args:
        schema_name: Name of the schema.
        api_key: API key for authentication.
        repository: Schema repository service.
        
    Returns:
        Schema version history.
        
    Raises:
        HTTPException: If the schema does not exist.
    """
    return await repository.get_schema_versions(schema_name)

@router.post("/{schema_name}/validate", response_model=ValidationResponse, summary="Test validate with schema")
async def validate_with_schema(
    data: Dict[str, Any],
    schema_name: str = Path(..., description="Name of the schema to validate against"),
    api_key: str = Depends(verify_api_key),
    repository: SchemaRepository = Depends(get_schema_repository)
):
    """Test validation against a schema in the repository.
    
    This endpoint allows testing data validation against a schema stored
    in the repository without going through the main validation endpoint.
    
    Args:
        data: Data to validate
        schema_name: Name of the schema to validate against
        api_key: API key for authentication
        repository: Schema repository service
        
    Returns:
        Validation response
        
    Raises:
        HTTPException: If the schema does not exist
    """
    settings = get_settings()
    
    try:
        # Get schema from repository
        schema_response = await repository.get_schema(schema_name)
        validation_schema = schema_response.schema
        
        # Create Pydantic model from schema
        schema_model = create_model_from_schema(validation_schema)
        
        # Perform structural validation
        structural_result, validated_data = await perform_structural_validation(
            data, 
            schema_model
        )
        
        # Prepare response
        is_valid = structural_result.is_structurally_valid
        semantic_result = None
        
        # Perform semantic validation if enabled and structurally valid
        if (
            structural_result.is_structurally_valid 
            and settings.SEMANTIC_VALIDATION_ENABLED
            and schema_response.validation_level != ValidationLevel.STRUCTURE_ONLY
        ):
            semantic_result = await perform_semantic_validation(
                data,
                validation_schema,
                "general",  # Default type
                schema_response.validation_level,
            )
            
            # Update overall validity based on semantic validation
            if semantic_result and not semantic_result.is_semantically_valid:
                is_valid = False
        
        # Return validation response
        return ValidationResponse(
            is_valid=is_valid,
            structural_validation=structural_result,
            semantic_validation=semantic_result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {str(e)}"
        )
