"""Test case tools registration"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from ...shared.schemas import AddCasePayload
from ...shared.schemas.cases import GetCasesInput
from .utils import create_success_response, create_error_response, format_case, truncate_output
from .rate_limiter import rate_limiter
from . import field_cache, priority_cache, case_type_cache

logger = logging.getLogger(__name__)


async def ensure_metadata_caches(client: TestRailClient):
    """Ensure priority and case type caches are populated"""
    if not priority_cache.is_cache_valid():
        logger.info("Priority cache invalid, fetching...")
        priorities = await client.case_fields.get_priorities()
        priority_cache.update_cache(priorities)
    
    if not case_type_cache.is_cache_valid():
        logger.info("Case type cache invalid, fetching...")
        types = await client.case_fields.get_case_types()
        case_type_cache.update_cache(types)


async def _get_field_mapping(client: TestRailClient, field_name: str) -> dict:
    """
    Get field value mappings using shared cache.
    Returns dict mapping lowercase names to IDs.
    Cache persists for 24 hours or until container restart.
    """
    # Check shared cache first
    if field_cache.is_cache_valid():
        mapping = field_cache.get_field_mapping(field_name)
        if mapping:
            logger.info(f"Using shared cache for {field_name}")
            return mapping
    
    # Fetch from API (cache expired or doesn't exist)
    logger.info(f"Fetching fresh field mappings from TestRail API...")
    try:
        fields = await client.case_fields.get_case_fields()
        
        # Parse all field mappings
        field_map = {}
        for field in fields:
            system_name = field.get("system_name", "")
            configs = field.get("configs", [])
            
            if configs and len(configs) > 0:
                items_str = configs[0].get("options", {}).get("items", "")
                if items_str:
                    # Parse items like "1, Platform\n2, Win\n3, Mac"
                    mapping = {}
                    for line in items_str.split("\n"):
                        if "," in line:
                            parts = line.split(",", 1)
                            if len(parts) == 2:
                                id_val = int(parts[0].strip())
                                name = parts[1].strip().lower()
                                mapping[name] = id_val
                                mapping[str(id_val)] = id_val  # Also map ID string to ID
                    
                    field_map[system_name] = mapping
        
        # Extract required fields
        required = []
        for field in fields:
            if field.get("is_required", False):
                system_name = field.get("system_name", "")
                if system_name:
                    required.append(system_name)
        
        # Update shared cache
        field_cache.update_cache(field_map, required)
        
        return field_map.get(field_name, {})
        
    except Exception as e:
        logger.error(f"Failed to fetch field mappings: {e}")
        return {}


async def _parse_field_values(client: TestRailClient, value_str: str | list, field_name: str) -> list[int]:
    """
    Parse comma-separated values that can be IDs or names.
    Uses persistent file cache for mappings.
    Handles both string inputs ("1,2,3") and pre-parsed list inputs ([1, 2, 3]).
    """
    # Handle if already a list (AI agents might send pre-parsed data)
    if isinstance(value_str, list):
        result = []
        for val in value_str:
            if isinstance(val, int):
                result.append(val)
            else:
                # Try to convert string/other to int
                try:
                    result.append(int(val))
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert '{val}' to int in {field_name} - skipping")
        return result
    
    # Original string parsing logic
    values = [v.strip().lower() for v in value_str.split(",")]
    result = []
    
    # Get mapping from cache (file-based)
    field_mapping = await _get_field_mapping(client, field_name)
    
    for val in values:
        # Try mapping lookup
        if val in field_mapping:
            result.append(field_mapping[val])
        else:
            # Try as direct integer
            try:
                result.append(int(val))
            except ValueError:
                logger.warning(f"Could not resolve value '{val}' in {field_name} - skipping")
    
    return result


async def _parse_single_field_value(client: TestRailClient, value_str: str | int, field_name: str) -> int:
    """
    Parse a single value (ID or name) for single-select dropdown fields.
    Uses persistent file cache for mappings.
    Returns a single integer ID.
    Handles both string inputs ("1" or "high") and pre-parsed int inputs (1).
    """
    # Handle if already an int (AI agents might send pre-parsed data)
    if isinstance(value_str, int):
        return value_str
    
    val = value_str.strip().lower()
    
    # Get mapping from cache (file-based)
    field_mapping = await _get_field_mapping(client, field_name)
    
    # Try mapping lookup
    if val in field_mapping:
        return field_mapping[val]
    
    # Try as direct integer
    try:
        return int(value_str.strip())  # Use original case for numeric parsing
    except ValueError:
        logger.error(f"Could not resolve value '{value_str}' in {field_name}")
        raise ValueError(f"Invalid value '{value_str}' for field {field_name}")


async def _get_required_fields(client: TestRailClient) -> list:
    """
    Get list of required field system names from shared cache.
    """
    # Check shared cache
    if field_cache.is_cache_valid():
        return field_cache.get_required_fields()
    
    # Trigger cache refresh by fetching field mappings
    # We need to call get_case_fields to populate the cache
    try:
        await client.case_fields.get_case_fields()
        # This will trigger the cache update in _get_field_mapping
        # when called from handlers
    except Exception as e:
        logger.warning(f"Failed to fetch case fields for required fields check: {e}")
    
    return field_cache.get_required_fields()


async def _validate_required_fields(client: TestRailClient, data: dict) -> list:
    """
    Validate that all required fields are present in data.
    Returns list of missing required field names (empty if all present).
    """
    required_fields = await _get_required_fields(client)
    missing = []
    
    for field_name in required_fields:
        if field_name not in data:
            missing.append(field_name)
    
    return missing


async def handle_get_cases(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get test cases for a project/suite with optional advanced filtering"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        # Validate and parse input
        input_data = GetCasesInput(**arguments)
        
        # Extract all parameters including new filters
        project_id = int(input_data.project_id)
        suite_id = int(input_data.suite_id) if input_data.suite_id else None
        limit = int(input_data.limit) if input_data.limit else 250
        
        # Advanced filter parameters (v1.4.0)
        created_by = int(input_data.created_by) if input_data.created_by else None
        created_after = int(input_data.created_after) if input_data.created_after else None
        created_before = int(input_data.created_before) if input_data.created_before else None
        updated_by = int(input_data.updated_by) if input_data.updated_by else None
        updated_after = int(input_data.updated_after) if input_data.updated_after else None
        updated_before = int(input_data.updated_before) if input_data.updated_before else None
        priority_id = input_data.priority_id
        type_id = input_data.type_id
        milestone_id = input_data.milestone_id
        # Handle section_id and template_id - they can be int or str from validation
        section_id = int(input_data.section_id) if input_data.section_id is not None else None
        template_id = int(input_data.template_id) if input_data.template_id is not None else None
        offset = int(input_data.offset) if input_data.offset is not None else None
        
        # Call client method with all parameters
        result = await client.cases.get_cases(
            project_id=project_id,
            suite_id=suite_id,
            limit=limit,
            created_by=created_by,
            created_after=created_after,
            created_before=created_before,
            updated_by=updated_by,
            updated_after=updated_after,
            updated_before=updated_before,
            priority_id=priority_id,
            type_id=type_id,
            milestone_id=milestone_id,
            section_id=section_id,
            template_id=template_id,
            offset=offset
        )
        cases = result.get("cases", [])
        
        if not cases:
            response = create_success_response("No test cases found", {"cases": [], "count": 0})
        else:
            output = f"**Test Cases (Project {project_id}"
            if suite_id:
                output += f", Suite {suite_id}"
            output += ")**\n\n"
            for case in cases:
                output += format_case(case) + "\n"
            
            response = create_success_response(
                f"Found {len(cases)} test case(s)",
                {
                    "cases": cases,
                    "count": len(cases),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_cases: {str(e)}")
        response = create_error_response("Failed to fetch test cases", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
async def handle_get_cases_by_ids(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Fetch multiple specific test cases by a list of case IDs (batch operation)"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        # Parse comma-separated case IDs
        case_ids = [int(cid.strip()) for cid in arguments["case_ids"].split(",")]
        
        if not case_ids:
            response = create_error_response("No case IDs provided", Exception("case_ids cannot be empty"))
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        # Fetch each case individually (TestRail API has no batch endpoint)
        cases = []
        failed_ids = []
        
        for case_id in case_ids:
            try:
                result = await client.cases.get_case(case_id)
                cases.append(result)
            except Exception as e:
                logger.warning(f"Failed to fetch case {case_id}: {e}")
                failed_ids.append(case_id)
        
        if not cases and failed_ids:
            response = create_error_response(
                f"Failed to fetch all {len(failed_ids)} case(s)",
                Exception(f"Case IDs: {', '.join(map(str, failed_ids))}")
            )
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        # Build formatted output
        output = f"**Test Cases (Batch Fetch: {len(cases)} successful, {len(failed_ids)} failed)**\n\n"
        for case in cases:
            output += format_case(case) + "\n"
        
        if failed_ids:
            output += f"\n⚠️ **Failed to fetch:** {', '.join(map(str, failed_ids))}"
        
        response = create_success_response(
            f"Retrieved {len(cases)} of {len(case_ids)} test case(s)",
            {
                "cases": cases,
                "count": len(cases),
                "requested_count": len(case_ids),
                "failed_ids": failed_ids,
                "formatted": truncate_output(output)
            }
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_cases_by_ids: {str(e)}")
        response = create_error_response("Failed to fetch test cases by IDs", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
async def handle_get_case(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get complete details of a specific test case"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        case_id = int(arguments["case_id"])
        result = await client.cases.get_case(case_id)
        
        output = f"**Test Case Details**\n\n{format_case(result)}"
        response = create_success_response(
            f"Retrieved test case {case_id}",
            {"case": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_case: {str(e)}")
        response = create_error_response("Failed to fetch test case", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
async def handle_add_case(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Create a new test case in a section"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    # Parse custom_fields JSON if provided
    if arguments.get("custom_fields"):
        try:
            custom_fields = json.loads(arguments["custom_fields"])
            # Merge custom fields into arguments (don't overwrite existing)
            for key, value in custom_fields.items():
                if key.startswith("custom_") and key not in arguments:
                    arguments[key] = value
            logger.info(f"Parsed custom_fields: {json.dumps(custom_fields, indent=2)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse custom_fields JSON: {e}")
            response = create_error_response("Invalid custom_fields JSON format", e)
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    retry_count = 0
    max_retries = 1
    
    while retry_count <= max_retries:
        try:
            # Ensure metadata caches are populated
            await ensure_metadata_caches(client)
            
            section_id = int(arguments["section_id"])
            
            # Build data dict directly
            data = {"title": arguments["title"]}
            
            # Standard fields with smart resolution
            if arguments.get("template_id"):
                data["template_id"] = int(arguments["template_id"])
            
            if arguments.get("type_id"):
                # Smart resolve case type
                try:
                    data["type_id"] = case_type_cache.resolve_case_type(arguments["type_id"])
                    logger.info(f"✅ Resolved type '{arguments['type_id']}' to ID {data['type_id']}")
                except ValueError as e:
                    logger.warning(f"Type resolution failed, using as-is: {e}")
                    data["type_id"] = int(arguments["type_id"])
            
            if arguments.get("priority_id"):
                # Smart resolve priority
                try:
                    data["priority_id"] = priority_cache.resolve_priority(arguments["priority_id"])
                    logger.info(f"✅ Resolved priority '{arguments['priority_id']}' to ID {data['priority_id']}")
                except ValueError as e:
                    logger.warning(f"Priority resolution failed, using as-is: {e}")
                    data["priority_id"] = int(arguments["priority_id"])
            
            if arguments.get("estimate"):
                data["estimate"] = arguments["estimate"]
            if arguments.get("refs"):
                data["refs"] = arguments["refs"]
            
            # Generic custom field handling: automatically parse any custom_* field
            # based on its type from get_case_fields metadata
            for key, value in arguments.items():
                if key.startswith("custom_") and key not in data and value:
                    # Try to get field mapping to determine if this is a dropdown field
                    field_mapping = await _get_field_mapping(client, key)
                    
                    if field_mapping:
                        # Field has a mapping (dropdown/multi-select)
                        # Check if value is already a list or contains comma (multi-select)
                        if isinstance(value, list):
                            # Already a list - parse it
                            data[key] = await _parse_field_values(client, value, key)
                        elif isinstance(value, str) and "," in value:
                            # Comma-separated string - multi-select field
                            data[key] = await _parse_field_values(client, value, key)
                        else:
                            # Single-select field (could be int or string)
                            try:
                                data[key] = await _parse_single_field_value(client, value, key)
                            except ValueError:
                                # If single-select parsing fails, try multi-select
                                data[key] = await _parse_field_values(client, value, key)
                    else:
                        # No mapping found - pass through as-is (text field, etc.)
                        data[key] = value
            
            # Validate required fields before sending POST
            missing_fields = await _validate_required_fields(client, data)
            if missing_fields:
                missing_names = ", ".join(missing_fields)
                raise ValueError(f"Missing required fields: {missing_names}")
            
            result = await client.cases.add_case(section_id, data)
            
            output = f"**Test Case Created**\n\n{format_case(result)}"
            response = create_success_response(
                f"Created test case {result.get('id')}",
                {"case": result, "formatted": truncate_output(output)}
            )
            
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if error is related to field values/mapping
            is_field_error = any(keyword in error_str for keyword in [
                'field', 'custom_', 'invalid value', 'unknown', 'not found', 'mapping'
            ])
            
            # If it's a field error and we haven't retried yet, invalidate cache and retry
            if is_field_error and retry_count == 0:
                logger.warning(f"Field-related error detected, invalidating cache and retrying: {e}")
                field_cache.invalidate_cache()
                retry_count += 1
                continue  # Retry the loop
            
            # Otherwise, return error
            logger.error(f"Error in add_case: {str(e)}")
            response = create_error_response("Failed to create test case", e)
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    # Should not reach here, but just in case
    response = create_error_response("Failed to create test case after retries", Exception("Max retries exceeded"))
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_update_case(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Update an existing test case"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    # Parse custom_fields JSON if provided
    if arguments.get("custom_fields"):
        try:
            custom_fields = json.loads(arguments["custom_fields"])
            # Merge custom fields into arguments (don't overwrite existing)
            for key, value in custom_fields.items():
                if key.startswith("custom_") and key not in arguments:
                    arguments[key] = value
            logger.info(f"Parsed custom_fields: {json.dumps(custom_fields, indent=2)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse custom_fields JSON: {e}")
            response = create_error_response("Invalid custom_fields JSON format", e)
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    try:
        # Ensure metadata caches are populated
        await ensure_metadata_caches(client)
        
        case_id = int(arguments["case_id"])
        data = {}
        
        # Standard fields
        if arguments.get("title"):
            data["title"] = arguments["title"]
        if arguments.get("template_id"):
            data["template_id"] = int(arguments["template_id"])
        
        if arguments.get("type_id"):
            # Smart resolve case type
            try:
                data["type_id"] = case_type_cache.resolve_case_type(arguments["type_id"])
                logger.info(f"✅ Resolved type '{arguments['type_id']}' to ID {data['type_id']}")
            except ValueError as e:
                logger.warning(f"Type resolution failed, using as-is: {e}")
                data["type_id"] = int(arguments["type_id"])
        
        if arguments.get("priority_id"):
            # Smart resolve priority
            try:
                data["priority_id"] = priority_cache.resolve_priority(arguments["priority_id"])
                logger.info(f"✅ Resolved priority '{arguments['priority_id']}' to ID {data['priority_id']}")
            except ValueError as e:
                logger.warning(f"Priority resolution failed, using as-is: {e}")
                data["priority_id"] = int(arguments["priority_id"])
        if arguments.get("estimate"):
            data["estimate"] = arguments["estimate"]
        if arguments.get("refs"):
            data["refs"] = arguments["refs"]
        
        # Generic custom field handling: automatically parse any custom_* field
        for key, value in arguments.items():
            if key.startswith("custom_") and key not in data and key != "case_id" and value:
                # Try to get field mapping to determine field type
                field_mapping = await _get_field_mapping(client, key)
                
                if field_mapping:
                    # Field has a mapping (dropdown/multi-select)
                    # Check if value is already a list or contains comma (multi-select)
                    if isinstance(value, list):
                        # Already a list - parse it
                        data[key] = await _parse_field_values(client, value, key)
                    elif isinstance(value, str) and "," in value:
                        # Comma-separated string - multi-select field
                        data[key] = await _parse_field_values(client, value, key)
                    else:
                        # Single-select field (could be int or string)
                        try:
                            data[key] = await _parse_single_field_value(client, value, key)
                        except ValueError:
                            # If single-select parsing fails, try multi-select
                            data[key] = await _parse_field_values(client, value, key)
                else:
                    # No mapping - pass through as-is (text field, etc.)
                    data[key] = value
        
        if not data:
            response = create_error_response("No update fields provided", Exception("No fields specified"))
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        result = await client.cases.update_case(case_id, data)
        
        output = f"**Test Case Updated**\n\n{format_case(result)}"
        response = create_success_response(
            f"Updated test case {case_id}",
            {"case": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in update_case: {str(e)}")
        response = create_error_response("Failed to update test case", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_case(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Delete a test case (soft delete)"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        case_id = int(arguments["case_id"])
        await client.cases.delete_case(case_id)
        
        response = create_success_response(
            f"Successfully deleted test case {case_id}",
            {"case_id": case_id, "formatted": f"Test case {case_id} has been deleted"}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in delete_case: {str(e)}")
        response = create_error_response("Failed to delete test case", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_case_history(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get the change history for a test case"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        case_id = int(arguments["case_id"])
        result = await client.cases.get_case_history(case_id)
        
        # API returns dict with history array
        history = result.get("history", []) if isinstance(result, dict) else []
        
        if not history:
            response = create_success_response(
                f"No history found for test case {case_id}",
                {"history": [], "count": 0}
            )
        else:
            output = f"**Case History for Test Case {case_id}**\n\n"
            for entry in history:
                output += f"**{entry.get('created_on')}** by {entry.get('user', 'Unknown')}\n"
                output += f"  └─ {entry.get('changes', 'No details')}\n\n"
            
            response = create_success_response(
                f"Found {len(history)} history entry(ies)",
                {
                    "history": history,
                    "count": len(history),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_case_history: {str(e)}")
        response = create_error_response("Failed to fetch case history", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_copy_cases_to_section(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Copy test cases to a different section"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        section_id = int(arguments["section_id"])
        case_ids = [int(cid.strip()) for cid in arguments["case_ids"].split(",")]
        
        data = {"case_ids": case_ids}
        result = await client.cases.copy_cases_to_section(section_id, data)
        
        response = create_success_response(
            f"Successfully copied {len(case_ids)} case(s) to section {section_id}",
            {
                "section_id": section_id,
                "case_ids": case_ids,
                "result": result,
                "formatted": f"Copied {len(case_ids)} test case(s) to section {section_id}"
            }
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in copy_cases_to_section: {str(e)}")
        response = create_error_response("Failed to copy test cases", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_move_cases_to_section(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Move test cases to a different section"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        section_id = int(arguments["section_id"])
        case_ids = [int(cid.strip()) for cid in arguments["case_ids"].split(",")]
        
        data = {"case_ids": case_ids}
        result = await client.cases.move_cases_to_section(section_id, data)
        
        response = create_success_response(
            f"Successfully moved {len(case_ids)} case(s) to section {section_id}",
            {
                "section_id": section_id,
                "case_ids": case_ids,
                "result": result,
                "formatted": f"Moved {len(case_ids)} test case(s) to section {section_id}"
            }
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in move_cases_to_section: {str(e)}")
        response = create_error_response("Failed to move test cases", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_update_cases(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Bulk update test cases"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    # Parse custom_fields JSON if provided
    if arguments.get("custom_fields"):
        try:
            custom_fields = json.loads(arguments["custom_fields"])
            # Merge custom fields into arguments (don't overwrite existing)
            for key, value in custom_fields.items():
                if key.startswith("custom_") and key not in arguments:
                    arguments[key] = value
            logger.info(f"Parsed custom_fields: {json.dumps(custom_fields, indent=2)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse custom_fields JSON: {e}")
            response = create_error_response("Invalid custom_fields JSON format", e)
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    try:
        # Ensure metadata caches are populated
        await ensure_metadata_caches(client)
        
        suite_id = int(arguments["suite_id"])
        case_ids = [int(cid.strip()) for cid in arguments["case_ids"].split(",")]
        
        data = {"case_ids": case_ids}
        
        # Standard fields for bulk update with smart resolution
        if arguments.get("priority_id"):
            try:
                data["priority_id"] = priority_cache.resolve_priority(arguments["priority_id"])  # type: ignore[assignment]
                logger.info(f"✅ Resolved priority '{arguments['priority_id']}' to ID {data['priority_id']}")
            except ValueError as e:
                logger.warning(f"Priority resolution failed, using as-is: {e}")
                data["priority_id"] = int(arguments["priority_id"])  # type: ignore[assignment]
        
        if arguments.get("type_id"):
            try:
                data["type_id"] = case_type_cache.resolve_case_type(arguments["type_id"])  # type: ignore[assignment]
                logger.info(f"✅ Resolved type '{arguments['type_id']}' to ID {data['type_id']}")
            except ValueError as e:
                logger.warning(f"Type resolution failed, using as-is: {e}")
                data["type_id"] = int(arguments["type_id"])  # type: ignore[assignment]
        
        if arguments.get("template_id"):
            data["template_id"] = int(arguments["template_id"])  # type: ignore[assignment]
        
        # Generic custom field handling: automatically parse any custom_* field
        for key, value in arguments.items():
            if key.startswith("custom_") and key not in data and value:
                # Try to get field mapping to determine field type
                field_mapping = await _get_field_mapping(client, key)
                
                if field_mapping:
                    # Field has a mapping (dropdown/multi-select)
                    # Check if value is already a list or contains comma (multi-select)
                    if isinstance(value, list):
                        # Already a list - parse it
                        data[key] = await _parse_field_values(client, value, key)
                    elif isinstance(value, str) and "," in value:
                        # Comma-separated string - multi-select field
                        data[key] = await _parse_field_values(client, value, key)
                    else:
                        # Single-select field (could be int or string)
                        try:
                            data[key] = await _parse_single_field_value(client, value, key)  # type: ignore[assignment]
                        except ValueError:
                            # If single-select parsing fails, try multi-select
                            data[key] = await _parse_field_values(client, value, key)
                else:
                    # No mapping - pass through as-is (text field, etc.)
                    data[key] = value
        
        result = await client.cases.update_cases(suite_id, data)
        
        response = create_success_response(
            f"Successfully updated {len(case_ids)} case(s)",
            {
                "suite_id": suite_id,
                "case_ids": case_ids,
                "result": result,
                "formatted": f"Bulk updated {len(case_ids)} test case(s) in suite {suite_id}"
            }
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in update_cases: {str(e)}")
        response = create_error_response("Failed to bulk update test cases", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_cases(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Bulk delete test cases (soft delete)"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        suite_id = int(arguments["suite_id"])
        case_ids = [int(cid.strip()) for cid in arguments["case_ids"].split(",")]
        
        data = {"case_ids": case_ids}
        result = await client.cases.delete_cases(suite_id, data)
        
        response = create_success_response(
            f"Successfully deleted {len(case_ids)} case(s)",
            {
                "suite_id": suite_id,
                "case_ids": case_ids,
                "result": result,
                "formatted": f"Bulk deleted {len(case_ids)} test case(s) from suite {suite_id}"
            }
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in delete_cases: {str(e)}")
        response = create_error_response("Failed to bulk delete test cases", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]

