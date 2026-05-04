"""Server-side access control for tool dispatch.

`configure_access()` reads env flags once at startup and stores them on
module-level state. `enforce_access()` runs before every tool dispatch in
`stdio.py:call_tool()` and raises `McpError` (-32603) when a call is
disallowed. The dispatcher must call `enforce_access()` BEFORE invoking
the handler so no work touches the TestRail HTTP client when blocked.

Env flags handled here:
- `TESTRAIL_READ_ONLY` (Phase 1) — when truthy, every tool name in
  `WRITE_TOOL_NAMES` is rejected.

Future phases extend this module:
- `TESTRAIL_ALLOWED_TOOLS` (Phase 2)
"""
from __future__ import annotations

import logging
import os
from collections.abc import Mapping

from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData

logger = logging.getLogger(__name__)

# Tool names that mutate state. Sourced from `get_tool_handlers()` in
# src/server/api/__init__.py. A test asserts this set matches the
# verb-prefix-derived set so adding a new write tool without updating
# this constant fails CI.
WRITE_TOOL_NAMES: frozenset[str] = frozenset({
    "add_suite", "update_suite", "delete_suite",
    "add_section", "update_section", "delete_section", "move_section",
    "add_case", "update_case", "delete_case",
    "copy_cases_to_section", "move_cases_to_section",
    "update_cases", "delete_cases",
    "add_run", "update_run", "close_run", "delete_run",
    "add_plan", "update_plan", "close_plan", "delete_plan",
    "add_plan_entry", "update_plan_entry", "delete_plan_entry",
    "add_result", "add_results", "add_result_for_case", "add_results_for_cases",
    "add_milestone", "update_milestone", "delete_milestone",
    "add_config_group", "add_config",
    "upload_attachment", "delete_attachment",
})


_TRUTHY_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})
_FALSY_VALUES: frozenset[str] = frozenset({"0", "false", "no", "off", ""})


# Module-level state mutated by configure_access().
_read_only: bool = False


def _parse_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY_VALUES


def _warn_unrecognized(env_var: str, raw_value: str) -> None:
    """Surface unrecognized boolean env values as a warning.

    Without this, `TESTRAIL_READ_ONLY=treu` silently disables the guard.
    """
    logger.warning(
        "[testrail-mcp] WARNING: unrecognized %s='%s', defaulting to OFF "
        "(expected one of: 1/true/yes/on, 0/false/no/off)",
        env_var,
        raw_value,
    )


def configure_access(env: Mapping[str, str] | None = None) -> None:
    """Resolve access-control flags from env and log the mode.

    Call once from `main()` before registering the call_tool handler.
    """
    global _read_only
    src: Mapping[str, str] = env if env is not None else os.environ

    raw = src.get("TESTRAIL_READ_ONLY")
    _read_only = _parse_truthy(raw)
    if (
        raw is not None
        and raw.strip().lower() not in _TRUTHY_VALUES
        and raw.strip().lower() not in _FALSY_VALUES
    ):
        _warn_unrecognized("TESTRAIL_READ_ONLY", raw)

    logger.info(
        "[testrail-mcp] read-only mode: %s",
        "ON" if _read_only else "OFF",
    )


def is_read_only() -> bool:
    return _read_only


def enforce_access(tool_name: str) -> None:
    """Raise McpError if dispatch of `tool_name` is disallowed.

    No-op when access is allowed.
    """
    if _read_only and tool_name in WRITE_TOOL_NAMES:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=(
                f"TestRail MCP is in read-only mode (TESTRAIL_READ_ONLY=1). "
                f"Tool '{tool_name}' is blocked."
            ),
        ))
