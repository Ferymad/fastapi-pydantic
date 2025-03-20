"""
Monitoring and logging configuration for the application.

This module provides centralized logging and monitoring capabilities
using Logfire for structured logging and metrics collection.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, Union

import logfire
from fastapi import Request, Response

from app.config import get_settings

# Get settings
settings = get_settings()

# Configure logger
logger = logging.getLogger(__name__)

def configure_monitoring():
    """
    Configure Logfire monitoring and standard Python logging.
    
    This function should be called during application startup.
    If LOGFIRE_API_KEY is not set, only standard logging will be used.
    """
    # Configure standard Python logging
    logging_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    
    # Configure Logfire if API key is provided
    if settings.LOGFIRE_API_KEY:
        try:
            logfire.configure(
                api_key=settings.LOGFIRE_API_KEY,
                service_name=settings.SERVICE_NAME,
                service_version=settings.SERVICE_VERSION,
                environment=settings.ENV,
            )
            logger.info(
                "Logfire monitoring configured",
                extra={
                    "service_name": settings.SERVICE_NAME,
                    "service_version": settings.SERVICE_VERSION,
                    "environment": settings.ENV,
                },
            )
        except Exception as e:
            logger.error(f"Failed to configure Logfire: {e}")
    else:
        logger.warning(
            "Logfire API key not provided. Using standard logging only.",
            extra={"missing_config": "LOGFIRE_API_KEY"}
        )

def log_request(
    request: Request,
    response: Optional[Response] = None,
    error: Optional[str] = None,
    processing_time: Optional[float] = None,
    request_id: Optional[str] = None,
):
    """
    Log request details and timing information.
    
    Args:
        request: The FastAPI request object
        response: Optional response object
        error: Optional error message if request failed
        processing_time: Processing time in milliseconds
        request_id: Optional request ID for tracking
    """
    # Collect request information
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "client_host": request.client.host if request.client else None,
        "request_id": request_id,
        "processing_time_ms": processing_time,
    }
    
    # Add response information if available
    if response:
        request_info["status_code"] = response.status_code
        
    # Add error information if available
    if error:
        request_info["error"] = error
        logger.error(f"Request failed: {error}", extra=request_info)
    else:
        logger.info("Request processed", extra=request_info)

def log_validation(
    content: Dict[str, Any],
    schema: Dict[str, Any],
    validation_type: str,
    standard_results: Dict[str, Any],
    semantic_results: Optional[Dict[str, Any]] = None,
    processing_time: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Log validation results with structured data.
    
    Args:
        content: Content that was validated
        schema: Schema used for validation
        validation_type: Type of validation performed
        standard_results: Results from standard validation
        semantic_results: Optional results from semantic validation
        processing_time: Optional processing time in milliseconds
        metadata: Optional additional metadata
    """
    is_valid = standard_results.get("status") == "valid"
    is_semantically_valid = None
    
    if semantic_results:
        is_semantically_valid = semantic_results.get("is_semantically_valid")
    
    # Build log data
    log_data = {
        "event_type": "validation",
        "validation_type": validation_type,
        "is_structurally_valid": is_valid,
        "is_semantically_valid": is_semantically_valid,
        "processing_time_ms": processing_time,
        "content_size": len(json.dumps(content)),
    }
    
    # Add error information if validation failed
    if not is_valid and "errors" in standard_results:
        log_data["structural_errors"] = standard_results["errors"]
    
    # Add semantic validation info if available
    if semantic_results:
        log_data["semantic_score"] = semantic_results.get("semantic_score")
        if not is_semantically_valid and "issues" in semantic_results:
            log_data["semantic_issues"] = semantic_results["issues"]
    
    # Add additional metadata if provided
    if metadata:
        log_data.update(metadata)
    
    # Log validation event
    if is_valid and (is_semantically_valid is None or is_semantically_valid):
        logger.info("Validation successful", extra=log_data)
    else:
        logger.warning("Validation failed", extra=log_data)

def get_validation_metrics() -> Dict[str, Any]:
    """
    Get metrics on validation performance and error rates.
    
    Returns:
        Dict with validation metrics
    """
    # This would typically collect metrics from a database or monitoring service
    # For now, we return a simple placeholder
    return {
        "total_validations": 0,
        "validation_success_rate": 0.0,
        "semantic_validation_success_rate": 0.0,
        "average_processing_time_ms": 0.0,
        "validation_types": {},
    }

async def log_request(request: Request) -> None:
    """
    Log request information.
    
    Args:
        request: FastAPI request object
    """
    # Store request start time
    request.state.start_time = time.time()
    
    # Extract basic request information
    client_host = request.client.host if request.client else "unknown"
    method = request.method
    url = str(request.url)
    
    # Log the request
    logger.info(
        f"Request received: {method} {url}",
        extra={
            "client_ip": client_host,
            "request_method": method,
            "request_url": url,
            "request_path": request.url.path,
            "request_query": str(request.url.query),
            "request_headers": dict(request.headers),
        },
    )

async def log_response(request: Request, response: Response) -> None:
    """
    Log response information including processing time.
    
    Args:
        request: FastAPI request object
        response: FastAPI response object
    """
    # Calculate processing time
    processing_time = time.time() - getattr(request.state, "start_time", time.time())
    processing_time_ms = round(processing_time * 1000, 2)
    
    # Extract basic response information
    status_code = response.status_code
    content_length = response.headers.get("content-length", 0)
    
    # Log the response
    logger.info(
        f"Response sent: {status_code} in {processing_time_ms}ms",
        extra={
            "response_status": status_code,
            "response_time_ms": processing_time_ms,
            "response_content_length": content_length,
            "response_headers": dict(response.headers),
        },
    ) 