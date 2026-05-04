"""Re-export shim — relocated to testrail_core.schemas.cases (plan-004 phase 5)."""
from testrail_core.schemas.cases import (
    AddCaseInput,
    AddCasePayload,
    CasesResponse,
    CopyCasesPayload,
    GetCaseInput,
    GetCasesInput,
    MoveCasesPayload,
    TestCase,
    UpdateCasePayload,
)

__all__ = [
    "AddCaseInput",
    "AddCasePayload",
    "CasesResponse",
    "CopyCasesPayload",
    "GetCaseInput",
    "GetCasesInput",
    "MoveCasesPayload",
    "TestCase",
    "UpdateCasePayload",
]
