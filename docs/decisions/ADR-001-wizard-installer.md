---
number: 1
title: Wizard installer for TestRail MCP
date: 2026-04-20
status: proposed
route: A
plan: plan-001-wizard-installer.md
---

# ADR-001: Wizard Installer for TestRail MCP

**Deciders**: Eden Fridman (owner), arkitect (design)

## Context

Current install paths for the TestRail MCP server (`pyproject.toml:29` exposes `testrail-mcp = "src.stdio:run"`, invoked via `uvx`):

1. **Manual JSON paste** — user copies the `mcpServers.testrail` block from `README.md:36-50` into `~/.claude.json`, `./.mcp.json`, or `~/Library/Application Support/Claude/claude_desktop_config.json`.
2. **Direct uvx** — `uvx --from git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git testrail-mcp` with env vars set ahead of time.

Both paths require the user to (a) know where their MCP client config lives, (b) hand-edit JSON without clobbering existing MCPs, (c) know the exact `--from` URL, and (d) manage three env vars (`TESTRAIL_URL`, `TESTRAIL_USERNAME`, `TESTRAIL_API_KEY` — validated at `src/stdio.py:35-44`). Enterprise QA users at Check Point hit all four friction points.

The proposed wizard is an **additive, optional** install path: a second console_script (`testrail-mcp-install`) that detects the user's MCP client, prompts for credentials, optionally validates via TestRail's `get_projects` endpoint, and writes the config block. The wizard does not alter any runtime behavior of the server itself.

### Constraints

- **Additive contract (Eden, 2026-04-20)**: The MCP must keep working exactly as today for users who bypass the wizard. No changes to `src/stdio.py` runtime, no new required env vars (the three in `stdio.py:37` remain the only required set), no change to the `testrail-mcp` console_script (`pyproject.toml:29`), no removal of the manual JSON block from `README.md`.
- **Stdlib preference**: Python 3.11+ (`pyproject.toml:11`), `httpx` already a dependency (`pyproject.toml:24`). No new runtime deps for the wizard.
- **Windows + macOS + Linux parity**: Check Point QA runs mixed fleets.
- **`.gitignore` allow-list**: `.gitignore:1-13` denies everything by default and re-allows specific files. Adding `install.sh`, `install.ps1`, and `docs/` requires explicit `!/install.sh`, `!/install.ps1`, `!/docs/**` entries. This is a plan concern but must be flagged.

## Decision

Ship `testrail-mcp-install` as a second console_script in `src/installer.py`, bootstrapped by `install.sh` / `install.ps1` one-liners that install `uv` via astral.sh and then `exec uvx --from git+<repo>@<ref> testrail-mcp-install`. Wizard writes to Claude Code and/or Claude Desktop configs via `claude mcp add` (preferred) with JSON-merge fallback. All decisions below are chosen to honor the additive contract.

---

## Decisions and Alternatives

### D1. `claude mcp add` vs direct JSON edit

**Decision**: Prefer `claude mcp add` for Claude Code targets; fall back to direct JSON edit only when the CLI is unavailable or returns non-zero. Always use direct JSON edit for Claude Desktop (no equivalent CLI).

**Detection logic**:
1. `shutil.which("claude")` — if missing, go straight to JSON fallback.
2. `claude --version` with 2s timeout — capture stdout; if exit != 0, JSON fallback.
3. `claude mcp add --help` exit 0 — confirms the subcommand exists on this version (Claude Code CLI shipped `mcp add` in 2024; older builds lack it).
4. Run: `claude mcp add --scope {user|project} -e TESTRAIL_URL=... -e TESTRAIL_USERNAME=... -e TESTRAIL_API_KEY=... testrail -- uvx --from git+<repo>@<ref> testrail-mcp`.
5. On non-zero exit from step 4 (stderr captured, shown to user), fall back to JSON edit on `~/.claude.json` (user) or `./.mcp.json` (project).

**Why CLI first**: the CLI handles config-path discovery across future Claude Code layout changes (home-dir restructuring, per-profile configs) — writing our own path resolver is a maintenance tax we don't need to pay.

**Alternatives**:
- *Always JSON edit*. Pro: one code path. Con: we carry path-discovery logic that duplicates CLI behavior and breaks silently on Claude Code updates. Rejected.
- *CLI-only, error if missing*. Pro: simplest. Con: breaks the additive contract for users on air-gapped machines or older Claude Code builds. Rejected.

