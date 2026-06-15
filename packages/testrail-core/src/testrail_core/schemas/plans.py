"""Test plan-related schemas"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from .common import PaginatedResponse


class PlanEntry(BaseModel):
    """TestRail Plan Entry schema"""
    id: str | None = None
    suite_id: int
    name: str | None = None
    description: str | None = None
    assignedto_id: int | None = None
    include_all: bool | None = None
    case_ids: list[int] | None = None
    config_ids: list[int] | None = None
    runs: list[Any] | None = None


class Plan(BaseModel):
    """TestRail Plan schema"""
    id: int
    name: str
    description: str | None = None
    milestone_id: int | None = None
    assignedto_id: int | None = None
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
    project_id: int | None = None
    created_on: int | None = None
    created_by: int | None = None
    url: str | None = None
    entries: list[PlanEntry] | None = None


class PlansResponse(PaginatedResponse):
    """Response for get_plans endpoint"""
    plans: list[Plan] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetPlansInput(BaseModel):
    """Input schema for getting test plans"""
    project_id: int | str = Field(..., description="Project ID")
    limit: int | str | None = Field("250", description="Max results (default 250)")
    offset: int | str | None = Field(None, description="✅ Pagination offset (API-supported)")

    # Advanced filtering parameters
    created_by: int | str | None = Field(None, description="✅ Filter by user ID who created the plan (API-supported)")
    created_after: int | str | None = Field(None, description="✅ Unix timestamp - plans created after this date (API-supported)")
    created_before: int | str | None = Field(None, description="✅ Unix timestamp - plans created before this date (API-supported)")
    milestone_id: int | str | None = Field(None, description="✅ Filter by milestone IDs (comma-separated for multiple) (API-supported)")
    is_completed: bool | int | str | None = Field(None, description="✅ Filter by completion status (true/false or 1/0) (API-supported)")


class GetPlanInput(BaseModel):
    """Input schema for getting a specific test plan"""
    plan_id: str = Field(..., description="Test plan ID")


class AddPlanPayload(BaseModel):
    """Payload for creating a new test plan"""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Test plan name (required)")
    description: str | None = Field(None, description="Test plan description")
    milestone_id: int | None = Field(None, description="Milestone ID")
    entries: list[dict] | None = Field(None, description="Test entries to include in the plan")


class UpdatePlanPayload(BaseModel):
    """Payload for updating a test plan"""
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, description="Test plan name")
    description: str | None = Field(None, description="Test plan description")
    milestone_id: int | None = Field(None, description="Milestone ID")
    entries: list[dict] | None = Field(None, description="Updated test entries")


class AddPlanEntryPayload(BaseModel):
    """Payload for adding a plan entry"""
    model_config = ConfigDict(populate_by_name=True)

    suite_id: int = Field(..., description="Suite ID (required)")
    name: str | None = Field(None, description="Entry name (optional)")
    description: str | None = Field(None, description="Entry description")
    assignedto_id: int | None = Field(None, description="User to assign runs to")
    include_all: bool | None = Field(None, description="Include all test cases")
    case_ids: list[int] | None = Field(None, description="Specific case IDs to include")
    config_ids: list[int] | None = Field(None, description="Configuration IDs for runs")
    runs: list[dict] | None = Field(None, description="Custom run configurations")


class UpdatePlanEntryPayload(BaseModel):
    """Payload for updating a plan entry"""
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, description="Entry name")
    description: str | None = Field(None, description="Entry description")
    assignedto_id: int | None = Field(None, description="User to assign runs to")
    include_all: bool | None = Field(None, description="Include all test cases")
    case_ids: list[int] | None = Field(None, description="Specific case IDs")
    config_ids: list[int] | None = Field(None, description="Configuration IDs")
