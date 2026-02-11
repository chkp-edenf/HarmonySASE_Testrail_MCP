"""Test case-related schemas"""

from typing import Optional, List, Any, Dict, Union
from pydantic import BaseModel, Field
from .common import PaginatedResponse


class TestCase(BaseModel):
    """TestRail Test Case schema"""
    id: int
    title: str
    section_id: Optional[int] = None
    template_id: Optional[int] = None
    type_id: Optional[int] = None
    priority_id: Optional[int] = None
    milestone_id: Optional[int] = None
    refs: Optional[str] = None
    created_by: Optional[int] = None
    created_on: Optional[int] = None
    updated_by: Optional[int] = None
    updated_on: Optional[int] = None
    estimate: Optional[str] = None
    estimate_forecast: Optional[str] = None
    suite_id: Optional[int] = None
    display_order: Optional[int] = None
    is_deleted: Optional[bool] = None
    custom_fields: Optional[Any] = None


class CasesResponse(PaginatedResponse):
    """Response for get_cases endpoint"""
    cases: List[TestCase] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetCasesInput(BaseModel):
    """Input schema for getting test cases"""
    project_id: str = Field(..., description="Project ID")
    suite_id: Optional[str] = Field(None, description="Suite ID (optional)")
    limit: Optional[str] = Field("250", description="Max results (default 250)")
    
    # Advanced filtering parameters (v1.4.0)
    created_by: Optional[str] = Field(None, description="Filter by user ID who created the case")
    created_after: Optional[str] = Field(None, description="Unix timestamp - cases created after this date")
    created_before: Optional[str] = Field(None, description="Unix timestamp - cases created before this date")
    updated_by: Optional[str] = Field(None, description="Filter by user ID who last updated")
    updated_after: Optional[str] = Field(None, description="Unix timestamp - cases updated after this date")
    updated_before: Optional[str] = Field(None, description="Unix timestamp - cases updated before this date")
    priority_id: Optional[str] = Field(None, description="Filter by priority IDs (comma-separated for multiple)")
    type_id: Optional[str] = Field(None, description="Filter by case type IDs (comma-separated for multiple)")
    milestone_id: Optional[str] = Field(None, description="Filter by milestone IDs (comma-separated for multiple)")
    section_id: Optional[Union[int, str]] = Field(None, description="✅ Filter by section ID (API-supported)")
    template_id: Optional[Union[int, str]] = Field(None, description="✅ Filter by template ID (API-supported)")
    offset: Optional[Union[int, str]] = Field(None, description="✅ Pagination offset (API-supported)")


class GetCaseInput(BaseModel):
    """Input schema for getting a specific test case"""
    case_id: str = Field(..., description="Test case ID")


# Payload schemas for API request bodies
class AddCasePayload(BaseModel):
    """Payload for creating a new test case"""
    title: str = Field(..., description="Test case title (required)")
    template_id: Optional[int] = Field(None, description="Template ID")
    type_id: Optional[int] = Field(None, description="Test case type ID")
    priority_id: Optional[int] = Field(None, description="Priority ID")
    estimate: Optional[str] = Field(None, description="Time estimate")
    milestone_id: Optional[int] = Field(None, description="Milestone ID")
    refs: Optional[str] = Field(None, description="References/requirements")
    
    # Generic custom fields - accepts any custom_* field dynamically
    # The schema allows additional fields via Config.extra = "allow"
    
    class Config:
        populate_by_name = True  # Allow both camelCase and snake_case
        extra = "allow"  # Allow additional custom_* fields not explicitly defined


class AddCaseInput(BaseModel):
    """Input schema for add_case MCP tool"""
    section_id: str = Field(..., description="Section ID")
    title: str = Field(..., description="Test case title")
    template_id: Optional[str] = Field(None, description="Template ID (optional)")
    type_id: Optional[str] = Field(None, description="Test case type ID (optional)")
    priority_id: Optional[str] = Field(None, description="Priority ID (optional)")
    estimate: Optional[str] = Field(None, description="Time estimate (optional)")
    refs: Optional[str] = Field(None, description="References/requirements (optional)")


class UpdateCasePayload(BaseModel):
    """Payload for updating a test case"""
    title: Optional[str] = Field(None, description="Test case title")
    template_id: Optional[int] = Field(None, description="Template ID")
    type_id: Optional[int] = Field(None, description="Test case type ID")
    priority_id: Optional[int] = Field(None, description="Priority ID")
    estimate: Optional[str] = Field(None, description="Time estimate")
    milestone_id: Optional[int] = Field(None, description="Milestone ID")
    refs: Optional[str] = Field(None, description="References/requirements")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")
    
    class Config:
        populate_by_name = True


class CopyCasesPayload(BaseModel):
    """Payload for copying cases to a section"""
    case_ids: List[int] = Field(..., description="List of case IDs to copy")


class MoveCasesPayload(BaseModel):
    """Payload for moving cases to a section"""
    case_ids: List[int] = Field(..., description="List of case IDs to move")

