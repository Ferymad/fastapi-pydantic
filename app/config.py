"""
Configuration management for the application.

This module centralizes all configuration settings for the application,
using Pydantic's BaseSettings for environment variable validation and typing.
"""

from functools import lru_cache
from typing import List, Union, Any
from pydantic import BaseModel, Field, field_validator
import os

class Settings(BaseModel):
    """
    Application settings loaded from environment variables
    """
    # Service information
    SERVICE_NAME: str = Field(
        default="ai-output-validator",
        description="Name of the service"
    )
    SERVICE_VERSION: str = Field(
        default="0.1.0",
        description="Version of the service"
    )
    ENV: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    
    # API Settings
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key for PydanticAI validation"
    )
    
    # Security settings
    SECRET_KEY: str = Field(
        default="dev_secret_key_change_in_production",
        description="Secret key for signing tokens"
    )
    AUTH_ENABLED: bool = Field(
        default=False,
        description="Whether authentication is enabled"
    )
    
    # Monitoring settings
    LOGFIRE_API_KEY: str = Field(
        default="",
        description="Logfire API key for logging"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["*"],
        description="List of allowed origins for CORS"
    )
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def validate_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS_ORIGINS from string if necessary"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
            
    @field_validator('AUTH_ENABLED', mode='before')
    @classmethod
    def validate_auth_enabled(cls, v: Any) -> bool:
        """Convert string values to boolean"""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "t", "yes")
        return bool(v)
    
    def model_post_init(self, __context) -> None:
        """Post-initialization validation and adjustments"""
        # Ensure development environment uses "*" for CORS if empty
        if self.ENV == "development" and not self.CORS_ORIGINS:
            self.CORS_ORIGINS = ["*"]
            
        # Production environment validation
        if self.ENV == "production":
            # Ensure we're not using default secret key in production
            if self.SECRET_KEY == "dev_secret_key_change_in_production":
                import warnings
                warnings.warn(
                    "WARNING: Using default secret key in production environment!"
                )

@lru_cache()
def get_settings() -> Settings:
    """
    Returns the settings object, using lru_cache to avoid
    re-initializing settings on every call.
    """
    # No need to manually process environment variables
    # The field_validator will handle string-to-list conversion for CORS_ORIGINS
    return Settings(
        SERVICE_NAME=os.getenv("SERVICE_NAME", "ai-output-validator"),
        SERVICE_VERSION=os.getenv("SERVICE_VERSION", "0.1.0"),
        ENV=os.getenv("ENV", "development"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        SECRET_KEY=os.getenv("SECRET_KEY", "dev_secret_key_change_in_production"),
        AUTH_ENABLED=os.getenv("AUTH_ENABLED", "False"),
        LOGFIRE_API_KEY=os.getenv("LOGFIRE_API_KEY", ""),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        CORS_ORIGINS=os.getenv("CORS_ORIGINS", "*"),
    ) 