"""Project-related schemas"""

from typing import Optional, List
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
    is_completed: Optional[bool] = Field(None, description="Filter by completion status")
