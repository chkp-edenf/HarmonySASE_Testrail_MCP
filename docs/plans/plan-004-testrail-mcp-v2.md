---
number: 4
title: TestRail MCP v2.0 — embedder-friendly hardening, library extraction, PyPI release
date: 2026-05-04
status: proposed
needs_tdd: true
route: B
adr: ADR-003-testrail-core-extraction.md
---

## Plan: TestRail MCP v2.0 [konstruct]

### Overview
Harden the TestRail MCP for downstream consumers and embedders by adding
server-side write protection, a tool allowlist, compatibility aliases for an
existing third-party fork, and an opt-in cache pre-warm. Extract the integration
core into a separately importable Python package so consumers can reuse the
HTTP client, caches, schemas, and rate limiter without spawning an MCP
subprocess. Publish both packages to PyPI as v2.0.0 and synchronise docs.

### Context (consumer-framed)
- Some consumers want to expose this server to LLM agents while guaranteeing
  no writes hit TestRail. They need a server-side switch, not a client-side
  contract — clients are not always trustworthy.
- Other consumers embed the server with a narrower tool surface (e.g. only
  the read tools they actually need). A coarse allowlist keeps tool discovery
  cheap and reduces surprise.
- A community fork (bun913) shipped earlier with a different tool naming
  convention (camelCase, slightly different verbs). Migrating consumers should
  not require a synchronized cutover; aliases make the switch reversible.
- Python consumers that do their own orchestration want the integration logic
  (HTTP, retry, rate-limit, schemas, cache) without paying the cost of an MCP
  subprocess. A separate `testrail-core` package solves this without forking
  the MCP server.
- v2.0.0 is the right time to do all of this in one coordinated release —
  the alias surface is a backwards-compatibility affordance, the package split
  is a forwards-compatibility affordance, and PyPI publishing is the
  distribution requirement that ties them together.

### Assumptions
- Repository layout today is a single Python package under `src/`; `pyproject.toml`
  uses hatchling. Phase 5 will migrate to a uv workspace with `packages/*/`.
- `uv` is the canonical package manager (per project CLAUDE.md). All commands
  wrap with `uv run`.
- The 36 write tools are a deterministic, code-derivable list:
  `add_*`, `update_*`, `delete_*`, `move_*`, `copy_*`, `close_*`, `upload_*`,
  `add_config`, `add_config_group`. Phase 0 verifies the exact count.
- "Tool" here means the underlying flat tool name as routed by the dispatcher
  (e.g. `add_case`, `delete_run`), not the user-facing consolidated names like
  `testrail_cases`. Action-based gating is out of scope for v2.0.
- The bun913 alias list (28 entries) in the high-level plan is authoritative.
- PyPI account / org for `testrail-mcp` and `testrail-core` is available, or
  Phase 6 owner will register before tagging v2.0.0.
- OIDC trusted-publishing on GitHub Actions is preferred but not required;
  fall back to API token stored as a repo secret if OIDC is impractical.
- Existing test suite uses `pytest` with `pytest.mark.parametrize` and is
  already structured per resource (per CLAUDE.md "Testing").

### Constraints
- Public-facing repo: motivation, ADRs, commit messages, code comments, and
  user-facing docs must stay generic. No internal product names, no internal
  architectures, no internal consumer references anywhere.
- No `--no-verify`, no force-push to `main`, no widening of linter/formatter
  configs (per global CLAUDE.md).
- Each phase = one PR (Phase 5 is the exception — multi-PR, see breakdown).
- Every phase must leave the codebase shippable; partial phases never merge.

### Phase 0: Research

- [ ] Step 0.1: Enumerate the exact set of write tools (S)
  - Action: grep the dispatcher / handler files for every `add_*`, `update_*`,
    `delete_*`, `move_*`, `copy_*`, `close_*`, `upload_*`, `add_config`,
    `add_config_group` route.
  - Files to inspect: `src/server/api/__init__.py`, `src/server/api/tools.py`,
    `src/server/api/<resource>.py`.
  - Verify: produce a checked-in list of 36 tool names matching the spec; if
    the count diverges, update the spec before Phase 1 starts.
  - Risk: Low.
