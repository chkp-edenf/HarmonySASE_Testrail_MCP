"""Status-related schemas"""

from pydantic import BaseModel, Field


class Status(BaseModel):
    """TestRail Status schema"""
    id: int
    name: str
    label: str
    color_dark: str | None = None
    color_medium: str | None = None
    color_bright: str | None = None
    is_system: bool | None = None
    is_untested: bool | None = None
    is_final: bool | None = None


class StatusesResponse(BaseModel):
    """Response for get_statuses endpoint"""
    statuses: list[Status] = Field(default_factory=list)
    count: int = 0
