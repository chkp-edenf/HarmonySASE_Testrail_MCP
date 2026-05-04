"""Re-export shim — relocated to testrail_core.schemas.results (plan-004 phase 5)."""
from testrail_core.schemas.results import (
    AddResultForCaseInput,
    AddResultPayload,
    AddResultsForCasesInput,
    AddResultsPayload,
    GetResultsForCaseInput,
    GetResultsForRunInput,
    GetResultsInput,
    Result,
    ResultsResponse
)

__all__ = [
    "AddResultForCaseInput",
    "AddResultPayload",
    "AddResultsForCasesInput",
    "AddResultsPayload",
    "GetResultsForCaseInput",
    "GetResultsForRunInput",
    "GetResultsInput",
    "Result",
    "ResultsResponse"
]
