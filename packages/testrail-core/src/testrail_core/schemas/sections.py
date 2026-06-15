"""Section-related schemas"""

from pydantic import BaseModel, ConfigDict, Field
from .common import PaginatedResponse


class Section(BaseModel):
    """TestRail Section schema"""
    id: int
    name: str
    description: str | None = None
    suite_id: int | None = None
    parent_id: int | None = None
    display_order: int | None = None
    depth: int | None = None


class SectionsResponse(PaginatedResponse):
    """Response for get_sections endpoint"""
    sections: list[Section] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetSectionsInput(BaseModel):
    """Input schema for getting sections"""
    project_id: str = Field(..., description="Project ID")
    suite_id: str | None = Field(None, description="Suite ID (optional, filters sections by suite)")
    limit: int | None = Field(None, description="✅ The number of sections to return (default 250) — TestRail 6.7+ (API-supported)")
    offset: int | None = Field(None, description="✅ Pagination offset — TestRail 6.7+ (API-supported)")


class AddSectionPayload(BaseModel):
    """Payload for creating a new section"""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Section name (required)")
    description: str | None = Field(None, description="Section description")
    suite_id: int | None = Field(None, description="Suite ID")
    parent_id: int | None = Field(None, description="Parent section ID")


class UpdateSectionPayload(BaseModel):
    """Payload for updating a section"""
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, description="Section name")
    description: str | None = Field(None, description="Section description")


class MoveSectionPayload(BaseModel):
    """Payload for moving a section"""
    model_config = ConfigDict(populate_by_name=True)

    parent_id: int | None = Field(None, description="New parent section ID")
    after_id: int | None = Field(None, description="Section ID to place after")
