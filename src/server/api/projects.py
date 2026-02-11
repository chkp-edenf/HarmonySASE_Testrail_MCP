"""Project handler functions"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from ...shared.schemas.projects import GetProjectsInput
from .utils import create_success_response, create_error_response, format_project, truncate_output

logger = logging.getLogger(__name__)


async def handle_get_projects(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all TestRail projects"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        # Validate and parse input
        input_data = GetProjectsInput(**arguments)
        
        is_completed = input_data.is_completed
        limit = input_data.limit
        offset = input_data.offset
        
        result = await client.projects.get_projects(
            is_completed=is_completed,
            limit=limit,
            offset=offset
        )
        projects = result.get("projects", [])
        
        if not projects:
            response = create_success_response(
                "No projects found",
                {"projects": [], "count": 0}
            )
        else:
            output = "**TestRail Projects**\n\n"
            for project in projects:
                output += format_project(project) + "\n"
            
            response = create_success_response(
                f"Found {len(projects)} project(s)",
                {
                    "projects": projects,
                    "count": len(projects),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_projects: {str(e)}")
        response = create_error_response("Failed to fetch projects", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_project(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get a specific project by ID"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        result = await client.projects.get_project(project_id)
        
        output = f"**Project Details**\n\n{format_project(result)}"
        response = create_success_response(
            f"Retrieved project {project_id}",
            {"project": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_project: {str(e)}")
        response = create_error_response("Failed to fetch project", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]

