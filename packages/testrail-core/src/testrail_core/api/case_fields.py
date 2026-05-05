"""Case fields and metadata API client"""

from typing import Optional
from ..client.base_client import BaseAPIClient


class CaseFieldsClient:
    """Client for TestRail Case Fields/Metadata API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_case_fields(self) -> list:
        """Get all available case fields including custom fields"""
        result = await self._client.get("get_case_fields")
        return result if isinstance(result, list) else []
    
    async def get_case_types(self) -> list:
        """Get all available case types"""
        result = await self._client.get("get_case_types")
        return result if isinstance(result, list) else []
    
    async def get_priorities(self) -> list:
        """Get all available priorities"""
        result = await self._client.get("get_priorities")
        return result if isinstance(result, list) else []
    
    async def get_templates(self, project_id: int) -> list:
        """Get all templates for a project"""
        result = await self._client.get(f"get_templates/{project_id}")
        return result if isinstance(result, list) else []
