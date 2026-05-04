"""Project-related schemas"""

from typing import Optional, List, Union
from pydantic import BaseModel, Field
from .common import PaginatedResponse


class Project(BaseModel):
    """TestRail Project schema"""
    id: int
    name: str
    announcement: Optional[str] = None
    show_announcement: Optional[bool] = None
    is_completed: bool = False
    completed_on: Optional[int] = None
    suite_mode: Optional[int] = None
    default_role_id: Optional[int] = None
    url: str


class ProjectsResponse(PaginatedResponse):
    """Response for get_projects endpoint"""
    projects: List[Project] = Field(default_factory=list)


class GetProjectsInput(BaseModel):
    """Input schema for getting projects"""
    is_completed: Optional[Union[bool, int]] = Field(None, description="✅ Filter by completion status (1=completed, 0=active) (API-supported)")
    limit: Optional[int] = Field(None, description="✅ The number of projects to return (default 250) — TestRail 6.7+ (API-supported)")
    offset: Optional[int] = Field(None, description="✅ Pagination offset — TestRail 6.7+ (API-supported)")
