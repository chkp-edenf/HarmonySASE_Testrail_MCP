"""bun913 compatibility aliases.

Lets consumers migrating from `@bun913/mcp-testrail` keep their existing
flat camelCase tool names (`getCases`, `getProject`, `getCasesByIds`)
working without rewriting prompts. The alias layer:

- exposes 28 explicit alias `Tool(...)` definitions in `list_tools` when
  enabled, so the agent sees them as available.
- on each call, rewrites the incoming name + camelCase argument keys to
  the canonical snake_case form before the dispatcher applies the
  read-only / allowlist gates. Gates always check the canonical name.

Gated by `TESTRAIL_LEGACY_ALIASES` (default `1` = enabled). Set to `0`
to register only the canonical surface.

Resolution order on each call (in `stdio.py:call_tool`):
1. `resolve(name, args)` — explicit map first, then generic
   camelCase->snake_case fallback.
2. read-only gate (`access_control.enforce_access`).
3. allowlist gate (same).
4. handler dispatch.
"""
from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping
from typing import Any

from mcp.types import Tool

logger = logging.getLogger(__name__)


# Explicit alias map: bun913 camelCase tool name -> canonical snake_case
# tool name in this MCP. Frozen as of v2.0.0; if bun913 ships new tools,
# the generic camelCase->snake_case translator covers them as a fallback,
# and the explicit map gets updated in a follow-up release.
BUN913_ALIASES: dict[str, str] = {
    "getProjects": "get_projects",
    "getProject": "get_project",
    "getSuites": "get_suites",
    "getSuite": "get_suite",
    "getSections": "get_sections",
    "getSection": "get_section",
    "getCases": "get_cases",
    "getCase": "get_case",
    "getCasesByIds": "get_cases_by_ids",
    "getRuns": "get_runs",
    "getRun": "get_run",
    "getTests": "get_tests",
    "getTest": "get_test",
    "getResults": "get_results",
    "getResultsForCase": "get_results_for_case",
    "getResultsForRun": "get_results_for_run",
    "getCaseFields": "get_case_fields",
    "getCaseTypes": "get_case_types",
    "getPriorities": "get_priorities",
    "getStatuses": "get_statuses",
    "getTemplates": "get_templates",
    "getMilestones": "get_milestones",
    "getMilestone": "get_milestone",
    "getPlans": "get_plans",
    "getPlan": "get_plan",
    "getUsers": "get_users",
    "getUser": "get_user",
    "getUserByEmail": "get_user_by_email",
}


_TRUTHY_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})


# Module-level state mutated by configure_aliases().
# Default ON: existing bun913 callers keep working when they swap servers.
_enabled: bool = True


# Insert an underscore before any uppercase letter that isn't at the
# start of the string. Then lowercase. Idempotent on already-snake_case
# input because there are no uppercase letters left to match.
_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def camel_to_snake(name: str) -> str:
    """Convert a camelCase or PascalCase identifier to snake_case.

    Idempotent on already-snake_case input.
    """
    return _CAMEL_BOUNDARY.sub("_", name).lower()


def translate_args(args: Mapping[str, Any]) -> dict[str, Any]:
    """Convert top-level dict keys from camelCase to snake_case.

    Only top-level keys are translated. Values pass through unchanged
    (bun913 inputs are flat — nested objects, if any, are domain payloads
    we must not touch).
    """
    return {camel_to_snake(key): value for key, value in args.items()}


def is_enabled() -> bool:
    return _enabled


def configure_aliases(env: Mapping[str, str] | None = None) -> None:
    """Resolve TESTRAIL_LEGACY_ALIASES and log the mode.

    Call once from `main()` before tools are listed.
    """
    global _enabled
    src: Mapping[str, str] = env if env is not None else os.environ

    # Default ON when unset; explicit value parsed via the same truthy
    # rules used elsewhere in access_control.
    raw = src.get("TESTRAIL_LEGACY_ALIASES")
    _enabled = True if raw is None else raw.strip().lower() in _TRUTHY_VALUES

    if _enabled:
        logger.info(
            "[testrail-mcp] legacy aliases: ON (%d aliases registered)",
            len(BUN913_ALIASES),
        )
    else:
        logger.info("[testrail-mcp] legacy aliases: OFF")


def resolve(name: str, args: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    """Resolve an incoming tool name + args to canonical form.

    When aliases are disabled, returns the inputs unchanged (cast to
    a plain dict for arg-mutation safety in callers).

    When enabled:
    - explicit map hit -> canonical name from BUN913_ALIASES, args
      translated.
    - explicit map miss but the name contains uppercase letters ->
      generic camelCase->snake_case translator on both name and args
      (forward-compat for new bun913 tools we haven't added explicit
      entries for yet).
    - already-canonical (snake_case) name -> passthrough.
    """
    if not _enabled:
        return name, dict(args)

    canonical_name = BUN913_ALIASES.get(name)
    if canonical_name is not None:
        return canonical_name, translate_args(args)

    # Generic fallback: only triggers for non-canonical (uppercase-
    # containing) names. Avoids accidentally mangling identifiers a
    # canonical handler already understands.
    if any(ch.isupper() for ch in name):
        return camel_to_snake(name), translate_args(args)

    return name, dict(args)


def get_alias_tool_defs() -> list[Tool]:
    """Return alias `Tool(...)` definitions for `list_tools` registration.

    Empty list when aliases are disabled. Each alias is a thin Tool def
    that points the agent at the bun913 name; the dispatcher rewrites
    the call to the canonical handler before any work happens.

    Schema: each alias Tool() carries a generic open-object inputSchema
    because bun913's full per-tool schemas use camelCase names that we
    translate at dispatch time. The canonical Tool() definitions in
    `tools.py` carry the strict snake_case schemas the underlying
    handlers actually validate against. Listing both surfaces gives the
    agent a clear hint that the canonical names are preferred; the
    aliases are a migration aid, not a permanent contract.
    """
    if not _enabled:
        return []

    tool_defs: list[Tool] = []
    for alias_name, canonical_name in BUN913_ALIASES.items():
        tool_defs.append(
            Tool(
                name=alias_name,
                description=(
                    f"Legacy bun913 alias for `{canonical_name}`. "
                    "Accepts camelCase arguments (e.g. caseId, projectId) "
                    "which are translated to snake_case before dispatch. "
                    "Prefer the canonical tool name in new code."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": True,
                },
            )
        )
    return tool_defs