---

### D2. Claude Desktop config merge strategy

**Decision**: Atomic write via temp-file + `os.replace()`, with a timestamped `.bak.<unix_ts>` created **before** the write. On malformed existing JSON, create the backup, prompt `Existing config is not valid JSON. Overwrite with backup preserved? [y/N]`, and abort on N.

**Algorithm** (applied to `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows, `~/.config/Claude/claude_desktop_config.json` on Linux):

1. `mkdir -p` the parent directory (create if Claude Desktop was installed but never launched).
2. If file missing, treat current content as `{"mcpServers": {}}`.
3. `shutil.copy2(config, f"{config}.bak.{int(time.time())}")` — backup first, before any parse.
4. `json.loads(config.read_text())` — on `JSONDecodeError`, prompt (above); on consent, proceed with `{"mcpServers": {}}`.
5. If `mcpServers.testrail` exists, prompt `Overwrite existing 'testrail' MCP entry? [y/N]`. Default N aborts with guidance to edit manually.
6. Write merged JSON to `{config}.tmp.<pid>`, then `os.replace(tmp, config)` (atomic on POSIX; Windows atomic rename when same volume — acceptable per Python docs).
7. Never touch other `mcpServers.*` keys.

**Why atomic rename over in-place write**: a Ctrl-C or power loss during `write_text()` leaves the user's Claude Desktop config corrupt. `os.replace` is the standard POSIX guarantee; on Windows it's atomic when source and target are on the same filesystem, which is always true here (same directory).

**Alternatives**:
- *Read-modify-write in place + `.bak`*. Pro: simplest. Con: non-atomic — partial write on crash destroys config. Rejected: the backup helps recovery, but we can avoid the corruption entirely.
- *File lock (`fcntl.flock` / `msvcrt.locking`)*. Pro: safe under concurrent writers. Con: Claude Desktop is not concurrently writing this file during wizard execution; adds Windows-specific code for a non-problem. Rejected.

---

### D3. uvx source pinning

**Decision**: Default to `@main` until a release tag is pushed. Override via `--ref <branch|tag|sha>` flag. The bootstrap scripts (`install.sh`, `install.ps1`) accept `--ref` and pass through. When the first tag (e.g., `v2.0.1`, `v2.1.0`) is pushed, flip the default in both scripts via the release checklist.

**Resolution 2026-04-20 (Eden)**: `git ls-remote --tags origin` returned empty — no `v2.0.0` tag exists on `origin`. Shipping a tagged default today would 404 the curl/irm one-liners on first use. Default is therefore `main`. Reproducibility trade-off is accepted until tags ship.

**Rationale (original)**: The current `README.md:41` and `mcp_config_example.json:5` pin to `git+https://...` (no ref, resolves to default branch). This is convenient but reproduces the "works on my machine" class of bug — if `main` lands a breaking change between `uvx` invocations, the user's MCP silently updates. A tagged default gives deterministic installs; the override flag preserves velocity for contributors. The resolution above defers this guarantee until the first tag exists.

**Bootstrap plumbing**: `install.sh` and `install.ps1` read `--ref` (default `main`), export as `TESTRAIL_MCP_REF`, and `installer.py` reads the env var when composing the `uvx --from` string written into the MCP config. The installer and the **final MCP config** both carry the resolved ref — users don't have to re-pin manually.

**Alternatives**:
- *`main` branch default*. Pro: users always get latest fixes. Con: non-reproducible; breaks offline re-installs; a hot-fix can break someone mid-sprint. Rejected as default, preserved as `--ref main`.
- *PyPI publish*. Pro: canonical, semver-friendly, no git-clone overhead. Con: not published yet (deferred scope); requires release automation not in place. Rejected for now, revisit in v2.1.

---

### D4. Credential handling

**Decision**: API key precedence (first non-empty wins): `--api-key` flag > `TESTRAIL_API_KEY` env var > `getpass.getpass()` interactive prompt. Username and URL follow the same precedence for `--username`/`TESTRAIL_USERNAME` and `--url`/`TESTRAIL_URL`. Logs never include the API key — stdout/stderr show only `API key received ({len} chars)`.

**Why env var before prompt**: users pasting `export TESTRAIL_API_KEY=...` before running the installer avoid shell-history leakage. A flag like `--api-key xxx` ends up in `.bash_history` / PowerShell history; the env var lives only in the process environment. `getpass` is the interactive fallback (masked input, not echoed).

**Validation**: API key minimum length 20 chars (TestRail keys are typically 40+ hex). Username warning (not block) if it doesn't match a basic email regex — TestRail allows non-email usernames in some self-hosted deployments.

**Logging**: `installer.py` uses stdlib `logging` to stderr (matching `stdio.py:18-22`). Structured single-line messages. **Never log**: the API key, the password field value, or any `-e TESTRAIL_API_KEY=...` string emitted to `claude mcp add` (command logged with the key redacted to `***`).

**Alternatives**:
- *Only `getpass`, no env/flag*. Pro: simplest, safest. Con: blocks `--yes` non-interactive CI use (needed for automated dev-environment setup). Rejected.
- *Only flags*. Pro: scriptable. Con: shell history leak. Rejected.

---

### D5. Additive guarantee — what the installer MUST NOT change

This is the contract with every future contributor. The wizard is a **parallel** install path, not a replacement.

| Must not change | Why | Where enforced |
|---|---|---|
| `src/stdio.py:35-44` — required env var set | Adding a fourth required var breaks direct-uvx users | ADR gate; test `test_stdio_env_validation_unchanged` |
| `pyproject.toml:29` — `testrail-mcp` console_script | Breaks `mcp_config_example.json:5` and every existing user's config | ADR gate; CI smoke test runs `testrail-mcp --help` |
| `README.md` manual JSON block (lines 36-50) | Users who prefer manual install must keep the copy-paste path | Doc gate: the block stays; wizard section is **prepended**, not replacing |
| Env var names (`TESTRAIL_URL`, `TESTRAIL_USERNAME`, `TESTRAIL_API_KEY`) | All downstream tooling reads these | Test `test_env_var_names_stable` |
| Runtime imports in `src/stdio.py` | No `import installer` from stdio — installer is isolated | Grep check in CI |
| Default uvx source URL in `mcp_config_example.json:5` | Users copy-pasting from the example file get the same behavior as before | Doc gate |

**Positive obligation**: the installer **adds** `src/installer.py`, **adds** a second entry under `[project.scripts]`, and **adds** two bootstrap shell scripts. That's it.

---

### D6. Error recovery

**Fatal abort** (exit 1, no partial state):
- `uv` install failure (astral.sh script exit != 0) — print manual URL (`https://docs.astral.sh/uv/getting-started/installation/`) and abort.
- Config file path not writable after `mkdir -p` — print path, abort.
- User declines overwrite on existing `testrail` MCP entry.
- Ctrl-C at any prompt — no backup delete, no config write.

**Warn + continue** (exit 0, record warning in final summary):
- TestRail ping returns 403 (auth OK, but user lacks `get_projects` permission — still a valid key).
- TestRail ping network error (corporate firewall, VPN not connected — the server will retry at runtime).
- `claude mcp add` stderr non-empty but exit 0 (CLI warning, not failure).

**Ctrl-C safety**: All file writes use the atomic rename pattern from D2. All backups are created **before** any write attempt. Interrupting mid-prompt leaves the user's existing configs untouched.

**Alternatives**:
- *Abort on any warning*. Pro: strict. Con: 403 on `get_projects` is a common read-permission limitation in TestRail; aborting there would block legitimate users. Rejected.

---

### D7. Testing strategy

**Unit tests** (`tests/test_installer.py`, `pytest` per global rules):
- Monkey-patch `builtins.input` and `getpass.getpass` via fixtures; drive the wizard as a scripted dialogue.
- Fixture Claude Desktop config files under `tmp_path` (empty, populated-with-other-MCPs, populated-with-testrail, malformed-JSON).
- Assert: no write happened to anything outside `tmp_path`; backup exists; atomic-rename path used; API key not present in captured stderr/stdout.
- `--dry-run` as a **first-class test vector**: every invocation that would write passes first as `--dry-run`, asserts the diff-plan printed to stdout matches expected, asserts no file changed, then re-runs without `--dry-run`.
- `--yes` non-interactive mode: parametrized across all combinations of `--client`, `--scope`, env-var-vs-flag credential sources.

**Integration tests** (skipped in CI without credentials):
- Real `claude mcp add` invocation against a throwaway scope.
- Real TestRail `get_projects` ping using a test-user env var set.

**What is NOT tested** (out of scope):
- The `install.sh` / `install.ps1` astral.sh fetch — that's delegated to astral's installer; we shell out and trust the exit code.
- Claude Code CLI internal behavior — we trust the documented `claude mcp add` contract.

---

### D8. Non-goals (explicit)

- **HTTP transport install**: the roadmap v2.1 AaaS (HTTP) work (per Eden's project roadmap memory) is a separate install story. Wizard is stdio-only.
- **Docker install**: `README.md:20` notes "no Docker required" as a feature. No Docker-compose generation.
- **systemd / launchd unit creation**: MCP servers are spawned by the client, not run as daemons. No unit files.
- **TestRail Enterprise SSO**: TestRail's SSO still issues API keys for programmatic access; no OAuth flow required.
- **Auto-update of existing wizard installs**: no self-update logic. Users re-run the one-liner to upgrade.
- **Multi-instance support**: the wizard writes a single `testrail` MCP entry. Users with multiple TestRail instances hand-edit the second entry (or run the wizard with a different key name — deferred).

---

## Consequences

### Positive
- Sub-2-minute install for new users; removes the four friction points (config path, JSON merging, uvx URL, env vars).
- Atomic writes + backups: losing a user's Claude Desktop config becomes structurally impossible.
- Pinned default ref: reproducible installs, no silent upgrades.
- `--dry-run` + `--yes` + env-var credential source: installer is CI-usable (important for Check Point dev-environment provisioning).
- Additive contract is explicit and testable — no regression risk for existing users.

### Negative
- Two install paths to document and maintain (wizard + manual). README grows.
- Bootstrap scripts (`install.sh`, `install.ps1`) are a minor surface that astral.sh's `uv` installer already covers; we're adding a thin wrapper.
- `src/installer.py` code path is not exercised by the MCP runtime — separate test maintenance burden.
- Pinned-ref default means wizard users don't get `main`-branch fixes until a new tag. Mitigated by `--ref` flag.
- `.gitignore` allow-list currently denies `install.sh`, `install.ps1`, and `docs/` — plan must add `!/install.sh`, `!/install.ps1`, `!/docs/**` or the wizard files won't be committable.

### Risks and Mitigations
- **Risk**: `claude mcp add` CLI flag semantics change in a future Claude Code release. **Mitigation**: probe with `claude mcp add --help` before invocation; fall back to JSON. Pin a minimum Claude Code version in docs after Route B plan verifies current CLI behavior.
- **Risk**: User on Windows has PowerShell execution policy `Restricted`. **Mitigation**: `install.ps1` starts with a documented `Set-ExecutionPolicy -Scope Process Bypass` line, per astral.sh's own installer pattern.
- **Risk**: Claude Desktop config path changes on new macOS versions. **Mitigation**: `installer.py` centralizes the path map; one-line update if Anthropic moves it. Covered by test fixture.
- **Risk**: A user re-runs the wizard and their old backup files pile up. **Mitigation**: log the backup path on each run; leave cleanup manual (don't auto-delete — if something broke we want the trail).
- **Risk**: The `--ref main` default is non-reproducible (resolves to moving HEAD). **Mitigation**: flip the default to the first tagged ref as soon as one is pushed; release checklist (Step 10.1) covers the flip. Short-term risk accepted per Resolution 2026-04-20.

---

## Open Questions

1. **Minimum Claude Code CLI version**: need empirical check — what's the earliest `claude --version` where `claude mcp add --scope user -e KEY=VAL name -- cmd` works as specified? Action: konstruct verifies during plan phase, pins in `installer.py` docstring.
2. **Windows `%APPDATA%` vs `%LOCALAPPDATA%` for Claude Desktop**: the official docs say `%APPDATA%`; confirm on a real Windows install before shipping. Action: manual QA test during plan execution.
3. **Should the wizard offer to run `testrail_metadata` cache-warming on first success?** Nice-to-have, but requires spawning the MCP server out-of-band. Defer to post-MVP.
4. **Telemetry**: should the installer log success/failure counts anywhere? Answer for now: **no**, per `README.md:186` security stance (no persistent storage, no outbound calls beyond TestRail itself).

**Review date**: 2026-10-20 — revisit once v2.1 AaaS work begins and HTTP-transport install story emerges.
