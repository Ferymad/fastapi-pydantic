"""
Schema repository service.

This module provides the service layer for the schema repository,
handling business logic and interacting with the storage.
"""

from typing import Dict, List, Optional, Any
from fastapi import Depends, HTTPException, status
import logging

from .models import (
    SchemaCreate, 
    SchemaUpdate, 
    SchemaDefinition, 
    SchemaResponse,
    SchemaList,
    SchemaListItem,
    SchemaVersionHistory,
    SchemaVersionInfo,
    SchemaDeleteResponse
)
from .storage import FileStorage

# Configure logging
logger = logging.getLogger(__name__)

class SchemaRepository:
    """Service for managing schemas in the repository."""
    
    def __init__(self, storage: FileStorage):
        """Initialize the schema repository service.
        
        Args:
            storage: Storage implementation for schemas.
        """
        self.storage = storage
    
    async def create_schema(self, schema: SchemaCreate) -> SchemaResponse:
        """Create a new schema.
        
        Args:
            schema: Schema to create.
            
        Returns:
            Created schema response.
            
        Raises:
            HTTPException: If the schema already exists.
        """
        try:
            schema_def = await self.storage.create_schema(schema)
            return self._convert_to_response(schema_def)
        except ValueError as e:
            logger.error(f"Failed to create schema: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Schema with name '{schema.name}' already exists"
            )
    
    async def get_schema(
        self, schema_name: str, version: Optional[str] = None
    ) -> SchemaResponse:
        """Get a schema by name and optional version.
        
        Args:
            schema_name: Name of the schema.
            version: Version of the schema. If None, the latest version is returned.
            
        Returns:
            Schema response.
            
        Raises:
            HTTPException: If the schema does not exist or the version does not exist.
        """
        try:
            schema_def = await self.storage.get_schema(schema_name, version)
            return self._convert_to_response(schema_def)
        except ValueError as e:
            logger.error(f"Failed to get schema: {str(e)}")
            if "does not exist" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e)
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    async def update_schema(
        self, schema_name: str, schema_update: SchemaUpdate
    ) -> SchemaResponse:
        """Update an existing schema.
        
        Args:
            schema_name: Name of the schema.
            schema_update: Schema update data.
            
        Returns:
            Updated schema response.
            
        Raises:
            HTTPException: If the schema does not exist.
        """
        try:
            schema_def = await self.storage.update_schema(schema_name, schema_update)
            return self._convert_to_response(schema_def)
        except ValueError as e:
            logger.error(f"Failed to update schema: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema with name '{schema_name}' does not exist"
            )
    
    async def delete_schema(self, schema_name: str) -> SchemaDeleteResponse:
        """Delete a schema.
        
        Args:
            schema_name: Name of the schema.
            
        Returns:
            Deletion response.
        """
        deleted = await self.storage.delete_schema(schema_name)
        
        if deleted:
            return SchemaDeleteResponse(
                name=schema_name,
                deleted=True,
                message=f"Schema '{schema_name}' has been deleted"
            )
        
        return SchemaDeleteResponse(
            name=schema_name,
            deleted=False,
            message=f"Schema '{schema_name}' does not exist"
        )
    
    async def list_schemas(self) -> SchemaList:
        """List all schemas in the repository.
        
        Returns:
            List of schemas.
        """
        schemas_data = await self.storage.list_schemas()
        
        schemas = [
            SchemaListItem(
                name=schema["name"],
                description=schema["description"],
                current_version=schema["current_version"],
                created_at=schema["created_at"],
                updated_at=schema["updated_at"],
                url=f"/schemas/{schema['name']}"
            )
            for schema in schemas_data
        ]
        
        return SchemaList(schemas=schemas)
    
    async def get_schema_versions(self, schema_name: str) -> SchemaVersionHistory:
        """Get the version history of a schema.
        
        Args:
            schema_name: Name of the schema.
            
        Returns:
            Schema version history.
            
        Raises:
            HTTPException: If the schema does not exist.
        """
        try:
            # Get all versions
            versions = await self.storage.get_schema_versions(schema_name)
            
            # Get metadata for current version
            metadata_schema = await self.storage.get_schema(schema_name)
            
            # Get all version details
            version_info = []
            for version in versions:
                schema_def = await self.storage.get_schema(schema_name, version)
                version_info.append(
                    SchemaVersionInfo(
                        version=version,
                        created_at=schema_def.updated_at,  # Use updated_at as creation time for version
                        version_notes=schema_def.version_notes,
                        url=f"/schemas/{schema_name}/versions/{version}"
                    )
                )
            
            return SchemaVersionHistory(
                name=schema_name,
                current_version=metadata_schema.version,
                versions=version_info
            )
        except ValueError as e:
            logger.error(f"Failed to get schema versions: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema with name '{schema_name}' does not exist"
            )
    
    def _convert_to_response(self, schema_def: SchemaDefinition) -> SchemaResponse:
        """Convert a schema definition to a response.
        
        Args:
            schema_def: Schema definition.
            
        Returns:
            Schema response.
        """
        return SchemaResponse(
            name=schema_def.name,
            description=schema_def.description,
            version=schema_def.version,
            created_at=schema_def.created_at,
            updated_at=schema_def.updated_at,
            schema=schema_def.schema,
            validation_level=schema_def.validation_level,
            example=schema_def.example,
            usage_url=f"/validate?schema={schema_def.name}"
        )

def get_schema_repository(storage: FileStorage = Depends()) -> SchemaRepository:
    """Dependency for getting the schema repository.
    
    Args:
        storage: Storage implementation for schemas.
        
    Returns:
        Schema repository service.
    """
    return SchemaRepository(storage)
