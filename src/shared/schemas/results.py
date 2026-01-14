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


# Input schemas for MCP tool validation
class GetResultsInput(BaseModel):
    """Input schema for getting test results"""
    test_id: str = Field(..., description="Test ID")
    limit: Optional[str] = Field("250", description="Max results (default 250)")
    
    # Advanced filtering parameters (v1.4.0)
    created_by: Optional[str] = Field(None, description="Filter by user ID who created the result")
    created_after: Optional[str] = Field(None, description="Unix timestamp - results created after this date")
    created_before: Optional[str] = Field(None, description="Unix timestamp - results created before this date")
    status_id: Optional[str] = Field(None, description="Filter by status IDs (comma-separated for multiple)")


class GetResultsForCaseInput(BaseModel):
    """Input schema for getting results for a case in a run"""
    run_id: str = Field(..., description="Test run ID")
    case_id: str = Field(..., description="Test case ID")
    limit: Optional[str] = Field("250", description="Max results (default 250)")
    
    # Advanced filtering parameters (v1.4.0)
    created_by: Optional[str] = Field(None, description="Filter by user ID who created the result")
    created_after: Optional[str] = Field(None, description="Unix timestamp - results created after this date")
    created_before: Optional[str] = Field(None, description="Unix timestamp - results created before this date")
    status_id: Optional[str] = Field(None, description="Filter by status IDs (comma-separated for multiple)")


class GetResultsForRunInput(BaseModel):
    """Input schema for getting all results for a run"""
    run_id: str = Field(..., description="Test run ID")
    limit: Optional[str] = Field("250", description="Max results (default 250)")
    
    # Advanced filtering parameters (v1.4.0)
    created_by: Optional[str] = Field(None, description="Filter by user ID who created the result")
    created_after: Optional[str] = Field(None, description="Unix timestamp - results created after this date")
    created_before: Optional[str] = Field(None, description="Unix timestamp - results created before this date")
    status_id: Optional[str] = Field(None, description="Filter by status IDs (comma-separated for multiple)")


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
