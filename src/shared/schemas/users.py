"""Re-export shim — relocated to testrail_core.schemas.users (plan-004 phase 5)."""
from testrail_core.schemas.users import (
    GetUserByEmailInput,
    GetUserInput,
    GetUsersInput,
    UserOutput
)

__all__ = [
    "GetUserByEmailInput",
    "GetUserInput",
    "GetUsersInput",
    "UserOutput"
]
