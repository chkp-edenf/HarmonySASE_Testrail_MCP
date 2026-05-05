"""Re-export shim — relocated to testrail_core.cache.field_cache (plan-004 phase 5)."""
from testrail_core.cache.field_cache import (
    CACHE_TTL_HOURS,
    get_cache,
    get_field_mapping,
    get_required_fields,
    invalidate_cache,
    is_cache_valid,
    update_cache,
)

__all__ = [
    "CACHE_TTL_HOURS",
    "get_cache",
    "get_field_mapping",
    "get_required_fields",
    "invalidate_cache",
    "is_cache_valid",
    "update_cache",
]
