"""User-specific API client"""

from typing import Optional
from .base_client import BaseAPIClient


class UsersClient:
    """Client for TestRail Users API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_users(self, is_active: Optional[bool] = None) -> dict:
        """Get all users in TestRail instance"""
        endpoint = "get_users"
        params = {}
        
        # Optional filter by active status
        if is_active is not None:
            params["is_active"] = 1 if is_active else 0
        
        result = await self._client.get(endpoint, params=params if params else None)
        
        # API returns list of users directly
        if isinstance(result, list):
            return {"users": result}
        # Fallback: already a dict
        if isinstance(result, dict):
            return result
        return {"users": []}
    
    async def get_user(self, user_id: int) -> dict:
        """Get specific user by ID"""
        result = await self._client.get(f"get_user/{user_id}")
        return result
    
    async def get_user_by_email(self, email: str) -> dict:
        """Lookup user by email address"""
        endpoint = "get_user_by_email"
        params = {"email": email}
        result = await self._client.get(endpoint, params=params)
        return result
