"""Test-specific API client"""

from typing import List, Optional
from .base_client import BaseAPIClient
from ...shared.schemas.tests import Test, TestsResponse


class TestsClient:
    """Client for TestRail Tests API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_tests(
        self,
        run_id: int,
        status_id: Optional[int] = None,
        assignedto_id: Optional[int] = None,
        priority_id: Optional[int] = None,
        type_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        with_data: Optional[str] = None
    ) -> dict:
        """
        Get tests for a test run
        
        Args:
            run_id: The ID of the test run
            status_id: Filter by status ID (API-supported)
            assignedto_id: Filter by assigned user ID (client-side)
            priority_id: Filter by priority ID (client-side)
            type_id: Filter by test type ID (client-side)
            limit: Maximum number of results to return (API-supported)
            offset: Pagination offset (API-supported)
            with_data: Include test data in response (API-supported)
            
        Returns:
            Dict with tests list and pagination info
        """
        # Build API params with server-side filters
        params = {}
        if status_id is not None:
            params["status_id"] = status_id
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if with_data is not None:
            params["with_data"] = with_data  # type: ignore
        
        # Make API call
        result = await self._client.get(
            f"get_tests/{run_id}",
            params=params if params else None
        )
        
        # Apply client-side filters
        from ...server.api.utils import apply_filters
        
        client_filters = {}
        if assignedto_id is not None:
            client_filters["assignedto_id"] = assignedto_id
        if priority_id is not None:
            client_filters["priority_id"] = priority_id
        if type_id is not None:
            client_filters["type_id"] = type_id
        
        # API returns dict with pagination: {"tests": [...], "offset": 0, "limit": 250, "size": X}
        # Return full dict so handler can access tests
        if isinstance(result, dict):
            if client_filters and "tests" in result:
                result["tests"] = apply_filters(result["tests"], client_filters)
            return result
        # Fallback: wrap list in dict
        if isinstance(result, list):
            tests = apply_filters(result, client_filters) if client_filters else result
            return {"tests": tests}
        return {"tests": []}
    
    async def get_test(self, test_id: int) -> dict:
        """Get a specific test by ID"""
        result = await self._client.get(f"get_test/{test_id}")
        return result
