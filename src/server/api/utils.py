"""Utility functions for response formatting"""

from typing import Any, Dict, Union
from datetime import datetime
from pydantic import BaseModel


def create_success_response(message: str, data: Any) -> Dict[str, Any]:
    """Create standardized success response
    
    Args:
        message: Success message
        data: Response data (can be dict, Pydantic model, or any JSON-serializable type)
    
    Returns:
        Standardized success response dictionary
    """
    # If data is a Pydantic model, convert to dict
    if isinstance(data, BaseModel):
        data = data.model_dump()
    
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }


def create_error_response(message: str, error: Union[Exception, str, None]) -> Dict[str, Any]:
    """Create standardized error response
    
    Args:
        message: Error message
        error: Exception, error string, or None
    
    Returns:
        Standardized error response dictionary
    """
    error_str = str(error) if error else None
    
    return {
        "success": False,
        "message": message,
        "error": error_str,
        "timestamp": datetime.utcnow().isoformat()
    }


def format_project(project: Dict[str, Any]) -> str:
    """Format a single project for display"""
    output = f"**{project.get('name', 'Unnamed')}** (ID: {project.get('id')})\n"
    output += f"  └─ URL: {project.get('url', 'N/A')}\n"
    output += f"  └─ Completed: {project.get('is_completed', False)}\n"
    return output


def format_suite(suite: Dict[str, Any]) -> str:
    """Format a single suite for display"""
    output = f"**{suite.get('name', 'Unnamed')}** (ID: {suite.get('id')})\n"
    output += f"  └─ Description: {suite.get('description', 'N/A')}\n"
    output += f"  └─ URL: {suite.get('url', 'N/A')}\n"
    return output


def format_section(section: Dict[str, Any]) -> str:
    """Format a single section for display"""
    output = f"**{section.get('name', 'Unnamed')}** (ID: {section.get('id')})\n"
    if section.get('description'):
        output += f"  └─ Description: {section.get('description')}\n"
    output += f"  └─ Suite ID: {section.get('suite_id', 'N/A')}\n"
    output += f"  └─ Parent ID: {section.get('parent_id', 'None')}\n"
    output += f"  └─ Depth: {section.get('depth', 0)}\n"
    return output


def format_case(case: Dict[str, Any]) -> str:
    """Format a single test case for display"""
    output = f"**{case.get('title', 'Untitled')}** (ID: {case.get('id')})\n"
    output += f"  └─ Section ID: {case.get('section_id', 'N/A')}\n"
    output += f"  └─ Priority: {case.get('priority_id', 'N/A')}\n"
    output += f"  └─ Type: {case.get('type_id', 'N/A')}\n"
    return output


def format_test(test: Dict[str, Any]) -> str:
    """Format a single test for display"""
    output = f"**{test.get('title', 'Untitled')}** (ID: {test.get('id')})\n"
    output += f"  └─ Case ID: {test.get('case_id', 'N/A')}\n"
    output += f"  └─ Status ID: {test.get('status_id', 'N/A')}\n"
    output += f"  └─ Assigned To: {test.get('assignedto_id', 'N/A')}\n"
    return output


def truncate_output(text: str, max_size: int = 100000) -> str:
    """Truncate output if it exceeds max size"""
    if len(text) > max_size:
        return text[:max_size] + f"\n\n Output truncated (exceeded {max_size} bytes)"
    return text

