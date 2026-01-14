"""User tools registration"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from .utils import create_success_response, create_error_response, truncate_output

logger = logging.getLogger(__name__)


def format_user(user: dict) -> str:
    """Format a user object for display"""
    output = f"**User #{user.get('id')}**\n"
    output += f"  Name: {user.get('name', 'N/A')}\n"
    output += f"  Email: {user.get('email', 'N/A')}\n"
    output += f"  Active: {'Yes' if user.get('is_active') else 'No'}\n"
    
    if user.get('role'):
        output += f"  Role: {user.get('role')} (ID: {user.get('role_id', 'N/A')})\n"
    
    return output


async def handle_get_users(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all users in TestRail instance"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        # Optional filter by active status
        is_active = None
        if arguments.get("is_active") is not None:
            is_active_str = str(arguments["is_active"]).lower()
            is_active = is_active_str in ("true", "1", "yes")
        
        result = await client.users.get_users(is_active=is_active)
        users = result.get("users", [])
        
        if not users:
            response = create_success_response("No users found", {"users": [], "count": 0})
        else:
            output = f"**Users ({len(users)} total)**\n\n"
            for user in users:
                output += format_user(user) + "\n"
            
            response = create_success_response(
                f"Found {len(users)} user(s)",
                {
                    "users": users,
                    "count": len(users),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_users: {str(e)}")
        response = create_error_response("Failed to fetch users", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_user(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get specific user by ID"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        user_id = int(arguments["user_id"])
        result = await client.users.get_user(user_id)
        
        output = f"**User Details**\n\n{format_user(result)}"
        response = create_success_response(
            f"Retrieved user {user_id}",
            {"user": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_user: {str(e)}")
        response = create_error_response("Failed to fetch user", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_user_by_email(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Lookup user by email address"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        email = arguments["email"]
        
        # Basic email validation
        if "@" not in email or "." not in email:
            raise ValueError(f"Invalid email format: {email}")
        
        result = await client.users.get_user_by_email(email)
        
        output = f"**User Lookup by Email**\n\n{format_user(result)}"
        response = create_success_response(
            f"Found user with email {email}",
            {"user": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_user_by_email: {str(e)}")
        response = create_error_response("Failed to lookup user by email", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
