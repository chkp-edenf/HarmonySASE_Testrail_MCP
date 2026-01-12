"""Test run-related schemas"""

from typing import Optional, List
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


class AddRunPayload(BaseModel):
    """Payload for creating a new test run"""
    name: str = Field(..., description="Test run name (required)")
    description: Optional[str] = Field(None, description="Test run description")
    suite_id: Optional[int] = Field(None, description="Suite ID")
    milestone_id: Optional[int] = Field(None, description="Milestone ID")
    assignedto_id: Optional[int] = Field(None, description="User ID to assign the run to")
    include_all: Optional[bool] = Field(None, description="Include all test cases")
    case_ids: Optional[List[int]] = Field(None, description="List of case IDs to include")
    
    class Config:
        populate_by_name = True


class UpdateRunPayload(BaseModel):
    """Payload for updating a test run"""
    name: Optional[str] = Field(None, description="Test run name")
    description: Optional[str] = Field(None, description="Test run description")
    milestone_id: Optional[int] = Field(None, description="Milestone ID")
    include_all: Optional[bool] = Field(None, description="Include all test cases")
    case_ids: Optional[List[int]] = Field(None, description="List of case IDs to include")
    
    class Config:
        populate_by_name = True
