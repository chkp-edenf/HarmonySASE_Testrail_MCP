"""Shared case type mappings cache for TestRail MCP

Case types are fully customizable by TestRail admins.
This cache dynamically learns from your TestRail instance.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_HOURS = 24

# Shared in-memory cache
_case_type_cache = {
    "case_types": [],
    "name_to_id": {},
    "id_to_name": {},
    "last_updated": None
}


def get_cache() -> dict:
    """Get reference to the shared case type cache"""
    return _case_type_cache


def invalidate_cache():
    """Invalidate the cache"""
    global _case_type_cache
    _case_type_cache["case_types"] = []
    _case_type_cache["name_to_id"] = {}
    _case_type_cache["id_to_name"] = {}
    _case_type_cache["last_updated"] = None
    logger.info("Case type cache invalidated")


def is_cache_valid() -> bool:
    """Check if cache is still valid based on TTL"""
    last_updated = _case_type_cache["last_updated"]
    if not last_updated:
        return False
    try:
        cache_time = datetime.fromisoformat(last_updated)
        expiry_time = cache_time + timedelta(hours=CACHE_TTL_HOURS)
        return datetime.now() < expiry_time
    except Exception:
        return False


def update_cache(case_types: list):
    """Update cache with case types from TestRail API"""
    global _case_type_cache
    
    name_to_id = {}
    id_to_name = {}
    
    for case_type in case_types:
        type_id = case_type.get("id")
        name = case_type.get("name", "").lower()
        
        if type_id:
            # Map name to ID (case-insensitive)
            if name:
                name_to_id[name] = type_id
            
            # Store ID to name mapping for display
            id_to_name[type_id] = case_type.get("name", f"Type {type_id}")
    
    _case_type_cache["case_types"] = case_types
    _case_type_cache["name_to_id"] = name_to_id
    _case_type_cache["id_to_name"] = id_to_name
    _case_type_cache["last_updated"] = datetime.now().isoformat()
    
    logger.info(f"Case type cache updated: {len(case_types)} types")


def resolve_case_type(type_value: str) -> int:
    """Resolve case type name or ID to numeric ID using cache"""
    from .metrics import record_cache_hit, record_cache_miss
    
    if not is_cache_valid():
        record_cache_miss()
        raise ValueError(
            "Case type cache not initialized. Call get_case_types first."
        )
    
    # Try as numeric ID
    try:
        type_id = int(type_value)
        if type_id in _case_type_cache["id_to_name"]:
            record_cache_hit()
            return type_id
        else:
            record_cache_miss()
            raise ValueError(f"Case type ID {type_id} not found")
    except (ValueError, TypeError):
        pass
    
    # Try as type name (case-insensitive)
    if isinstance(type_value, str):
        normalized = type_value.lower().strip()
        if normalized in _case_type_cache["name_to_id"]:
            record_cache_hit()
            return _case_type_cache["name_to_id"][normalized]
    
    record_cache_miss()
    available = ", ".join(sorted(set(_case_type_cache["name_to_id"].keys())))
    raise ValueError(
        f"Cannot resolve case type '{type_value}'. Available: {available}"
    )


def get_case_type_name(type_id: int) -> str:
    """Get display name for a case type ID"""
    if is_cache_valid():
        return _case_type_cache["id_to_name"].get(type_id, f"Unknown ({type_id})")
    return f"Type {type_id}"
