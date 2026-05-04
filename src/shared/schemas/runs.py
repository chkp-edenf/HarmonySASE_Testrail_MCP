"""Re-export shim — relocated to testrail_core.schemas.runs (plan-004 phase 5)."""
from testrail_core.schemas.runs import (
    AddRunPayload,
    GetRunInput,
    GetRunsInput,
    Run,
    RunsResponse,
    UpdateRunPayload
)

__all__ = [
    "AddRunPayload",
    "GetRunInput",
    "GetRunsInput",
    "Run",
    "RunsResponse",
    "UpdateRunPayload"
]
