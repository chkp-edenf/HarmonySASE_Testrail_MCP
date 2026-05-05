"""Re-export shim — TestRailClient aggregator relocated to testrail_core.client (plan-004 phase 5)."""
from testrail_core.client import (
    BaseAPIClient,
    ClientConfig,
    TestRailAPIError,
    TestRailAuthenticationError,
    TestRailBadRequestError,
    TestRailClient,
    TestRailError,
    TestRailNetworkError,
    TestRailNotFoundError,
    TestRailPermissionError,
    TestRailRateLimitError,
    TestRailServerError,
    TestRailTimeoutError,
)

__all__ = [
    "TestRailClient",
    "BaseAPIClient",
    "ClientConfig",
    "TestRailError",
    "TestRailAPIError",
    "TestRailTimeoutError",
    "TestRailNetworkError",
    "TestRailAuthenticationError",
    "TestRailPermissionError",
    "TestRailNotFoundError",
    "TestRailBadRequestError",
    "TestRailRateLimitError",
    "TestRailServerError",
]
