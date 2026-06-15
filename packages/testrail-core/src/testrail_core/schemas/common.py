"""Common schemas and types shared across the TestRail MCP server"""

from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime


class PaginatedResponse(BaseModel):
    """Standard paginated response from TestRail API"""
    offset: int = 0
    limit: int = 250
    size: int = 0
    _links: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    message: str
    error: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str
    data: Any
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
