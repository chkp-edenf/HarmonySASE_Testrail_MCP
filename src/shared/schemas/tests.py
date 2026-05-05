"""Re-export shim — relocated to testrail_core.schemas.tests (plan-004 phase 5)."""
from testrail_core.schemas.tests import (
    GetTestInput,
    GetTestsInput,
    Test,
    TestsResponse
)

__all__ = [
    "GetTestInput",
    "GetTestsInput",
    "Test",
    "TestsResponse"
]
