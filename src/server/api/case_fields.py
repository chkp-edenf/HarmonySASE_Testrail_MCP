"""Case fields handler functions"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from . import field_cache, priority_cache, case_type_cache


logger = logging.getLogger(__name__)


async def handle_get_case_fields(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all available case fields including custom fields with their possible values
    
    This tool also populates the shared cache with field mappings and required fields,
    making subsequent add_case/update_case calls more efficient.
    """
    
    try:
        result = await client.case_fields.get_case_fields()
        
        # Build field mappings for cache AND formatted output
        field_map = {}
        required_fields = []
        output = "**TestRail Case Fields**\n\n"
        
        for field in result:
            field_name = field.get("name", "Unknown")
            system_name = field.get("system_name", "")
            field_type = field.get("type_id", "")
            label = field.get("label", "")
            
            # Check if field is required (from configs)
            configs = field.get("configs", [])
            is_required = False
            if configs and len(configs) > 0:
                options = configs[0].get("options", {})
                is_required = options.get("is_required", False)
            
            # Track required fields
            if is_required and system_name:
                required_fields.append(system_name)
            
            output += f"**{label}** (`{system_name}`)\n"
            output += f"  └─ Type: {field_type}\n"
            if is_required:
                output += f"  └─  REQUIRED\n"
            
            # Show possible values for dropdowns/multiselects and build cache mapping
            if configs and len(configs) > 0:
                options = configs[0].get("options", {})
                if options:
                    items = options.get("items", "")
                    if items:
                        output += f"  └─ Possible values:\n"
                        
                        # Build mapping for shared cache
                        mapping = {}
                        for line in items.split("\n"):
                            if line.strip():
                                # Format: "1, Value Name"
                                parts = line.split(",", 1)
                                if len(parts) == 2:
                                    id_val = int(parts[0].strip())
                                    name = parts[1].strip()
                                    output += f"     • {parts[0].strip()}: {name}\n"
                                    
                                    # Add to mapping (lowercase for matching)
                                    mapping[name.lower()] = id_val
                                    mapping[str(id_val)] = id_val  # Also map ID string to ID
                        
                        if mapping:
                            field_map[system_name] = mapping
            
            output += "\n"
        
        # Update shared cache with field mappings and required fields
        field_cache.update_cache(field_map, required_fields)
        logger.info(f"Populated shared cache: {len(field_map)} field mappings, {len(required_fields)} required fields")
        
        response = {
            "success": True,
            "message": f"Found {len(result)} case field(s) and populated shared cache",
            "data": {
                "fields": result,
                "count": len(result),
                "formatted": output[:10000]  # Truncate if too long
            }
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_case_fields: {str(e)}")
        response = {
            "success": False,
            "message": "Failed to fetch case fields",
            "error": str(e)
        }
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_case_types(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all available case types"""
    
    try:
        result = await client.case_fields.get_case_types()
        
        # Update the case type cache
        case_type_cache.update_cache(result)
        logger.info(f"✅ Case type cache populated with {len(result)} types")
        
        output = "**TestRail Case Types**\n\n"
        for case_type in result:
            output += f"**{case_type.get('name')}** (ID: {case_type.get('id')})\n"
        
        response = {
            "success": True,
            "message": f"Found {len(result)} case type(s)",
            "data": {
                "types": result,
                "count": len(result),
                "formatted": output
            }
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_case_types: {str(e)}")
        response = {
            "success": False,
            "message": "Failed to fetch case types",
            "error": str(e)
        }
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_priorities(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all available priorities"""
    
    try:
        result = await client.case_fields.get_priorities()
        
        # Update the priority cache
        priority_cache.update_cache(result)
        logger.info(f"✅ Priority cache populated with {len(result)} priorities")
        
        output = "**TestRail Priorities**\n\n"
        for priority in result:
            output += f"**{priority.get('name')}** (ID: {priority.get('id')})\n"
        
        response = {
            "success": True,
            "message": f"Found {len(result)} priorit{'y' if len(result) == 1 else 'ies'}",
            "data": {
                "priorities": result,
                "count": len(result),
                "formatted": output
            }
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_priorities: {str(e)}")
        response = {
            "success": False,
            "message": "Failed to fetch priorities",
            "error": str(e)
        }
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
