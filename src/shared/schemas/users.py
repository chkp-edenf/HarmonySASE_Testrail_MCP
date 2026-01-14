"""Schema definitions for user-related operations"""

from typing import Optional
from pydantic import BaseModel, Field


class GetUsersInput(BaseModel):
    """Input for get_users tool - list all users"""
    is_active: Optional[bool] = Field(
        None,
        description="Filter by active status (true=active, false=inactive). Omit to get all users."
    )


class GetUserInput(BaseModel):
    """Input for get_user tool - get user by ID"""
    user_id: str = Field(
        ...,
        description="User ID (numeric identifier)"
    )


class GetUserByEmailInput(BaseModel):
    """Input for get_user_by_email tool - lookup user by email"""
    email: str = Field(
        ...,
        description="Email address of the user to lookup"
    )


class UserOutput(BaseModel):
    """Output schema for user objects"""
    id: int = Field(..., description="User ID")
    name: str = Field(..., description="Full name of the user")
    email: str = Field(..., description="Email address")
    is_active: bool = Field(..., description="Whether the user is active")
    role_id: Optional[int] = Field(None, description="Role ID")
    role: Optional[str] = Field(None, description="Role name")
    
    class Config:
        extra = "allow"  # Allow additional fields from API
