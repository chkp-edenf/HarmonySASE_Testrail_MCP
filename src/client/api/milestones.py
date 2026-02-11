"""TestRail Milestones API client"""

from typing import Optional
from .base_client import BaseAPIClient


class MilestonesClient:
    """Client for milestone operations"""
    
    def __init__(self, client: BaseAPIClient):
        self._client = client
    
    async def get_milestones(
        self,
        project_id: int,
        is_completed: Optional[bool] = None,
        is_started: Optional[bool] = None,
        name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> dict:
        """
        Get milestones for a project with optional filtering
        
        Args:
            project_id: The ID of the project
            is_completed: Filter by completion status (API-supported)
            is_started: Filter by started status (API-supported)
            name: Filter by milestone name (client-side, case-insensitive)
            limit: Maximum number of results to return (API-supported, TestRail 6.7+)
            offset: Pagination offset (API-supported, TestRail 6.7+)
            
        Returns:
            Dict with milestones list
        """
        params = {}
        
        # Add API-supported filters
        if is_completed is not None:
            params["is_completed"] = 1 if is_completed else 0
        if is_started is not None:
            params["is_started"] = 1 if is_started else 0
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        
        result = await self._client.get(
            f"get_milestones/{project_id}",
            params=params if params else None
        )
        
        # Apply client-side name filter
        from ...server.api.utils import apply_name_filter
        
        # Handle pagination
        if isinstance(result, dict) and "milestones" in result:
            if name:
                result["milestones"] = apply_name_filter(result["milestones"], name)
            return result
        
        milestones = result if isinstance(result, list) else []
        if name and milestones:
            milestones = apply_name_filter(milestones, name)
        
        return {"milestones": milestones}
    
    async def get_milestone(self, milestone_id: int) -> dict:
        """Get details of a specific milestone"""
        return await self._client.get(f"get_milestone/{milestone_id}")
    
    async def add_milestone(self, project_id: int, data: dict) -> dict:
        """Create a new milestone"""
        return await self._client.post(f"add_milestone/{project_id}", data)
    
    async def update_milestone(self, milestone_id: int, data: dict) -> dict:
        """Update an existing milestone"""
        return await self._client.post(f"update_milestone/{milestone_id}", data)
    
    async def delete_milestone(self, milestone_id: int) -> dict:
        """Delete a milestone"""
        return await self._client.post(f"delete_milestone/{milestone_id}", {})
