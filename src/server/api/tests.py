"""Test tools registration"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from .utils import create_success_response, create_error_response, format_test, truncate_output

logger = logging.getLogger(__name__)


async def handle_get_tests(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get tests for a test run"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        run_id = int(arguments["run_id"])
        status_id = int(arguments["status_id"]) if arguments.get("status_id") else None
        
        result = await client.tests.get_tests(run_id, status_id)
        tests = result.get("tests", [])
        
        if not tests:
            response = create_success_response(
                f"No tests found for run {run_id}",
                {"tests": [], "count": 0}
            )
        else:
            output = f"**Tests for Run {run_id}**\n\n"
            for test in tests:
                output += format_test(test) + "\n"
            
            response = create_success_response(
                f"Found {len(tests)} test(s)",
                {
                    "tests": tests,
                    "count": len(tests),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_tests: {str(e)}")
        response = create_error_response("Failed to fetch tests", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
async def handle_get_test(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get details of a specific test"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        test_id = int(arguments["test_id"])
        result = await client.tests.get_test(test_id)
        
        output = f"**Test Details**\n\n{format_test(result)}"
        response = create_success_response(
            f"Retrieved test {test_id}",
            {"test": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_test: {str(e)}")
        response = create_error_response("Failed to fetch test", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
