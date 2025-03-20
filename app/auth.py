"""
Authentication handlers for the API.

This module handles API key authentication for secure endpoints.
Authentication can be enabled/disabled through the AUTH_ENABLED setting.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from typing import Annotated

from app.config import get_settings

# Get settings
settings = get_settings()
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def verify_api_key(
    api_key: Annotated[str, Depends(api_key_header)]
) -> str:
    """
    Verify the API key provided in the request header.
    
    If AUTH_ENABLED is False, this will always pass authentication.
    
    Args:
        api_key: The API key from the x-api-key header
        
    Returns:
        The API key if valid
        
    Raises:
        HTTPException: If API key is missing or invalid when AUTH_ENABLED is True
    """
    # Skip authentication if disabled
    if not settings.AUTH_ENABLED:
        return api_key or "auth_disabled"
    
    # When auth is enabled, validate the API key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key 