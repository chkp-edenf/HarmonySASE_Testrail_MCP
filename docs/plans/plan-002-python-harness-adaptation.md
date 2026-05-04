---
number: 2
title: Python-adapt kadmon-harness commands for this repo
date: 2026-04-21
status: in_progress
needs_tdd: false
route: A
adr: ADR-002-python-harness-adaptation.md
---

## Plan: Python-adapt kadmon-harness commands [konstruct]

### Overview
Execute ADR-002 by shipping project-local `.claude/` overrides that Python-adapt `/medik`, `/chekpoint`, and the `verification-loop` skill, plus wiring the Python tool configs (`ruff`, `mypy`, `pytest`, `coverage`) into `pyproject.toml`. No plugin files are modified. Existing hooks are left alone (they already no-op on `.py`).

This is a **`needs_tdd: false`** plan — the artifacts are markdown command/skill definitions and config TOML; there is no new runtime Python code to test-drive. Verification happens end-to-end by running the adapted `/chekpoint` sequence against the live repo.

### Assumptions
- Project-local `.claude/commands/*.md` overrides plugin commands of the same name when invoked from this project (R1 in ADR). Verification step 8.1 confirms.
- `ruff` and `mypy` can be installed via `uv sync --extra dev` once added to `pyproject.toml`.
- Eden does not want to modify the upstream plugin — confirmed in ADR-002 Decision section.
- Current repo has `.ruff_cache/` and `.mypy_cache/` but no tool config — so baseline lint/type output is whatever the tools produce with defaults. Some findings are expected and will be triaged, not blocked, in this plan.

### Constraints (from ADR + repo conventions)
- No plugin files modified.
- Branch: `fix/curl-pipe-tty` (current). No push in this plan — user will decide after review.
- Python 3.11+ (`pyproject.toml:11`).
- `uv` is the package manager; all commands wrap with `uv run`.
- Commit message style: conventional (`feat(harness): ...`, `chore(config): ...`) per CLAUDE.md "Commit messages" section.
- `/chekpoint` itself should run cleanly against the final state.

### Steps

#### Phase 1: Config foundation

- [x] **Step 1 — Extend pyproject.toml with tool configs (S)** — `pyproject.toml`
  - Add `ruff>=0.6` and `mypy>=1.11` to `[project.optional-dependencies].dev`.
  - Add `[tool.ruff]` — `line-length = 100`, `target-version = "py311"`, rules sensible for the existing codebase (`E`, `F`, `I`, `UP`, `B`, `SIM`).
  - Add `[tool.mypy]` — `python_version = "3.11"`, `check_untyped_defs = true`, `warn_unused_ignores = true`, `strict = false` (tighten later per ADR R3).
  - Add `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`.
  - Add `[tool.coverage.run]` — `source = ["src"]`, `branch = true`.

