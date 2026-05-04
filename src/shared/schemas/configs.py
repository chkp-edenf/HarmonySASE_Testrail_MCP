"""Re-export shim — relocated to testrail_core.schemas.configs (plan-004 phase 5)."""
from testrail_core.schemas.configs import (
    AddConfigGroupInput,
    AddConfigInput,
    Config,
    ConfigGroup,
    GetConfigsInput
)

__all__ = [
    "AddConfigGroupInput",
    "AddConfigInput",
    "Config",
    "ConfigGroup",
    "GetConfigsInput"
]
