"""Main TestRail API client aggregator"""

from .base_client import BaseAPIClient, ClientConfig
from .projects import ProjectsClient
from .suites import SuitesClient
from .sections import SectionsClient
from .cases import CasesClient
from .tests import TestsClient
from .runs import RunsClient
from .plans import PlansClient
from .results import ResultsClient
from .case_fields import CaseFieldsClient
from .statuses import StatusesClient
from .users import UsersClient
from .milestones import MilestonesClient
from .configs import ConfigsClient
from .exceptions import (
    TestRailError,
    TestRailAPIError,
    TestRailTimeoutError,
    TestRailNetworkError,
    TestRailAuthenticationError,
    TestRailPermissionError,
    TestRailNotFoundError,
    TestRailBadRequestError,
    TestRailRateLimitError,
    TestRailServerError
)


class TestRailClient(BaseAPIClient):
    """Main TestRail API client with all resource clients"""
    
    def __init__(self, config: ClientConfig, rate_limiter=None):
        super().__init__(config, rate_limiter)
        # Pass self (BaseAPIClient instance) to resource clients
        # This ensures single auth setup and HTTP client pattern
        self.projects = ProjectsClient(self)
        self.suites = SuitesClient(self)
        self.sections = SectionsClient(self)
        self.cases = CasesClient(self)
        self.tests = TestsClient(self)
        self.runs = RunsClient(self)
        self.plans = PlansClient(self)
        self.results = ResultsClient(self)
        self.case_fields = CaseFieldsClient(self)
        self.statuses = StatusesClient(self)
        self.users = UsersClient(self)
        self.milestones = MilestonesClient(self)
        self.configs = ConfigsClient(self)


__all__ = [
    "TestRailClient",
    "ClientConfig",
    "TestRailError",
    "TestRailAPIError",
    "TestRailTimeoutError",
    "TestRailNetworkError",
    "TestRailAuthenticationError",
    "TestRailPermissionError",
    "TestRailNotFoundError",
    "TestRailBadRequestError",
    "TestRailRateLimitError",
    "TestRailServerError"
]
