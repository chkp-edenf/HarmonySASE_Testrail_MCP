"""Configuration-specific API client"""

import logging
from typing import List
from ..client.base_client import BaseAPIClient
from ..schemas.configs import ConfigGroup

logger = logging.getLogger(__name__)


class ConfigsClient:
    """Client for TestRail Configurations API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_configs(self, project_id: int) -> list:
        """Get all configuration groups for a project"""
        result = await self._client.get(f"get_configs/{project_id}")
        
        # API returns list of config groups with nested configs
        return result if isinstance(result, list) else []
    
    async def add_config_group(self, project_id: int, data: dict) -> dict:
        """Create a new configuration group"""
        result = await self._client.post(f"add_config_group/{project_id}", data)
        return result
    
    async def add_config(self, config_group_id: int, data: dict) -> dict:
        """Add a configuration to a group"""
        result = await self._client.post(f"add_config/{config_group_id}", data)
        return result
