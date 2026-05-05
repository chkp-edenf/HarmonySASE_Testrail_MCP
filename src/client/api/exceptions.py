"""Re-export shim — relocated to testrail_core.client.exceptions (plan-004 phase 5)."""
from testrail_core.client.exceptions import (
    TestRailAPIError,
    TestRailAuthenticationError,
    TestRailBadRequestError,
    TestRailError,
    TestRailNetworkError,
    TestRailNotFoundError,
    TestRailPermissionError,
    TestRailRateLimitError,
    TestRailServerError,
    TestRailTimeoutError,
)

__all__ = [
    "TestRailAPIError",
    "TestRailAuthenticationError",
    "TestRailBadRequestError",
    "TestRailError",
    "TestRailNetworkError",
    "TestRailNotFoundError",
    "TestRailPermissionError",
    "TestRailRateLimitError",
    "TestRailServerError",
    "TestRailTimeoutError",
]
