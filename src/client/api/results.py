"""TestRail Results API client"""

from typing import Optional
from .base_client import BaseAPIClient


class ResultsClient:
    """Client for test result operations"""
    
    def __init__(self, client: BaseAPIClient):
        self._client = client
    
    async def get_results(
        self,
        test_id: int,
        limit: int = 250,
        # Advanced filtering parameters (v1.4.0)
        created_by: Optional[int] = None,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
        status_id: Optional[str] = None
    ) -> dict:
        """Get results for a test with optional advanced filtering"""
        params = {"limit": limit}
        
        # Add advanced filter parameters if provided
        if created_by is not None:
            params["created_by"] = created_by
        if created_after is not None:
            params["created_after"] = created_after
        if created_before is not None:
            params["created_before"] = created_before
        if status_id is not None:
            params["status_id"] = status_id
        
        result = await self._client.get(f"get_results/{test_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "results" in result:
            return result
        return {"results": result if isinstance(result, list) else []}
    
    async def get_results_for_case(
        self,
        run_id: int,
        case_id: int,
        limit: int = 250,
        # Advanced filtering parameters (v1.4.0)
        created_by: Optional[int] = None,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
        status_id: Optional[str] = None
    ) -> dict:
        """Get results for a case in a run with optional advanced filtering"""
        params = {"limit": limit}
        
        # Add advanced filter parameters if provided
        if created_by is not None:
            params["created_by"] = created_by
        if created_after is not None:
            params["created_after"] = created_after
        if created_before is not None:
            params["created_before"] = created_before
        if status_id is not None:
            params["status_id"] = status_id
        
        result = await self._client.get(f"get_results_for_case/{run_id}/{case_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "results" in result:
            return result
        return {"results": result if isinstance(result, list) else []}
    
    async def get_results_for_run(
        self,
        run_id: int,
        limit: int = 250,
        # Advanced filtering parameters (v1.4.0)
        created_by: Optional[int] = None,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
        status_id: Optional[str] = None
    ) -> dict:
        """Get all results for a run with optional advanced filtering"""
        params = {"limit": limit}
        
        # Add advanced filter parameters if provided
        if created_by is not None:
            params["created_by"] = created_by
        if created_after is not None:
            params["created_after"] = created_after
        if created_before is not None:
            params["created_before"] = created_before
        if status_id is not None:
            params["status_id"] = status_id
        
        result = await self._client.get(f"get_results_for_run/{run_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "results" in result:
            return result
        return {"results": result if isinstance(result, list) else []}
    
    async def add_result(self, test_id: int, data: dict) -> dict:
        """Add a result for a test"""
        return await self._client.post(f"add_result/{test_id}", data)
    
    async def add_results(self, run_id: int, data: dict) -> dict:
        """Add results for multiple tests in a run"""
        return await self._client.post(f"add_results/{run_id}", data)
