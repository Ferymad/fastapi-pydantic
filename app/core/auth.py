"""
Authentication utilities for the AI Output Validation Service.

This module provides utilities for API key validation and management.
"""

from typing import Optional
from fastapi import Header, HTTPException, Depends, status
from app.config import Settings, get_settings

async def get_optional_api_key(
    x_api_key: Optional[str] = Header(None, description="Optional API key for authentication"),
    settings: Settings = Depends(get_settings)
) -> Optional[str]:
    """
    Validate the API key if authentication is enabled.
    
    If AUTH_ENABLED is False, this function will always pass and return None,
    regardless of whether an API key is provided or not.
    
    Args:
        x_api_key: The API key provided in the X-API-Key header
        settings: Application settings
        
    Returns:
        The validated API key or None if authentication is disabled
        
    Raises:
        HTTPException: If authentication is enabled and the API key is invalid
    """
    # If authentication is disabled, skip validation
    if not settings.AUTH_ENABLED:
        return None
    
    # If authentication is enabled, require and validate API key
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return x_api_key 