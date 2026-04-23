---
number: 3
title: Wizard robustness + self-diagnosis
date: 2026-04-23
status: pending
needs_tdd: true
route: B
adr: none
---

## Plan: Wizard robustness + self-diagnosis [konstruct]

### Overview
Close three real failure modes surfaced by Idan on Windows this week: (1) pasting a TestRail browser-tab URL and having the wizard pass it straight through to the ping, (2) Claude detection missing MS Store / packaged-app / redirected-`%APPDATA%` / PATH-less installs, and (3) `uv` cache rename failing under OneDrive / Defender / EDR scan locks. We also ship `--diagnose` and `--verbose` so the next time something like this happens Idan can paste a probe report instead of screenshots. All changes are additive — every existing flag keeps its current behavior, and the API-key redaction invariant that `spektr` has already reviewed still holds.

**Symmetric detection.** The hardening applies to *both* clients: Claude Code and Claude Desktop each get a layered probe chain (items B and C). If Claude is installed on the machine at all — as CLI, as app, through any of the known installers or package managers, in any of the common directories, or currently running — the wizard should find it regardless of which client it is. The two detection functions mirror each other in shape and in probe-name vocabulary so `--diagnose` produces a symmetric report.

### Context

Three teammate reports this week, all Windows, all traceable:

1. **URL paste mistake.** Idan set `$env:TESTRAIL_URL = "https://perimeter81.testrail.io/index.php?/suites/view/392&group_by=cases:section_id&group_order=asc&display=compact&display_deleted_cases=0&group_id=121703"` — the URL of the tab he had open. Our `_prompt_url` / `_resolve_credentials` validate `startswith("https://")` and pass the whole string through. The ping then appends `/index.php?/api/v2/get_projects`, the result is a garbled path, and TestRail 404s.

2. **Claude Desktop detection miss on Windows.** Idan has Claude Desktop *installed and running*, but `Path("%APPDATA%/Claude").is_dir()` returns False. Causes we need to cover:
   - `%APPDATA%` redirected to a network share by corporate group policy (path exists but resolves off-box).
   - MS Store / MSIX install — config lives under `%LOCALAPPDATA%\Packages\*Claude*\`.
   - Installed under `%LOCALAPPDATA%\Programs\Claude\Claude.exe` but runtime config dir not yet created (never launched).

3. **`uv` cache rename denial.** `pywin32` download fails with `Access is denied (os error 5)` during `rename()` from `.tmpXXX` → `archive-v0/...` in `%LOCALAPPDATA%\uv\cache`. OneDrive sync / Windows Defender real-time scan / corporate EDR holds a lock on the just-written file for ~200 ms. Idan worked around with `$env:UV_CACHE_DIR = "C:\uv-cache"`; we should bake that into `install.ps1`.

### Scope

Seven items (A–G) grouped into five implementation phases. **The 7 items listed here are the complete scope.** Tier 3 items (`--force`, reparse-point warning, registry writes) are explicitly **not in scope** — see Non-goals.

#### Tier 1 — must ship (unblocks Windows teammates)

- **A. URL auto-normalize** via `urllib.parse.urlsplit`. Accept `company.testrail.io`, `https://company.testrail.io/`, `https://company.testrail.io/index.php?/suites/view/392&...`, `http://company.testrail.io` (auto-upgrade to https). Reject empty, no-dot, `file://`, `ftp://`, any other scheme. Applied in three places: `_prompt_url`, `--url` flag path in `_resolve_credentials`, and the `TESTRAIL_URL` env-var path in `_resolve_credentials`. When anything is stripped, echo back `Normalized: <url>  (dropped path/query)` so the user sees what happened.

**Symmetric detection contract (items B and C together).** The same layered
"check-everywhere" approach applies to **both** Claude clients. If Claude is
installed on the machine at all — as CLI, as app, in any install location,
in any install mode — the wizard should find it. Each probe is tried in
order, first hit wins, and the winning probe name lands in
`_ClientDetection.detected_via` for both display and `--diagnose` output.
"Installed" means present on disk or running in memory; it does *not* require
the user to have launched the client once before.

