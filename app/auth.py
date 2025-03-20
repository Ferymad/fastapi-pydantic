from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import os
from typing import Annotated

# Use environment variable for API key in production
API_KEY = os.getenv("API_KEY", "test_api_key")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def verify_api_key(
    api_key: Annotated[str, Depends(api_key_header)]
) -> str:
    """
    Verify the API key provided in the request header.
    
    Args:
        api_key: The API key from the x-api-key header
        
    Returns:
        The API key if valid
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key 