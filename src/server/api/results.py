"""Test result handler functions"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from .utils import create_success_response, create_error_response, truncate_output
from . import status_cache

logger = logging.getLogger(__name__)


async def ensure_status_cache(client: TestRailClient):
    """Ensure status cache is populated, fetch if needed"""
    if not status_cache.is_cache_valid():
        logger.info("Status cache invalid, fetching from TestRail...")
        statuses = await client.statuses.get_statuses()
        status_cache.update_cache(statuses)
        logger.info(f"✅ Status cache populated with {len(statuses)} statuses")


def format_result(result: dict) -> str:
    """Format a single test result for display"""
    status_id = result.get("status_id")
    status_name = status_cache.get_status_name(status_id) if status_id else "Unknown"
    
    output = f"**Result ID: {result.get('id')}**\n"
    output += f"  └─ Test ID: {result.get('test_id', 'N/A')}\n"
    output += f"  └─ Status: {status_name} ({status_id})\n"
    output += f"  └─ Created By: {result.get('created_by', 'N/A')}\n"
    output += f"  └─ Created On: {result.get('created_on', 'N/A')}\n"
    comment = result.get("comment")
    if comment:
        output += f"  └─ Comment: {comment[:100]}...\n"
    return output


async def handle_get_results(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get results for a test"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        test_id = int(arguments["test_id"])
        limit = int(arguments.get("limit", "250"))
        
        result = await client.results.get_results(test_id, limit)
        results = result.get("results", [])
        
        if not results:
            response = create_success_response(
                "No results found",
                {"results": [], "count": 0}
            )
        else:
            output = f"**Results for Test {test_id}**\n\n"
            for res in results:
                output += format_result(res) + "\n"
            
            response = create_success_response(
                f"Found {len(results)} result(s)",
                {
                    "results": results,
                    "count": len(results),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_results: {str(e)}")
        response = create_error_response("Failed to fetch results", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_results_for_case(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get results for a case in a run"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        run_id = int(arguments["run_id"])
        case_id = int(arguments["case_id"])
        limit = int(arguments.get("limit", "250"))
        
        result = await client.results.get_results_for_case(run_id, case_id, limit)
        results = result.get("results", [])
        
        if not results:
            response = create_success_response(
                f"No results found for case {case_id} in run {run_id}",
                {"results": [], "count": 0}
            )
        else:
            output = f"**Results for Case {case_id} in Run {run_id}**\n\n"
            for res in results:
                output += format_result(res) + "\n"
            
            response = create_success_response(
                f"Found {len(results)} result(s)",
                {
                    "results": results,
                    "count": len(results),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_results_for_case: {str(e)}")
        response = create_error_response("Failed to fetch results for case", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_results_for_run(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get all results for a run"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        run_id = int(arguments["run_id"])
        limit = int(arguments.get("limit", "250"))
        
        result = await client.results.get_results_for_run(run_id, limit)
        results = result.get("results", [])
        
        if not results:
            response = create_success_response(
                f"No results found for run {run_id}",
                {"results": [], "count": 0}
            )
        else:
            output = f"**Results for Run {run_id}**\n\n"
            for res in results:
                output += format_result(res) + "\n"
            
            response = create_success_response(
                f"Found {len(results)} result(s)",
                {
                    "results": results,
                    "count": len(results),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_results_for_run: {str(e)}")
        response = create_error_response("Failed to fetch results for run", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_result(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Add a result for a test"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        # Ensure status cache is populated
        await ensure_status_cache(client)
        
        test_id = int(arguments["test_id"])
        
        # Required field
        if not arguments.get("status_id"):
            raise ValueError("Missing required field: status_id")
        
        # Resolve status name/ID to numeric ID using smart cache
        try:
            status_id = status_cache.resolve_status(arguments["status_id"])
            logger.info(f"✅ Resolved status '{arguments['status_id']}' to ID {status_id}")
        except ValueError as e:
            # Provide helpful error with available statuses
            raise ValueError(str(e))
        
        data = {"status_id": status_id}
        
        # Optional fields
        if arguments.get("comment"):
            data["comment"] = arguments["comment"]
        if arguments.get("version"):
            data["version"] = arguments["version"]
        if arguments.get("elapsed"):
            data["elapsed"] = arguments["elapsed"]
        if arguments.get("defects"):
            data["defects"] = arguments["defects"]
        if arguments.get("assignedto_id"):
            data["assignedto_id"] = int(arguments["assignedto_id"])
        
        # Custom fields passthrough
        for key, value in arguments.items():
            if key.startswith("custom_") and key not in data:
                data[key] = value
        
        result = await client.results.add_result(test_id, data)
        
        output = f"**Result Added**\n\n{format_result(result)}"
        response = create_success_response(
            f"Successfully added result for test {test_id}",
            {"result": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_result: {str(e)}")
        response = create_error_response("Failed to add result", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_results(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Add results for multiple tests in a run"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        # Ensure status cache is populated
        await ensure_status_cache(client)
        
        run_id = int(arguments["run_id"])
        
        # Parse results JSON
        if not arguments.get("results"):
            raise ValueError("Missing required field: results")
        
        # Results should be a JSON string like: '[{"test_id": 1, "status_id": 1}, ...]'
        results_data = json.loads(arguments["results"]) if isinstance(arguments["results"], str) else arguments["results"]
        
        # Resolve status names to IDs in each result
        for result in results_data:
            if "status_id" in result:
                try:
                    result["status_id"] = status_cache.resolve_status(str(result["status_id"]))
                    logger.info(f"✅ Resolved status to ID {result['status_id']}")
                except ValueError as e:
                    logger.warning(f"Status resolution failed for result: {e}")
        
        data = {"results": results_data}
        result = await client.results.add_results(run_id, data)
        
        response = create_success_response(
            f"Successfully added {len(results_data)} result(s) to run {run_id}",
            {"result": result, "formatted": f"Added {len(results_data)} results to run {run_id}"}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_results: {str(e)}")
        response = create_error_response("Failed to add results", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
