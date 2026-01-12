"""Test result-related schemas"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from .common import PaginatedResponse


class Result(BaseModel):
    """TestRail Result schema"""
    id: int
    test_id: Optional[int] = None
    status_id: Optional[int] = None
    created_by: Optional[int] = None
    created_on: Optional[int] = None
    assignedto_id: Optional[int] = None
    comment: Optional[str] = None
    version: Optional[str] = None
    elapsed: Optional[str] = None
    defects: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ResultsResponse(PaginatedResponse):
    """Response for get_results endpoint"""
    results: List[Result] = Field(default_factory=list)


class AddResultPayload(BaseModel):
    """Payload for adding a test result"""
    status_id: int = Field(..., description="Status ID (required)")
    comment: Optional[str] = Field(None, description="Comment/notes for the result")
    version: Optional[str] = Field(None, description="Version or build tested")
    elapsed: Optional[str] = Field(None, description="Time elapsed (e.g., '2m', '1h 30m')")
    defects: Optional[str] = Field(None, description="Comma-separated list of defect IDs")
    assignedto_id: Optional[int] = Field(None, description="User ID to assign")
    
    class Config:
        populate_by_name = True
        extra = "allow"  # Allow custom_* fields


class AddResultsPayload(BaseModel):
    """Payload for adding multiple test results"""
    results: List[Dict[str, Any]] = Field(..., description="List of result objects")
    
    class Config:
        populate_by_name = True
