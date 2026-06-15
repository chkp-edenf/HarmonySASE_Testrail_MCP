"""Project-related schemas"""

from pydantic import BaseModel, Field
from .common import PaginatedResponse


class Project(BaseModel):
    """TestRail Project schema"""
    id: int
    name: str
    announcement: str | None = None
    show_announcement: bool | None = None
    is_completed: bool = False
    completed_on: int | None = None
    suite_mode: int | None = None
    default_role_id: int | None = None
    url: str


class ProjectsResponse(PaginatedResponse):
    """Response for get_projects endpoint"""
    projects: list[Project] = Field(default_factory=list)


class GetProjectsInput(BaseModel):
    """Input schema for getting projects"""
    is_completed: bool | int | None = Field(None, description="✅ Filter by completion status (1=completed, 0=active) (API-supported)")
    limit: int | None = Field(None, description="✅ The number of projects to return (default 250) — TestRail 6.7+ (API-supported)")
    offset: int | None = Field(None, description="✅ Pagination offset — TestRail 6.7+ (API-supported)")