- **B. Layered Claude Desktop detection.** Check in order, stop at first hit, record which probe succeeded:
  1. Config dir: `%APPDATA%\Claude\` (current behavior) + fallback `%LOCALAPPDATA%\Claude\`.
  2. Install binary: `%LOCALAPPDATA%\Programs\Claude\Claude.exe`, `%ProgramFiles%\Claude\Claude.exe`, `%ProgramFiles(x86)%\Claude\Claude.exe`.
  3. MSIX / Store: glob `%LOCALAPPDATA%\Packages\*Claude*\`.
  4. Running process: `tasklist /FI "IMAGENAME eq Claude.exe" /FO CSV` — parse CSV, True if any row matches.
  5. Registry: `winreg.OpenKey(HKCU, "Software\\Claude")` (Windows-only; optional-import; try/except on everything).

  macOS: add `/Applications/Claude.app` install probe + `pgrep -f 'Claude.app'` running-process probe.
  Linux: add desktop-file probes at `/usr/share/applications/claude.desktop` and `~/.local/share/applications/claude.desktop`.

  Extend `_ClientDetection` with `detected_via: str | None` so the display line reads `✓ Claude Desktop detected (via running process)`.

- **C. Layered Claude Code CLI detection.** Mirror of item B: check every common install location the official installer + npm + manual installs use, not just PATH. First hit wins, `detected_via` records which probe succeeded.
  1. PATH: `shutil.which("claude")` (current behavior — keep it first; it's the cheapest and handles the expected case).
  2. Official installer fallback: `%USERPROFILE%\.claude\local\claude.exe` on Windows; `~/.claude/local/claude` on macOS/Linux. These are where `curl -LsSf https://claude.ai/install.sh | sh` drops the binary when `~/.claude/local/` isn't on PATH (a known Anthropic installer quirk that routinely bites new users).
  3. Unix alt install: `~/.local/bin/claude` (uv / pipx / manual installs).
  4. npm global install: `%APPDATA%\npm\claude.cmd` on Windows; `$(npm config get prefix)/bin/claude` on Unix (gated on `shutil.which("npm")` so we don't shell out when npm isn't present).
  5. Install binary under standard app paths (Windows only, matches B): `%LOCALAPPDATA%\Programs\Claude\claude.exe`, `%ProgramFiles%\Claude\claude.exe`.
  6. Running process (Windows only): `tasklist /FI "IMAGENAME eq claude.exe" /FO CSV` — lowercase `claude.exe` (distinct from Desktop's `Claude.exe`). Covers Claude Code running as a long-lived IDE helper.
  7. Registry (Windows only): `winreg.OpenKey(HKCU, "Software\\Anthropic\\ClaudeCode")` if Anthropic's installer writes one (try/except; no-op on failure).

  When a fallback path hits, use the absolute path for the `claude --version` subprocess probe so the version string + install location both land in the display and `--diagnose`.

  **Parity with item B is deliberate.** Every place Claude Desktop might be found has an equivalent check for Claude Code, and vice versa; the two detection functions differ only in the probe targets, not in the probe structure.

- **D. Better neither-detected exit message.** When both Claude Code and Claude Desktop detection fail, print an OS-specific next step:
  - Windows: *"If Claude Desktop is installed but detection missed it (common with MS Store / Packaged App installs), re-run with `--client claude-desktop` and the wizard will write the config anyway. Run `--diagnose` for a probe report."*
  - macOS: equivalent wording pointing at `/Applications/Claude.app`.
  - Linux: point at the two desktop-file paths.

- **E. `install.ps1`** — default `$env:UV_CACHE_DIR` to `"$env:TEMP\uvcache"` unless already set. Inline comment explaining the OneDrive / Defender lock-contention root cause so the next reader doesn't delete it.

#### Tier 2 — self-diagnosis (ship next)

- **F. `--diagnose` command.** Read-only, exits 0. Prints: OS / Python / package version / uv version; env-var values (api_key redacted via `_redact`); `%APPDATA%` / `%LOCALAPPDATA%` values + reparse-point detection; every detection probe's result (pass/fail + which path matched); uv cache write-test (create + delete a temp file under the cache dir); network reachability to `raw.githubusercontent.com` and the resolved `TESTRAIL_URL`. Purpose: Idan pastes the output in Slack when stuck.

- **G. `--verbose` flag** on the main wizard. When set, inline-log each detection probe as it runs (which probe, what path, hit/miss). Redacts API key through the existing path.

#### Tier 3 — descoped

`--force` flag, reparse-point write warning, registry writes for Claude Desktop config. **Not in scope** for plan-003; reopen if Idan or others ask.

### Constraints

- **Additive contract.** Existing `--client` / `--scope` / `--url` / `--username` / `--api-key` / `--yes` / `--dry-run` / `--no-validate` / `--ref` flags preserve today's behavior and today's exit codes. Every new code path is gated on new input (a URL containing a path/query, a new flag, a new probe).
- **API-key redaction invariant.** Never log the raw key. `_redact()` (`src/installer.py` ~L1115) is the single choke point; `--diagnose` and `--verbose` both route through it. Preserved for `spektr`'s existing invariant check.
- **Cross-platform with mockable platform.** Detection branches on `sys.platform`; tests monkeypatch it so macOS CI can exercise the Windows code path without a Windows runner.
- **Single-file scope.** Wizard logic stays in `src/installer.py`. `install.ps1` gets the cache-dir default. Tests in `tests/test_installer.py`. No other files change.
- **No new third-party deps.** Stdlib only (`urllib.parse`, `subprocess`, `winreg` optional-import guarded by `sys.platform == "win32"`).
- **TDD (`needs_tdd: true`).** Tests precede implementation for every new probe, parser, and flag; feniks should guide the red→green→refactor loop.

### Files to modify

- `src/installer.py` — URL normalizer, layered detection, `--diagnose`, `--verbose`, `_ClientDetection.detected_via`, OS-specific exit message, CLI fallback probes. Reuses existing `_c`, `_ok`, `_fail`, `_warn`, `_emit` (L100–129), `_ClientDetection` (L148), `_PingOutcome` (L168), `_redact` (~L1115).
- `install.ps1` — default `$env:UV_CACHE_DIR` to `"$env:TEMP\uvcache"` with explanatory comment.
- `tests/test_installer.py` — new tests for A–G. Reuses conftest fixtures `fake_prompts`, `fake_claude_cli`, `fake_claude_desktop_config`, `fake_testrail_ping`. Monkeypatches `sys.platform`, `subprocess.run`, `shutil.which`, and `pathlib.Path` probes.

### Phased steps

Every step is TDD: write the test first, watch it fail, implement, watch it pass.

#### Phase 0: Research

- [ ] **Step 0.1 — Re-read installer helpers to confirm signatures** (S)
  - Files: `src/installer.py` L100–180 (helpers + dataclasses), L1100–1140 (`_redact` + surrounding), `_prompt_url`, `_resolve_credentials`, `_detect_claude_code`, `_claude_desktop_detected`, existing argparse setup.
  - Verify: confirm exact call sites for `_prompt_url` and the two `_resolve_credentials` URL paths; confirm `_ClientDetection` field order before extending; confirm existing conftest fixture names.
  - Depends on: none.
  - Risk: Low.

- [ ] **Step 0.2 — Enumerate existing tests that monkeypatch `_detect_claude_code` / `_claude_desktop_detected`** (S)
  - File: `tests/test_installer.py`.
  - Verify: `grep` produces the list; confirm the backward-compat note in the `_ClientDetection` docstring is still accurate (the bool helpers must remain for ~100 existing tests).
  - Depends on: 0.1.
  - Risk: Low — if this count is off, phase 2 breaks a lot of tests at once.

#### Phase 1: URL auto-normalize (item A)

- [ ] **Step 1.1 — Add `_normalize_testrail_url()` with parametrized tests** (M) — **TDD: tests first**
  - File: `src/installer.py` (new private function), `tests/test_installer.py` (new test class).
  - Behavior: accepts str, returns `(normalized_url: str, notes: list[str])` where notes is empty on clean input and contains human-readable messages like `"dropped path/query"` or `"upgraded http → https"` when changes are made. Raises `ValueError` with a user-facing message on invalid input.
  - Parametrized happy-path cases: `company.testrail.io` → `https://company.testrail.io`; `https://company.testrail.io/` → `https://company.testrail.io`; full browser-tab URL with `/index.php?/suites/view/...` → `https://company.testrail.io` + note; `http://...` → `https://...` + note.
  - Parametrized failure cases: empty string, whitespace-only, `file:///etc/passwd`, `ftp://x`, `notaurl`, `https://` (no host), `https://nodot`.
  - Verify: `uv run pytest tests/test_installer.py -k normalize_testrail_url -v` — all parametrized cases green.
  - Depends on: 0.1.
  - Risk: Low — pure function, fully testable.

- [ ] **Step 1.2 — Wire normalizer into `_prompt_url`, `--url` flag path, and `TESTRAIL_URL` env-var path** (M) — **TDD: tests first**
  - File: `src/installer.py` (three call sites), `tests/test_installer.py`.
  - Behavior: on successful normalize with non-empty notes, emit `_emit(_warn(f"Normalized: {url}  ({'; '.join(notes)})"))`. On `ValueError`, `_prompt_url` reprompts; the `--url` / env-var paths exit with `_fail(...)` and non-zero status using the same exit code today's invalid-URL path uses.
  - Tests: three new tests, one per call site, each supplying a browser-tab URL and asserting the resolved credentials URL is the normalized form, and the `Normalized:` line appears in captured stderr. One test for the env-var path asserting the normalized URL reaches the ping.
  - Verify: `uv run pytest tests/test_installer.py -k url -v` — green; existing URL tests still green.
  - Depends on: 1.1.
  - Risk: Medium — three call sites; easy to miss one. Mitigation: each site gets a dedicated test.

#### Phase 2: Layered detection + CLI fallback (items B, C)

- [ ] **Step 2.1 — Extend `_ClientDetection` with `detected_via: str | None = None`** (S) — **TDD: tests first**
  - File: `src/installer.py` L148 dataclass, `tests/test_installer.py`.
  - Behavior: new field defaults to None; `__bool__` unchanged. Add a unit test asserting the field exists and defaults correctly, and that the existing boolean helpers still return bool (backward-compat guard for the ~100 tests that monkeypatch them).
  - Verify: `uv run pytest tests/test_installer.py -v` — full suite green; no regressions.
  - Depends on: 0.2.
  - Risk: Low.

- [ ] **Step 2.2 — Implement layered Claude Desktop detection with `detected_via`** (L) — **TDD: tests first**
  - File: `src/installer.py` (`_claude_desktop_detected` and the richer `_claude_desktop_details`), `tests/test_installer.py` (new parametrized class).
  - Behavior: five probes in order (config dir, install binary, MSIX glob, running process, registry) on Windows; macOS probes (`.app` + `pgrep`); Linux desktop-file probes. First hit wins; returns a `_ClientDetection(installed=True, detected_via="<probe-name>", path=...)`. `winreg` import guarded `if sys.platform == "win32": import winreg`. Every probe wrapped in try/except returning False on any error.
  - Tests (all mock `sys.platform`, `pathlib.Path`, `subprocess.run`, `winreg`):
    - Windows config-dir hit (current behavior preserved).
    - Windows `%LOCALAPPDATA%\Claude\` hit when `%APPDATA%` miss.
    - Windows install-binary hit (each of three paths).
    - Windows MSIX glob hit.
    - Windows `tasklist` hit — mock `subprocess.run` to return CSV with `"Claude.exe",...` row.
    - Windows `tasklist` miss — mock empty CSV.
    - Windows registry hit — mock `winreg.OpenKey` success.
    - Windows all-miss — returns `_ClientDetection(installed=False)`.
    - macOS `.app` hit, macOS `pgrep` hit, macOS all-miss.
    - Linux desktop-file hit, Linux all-miss.
    - Each hit case asserts `detected_via` string matches expected probe name.
  - Verify: `uv run pytest tests/test_installer.py -k claude_desktop -v` — all parametrized cases green; existing Claude Desktop tests still green.
  - Depends on: 2.1.
  - Risk: High — five probes × three platforms is the largest surface in this plan; `tasklist` CSV parsing and `winreg` handling are the most error-prone. Mitigation: one test per probe per platform, no shortcuts; `winreg` fully monkeypatched so tests run on macOS CI.

- [ ] **Step 2.3 — Layered Claude Code CLI detection (mirrors Step 2.2)** (L) — **TDD: tests first**
  - File: `src/installer.py` (`_detect_claude_code` / `_claude_code_details`), `tests/test_installer.py` (new parametrized class).
  - Behavior: seven probes in order (PATH → official-installer fallback → Unix alt install → npm global → Windows app-install binary → Windows running process → Windows registry). First hit wins; returns a `_ClientDetection(installed=True, detected_via="<probe-name>", path=<abs-path>, version=<parsed>)`. Every Windows-only probe gated on `sys.platform == "win32"`; each probe wrapped in try/except returning False on any error. When a fallback path hits, use the absolute path for the `claude --version` subprocess probe so the version string lands in the display.
  - Tests (mock `sys.platform`, `shutil.which`, `pathlib.Path`, `subprocess.run`, `winreg`):
    - PATH hit (current behavior preserved — no regression).
    - Windows `%USERPROFILE%\.claude\local\claude.exe` hit when PATH misses.
    - macOS `~/.claude/local/claude` hit when PATH misses.
    - Linux `~/.local/bin/claude` hit when PATH misses.
    - Windows `%APPDATA%\npm\claude.cmd` hit (mocked `shutil.which("npm")` returning a path, mocked cmd exists).
    - Unix `$(npm config get prefix)/bin/claude` hit (mocked npm + path).
    - Windows `%LOCALAPPDATA%\Programs\Claude\claude.exe` hit.
    - Windows `tasklist` hit — mocked CSV output with `"claude.exe",...` row (lowercase; distinct from Desktop's `Claude.exe`).
    - Windows registry hit — mocked `winreg.OpenKey` success.
    - Windows all-miss — returns `_ClientDetection(installed=False)`.
    - macOS/Linux all-miss — returns `_ClientDetection(installed=False)`.
    - Each hit case asserts `detected_via` string matches expected probe name (e.g., `"path"`, `"installer-fallback"`, `"npm-global"`, `"running-process"`, `"registry"`).
    - **Parity assertion**: probe-name vocabulary used by `_claude_code_details` matches `_claude_desktop_details` 1:1 where applicable so `--diagnose` output stays consistent between the two sections.
  - Verify: `uv run pytest tests/test_installer.py -k claude_code -v` — all parametrized cases green; existing Claude Code tests still green.
  - Depends on: 2.1.
  - Risk: High — seven probes × two platforms, symmetric with 2.2. Same mitigation: one test per probe, full mocking of subprocess/`winreg`.

#### Phase 3: Operator UX (items D, E)

- [ ] **Step 3.1 — OS-specific neither-detected exit message** (S) — **TDD: tests first**
  - File: `src/installer.py` (the existing "no client detected" branch), `tests/test_installer.py`.
  - Behavior: switch on `sys.platform`. Windows message mentions MS Store / Packaged App + `--client claude-desktop` override + `--diagnose`. macOS mentions `/Applications/Claude.app`. Linux mentions desktop-file paths. Exit code unchanged.
  - Tests: three tests, one per platform, asserting exact substrings in captured stderr.
  - Verify: `uv run pytest tests/test_installer.py -k neither_detected -v` — green.
  - Depends on: 2.2, 2.3.
  - Risk: Low.

- [ ] **Step 3.2 — `install.ps1` default `UV_CACHE_DIR`** (S)
  - File: `install.ps1`.
  - Behavior: before the `uvx --from git+...` invocation, add `if (-not $env:UV_CACHE_DIR) { $env:UV_CACHE_DIR = Join-Path $env:TEMP 'uvcache' }` with an inline comment explaining the OneDrive / Defender / EDR lock-contention root cause.
  - Verify: manual smoke — run `install.ps1` on a Windows box (or in CI if available), inspect that `$env:UV_CACHE_DIR` is set to the `%TEMP%\uvcache` value when not pre-set, and left alone when pre-set.
  - Depends on: none.
  - Risk: Low — one-line default with a guard.

#### Phase 4: Self-diagnosis (items F, G)

- [ ] **Step 4.1 — `--verbose` flag wiring** (M) — **TDD: tests first**
  - File: `src/installer.py` (argparse + a module-level `_VERBOSE` flag or threaded parameter), `tests/test_installer.py`.
  - Behavior: new `--verbose` flag; when set, detection probes emit `[probe] <name>: hit <path>` / `[probe] <name>: miss` via `_emit`. No effect on non-verbose runs. Redacts through `_redact` if any probe output could include secrets (none do today, but the code path exists).
  - Tests: verbose run captures probe lines for Claude Desktop + Claude Code; non-verbose run captures none; `--verbose` combined with existing flags doesn't break `--dry-run`.
  - Verify: `uv run pytest tests/test_installer.py -k verbose -v` — green.
  - Depends on: 2.2, 2.3.
  - Risk: Medium — threading the verbosity into probe functions without breaking their signatures for existing tests. Mitigation: module-level flag (read-only from probes) keeps signatures stable.

- [ ] **Step 4.2 — `--diagnose` command** (L) — **TDD: tests first**
  - File: `src/installer.py` (new top-level function invoked from argparse, short-circuits the wizard), `tests/test_installer.py`.
  - Behavior: read-only; exits 0. Emits a structured report:
    - OS (`platform.platform()`), Python (`sys.version`), package version (`_package_version()`), uv version (`subprocess.run(["uv", "--version"])`).
    - Env var values: `TESTRAIL_URL`, `TESTRAIL_USERNAME`, `TESTRAIL_API_KEY` (via `_redact`), `TESTRAIL_MCP_REF`, `UV_CACHE_DIR`, `APPDATA`, `LOCALAPPDATA`, `USERPROFILE` / `HOME`.
    - Reparse-point detection on `%APPDATA%` / `%LOCALAPPDATA%` (Windows) — `os.path.realpath` vs raw; flag mismatch.
    - Every detection probe with pass/fail + matched path (reuses verbose-mode output format).
    - uv cache write-test: create + delete a temp file under `UV_CACHE_DIR` (fallback `%TEMP%` / `/tmp`); report success + elapsed ms or the exception.
    - Network reachability: HEAD `raw.githubusercontent.com`; HEAD the resolved `TESTRAIL_URL` (if set); 3 s timeout each.
  - Tests:
    - `--diagnose` exits 0 and emits the expected section headers (OS, Env, Probes, uv cache, Network).
    - API key is redacted in output (regex-assert masked form, not raw).
    - Network probes handle timeout / unreachable without crashing (mock httpx / urllib to raise).
    - uv cache write-test reports failure cleanly when dir is unwritable (mock).
    - Exit code is 0 even when probes fail (it's a report, not a gate).
  - Verify: `uv run pytest tests/test_installer.py -k diagnose -v` — green; `uv run python -m src.installer --diagnose` produces a human-readable report with key redacted.
  - Depends on: 4.1 (reuses probe emitter), 2.2, 2.3.
  - Risk: High — largest single addition; network probes need strict timeouts and broad exception handling. Mitigation: every subprocess / network call wrapped in try/except and time-boxed; tests mock every external call.

### Test plan

- **Unit (phased):**
  - `tests/test_installer.py::test_normalize_testrail_url_*` — parametrized happy + failure cases (step 1.1).
  - `tests/test_installer.py::test_url_normalization_in_{prompt,flag,env}` — three call-site integration tests (step 1.2).
  - `tests/test_installer.py::test_claude_desktop_detection_*` — parametrized per probe per platform (step 2.2).
  - `tests/test_installer.py::test_claude_code_detection_*` — parametrized per probe per platform (step 2.3) — **same probe-vocabulary as Desktop where applicable** (PATH / installer-fallback / alt-install / npm-global / install-binary / running-process / registry).
  - `tests/test_installer.py::test_detection_parity` — asserts probe names used by `_claude_code_details` and `_claude_desktop_details` share a consistent vocabulary, so `--diagnose` output reads the same format for both sections.
  - `tests/test_installer.py::test_neither_detected_message_*` — one per platform (step 3.1).
  - `tests/test_installer.py::test_verbose_*` — probe-line emission (step 4.1).
  - `tests/test_installer.py::test_diagnose_*` — report sections, redaction, timeout handling, exit code (step 4.2).
- **Integration / manual:**
  - macOS (Eden's box): `uv run testrail-mcp-install --diagnose` — eyeball the report, confirm API key is masked, confirm `/Applications/Claude.app` probe hits.
  - Windows (Idan's box, coordinate asynchronously): end-to-end wizard run with `TESTRAIL_URL` set to the browser-tab URL — confirm normalization + successful ping; run with Claude Desktop closed and open — confirm detection hits; run `install.ps1` from scratch in a fresh shell — confirm `UV_CACHE_DIR` is auto-set.
- **Backward-compat guard:** full `uv run pytest` must pass unchanged — the ~100 existing tests that monkeypatch `_detect_claude_code` / `_claude_desktop_detected` to bool must keep working because those helpers remain for truth checks (see `_ClientDetection` docstring L150–157).

### Verification

- `uv run pytest tests/test_installer.py -v` — all new + existing tests green.
- `uv run pytest` — full suite green (no regressions elsewhere).
- `uv run ruff check src tests` — clean.
- `uv run ruff format --check src tests` — clean.
- `uv run mypy src` — no new errors beyond the current baseline.
- `uv run python -m src.installer --diagnose` — prints a complete report, API key redacted, exits 0.
- `uv run python -m src.installer --verbose --dry-run --client claude-desktop --scope user --url https://example.testrail.io/index.php?/suites/view/1 --username a@b.com --api-key REDACTED --no-validate` — prints `Normalized:` line and probe lines, completes dry-run, API key masked in any echo.
- Manual: `install.ps1` smoke on Windows — `$env:UV_CACHE_DIR` auto-defaults when not set.

### Risks & Mitigations

- **Risk: Five probes × three platforms in step 2.2 is easy to get subtly wrong.** → Mitigation: one test per probe per platform before the implementation lands; no shared test bodies; monkeypatch `sys.platform` + every external call so macOS CI covers the Windows path.
- **Risk: `winreg` import breaks non-Windows runs.** → Mitigation: optional-import guarded by `sys.platform == "win32"`; tests stub `winreg` on non-Windows platforms.
- **Risk: `tasklist` CSV parsing on locales that produce non-English headers.** → Mitigation: use `/FO CSV` (language-independent format) and match on the `"Claude.exe"` cell, not a header name.
- **Risk: `--diagnose` network probes hang.** → Mitigation: 3 s timeout on every call; broad try/except; report prints the exception and moves on.
- **Risk: API key accidentally leaked in verbose or diagnose output.** → Mitigation: `_redact` is the single choke point for any code path that touches `api_key`; a dedicated test asserts the masked form appears and the raw form does not; invariant remains under `spektr` review.
- **Risk: Extending `_ClientDetection` breaks the ~100 tests that monkeypatch the bool helpers.** → Mitigation: the bool helpers stay — the dataclass adds a field with a default; step 2.1 runs the full suite before step 2.2 starts.
- **Risk: `install.ps1` auto-setting `UV_CACHE_DIR` overrides a user's intentional empty-string.** → Mitigation: guard is `-not $env:UV_CACHE_DIR`, which treats empty string as unset — matches PowerShell convention and the exact failure Idan hit.

### Non-goals

- `--force` flag to skip detection entirely (Tier 3; reopen if requested).
- Reparse-point *warning* when `%APPDATA%` is redirected (Tier 3; `--diagnose` reports it but the wizard does not warn mid-run).
- Registry *writes* for Claude Desktop config (Tier 3; still file-based only).
- Changing any existing flag's behavior or exit code.
- Adding third-party dependencies.
- Touching any file outside `src/installer.py`, `install.ps1`, and `tests/test_installer.py`.

### Success Criteria

- [ ] Pasting a full TestRail browser-tab URL (as `TESTRAIL_URL` env var, as `--url` flag, or at the interactive prompt) produces a successful ping and an on-screen `Normalized:` notice.
- [ ] Claude Desktop is detected on Windows via any of: config-dir, alt config-dir, install-binary, MSIX package, running process, registry. Each detection surfaces the probe name (`detected_via`) on the display line.
- [ ] Claude Code is detected on Windows via any of: PATH, installer-fallback (`~/.claude/local/`), npm-global, app-install-binary, running process, registry. Each detection surfaces the probe name.
- [ ] Detection parity: the two clients use the same probe-name vocabulary — a teammate looking at `--diagnose` output sees a symmetric report for both Code and Desktop sections.
- [ ] When neither client is detected, the exit message is OS-specific and mentions `--diagnose` and the `--client` override.
- [ ] `install.ps1` run from a fresh PowerShell on a box with OneDrive + Defender does not hit the `Access is denied` rename error.
- [ ] `--diagnose` prints a complete report, exits 0, API key is masked.
- [ ] `--verbose` emits per-probe hit/miss lines during detection.
- [ ] Full test suite green (`uv run pytest`).
- [ ] Static checks clean (`uv run ruff check`, `uv run ruff format --check`, `uv run mypy src`).
- [ ] No new third-party dependencies added to `pyproject.toml`.
- [ ] `_redact` remains the sole path for API-key output; no test finds the raw key in any captured stream.

### Review gate

Before `feniks` begins implementation:

1. Eden reviews this plan and confirms the A–G scope is correct and Tier 3 stays out.
2. Eden confirms the layered Windows detection order (config dir → install binary → MSIX → process → registry) matches his expectation of "fastest + cheapest probe first."
3. Eden confirms `install.ps1` defaulting `UV_CACHE_DIR` to `%TEMP%\uvcache` is acceptable (vs. e.g. `C:\uv-cache` which Idan used — but `%TEMP%` is user-writable by default and not synced by OneDrive).
4. On approval, `feniks` picks up and runs TDD against each step in phase order. Each phase is independently mergeable.
