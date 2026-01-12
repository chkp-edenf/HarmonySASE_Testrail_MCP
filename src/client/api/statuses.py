"""Statuses API client"""

from typing import List, Dict
from .base_client import BaseAPIClient


class StatusesClient:
    """Client for TestRail Statuses API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_statuses(self) -> List[Dict]:
        """Get all available test statuses"""
        result = await self._client.get("get_statuses")
        return result if isinstance(result, list) else []
