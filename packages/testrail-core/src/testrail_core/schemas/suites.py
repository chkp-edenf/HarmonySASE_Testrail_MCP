"""Suite-related schemas"""

from pydantic import BaseModel, Field


class Suite(BaseModel):
    """TestRail Suite schema"""
    id: int
    name: str
    description: str | None = None
    project_id: int
    is_master: bool | None = None
    is_baseline: bool | None = None
    is_completed: bool | None = None
    completed_on: int | None = None
    url: str


class GetSuitesInput(BaseModel):
    """Input schema for getting suites"""
    project_id: str = Field(..., description="Project ID")


class GetSuiteInput(BaseModel):
    """Input schema for getting a specific suite"""
    suite_id: str = Field(..., description="Suite ID")
