"""Operational metrics tracking for TestRail MCP server

This module provides centralized metrics collection for monitoring server health,
performance, and operational insights.
"""

import time
import logging
from datetime import datetime
from threading import Lock
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Global metrics store
_metrics = {
    "server_start_time": time.time(),
    "requests": {
        "total": 0,
        "successful": 0,
        "failed": 0,
    },
    "cache": {
        "hits": 0,
        "misses": 0,
    },
    "last_api_call": None,  # ISO 8601 timestamp
}

# Thread-safe lock for metrics updates
_metrics_lock = Lock()


def get_server_start_time() -> float:
    """Get server start timestamp"""
    return _metrics["server_start_time"]


def get_uptime_seconds() -> float:
    """Get server uptime in seconds"""
    return time.time() - _metrics["server_start_time"]


def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format (e.g., '2h 34m 15s')
    
    Args:
        seconds: Uptime in seconds
        
    Returns:
        str: Formatted uptime string
    """
    seconds = int(seconds)
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:  # Always show seconds if nothing else
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def record_request_success():
    """Record a successful API request"""
    with _metrics_lock:
        _metrics["requests"]["total"] += 1
        _metrics["requests"]["successful"] += 1
        _metrics["last_api_call"] = datetime.utcnow().isoformat() + "Z"


def record_request_failure():
    """Record a failed API request"""
    with _metrics_lock:
        _metrics["requests"]["total"] += 1
        _metrics["requests"]["failed"] += 1


def record_cache_hit():
    """Record a cache hit"""
    with _metrics_lock:
        _metrics["cache"]["hits"] += 1


def record_cache_miss():
    """Record a cache miss"""
    with _metrics_lock:
        _metrics["cache"]["misses"] += 1


def get_request_stats() -> Dict[str, Any]:
    """Get request statistics
    
    Returns:
        dict: Request metrics including total, successful, failed, and error rate
    """
    with _metrics_lock:
        total = _metrics["requests"]["total"]
        successful = _metrics["requests"]["successful"]
        failed = _metrics["requests"]["failed"]
        
        error_rate = 0.0
        if total > 0:
            error_rate = round((failed / total) * 100, 2)
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "error_rate": error_rate
        }


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics
    
    Returns:
        dict: Cache metrics including hits, misses, and hit rate
    """
    with _metrics_lock:
        hits = _metrics["cache"]["hits"]
        misses = _metrics["cache"]["misses"]
        
        total_cache_requests = hits + misses
        hit_rate = 0.0
        if total_cache_requests > 0:
            hit_rate = round((hits / total_cache_requests) * 100, 2)
        
        return {
            "hits": hits,
            "misses": misses,
            "hit_rate": hit_rate
        }


def get_last_api_call() -> Optional[str]:
    """Get timestamp of last successful API call
    
    Returns:
        str: ISO 8601 timestamp or None if no calls made yet
    """
    with _metrics_lock:
        return _metrics["last_api_call"]


def get_seconds_since_last_call() -> Optional[float]:
    """Get seconds since last API call
    
    Returns:
        float: Seconds since last call or None if no calls made yet
    """
    last_call = get_last_api_call()
    if not last_call:
        return None
    
    try:
        # Parse ISO 8601 timestamp
        last_call_time = datetime.fromisoformat(last_call.replace("Z", "+00:00"))
        current_time = datetime.utcnow().replace(tzinfo=last_call_time.tzinfo)
        delta = current_time - last_call_time
        return round(delta.total_seconds(), 2)
    except Exception as e:
        logger.warning(f"Error calculating time since last call: {e}")
        return None


def get_all_metrics() -> Dict[str, Any]:
    """Get all metrics in a structured format
    
    Returns:
        dict: Complete metrics snapshot
    """
    uptime_secs = get_uptime_seconds()
    
    return {
        "uptime_seconds": round(uptime_secs, 2),
        "uptime_formatted": format_uptime(uptime_secs),
        "requests": get_request_stats(),
        "cache": get_cache_stats(),
        "timing": {
            "last_api_call": get_last_api_call(),
            "seconds_since_last_call": get_seconds_since_last_call()
        }
    }


def reset_metrics():
    """Reset all metrics (useful for testing)"""
    with _metrics_lock:
        _metrics["server_start_time"] = time.time()
        _metrics["requests"]["total"] = 0
        _metrics["requests"]["successful"] = 0
        _metrics["requests"]["failed"] = 0
        _metrics["cache"]["hits"] = 0
        _metrics["cache"]["misses"] = 0
        _metrics["last_api_call"] = None
    logger.info("All metrics reset")