- [x] **Step 2 — `uv sync --extra dev` and smoke-run each tool (S)**
  - Verify `uv run ruff check src tests` returns (any exit code — we're probing availability, not cleanliness).
  - Verify `uv run mypy src` returns.
  - Verify `uv run pytest` passes (existing tests are presumed green — if not, stop and hand back).

#### Phase 2: Command + skill overrides

- [x] **Step 3 — Create `.claude/skills/verification-loop/SKILL.md` (M)**
  - Python sequence: `uv sync` → `uv run python -c "import src.stdio"` (import-check; cheaper than `uv build`) → `uv run mypy src` → `uv run ruff check src tests` → `uv run ruff format --check src tests` → `uv run pytest`.
  - Stop-at-first-failure discipline, same as upstream skill.
  - Include `based_on: kadmon-harness@1.1.0/skills/verification-loop/SKILL.md` frontmatter for drift tracking.

- [x] **Step 4 — Create `.claude/commands/medik.md` (M)**
  - Phase 1 health checks in Python terms: import check, mypy, ruff check, ruff format --check, pytest, `uv build` (full wheel), `uv pip list --outdated` in place of `npm audit`.
  - Drop `dist/` staleness check and `lint-agent-frontmatter.ts` step.
  - Keep the mekanik + kurator invocation chain unchanged (those agents work across languages).
  - `based_on: kadmon-harness@1.1.0/commands/medik.md`.

- [x] **Step 5 — Create `.claude/commands/chekpoint.md` (M)**
  - Phase 1 verification: delegate to `verification-loop` skill (which we own now).
  - Phase 2a reviewer dispatch: only `python-reviewer`, `spektr`, `orakle` (drop `typescript-reviewer` — zero `.ts` files here).
  - Phase 2b (`kody` consolidation), Phase 3 (gate), Phase 4 (commit) unchanged.
  - Tier selection matrix mapped to Python: `Full` = any `src/**/*.py`, `Lite` = tests-only or single file < 50 LOC, `Skip` = docs/config only.
  - `based_on: kadmon-harness@1.1.0/commands/chekpoint.md`.

#### Phase 3: Cross-reference + global mapping

- [x] **Step 6 — Append toolchain mapping to CLAUDE.md (S)**
  - New section "## Harness Toolchain Mapping" with a 2-column table TS → Python covering: build, typecheck, test, lint, format, audit, package add, run local.
  - Placed after "Important Notes" so any agent reading CLAUDE.md catches it late enough to be top-of-mind.

#### Phase 4: Verification + review

- [x] **Step 7 — Run adapted `/chekpoint` end-to-end (M)** — verification only, no commit from within plan.
  - Confirm `/chekpoint` resolves to the project override (print command path Claude picks).
  - Run Phase 1 sequence manually via Bash (`uv run mypy src`, `uv run ruff check src tests`, `uv run pytest`) and capture results.
  - Document any baseline findings (expected — first ruff/mypy pass on unconfigured code).

- [x] **Step 8 — kody code review (S)**
  - Invoke `kody` agent on the four new files + pyproject.toml + CLAUDE.md diff.
  - Address any BLOCK findings before handing back to user.

### Critical files
- `pyproject.toml` — modified
- `CLAUDE.md` — appended
- `.claude/commands/medik.md` — new
- `.claude/commands/chekpoint.md` — new
- `.claude/skills/verification-loop/SKILL.md` — new
- `docs/decisions/ADR-002-python-harness-adaptation.md` — new (this task)
- `docs/plans/plan-002-python-harness-adaptation.md` — new (this file)

### Existing utilities reused
- **`python-reviewer` agent** (plugin `agents/python-reviewer.md`) — already handles `.py` review; `/chekpoint` override just calls it.
- **`spektr`, `orakle`, `kody`, `mekanik`, `kurator`** — language-agnostic; used as-is.
- **`uv` + `hatchling`** — already in the repo's toolchain.
- **`pytest` + existing `tests/conftest.py`** — test infra already built out for the installer.

### Verification

After implementation, these commands must all succeed from the project root:

```bash
# Step 2 smoke
uv sync --extra dev
uv run ruff check src tests
uv run mypy src
uv run pytest

# Step 7 end-to-end harness verify (what /chekpoint Phase 1 will run)
uv run python -c "import src.stdio"
uv run mypy src
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest
```

Further manual verification:

- Invoke `/chekpoint` from a new Claude Code session in this project and confirm Phase 1 now lists Python commands in its trace (not `npm run build`).
- Invoke `/medik` and confirm the Phase 1 health report references mypy/ruff/pytest, not tsc/eslint/vitest.

### Out of scope (future ADRs)
- Hook rewrites (`post-edit-typecheck.js` → `.py` aware) — deferred, noted as OQ1 in ADR-002.
- Tightening mypy to `strict = true` — deferred, noted as ADR-002 R3.
- Python-aware `/forge`, `/evolve` report templates — deferred, OQ2.
- Test framework routing for `kartograf` (Playwright is web E2E; this MCP has no web UI).
