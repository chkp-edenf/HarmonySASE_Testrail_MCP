"""Milestone handler functions"""

import json
import logging
from datetime import datetime
from mcp.types import TextContent
from ...client.api import TestRailClient
from .utils import create_success_response, create_error_response, truncate_output

logger = logging.getLogger(__name__)


def format_milestone(milestone: dict) -> str:
    """Format a single milestone for display"""
    output = f"**{milestone.get('name', 'Unnamed')}** (ID: {milestone.get('id')})\n"
    output += f"  └─ Project ID: {milestone.get('project_id', 'N/A')}\n"
    
    # Parent milestone
    parent_id = milestone.get('parent_id')
    if parent_id:
        output += f"  └─ Parent Milestone ID: {parent_id}\n"
    
    # Status flags
    is_started = milestone.get('is_started', False)
    is_completed = milestone.get('is_completed', False)
    output += f"  └─ Status: "
    if is_completed:
        output += "✓ Completed"
    elif is_started:
        output += "▶ In Progress"
    else:
        output += "○ Not Started"
    output += "\n"
    
    # Dates
    start_on = milestone.get('start_on')
    if start_on:
        start_date = datetime.fromtimestamp(start_on).strftime('%Y-%m-%d')
        output += f"  └─ Start Date: {start_date}\n"
    
    due_on = milestone.get('due_on')
    if due_on:
        due_date = datetime.fromtimestamp(due_on).strftime('%Y-%m-%d')
        output += f"  └─ Due Date: {due_date}\n"
    
    # Description
    description = milestone.get('description')
    if description:
        desc_preview = description[:80] + "..." if len(description) > 80 else description
        output += f"  └─ Description: {desc_preview}\n"
    
    return output


async def handle_get_milestones(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get milestones for a project"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        
        # Optional filters
        filters = {}
        if arguments.get("is_completed") is not None:
            filters["is_completed"] = 1 if arguments["is_completed"].lower() == "true" else 0
        if arguments.get("is_started") is not None:
            filters["is_started"] = 1 if arguments["is_started"].lower() == "true" else 0
        
        result = await client.milestones.get_milestones(project_id, filters if filters else None)
        milestones = result.get("milestones", [])
        
        if not milestones:
            response = create_success_response(
                "No milestones found",
                {"milestones": [], "count": 0}
            )
        else:
            output = f"**Milestones for Project {project_id}**\n\n"
            for milestone in milestones:
                output += format_milestone(milestone) + "\n"
            
            response = create_success_response(
                f"Found {len(milestones)} milestone(s)",
                {
                    "milestones": milestones,
                    "count": len(milestones),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_milestones: {str(e)}")
        response = create_error_response("Failed to fetch milestones", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_milestone(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get details of a specific milestone"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        milestone_id = int(arguments["milestone_id"])
        result = await client.milestones.get_milestone(milestone_id)
        
        output = f"**Milestone Details**\n\n{format_milestone(result)}"
        
        # Add full description if available
        description = result.get('description')
        if description and len(description) > 80:
            output += f"\n**Full Description:**\n{description}\n"
        
        response = create_success_response(
            f"Retrieved milestone {milestone_id}",
            {"milestone": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_milestone: {str(e)}")
        response = create_error_response("Failed to fetch milestone", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_milestone(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Create a new milestone"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        
        # Required fields
        if not arguments.get("name"):
            raise ValueError("Missing required field: name")
        
        data = {"name": arguments["name"]}
        
        # Optional fields
        if arguments.get("description"):
            data["description"] = arguments["description"]
        if arguments.get("due_on"):
            data["due_on"] = int(arguments["due_on"])
        if arguments.get("start_on"):
            data["start_on"] = int(arguments["start_on"])
        if arguments.get("parent_id"):
            data["parent_id"] = int(arguments["parent_id"])
        
        result = await client.milestones.add_milestone(project_id, data)
        
        output = f"**Milestone Created**\n\n{format_milestone(result)}"
        response = create_success_response(
            f"Successfully created milestone '{result.get('name')}'",
            {"milestone": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_milestone: {str(e)}")
        response = create_error_response("Failed to create milestone", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_update_milestone(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Update an existing milestone"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        milestone_id = int(arguments["milestone_id"])
        data = {}
        
        # Optional fields
        if arguments.get("name"):
            data["name"] = arguments["name"]
        if arguments.get("description"):
            data["description"] = arguments["description"]
        if arguments.get("due_on"):
            data["due_on"] = int(arguments["due_on"])
        if arguments.get("start_on"):
            data["start_on"] = int(arguments["start_on"])
        if arguments.get("parent_id"):
            data["parent_id"] = int(arguments["parent_id"])
        if arguments.get("is_completed") is not None:
            data["is_completed"] = arguments["is_completed"].lower() == "true"
        if arguments.get("is_started") is not None:
            data["is_started"] = arguments["is_started"].lower() == "true"
        
        if not data:
            response = create_error_response("No update fields provided", Exception("No fields specified"))
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        result = await client.milestones.update_milestone(milestone_id, data)
        
        output = f"**Milestone Updated**\n\n{format_milestone(result)}"
        response = create_success_response(
            f"Successfully updated milestone {milestone_id}",
            {"milestone": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in update_milestone: {str(e)}")
        response = create_error_response("Failed to update milestone", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_milestone(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Delete a milestone"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        milestone_id = int(arguments["milestone_id"])
        await client.milestones.delete_milestone(milestone_id)
        
        response = create_success_response(
            f"Successfully deleted milestone {milestone_id}",
            {"milestone_id": milestone_id, "formatted": f"Milestone {milestone_id} has been deleted"}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in delete_milestone: {str(e)}")
        response = create_error_response("Failed to delete milestone", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
