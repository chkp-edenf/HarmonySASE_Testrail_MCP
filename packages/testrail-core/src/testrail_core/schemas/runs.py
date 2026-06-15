"""Test run-related schemas"""

from pydantic import BaseModel, ConfigDict, Field
from .common import PaginatedResponse


class Run(BaseModel):
    """TestRail Run schema"""
    id: int
    name: str
    description: str | None = None
    suite_id: int | None = None
    project_id: int | None = None
    plan_id: int | None = None
    milestone_id: int | None = None
    assignedto_id: int | None = None
    include_all: bool | None = None
    is_completed: bool | None = None
    completed_on: int | None = None
    passed_count: int | None = None
    blocked_count: int | None = None
    untested_count: int | None = None
    retest_count: int | None = None
    failed_count: int | None = None
    custom_status1_count: int | None = None
    custom_status2_count: int | None = None
    custom_status3_count: int | None = None
    custom_status4_count: int | None = None
    custom_status5_count: int | None = None
    custom_status6_count: int | None = None
    custom_status7_count: int | None = None
    config: str | None = None
    config_ids: list[int] | None = None
    url: str | None = None
    created_on: int | None = None
    created_by: int | None = None


class RunsResponse(PaginatedResponse):
    """Response for get_runs endpoint"""
    runs: list[Run] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetRunsInput(BaseModel):
    """Input schema for getting test runs"""
    project_id: int | str = Field(..., description="Project ID")
    limit: int | str | None = Field("250", description="Max results (default 250)")

    # Advanced filtering parameters (v1.4.0)
    created_by: int | str | None = Field(None, description="Filter by user ID who created the run")
    created_after: int | str | None = Field(None, description="Unix timestamp - runs created after this date")
    created_before: int | str | None = Field(None, description="Unix timestamp - runs created before this date")
    milestone_id: int | str | None = Field(None, description="Filter by milestone IDs (comma-separated for multiple)")
    is_completed: bool | int | str | None = Field(None, description="Filter by completion status (true/false)")
    suite_id: int | str | None = Field(None, description="✅ Filter by suite ID (API-supported)")
    refs_filter: str | None = Field(None, description="✅ A single Reference ID (e.g. TR-a, 4291, etc.) (API-supported)")
    offset: int | str | None = Field(None, description="✅ Pagination offset (API-supported)")


class GetRunInput(BaseModel):
    """Input schema for getting a specific test run"""
    run_id: str = Field(..., description="Test run ID")


class AddRunPayload(BaseModel):
    """Payload for creating a new test run"""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Test run name (required)")
    description: str | None = Field(None, description="Test run description")
    suite_id: int | None = Field(None, description="Suite ID")
    milestone_id: int | None = Field(None, description="Milestone ID")
    assignedto_id: int | None = Field(None, description="User ID to assign the run to")
    include_all: bool | None = Field(None, description="Include all test cases")
    case_ids: list[int] | None = Field(None, description="List of case IDs to include")
    refs: str | None = Field(None, description="A comma-separated list of references/requirements — TestRail 6.1+")
    start_on: int | None = Field(None, description="The start date of a test run as UNIX timestamp")
    due_on: int | None = Field(None, description="The due date of a test run as UNIX timestamp")


class UpdateRunPayload(BaseModel):
    """Payload for updating a test run"""
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, description="Test run name")
    description: str | None = Field(None, description="Test run description")
    milestone_id: int | None = Field(None, description="Milestone ID")
    include_all: bool | None = Field(None, description="Include all test cases")
    case_ids: list[int] | None = Field(None, description="List of case IDs to include")
    refs: str | None = Field(None, description="A comma-separated list of references/requirements — TestRail 6.1+")
    start_on: int | None = Field(None, description="The start date of a test run as UNIX timestamp")
    due_on: int | None = Field(None, description="The due date of a test run as UNIX timestamp")
