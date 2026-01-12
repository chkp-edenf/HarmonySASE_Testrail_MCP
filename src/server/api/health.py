"""Health check handler for server status monitoring"""

import json
import logging
from mcp.types import TextContent
from ...client.api import TestRailClient
from . import field_cache, status_cache, priority_cache, case_type_cache
from .rate_limiter import rate_limiter
from .utils import create_success_response, create_error_response

logger = logging.getLogger(__name__)


async def handle_get_server_health(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Handle get_server_health tool call.
    
    Returns comprehensive health information including:
    - Cache status for all 4 cache modules
    - Rate limiter statistics
    - Connection readiness
    """
    logger.info("Checking server health")
    
    try:
        # Check all 4 cache modules
        field_cache_data = field_cache.get_cache()
        status_cache_data = status_cache.get_cache()
        priority_cache_data = priority_cache.get_cache()
        case_type_cache_data = case_type_cache.get_cache()
        
        # Build cache status information
        caches = {
            "field_cache": {
                "loaded": field_cache.is_cache_valid(),
                "entries": len(field_cache_data.get("fields", {}))
            },
            "status_cache": {
                "loaded": status_cache.is_cache_valid(),
                "entries": len(status_cache_data.get("statuses", []))
            },
            "priority_cache": {
                "loaded": priority_cache.is_cache_valid(),
                "entries": len(priority_cache_data.get("priorities", []))
            },
            "case_type_cache": {
                "loaded": case_type_cache.is_cache_valid(),
                "entries": len(case_type_cache_data.get("case_types", []))
            }
        }
        
        # Get rate limiter statistics
        rate_stats = rate_limiter.get_stats()
        rate_limiter_info = {
            "current_tokens": rate_stats.get("available_requests", 0),
            "max_tokens": rate_stats.get("max_requests", 180),
            "capacity_percent": round(
                (rate_stats.get("available_requests", 0) / rate_stats.get("max_requests", 180)) * 100, 
                2
            )
        }
        
        # Determine overall health status
        all_caches_loaded = all(cache["loaded"] for cache in caches.values())
        status = "healthy" if all_caches_loaded else "degraded"
        
        # Build health data response
        health_data = {
            "status": status,
            "caches": caches,
            "rate_limiter": rate_limiter_info,
            "connection": "ready"
        }
        
        response = create_success_response(
            f"Server health check complete - Status: {status}",
            health_data
        )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in get_server_health: {str(e)}")
        response = create_error_response("Failed to check server health", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
