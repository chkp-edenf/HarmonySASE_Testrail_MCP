"""Re-export shim — module relocated to testrail_core.rate_limiter.

This shim preserves the legacy import path `src.server.api.rate_limiter`
while plan-004 phase 5 moves the integration core into the
`testrail-core` package. To be removed in phase 5.11 once all importers
point at testrail_core directly.
"""
from testrail_core.rate_limiter import RateLimiter, rate_limiter

__all__ = ["RateLimiter", "rate_limiter"]
