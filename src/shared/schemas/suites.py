"""Suite-related schemas"""

from typing import Optional, List
from pydantic import BaseModel, Field


class Suite(BaseModel):
    """TestRail Suite schema"""
    id: int
    name: str
    description: Optional[str] = None
    project_id: int
    is_master: Optional[bool] = None
    is_baseline: Optional[bool] = None
    is_completed: Optional[bool] = None
    completed_on: Optional[int] = None
    url: str


class GetSuitesInput(BaseModel):
    """Input schema for getting suites"""
    project_id: str = Field(..., description="Project ID")


class GetSuiteInput(BaseModel):
    """Input schema for getting a specific suite"""
    suite_id: str = Field(..., description="Suite ID")
