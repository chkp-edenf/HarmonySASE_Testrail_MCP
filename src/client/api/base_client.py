"""Re-export shim — relocated to testrail_core.client.base_client (plan-004 phase 5)."""
from testrail_core.client.base_client import BaseAPIClient, ClientConfig

__all__ = ["BaseAPIClient", "ClientConfig"]
