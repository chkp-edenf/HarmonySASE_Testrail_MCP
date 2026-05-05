"""Suite-specific API client"""

import logging
from typing import List
from ..client.base_client import BaseAPIClient
from ..schemas.suites import Suite

logger = logging.getLogger(__name__)


class SuitesClient:
    """Client for TestRail Suites API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_suites(self, project_id: int) -> list:
        """Get all suites for a project"""
        result = await self._client.get(f"get_suites/{project_id}")
        
        # API returns dict with pagination: {"suites": [...], "offset": 0, "limit": 250, "size": 9}
        if isinstance(result, dict) and "suites" in result:
            return result["suites"]
        # Fallback for direct list response
        return result if isinstance(result, list) else []
    
    async def get_suite(self, suite_id: int) -> dict:
        """Get a specific suite by ID"""
        result = await self._client.get(f"get_suite/{suite_id}")
        return result
    
    async def add_suite(self, project_id: int, data: dict) -> dict:
        """Create a new test suite"""
        result = await self._client.post(f"add_suite/{project_id}", data)
        return result
    
    async def update_suite(self, suite_id: int, data: dict) -> dict:
        """Update an existing test suite"""
        result = await self._client.post(f"update_suite/{suite_id}", data)
        return result
    
    async def delete_suite(self, suite_id: int) -> dict:
        """Delete a test suite (soft delete)"""
        result = await self._client.post(f"delete_suite/{suite_id}", {})
        return result
