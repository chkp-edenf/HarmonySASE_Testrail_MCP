"""Project-specific API client"""

from typing import List, Optional
from .base_client import BaseAPIClient
from ...shared.schemas import Project, ProjectsResponse


class ProjectsClient:
    """Client for TestRail Projects API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_projects(self, is_completed: Optional[bool] = None) -> dict:
        """Get all TestRail projects"""
        params = None  # Don't pass empty dict
        if is_completed is not None:
            params = {"is_completed": 1 if is_completed else 0}
        
        result = await self._client.get("get_projects", params=params)
        # Wrap raw list in dict for consistency
        if isinstance(result, list):
            return {"projects": result}
        return result
    
    async def get_project(self, project_id: int) -> dict:
        """Get a specific project by ID"""
        result = await self._client.get(f"get_project/{project_id}")
        return result
