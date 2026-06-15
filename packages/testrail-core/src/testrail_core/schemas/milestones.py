"""Milestone-related schemas"""

from pydantic import BaseModel, ConfigDict, Field
from .common import PaginatedResponse


class Milestone(BaseModel):
    """TestRail Milestone schema"""
    id: int
    project_id: int
    name: str
    description: str | None = None
    is_completed: bool | None = None
    is_started: bool | None = None
    completed_on: int | None = None
    due_on: int | None = None
    start_on: int | None = None
    started_on: int | None = None
    parent_id: int | None = None
    url: str | None = None


class MilestonesResponse(PaginatedResponse):
    """Response for get_milestones endpoint"""
    milestones: list[Milestone] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetMilestonesInput(BaseModel):
    """Input schema for getting milestones"""
    project_id: int | str = Field(..., description="Project ID")
    is_completed: bool | int | str | None = Field(None, description="✅ Filter by completion status (true/false or 1/0) (API-supported)")
    is_started: bool | int | str | None = Field(None, description="✅ Filter by started status (true/false or 1/0) (API-supported)")
    name: str | None = Field(None, description="🔧 Filter by milestone name (client-side)")
    limit: int | None = Field(None, description="✅ The number of milestones to return (default 250) — TestRail 6.7+ (API-supported)")
    offset: int | None = Field(None, description="✅ Pagination offset — TestRail 6.7+ (API-supported)")


class GetMilestoneInput(BaseModel):
    """Input schema for getting a specific milestone"""
    milestone_id: str = Field(..., description="Milestone ID")


class AddMilestonePayload(BaseModel):
    """Payload for creating a new milestone"""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Milestone name (required)")
    description: str | None = Field(None, description="Milestone description")
    due_on: int | None = Field(None, description="Due date as Unix timestamp")
    start_on: int | None = Field(None, description="Start date as Unix timestamp")
    parent_id: int | None = Field(None, description="Parent milestone ID for hierarchical milestones")


class UpdateMilestonePayload(BaseModel):
    """Payload for updating a milestone"""
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, description="Milestone name")
    description: str | None = Field(None, description="Milestone description")
    due_on: int | None = Field(None, description="Due date as Unix timestamp")
    start_on: int | None = Field(None, description="Start date as Unix timestamp")
    parent_id: int | None = Field(None, description="Parent milestone ID")
    is_completed: bool | None = Field(None, description="Mark milestone as completed")
    is_started: bool | None = Field(None, description="Mark milestone as started")
