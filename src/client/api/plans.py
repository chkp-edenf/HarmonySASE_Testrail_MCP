"""TestRail Plans API client"""

from typing import Optional
from .base_client import BaseAPIClient


class PlansClient:
    """Client for test plan operations"""
    
    def __init__(self, client: BaseAPIClient):
        self._client = client
    
    async def get_plans(self, project_id: int, limit: int = 250, offset: int = 0, filters: Optional[dict] = None) -> dict:
        """Get test plans for a project"""
        params = {"limit": limit, "offset": offset}
        if filters:
            params.update(filters)
        
        result = await self._client.get(f"get_plans/{project_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "plans" in result:
            return result
        return {"plans": result if isinstance(result, list) else []}
    
    async def get_plan(self, plan_id: int) -> dict:
        """Get details of a specific test plan"""
        return await self._client.get(f"get_plan/{plan_id}")
    
    async def add_plan(self, project_id: int, data: dict) -> dict:
        """Create a new test plan"""
        return await self._client.post(f"add_plan/{project_id}", data)
    
    async def update_plan(self, plan_id: int, data: dict) -> dict:
        """Update an existing test plan"""
        return await self._client.post(f"update_plan/{plan_id}", data)
    
    async def close_plan(self, plan_id: int) -> dict:
        """Close a test plan"""
        return await self._client.post(f"close_plan/{plan_id}", {})
    
    async def delete_plan(self, plan_id: int) -> dict:
        """Delete a test plan"""
        return await self._client.post(f"delete_plan/{plan_id}", {})
    
    async def add_plan_entry(self, plan_id: int, data: dict) -> dict:
        """Add a test run/entry to an existing plan
        
        API: POST /add_plan_entry/{plan_id}
        
        Args:
            plan_id: Plan ID to add entry to
            data: Entry data including suite_id, name, config_ids, case_ids
        
        Returns:
            Updated plan with new entry
        """
        return await self._client.post(f"add_plan_entry/{plan_id}", data)
    
    async def update_plan_entry(self, plan_id: int, entry_id: str, data: dict) -> dict:
        """Update an existing plan entry
        
        API: POST /update_plan_entry/{plan_id}/{entry_id}
        
        Args:
            plan_id: Plan ID containing the entry
            entry_id: Entry ID to update
            data: Updated entry data
        
        Returns:
            Updated plan entry
        """
        return await self._client.post(f"update_plan_entry/{plan_id}/{entry_id}", data)
    
    async def delete_plan_entry(self, plan_id: int, entry_id: str) -> dict:
        """Remove an entry from a plan
        
        API: POST /delete_plan_entry/{plan_id}/{entry_id}
        
        Args:
            plan_id: Plan ID containing the entry
            entry_id: Entry ID to delete
        
        Returns:
            Empty dict on success
        """
        return await self._client.post(f"delete_plan_entry/{plan_id}/{entry_id}", {})