"""Re-export shim — relocated to testrail_core.schemas.projects (plan-004 phase 5)."""
from testrail_core.schemas.projects import (
    GetProjectsInput,
    Project,
    ProjectsResponse
)

__all__ = [
    "GetProjectsInput",
    "Project",
    "ProjectsResponse"
]
