"""Status tools registration"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from .utils import create_success_response, create_error_response
from . import status_cache

logger = logging.getLogger(__name__)


async def handle_get_statuses(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all available test statuses
    
    Lists all status options that can be used when adding test results.
    
    Returns:
        List of statuses with ID, name, label, and color information
    """
    logger.info(" Getting statuses...")
    
    try:
        statuses = await client.statuses.get_statuses()
        
        if not statuses:
            response = create_success_response(
                "ℹ No statuses found",
                "No statuses available"
            )
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        # Update the status cache
        status_cache.update_cache(statuses)
        logger.info(f"✅ Status cache populated with {len(statuses)} statuses")
        
        # Format statuses
        output_lines = [
            " **Test Statuses**",
            f"Found {len(statuses)} status(es):",
            ""
        ]
        
        for status in statuses:
            status_id = status.get("id", "N/A")
            name = status.get("name", "Unnamed")
            label = status.get("label", name)
            color_dark = status.get("color_dark", "")
            color_hex = f" ({color_dark})" if color_dark else ""
            is_system = status.get("is_system", False)
            is_final = status.get("is_final", False)
            
            # Build status line
            status_line = f"**ID {status_id}**: {label}{color_hex}"
            
            # Add badges
            badges = []
            if is_system:
                badges.append(" System")
            if is_final:
                badges.append("🏁 Final")
            
            if badges:
                status_line += f" - {' '.join(badges)}"
            
            output_lines.append(status_line)
        
        output_lines.extend([
            "",
            " **Usage**: Use the status ID when calling `add_result` or `add_results`",
            "   Example: `add_result test_id=12345 status_id=1 comment=\"Test passed\"`"
        ])
        
        response = create_success_response(
            " Successfully retrieved statuses",
            {
                "statuses": statuses,
                "count": len(statuses),
                "formatted": "\n".join(output_lines)
            }
        )
        
        logger.info(f"Returning response with message and populated cache")
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error getting statuses: {e}")
        response = create_error_response(
            "Failed to get statuses",
            e
        )
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
