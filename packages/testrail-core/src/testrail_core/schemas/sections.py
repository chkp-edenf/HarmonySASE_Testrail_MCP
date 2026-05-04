"""Section-related schemas"""

from typing import Optional, List
from pydantic import BaseModel, Field
from .common import PaginatedResponse


class Section(BaseModel):
    """TestRail Section schema"""
    id: int
    name: str
    description: Optional[str] = None
    suite_id: Optional[int] = None
    parent_id: Optional[int] = None
    display_order: Optional[int] = None
    depth: Optional[int] = None


class SectionsResponse(PaginatedResponse):
    """Response for get_sections endpoint"""
    sections: List[Section] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetSectionsInput(BaseModel):
    """Input schema for getting sections"""
    project_id: str = Field(..., description="Project ID")
    suite_id: Optional[str] = Field(None, description="Suite ID (optional, filters sections by suite)")
    limit: Optional[int] = Field(None, description="✅ The number of sections to return (default 250) — TestRail 6.7+ (API-supported)")
    offset: Optional[int] = Field(None, description="✅ Pagination offset — TestRail 6.7+ (API-supported)")


class AddSectionPayload(BaseModel):
    """Payload for creating a new section"""
    name: str = Field(..., description="Section name (required)")
    description: Optional[str] = Field(None, description="Section description")
    suite_id: Optional[int] = Field(None, description="Suite ID")
    parent_id: Optional[int] = Field(None, description="Parent section ID")
    
    class Config:
        populate_by_name = True


class UpdateSectionPayload(BaseModel):
    """Payload for updating a section"""
    name: Optional[str] = Field(None, description="Section name")
    description: Optional[str] = Field(None, description="Section description")
    
    class Config:
        populate_by_name = True


class MoveSectionPayload(BaseModel):
    """Payload for moving a section"""
    parent_id: Optional[int] = Field(None, description="New parent section ID")
    after_id: Optional[int] = Field(None, description="Section ID to place after")
    
    class Config:
        populate_by_name = True
