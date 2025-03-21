"""
API package for FastAPI route handlers.

This package contains all the API routes and controllers.
"""

from fastapi import APIRouter

from .routes import schemas

api_router = APIRouter()

api_router.include_router(schemas.router, prefix="/schemas", tags=["schemas"])

__all__ = ["api_router"]
