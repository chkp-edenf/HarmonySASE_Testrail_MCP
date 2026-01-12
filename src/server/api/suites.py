"""Suite tools registration"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from .utils import create_success_response, create_error_response, format_suite, truncate_output

logger = logging.getLogger(__name__)


async def handle_get_suites(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all test suites for a project"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        result = await client.suites.get_suites(project_id)
        
        if not result:
            response = create_success_response(
                f"No suites found for project {project_id}",
                {"suites": [], "count": 0}
            )
        else:
            output = f"**Test Suites for Project {project_id}**\n\n"
            for suite in result:
                output += format_suite(suite) + "\n"
            
            response = create_success_response(
                f"Found {len(result)} suite(s)",
                {
                    "suites": result,
                    "count": len(result),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_suites: {str(e)}")
        response = create_error_response("Failed to fetch suites", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_suite(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get details of a specific test suite"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        suite_id = int(arguments["suite_id"])
        result = await client.suites.get_suite(suite_id)
        
        output = f"**Suite Details**\n\n{format_suite(result)}"
        response = create_success_response(
            f"Retrieved suite {suite_id}",
            {"suite": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_suite: {str(e)}")
        response = create_error_response("Failed to fetch suite", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_suite(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Create a new test suite"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        
        # Validate required fields
        if not arguments.get("name"):
            raise ValueError("Missing required field: name")
        
        data = {"name": arguments["name"]}
        
        # Optional fields
        if arguments.get("description"):
            data["description"] = arguments["description"]
        
        result = await client.suites.add_suite(project_id, data)
        
        output = f"**Suite Created**\n\n{format_suite(result)}"
        response = create_success_response(
            f"Successfully created suite '{result.get('name')}'",
            {"suite": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_suite: {str(e)}")
        response = create_error_response("Failed to create suite", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_update_suite(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Update an existing test suite"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        suite_id = int(arguments["suite_id"])
        data = {}
        
        # Optional fields
        if arguments.get("name"):
            data["name"] = arguments["name"]
        if arguments.get("description"):
            data["description"] = arguments["description"]
        
        if not data:
            response = create_error_response("No update fields provided", None)
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        result = await client.suites.update_suite(suite_id, data)
        
        output = f"**Suite Updated**\n\n{format_suite(result)}"
        response = create_success_response(
            f"Successfully updated suite {suite_id}",
            {"suite": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in update_suite: {str(e)}")
        response = create_error_response("Failed to update suite", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_suite(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Delete a test suite (soft delete)"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        suite_id = int(arguments["suite_id"])
        await client.suites.delete_suite(suite_id)
        
        response = create_success_response(
            f"Successfully deleted suite {suite_id}",
            {"suite_id": suite_id, "formatted": f"Suite {suite_id} has been deleted"}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in delete_suite: {str(e)}")
        response = create_error_response("Failed to delete suite", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]