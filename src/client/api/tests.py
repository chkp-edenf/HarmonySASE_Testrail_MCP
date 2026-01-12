"""Test-specific API client"""

from typing import List, Optional
from .base_client import BaseAPIClient
from ...shared.schemas.tests import Test, TestsResponse


class TestsClient:
    """Client for TestRail Tests API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_tests(self, run_id: int, status_id: Optional[int] = None) -> dict:
        """Get tests for a test run"""
        params = None
        if status_id is not None:
            params = {"status_id": status_id}
        
        result = await self._client.get(f"get_tests/{run_id}", params=params)
        
        # API returns dict with pagination: {"tests": [...], "offset": 0, "limit": 250, "size": X}
        # Return full dict so handler can access tests
        if isinstance(result, dict):
            return result
        # Fallback: wrap list in dict
        if isinstance(result, list):
            return {"tests": result}
        return {"tests": []}
    
    async def get_test(self, test_id: int) -> dict:
        """Get a specific test by ID"""
        result = await self._client.get(f"get_test/{test_id}")
        return result
