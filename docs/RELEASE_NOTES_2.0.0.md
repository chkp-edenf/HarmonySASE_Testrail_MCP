# TestRail MCP Server v2.0.0

**Release date:** 2026-05-05

This is the v2.0.0 release. It hardens the server for embedding in
production LLM contexts, extracts the integration core into a separately
importable Python library, and reconciles the documented tool surface
with what the dispatcher actually exposes.

## Highlights

- **Server-side gates** — `TESTRAIL_READ_ONLY` blocks every write tool;
  `TESTRAIL_ALLOWED_TOOLS` narrows the surface to a comma-separated allow-list.
- **bun913 compat aliases** — drop-in replacement for the bun913 fork.
  Default-on; flip `TESTRAIL_LEGACY_ALIASES=0` once your client has migrated.
- **Optional cache preload** — `TESTRAIL_PRELOAD_CACHE=1` warms the four
  metadata caches at startup; failures are non-fatal.
- **`testrail-core` Python library** — HTTP client, retry, rate-limit, four
  metadata caches, Pydantic schemas, exception hierarchy, attachment
  handling, and the `TestRailClient` aggregator are now importable without
  loading the MCP runtime. See ADR-003.
- **Tool surface documented as flat** — 68 snake_case tools, one per
  TestRail v2 endpoint. The "15 consolidated tools" framing in earlier
  docs was aspirational; the dispatcher always exposed the flat set.

## Added

- `TESTRAIL_READ_ONLY` (default `0`) — write-block gate. PR #4 (+109 tests).
- `TESTRAIL_ALLOWED_TOOLS` (default unset = all) — tool allowlist. PR #5 (+25 tests).
- `TESTRAIL_LEGACY_ALIASES` (default `1`) — bun913 28-alias compat layer + generic camelCase->snake_case translator. PR #6 (+45 tests).
- `TESTRAIL_PRELOAD_CACHE` (default `0`) — startup metadata warm-up. PR #7 (+18 tests).
- `testrail-core` library (`packages/testrail-core/`) — Phase 5 extraction, 16 stacked PRs.

## Changed

- README, CLAUDE.md, USER_GUIDE rewritten for the flat 68-tool surface and the four new env vars.
- USER_GUIDE adds three new sections: **Read-Only Mode**, **Restricting the Tool Surface**, **bun913 Migration**.
- `testrail-core` package version bumped to `2.0.0`.

## Deprecated

The legacy import paths under `src/client/api/`, `src/shared/schemas/`,
and `src/server/api/{rate_limiter,*_cache}.py` are kept as thin re-export
shims for backward compatibility but new code should import from
`testrail_core.*` directly. The shims will be removed in a future major
release.

## Migration

**From v1.x** — no code or tool-name changes needed. Pin to `@v2.0.0`
in your `git+` URL.

**From the bun913 fork** — keep `TESTRAIL_LEGACY_ALIASES=1` (the default)
so your existing camelCase tool names continue to resolve. Migrate to the
canonical snake_case names at your own pace, then flip the flag to `0`.

## Packaging layout

- `testrail-mcp` (root `pyproject.toml`) — MCP wrapper. Stdio entry,
  68-tool dispatcher, server-side gates (read-only, allowlist, aliases,
  preload), per-resource handlers, health, metrics, wizard installer.
  Ships from `src/`.
- `testrail-core` (`packages/testrail-core/pyproject.toml`) — importable
  library. HTTP client, retry, rate-limit, four metadata caches,
  Pydantic schemas, exception hierarchy, attachment handling,
  `TestRailClient` aggregator. No MCP dependency. Ships from
  `packages/testrail-core/src/testrail_core/`.

`testrail-mcp` declares `testrail-core==2.0.0` as a runtime dep; the
workspace `tool.uv.sources` overrides this for local development so
both move together when consumed from this repository.

## Acknowledgments

Plan: `docs/plans/plan-004-testrail-mcp-v2.md`.
ADR: `docs/decisions/ADR-003-testrail-core-extraction.md`.
