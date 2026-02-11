"""Test plan-related schemas"""

from typing import Optional, List, Any, Union
from pydantic import BaseModel, Field
from .common import PaginatedResponse


class PlanEntry(BaseModel):
    """TestRail Plan Entry schema"""
    id: Optional[str] = None
    suite_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    assignedto_id: Optional[int] = None
    include_all: Optional[bool] = None
    case_ids: Optional[List[int]] = None
    config_ids: Optional[List[int]] = None
    runs: Optional[List[Any]] = None


class Plan(BaseModel):
    """TestRail Plan schema"""
    id: int
    name: str
    description: Optional[str] = None
    milestone_id: Optional[int] = None
    assignedto_id: Optional[int] = None
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
    project_id: Optional[int] = None
    created_on: Optional[int] = None
    created_by: Optional[int] = None
    url: Optional[str] = None
    entries: Optional[List[PlanEntry]] = None


class PlansResponse(PaginatedResponse):
    """Response for get_plans endpoint"""
    plans: List[Plan] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetPlansInput(BaseModel):
    """Input schema for getting test plans"""
    project_id: Union[int, str] = Field(..., description="Project ID")
    limit: Optional[Union[int, str]] = Field("250", description="Max results (default 250)")
    offset: Optional[Union[int, str]] = Field(None, description="✅ Pagination offset (API-supported)")
    
    # Advanced filtering parameters
    created_by: Optional[Union[int, str]] = Field(None, description="✅ Filter by user ID who created the plan (API-supported)")
    created_after: Optional[Union[int, str]] = Field(None, description="✅ Unix timestamp - plans created after this date (API-supported)")
    created_before: Optional[Union[int, str]] = Field(None, description="✅ Unix timestamp - plans created before this date (API-supported)")
    milestone_id: Optional[Union[int, str]] = Field(None, description="✅ Filter by milestone IDs (comma-separated for multiple) (API-supported)")
    is_completed: Optional[Union[bool, int, str]] = Field(None, description="✅ Filter by completion status (true/false or 1/0) (API-supported)")


class GetPlanInput(BaseModel):
    """Input schema for getting a specific test plan"""
    plan_id: str = Field(..., description="Test plan ID")


class AddPlanPayload(BaseModel):
    """Payload for creating a new test plan"""
    name: str = Field(..., description="Test plan name (required)")
    description: Optional[str] = Field(None, description="Test plan description")
    milestone_id: Optional[int] = Field(None, description="Milestone ID")
    entries: Optional[List[dict]] = Field(None, description="Test entries to include in the plan")
    
    class Config:
        populate_by_name = True


class UpdatePlanPayload(BaseModel):
    """Payload for updating a test plan"""
    name: Optional[str] = Field(None, description="Test plan name")
    description: Optional[str] = Field(None, description="Test plan description")
    milestone_id: Optional[int] = Field(None, description="Milestone ID")
    entries: Optional[List[dict]] = Field(None, description="Updated test entries")
    
    class Config:
        populate_by_name = True


class AddPlanEntryPayload(BaseModel):
    """Payload for adding a plan entry"""
    suite_id: int = Field(..., description="Suite ID (required)")
    name: Optional[str] = Field(None, description="Entry name (optional)")
    description: Optional[str] = Field(None, description="Entry description")
    assignedto_id: Optional[int] = Field(None, description="User to assign runs to")
    include_all: Optional[bool] = Field(None, description="Include all test cases")
    case_ids: Optional[List[int]] = Field(None, description="Specific case IDs to include")
    config_ids: Optional[List[int]] = Field(None, description="Configuration IDs for runs")
    runs: Optional[List[dict]] = Field(None, description="Custom run configurations")
    
    class Config:
        populate_by_name = True


class UpdatePlanEntryPayload(BaseModel):
    """Payload for updating a plan entry"""
    name: Optional[str] = Field(None, description="Entry name")
    description: Optional[str] = Field(None, description="Entry description")
    assignedto_id: Optional[int] = Field(None, description="User to assign runs to")
    include_all: Optional[bool] = Field(None, description="Include all test cases")
    case_ids: Optional[List[int]] = Field(None, description="Specific case IDs")
    config_ids: Optional[List[int]] = Field(None, description="Configuration IDs")
    
    class Config:
        populate_by_name = True
