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
    status_id: Optional[str] = Field(None, description="✅ Filter by status ID (API-supported)")
    assignedto_id: Optional[int] = Field(None, description="🔧 Filter by assigned user ID (client-side)")
    priority_id: Optional[int] = Field(None, description="🔧 Filter by priority ID (client-side)")
    type_id: Optional[int] = Field(None, description="🔧 Filter by test type ID (client-side)")
    with_data: Optional[str] = Field(None, description="✅ Include test data (API-supported)")
    limit: Optional[int] = Field(None, description="✅ Limit results (API-supported)")
    offset: Optional[int] = Field(None, description="✅ Pagination offset (API-supported)")


class GetTestInput(BaseModel):
    """Input schema for getting a specific test"""
    test_id: str = Field(..., description="Test ID")

