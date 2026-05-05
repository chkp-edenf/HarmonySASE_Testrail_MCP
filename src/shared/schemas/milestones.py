"""Re-export shim — relocated to testrail_core.schemas.milestones (plan-004 phase 5)."""
from testrail_core.schemas.milestones import (
    AddMilestonePayload,
    GetMilestoneInput,
    GetMilestonesInput,
    Milestone,
    MilestonesResponse,
    UpdateMilestonePayload
)

__all__ = [
    "AddMilestonePayload",
    "GetMilestoneInput",
    "GetMilestonesInput",
    "Milestone",
    "MilestonesResponse",
    "UpdateMilestonePayload"
]
