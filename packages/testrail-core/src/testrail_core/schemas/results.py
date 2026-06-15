"""Test result-related schemas"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from .common import PaginatedResponse


class Result(BaseModel):
    """TestRail Result schema"""
    id: int
    test_id: int | None = None
    status_id: int | None = None
    created_by: int | None = None
    created_on: int | None = None
    assignedto_id: int | None = None
    comment: str | None = None
    version: str | None = None
    elapsed: str | None = None
    defects: str | None = None
    custom_fields: dict[str, Any] | None = None


class ResultsResponse(PaginatedResponse):
    """Response for get_results endpoint"""
    results: list[Result] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetResultsInput(BaseModel):
    """Input schema for getting test results"""
    test_id: str = Field(..., description="Test ID")
    limit: str | None = Field("250", description="Max results (default 250)")
    offset: str | None = Field(None, description="✅ Pagination offset (API-supported)")

    # Advanced filtering parameters (v1.4.0)
    created_by: str | None = Field(None, description="Filter by user ID who created the result")
    created_after: str | None = Field(None, description="Unix timestamp - results created after this date")
    created_before: str | None = Field(None, description="Unix timestamp - results created before this date")
    status_id: str | None = Field(None, description="Filter by status IDs (comma-separated for multiple)")


class GetResultsForCaseInput(BaseModel):
    """Input schema for getting results for a case in a run"""
    run_id: str = Field(..., description="Test run ID")
    case_id: str = Field(..., description="Test case ID")
    limit: str | None = Field("250", description="Max results (default 250)")
    offset: str | None = Field(None, description="✅ Pagination offset (API-supported)")

    # Advanced filtering parameters (v1.4.0)
    created_by: str | None = Field(None, description="Filter by user ID who created the result")
    created_after: str | None = Field(None, description="Unix timestamp - results created after this date")
    created_before: str | None = Field(None, description="Unix timestamp - results created before this date")
    status_id: str | None = Field(None, description="Filter by status IDs (comma-separated for multiple)")


class GetResultsForRunInput(BaseModel):
    """Input schema for getting all results for a run"""
    run_id: str = Field(..., description="Test run ID")
    limit: str | None = Field("250", description="Max results (default 250)")
    offset: str | None = Field(None, description="✅ Pagination offset (API-supported)")

    # Advanced filtering parameters (v1.4.0)
    created_by: str | None = Field(None, description="Filter by user ID who created the result")
    created_after: str | None = Field(None, description="Unix timestamp - results created after this date")
    created_before: str | None = Field(None, description="Unix timestamp - results created before this date")
    status_id: str | None = Field(None, description="Filter by status IDs (comma-separated for multiple)")
    defects_filter: str | None = Field(None, description="✅ A single Defect ID (e.g. TR-1, 4291, etc.) (API-supported)")


class AddResultPayload(BaseModel):
    """Payload for adding a test result"""
    model_config = ConfigDict(populate_by_name=True, extra="allow")  # Allow custom_* fields

    status_id: int = Field(..., description="Status ID (required)")
    comment: str | None = Field(None, description="Comment/notes for the result")
    version: str | None = Field(None, description="Version or build tested")
    elapsed: str | None = Field(None, description="Time elapsed (e.g., '2m', '1h 30m')")
    defects: str | None = Field(None, description="Comma-separated list of defect IDs")
    assignedto_id: int | None = Field(None, description="User ID to assign")


class AddResultsPayload(BaseModel):
    """Payload for adding multiple test results"""
    model_config = ConfigDict(populate_by_name=True)

    results: list[dict[str, Any]] = Field(..., description="List of result objects")


class AddResultForCaseInput(BaseModel):
    """Input schema for adding a result for a case in a run"""
    run_id: str = Field(..., description="Test run ID")
    case_id: str = Field(..., description="Test case ID")
    status_id: str = Field(..., description="Status ID or name (e.g., '1', 'passed', 'failed', 'blocked'). Use get_statuses to discover all available status options. Accepts both numeric IDs and human-readable names.")
    comment: str | None = Field(None, description="Result comment (optional)")
    version: str | None = Field(None, description="Version tested (optional)")
    elapsed: str | None = Field(None, description="Time elapsed (optional)")
    defects: str | None = Field(None, description="Defects/bugs found (optional)")
    assignedto_id: str | None = Field(None, description="Assigned user ID (optional). Use get_users to retrieve valid user IDs for assignment.")


class AddResultsForCasesInput(BaseModel):
    """Input schema for adding results for multiple cases in a run"""
    run_id: str = Field(..., description="Test run ID")
    results: str = Field(..., description="JSON array of results: [{\"case_id\": 1, \"status_id\": 1}, ...]")
