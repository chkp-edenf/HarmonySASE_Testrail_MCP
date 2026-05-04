---
number: 2
title: Python-adapt kadmon-harness commands for this repo
date: 2026-04-21
status: accepted
route: A
plan: plan-002-python-harness-adaptation.md
---

# ADR-002: Python-Adapt kadmon-harness Commands for this Repo

**Deciders**: Eden Fridman (owner), arkitect (design via /abra-kdabra)

## Context

The kadmon-harness plugin (`/Users/edenf/.claude/plugins/cache/kadmon-harness/kadmon-harness/1.1.0/.claude/`) ships a TypeScript-first toolchain. Its verification commands — `/medik`, `/chekpoint`, and the shared `verification-loop` skill — call `npm run build`, `npx tsc --noEmit`, `npx vitest run`, and `npx eslint .` directly. Running any of those in this repo fails at the first command because this project is Python (`pyproject.toml:5-12`: `harmonysase-testrail-mcp`, Python `>=3.11`, hatchling build-backend, pytest-only dev deps).

Phase 1 exploration surfaced the concrete TS assumptions:
- `/medik` (plugin `commands/medik.md:20-27, :61`) runs `npm run build`, `npx tsc --noEmit`, `npx vitest run`, `npx tsx scripts/lint-agent-frontmatter.ts`.
- `/chekpoint` (plugin `commands/chekpoint.md:33-36`) runs `npm run build`, `npx tsc --noEmit`, `npx vitest run`, `npx eslint . --ext .ts,.js`.
- `verification-loop` skill (plugin `skills/verification-loop/SKILL.md:21-24`) is the shared sequence both commands anchor on.
- Several hooks (`post-edit-typecheck.js`, `post-edit-format.js`, `quality-gate.js`, `ts-review-reminder.js`, `ensure-dist.js`) gate on `.ts/.tsx/.js/.jsx` extensions and `node_modules`; they are inert for `.py` files in this repo, so they are a no-op — not a blocker.
- Agents `typescript-reviewer` and `python-reviewer` both exist (plugin `agents/python-reviewer.md` confirmed, not a duplicate). `/chekpoint`'s Phase 2a dispatcher already routes `.py` files to `python-reviewer` — that part needs no change.

The ask is to make `/medik` and `/chekpoint` actually run here, plus any other TS-bound commands that block day-to-day work, without forking the upstream plugin (Eden still uses the harness on TypeScript projects).

## Decision

**Adapt at the project layer, not the plugin layer.** Create a project-local `.claude/` override tree at `BMAD_HarmonySASE_Testrail_MCP/.claude/` that shadows only the TS-bound surfaces with Python equivalents. The plugin stays untouched.

Scope (minimum viable override):

1. **`.claude/commands/medik.md`** — Python-adapted health checks: `uv build`, `uv run mypy src`, `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`. Skips `dist/` staleness (no compiled output in Python source-dist workflow) and `lint-agent-frontmatter.ts` (plugin-internal tool).
2. **`.claude/commands/chekpoint.md`** — Python-adapted verify sequence + Phase 2a reviewer routing trimmed to `python-reviewer` + `spektr` + `orakle`; `typescript-reviewer` is unreachable here because there are no `.ts` files.
3. **`.claude/skills/verification-loop/SKILL.md`** — Python sequence (`uv sync`, `uv build`, `uv run mypy`, `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`) — this is the shared anchor `/medik` and `/chekpoint` reference.
4. **`pyproject.toml`** — add `ruff` and `mypy` to `[project.optional-dependencies].dev`, plus `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`, `[tool.coverage.run]` config so the commands call real, configured tools rather than defaulting.
5. **`CLAUDE.md`** — append a short "Harness toolchain mapping" section so any harness command not overridden (e.g., `/doks`, `/skanner`, `/forge`, `/evolve`) still knows the TS→Python equivalences when Claude interprets them.

