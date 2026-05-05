"""Re-export shim — relocated to testrail_core.cache.status_cache (plan-004 phase 5)."""
from testrail_core.cache.status_cache import *  # noqa: F401, F403
from testrail_core.cache import status_cache as _src
_status_cache = _src._status_cache  # preserve direct module-level access for tests
