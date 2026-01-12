"""Shared status mappings cache for TestRail MCP

This module provides a centralized cache for status mappings that is shared
across all tools within the same container session. Cache persists for 24 hours
or until container restart.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_HOURS = 24  # Cache persists for 24 hours in memory

# Shared in-memory cache (persists during container lifetime)
_status_cache = {
    "statuses": [],  # List of all statuses from TestRail
    "name_to_id": {},  # Map status names/labels to IDs
    "id_to_name": {},  # Map status IDs to names
    "last_updated": None
}


def get_cache() -> dict:
    """Get reference to the shared status cache"""
    return _status_cache


def invalidate_cache():
    """Invalidate the cache by clearing memory and setting expired timestamp"""
    global _status_cache
    _status_cache["statuses"] = []
    _status_cache["name_to_id"] = {}
    _status_cache["id_to_name"] = {}
    _status_cache["last_updated"] = None
    logger.info("Status cache invalidated")


def is_cache_valid() -> bool:
    """Check if cache is still valid based on TTL"""
    last_updated = _status_cache["last_updated"]
    if not last_updated:
        return False
    try:
        cache_time = datetime.fromisoformat(last_updated)
        expiry_time = cache_time + timedelta(hours=CACHE_TTL_HOURS)
        return datetime.now() < expiry_time
    except Exception:
        return False


def update_cache(statuses: list):
    """Update the cache with statuses from TestRail API
    
    Args:
        statuses: List of status dictionaries from get_statuses API
    """
    global _status_cache
    
    name_to_id = {}
    id_to_name = {}
    
    for status in statuses:
        status_id = status.get("id")
        name = status.get("name", "").lower()
        label = status.get("label", "").lower()
        
        if status_id:
            # Map both name and label to ID (case-insensitive)
            if name:
                name_to_id[name] = status_id
            if label:
                name_to_id[label] = status_id
            
            # Store ID to label mapping for display
            id_to_name[status_id] = status.get("label", status.get("name", f"Status {status_id}"))
    
    _status_cache["statuses"] = statuses
    _status_cache["name_to_id"] = name_to_id
    _status_cache["id_to_name"] = id_to_name
    _status_cache["last_updated"] = datetime.now().isoformat()
    
    logger.info(f"Status cache updated: {len(statuses)} statuses, {len(name_to_id)} name mappings")


def resolve_status(status_value: str) -> int:
    """Resolve status name or ID to numeric ID using cache
    
    Args:
        status_value: Either a numeric ID or name/label
    
    Returns:
        int: The resolved status ID
    
    Raises:
        ValueError: If status cannot be resolved or cache is invalid
    """
    if not is_cache_valid():
        raise ValueError(
            "Status cache not initialized. Call get_statuses first or ensure cache is populated."
        )
    
    # Try as numeric ID first
    try:
        status_id = int(status_value)
        # Verify it exists in our cache
        if status_id in _status_cache["id_to_name"]:
            return status_id
        else:
            raise ValueError(f"Status ID {status_id} not found in TestRail")
    except (ValueError, TypeError):
        pass
    
    # Try as status name/label (case-insensitive)
    if isinstance(status_value, str):
        normalized = status_value.lower().strip()
        
        if normalized in _status_cache["name_to_id"]:
            return _status_cache["name_to_id"][normalized]
    
    # If we get here, we couldn't resolve it
    available = ", ".join(sorted(set(_status_cache["name_to_id"].keys())))
    raise ValueError(
        f"Cannot resolve status '{status_value}'. Available: {available}"
    )


def get_status_name(status_id: int) -> str:
    """Get display name for a status ID
    
    Args:
        status_id: Numeric status ID
    
    Returns:
        str: Status label/name or "Unknown"
    """
    if is_cache_valid():
        return _status_cache["id_to_name"].get(status_id, f"Unknown ({status_id})")
    return f"Status {status_id}"
