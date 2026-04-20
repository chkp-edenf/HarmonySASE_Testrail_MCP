---
number: 1
title: Wizard installer for TestRail MCP
date: 2026-04-20
status: pending
needs_tdd: true
route: A
adr: ADR-001-wizard-installer.md
---

## Plan: Wizard Installer for TestRail MCP [konstruct]

### Overview
Execute ADR-001 by shipping a second console_script `testrail-mcp-install` in `src/installer.py` plus `install.sh` / `install.ps1` bootstrappers. The wizard detects Claude Code and/or Claude Desktop, prompts for credentials, optionally pings TestRail, and atomically writes MCP config entries. All work is test-driven and honors the ADR's additive contract — no changes to runtime behavior, env var set, or existing console_script.

### Assumptions
- Eden is on macOS (current working directory confirms Darwin 25.2.0); Windows paths are implemented from the ADR path map but verified by automated tests only, not manual QA during this plan.
- `pytest` is not yet a project dependency — must be added under a dev optional group.
- `httpx >= 0.27.0` is already a runtime dep (`pyproject.toml:24`); it can be imported from the installer for the TestRail ping.
- Branch `feat/wizard-installer` is already checked out off `origin/main` @ 52d2b21.
- The three ADR Open Questions (minimum `claude` CLI version, Windows `%APPDATA%` verification, cache-warming) are addressed in Phase 0 research or explicitly deferred per ADR D8.

### Constraints (from ADR + user)
- Branch: `feat/wizard-installer`. No push, no PR.
- Python 3.11+, stdlib preferred; `httpx` is the only third-party import allowed in the installer.
- No new runtime deps on the core MCP.
- Every commit body ends with `Reviewed: full` footer (global rule, /chekpoint tier = FULL).
- `/chekpoint` runs kody + spektr + python-reviewer; `--no-verify` is forbidden.

### ADR red flags addressed in this plan
1. `.gitignore` allow-list (ADR Consequences) — Step 8.1 adds `!/install.sh`, `!/install.ps1`, `!/docs/**` and verifies via `git status`.
2. `claude mcp add` minimum version (ADR Open Question 1) — Step 0.1 empirically determines it; finding recorded in Step 2.1 docstring.
3. `@v2.0.0` pinning drift (ADR D3) — Step 10.1 adds a release-checklist note.

---

### Phase 0 — Research (read-only, no code)

- [ ] Step 0.1: Probe local `claude` CLI for `mcp add` compatibility (S)
  - Files: none (record findings in Phase 2 docstring).
  - Test first: no (read-only probe).
  - Verify: run `claude --version` and `claude mcp add --help`; paste output into the ADR Open Question 1 answer section when updating the ADR post-plan (or into the installer module docstring if the ADR is immutable post-accept). Confirm the `--scope`, `-e KEY=VAL`, and `-- cmd` argument forms exist.