- [ ] Step 0.2: Confirm dispatcher entry point and how tool names reach it (S)
  - Verify: the boundary where a name becomes an executed handler is a single
    function (or a small set). Phase 1's gate must live there.
- [ ] Step 0.3: Inventory cache modules and the exact APIs Phase 4 needs to call (S)
  - Files: `src/server/api/field_cache.py`, `status_cache.py`, `priority_cache.py`,
    `case_type_cache.py`, plus the metadata handler.
  - Verify: a one-liner per cache describing the warm-up entry function.
- [ ] Step 0.4: Read existing tests to confirm fixture and parametrize patterns (S)
  - Files: `tests/` (whichever resource files exist).
  - Verify: a note on whether new tests should subclass an existing fixture
    or stand alone.

### Phase 1: `TESTRAIL_READ_ONLY` write-protection gate

**Branch**: `feat/read-only-mode`
**PR scope**: env flag, dispatcher gate, startup log, tests, env-var doc stub.

- [ ] Step 1.1: Add module-level boolean read once at import time (S)
  - File: `src/server/api/__init__.py` (or `src/server/api/config.py` if a
    config module is preferred — Phase 0.2 will tell us).
  - Behavior: `READ_ONLY = os.getenv("TESTRAIL_READ_ONLY", "").strip().lower() in {"1","true","yes","on"}`.
  - Verify: import the module in a unit test, assert the flag reflects the env.
  - Risk: Low.
- [ ] Step 1.2: Define the canonical set of 36 write tool names as a frozen set (S)
  - File: same module as 1.1, constant `WRITE_TOOLS: frozenset[str]`.
  - Verify: unit test asserts `len(WRITE_TOOLS) == 36` and that each name
    routes to a handler in the dispatcher.
  - Depends on: 0.1.
- [ ] Step 1.3: Insert the gate in the dispatcher (M)
  - Behavior: when `READ_ONLY is True` and the requested tool is in
    `WRITE_TOOLS`, raise an MCP error with code `-32603` and message exactly:
    `TestRail MCP is in read-only mode (TESTRAIL_READ_ONLY=1). Tool '<name>' is blocked.`
  - Verify: dispatcher unit test parametrized across all 36 names, each
    asserts code + message.
  - Depends on: 1.1, 1.2.
  - Risk: Medium (must not change the success path for read tools).
- [ ] Step 1.4: Stderr startup log when read-only is active (S)
  - Behavior: in `src/stdio.py` startup path, after env validation, write
    `TESTRAIL_READ_ONLY=1 — write tools blocked` to stderr. Silent when off.
  - Verify: capture stderr in a test; assert presence/absence by env state.
  - Depends on: 1.1.
- [ ] Step 1.5: Tests (M)
  - File: `tests/server/test_read_only_gate.py`.
  - Parametrize matrix: 36 write tools (each blocked when on, each allowed
    when off) + a sample of 5 read tools (each unaffected when on).
  - Use `monkeypatch.setenv` for env state.
  - Verify: `uv run pytest tests/server/test_read_only_gate.py -v` passes;
    each parametrize id is human-readable (tool name).
  - Depends on: 1.3, 1.4.
- [ ] Step 1.6: Stub env-var documentation in `.env.example` (S)
  - Add `TESTRAIL_READ_ONLY=` (empty default, comment explains values).
  - Verify: file diff is one block; no other vars touched.
- [ ] Step 1.7: PR opens with conventional commit `feat(server): add TESTRAIL_READ_ONLY write-protection gate` and a Test plan section.

### Phase 2: `TESTRAIL_ALLOWED_TOOLS` allowlist

**Branch**: `feat/tool-allowlist`
**PR scope**: env parsing, dispatcher gate (chained after read-only), tests, doc.
**Depends on Phase 1 merged.**

- [ ] Step 2.1: CSV parser, parsed once at startup (S)
  - File: same config location as Phase 1.
  - Behavior: `ALLOWED_TOOLS: frozenset[str] | None`. `None` (env unset or empty
    after strip) means "all allowed". Whitespace tolerant: split on `,`, strip
    each entry, drop empty entries, lowercase preserved as written.
  - Verify: unit test for empty/unset/whitespace/duplicates/single/multi.
  - Risk: Low.
