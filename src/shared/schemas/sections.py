"""Re-export shim — relocated to testrail_core.schemas.sections (plan-004 phase 5)."""
from testrail_core.schemas.sections import (
    AddSectionPayload,
    GetSectionsInput,
    MoveSectionPayload,
    Section,
    SectionsResponse,
    UpdateSectionPayload
)

__all__ = [
    "AddSectionPayload",
    "GetSectionsInput",
    "MoveSectionPayload",
    "Section",
    "SectionsResponse",
    "UpdateSectionPayload"
]
