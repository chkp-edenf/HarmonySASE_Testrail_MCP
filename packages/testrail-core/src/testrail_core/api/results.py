"""TestRail Results API client"""

from typing import Optional, Union
from ..client.base_client import BaseAPIClient


class ResultsClient:
    """Client for test result operations"""
    
    def __init__(self, client: BaseAPIClient):
        self._client = client
    
    async def get_results(
        self,
        test_id: int,
        limit: int = 250,
        offset: Optional[int] = None,
        # Advanced filtering parameters (v1.4.0)
        created_by: Optional[int] = None,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
        status_id: Optional[Union[int, str]] = None
    ) -> dict:
        """
        Get results for a test with optional advanced filtering
        
        Args:
            test_id: The ID of the test
            limit: Maximum number of results to return (default: 250)
            offset: Pagination offset (API-supported)
            created_by: Filter by creator user ID(s) (API-supported)
            created_after: Filter results created after timestamp (API-supported)
            created_before: Filter results created before timestamp (API-supported)
            status_id: Filter by status ID(s) (API-supported)
            
        Returns:
            Dict with results list and pagination info
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
        if status_id is not None:
            params["status_id"] = status_id  # type: ignore
        
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
        offset: Optional[int] = None,
        # Advanced filtering parameters (v1.4.0)
        created_by: Optional[int] = None,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
        status_id: Optional[Union[int, str]] = None
    ) -> dict:
        """
        Get results for a case in a run with optional advanced filtering
        
        Args:
            run_id: The ID of the run
            case_id: The ID of the case
            limit: Maximum number of results to return (default: 250)
            offset: Pagination offset (API-supported)
            created_by: Filter by creator user ID(s) (API-supported)
            created_after: Filter results created after timestamp (API-supported)
            created_before: Filter results created before timestamp (API-supported)
            status_id: Filter by status ID(s) (API-supported)
            
        Returns:
            Dict with results list and pagination info
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
        if status_id is not None:
            params["status_id"] = status_id  # type: ignore
        
        result = await self._client.get(f"get_results_for_case/{run_id}/{case_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "results" in result:
            return result
        return {"results": result if isinstance(result, list) else []}
    
    async def get_results_for_run(
        self,
        run_id: int,
        limit: int = 250,
        offset: Optional[int] = None,
        # Advanced filtering parameters (v1.4.0)
        created_by: Optional[int] = None,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
        status_id: Optional[Union[int, str]] = None,
        defects_filter: Optional[str] = None
    ) -> dict:
        """
        Get all results for a run with optional advanced filtering
        
        Args:
            run_id: The ID of the run
            limit: Maximum number of results to return (default: 250)
            offset: Pagination offset (API-supported)
            created_by: Filter by creator user ID(s) (API-supported)
            created_after: Filter results created after timestamp (API-supported)
            created_before: Filter results created before timestamp (API-supported)
            status_id: Filter by status ID(s) (API-supported)
            defects_filter: Filter by single defect ID (e.g., TR-1, 4291) (API-supported)
            
        Returns:
            Dict with results list and pagination info
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
        if status_id is not None:
            params["status_id"] = status_id  # type: ignore
        if defects_filter is not None:
            params["defects_filter"] = defects_filter  # type: ignore
        
        result = await self._client.get(f"get_results_for_run/{run_id}", params=params)
        
        # Handle pagination
        if isinstance(result, dict) and "results" in result:
            return result
        return {"results": result if isinstance(result, list) else []}
    
    async def add_result(self, test_id: int, data: dict) -> dict:
        """Add a result for a test"""
        return await self._client.post(f"add_result/{test_id}", data)
    
    async def add_result_for_case(self, run_id: int, case_id: int, data: dict) -> dict:
        """
        Add a result for a case in a run
        
        Alternative to add_result that doesn't require test_id.
        Useful when you know the run and case but don't have the test_id.
        
        Args:
            run_id: The ID of the test run
            case_id: The ID of the test case
            data: Result data including status_id and optional fields
            
        Returns:
            The created result object
        """
        return await self._client.post(f"add_result_for_case/{run_id}/{case_id}", data)
    
    async def add_results(self, run_id: int, data: dict) -> dict:
        """Add results for multiple tests in a run"""
        return await self._client.post(f"add_results/{run_id}", data)
    
    async def add_results_for_cases(self, run_id: int, data: dict) -> dict:
        """
        Add results for multiple cases in a run
        
        Bulk version of add_result_for_case. Submits multiple results for cases
        in a run using case IDs instead of test IDs.
        
        Args:
            run_id: The ID of the test run
            data: Dict with 'results' key containing list of result objects,
                  each with case_id and result fields
                  
        Returns:
            List of created result objects
        """
        return await self._client.post(f"add_results_for_cases/{run_id}", data)
