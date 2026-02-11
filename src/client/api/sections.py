"""Section-specific API client"""

from typing import Optional
from .base_client import BaseAPIClient


class SectionsClient:
    """Client for TestRail Sections API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_sections(
        self,
        project_id: int,
        suite_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> dict:
        """
        Get all sections for a project/suite
        
        Args:
            project_id: The ID of the project
            suite_id: Filter sections by suite ID (optional)
            limit: Maximum number of results to return (API-supported, TestRail 6.7+)
            offset: Pagination offset (API-supported, TestRail 6.7+)
            
        Returns:
            Dict with sections list and pagination info
        """
        endpoint = f"get_sections/{project_id}"
        params = {}
        
        if suite_id is not None:
            params["suite_id"] = suite_id
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        
        result = await self._client.get(endpoint, params=params if params else None)
        
        # API returns dict with pagination: {"sections": [...], "offset": 0, "limit": 250}
        if isinstance(result, dict) and "sections" in result:
            return result
        # Fallback: wrap list in dict
        if isinstance(result, list):
            return {"sections": result}
        return {"sections": []}
    
    async def get_section(self, section_id: int) -> dict:
        """Get a specific section by ID"""
        result = await self._client.get(f"get_section/{section_id}")
        return result
    
    async def add_section(self, project_id: int, data: dict) -> dict:
        """Create a new section"""
        result = await self._client.post(f"add_section/{project_id}", data)
        return result
    
    async def update_section(self, section_id: int, data: dict) -> dict:
        """Update an existing section"""
        result = await self._client.post(f"update_section/{section_id}", data)
        return result
    
    async def delete_section(self, section_id: int) -> dict:
        """Delete a section (soft delete)"""
        result = await self._client.post(f"delete_section/{section_id}", {})
        return result
    
    async def move_section(self, section_id: int, data: dict) -> dict:
        """Move section to different parent or change display order"""
        result = await self._client.post(f"move_section/{section_id}", data)
        return result
