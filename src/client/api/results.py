"""TestRail Results API client"""

from typing import Optional
from .base_client import BaseAPIClient


class ResultsClient:
    """Client for test result operations"""
    
    def __init__(self, client: BaseAPIClient):
        self._client = client
    
    async def get_results(self, test_id: int, limit: int = 250) -> dict:
        """Get results for a test"""
        params = {"limit": limit}
        result = await self._client.get(f"get_results/{test_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "results" in result:
            return result
        return {"results": result if isinstance(result, list) else []}
    
    async def get_results_for_case(self, run_id: int, case_id: int, limit: int = 250) -> dict:
        """Get results for a case in a run"""
        params = {"limit": limit}
        result = await self._client.get(f"get_results_for_case/{run_id}/{case_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "results" in result:
            return result
        return {"results": result if isinstance(result, list) else []}
    
    async def get_results_for_run(self, run_id: int, limit: int = 250) -> dict:
        """Get all results for a run"""
        params = {"limit": limit}
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
