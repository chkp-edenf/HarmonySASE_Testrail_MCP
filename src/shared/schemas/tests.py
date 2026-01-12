"""Test-related schemas"""

from typing import Optional, List
from pydantic import BaseModel, Field
from .common import PaginatedResponse


class Test(BaseModel):
    """TestRail Test schema"""
    id: int
    case_id: int
    status_id: Optional[int] = None
    assignedto_id: Optional[int] = None
    run_id: int
    title: str
    type_id: Optional[int] = None
    priority_id: Optional[int] = None
    estimate: Optional[str] = None
    estimate_forecast: Optional[str] = None
    refs: Optional[str] = None
    milestone_id: Optional[int] = None


class TestsResponse(PaginatedResponse):
    """Response for get_tests endpoint"""
    tests: List[Test] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetTestsInput(BaseModel):
    """Input schema for getting tests in a run"""
    run_id: str = Field(..., description="Test run ID")
    status_id: Optional[str] = Field(None, description="Filter by status ID (optional)")


class GetTestInput(BaseModel):
    """Input schema for getting a specific test"""
    test_id: str = Field(..., description="Test ID")

