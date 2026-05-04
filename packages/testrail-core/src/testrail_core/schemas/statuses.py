"""Status-related schemas"""

from typing import Optional, List
from pydantic import BaseModel, Field


class Status(BaseModel):
    """TestRail Status schema"""
    id: int
    name: str
    label: str
    color_dark: Optional[str] = None
    color_medium: Optional[str] = None
    color_bright: Optional[str] = None
    is_system: Optional[bool] = None
    is_untested: Optional[bool] = None
    is_final: Optional[bool] = None


class StatusesResponse(BaseModel):
    """Response for get_statuses endpoint"""
    statuses: List[Status] = Field(default_factory=list)
    count: int = 0
