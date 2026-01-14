"""TestRail Milestones API client"""

from typing import Optional
from .base_client import BaseAPIClient


class MilestonesClient:
    """Client for milestone operations"""
    
    def __init__(self, client: BaseAPIClient):
        self._client = client
    
    async def get_milestones(self, project_id: int, filters: Optional[dict] = None) -> dict:
        """Get milestones for a project"""
        params = {}
        if filters:
            params.update(filters)
        
        result = await self._client.get(f"get_milestones/{project_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "milestones" in result:
            return result
        return {"milestones": result if isinstance(result, list) else []}
    
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
