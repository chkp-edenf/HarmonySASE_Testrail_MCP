"""MCP Tool Registration

This module provides centralized tool registration and routing.
Returns a dictionary mapping tool names to their handler functions,
enabling clean dispatch through a single call handler.
"""

from typing import Callable, Awaitable
from mcp.types import TextContent
from ...client.api import TestRailClient

# Import all handlers
from .projects import handle_get_projects, handle_get_project
from .suites import handle_get_suites, handle_get_suite, handle_add_suite, handle_update_suite, handle_delete_suite
from .sections import (
    handle_get_sections, handle_get_section, handle_add_section,
    handle_update_section, handle_delete_section, handle_move_section
)
from .cases import (
    handle_get_cases, handle_get_case, handle_add_case, handle_update_case,
    handle_delete_case, handle_get_case_history, handle_copy_cases_to_section,
    handle_move_cases_to_section, handle_update_cases, handle_delete_cases
)
from .tests import handle_get_tests, handle_get_test
from .runs import (
    handle_get_runs, handle_get_run, handle_add_run, handle_update_run,
    handle_close_run, handle_delete_run
)
from .results import (
    handle_get_results, handle_get_results_for_case, handle_get_results_for_run,
    handle_add_result, handle_add_results
)
from .case_fields import handle_get_case_fields, handle_get_case_types, handle_get_priorities
from .statuses import handle_get_statuses
from .health import handle_get_server_health


# Type alias for handler functions
ToolHandler = Callable[[dict, TestRailClient], Awaitable[list[TextContent]]]


def get_tool_handlers() -> dict[str, ToolHandler]:
    """Get routing map of tool names to handler functions
    
    Returns:
        Dictionary mapping tool names to async handler functions
    """
    return {
        # Projects
        "get_projects": handle_get_projects,
        "get_project": handle_get_project,
        
        # Suites
        "get_suites": handle_get_suites,
        "get_suite": handle_get_suite,
        "add_suite": handle_add_suite,
        "update_suite": handle_update_suite,
        "delete_suite": handle_delete_suite,
        
        # Sections
        "get_sections": handle_get_sections,
        "get_section": handle_get_section,
        "add_section": handle_add_section,
        "update_section": handle_update_section,
        "delete_section": handle_delete_section,
        "move_section": handle_move_section,
        
        # Cases
        "get_cases": handle_get_cases,
        "get_case": handle_get_case,
        "add_case": handle_add_case,
        "update_case": handle_update_case,
        "delete_case": handle_delete_case,
        "get_case_history": handle_get_case_history,
        "copy_cases_to_section": handle_copy_cases_to_section,
        "move_cases_to_section": handle_move_cases_to_section,
        "update_cases": handle_update_cases,
        "delete_cases": handle_delete_cases,
        
        # Tests
        "get_tests": handle_get_tests,
        "get_test": handle_get_test,
        
        # Runs
        "get_runs": handle_get_runs,
        "get_run": handle_get_run,
        "add_run": handle_add_run,
        "update_run": handle_update_run,
        "close_run": handle_close_run,
        "delete_run": handle_delete_run,
        
        # Results
        "get_results": handle_get_results,
        "get_results_for_case": handle_get_results_for_case,
        "get_results_for_run": handle_get_results_for_run,
        "add_result": handle_add_result,
        "add_results": handle_add_results,
        
        # Metadata
        "get_case_fields": handle_get_case_fields,
        "get_case_types": handle_get_case_types,
        "get_priorities": handle_get_priorities,
        "get_statuses": handle_get_statuses,
        
        # Health
        "get_server_health": handle_get_server_health,
    }


__all__ = [
    "get_tool_handlers",
    # Re-export handlers for backwards compatibility
    "handle_get_projects",
    "handle_get_project",
    "handle_get_suites",
    "handle_get_suite",
    "handle_add_suite",
    "handle_update_suite",
    "handle_delete_suite",
    "handle_get_sections",
    "handle_get_section",
    "handle_add_section",
    "handle_update_section",
    "handle_delete_section",
    "handle_move_section",
    "handle_get_cases",
    "handle_get_case",
    "handle_add_case",
    "handle_update_case",
    "handle_delete_case",
    "handle_get_case_history",
    "handle_copy_cases_to_section",
    "handle_move_cases_to_section",
    "handle_update_cases",
    "handle_delete_cases",
    "handle_get_tests",
    "handle_get_test",
    "handle_get_runs",
    "handle_get_run",
    "handle_add_run",
    "handle_update_run",
    "handle_close_run",
    "handle_delete_run",
    "handle_get_results",
    "handle_get_results_for_case",
    "handle_get_results_for_run",
    "handle_add_result",
    "handle_add_results",
    "handle_get_case_fields",
    "handle_get_case_types",
    "handle_get_priorities",
    "handle_get_statuses",
    "handle_get_server_health",
]

