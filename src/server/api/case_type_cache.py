"""Re-export shim — relocated to testrail_core.cache.case_type_cache (plan-004 phase 5)."""
from testrail_core.cache.case_type_cache import *  # noqa: F401, F403
from testrail_core.cache import case_type_cache as _src
_case_type_cache = _src._case_type_cache  # preserve direct module-level access for tests
