"""TestRail Runs API client"""

from typing import Optional
from .base_client import BaseAPIClient


class RunsClient:
    """Client for test run operations"""
    
    def __init__(self, client: BaseAPIClient):
        self._client = client
    
    async def get_runs(
        self,
        project_id: int,
        limit: int = 250,
        # Advanced filtering parameters (v1.4.0)
        created_by: Optional[int] = None,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
        milestone_id: Optional[str] = None,
        is_completed: Optional[bool] = None
    ) -> dict:
        """Get test runs for a project with optional advanced filtering"""
        params = {"limit": limit}
        
        # Add advanced filter parameters if provided
        if created_by is not None:
            params["created_by"] = created_by
        if created_after is not None:
            params["created_after"] = created_after
        if created_before is not None:
            params["created_before"] = created_before
        if milestone_id is not None:
            params["milestone_id"] = milestone_id
        if is_completed is not None:
            params["is_completed"] = 1 if is_completed else 0
        
        result = await self._client.get(f"get_runs/{project_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "runs" in result:
            return result
        return {"runs": result if isinstance(result, list) else []}
    
    async def get_run(self, run_id: int) -> dict:
        """Get details of a specific test run"""
        return await self._client.get(f"get_run/{run_id}")
    
    async def add_run(self, project_id: int, data: dict) -> dict:
        """Create a new test run"""
        return await self._client.post(f"add_run/{project_id}", data)
    
    async def update_run(self, run_id: int, data: dict) -> dict:
        """Update an existing test run"""
        return await self._client.post(f"update_run/{run_id}", data)
    
    async def close_run(self, run_id: int) -> dict:
        """Close a test run"""
        return await self._client.post(f"close_run/{run_id}", {})
    
    async def delete_run(self, run_id: int) -> dict:
        """Delete a test run"""
        return await self._client.post(f"delete_run/{run_id}", {})
