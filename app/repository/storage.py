"""
Schema repository storage implementation.

This module provides file-based storage for schemas in the repository.
"""

import os
import json
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path

from .models import SchemaDefinition, SchemaMetadata, SchemaCreate, SchemaUpdate

# Configure logging
logger = logging.getLogger(__name__)

class FileStorage:
    """File-based storage for schemas."""
    
    def __init__(self, base_dir: str = "data/schemas"):
        """Initialize file storage with base directory.
        
        Args:
            base_dir: Base directory for storing schemas. Defaults to "data/schemas".
        """
        self.base_dir = Path(base_dir)
        self._ensure_base_dir_exists()
    
    def _ensure_base_dir_exists(self) -> None:
        """Ensure the base directory exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured base directory exists: {self.base_dir}")
    
    def _get_schema_dir(self, schema_name: str) -> Path:
        """Get the directory path for a schema.
        
        Args:
            schema_name: Name of the schema.
            
        Returns:
            Path to the schema directory.
        """
        return self.base_dir / schema_name
    
    def _get_schema_metadata_path(self, schema_name: str) -> Path:
        """Get the path to the metadata file for a schema.
        
        Args:
            schema_name: Name of the schema.
            
        Returns:
            Path to the schema metadata file.
        """
        return self._get_schema_dir(schema_name) / "metadata.json"
    
    def _get_schema_version_path(self, schema_name: str, version: str) -> Path:
        """Get the path to the schema version file.
        
        Args:
            schema_name: Name of the schema.
            version: Version of the schema.
            
        Returns:
            Path to the schema version file.
        """
        return self._get_schema_dir(schema_name) / f"{version}.json"
    
    async def schema_exists(self, schema_name: str) -> bool:
        """Check if a schema exists.
        
        Args:
            schema_name: Name of the schema.
            
        Returns:
            True if the schema exists, False otherwise.
        """
        schema_dir = self._get_schema_dir(schema_name)
        metadata_path = self._get_schema_metadata_path(schema_name)
        
        return schema_dir.exists() and metadata_path.exists()
    
    async def create_schema(self, schema: SchemaCreate) -> SchemaDefinition:
        """Create a new schema.
        
        Args:
            schema: Schema to create.
            
        Returns:
            Created schema definition.
            
        Raises:
            ValueError: If the schema already exists.
        """
        # Check if schema already exists
        if await self.schema_exists(schema.name):
            raise ValueError(f"Schema with name '{schema.name}' already exists")
        
        # Create schema directory
        schema_dir = self._get_schema_dir(schema.name)
        schema_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare initial version
        version = "1.0"
        now = datetime.utcnow()
        
        # Create schema definition
        schema_def = SchemaDefinition(
            name=schema.name,
            description=schema.description,
            version=version,
            created_at=now,
            updated_at=now,
            schema=schema.schema,
            validation_level=schema.validation_level,
            example=schema.example
        )
        
        # Create metadata
        metadata = SchemaMetadata(
            name=schema.name,
            description=schema.description,
            current_version=version,
            created_at=now,
            updated_at=now,
            versions=[version]
        )
        
        # Save schema version
        version_path = self._get_schema_version_path(schema.name, version)
        with open(version_path, "w") as f:
            f.write(schema_def.model_dump_json(indent=2))
        
        # Save metadata
        metadata_path = self._get_schema_metadata_path(schema.name)
        with open(metadata_path, "w") as f:
            f.write(metadata.model_dump_json(indent=2))
        
        logger.info(f"Created schema '{schema.name}' with version {version}")
        
        return schema_def
    
    async def get_schema(self, schema_name: str, version: Optional[str] = None) -> SchemaDefinition:
        """Get a schema by name and optional version.
        
        Args:
            schema_name: Name of the schema.
            version: Version of the schema. If None, the latest version is returned.
            
        Returns:
            Schema definition.
            
        Raises:
            ValueError: If the schema does not exist or the version does not exist.
        """
        # Check if schema exists
        if not await self.schema_exists(schema_name):
            raise ValueError(f"Schema with name '{schema_name}' does not exist")
        
        # Get metadata
        metadata_path = self._get_schema_metadata_path(schema_name)
        with open(metadata_path, "r") as f:
            metadata = SchemaMetadata.model_validate_json(f.read())
        
        # If version not provided, use the latest version
        if version is None:
            version = metadata.current_version
        
        # Check if version exists
        if version not in metadata.versions:
            raise ValueError(f"Version '{version}' does not exist for schema '{schema_name}'")
        
        # Get schema definition
        version_path = self._get_schema_version_path(schema_name, version)
        with open(version_path, "r") as f:
            schema_def = SchemaDefinition.model_validate_json(f.read())
        
        return schema_def
    
    async def update_schema(
        self, schema_name: str, schema_update: SchemaUpdate
    ) -> SchemaDefinition:
        """Update an existing schema.
        
        Args:
            schema_name: Name of the schema.
            schema_update: Schema update data.
            
        Returns:
            Updated schema definition.
            
        Raises:
            ValueError: If the schema does not exist.
        """
        # Check if schema exists
        if not await self.schema_exists(schema_name):
            raise ValueError(f"Schema with name '{schema_name}' does not exist")
        
        # Get metadata
        metadata_path = self._get_schema_metadata_path(schema_name)
        with open(metadata_path, "r") as f:
            metadata = SchemaMetadata.model_validate_json(f.read())
        
        # Get current schema definition
        current_version = metadata.current_version
        current_schema_path = self._get_schema_version_path(schema_name, current_version)
        with open(current_schema_path, "r") as f:
            current_schema = SchemaDefinition.model_validate_json(f.read())
        
        # Check if anything is being updated
        if (
            schema_update.description is None 
            and schema_update.schema is None 
            and schema_update.validation_level is None 
            and schema_update.example is None
        ):
            # Nothing to update
            return current_schema
        
        # Create new version
        # Parse current version
        major, minor = map(int, current_version.split("."))
        # Increment minor version
        new_version = f"{major}.{minor + 1}"
        now = datetime.utcnow()
        
        # Create updated schema definition
        updated_schema = SchemaDefinition(
            name=schema_name,
            description=schema_update.description or current_schema.description,
            version=new_version,
            created_at=current_schema.created_at,
            updated_at=now,
            schema=schema_update.schema or current_schema.schema,
            validation_level=schema_update.validation_level or current_schema.validation_level,
            example=schema_update.example if schema_update.example is not None else current_schema.example,
            version_notes=schema_update.version_notes
        )
        
        # Update metadata
        updated_metadata = SchemaMetadata(
            name=schema_name,
            description=schema_update.description or metadata.description,
            current_version=new_version,
            created_at=metadata.created_at,
            updated_at=now,
            versions=metadata.versions + [new_version]
        )
        
        # Save updated schema
        new_schema_path = self._get_schema_version_path(schema_name, new_version)
        with open(new_schema_path, "w") as f:
            f.write(updated_schema.model_dump_json(indent=2))
        
        # Save updated metadata
        with open(metadata_path, "w") as f:
            f.write(updated_metadata.model_dump_json(indent=2))
        
        logger.info(f"Updated schema '{schema_name}' to version {new_version}")
        
        return updated_schema
    
    async def delete_schema(self, schema_name: str) -> bool:
        """Delete a schema.
        
        Args:
            schema_name: Name of the schema.
            
        Returns:
            True if the schema was deleted, False if it didn't exist.
        """
        schema_dir = self._get_schema_dir(schema_name)
        
        if not schema_dir.exists():
            return False
        
        # Delete schema directory
        shutil.rmtree(schema_dir)
        
        logger.info(f"Deleted schema '{schema_name}'")
        
        return True
    
    async def list_schemas(self) -> List[Dict[str, Any]]:
        """List all schemas in the repository.
        
        Returns:
            List of schema metadata.
        """
        schemas = []
        
        # Iterate over all directories in base dir
        for item in self.base_dir.iterdir():
            if item.is_dir():
                schema_name = item.name
                metadata_path = self._get_schema_metadata_path(schema_name)
                
                if metadata_path.exists():
                    # Load metadata
                    with open(metadata_path, "r") as f:
                        metadata = SchemaMetadata.model_validate_json(f.read())
                    
                    schemas.append(metadata.model_dump())
        
        return schemas
    
    async def get_schema_versions(self, schema_name: str) -> List[str]:
        """Get the versions of a schema.
        
        Args:
            schema_name: Name of the schema.
            
        Returns:
            List of versions.
            
        Raises:
            ValueError: If the schema does not exist.
        """
        # Check if schema exists
        if not await self.schema_exists(schema_name):
            raise ValueError(f"Schema with name '{schema_name}' does not exist")
        
        # Get metadata
        metadata_path = self._get_schema_metadata_path(schema_name)
        with open(metadata_path, "r") as f:
            metadata = SchemaMetadata.model_validate_json(f.read())
        
        return metadata.versions
