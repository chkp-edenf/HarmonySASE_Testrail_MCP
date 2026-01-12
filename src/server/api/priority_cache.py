"""Shared priority mappings cache for TestRail MCP

Priorities are fully customizable by TestRail admins - no defaults exist.
This cache dynamically learns from your TestRail instance.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_HOURS = 24

# Shared in-memory cache
_priority_cache = {
    "priorities": [],
    "name_to_id": {},
    "id_to_name": {},
    "last_updated": None
}


def get_cache() -> dict:
    """Get reference to the shared priority cache"""
    return _priority_cache


def invalidate_cache():
    """Invalidate the cache"""
    global _priority_cache
    _priority_cache["priorities"] = []
    _priority_cache["name_to_id"] = {}
    _priority_cache["id_to_name"] = {}
    _priority_cache["last_updated"] = None
    logger.info("Priority cache invalidated")


def is_cache_valid() -> bool:
    """Check if cache is still valid based on TTL"""
    last_updated = _priority_cache["last_updated"]
    if not last_updated:
        return False
    try:
        cache_time = datetime.fromisoformat(last_updated)
        expiry_time = cache_time + timedelta(hours=CACHE_TTL_HOURS)
        return datetime.now() < expiry_time
    except Exception:
        return False


def update_cache(priorities: list):
    """Update cache with priorities from TestRail API"""
    global _priority_cache
    
    name_to_id = {}
    id_to_name = {}
    
    for priority in priorities:
        priority_id = priority.get("id")
        name = priority.get("name", "").lower()
        short_name = priority.get("short_name", "").lower()
        
        if priority_id:
            # Map both name and short_name to ID (case-insensitive)
            if name:
                name_to_id[name] = priority_id
            if short_name:
                name_to_id[short_name] = priority_id
            
            # Store ID to name mapping for display
            id_to_name[priority_id] = priority.get("name", f"Priority {priority_id}")
    
    _priority_cache["priorities"] = priorities
    _priority_cache["name_to_id"] = name_to_id
    _priority_cache["id_to_name"] = id_to_name
    _priority_cache["last_updated"] = datetime.now().isoformat()
    
    logger.info(f"Priority cache updated: {len(priorities)} priorities")


def resolve_priority(priority_value: str) -> int:
    """Resolve priority name or ID to numeric ID using cache"""
    if not is_cache_valid():
        raise ValueError(
            "Priority cache not initialized. Call get_priorities first."
        )
    
    # Try as numeric ID
    try:
        priority_id = int(priority_value)
        if priority_id in _priority_cache["id_to_name"]:
            return priority_id
        else:
            raise ValueError(f"Priority ID {priority_id} not found")
    except (ValueError, TypeError):
        pass
    
    # Try as priority name (case-insensitive)
    if isinstance(priority_value, str):
        normalized = priority_value.lower().strip()
        if normalized in _priority_cache["name_to_id"]:
            return _priority_cache["name_to_id"][normalized]
    
    available = ", ".join(sorted(set(_priority_cache["name_to_id"].keys())))
    raise ValueError(
        f"Cannot resolve priority '{priority_value}'. Available: {available}"
    )


def get_priority_name(priority_id: int) -> str:
    """Get display name for a priority ID"""
    if is_cache_valid():
        return _priority_cache["id_to_name"].get(priority_id, f"Unknown ({priority_id})")
    return f"Priority {priority_id}"