- [ ] Step 0.2: Verify `uv` version and `uvx --from git+<repo>` support (S)
  - Files: none.
  - Test first: no.
  - Verify: `uv --version`; `uvx --from git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git@main testrail-mcp --help` returns 0 (Resolution #3 confirmed `v2.0.0` tag is not pushed; probe uses `@main`). Record minimum `uv` version in `install.sh` comment.

- [ ] Step 0.3: Confirm Claude Desktop config dir behavior on macOS (S)
  - Files: none.
  - Test first: no.
  - Verify: `ls -la "$HOME/Library/Application Support/Claude/"`. Document whether the parent dir exists pre-launch. If it does not exist, the installer's `mkdir -p` step (ADR D2 algorithm step 1) remains correct — log the observation in Step 5.1's docstring.

---

### Phase 1 — Test scaffolding and harness

- [ ] Step 1.1: Add pytest to dev optional deps (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/pyproject.toml`
  - Test first: no (config change).
  - Complexity: S.
  - Verify: `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` passes; `uv pip install -e '.[dev]'` in a throwaway venv succeeds. Add under `[project.optional-dependencies]`: `dev = ["pytest>=8.0", "pytest-cov>=5.0"]`.

- [ ] Step 1.2: Create `tests/` package skeleton and shared fixtures (M)
  - Files:
    - `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/__init__.py` (empty)
    - `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/conftest.py`
  - Test first: no (fixtures are the test infrastructure; they are validated when first consumed in Step 1.3).
  - Complexity: M (~60 LoC: 4 fixtures).
  - Fixtures to implement:
    - `fake_claude_cli(monkeypatch)` — monkey-patch `shutil.which` and `subprocess.run` to simulate CLI presence/absence and capture invocation args.
    - `fake_claude_desktop_config(tmp_path)` — parametrized via `pytest.fixture(params=[...])` for four states: missing file, empty `{}`, `{"mcpServers":{"other":{...}}}`, malformed JSON.
    - `fake_prompts(monkeypatch)` — replaces `builtins.input` and `getpass.getpass` with a scripted queue.
    - `fake_testrail_ping(monkeypatch)` — patches `httpx.get` (or an installer-local `_ping()` helper) to return configurable `(status_code, exception)` tuples.
  - Verify: `uv run pytest --collect-only` lists the fixtures as collectable.

- [ ] Step 1.3: Write first red test — module import + `--dry-run` smoke (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes (feniks red step).
  - Complexity: S (~15 LoC).
  - Test cases (all should FAIL initially):
    - `test_installer_module_imports` — `import src.installer`.
    - `test_installer_main_exits_0_on_dry_run` — invokes `src.installer.main(["--dry-run", "--yes", "--client", "both", "--scope", "user", "--url", "https://x.testrail.io", "--username", "u@x.com", "--api-key", "A"*40, "--no-validate"])` and asserts `SystemExit.code == 0` (or returns 0 if main returns int).
  - Verify: `uv run pytest tests/test_installer.py -v` shows 2 failures with `ModuleNotFoundError: No module named 'src.installer'`. This is the red baseline.

---

### Phase 2 — Core installer scaffold

- [ ] Step 2.1: Create `src/installer.py` with argparse skeleton (M)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`
  - Test first: yes — the tests from Step 1.3 drive this; add a green test `test_installer_help_text_lists_all_flags` asserting `--client`, `--scope`, `--url`, `--username`, `--api-key`, `--no-validate`, `--yes`, `--dry-run`, `--ref` all appear in `--help`.
  - Complexity: M (~80 LoC: module docstring with Step 0.1 findings, argparse setup, `main()` entry point that currently just echoes parsed args under `--dry-run` and exits 0).
  - Depends on: 1.3.
  - Verify: `uv run pytest tests/test_installer.py::test_installer_main_exits_0_on_dry_run -v` goes green; `uv run pytest tests/test_installer.py::test_installer_help_text_lists_all_flags -v` goes green; both Step 1.3 tests pass.

- [ ] Step 2.2: Credential precedence resolution (M)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: M (~40 LoC impl + ~50 LoC tests).
  - Depends on: 2.1.
  - Tests (write first, red):
    - `test_api_key_flag_beats_env` — `--api-key F`, env `TESTRAIL_API_KEY=E` ⇒ resolved key == `F`.
    - `test_api_key_env_beats_prompt` — no flag, env `TESTRAIL_API_KEY=E`, prompt would return `P` ⇒ resolved == `E` and `getpass` not called.
    - `test_api_key_prompt_when_missing` — no flag, no env ⇒ `fake_prompts` queue `["P"]` consumed ⇒ resolved == `P`.
    - Equivalent tests for `--url`/`TESTRAIL_URL` and `--username`/`TESTRAIL_USERNAME`.
    - `test_api_key_short_rejected` — key of length 19 ⇒ re-prompt; length 20+ ⇒ accepted (ADR D4).
    - `test_username_warn_not_block_on_non_email` — username `admin` logs a warning, returns 0 exit.
    - `test_url_reprompt_on_invalid` — malformed URL (`ftp://x`) re-prompts; valid URL (`https://x.testrail.io`) accepted.
  - Impl: `_resolve_credentials(args) -> tuple[str, str, str]` following ADR D4 precedence; `_prompt_url()`, `_prompt_username()`, `_prompt_api_key()` helpers using `input()` and `getpass.getpass()`.
  - Verify: `uv run pytest tests/test_installer.py -k credential -v` all green.

- [ ] Step 2.3: Ctrl-C clean-exit handler (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: S (~10 LoC impl + ~20 LoC test).
  - Depends on: 2.2.
  - Test (red first): `test_ctrl_c_at_prompt_exits_clean_no_write` — patch `input` to raise `KeyboardInterrupt`; assert `SystemExit.code == 130` and no file under `tmp_path` was modified.
  - Impl: wrap `main()` body in `try/except KeyboardInterrupt: sys.exit(130)`.
  - Verify: `uv run pytest tests/test_installer.py::test_ctrl_c_at_prompt_exits_clean_no_write -v` green.

---

### Phase 3 — Detection

- [ ] Step 3.1: Claude Code CLI detection (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: S (~20 LoC impl + ~30 LoC tests).
  - Tests (red first):
    - `test_detect_claude_code_present` — `fake_claude_cli` returns path + version 0 exit ⇒ `_detect_claude_code()` returns `True`.
    - `test_detect_claude_code_absent` — `shutil.which` returns `None` ⇒ returns `False`.
    - `test_detect_claude_code_version_fails` — `which` returns path, `claude --version` exits 1 ⇒ returns `False`.
  - Impl: `_detect_claude_code() -> bool` per ADR D1 steps 1-2 (2-second timeout on subprocess).
  - Verify: `uv run pytest tests/test_installer.py -k claude_code -v` green.

- [ ] Step 3.2: Claude Desktop detection (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: S (~15 LoC impl + ~30 LoC tests).
  - Depends on: 3.1.
  - Tests (red first):
    - `test_detect_claude_desktop_macos_present` — patch `sys.platform="darwin"` and `pathlib.Path.expanduser` to point at `tmp_path` with `Library/Application Support/Claude` created ⇒ detect returns path.
    - `test_detect_claude_desktop_windows_appdata` — `sys.platform="win32"`, `%APPDATA%` set ⇒ returns `$APPDATA\Claude\claude_desktop_config.json`.
    - `test_detect_claude_desktop_linux_xdg` — `sys.platform="linux"` ⇒ returns `~/.config/Claude/claude_desktop_config.json`.
    - `test_detect_claude_desktop_absent` — parent dir missing ⇒ returns `None` (installer will later offer to create parent if user picks Desktop).
  - Impl: `_claude_desktop_config_path() -> Path | None` with OS-specific branches.
  - Verify: `uv run pytest tests/test_installer.py -k claude_desktop -v` green.

- [ ] Step 3.3: Client-selection menu (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: S (~20 LoC impl + ~25 LoC tests).
  - Depends on: 3.1, 3.2.
  - Tests (red first):
    - `test_menu_skips_undetected_clients` — only Claude Desktop detected; menu shows only `[2] Claude Desktop` and accepts `2`.
    - `test_menu_flag_overrides_menu` — `--client code` with only Desktop detected ⇒ warn + honor flag (flag wins, menu not shown).
    - `test_menu_both_selected` — both detected, user picks `3` ⇒ returns `{"code", "desktop"}`.
  - Impl: `_choose_clients(args) -> set[str]` — if `args.client` set, return directly; otherwise interactive menu skipping undetected entries.
  - Verify: `uv run pytest tests/test_installer.py -k menu -v` green.

---

### Phase 4 — Claude Code config writer

- [ ] Step 4.1: `claude mcp add` subprocess writer (primary path) (M)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: M (~40 LoC impl + ~60 LoC tests).
  - Depends on: 3.1, 2.2.
  - Tests (red first):
    - `test_claude_cli_writer_invokes_with_correct_args` — `fake_claude_cli` captures args ⇒ assert exactly `["claude", "mcp", "add", "--scope", "user", "-e", "TESTRAIL_URL=...", "-e", "TESTRAIL_USERNAME=...", "-e", "TESTRAIL_API_KEY=...", "testrail", "--", "uvx", "--from", "git+https://...@v2.0.0", "testrail-mcp"]`.
    - `test_claude_cli_writer_redacts_api_key_in_logs` — log capture shows `TESTRAIL_API_KEY=***`, never the raw key.
    - `test_claude_cli_writer_respects_scope_project` — `--scope project` flag ⇒ command carries `--scope project`.
    - `test_claude_cli_writer_respects_ref_override` — `--ref main` ⇒ command carries `@main`.
    - `test_claude_cli_writer_dry_run_no_subprocess` — `--dry-run` ⇒ subprocess.run NOT invoked, diff-plan printed to stdout.
    - `test_claude_cli_writer_nonzero_exit_triggers_fallback` — subprocess exit 1 ⇒ fallback JSON writer invoked (covered further in 4.2).
  - Impl: `_write_claude_code_via_cli(args, creds) -> WriteResult`; argument array passed to `subprocess.run(..., check=False, capture_output=True, timeout=30)`; key redacted via separate logger-only copy of command list.
  - Verify: `uv run pytest tests/test_installer.py -k claude_cli -v` green.

- [ ] Step 4.2: Direct JSON fallback for Claude Code (M)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: M (~60 LoC impl + ~50 LoC tests).
  - Depends on: 4.1.
  - Tests (red first):
    - `test_json_fallback_user_scope_writes_home_claude_json` — target resolves to `~/.claude.json` (patched via `HOME`/`Path.home` to `tmp_path`); assert `mcpServers.testrail` present after write.
    - `test_json_fallback_project_scope_writes_local_mcp_json` — `--scope project` ⇒ `./.mcp.json` in `tmp_path`.
    - `test_json_fallback_preserves_other_mcpservers` — seed file with `{"mcpServers":{"other":{...}}}` ⇒ after write, `other` still present, `testrail` added.
    - `test_json_fallback_prompts_on_existing_testrail` — existing `testrail` key ⇒ prompt; answer `n` aborts with exit 1; answer `y` overwrites.
    - `test_json_fallback_atomic_rename_used` — monkey-patch `os.replace` to record calls; assert called exactly once with (tmp-path, final-path).
    - `test_json_fallback_api_key_not_in_backup` — backup file IS written (per D2); assert path exists, but also assert API key is only in backup's own write, never in stderr/stdout logs.
  - Impl: `_write_claude_code_via_json(args, creds)` — atomic temp + `os.replace` + `.bak.<ts>` (D2 algorithm).
  - Verify: `uv run pytest tests/test_installer.py -k json_fallback -v` green.

---

### Phase 5 — Claude Desktop config writer

- [ ] Step 5.1: Atomic merge-write for Claude Desktop config (L)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: L (~90 LoC impl + ~120 LoC tests — 6 distinct code paths).
  - Depends on: 3.2, 4.2 (shares atomic-write helper with 4.2 — extract into `_atomic_write_json(path, data, make_backup=True)`).
  - Tests (red first, parametrized on `fake_claude_desktop_config`):
    - `test_desktop_missing_file_creates_parent_and_writes_seed` — parent dir missing ⇒ `mkdir -p` then write `{"mcpServers":{"testrail":...}}`. No backup (nothing to back up).
    - `test_desktop_empty_mcpservers_merged` — empty `{"mcpServers":{}}` ⇒ after write, only `testrail` present.
    - `test_desktop_preserves_other_mcps` — `{"mcpServers":{"other":{...}}}` ⇒ `other` untouched, `testrail` added.
    - `test_desktop_existing_testrail_prompts_overwrite` — prompt ⇒ `n` aborts with exit 1 + guidance message; `y` overwrites.
    - `test_desktop_malformed_json_prompts_consent` — malformed file ⇒ backup created FIRST, then prompt; `n` aborts with backup intact; `y` overwrites with seed.
    - `test_desktop_backup_created_before_parse` — inject `json.loads` failure; assert backup file exists on disk at the moment of failure (sequence: backup → parse).
    - `test_desktop_atomic_rename_preserves_on_crash` — simulate exception between temp-write and `os.replace` ⇒ original file unchanged.
  - Impl: `_write_claude_desktop(path, creds, args) -> WriteResult`; extract shared `_atomic_write_json()` and `_backup_file(path) -> Path`.
  - Security note for spektr: explicit `os.replace` (not `shutil.move`) to guarantee atomic semantics; file modes preserved via `shutil.copy2` for backup.
  - Verify: `uv run pytest tests/test_installer.py -k desktop -v` all 7 green.

---

### Phase 6 — Optional TestRail ping

- [ ] Step 6.1: Credentials ping with error classification (M)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: M (~35 LoC impl + ~50 LoC tests).
  - Depends on: 2.2.
  - Tests (red first, using `fake_testrail_ping`):
    - `test_ping_200_ok_returns_success` — status 200 ⇒ returns `PingResult.OK`, proceeds.
    - `test_ping_401_reprompts_credentials` — first call 401, second call 200 ⇒ re-prompts API key, succeeds on second.
    - `test_ping_403_warns_continues` — 403 ⇒ returns `PingResult.WARN`, continues.
    - `test_ping_network_error_warns_continues` — `httpx.ConnectError` ⇒ `PingResult.WARN`, continues.
    - `test_ping_skipped_when_no_validate` — `--no-validate` ⇒ ping function never called.
    - `test_ping_uses_5s_timeout` — assert `httpx.get` called with `timeout=5`.
  - Impl: `_ping_testrail(url, username, api_key) -> PingResult` calling `httpx.get(f"{url.rstrip('/')}/index.php?/api/v2/get_projects", auth=(username, api_key), timeout=5)`.
  - Verify: `uv run pytest tests/test_installer.py -k ping -v` green.

- [ ] Step 6.2: Wire ping into main() flow + end-to-end dry-run test (M)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/src/installer.py`, `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/tests/test_installer.py`
  - Test first: yes.
  - Complexity: M (~20 LoC impl + ~40 LoC tests).
  - Depends on: 4.1, 4.2, 5.1, 6.1.
  - Tests (red first):
    - `test_main_both_clients_dry_run_prints_plan_writes_nothing` — full invocation with `--client both --dry-run --yes` ⇒ stdout lists planned writes for both `~/.claude.json` and desktop config; no files modified; ping NOT called because `--no-validate` or because `--dry-run` implies no-validate (decision: `--dry-run` implies `--no-validate` — document in docstring).
    - `test_main_happy_path_writes_both` — no `--dry-run`, `--no-validate`, `--yes`, both clients detected ⇒ both config files updated; exit 0.
    - `test_main_final_summary_printed` — successful run prints summary with: clients written, scope, ping result (or skipped), backup paths, masked key length.
  - Impl: compose `_resolve_credentials` → `_choose_clients` → optional `_ping_testrail` → dispatch to writers → print summary.
  - Verify: `uv run pytest tests/test_installer.py -v` — full test file green; run `uv run pytest --cov=src.installer --cov-report=term-missing tests/test_installer.py` and confirm coverage >= 80%.

---

### Phase 7 — Shell bootstrappers

- [ ] Step 7.1: `install.sh` POSIX bootstrapper (M)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/install.sh`
  - Test first: no (shell script; tested via Phase 9 verification commands, not pytest).
  - Complexity: M (~50 LoC).
  - Depends on: Phase 6 complete (installer is callable).
  - Contents:
    - Shebang `#!/bin/sh` (POSIX-sh per user constraint, not bash-only).
    - Detect `uv` via `command -v uv`; if absent, prompt `y/N` consent before `curl -LsSf https://astral.sh/uv/install.sh | sh`.
    - Refresh PATH after install: `export PATH="$HOME/.local/bin:$PATH"` (matches astral.sh default).
    - Read `TESTRAIL_MCP_REF` env var, default `main` (Resolution #3 — no release tag yet).
    - `exec uvx --from "git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git@${TESTRAIL_MCP_REF}" testrail-mcp-install "$@"` (forwards all flags).
    - Chmod comment: file must be `chmod +x install.sh` when committed.
  - Verify: `sh -n install.sh` (syntax check); `shellcheck install.sh` if available (not a blocker if shellcheck absent); manual dry-run: `sh install.sh --help` prints installer help via uvx.

- [ ] Step 7.2: `install.ps1` Windows bootstrapper (M)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/install.ps1`
  - Test first: no (shell script).
  - Complexity: M (~45 LoC).
  - Depends on: 7.1 (mirror structure).
  - Contents:
    - Top-of-file doc comment referencing `Set-ExecutionPolicy -Scope Process Bypass` per ADR Risks.
    - `Get-Command uv -ErrorAction SilentlyContinue`; if null, prompt then `irm https://astral.sh/uv/install.ps1 | iex`.
    - Read `$env:TESTRAIL_MCP_REF`, default `main` (Resolution #3 — no release tag yet).
    - `& uvx --from "git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git@$Ref" testrail-mcp-install @args` (forwards all args via PowerShell splat).
  - Verify: manual — cannot run on macOS; rely on PowerShell syntax review during kody's /chekpoint pass. Add a comment pointing reviewers at the astral.sh reference script.

---

### Phase 8 — Repo plumbing

- [ ] Step 8.1: `.gitignore` allow-list update (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/.gitignore`
  - Test first: no (config).
  - Complexity: S (3-line edit).
  - Depends on: 7.1, 7.2 (files must exist to verify tracking).
  - Add after existing allow-list:
    ```
    !/install.sh
    !/install.ps1
    !/docs/**
    ```
  - Verify: `git status --porcelain install.sh install.ps1 docs/` shows all three as untracked/modified (not ignored). `git check-ignore -v install.sh` returns non-zero (means: NOT ignored). Also verify `tests/` is ignored as expected (it's a dev-only dir — **IMPORTANT: ADR did not explicitly address tests/ tracking**; add `!/tests/**` here as well, justification below).
  - **Note to Eden**: the `.gitignore` allow-list also excludes `tests/` today. Since the plan adds tests, we must also add `!/tests/**` (and `!/conftest.py` if we ever add a root-level one). Flagged as an ambiguity in the ADR — resolved in favor of tracking tests (they are first-class artifacts per global testing rules).

- [ ] Step 8.2: `pyproject.toml` second console_script (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/pyproject.toml`
  - Test first: no (already covered indirectly by Phase 9 `uvx --from . testrail-mcp-install --help`).
  - Complexity: S (1-line add).
  - Depends on: 2.1.
  - Edit `[project.scripts]` block to:
    ```toml
    [project.scripts]
    testrail-mcp = "src.stdio:run"
    testrail-mcp-install = "src.installer:main"
    ```
  - Verify: `python3 -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert 'testrail-mcp-install' in d['project']['scripts']"` passes; `uv build` succeeds; `uvx --from dist/*.whl testrail-mcp-install --help` prints argparse help.

- [ ] Step 8.3: README.md Quick Install prepend (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/README.md`
  - Test first: no (docs).
  - Complexity: S (~25 new lines, no deletions).
  - Depends on: 7.1, 7.2, 8.2.
  - Insert a new `## Quick Install (Wizard)` section immediately after the `## Highlights` section and **before** the existing `## Quick Start` section. Content:
    - macOS/Linux: `curl -LsSf https://raw.githubusercontent.com/chkp-edenf/HarmonySASE_Testrail_MCP/main/install.sh | sh`
    - Windows (PowerShell): `irm https://raw.githubusercontent.com/chkp-edenf/HarmonySASE_Testrail_MCP/main/install.ps1 | iex`
    - Note: "Prefer manual config? The step-by-step Quick Start below still works."
  - **ADR D5 enforcement**: the existing Quick Start section (lines 24-80) and manual JSON block (lines 36-50) must remain **byte-for-byte identical** post-edit. Verify via `git diff README.md` showing only additions, no deletions within that range.
  - Verify: `git diff README.md | grep '^-' | grep -v '^---'` returns empty (no removed lines). `markdownlint README.md` if available.

---

### Phase 9 — Verification and /chekpoint

- [ ] Step 9.1: End-to-end smoke tests (S)
  - Files: none (verification only).
  - Test first: no.
  - Complexity: S.
  - Depends on: Phase 8 complete.
  - Commands (all must pass):
    1. `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` (exit 0).
    2. `uv build` succeeds; produces `dist/harmonysase_testrail_mcp-2.0.0-py3-none-any.whl`.
    3. `uvx --from dist/*.whl testrail-mcp-install --help` exits 0 and prints help text containing all 9 flags.
    4. `uvx --from . testrail-mcp-install --dry-run --yes --client both --scope user --url https://example.testrail.io --username test@example.com --api-key $(python3 -c 'print("A"*40)') --no-validate` exits 0 and prints planned writes for both clients; `git status --porcelain ~/.claude.json ~/Library/Application\ Support/Claude/claude_desktop_config.json` shows no modification (verifies `--dry-run` truly touches nothing).
    5. `uv run pytest tests/ -v --cov=src.installer --cov-report=term-missing` passes with coverage >= 80% on `src/installer.py`.
    6. `sh -n install.sh` (exit 0).
  - Verify: all six commands return non-zero exit = BLOCK; any coverage < 80% = WARN escalated to BLOCK if on critical paths (file-writers, credential resolution).

- [ ] Step 9.2: Run /chekpoint at FULL tier (M)
  - Files: none (orchestration).
  - Test first: no.
  - Complexity: M (command orchestration; individual reviewer outputs are the real work).
  - Depends on: 9.1.
  - Verify:
    - kody runs (general TS/Python reviewer — coordinates others).
    - python-reviewer validates PEP 8, type hints, pathlib usage, `f-strings`, `logging` not `print`, `subprocess` with list args.
    - spektr validates: no API key in logs (grep `TESTRAIL_API_KEY=` in captured test output must show only `***`), no `shell=True`, no path traversal in config-path resolution, atomic-rename used, backups created before parse.
    - Zero CRITICAL/BLOCK findings; HIGH findings resolved or explicitly accepted.
  - Commit with `Reviewed: full` footer.

---

### Phase 10 — Release checklist delta

- [ ] Step 10.1: Release checklist note (S)
  - Files: `/Users/edenf/Projects/checkpoint/Eden/Tools/BMAD_HarmonySASE_Testrail_MCP/docs/RELEASE_CHECKLIST.md` (NEW) or append to existing if present.
  - Test first: no (docs).
  - Complexity: S (~15 LoC).
  - Depends on: 8.3.
  - Content (new file):
    ```markdown
    # Release Checklist

    For every new tag (e.g., v2.1.0):

    1. Bump `version` in `pyproject.toml`.
    2. Update `TESTRAIL_MCP_REF` default in `install.sh` (search for `v2.0.0`).
    3. Update `$Ref` default in `install.ps1` (search for `v2.0.0`).
    4. Update the curl/irm URLs in `README.md` Quick Install section (replace `v2.0.0` in raw.githubusercontent.com paths).
    5. Create and push the tag: `git tag v2.1.0 && git push origin v2.1.0`.
    6. Smoke-test the one-liners against the fresh tag from a clean shell.
    ```
  - Verify: `ls docs/RELEASE_CHECKLIST.md` exists; `grep -c 'install.sh\|install.ps1\|README.md' docs/RELEASE_CHECKLIST.md` >= 3.

---

### Testing Strategy

- **Unit**: `tests/test_installer.py` — covers every branch in `src/installer.py`. Parametrized fixtures drive the four Claude Desktop config states and the four credential-source combinations. Every file-write test pins the write target inside `tmp_path`; no test may touch `$HOME` or `/Users/edenf/Library/`. Coverage target: 80% minimum on `src/installer.py`.
- **Integration**: deferred per ADR D7 (requires live `claude` CLI + real TestRail creds). Not in scope for this plan.
- **Smoke**: Phase 9 commands exercise `uv build` + `uvx` path against the local checkout.
- **TDD cadence**: feniks enforces red-green-refactor per step. Every code-producing step lists failing tests BEFORE the implementation sub-task.

### Risks & Mitigations

- **Risk**: `claude mcp add` argument format differs on Eden's installed CLI version → implementation breaks on first integration test.
  **Mitigation**: Phase 0.1 probe records exact arg format; Step 4.1 tests pin the exact arg list captured from that probe.
- **Risk**: Windows-specific code paths (Step 3.2, 5.1) aren't exercisable on Eden's macOS machine → regressions ship undetected.
  **Mitigation**: all Windows paths are unit-tested via `monkeypatch.setattr(sys, "platform", "win32")` with fake `%APPDATA%`. Windows manual QA deferred (ADR Open Question 2); Step 7.2 comment flags this for future contributors.
- **Risk**: `tests/` not in `.gitignore` allow-list → first `git add` silently drops the test directory.
  **Mitigation**: Step 8.1 explicitly adds `!/tests/**` (ADR only flagged `install.sh`/`install.ps1`/`docs/`; this plan broadens the fix).
- **Risk**: `httpx` import in installer creates implicit dependency that breaks uvx install if the installer module is loaded before deps resolve.
  **Mitigation**: `httpx` is already a runtime dep; uvx resolves deps before any module import. Validated by Step 9.1 command 3.
- **Risk**: Atomic-rename helper extracted in Step 5.1 is used by Step 4.2 JSON fallback, creating a hidden order-of-operations dependency.
  **Mitigation**: Step 4.2 creates `_atomic_write_json` inline FIRST; Step 5.1 reuses it. Plan order enforces this.
- **Risk**: The Quick Install README URLs reference `v2.0.0` but that tag may not exist yet on GitHub → one-liner 404s.
  **Mitigation**: Phase 0.2 verifies tag resolution; if `v2.0.0` tag isn't pushed, Eden creates it before merging `feat/wizard-installer`, OR we ship pointing at `main` with a Step 10.1 note to retarget on first release.

### Success Criteria

- [ ] `src/installer.py` exists, imports cleanly, and `testrail-mcp-install --help` exits 0 under `uvx --from .`.
- [ ] `pytest --cov=src.installer` reports >= 80% coverage.
- [ ] Dry-run end-to-end invocation (Phase 9.1 command 4) prints planned writes for both clients and modifies no files.
- [ ] `install.sh` passes `sh -n` syntax check; `install.ps1` manually reviewed.
- [ ] `.gitignore` allows `install.sh`, `install.ps1`, `docs/**`, and `tests/**`.
- [ ] Existing `README.md` Quick Start section and JSON config block are byte-for-byte unchanged (ADR D5).
- [ ] `pyproject.toml` exposes both `testrail-mcp` and `testrail-mcp-install` console_scripts.
- [ ] No API key appears in any captured test output (spektr verification).
- [ ] Atomic-rename + pre-parse backup pattern used for every config-file write (ADR D2).
- [ ] `/chekpoint` at FULL tier passes with zero BLOCK findings.
- [ ] Commit body ends with `Reviewed: full` footer.

### Resolutions (locked 2026-04-20 by Eden)

1. **`tests/` in `.gitignore`**: ADR is silent on this. RESOLVED — add `!/tests/**` to `.gitignore` in Step 8.1 (tracked first-class artifacts).
2. **`--dry-run` implies `--no-validate`**: RESOLVED — yes. Dry-run never hits the network. `main()` sets `args.no_validate = True` whenever `args.dry_run` is set. Documented in Step 2.1 docstring.
3. **Default uvx ref**: RESOLVED — `main`, not `v2.0.0`. `git ls-remote --tags origin` confirmed no `v2.0.0` tag exists on `origin`. Bootstrap scripts and README one-liners use `main`. Step 10.1 release-checklist covers flipping the default to the first tagged ref once published. ADR D3 updated in lockstep.
4. **Coverage threshold**: RESOLVED — 80% on `src/installer.py` only. Existing `src/` modules are untouched and out of scope.
