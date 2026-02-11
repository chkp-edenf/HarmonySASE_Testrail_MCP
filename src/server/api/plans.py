"""Test plan handler functions"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from ...shared.schemas.plans import GetPlansInput
from .utils import create_success_response, create_error_response, truncate_output

logger = logging.getLogger(__name__)


def format_plan(plan: dict) -> str:
    """Format a single test plan for display"""
    output = f"**{plan.get('name', 'Unnamed')}** (ID: {plan.get('id')})\n"
    output += f"  └─ Project ID: {plan.get('project_id', 'N/A')}\n"
    output += f"  └─ Milestone ID: {plan.get('milestone_id', 'None')}\n"
    output += f"  └─ Is Completed: {plan.get('is_completed', False)}\n"
    output += f"  └─ Passed: {plan.get('passed_count', 0)} | "
    output += f"Failed: {plan.get('failed_count', 0)} | "
    output += f"Blocked: {plan.get('blocked_count', 0)}\n"
    
    # Show entries if available
    entries = plan.get('entries', [])
    if entries:
        output += f"  └─ Entries: {len(entries)}\n"
    
    return output


async def handle_get_plans(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get test plans for a project with filtering support"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        # Validate and parse input
        input_data = GetPlansInput(**arguments)
        
        # Extract all parameters including new filters
        project_id = int(input_data.project_id)
        limit = int(input_data.limit) if input_data.limit else 250
        offset = int(input_data.offset) if input_data.offset else 0
        
        # Advanced filter parameters
        created_by = int(input_data.created_by) if input_data.created_by else None
        created_after = int(input_data.created_after) if input_data.created_after else None
        created_before = int(input_data.created_before) if input_data.created_before else None
        milestone_id = input_data.milestone_id
        is_completed = None
        if input_data.is_completed is not None:
            is_completed = input_data.is_completed.lower() in ("true", "1")
        
        # Call client method with all parameters
        result = await client.plans.get_plans(
            project_id=project_id,
            limit=limit,
            offset=offset,
            created_by=created_by,
            created_after=created_after,
            created_before=created_before,
            milestone_id=milestone_id,
            is_completed=is_completed
        )
        plans = result.get("plans", [])
        
        if not plans:
            response = create_success_response(
                "No test plans found",
                {"plans": [], "count": 0}
            )
        else:
            output = f"**Test Plans for Project {project_id}**\n\n"
            for plan in plans:
                output += format_plan(plan) + "\n"
            
            response = create_success_response(
                f"Found {len(plans)} test plan(s)",
                {
                    "plans": plans,
                    "count": len(plans),
                    "formatted": truncate_output(output)
                }
            )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_plans: {str(e)}")
        response = create_error_response("Failed to fetch test plans", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_plan(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get details of a specific test plan"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        plan_id = int(arguments["plan_id"])
        result = await client.plans.get_plan(plan_id)
        
        output = f"**Test Plan Details**\n\n{format_plan(result)}"
        
        # Show detailed entries info
        entries = result.get('entries', [])
        if entries:
            output += f"\n**Plan Entries ({len(entries)})**:\n"
            for i, entry in enumerate(entries, 1):
                output += f"{i}. {entry.get('name', 'Unnamed Entry')}\n"
                output += f"   └─ Suite ID: {entry.get('suite_id', 'N/A')}\n"
                runs = entry.get('runs', [])
                if runs:
                    output += f"   └─ Runs: {len(runs)}\n"
        
        response = create_success_response(
            f"Retrieved test plan {plan_id}",
            {"plan": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_plan: {str(e)}")
        response = create_error_response("Failed to fetch test plan", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_plan(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Create a new test plan"""
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
        if arguments.get("milestone_id"):
            data["milestone_id"] = int(arguments["milestone_id"])
        if arguments.get("entries"):
            # Parse entries if provided as JSON string
            entries = arguments["entries"]
            if isinstance(entries, str):
                data["entries"] = json.loads(entries)
            else:
                data["entries"] = entries
        
        result = await client.plans.add_plan(project_id, data)
        
        output = f"**Test Plan Created**\n\n{format_plan(result)}"
        response = create_success_response(
            f"Successfully created test plan '{result.get('name')}'",
            {"plan": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_plan: {str(e)}")
        response = create_error_response("Failed to create test plan", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_update_plan(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Update an existing test plan"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        plan_id = int(arguments["plan_id"])
        data = {}
        
        # Optional fields
        if arguments.get("name"):
            data["name"] = arguments["name"]
        if arguments.get("description"):
            data["description"] = arguments["description"]
        if arguments.get("milestone_id"):
            data["milestone_id"] = int(arguments["milestone_id"])
        if arguments.get("entries"):
            # Parse entries if provided as JSON string
            entries = arguments["entries"]
            if isinstance(entries, str):
                data["entries"] = json.loads(entries)
            else:
                data["entries"] = entries
        
        if not data:
            response = create_error_response("No update fields provided", Exception("No fields specified"))
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        result = await client.plans.update_plan(plan_id, data)
        
        output = f"**Test Plan Updated**\n\n{format_plan(result)}"
        response = create_success_response(
            f"Successfully updated test plan {plan_id}",
            {"plan": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in update_plan: {str(e)}")
        response = create_error_response("Failed to update test plan", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_close_plan(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Close a test plan"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        plan_id = int(arguments["plan_id"])
        result = await client.plans.close_plan(plan_id)
        
        output = f"**Test Plan Closed**\n\n{format_plan(result)}"
        response = create_success_response(
            f"Successfully closed test plan {plan_id}",
            {"plan": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in close_plan: {str(e)}")
        response = create_error_response("Failed to close test plan", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_plan(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Delete a test plan"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        plan_id = int(arguments["plan_id"])
        await client.plans.delete_plan(plan_id)
        
        response = create_success_response(
            f"Successfully deleted test plan {plan_id}",
            {"plan_id": plan_id, "formatted": f"Test plan {plan_id} has been deleted"}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in delete_plan: {str(e)}")
        response = create_error_response("Failed to delete test plan", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_plan_entry(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Add a test run/entry to an existing plan"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        plan_id = int(arguments["plan_id"])
        
        # Required fields
        if not arguments.get("suite_id"):
            raise ValueError("Missing required field: suite_id")
        
        data = {"suite_id": int(arguments["suite_id"])}
        
        # Optional fields
        if arguments.get("name"):
            data["name"] = arguments["name"]
        if arguments.get("description"):
            data["description"] = arguments["description"]
        if arguments.get("assignedto_id"):
            data["assignedto_id"] = int(arguments["assignedto_id"])
        if arguments.get("include_all"):
            data["include_all"] = arguments["include_all"].lower() == "true"
        if arguments.get("case_ids"):
            # Parse comma-separated list
            data["case_ids"] = [int(x.strip()) for x in arguments["case_ids"].split(",")]
        if arguments.get("config_ids"):
            # Parse comma-separated list
            data["config_ids"] = [int(x.strip()) for x in arguments["config_ids"].split(",")]
        if arguments.get("runs"):
            # Parse JSON if provided as string
            runs = arguments["runs"]
            if isinstance(runs, str):
                data["runs"] = json.loads(runs)
            else:
                data["runs"] = runs
        
        result = await client.plans.add_plan_entry(plan_id, data)
        
        # Find the newly added entry in the response
        entries = result.get('entries', [])
        new_entry = entries[-1] if entries else {}
        
        output = f"**Plan Entry Added to Plan {plan_id}**\n\n"
        output += f"Entry: {new_entry.get('name', 'Unnamed Entry')}\n"
        output += f"  └─ Suite ID: {new_entry.get('suite_id', 'N/A')}\n"
        output += f"  └─ Entry ID: {new_entry.get('id', 'N/A')}\n"
        
        runs = new_entry.get('runs', [])
        if runs:
            output += f"  └─ Runs Created: {len(runs)}\n"
            for run in runs:
                output += f"     • Run {run.get('id')}: {run.get('name')}\n"
        
        response = create_success_response(
            f"Successfully added entry to plan {plan_id}",
            {"plan": result, "entry": new_entry, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in add_plan_entry: {str(e)}")
        response = create_error_response("Failed to add plan entry", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_update_plan_entry(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Update an existing plan entry"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        plan_id = int(arguments["plan_id"])
        entry_id = arguments["entry_id"]
        data = {}
        
        # Optional fields
        if arguments.get("name"):
            data["name"] = arguments["name"]
        if arguments.get("description"):
            data["description"] = arguments["description"]
        if arguments.get("assignedto_id"):
            data["assignedto_id"] = int(arguments["assignedto_id"])
        if arguments.get("include_all"):
            data["include_all"] = arguments["include_all"].lower() == "true"
        if arguments.get("case_ids"):
            data["case_ids"] = [int(x.strip()) for x in arguments["case_ids"].split(",")]
        if arguments.get("config_ids"):
            data["config_ids"] = [int(x.strip()) for x in arguments["config_ids"].split(",")]
        
        if not data:
            response = create_error_response("No update fields provided", Exception("No fields specified"))
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
        result = await client.plans.update_plan_entry(plan_id, entry_id, data)
        
        output = f"**Plan Entry Updated**\n\n"
        output += f"Entry ID: {result.get('id', entry_id)}\n"
        output += f"  └─ Name: {result.get('name', 'N/A')}\n"
        output += f"  └─ Suite ID: {result.get('suite_id', 'N/A')}\n"
        
        response = create_success_response(
            f"Successfully updated entry {entry_id} in plan {plan_id}",
            {"entry": result, "formatted": truncate_output(output)}
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in update_plan_entry: {str(e)}")
        response = create_error_response("Failed to update plan entry", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_plan_entry(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Delete a plan entry"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    try:
        plan_id = int(arguments["plan_id"])
        entry_id = arguments["entry_id"]
        
        await client.plans.delete_plan_entry(plan_id, entry_id)
        
        response = create_success_response(
            f"Successfully deleted entry {entry_id} from plan {plan_id}",
            {
                "plan_id": plan_id,
                "entry_id": entry_id,
                "formatted": f"Entry {entry_id} has been removed from plan {plan_id}"
            }
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in delete_plan_entry: {str(e)}")
        response = create_error_response("Failed to delete plan entry", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
