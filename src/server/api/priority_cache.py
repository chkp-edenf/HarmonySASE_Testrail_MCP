"""Re-export shim — relocated to testrail_core.cache.priority_cache (plan-004 phase 5)."""
from testrail_core.cache.priority_cache import *  # noqa: F401, F403
from testrail_core.cache import priority_cache as _src
_priority_cache = _src._priority_cache  # preserve direct module-level access for tests
