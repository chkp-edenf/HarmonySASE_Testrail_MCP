"""Test run-related schemas"""

from typing import Optional, List, Union
from pydantic import BaseModel, Field
from .common import PaginatedResponse


class Run(BaseModel):
    """TestRail Run schema"""
    id: int
    name: str
    description: Optional[str] = None
    suite_id: Optional[int] = None
    project_id: Optional[int] = None
    plan_id: Optional[int] = None
    milestone_id: Optional[int] = None
    assignedto_id: Optional[int] = None
    include_all: Optional[bool] = None
    is_completed: Optional[bool] = None
    completed_on: Optional[int] = None
    passed_count: Optional[int] = None
    blocked_count: Optional[int] = None
    untested_count: Optional[int] = None
    retest_count: Optional[int] = None
    failed_count: Optional[int] = None
    custom_status1_count: Optional[int] = None
    custom_status2_count: Optional[int] = None
    custom_status3_count: Optional[int] = None
    custom_status4_count: Optional[int] = None
    custom_status5_count: Optional[int] = None
    custom_status6_count: Optional[int] = None
    custom_status7_count: Optional[int] = None
    config: Optional[str] = None
    config_ids: Optional[List[int]] = None
    url: Optional[str] = None
    created_on: Optional[int] = None
    created_by: Optional[int] = None


class RunsResponse(PaginatedResponse):
    """Response for get_runs endpoint"""
    runs: List[Run] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetRunsInput(BaseModel):
    """Input schema for getting test runs"""
    project_id: Union[int, str] = Field(..., description="Project ID")
    limit: Optional[Union[int, str]] = Field("250", description="Max results (default 250)")
    
    # Advanced filtering parameters (v1.4.0)
    created_by: Optional[Union[int, str]] = Field(None, description="Filter by user ID who created the run")
    created_after: Optional[Union[int, str]] = Field(None, description="Unix timestamp - runs created after this date")
    created_before: Optional[Union[int, str]] = Field(None, description="Unix timestamp - runs created before this date")
    milestone_id: Optional[Union[int, str]] = Field(None, description="Filter by milestone IDs (comma-separated for multiple)")
    is_completed: Optional[Union[bool, int, str]] = Field(None, description="Filter by completion status (true/false)")
    suite_id: Optional[Union[int, str]] = Field(None, description="✅ Filter by suite ID (API-supported)")
    refs_filter: Optional[str] = Field(None, description="✅ A single Reference ID (e.g. TR-a, 4291, etc.) (API-supported)")
    offset: Optional[Union[int, str]] = Field(None, description="✅ Pagination offset (API-supported)")


class GetRunInput(BaseModel):
    """Input schema for getting a specific test run"""
    run_id: str = Field(..., description="Test run ID")


class AddRunPayload(BaseModel):
    """Payload for creating a new test run"""
    name: str = Field(..., description="Test run name (required)")
    description: Optional[str] = Field(None, description="Test run description")
    suite_id: Optional[int] = Field(None, description="Suite ID")
    milestone_id: Optional[int] = Field(None, description="Milestone ID")
    assignedto_id: Optional[int] = Field(None, description="User ID to assign the run to")
    include_all: Optional[bool] = Field(None, description="Include all test cases")
    case_ids: Optional[List[int]] = Field(None, description="List of case IDs to include")
    refs: Optional[str] = Field(None, description="A comma-separated list of references/requirements — TestRail 6.1+")
    start_on: Optional[int] = Field(None, description="The start date of a test run as UNIX timestamp")
    due_on: Optional[int] = Field(None, description="The due date of a test run as UNIX timestamp")
    
    class Config:
        populate_by_name = True


class UpdateRunPayload(BaseModel):
    """Payload for updating a test run"""
    name: Optional[str] = Field(None, description="Test run name")
    description: Optional[str] = Field(None, description="Test run description")
    milestone_id: Optional[int] = Field(None, description="Milestone ID")
    include_all: Optional[bool] = Field(None, description="Include all test cases")
    case_ids: Optional[List[int]] = Field(None, description="List of case IDs to include")
    refs: Optional[str] = Field(None, description="A comma-separated list of references/requirements — TestRail 6.1+")
    start_on: Optional[int] = Field(None, description="The start date of a test run as UNIX timestamp")
    due_on: Optional[int] = Field(None, description="The due date of a test run as UNIX timestamp")
    
    class Config:
        populate_by_name = True
