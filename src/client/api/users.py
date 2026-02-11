"""User-specific API client"""

from typing import Optional
from .base_client import BaseAPIClient


class UsersClient:
    """Client for TestRail Users API"""
    
    def __init__(self, client: BaseAPIClient):
        """Initialize with shared HTTP client"""
        self._client = client
    
    async def get_users(
        self,
        is_active: Optional[bool] = None,
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        email: Optional[str] = None
    ) -> dict:
        """
        Get all users in TestRail instance with optional filtering
        
        Args:
            is_active: Filter by active status (API-supported)
            project_id: Filter users visible in project (API-supported)
            name: Filter by user name (client-side, case-insensitive)
            email: Filter by email address (client-side, case-insensitive)
            
        Returns:
            Dict with users list
        """
        endpoint = "get_users"
        params = {}
        
        # Add API-supported filters
        if is_active is not None:
            params["is_active"] = 1 if is_active else 0
        if project_id is not None:
            params["project_id"] = project_id
        
        result = await self._client.get(endpoint, params=params if params else None)
        
        # Apply client-side filters
        from ...server.api.utils import apply_name_filter
        
        # API returns list of users directly
        if isinstance(result, list):
            users = result
        elif isinstance(result, dict) and "users" in result:
            users = result["users"]
        else:
            users = []
        
        # Apply client-side name filter if provided
        if name and users:
            users = apply_name_filter(users, name)
        
        # Apply client-side email filter if provided
        if email and users:
            email_lower = email.lower()
            users = [u for u in users if u.get("email", "").lower().find(email_lower) != -1]
        
        return {"users": users}
    
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
