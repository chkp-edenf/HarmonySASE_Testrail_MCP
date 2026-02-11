"""TestRail Runs API client"""

from typing import Optional, Union
from .base_client import BaseAPIClient


class RunsClient:
    """Client for test run operations"""
    
    def __init__(self, client: BaseAPIClient):
        self._client = client
    
    async def get_runs(
        self,
        project_id: int,
        limit: int = 250,
        offset: Optional[int] = None,
        # Advanced filtering parameters (v1.4.0)
        created_by: Optional[int] = None,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
        suite_id: Optional[Union[int, str]] = None,
        milestone_id: Optional[Union[int, str]] = None,
        is_completed: Optional[bool] = None,
        refs_filter: Optional[str] = None
    ) -> dict:
        """
        Get test runs for a project with optional advanced filtering
        
        Args:
            project_id: The ID of the project
            limit: Maximum number of results to return (default: 250)
            offset: Pagination offset (API-supported)
            created_by: Filter by creator user ID(s) (API-supported)
            created_after: Filter runs created after timestamp (API-supported)
            created_before: Filter runs created before timestamp (API-supported)
            suite_id: Filter by suite ID(s) (API-supported)
            milestone_id: Filter by milestone ID(s) (API-supported)
            is_completed: Filter by completion status (API-supported)
            refs_filter: Filter by single reference ID (e.g., TR-a, 4291) (API-supported)
            
        Returns:
            Dict with runs list and pagination info
        """
        params = {"limit": limit}
        
        if offset is not None:
            params["offset"] = offset
        
        # Add advanced filter parameters if provided
        if created_by is not None:
            params["created_by"] = created_by
        if created_after is not None:
            params["created_after"] = created_after
        if created_before is not None:
            params["created_before"] = created_before
        if suite_id is not None:
            params["suite_id"] = suite_id  # type: ignore
        if milestone_id is not None:
            params["milestone_id"] = milestone_id  # type: ignore
        if is_completed is not None:
            params["is_completed"] = 1 if is_completed else 0
        if refs_filter is not None:
            params["refs_filter"] = refs_filter  # type: ignore
        
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
