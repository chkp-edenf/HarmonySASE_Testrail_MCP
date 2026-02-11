"""Utility functions for response formatting and filtering"""

from typing import Any, Dict, Union, List, Optional
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


def apply_filters(items: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply multiple field filters to a list of items (client-side filtering)
    
    This function performs client-side filtering on a list of dictionaries,
    returning only items that match ALL provided filter criteria (AND logic).
    This is useful when the TestRail API has limited server-side filtering.
    
    Args:
        items: List of dictionaries (response data from TestRail API)
        filters: Dictionary of field_name -> expected_value mappings
                 None values are skipped (allow optional filters)
    
    Returns:
        List of items that match all provided filters
    
    Examples:
        >>> tests = [
        ...     {"id": 1, "assignedto_id": 5, "priority_id": 2},
        ...     {"id": 2, "assignedto_id": 5, "priority_id": 3},
        ...     {"id": 3, "assignedto_id": 6, "priority_id": 2}
        ... ]
        >>> apply_filters(tests, {"assignedto_id": 5, "priority_id": 2})
        [{"id": 1, "assignedto_id": 5, "priority_id": 2}]
        
        >>> apply_filters(tests, {"assignedto_id": None})  # None values ignored
        [{"id": 1, ...}, {"id": 2, ...}, {"id": 3, ...}]
    
    Edge Cases:
        - Empty items list returns empty list
        - Empty filters dict returns all items unchanged
        - Missing fields in items are treated as non-matches for that filter
        - None filter values are skipped (allows optional filtering)
    """
    if not items:
        return []
    
    if not filters:
        return items
    
    # Filter out None values from filters (allow optional filters)
    active_filters = {k: v for k, v in filters.items() if v is not None}
    
    if not active_filters:
        return items
    
    filtered_items = []
    for item in items:
        # Check if item matches ALL filter criteria (AND logic)
        matches_all = True
        for field_name, expected_value in active_filters.items():
            # Get the field value from item, handle missing fields gracefully
            item_value = item.get(field_name)
            
            # If field doesn't exist or doesn't match, exclude this item
            if item_value != expected_value:
                matches_all = False
                break
        
        if matches_all:
            filtered_items.append(item)
    
    return filtered_items


def apply_name_filter(
    items: List[Dict[str, Any]],
    name: Optional[str],
    field: str = "name"
) -> List[Dict[str, Any]]:
    """Apply substring matching filter for name-based searches
    
    This function performs case-insensitive substring matching on a specified
    field in a list of dictionaries. Useful for searching users by name/email,
    projects by name, etc.
    
    Args:
        items: List of dictionaries to filter
        name: Search string for case-insensitive substring match
              If None or empty, returns all items unchanged
        field: Field name to search in (default: "name")
    
    Returns:
        List of items where the specified field contains the search string
    
    Examples:
        >>> users = [
        ...     {"id": 1, "name": "John Doe", "email": "john@example.com"},
        ...     {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
        ...     {"id": 3, "name": "Bob Johnson", "email": "bob@example.com"}
        ... ]
        >>> apply_name_filter(users, "john")
        [{"id": 1, "name": "John Doe", ...}, {"id": 3, "name": "Bob Johnson", ...}]
        
        >>> apply_name_filter(users, "john", field="email")
        [{"id": 1, "name": "John Doe", "email": "john@example.com"}]
        
        >>> apply_name_filter(users, None)  # None returns all
        [{"id": 1, ...}, {"id": 2, ...}, {"id": 3, ...}]
    
    Edge Cases:
        - Empty items list returns empty list
        - None or empty name returns all items unchanged
        - Missing field in items are excluded from results
        - Case-insensitive matching (e.g., "JOHN" matches "john")
        - Non-string field values are converted to string for matching
    """
    if not items:
        return []
    
    # If no search string provided, return all items
    if not name or name.strip() == "":
        return items
    
    # Convert search string to lowercase for case-insensitive matching
    search_string = name.lower()
    
    filtered_items = []
    for item in items:
        # Get the field value, handle missing fields gracefully
        field_value = item.get(field)
        
        # Skip items that don't have the field
        if field_value is None:
            continue
        
        # Convert field value to string and perform case-insensitive substring match
        field_str = str(field_value).lower()
        
        if search_string in field_str:
            filtered_items.append(item)
    
    return filtered_items

