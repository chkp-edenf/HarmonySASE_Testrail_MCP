"""Test case-specific API client"""

from typing import Optional, Dict, Any
from .base_client import BaseAPIClient
from ...shared.schemas import TestCase, CasesResponse, AddCasePayload


class CasesClient:
    """Client for TestRail Cases API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_cases(
        self,
        project_id: int,
        suite_id: Optional[int] = None,
        limit: int = 250
    ) -> dict:
        """Get test cases for a project/suite"""
        endpoint = f"get_cases/{project_id}"
        params = {"limit": limit}
        
        if suite_id is not None:
            params["suite_id"] = suite_id
        
        result = await self._client.get(endpoint, params=params)
        
        # API returns dict with pagination: {"cases": [...], "offset": 0, "limit": 250, "size": X}
        # Return full dict so handler can access cases
        if isinstance(result, dict):
            return result
        # Fallback: wrap list in dict
        if isinstance(result, list):
            return {"cases": result}
        return {"cases": []}
    
    async def get_case(self, case_id: int) -> dict:
        """Get a specific test case by ID"""
        result = await self._client.get(f"get_case/{case_id}")
        return result
    
    async def add_case(self, section_id: int, data: dict) -> dict:
        """Create a new test case in a section"""
        result = await self._client.post(f"add_case/{section_id}", data)
        return result
    
    async def update_case(self, case_id: int, data: dict) -> dict:
        """Update an existing test case"""
        result = await self._client.post(f"update_case/{case_id}", data)
        return result
    
    async def delete_case(self, case_id: int) -> dict:
        """Delete a test case (soft delete)"""
        result = await self._client.post(f"delete_case/{case_id}", {})
        return result
    
    async def get_case_history(self, case_id: int) -> dict:
        """Get the change history for a test case"""
        result = await self._client.get(f"get_history_for_case/{case_id}")
        return result
    
    async def copy_cases_to_section(self, section_id: int, data: dict) -> dict:
        """Copy test cases to a different section"""
        result = await self._client.post(f"copy_cases_to_section/{section_id}", data)
        return result
    
    async def move_cases_to_section(self, section_id: int, data: dict) -> dict:
        """Move test cases to a different section"""
        result = await self._client.post(f"move_cases_to_section/{section_id}", data)
        return result
    
    async def update_cases(self, suite_id: int, data: dict) -> dict:
        """Bulk update test cases"""
        result = await self._client.post(f"update_cases/{suite_id}", data)
        return result
    
    async def delete_cases(self, suite_id: int, data: dict) -> dict:
        """Bulk delete test cases (soft delete)"""
        result = await self._client.post(f"delete_cases/{suite_id}", data)
        return result
