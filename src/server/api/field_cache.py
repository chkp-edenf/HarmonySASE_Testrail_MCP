"""Shared field mappings cache for TestRail MCP

This module provides a centralized cache for field mappings and required fields
that is shared across all tools (case_fields, cases, etc.) within the same
container session. Cache persists for 24 hours or until container restart.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_HOURS = 24  # Cache persists for 24 hours in memory

# Shared in-memory cache (persists during container lifetime)
_field_mappings_cache = {
    "fields": {},  # Will contain all custom field mappings
    "required_fields": [],
    "last_updated": None
}


def get_cache() -> dict:
    """Get reference to the shared cache"""
    return _field_mappings_cache


def invalidate_cache():
    """Invalidate the cache by clearing memory and setting expired timestamp"""
    global _field_mappings_cache
    _field_mappings_cache["fields"] = {}
    _field_mappings_cache["required_fields"] = []
    _field_mappings_cache["last_updated"] = None
    logger.info("Field mappings cache invalidated")


def is_cache_valid() -> bool:
    """Check if cache is still valid based on TTL"""
    last_updated = _field_mappings_cache["last_updated"]
    if not last_updated:
        return False
    try:
        cache_time = datetime.fromisoformat(last_updated)
        expiry_time = cache_time + timedelta(hours=CACHE_TTL_HOURS)
        return datetime.now() < expiry_time
    except Exception:
        return False


def update_cache(field_map: dict, required_fields: list):
    """Update the cache with new field mappings and required fields"""
    global _field_mappings_cache
    _field_mappings_cache["fields"] = field_map
    _field_mappings_cache["required_fields"] = required_fields
    _field_mappings_cache["last_updated"] = datetime.now().isoformat()
    logger.info(f"Cache updated: {len(field_map)} field mappings, {len(required_fields)} required fields")


def get_field_mapping(field_name: str) -> dict:
    """Get mapping for a specific field from cache"""
    if is_cache_valid():
        return _field_mappings_cache["fields"].get(field_name, {})
    return {}


def get_required_fields() -> list:
    """Get list of required field names from cache"""
    if is_cache_valid():
        return _field_mappings_cache["required_fields"]
    return []
