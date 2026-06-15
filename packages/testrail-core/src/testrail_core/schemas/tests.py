"""Test-related schemas"""

from pydantic import BaseModel, Field
from .common import PaginatedResponse


class Test(BaseModel):
    """TestRail Test schema"""
    id: int
    case_id: int
    status_id: int | None = None
    assignedto_id: int | None = None
    run_id: int
    title: str
    type_id: int | None = None
    priority_id: int | None = None
    estimate: str | None = None
    estimate_forecast: str | None = None
    refs: str | None = None
    milestone_id: int | None = None


class TestsResponse(PaginatedResponse):
    """Response for get_tests endpoint"""
    tests: list[Test] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetTestsInput(BaseModel):
    """Input schema for getting tests in a run"""
    run_id: str = Field(..., description="Test run ID")
    status_id: str | None = Field(None, description="✅ Filter by status ID (API-supported)")
    assignedto_id: int | None = Field(None, description="🔧 Filter by assigned user ID (client-side)")
    priority_id: int | None = Field(None, description="🔧 Filter by priority ID (client-side)")
    type_id: int | None = Field(None, description="🔧 Filter by test type ID (client-side)")
    with_data: str | None = Field(None, description="✅ Include test data (API-supported)")
    limit: int | None = Field(None, description="✅ Limit results (API-supported)")
    offset: int | None = Field(None, description="✅ Pagination offset (API-supported)")


class GetTestInput(BaseModel):
    """Input schema for getting a specific test"""
    test_id: str = Field(..., description="Test ID")

