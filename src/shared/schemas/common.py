"""Re-export shim — relocated to testrail_core.schemas.common (plan-004 phase 5)."""
from testrail_core.schemas.common import (
    ErrorResponse,
    PaginatedResponse,
    SuccessResponse,
)

__all__ = ["ErrorResponse", "PaginatedResponse", "SuccessResponse"]