- [ ] Step 2.2: Dispatcher gate (M)
  - Behavior: chain order is **read-only first, allowlist second**. If
    `ALLOWED_TOOLS is not None` and the tool is not in it, raise MCP error
    `-32601` with message `Tool '<name>' is not in TESTRAIL_ALLOWED_TOOLS allowlist.`
    (`-32601` = method not found, the closest semantic match for "this tool is
    not exposed in this configuration").
  - Verify: dispatcher unit test asserts a write tool blocked by Phase 1 sees
    Phase 1's message (precedence), and a read tool excluded by allowlist sees
    Phase 2's message.
  - Depends on: 2.1, Phase 1.
- [ ] Step 2.3: Tests (M)
  - File: `tests/server/test_allowlist.py`.
  - Parametrize cases:
    - allowlist unset → all tools allowed
    - allowlist empty string → all tools allowed
    - allowlist `"get_cases"` → `get_cases` allowed, `get_runs` blocked
    - allowlist `" get_cases , get_runs "` (whitespace) → both allowed
    - read-only + allowlist that includes a write tool → still blocked by
      read-only (precedence test)
    - read-only off + allowlist excludes a write tool → blocked by allowlist
  - Verify: `uv run pytest tests/server/test_allowlist.py -v` passes.
  - Depends on: 2.2.
- [ ] Step 2.4: `.env.example` entry for `TESTRAIL_ALLOWED_TOOLS` (S).
- [ ] Step 2.5: PR — `feat(server): add TESTRAIL_ALLOWED_TOOLS tool allowlist`.

### Phase 3: bun913 compatibility aliases

**Branch**: `feat/bun913-aliases`
**PR scope**: alias map, request-rewrite layer, env gate, tests, migration note.
**Depends on Phase 2 merged.**

- [ ] Step 3.1: Codify the 28-entry alias map (S)
  - File: `src/server/api/aliases.py`.
  - Constant: `BUN913_ALIASES: dict[str, str]` mapping camelCase legacy name →
    canonical snake_case name.
  - Verify: unit test asserts `len(BUN913_ALIASES) == 28` and every value is a
    valid registered tool name (cross-checked against the dispatcher registry).
  - Risk: Low.
- [ ] Step 3.2: Generic camelCase→snake_case translator (S)
  - Behavior: only used as a fallback when an incoming tool name is not in the
    explicit alias map and not in the canonical registry. Pure function, no
    side effects.
  - Verify: unit tests for `addCase`→`add_case`, `getCasesByIds`→`get_cases_by_ids`,
    `bulkAddForCases`→`bulk_add_for_cases`, idempotency on already-snake_case input.
- [ ] Step 3.3: Env gate `TESTRAIL_LEGACY_ALIASES` (S)
  - Default `1` (aliases on). `0` disables both the explicit map and the
    generic translator.
  - Verify: unit test confirms gate behavior.
- [ ] Step 3.4: Wire alias resolution into the dispatcher entry (M)
  - Order of operations on each incoming call:
    1. If aliases enabled, resolve incoming name → canonical (explicit map
       first, then generic translator if name still unknown).
    2. Apply read-only gate (Phase 1) on the **canonical** name.
    3. Apply allowlist gate (Phase 2) on the **canonical** name.
    4. Dispatch.
  - Verify: dispatcher integration test asserts that gating uses the canonical
    name (e.g. `addCase` is blocked under read-only, allowlist `"add_case"`
    allows `addCase` calls).
  - Depends on: 3.1, 3.2, 3.3, Phase 1, Phase 2.
  - Risk: Medium (precedence matters; mistakes here defeat the gates).
- [ ] Step 3.5: Tests (M)
  - File: `tests/server/test_aliases.py`.
  - Parametrize:
    - all 28 explicit aliases resolve correctly
    - generic translator covers 5 representative camelCase patterns
    - aliases disabled → camelCase name returns "tool not found"
    - read-only + alias → canonical name is what gets gate-checked
    - allowlist + alias → canonical name is what gets gate-checked
  - Verify: `uv run pytest tests/server/test_aliases.py -v` passes.
  - Depends on: 3.4.
- [ ] Step 3.6: `.env.example` entry for `TESTRAIL_LEGACY_ALIASES` (S).
- [ ] Step 3.7: PR — `feat(server): add bun913 compatibility aliases (TESTRAIL_LEGACY_ALIASES)`.

### Phase 4: `TESTRAIL_PRELOAD_CACHE` startup warm-up

**Branch**: `feat/preload-cache`
**PR scope**: opt-in env flag, warm-up call site, failure-as-warning, tests.
**Depends on Phase 3 merged (or Phase 2 — no Phase 3 dependency, but ship in order).**

- [ ] Step 4.1: Add the env flag (S)
  - Default off. Same parsing convention as Phase 1.
  - Verify: unit test.
- [ ] Step 4.2: Warm-up function (M)
  - File: `src/server/api/cache_warmup.py` (new).
  - Behavior: call the existing fetchers for `case_fields`, `case_types`,
    `priorities`, `statuses`, `templates` in sequence (project_id is required —
    accept `TESTRAIL_PRELOAD_PROJECT_ID` env var; if missing, log a warning
    and skip warm-up gracefully).
  - Failure handling: each cache wrapped in `try/except`; on exception, log a
    warning to stderr with the cache name and error class, continue. Server
    must start regardless.
  - Verify: unit test with a stubbed client where one fetcher raises — assert
    server start completes and warning is emitted.
  - Risk: Medium — must not regress startup time when the flag is off.
- [ ] Step 4.3: Call from `src/stdio.py` startup, after client init, before
      registering tools (S).
  - Verify: integration test confirms warm-up runs only when flag is on.
  - Depends on: 4.1, 4.2.
- [ ] Step 4.4: Tests (M)
  - File: `tests/server/test_cache_warmup.py`.
  - Cases: flag off → no fetcher called; flag on + project_id → all five
    fetchers called once; flag on + project_id missing → warning + skip;
    flag on + one fetcher raises → other four still called, server still starts.
  - Verify: `uv run pytest tests/server/test_cache_warmup.py -v` passes.
- [ ] Step 4.5: `.env.example` entries for `TESTRAIL_PRELOAD_CACHE` and
      `TESTRAIL_PRELOAD_PROJECT_ID` (S).
- [ ] Step 4.6: PR — `feat(server): add TESTRAIL_PRELOAD_CACHE startup warm-up`.

### Phase 5: Extract `testrail-core` shared library

**Per ADR-003.** This phase is multi-PR. Cases is the canary; remaining
resources follow as small, independent PRs that each green CI before the next
opens. The workspace skeleton lands in PR 5.0; ADR-003 is committed in the
same PR.

**Workspace target layout**
```
packages/
  testrail-core/
    pyproject.toml
    src/testrail_core/
      __init__.py
      client/         # HTTP client, retry, rate-limit, exceptions, attachments
      cache/          # field, status, priority, case_type
      schemas/        # pydantic models, ported from src/shared/schemas
      api/            # per-resource client modules, ported one PR at a time
    tests/
  testrail-mcp/
    pyproject.toml
    src/testrail_mcp/
      stdio.py
      server/         # tool defs, handlers, dispatcher, gates from Phases 1-4
    tests/
pyproject.toml          # workspace root
uv.lock
```

#### PR 5.0: Workspace skeleton + ADR (M)

**Branch**: `refactor/workspace-skeleton`

- [ ] 5.0.1: Add ADR `docs/decisions/ADR-003-testrail-core-extraction.md`
  (already drafted alongside this plan).
- [ ] 5.0.2: Create `packages/testrail-core/` and `packages/testrail-mcp/`
  with empty `pyproject.toml` files and `src/` skeletons.
- [ ] 5.0.3: Convert root `pyproject.toml` to a uv workspace
  (`[tool.uv.workspace] members = ["packages/*"]`); keep top-level metadata
  minimal.
- [ ] 5.0.4: Both packages declare version `0.1.0-pre` so PR 5.0 publishes
  nothing; they bump to `2.0.0` only at Phase 6.
- [ ] 5.0.5: `uv sync` and `uv run pytest` still pass against the existing
  test suite (which still imports from `src/`).
- [ ] 5.0.6: Verify: CI green, no consumer-visible behavior change.
- [ ] 5.0.7: PR — `refactor: introduce uv workspace skeleton (testrail-core/testrail-mcp split)`.
- Risk: Medium — workspace migration can break editable installs; canary
  before any code moves.

#### PR 5.1 (canary): Move cases resource (M)

**Branch**: `refactor/extract-cases`

- [ ] 5.1.1: Move client `src/client/api/cases.py` →
  `packages/testrail-core/src/testrail_core/api/cases.py`.
- [ ] 5.1.2: Move case schemas `src/shared/schemas/cases.py` →
  `packages/testrail-core/src/testrail_core/schemas/cases.py`.
- [ ] 5.1.3: Move base infrastructure required by cases:
  `base_client.py`, `exceptions.py`, the relevant cache module(s),
  `rate_limiter.py`, `attachments.py` (cases tool uploads attachments).
- [ ] 5.1.4: Update imports in `src/server/api/cases.py` and the dispatcher
  to point at `testrail_core`.
- [ ] 5.1.5: Move existing case-client unit tests under
  `packages/testrail-core/tests/`; leave server-handler tests in the MCP package.
- [ ] 5.1.6: Verify: `uv run pytest` (whole workspace) green; `testrail_core`
  importable as a standalone module (`uv run python -c "from testrail_core.api.cases import CasesClient"`).
- [ ] 5.1.7: PR — `refactor(core): extract cases resource into testrail-core (canary)`.
- Risk: High — first move; surfaces shared-base-client coupling. Treat as a
  blocking checkpoint: do not open PR 5.2 until 5.1 is merged and CI is green
  on `main`.

#### PRs 5.2–5.11: Remaining resources (one PR per resource, S–M each)

Order chosen to minimise inter-resource dependencies (suites/sections before
runs/plans, results last because they reference runs+cases, attachments
already lives in core after 5.1):

- [ ] 5.2 — `refactor/extract-suites` — move `suites` client + schemas + tests.
- [ ] 5.3 — `refactor/extract-sections` — move `sections`.
- [ ] 5.4 — `refactor/extract-runs` — move `runs` (+ `tests` resource if coupled).
- [ ] 5.5 — `refactor/extract-plans` — move `plans` + `plan_entries`.
- [ ] 5.6 — `refactor/extract-results` — move `results`.
- [ ] 5.7 — `refactor/extract-metadata` — move `metadata` (templates, statuses lookup, etc.).
- [ ] 5.8 — `refactor/extract-users` — move `users`.
- [ ] 5.9 — `refactor/extract-milestones` — move `milestones`.
- [ ] 5.10 — `refactor/extract-configs` — move `configs`.
- [ ] 5.11 — `refactor/extract-health` — move health check + metrics shared bits;
  delete the now-empty `src/` tree; final cleanup PR.

Each PR (5.2–5.11):
- File-level moves only — no behavior changes, no API renames.
- Updates the MCP package's imports.
- All existing tests still pass; tests for the moved resource live in
  `packages/testrail-core/tests/`.
- Verify: `uv run pytest` green on the whole workspace; `git grep` confirms no
  `src/client/api/<moved-resource>` imports remain.
- Risk: Low–Medium per PR (canary already paid the high-risk cost).

### Phase 6: PyPI release v2.0.0

**Branch**: `chore/release-2.0.0`
**Depends on Phase 5 fully merged.**

- [ ] 6.1: Bump both `packages/*/pyproject.toml` versions to `2.0.0` (S).
- [ ] 6.2: `testrail-mcp` declares `testrail-core==2.0.0` as a dependency (S).
  - Verify: `uv lock` produces a clean lockfile with both at 2.0.0.
- [ ] 6.3: Add `.github/workflows/publish.yml` (M).
  - Trigger: `push` on tag matching `v*.*.*`.
  - Two jobs in matrix or sequential: build + publish `testrail-core`, then
    `testrail-mcp` (in that order, because the MCP depends on core).
  - Use `pypa/gh-action-pypi-publish@release/v1`.
  - Prefer OIDC trusted-publishing: configure both PyPI projects with the
    repo + workflow name; no secret needed.
  - Fallback: if OIDC is impractical, use `PYPI_API_TOKEN` repo secret with
    minimum-scope token per project.
  - Verify: dry-run on a pre-release tag (`v2.0.0rc1`) publishes both
    packages to TestPyPI first.
- [ ] 6.4: Update README install matrix (M)
  - PyPI: `uvx testrail-mcp` and `uv pip install testrail-mcp`.
  - Git+: `uvx --from git+https://github.com/<org>/<repo>@v2.0.0 testrail-mcp`.
  - Pinned SHA: `uvx --from git+https://github.com/<org>/<repo>@<sha> testrail-mcp`.
  - Verify: each form runs end-to-end against a TestRail sandbox.
- [ ] 6.5: Tag `v2.0.0` and push.
  - Verify: workflow publishes both to PyPI; install from PyPI in a clean
    venv produces a working server (`uvx testrail-mcp --help`).
- [ ] 6.6: GitHub Release notes drafted from CHANGELOG (S).
- Risk: High on the publish workflow — first-time PyPI publishing is
  unforgiving. Mitigate with TestPyPI dry-run before the real tag.

### Phase 7: Docs sync (skip-tier `/chekpoint`)

**Branch**: `docs/v2-sync`

- [ ] 7.1: Update root `CLAUDE.md` (M)
  - Drop the "15 consolidated action-based tools" framing where it describes
    the runtime surface; document that the dispatcher exposes the underlying
    flat tool registry (62 tools — verify exact count from Phase 0.1).
  - Add a new "Environment Variables" subsection documenting:
    `TESTRAIL_READ_ONLY`, `TESTRAIL_ALLOWED_TOOLS`, `TESTRAIL_LEGACY_ALIASES`,
    `TESTRAIL_PRELOAD_CACHE`, `TESTRAIL_PRELOAD_PROJECT_ID`.
  - Verify: diff reads cleanly; no stale references to removed concepts.
- [ ] 7.2: Update `README.md` (M)
  - Env-var matrix table.
  - bun913 migration note: "If you are migrating from the bun913 fork, leave
    `TESTRAIL_LEGACY_ALIASES` at its default of `1` — your existing tool
    names continue to work. Set to `0` once your client is fully migrated."
  - Install matrix from Phase 6.4.
- [ ] 7.3: Update `USER_GUIDE.md` (S)
  - New "Read-only mode" section.
  - New "Restricting the tool surface" section.
- [ ] 7.4: Skip-tier `/chekpoint` because docs-only.
- [ ] 7.5: PR — `docs(v2): sync README, CLAUDE.md, USER_GUIDE for v2.0.0`.

### Testing Strategy

**Unit (per-phase test files)**
- `tests/server/test_read_only_gate.py` — Phase 1, parametrize over 36 tools.
- `tests/server/test_allowlist.py` — Phase 2, parametrize precedence cases.
- `tests/server/test_aliases.py` — Phase 3, parametrize 28 aliases + generic.
- `tests/server/test_cache_warmup.py` — Phase 4, fetcher matrix.
- `packages/testrail-core/tests/...` — Phase 5, one file per resource, ported
  from existing tests.

**Integration**
- After Phase 1: stdio smoke test confirms read-only blocks one write tool
  end-to-end via the real dispatcher.
- After Phase 4: stdio smoke test confirms warm-up populates all four caches
  visible via `testrail_health`.
- After Phase 5 final PR: `import testrail_core` from a fresh venv with only
  the core package installed; instantiate a client; round-trip a `get_cases`
  call against a sandbox.
- After Phase 6: install `testrail-mcp` from PyPI in a fresh venv;
  `uvx testrail-mcp` boots; tool list matches expected count.

**Regression evals** (eval-harness skill)
- Capability: `pass^3` for read-only blocking the canonical 36 names.
- Capability: `pass^3` for allowlist precedence behavior.
- Regression: `pass^3` for the existing read-tool happy paths after each
  Phase 5 sub-PR.

### Cross-Phase Risks & Mitigations

- **Risk**: Phase 5 canary uncovers shared-state coupling between resources
  (e.g. all caches share a singleton in `src/server/api/`).
  **Mitigation**: PR 5.1 explicitly moves the shared base + caches first;
  if coupling is deeper than expected, pause and revise the workspace layout
  in a hotfix to ADR-003 before proceeding to 5.2.
- **Risk**: Alias precedence bug silently lets a write tool through when
  read-only is on (e.g. canonical resolution happens after gating).
  **Mitigation**: Phase 3 dispatcher integration test explicitly covers
  `addCase` (camelCase) under read-only — that test is the gate.
- **Risk**: PyPI publish workflow leaks API token in logs.
  **Mitigation**: prefer OIDC trusted-publishing (no secret in the repo);
  if a token is required, scope to the single project and rotate after first
  successful publish.
- **Risk**: Cache warm-up adds startup latency for consumers who don't want
  it (e.g. CLI users running one-shot commands).
  **Mitigation**: opt-in only — default off. Documented in README env-var
  matrix.
- **Risk**: Workspace migration breaks `uvx --from /local/path testrail-mcp`
  for existing consumers.
  **Mitigation**: Phase 5.0 PR explicitly tests the local-path install in CI
  before merge; README install matrix lists the new invocation
  (`uvx --from /local/path/packages/testrail-mcp testrail-mcp`) on the same PR.
- **Risk**: 36-tool list drifts from the source of truth between Phase 0
  enumeration and Phase 1 frozen set.
  **Mitigation**: Step 1.2 cross-checks `WRITE_TOOLS` against the dispatcher
  registry as a unit test; CI fails if a new write tool is added without
  updating the constant.
- **Risk**: Public-facing leakage of internal product context in commit
  messages, ADRs, or comments.
  **Mitigation**: every PR description and every ADR in this plan stays
  generic — review by author before opening, and `git log --grep` audit at
  Phase 7 against a deny-list of internal terms.

### Phase Dependency Graph

```
Phase 0 (research)
   ↓
Phase 1 (read-only) ── PR
   ↓
Phase 2 (allowlist) ── PR
   ↓
Phase 3 (aliases)   ── PR
   ↓
Phase 4 (preload)   ── PR
   ↓
Phase 5.0 (workspace + ADR) ── PR
   ↓
Phase 5.1 (cases canary)    ── PR  ← blocking checkpoint
   ↓
Phase 5.2…5.11 (one resource per PR, can be sequential or lightly parallel
                 once 5.1 is merged; each PR independently green)
   ↓
Phase 6 (PyPI publish v2.0.0) ── PR + tag
   ↓
Phase 7 (docs sync)           ── PR
```

### End-to-End Verification Checklist

- [ ] All 36 write tools blocked under `TESTRAIL_READ_ONLY=1`.
- [ ] Read tools unaffected by `TESTRAIL_READ_ONLY=1`.
- [ ] `TESTRAIL_ALLOWED_TOOLS=""` and unset both behave as "all allowed".
- [ ] Read-only takes precedence over allowlist.
- [ ] All 28 explicit bun913 aliases resolve to the correct canonical name.
- [ ] Generic camelCase translator handles names not in the explicit map.
- [ ] `TESTRAIL_LEGACY_ALIASES=0` disables alias resolution entirely.
- [ ] Gating uses canonical names regardless of which alias the client called.
- [ ] `TESTRAIL_PRELOAD_CACHE=1` populates four caches at startup; failure
      degrades to a warning, not a crash.
- [ ] `testrail-core` importable from a fresh venv with no MCP code present.
- [ ] `testrail-mcp` from PyPI boots and serves the same tool surface as the
      pre-split version.
- [ ] README install matrix verified for PyPI, git+, and pinned-SHA forms.
- [ ] No internal product names appear in `git log`, ADRs, code, or docs
      (audit at Phase 7).
- [ ] `uv run pytest` green on the whole workspace at every phase boundary.
- [ ] All PRs merged through normal review with `/chekpoint` at the
      appropriate tier (full for Phases 1–6, skip for Phase 7).

### Success Criteria

- [ ] v2.0.0 published to PyPI for both `testrail-core` and `testrail-mcp`.
- [ ] An external consumer can `uv pip install testrail-core` and use the
      HTTP client without any MCP machinery loaded.
- [ ] An external consumer can run `uvx testrail-mcp` with
      `TESTRAIL_READ_ONLY=1` and verify (by attempting a write tool) that the
      block is enforced server-side.
- [ ] The bun913 migration note in README is sufficient for a fork user to
      switch to upstream without changing their tool names.
- [ ] No regressions: every read-tool test that passed at Phase 0 still
      passes at Phase 7.
- [ ] Public repo audit: zero references to internal product context in any
      committed file or commit message.
