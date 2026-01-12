"""MCP Tool Definitions for TestRail

This module contains all Tool() schema definitions organized by resource type.
Separating tool definitions from stdio.py keeps the entry point clean and focused.
"""

from mcp.types import Tool


def get_all_tools() -> list[Tool]:
    """Get all TestRail MCP tool definitions"""
    return [
        # ==================== PROJECTS ====================
        Tool(
            name="get_projects",
            description="Get all TestRail projects",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_project",
            description="Get a specific project by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        
        # ==================== SUITES ====================
        Tool(
            name="get_suites",
            description="Get all test suites for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_suite",
            description="Get details of a specific test suite",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"}
                },
                "required": ["suite_id"]
            }
        ),
        Tool(
            name="add_suite",
            description="Create a new test suite",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "description": "Suite name"},
                    "description": {"type": "string", "description": "Suite description (optional)"}
                },
                "required": ["project_id", "name"]
            }
        ),
        Tool(
            name="update_suite",
            description="Update an existing test suite",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"},
                    "name": {"type": "string", "description": "New suite name (optional)"},
                    "description": {"type": "string", "description": "New suite description (optional)"}
                },
                "required": ["suite_id"]
            }
        ),
        Tool(
            name="delete_suite",
            description="Delete a test suite (soft delete)",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"}
                },
                "required": ["suite_id"]
            }
        ),
        
        # ==================== SECTIONS ====================
        Tool(
            name="get_sections",
            description="Get all sections for a project/suite",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "suite_id": {"type": "string", "description": "Suite ID (optional, filters sections by suite)"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_section",
            description="Get details of a specific section",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"}
                },
                "required": ["section_id"]
            }
        ),
        Tool(
            name="add_section",
            description="Create a new section in a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "description": "Section name"},
                    "description": {"type": "string", "description": "Section description (optional)"},
                    "suite_id": {"type": "string", "description": "Suite ID (optional, for multi-suite projects)"},
                    "parent_id": {"type": "string", "description": "Parent section ID (optional, for nested sections)"}
                },
                "required": ["project_id", "name"]
            }
        ),
        Tool(
            name="update_section",
            description="Update an existing section",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                    "name": {"type": "string", "description": "New section name (optional)"},
                    "description": {"type": "string", "description": "New section description (optional)"}
                },
                "required": ["section_id"]
            }
        ),
        Tool(
            name="delete_section",
            description="Delete a section (soft delete)",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"}
                },
                "required": ["section_id"]
            }
        ),
        Tool(
            name="move_section",
            description="Move section to different parent or change display order",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                    "parent_id": {"type": "string", "description": "New parent section ID (optional)"},
                    "after_id": {"type": "string", "description": "Section ID to place after (optional, for ordering)"}
                },
                "required": ["section_id"]
            }
        ),
        
        # ==================== CASES ====================
        Tool(
            name="get_cases",
            description="Get test cases for a project/suite with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "suite_id": {"type": "string", "description": "Suite ID (optional)"},
                    "limit": {"type": "string", "description": "Max results (default 250)"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_case",
            description="Get complete details of a specific test case",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Test case ID"}
                },
                "required": ["case_id"]
            }
        ),
        Tool(
            name="add_case",
            description="Create a new test case in a section. Use get_case_fields to discover available custom fields for your TestRail instance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                    "title": {"type": "string", "description": "Test case title"},
                    "template_id": {"type": "string", "description": "Template ID (optional)"},
                    "type_id": {"type": "string", "description": "Test case type ID (optional)"},
                    "priority_id": {"type": "string", "description": "Priority ID (optional)"},
                    "estimate": {"type": "string", "description": "Time estimate (optional)"},
                    "refs": {"type": "string", "description": "References/requirements (optional)"},
                    "custom_fields": {"type": "string", "description": "JSON object containing custom fields as key-value pairs. Example: '{\"custom_field1\": \"value\", \"custom_field2\": \"option1,option2\"}'. Use get_case_fields to discover available custom fields and their valid values for your TestRail instance. Field values can be provided as human-readable strings or numeric IDs - the MCP will convert them automatically. (optional)"}
                },
                "required": ["section_id", "title"]
            }
        ),
        Tool(
            name="update_case",
            description="Update an existing test case. Use get_case_fields to discover available custom fields for your TestRail instance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Test case ID"},
                    "title": {"type": "string", "description": "New title (optional)"},
                    "template_id": {"type": "string", "description": "Template ID (optional)"},
                    "type_id": {"type": "string", "description": "Test case type ID (optional)"},
                    "priority_id": {"type": "string", "description": "Priority ID (optional)"},
                    "estimate": {"type": "string", "description": "Time estimate (optional)"},
                    "refs": {"type": "string", "description": "References/requirements (optional)"},
                    "custom_fields": {"type": "string", "description": "JSON object containing custom fields as key-value pairs. Example: '{\"custom_field1\": \"new_value\", \"custom_field2\": \"updated_text\"}'. Use get_case_fields to discover available custom fields for your instance. (optional)"}
                },
                "required": ["case_id"]
            }
        ),
        Tool(
            name="delete_case",
            description="Delete a test case (soft delete)",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Test case ID"}
                },
                "required": ["case_id"]
            }
        ),
        Tool(
            name="get_case_history",
            description="Get the change history for a test case",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Test case ID"}
                },
                "required": ["case_id"]
            }
        ),
        Tool(
            name="copy_cases_to_section",
            description="Copy test cases to a different section",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Target section ID"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (e.g., '123,456,789')"}
                },
                "required": ["section_id", "case_ids"]
            }
        ),
        Tool(
            name="move_cases_to_section",
            description="Move test cases to a different section",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Target section ID"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (e.g., '123,456,789')"}
                },
                "required": ["section_id", "case_ids"]
            }
        ),
        Tool(
            name="update_cases",
            description="Bulk update test cases. Use get_case_fields to discover available custom fields for your TestRail instance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs"},
                    "priority_id": {"type": "string", "description": "New priority ID (optional)"},
                    "type_id": {"type": "string", "description": "New type ID (optional)"},
                    "template_id": {"type": "string", "description": "New template ID (optional)"},
                    "custom_fields": {"type": "string", "description": "JSON object containing custom fields to update as key-value pairs. Example: '{\"custom_field1\": \"value\", \"custom_field2\": \"option1,option2,option3\"}'. Use get_case_fields to discover available fields. (optional)"}
                },
                "required": ["suite_id", "case_ids"]
            }
        ),
        Tool(
            name="delete_cases",
            description="Bulk delete test cases (soft delete)",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs"}
                },
                "required": ["suite_id", "case_ids"]
            }
        ),
        
        # ==================== TESTS ====================
        Tool(
            name="get_tests",
            description="Get tests for a test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "status_id": {"type": "string", "description": "Filter by status ID (optional)"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="get_test",
            description="Get details of a specific test",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_id": {"type": "string", "description": "Test ID"}
                },
                "required": ["test_id"]
            }
        ),
        
        # ==================== RUNS ====================
        Tool(
            name="get_runs",
            description="Get test runs for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "limit": {"type": "string", "description": "Max results (default 250)"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_run",
            description="Get details of a specific test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="add_run",
            description="Create a new test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "description": "Run name"},
                    "description": {"type": "string", "description": "Run description (optional)"},
                    "suite_id": {"type": "string", "description": "Suite ID (optional)"},
                    "milestone_id": {"type": "string", "description": "Milestone ID (optional)"},
                    "assignedto_id": {"type": "string", "description": "User ID to assign (optional)"},
                    "include_all": {"type": "string", "description": "Include all cases: true/false (optional)"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (optional)"}
                },
                "required": ["project_id", "name"]
            }
        ),
        Tool(
            name="update_run",
            description="Update an existing test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "name": {"type": "string", "description": "New run name (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "milestone_id": {"type": "string", "description": "New milestone ID (optional)"},
                    "include_all": {"type": "string", "description": "Include all cases: true/false (optional)"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (optional)"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="close_run",
            description="Close a test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="delete_run",
            description="Delete a test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"}
                },
                "required": ["run_id"]
            }
        ),
        
        # ==================== RESULTS ====================
        Tool(
            name="get_results",
            description="Get results for a test",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_id": {"type": "string", "description": "Test ID"},
                    "limit": {"type": "string", "description": "Max results (default 250)"}
                },
                "required": ["test_id"]
            }
        ),
        Tool(
            name="get_results_for_case",
            description="Get results for a case in a run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "case_id": {"type": "string", "description": "Test case ID"},
                    "limit": {"type": "string", "description": "Max results (default 250)"}
                },
                "required": ["run_id", "case_id"]
            }
        ),
        Tool(
            name="get_results_for_run",
            description="Get all results for a run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "limit": {"type": "string", "description": "Max results (default 250)"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="add_result",
            description="Add a result for a test. Accepts status by ID or name (e.g., '1', 'passed', 'failed')",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_id": {"type": "string", "description": "Test ID"},
                    "status_id": {"type": "string", "description": "Status ID or name (e.g., '1', 'passed', 'failed', 'blocked')"},
                    "comment": {"type": "string", "description": "Result comment (optional)"},
                    "version": {"type": "string", "description": "Version tested (optional)"},
                    "elapsed": {"type": "string", "description": "Time elapsed (optional)"},
                    "defects": {"type": "string", "description": "Defects/bugs found (optional)"},
                    "assignedto_id": {"type": "string", "description": "Assigned user ID (optional)"}
                },
                "required": ["test_id", "status_id"]
            }
        ),
        Tool(
            name="add_results",
            description="Add results for multiple tests in a run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "results": {"type": "string", "description": "JSON array of results: [{\"test_id\": 1, \"status_id\": 1}, ...]"}
                },
                "required": ["run_id", "results"]
            }
        ),
        
        # ==================== METADATA ====================
        Tool(
            name="get_case_fields",
            description="Get all available case fields including custom fields and their possible values",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_case_types",
            description="Get all available case types and populate cache for smart resolution",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_priorities",
            description="Get all available priorities and populate cache for smart resolution",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_statuses",
            description="Get all available test statuses for use with test results",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        # ==================== HEALTH CHECK ====================
        Tool(
            name="get_server_health",
            description="Get server health status including cache status, rate limiter stats, and connection readiness",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]
