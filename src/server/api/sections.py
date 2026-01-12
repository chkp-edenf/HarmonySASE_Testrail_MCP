"""Section handler functions"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from .utils import create_success_response, create_error_response, format_section, truncate_output

logger = logging.getLogger(__name__)


async def handle_get_sections(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all sections for a project/suite"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        suite_id = int(arguments["suite_id"]) if arguments.get("suite_id") else None
        
        result = await client.sections.get_sections(project_id, suite_id)
        sections = result.get("sections", [])
        
        if not sections:
            response = create_success_response(
                "No sections found",
                {"sections": [], "count": 0}
            )
        else:
            output = f"**Sections for Project {project_id}"
            if suite_id:
                output += f" (Suite {suite_id})"
            output += "**\n\n"
            
            for section in sections:
                output += format_section(section) + "\n"
            
            response = create_success_response(
                f"Found {len(sections)} section(s)",
                {
                    "sections": sections,
                    "count": len(sections),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_sections: {str(e)}")
        response = create_error_response("Failed to fetch sections", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_section(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get details of a specific section"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        section_id = int(arguments["section_id"])
        result = await client.sections.get_section(section_id)
        
        output = f"**Section Details**\n\n{format_section(result)}"
        response = create_success_response(
            f"Retrieved section {section_id}",
            {"section": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_section: {str(e)}")
        response = create_error_response("Failed to fetch section", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_section(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Create a new section"""
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
        if arguments.get("suite_id"):
            data["suite_id"] = int(arguments["suite_id"])
        if arguments.get("parent_id"):
            data["parent_id"] = int(arguments["parent_id"])
        
        result = await client.sections.add_section(project_id, data)
        
        output = f"**Section Created**\n\n{format_section(result)}"
        response = create_success_response(
            f"Successfully created section '{result.get('name')}'",
            {"section": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_section: {str(e)}")
        response = create_error_response("Failed to create section", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_update_section(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Update an existing section"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        section_id = int(arguments["section_id"])
        data = {}
        
        # Optional fields
        if arguments.get("name"):
            data["name"] = arguments["name"]
        if arguments.get("description"):
            data["description"] = arguments["description"]
        
        if not data:
            response = create_error_response("No update fields provided", Exception("No fields specified"))
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        result = await client.sections.update_section(section_id, data)
        
        output = f"**Section Updated**\n\n{format_section(result)}"
        response = create_success_response(
            f"Successfully updated section {section_id}",
            {"section": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in update_section: {str(e)}")
        response = create_error_response("Failed to update section", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_section(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Delete a section (soft delete)"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        section_id = int(arguments["section_id"])
        await client.sections.delete_section(section_id)
        
        response = create_success_response(
            f"Successfully deleted section {section_id}",
            {"section_id": section_id, "formatted": f"Section {section_id} has been deleted"}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in delete_section: {str(e)}")
        response = create_error_response("Failed to delete section", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_move_section(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Move section to different parent or change display order"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        section_id = int(arguments["section_id"])
        data = {}
        
        # Optional fields for moving
        if arguments.get("parent_id"):
            data["parent_id"] = int(arguments["parent_id"])
        if arguments.get("after_id"):
            data["after_id"] = int(arguments["after_id"])
        
        if not data:
            response = create_error_response("No move parameters provided", Exception("Specify parent_id or after_id"))
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        result = await client.sections.move_section(section_id, data)
        
        output = f"**Section Moved**\n\n{format_section(result)}"
        response = create_success_response(
            f"Successfully moved section {section_id}",
            {"section": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in move_section: {str(e)}")
        response = create_error_response("Failed to move section", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
