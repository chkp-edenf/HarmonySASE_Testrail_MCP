"""Configuration handler functions"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from .utils import create_success_response, create_error_response, truncate_output

logger = logging.getLogger(__name__)


def format_config(config: dict) -> str:
    """Format a single configuration for display"""
    lines = [
        f"**{config.get('name', 'Unnamed')}** (ID: {config.get('id', 'N/A')})",
        f"  Group ID: {config.get('group_id', 'N/A')}"
    ]
    return "\n".join(lines)


def format_config_group(group: dict) -> str:
    """Format a configuration group with its configs for display"""
    lines = [
        f"**{group.get('name', 'Unnamed')}** (ID: {group.get('id', 'N/A')})",
        f"  Project ID: {group.get('project_id', 'N/A')}"
    ]
    
    configs = group.get('configs', [])
    if configs:
        lines.append(f"  Configurations ({len(configs)}):")
        for config in configs:
            lines.append(f"    - {config.get('name', 'Unnamed')} (ID: {config.get('id', 'N/A')})")
    else:
        lines.append("  Configurations: None")
    
    return "\n".join(lines)


async def handle_get_configs(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all configuration groups for a project"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        result = await client.configs.get_configs(project_id)
        
        if not result:
            response = create_success_response(
                f"No configuration groups found for project {project_id}",
                {"config_groups": [], "count": 0}
            )
        else:
            output = f"**Configuration Groups for Project {project_id}**\n\n"
            for group in result:
                output += format_config_group(group) + "\n\n"
            
            # Count total configs across all groups
            total_configs = sum(len(group.get('configs', [])) for group in result)
            
            response = create_success_response(
                f"Found {len(result)} configuration group(s) with {total_configs} configuration(s)",
                {
                    "config_groups": result,
                    "count": len(result),
                    "total_configs": total_configs,
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_configs: {str(e)}")
        response = create_error_response("Failed to fetch configuration groups", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_config_group(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Create a new configuration group"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        
        # Validate required fields
        if not arguments.get("name"):
            raise ValueError("Missing required field: name")
        
        data = {"name": arguments["name"]}
        
        result = await client.configs.add_config_group(project_id, data)
        
        output = f"**Configuration Group Created**\n\n{format_config_group(result)}"
        response = create_success_response(
            f"Successfully created configuration group '{result.get('name')}'",
            {"config_group": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_config_group: {str(e)}")
        response = create_error_response("Failed to create configuration group", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_config(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Add a configuration to a group"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        config_group_id = int(arguments["config_group_id"])
        
        # Validate required fields
        if not arguments.get("name"):
            raise ValueError("Missing required field: name")
        
        data = {"name": arguments["name"]}
        
        result = await client.configs.add_config(config_group_id, data)
        
        output = f"**Configuration Created**\n\n{format_config(result)}"
        response = create_success_response(
            f"Successfully created configuration '{result.get('name')}'",
            {"config": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_config: {str(e)}")
        response = create_error_response("Failed to create configuration", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
