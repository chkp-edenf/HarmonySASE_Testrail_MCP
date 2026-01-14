"""Test run handler functions"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from .utils import create_success_response, create_error_response, truncate_output

logger = logging.getLogger(__name__)


def format_run(run: dict) -> str:
    """Format a single test run for display"""
    output = f"**{run.get('name', 'Unnamed')}** (ID: {run.get('id')})\n"
    output += f"  └─ Suite ID: {run.get('suite_id', 'N/A')}\n"
    output += f"  └─ Plan ID: {run.get('plan_id', 'None')}\n"
    output += f"  └─ Is Completed: {run.get('is_completed', False)}\n"
    output += f"  └─ Passed: {run.get('passed_count', 0)} | "
    output += f"Failed: {run.get('failed_count', 0)} | "
    output += f"Blocked: {run.get('blocked_count', 0)}\n"
    return output


async def handle_get_runs(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get test runs for a project with optional advanced filtering"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        limit = int(arguments.get("limit", "250"))
        
        # Advanced filter parameters (v1.4.0)
        created_by = int(arguments["created_by"]) if arguments.get("created_by") else None
        created_after = int(arguments["created_after"]) if arguments.get("created_after") else None
        created_before = int(arguments["created_before"]) if arguments.get("created_before") else None
        milestone_id = arguments.get("milestone_id")
        is_completed = None
        if arguments.get("is_completed") is not None:
            is_completed = arguments["is_completed"].lower() == "true"
        
        result = await client.runs.get_runs(
            project_id,
            limit,
            created_by=created_by,
            created_after=created_after,
            created_before=created_before,
            milestone_id=milestone_id,
            is_completed=is_completed
        )
        runs = result.get("runs", [])
        
        if not runs:
            response = create_success_response(
                "No test runs found",
                {"runs": [], "count": 0}
            )
        else:
            output = f"**Test Runs for Project {project_id}**\n\n"
            for run in runs:
                output += format_run(run) + "\n"
            
            response = create_success_response(
                f"Found {len(runs)} test run(s)",
                {
                    "runs": runs,
                    "count": len(runs),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_runs: {str(e)}")
        response = create_error_response("Failed to fetch test runs", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_run(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get details of a specific test run"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        run_id = int(arguments["run_id"])
        result = await client.runs.get_run(run_id)
        
        output = f"**Test Run Details**\n\n{format_run(result)}"
        response = create_success_response(
            f"Retrieved test run {run_id}",
            {"run": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_run: {str(e)}")
        response = create_error_response("Failed to fetch test run", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_run(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Create a new test run"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        project_id = int(arguments["project_id"])
        
        # Required fields
        if not arguments.get("name"):
            raise ValueError("Missing required field: name")
        
        data = {"name": arguments["name"]}
        
        # Optional fields
        if arguments.get("description"):
            data["description"] = arguments["description"]
        if arguments.get("suite_id"):
            data["suite_id"] = int(arguments["suite_id"])
        if arguments.get("milestone_id"):
            data["milestone_id"] = int(arguments["milestone_id"])
        if arguments.get("assignedto_id"):
            data["assignedto_id"] = int(arguments["assignedto_id"])
        if arguments.get("include_all") is not None:
            data["include_all"] = arguments["include_all"].lower() == "true"
        if arguments.get("case_ids"):
            data["case_ids"] = [int(cid.strip()) for cid in arguments["case_ids"].split(",")]
        
        result = await client.runs.add_run(project_id, data)
        
        output = f"**Test Run Created**\n\n{format_run(result)}"
        response = create_success_response(
            f"Successfully created test run '{result.get('name')}'",
            {"run": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_run: {str(e)}")
        response = create_error_response("Failed to create test run", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_update_run(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Update an existing test run"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        run_id = int(arguments["run_id"])
        data = {}
        
        # Optional fields
        if arguments.get("name"):
            data["name"] = arguments["name"]
        if arguments.get("description"):
            data["description"] = arguments["description"]
        if arguments.get("milestone_id"):
            data["milestone_id"] = int(arguments["milestone_id"])
        if arguments.get("include_all") is not None:
            data["include_all"] = arguments["include_all"].lower() == "true"
        if arguments.get("case_ids"):
            data["case_ids"] = [int(cid.strip()) for cid in arguments["case_ids"].split(",")]
        
        if not data:
            response = create_error_response("No update fields provided", Exception("No fields specified"))
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        result = await client.runs.update_run(run_id, data)
        
        output = f"**Test Run Updated**\n\n{format_run(result)}"
        response = create_success_response(
            f"Successfully updated test run {run_id}",
            {"run": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in update_run: {str(e)}")
        response = create_error_response("Failed to update test run", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_close_run(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Close a test run"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        run_id = int(arguments["run_id"])
        result = await client.runs.close_run(run_id)
        
        output = f"**Test Run Closed**\n\n{format_run(result)}"
        response = create_success_response(
            f"Successfully closed test run {run_id}",
            {"run": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in close_run: {str(e)}")
        response = create_error_response("Failed to close test run", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_run(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Delete a test run"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        run_id = int(arguments["run_id"])
        await client.runs.delete_run(run_id)
        
        response = create_success_response(
            f"Successfully deleted test run {run_id}",
            {"run_id": run_id, "formatted": f"Test run {run_id} has been deleted"}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in delete_run: {str(e)}")
        response = create_error_response("Failed to delete test run", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
