"""TestRail Runs API client"""

from typing import Optional
from .base_client import BaseAPIClient


class RunsClient:
    """Client for test run operations"""
    
    def __init__(self, client: BaseAPIClient):
        self._client = client
    
    async def get_runs(self, project_id: int, limit: int = 250, filters: Optional[dict] = None) -> dict:
        """Get test runs for a project"""
        params = {"limit": limit}
        if filters:
            params.update(filters)
        
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
