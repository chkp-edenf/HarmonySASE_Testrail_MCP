"""Re-export shim — relocated to testrail_core.schemas.statuses (plan-004 phase 5)."""
from testrail_core.schemas.statuses import (
    Status,
    StatusesResponse
)

__all__ = [
    "Status",
    "StatusesResponse"
]