### What we explicitly do NOT change
- **Plugin files** in `/Users/edenf/.claude/plugins/cache/kadmon-harness/...` — plugin updates would clobber; Eden uses the plugin on TS projects too.
- **The hooks under `.claude/hooks/scripts/`** — they already gate on file extension and silently no-op on `.py`. Rewriting them is a second PR and out of scope.
- **`/doks`, `/evolve`, `/forge`, `/skanner`, `/abra-kdabra`** — these do not shell out to `npm/tsc/vitest/eslint` in their bodies. `/forge` and `/skanner` delegate to plugin-internal TS pipelines (`forge-pipeline.js`, `kartograf`'s Vitest harness) that describe the *plugin's own self-tests*, not user-project verification. They still work fine when invoked here; the toolchain mapping in CLAUDE.md covers any TS references their agents encounter.
- **Agents `mekanik`, `feniks`, `kartograf`** — their prompts reference Vitest/TSC in examples but they already list Python test frameworks (feniks: `python-testing`, `tdd-workflow`). python-reviewer handles the Python-specific review.

### Alternative approaches considered

- **Approach B: Fork the plugin** — rejected. High maintenance burden; breaks Eden's TS-project usage.
- **Approach C: Rely purely on CLAUDE.md toolchain mapping without command overrides** — rejected. The plugin commands have explicit shell commands in their bodies; Claude would see `npx vitest run` in the instructions and either follow it (fail) or improvise inconsistently.
- **Approach D: New command names (`/medik-py`, `/chekpoint-py`)** — rejected. Muscle memory matters; Eden already types `/chekpoint`. Project-local overrides win naturally when invoked from this repo.

## Consequences

### Positive
- `/medik` and `/chekpoint` work end-to-end in this repo with no manual translation.
- Plugin updates land cleanly (we own no plugin files).
- `verification-loop` skill override documents the canonical Python verify sequence once; both commands reuse it.
- Forces us to actually configure ruff/mypy/pytest/coverage in `pyproject.toml` — previously the `.ruff_cache/` and `.mypy_cache/` dirs existed but no tool config did, meaning both ran with pure defaults.

### Negative
- Two `.claude/commands/*.md` files drift from upstream plugin versions over time — each plugin bump needs a diff-check. Mitigation: include upstream version (`1.1.0`) in each override's frontmatter `based_on` field so drift is visible.
- `python-reviewer` agent body still references `mypy`/`ruff` generically; if it assumes specific config keys that we don't set, the agent's review findings may be generic. Acceptable — we set the core keys (`[tool.mypy] strict`, `[tool.ruff] line-length`, etc.) and let the agent improvise.

### Risks flagged

- **R1 — Command-name collision between project override and plugin**: Claude Code's precedence is project-local `.claude/commands/` over plugin commands for the shortform (`/chekpoint`). The fully-qualified form (`/kadmon-harness:chekpoint`) always resolves to the plugin. If precedence behaves otherwise, rename project commands to `/chekpoint` (force-override) via the command's frontmatter `name` field. Verification step in plan-002 confirms this after install.
- **R2 — `uv build` pollutes `dist/`** on every `/chekpoint` run. Mitigation: `/chekpoint` Phase 1 treats build as "import check only" — invoke `uv run python -c "import src.stdio"` instead of `uv build` for the Lite tier; full `uv build` stays in `/medik` and Full-tier `/chekpoint`.
- **R3 — mypy strict mode fails on existing code**: Current code has no type-check history. Mitigation: start mypy at `strict = false` + `check_untyped_defs = true` in pyproject; tighten in a follow-up ADR after a baseline pass.

## Open Questions

- **OQ1** — Should `ensure-dist.js` hook behavior be replaced with a Python-aware equivalent (detect stale wheel vs source)? Deferred; hook is inert today.
- **OQ2** — Should `/forge` and `/evolve` grow Python-project awareness for their report templates? Deferred; they don't block verification.

## References

- Plugin `commands/medik.md`, `commands/chekpoint.md`, `skills/verification-loop/SKILL.md`, `agents/python-reviewer.md`
- `pyproject.toml:22-32` (current deps)
- `tests/conftest.py:1-10` (pytest layout)
- Phase 1 inventory (session transcript, 2026-04-21)
