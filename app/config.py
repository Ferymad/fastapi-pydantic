"""
Configuration management for the application.

This module centralizes all configuration settings for the application,
using Pydantic's BaseSettings for environment variable validation and typing.
"""

from functools import lru_cache
from typing import List
from pydantic import BaseModel, Field
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
        default=["*"],
        description="List of allowed origins for CORS"
    )
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        case_sensitive = True
        
    def model_post_init(self, __context) -> None:
        """Post-initialization to extract list values from env vars"""
        # Parse CORS_ORIGINS from string if necessary
        if isinstance(self.CORS_ORIGINS, str):
            self.CORS_ORIGINS = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
            
        # Ensure development environment uses "*" for CORS
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
    return Settings(
        # Explicitly load environment variables to handle any parsing or transformation
        SERVICE_NAME=os.getenv("SERVICE_NAME", "ai-output-validator"),
        SERVICE_VERSION=os.getenv("SERVICE_VERSION", "0.1.0"),
        ENV=os.getenv("ENV", "development"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        SECRET_KEY=os.getenv("SECRET_KEY", "dev_secret_key_change_in_production"),
        AUTH_ENABLED=os.getenv("AUTH_ENABLED", "False").lower() in ("true", "1", "t"),
        LOGFIRE_API_KEY=os.getenv("LOGFIRE_API_KEY", ""),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        CORS_ORIGINS=os.getenv("CORS_ORIGINS", "*"),
    ) 