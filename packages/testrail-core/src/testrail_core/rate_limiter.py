"""Rate limiter for TestRail API requests"""

import asyncio
import time
import logging
from collections import deque
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API requests"""
    
    def __init__(self, max_requests: int = 180, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds (default 60s = 1 minute)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self._lock = asyncio.Lock()  # Async-safe lock
    
    async def acquire(self) -> bool:
        """
        Acquire permission to make a request.
        Returns True if request is allowed, blocks if rate limit exceeded.
        """
        async with self._lock:
            current_time = time.time()
            
            # Remove requests outside the window
            while self.requests and self.requests[0] < current_time - self.window_seconds:
                self.requests.popleft()
            
            # Check if we're at the limit
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest_request = self.requests[0]
                wait_time = (oldest_request + self.window_seconds) - current_time
                
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached ({self.max_requests} requests/{self.window_seconds}s). "
                        f"Waiting {wait_time:.2f}s..."
                    )
                    await asyncio.sleep(wait_time)
                    
                    # Clean up after waiting
                    current_time = time.time()
                    while self.requests and self.requests[0] < current_time - self.window_seconds:
                        self.requests.popleft()
            
            # Add current request
            self.requests.append(current_time)
            return True
    
    def reset(self):
        """Reset the rate limiter"""
        self.requests.clear()
        logger.info("Rate limiter reset")
    
    def get_stats(self) -> Dict[str, int]:
        """Get current rate limiter statistics"""
        current_time = time.time()
        # Count requests in current window
        recent_requests = [r for r in self.requests if r >= current_time - self.window_seconds]
        
        return {
            "requests_in_window": len(recent_requests),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "available_requests": max(0, self.max_requests - len(recent_requests))
        }


# Global rate limiter instance (180 requests per minute as per TestRail API limits)
rate_limiter = RateLimiter(max_requests=180, window_seconds=60)
