"""Test case-related schemas"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from .common import PaginatedResponse


class TestCase(BaseModel):
    """TestRail Test Case schema"""
    id: int
    title: str
    section_id: int | None = None
    template_id: int | None = None
    type_id: int | None = None
    priority_id: int | None = None
    milestone_id: int | None = None
    refs: str | None = None
    created_by: int | None = None
    created_on: int | None = None
    updated_by: int | None = None
    updated_on: int | None = None
    estimate: str | None = None
    estimate_forecast: str | None = None
    suite_id: int | None = None
    display_order: int | None = None
    is_deleted: bool | None = None
    custom_fields: Any | None = None


class CasesResponse(PaginatedResponse):
    """Response for get_cases endpoint"""
    cases: list[TestCase] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetCasesInput(BaseModel):
    """Input schema for getting test cases"""
    project_id: str = Field(..., description="Project ID")
    suite_id: str | None = Field(None, description="Suite ID (optional)")
    limit: str | None = Field("250", description="Max results (default 250)")

    # Advanced filtering parameters (v1.4.0)
    created_by: str | None = Field(None, description="Filter by user ID who created the case")
    created_after: str | None = Field(None, description="Unix timestamp - cases created after this date")
    created_before: str | None = Field(None, description="Unix timestamp - cases created before this date")
    updated_by: str | None = Field(None, description="Filter by user ID who last updated")
    updated_after: str | None = Field(None, description="Unix timestamp - cases updated after this date")
    updated_before: str | None = Field(None, description="Unix timestamp - cases updated before this date")
    priority_id: str | None = Field(None, description="Filter by priority IDs (comma-separated for multiple)")
    type_id: str | None = Field(None, description="Filter by case type IDs (comma-separated for multiple)")
    milestone_id: str | None = Field(None, description="Filter by milestone IDs (comma-separated for multiple)")
    section_id: int | str | None = Field(None, description="✅ Filter by section ID (API-supported)")
    template_id: int | str | None = Field(None, description="✅ Filter by template ID (API-supported)")
    offset: int | str | None = Field(None, description="✅ Pagination offset (API-supported)")


class GetCaseInput(BaseModel):
    """Input schema for getting a specific test case"""
    case_id: str = Field(..., description="Test case ID")


# Payload schemas for API request bodies
class AddCasePayload(BaseModel):
    """Payload for creating a new test case"""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    title: str = Field(..., description="Test case title (required)")
    template_id: int | None = Field(None, description="Template ID")
    type_id: int | None = Field(None, description="Test case type ID")
    priority_id: int | None = Field(None, description="Priority ID")
    estimate: str | None = Field(None, description="Time estimate")
    milestone_id: int | None = Field(None, description="Milestone ID")
    refs: str | None = Field(None, description="References/requirements")

    # Generic custom fields - accepts any custom_* field dynamically
    # The schema allows additional fields via model_config extra="allow"


class AddCaseInput(BaseModel):
    """Input schema for add_case MCP tool"""
    section_id: str = Field(..., description="Section ID")
    title: str = Field(..., description="Test case title")
    template_id: str | None = Field(None, description="Template ID (optional)")
    type_id: str | None = Field(None, description="Test case type ID (optional)")
    priority_id: str | None = Field(None, description="Priority ID (optional)")
    estimate: str | None = Field(None, description="Time estimate (optional)")
    refs: str | None = Field(None, description="References/requirements (optional)")


class UpdateCasePayload(BaseModel):
    """Payload for updating a test case"""
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(None, description="Test case title")
    template_id: int | None = Field(None, description="Template ID")
    type_id: int | None = Field(None, description="Test case type ID")
    priority_id: int | None = Field(None, description="Priority ID")
    estimate: str | None = Field(None, description="Time estimate")
    milestone_id: int | None = Field(None, description="Milestone ID")
    refs: str | None = Field(None, description="References/requirements")
    custom_fields: dict[str, Any] | None = Field(None, description="Custom fields")


class CopyCasesPayload(BaseModel):
    """Payload for copying cases to a section"""
    case_ids: list[int] = Field(..., description="List of case IDs to copy")


class MoveCasesPayload(BaseModel):
    """Payload for moving cases to a section"""
    case_ids: list[int] = Field(..., description="List of case IDs to move")

