"""Milestone-related schemas"""

from typing import Optional, List, Union
from pydantic import BaseModel, Field
from .common import PaginatedResponse


class Milestone(BaseModel):
    """TestRail Milestone schema"""
    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    is_completed: Optional[bool] = None
    is_started: Optional[bool] = None
    completed_on: Optional[int] = None
    due_on: Optional[int] = None
    start_on: Optional[int] = None
    started_on: Optional[int] = None
    parent_id: Optional[int] = None
    url: Optional[str] = None


class MilestonesResponse(PaginatedResponse):
    """Response for get_milestones endpoint"""
    milestones: List[Milestone] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetMilestonesInput(BaseModel):
    """Input schema for getting milestones"""
    project_id: Union[int, str] = Field(..., description="Project ID")
    is_completed: Optional[Union[bool, int, str]] = Field(None, description="✅ Filter by completion status (true/false or 1/0) (API-supported)")
    is_started: Optional[Union[bool, int, str]] = Field(None, description="✅ Filter by started status (true/false or 1/0) (API-supported)")
    name: Optional[str] = Field(None, description="🔧 Filter by milestone name (client-side)")
    limit: Optional[int] = Field(None, description="✅ The number of milestones to return (default 250) — TestRail 6.7+ (API-supported)")
    offset: Optional[int] = Field(None, description="✅ Pagination offset — TestRail 6.7+ (API-supported)")


class GetMilestoneInput(BaseModel):
    """Input schema for getting a specific milestone"""
    milestone_id: str = Field(..., description="Milestone ID")


class AddMilestonePayload(BaseModel):
    """Payload for creating a new milestone"""
    name: str = Field(..., description="Milestone name (required)")
    description: Optional[str] = Field(None, description="Milestone description")
    due_on: Optional[int] = Field(None, description="Due date as Unix timestamp")
    start_on: Optional[int] = Field(None, description="Start date as Unix timestamp")
    parent_id: Optional[int] = Field(None, description="Parent milestone ID for hierarchical milestones")
    
    class Config:
        populate_by_name = True


class UpdateMilestonePayload(BaseModel):
    """Payload for updating a milestone"""
    name: Optional[str] = Field(None, description="Milestone name")
    description: Optional[str] = Field(None, description="Milestone description")
    due_on: Optional[int] = Field(None, description="Due date as Unix timestamp")
    start_on: Optional[int] = Field(None, description="Start date as Unix timestamp")
    parent_id: Optional[int] = Field(None, description="Parent milestone ID")
    is_completed: Optional[bool] = Field(None, description="Mark milestone as completed")
    is_started: Optional[bool] = Field(None, description="Mark milestone as started")
    
    class Config:
        populate_by_name = True
