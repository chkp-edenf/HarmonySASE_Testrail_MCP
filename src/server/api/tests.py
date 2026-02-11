"""Test tools registration"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from ...shared.schemas.tests import GetTestsInput
from .utils import create_success_response, create_error_response, format_test, truncate_output

logger = logging.getLogger(__name__)


async def handle_get_tests(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get tests for a test run with filtering support"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        # Validate and parse input
        input_data = GetTestsInput(**arguments)
        
        # Extract all parameters including new filters
        run_id = int(input_data.run_id)
        status_id = int(input_data.status_id) if input_data.status_id else None
        assignedto_id = input_data.assignedto_id  # Already int from schema
        priority_id = input_data.priority_id  # Already int from schema
        type_id = input_data.type_id  # Already int from schema
        limit = input_data.limit  # Already int from schema
        offset = input_data.offset  # Already int from schema
        with_data = input_data.with_data  # Already str from schema
        
        # Call client method with all parameters
        result = await client.tests.get_tests(
            run_id=run_id,
            status_id=status_id,
            assignedto_id=assignedto_id,
            priority_id=priority_id,
            type_id=type_id,
            limit=limit,
            offset=offset,
            with_data=with_data
        )
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
