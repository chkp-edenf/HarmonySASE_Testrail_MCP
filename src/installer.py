"""TestRail MCP — Wizard Installer  (src/installer.py)

Entry point: ``testrail-mcp-install`` console_script (Step 8.2 wires pyproject.toml).

Phase 0.1 findings (2026-04-20):
    claude --version  →  "2.1.114 (Claude Code)"
    claude mcp add syntax:
        claude mcp add -s <local|user|project> -e KEY=VAL <name> -- <cmd> [args...]
    Scope flag is ``-s`` / ``--scope``; default scope is "local"; our wizard default is "user".
    Subcommand confirmed present on this build — no minimum-version gate needed for this env.

Resolution #2 (locked by Eden, 2026-04-20):
    ``--dry-run`` implies ``--no-validate``.
    When ``args.dry_run`` is True, ``main()`` sets ``args.no_validate = True`` immediately
    after parsing, before any credential resolution or network call.  Dry-run never hits
    the network and never writes any file.

Resolution #3 (locked by Eden, 2026-04-20):
    Default uvx ref is ``"main"``.  ``git ls-remote --tags origin`` returned empty —
    no ``v2.0.0`` tag exists on origin.  Flip the default in ``install.sh``, ``install.ps1``,
    and this module when the first tag is pushed (see docs/RELEASE_CHECKLIST.md Step 2-3).

Security contract:
    The raw API key is NEVER written to any log line.  All log output referring to the key
    uses the redacted form ``API key received (<N> chars)`` or ``TESTRAIL_API_KEY=***``.
    Enforced by test_api_key_not_logged_raw and the spektr reviewer gate (/chekpoint FULL).
"""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlsplit

if TYPE_CHECKING:
    import httpx

# ---------------------------------------------------------------------------
# Logging — match src/stdio.py:17-22 pattern (stderr, single-line INFO)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level verbose flag — set by main() before detection runs.
# Probe functions read this to decide whether to emit [probe] lines.
# Keeping it module-level avoids threading a new parameter through every
# probe function signature and keeps existing tests stable.
# ---------------------------------------------------------------------------

_VERBOSE: bool = False

# ---------------------------------------------------------------------------
# Repository constant (Step 4.1)
# ---------------------------------------------------------------------------

REPO_URL = "git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git"


def _build_uvx_from(ref: str) -> str:
    """Return 'git+https://.../repo.git@<ref>' — the uvx --from target."""
    return f"{REPO_URL}@{ref}"


# ---------------------------------------------------------------------------
# Presentation helpers (wizard polish)
# ---------------------------------------------------------------------------
# All print/prompt code goes through these so tests can disable color via
# NO_COLOR and non-TTY stderr. The wizard uses stderr (not stdout) for UI
# because stdout is reserved for structured output (e.g., --dry-run planned
# commands) and for clean piping.

_ANSI_RESET = "\033[0m"
_ANSI_BOLD = "\033[1m"
_ANSI_GREEN = "\033[32m"
_ANSI_RED = "\033[31m"
_ANSI_YELLOW = "\033[33m"
_ANSI_CYAN = "\033[36m"
_ANSI_DIM = "\033[2m"


def _use_color() -> bool:
    """True when stderr is a TTY and NO_COLOR is not set.

    Honors the NO_COLOR informal standard (https://no-color.org). Under pytest
    or when piping to a file/log, stderr is not a tty and this returns False.
    """
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stderr.isatty()


def _c(text: str, code: str) -> str:
    """Wrap text in an ANSI color code when color is enabled; no-op otherwise."""
    if not _use_color():
        return text
    return f"{code}{text}{_ANSI_RESET}"


def _ok(text: str) -> str:
    return _c(f"✓ {text}", _ANSI_GREEN)


def _fail(text: str) -> str:
    return _c(f"✗ {text}", _ANSI_RED)


def _warn(text: str) -> str:
    return _c(f"⚠ {text}", _ANSI_YELLOW)


def _step_label(n: int, total: int, label: str) -> str:
    """Return '[n/total] label' with cyan-bold prefix when color is on."""
    prefix = f"[{n}/{total}]"
    if _use_color():
        prefix = f"{_ANSI_CYAN}{_ANSI_BOLD}{prefix}{_ANSI_RESET}"
    return f"{prefix} {label}"


def _emit(line: str = "") -> None:
    """Print a line to stderr (wizard UI channel). Empty arg prints blank line."""
    print(line, file=sys.stderr, flush=True)


def _package_version() -> str:
    """Return the installed package version, or 'dev' if running from source.

    Uses importlib.metadata — lightweight, stdlib, no extra deps.
    """
    try:
        from importlib.metadata import version  # noqa: PLC0415

        return version("harmonysase-testrail-mcp")
    except Exception:  # noqa: BLE001 — never fail startup for a banner
        return "dev"


def _get_uv_version() -> str:
    """Return the uv version string, or 'uv not on PATH' if uv is not found."""
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            timeout=2,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip()
        return "uv not on PATH"
    except Exception:  # noqa: BLE001
        return "uv not on PATH"


def _emit_probe(name: str, *, hit: bool, path: str | None = None) -> None:
    """Emit a single [probe] line to stderr when _VERBOSE is set.

    Format:
        [probe] <name>: hit <path>   (when hit=True and path given)
        [probe] <name>: hit          (when hit=True, no path)
        [probe] <name>: miss         (when hit=False)

    Called from detection functions (_claude_code_details, _claude_desktop_details_*).
    No-op when _VERBOSE is False.
    """
    if not _VERBOSE:
        return
    if hit:
        suffix = f" {path}" if path else ""
        _emit(f"[probe] {name}: hit{suffix}")
    else:
        _emit(f"[probe] {name}: miss")


# ---------------------------------------------------------------------------
# Detection + ping result dataclasses (wizard polish)
# ---------------------------------------------------------------------------


@dataclass
class _ClientDetection:
    """Rich detection result for a single client — used for display only.

    The boolean helpers `_detect_claude_code()` / `_claude_desktop_detected()`
    remain for truth checks and backward compatibility with the 100+ tests
    that monkeypatch them to bool. This dataclass powers the "✓ detected at
    <path> (version X)" display lines via `_claude_code_details()` /
    `_claude_desktop_details()`.

    detected_via: the probe name that succeeded (e.g., "config-dir",
    "install-binary", "running-process", "registry", "path",
    "installer-fallback", "alt-install", "npm-global", "msix-package",
    "desktop-file"). None when not installed or unknown.
    """

    installed: bool
    label: str  # "Claude Code" or "Claude Desktop"
    version: str | None = None  # e.g., "2.1.114" — None when unknown
    path: str | None = None  # CLI path or config-dir path
    detected_via: str | None = None  # which probe found the client

    def __bool__(self) -> bool:
        return self.installed


@dataclass
class _PingOutcome:
    """Structured result from a TestRail credentials ping.

    status:
        "ok"            HTTP 200, credentials accepted
        "unauthorized"  HTTP 401 — retry with a fresh key
        "permission"    HTTP 403 — partial permission, can continue
        "server"        HTTP 404 / 5xx — server-side issue
        "network"       connection refused / DNS error / generic network
        "timeout"       request exceeded the 5 s budget

    project_count: populated on "ok" from len(response.json()).
    hint: human-readable next step for the user; always set on failure.
    retry: True iff main() should re-prompt for the API key and loop.
    http_code: raw HTTP status code when one was returned (diagnostic only).
    """

    status: Literal["ok", "unauthorized", "permission", "server", "network", "timeout"]
    project_count: int | None = None
    hint: str | None = None
    retry: bool = False
    http_code: int | None = None


# ---------------------------------------------------------------------------
# WriteResult dataclass (Step 4.1)
# ---------------------------------------------------------------------------


@dataclass
class WriteResult:
    """Outcome of a single config-write attempt."""

    target: str  # "claude-code-cli", "claude-code-json", "claude-desktop"
    success: bool
    config_path: Path | None  # where the config landed (or would have)
    backup_path: Path | None  # timestamped .bak, if a backup was taken
    message: str  # human summary


# ---------------------------------------------------------------------------
# Step 4.1 — `claude mcp add` subprocess writer
# ---------------------------------------------------------------------------


def _build_claude_cli_command(
    scope: str,
    ref: str,
    url: str,
    username: str,
    api_key: str,
) -> list[str]:
    """Return the exact argument list passed to subprocess.run for claude mcp add.

    Extracted for testability — the API-key value is IN this list; redaction
    happens separately in the logging layer.

    IMPORTANT: the server name `testrail` MUST precede all `-e` flags.
    `claude mcp add` declares `-e` as variadic (`<env...>`). When `-e` flags
    appear before the server name, the parser greedily consumes the server
    name into the last `-e` value list and the CLI rejects it with
    "Invalid environment variable format: testrail". Verified empirically on
    `claude` v2.1.114.
    """
    return [
        "claude",
        "mcp",
        "add",
        "--scope",
        scope,
        "testrail",
        "-e",
        f"TESTRAIL_URL={url}",
        "-e",
        f"TESTRAIL_USERNAME={username}",
        "-e",
        f"TESTRAIL_API_KEY={api_key}",
        "--",
        "uvx",
        "--from",
        _build_uvx_from(ref),
        "testrail-mcp",
    ]


def _redact_command_for_log(cmd: list[str]) -> list[str]:
    """Return a copy of cmd with 'TESTRAIL_API_KEY=<val>' rewritten to 'TESTRAIL_API_KEY=***'."""
    redacted: list[str] = []
    for token in cmd:
        if token.startswith("TESTRAIL_API_KEY="):
            redacted.append("TESTRAIL_API_KEY=***")
        else:
            redacted.append(token)
    return redacted


def _write_claude_code_via_cli(
    scope: str,
    ref: str,
    url: str,
    username: str,
    api_key: str,
    *,
    dry_run: bool,
) -> WriteResult:
    """Primary Claude Code writer: shells out to `claude mcp add`.

    Dry-run: log the (redacted) command, do NOT invoke subprocess.
             Return success=True with a descriptive message.
    Real run: subprocess.run with list args (never shell=True),
              check=False, capture_output=True, timeout=30.
    Non-zero exit: return success=False with stderr snippet (caller triggers fallback).
    Exit 0: return success=True with stdout snippet.
    """
    cmd = _build_claude_cli_command(scope, ref, url, username, api_key)
    redacted = _redact_command_for_log(cmd)

    if dry_run:
        logger.info("DRY-RUN: would run: %s", " ".join(redacted))
        return WriteResult(
            target="claude-code-cli",
            success=True,
            config_path=None,
            backup_path=None,
            message=f"DRY-RUN: would run: {' '.join(redacted)}",
        )

    logger.info("Running: %s", " ".join(redacted))
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        timeout=30,
        text=True,
    )

    if result.returncode != 0:
        snippet = (result.stderr or "").strip()[:200]
        logger.error("claude mcp add exited %d: %s", result.returncode, snippet)
        return WriteResult(
            target="claude-code-cli",
            success=False,
            config_path=None,
            backup_path=None,
            message=snippet or f"claude mcp add exited {result.returncode}",
        )

    snippet = (result.stdout or "").strip()[:200]
    logger.info("claude mcp add succeeded: %s", snippet)
    return WriteResult(
        target="claude-code-cli",
        success=True,
        config_path=None,
        backup_path=None,
        message=snippet or "claude mcp add completed successfully",
    )


# ---------------------------------------------------------------------------
# Step 4.2 — Claude Code JSON fallback + shared atomic-write helper
# ---------------------------------------------------------------------------


def _backup_file(path: Path) -> Path:
    """Copy ``path`` to ``path.parent / f'{path.name}.bak.{int(time.time())}'`` byte-for-byte.

    Returns the backup path.
    Preserves file mode via shutil.copy2.
    Raises FileNotFoundError if path doesn't exist — caller must gate on existence.

    ADR D2: backup precedes parse so malformed JSON is always recoverable.
    """
    if not path.exists():
        raise FileNotFoundError(f"Cannot backup non-existent file: {path}")
    backup_path = path.parent / f"{path.name}.bak.{int(time.time())}"
    shutil.copy2(path, backup_path)
    return backup_path


def _atomic_write_json(path: Path, data: dict[str, Any], *, make_backup: bool) -> Path | None:
    """Atomically write JSON to `path`.

    If make_backup and path exists, copy it to
    `path.with_suffix(path.suffix + f'.bak.{int(time.time())}')` BEFORE any
    parse/modify. Write via temp file in same dir + os.replace for atomicity.
    Preserves file mode via shutil.copymode if backup was taken.

    Returns backup path if one was created, else None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    backup_path: Path | None = None
    if make_backup and path.exists():
        backup_path = path.parent / f"{path.name}.bak.{int(time.time())}"
        shutil.copy2(path, backup_path)

    # Write to a temp file in the same directory, then atomically rename
    fd, tmp_str = tempfile.mkstemp(
        dir=str(path.parent),
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())

        if backup_path is not None:
            shutil.copymode(str(backup_path), tmp_str)

        os.replace(tmp_str, path)
    except Exception:
        import contextlib  # noqa: PLC0415

        with contextlib.suppress(OSError):
            Path(tmp_str).unlink(missing_ok=True)
        raise

    return backup_path


def _claude_code_json_path(scope: str) -> Path:
    """user scope → ~/.claude.json; project scope → ./.mcp.json."""
    if scope == "user":
        return Path.home() / ".claude.json"
    return Path.cwd() / ".mcp.json"


def _build_mcp_entry(ref: str, url: str, username: str, api_key: str) -> dict[str, Any]:
    """Return the canonical mcpServers.testrail entry dict written to both config targets.

    Shape:
      {"command": "uvx",
       "args": ["--from", <uvx_from>, "testrail-mcp"],
       "env": {"TESTRAIL_URL": url, "TESTRAIL_USERNAME": username, "TESTRAIL_API_KEY": api_key}}

    Extracted here so Step 4.2 (JSON fallback) and Step 5.1 (Claude Desktop) share identical
    entry structure without duplication.
    SECURITY CONTRACT: api_key is stored in the JSON value only — never logged here.
    """
    return {
        "command": "uvx",
        "args": ["--from", _build_uvx_from(ref), "testrail-mcp"],
        "env": {
            "TESTRAIL_URL": url,
            "TESTRAIL_USERNAME": username,
            "TESTRAIL_API_KEY": api_key,
        },
    }


def _prompt_existing_entry(assume_yes: bool) -> Literal["replace", "keep", "abort"]:
    """Prompt the user how to handle an existing 'testrail' MCP entry.

    Returns one of:
      "replace"  — overwrite with the new credentials (writer proceeds)
      "keep"     — leave the existing entry untouched, report success
      "abort"    — stop this client, writer returns success=False

    Accepted inputs (case-insensitive):
      r / replace / y / yes  → "replace"  (y/yes are legacy aliases)
      k / keep               → "keep"
      a / abort / n / no     → "abort"    (n/no are legacy aliases)

    Under `assume_yes=True` (CI / --yes mode): returns "replace" silently so
    existing automation keeps working.
    """
    if assume_yes:
        logger.info("Overwriting existing 'testrail' MCP entry (--yes mode).")
        return "replace"
    print("An existing 'testrail' MCP entry was found.")
    print("  [r]eplace  — overwrite with new credentials")
    print("  [k]eep     — leave the existing entry untouched")
    print("  [a]bort    — stop this client (no changes)")
    while True:
        raw = input("Select [r/k/a]: ").strip().lower()
        if raw in ("r", "replace", "y", "yes"):
            return "replace"
        if raw in ("k", "keep"):
            return "keep"
        if raw in ("a", "abort", "n", "no"):
            return "abort"
        logger.warning("Please answer r, k, or a.")


def _write_claude_code_via_json(
    scope: str,
    ref: str,
    url: str,
    username: str,
    api_key: str,
    *,
    dry_run: bool,
    assume_yes: bool,
) -> WriteResult:
    """Direct JSON edit path. Called when CLI unavailable OR after CLI non-zero.

    If `testrail` key already exists in the target's mcpServers:
      - assume_yes=True → overwrite silently (log info).
      - assume_yes=False → prompt y/N; "n" → return success=False with message, DO NOT write.

    Builds the entry via _build_mcp_entry (shared with _write_claude_desktop).
    Uses _atomic_write_json for the write.
    """
    target_path = _claude_code_json_path(scope)

    entry = _build_mcp_entry(ref, url, username, api_key)

    if dry_run:
        logger.info(
            "DRY-RUN: would write mcpServers.testrail to %s (scope=%s, ref=%s)",
            target_path,
            scope,
            ref,
        )
        return WriteResult(
            target="claude-code-json",
            success=True,
            config_path=target_path,
            backup_path=None,
            message=f"DRY-RUN: would write mcpServers.testrail to {target_path}",
        )

    # Load existing data or seed empty
    existing: dict[str, Any] = {}
    if target_path.exists():
        try:
            existing = json.loads(target_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    mcp_servers: dict[str, Any] = existing.get("mcpServers", {})

    # Check for existing testrail entry
    if "testrail" in mcp_servers:
        choice = _prompt_existing_entry(assume_yes)
        if choice == "keep":
            return WriteResult(
                target="claude-code-json",
                success=True,
                config_path=target_path,
                backup_path=None,
                message=f"Kept existing 'testrail' entry in {target_path} (kept per user choice).",
            )
        if choice == "abort":
            return WriteResult(
                target="claude-code-json",
                success=False,
                config_path=target_path,
                backup_path=None,
                message="Aborted: user declined to overwrite existing 'testrail' entry.",
            )
        # choice == "replace" — fall through to overwrite

    mcp_servers["testrail"] = entry
    existing["mcpServers"] = mcp_servers

    make_backup = target_path.exists()
    backup_path = _atomic_write_json(target_path, existing, make_backup=make_backup)
    logger.info("Wrote mcpServers.testrail to %s", target_path)

    return WriteResult(
        target="claude-code-json",
        success=True,
        config_path=target_path,
        backup_path=backup_path,
        message=f"Wrote mcpServers.testrail to {target_path}",
    )


# ---------------------------------------------------------------------------
# Step 5.1 — Claude Desktop atomic merge-write
# ---------------------------------------------------------------------------


def _write_claude_desktop(
    path: Path,
    ref: str,
    url: str,
    username: str,
    api_key: str,
    *,
    dry_run: bool,
    assume_yes: bool,
) -> WriteResult:
    """Write the testrail MCP entry into Claude Desktop's claude_desktop_config.json.

    Algorithm (strictly in this order — tests verify the sequence per ADR D2):

    1. dry_run=True: log planned writes, return success=True, DO NOT touch fs.
    2. If parent dir missing: mkdir -p (real-write path only).
    3. If file exists: _backup_file(path) → record backup_path.
       If file missing: skip backup; data starts as {"mcpServers": {}}.
    4. Try json.loads(text). On JSONDecodeError:
       - assume_yes=True: log warning (backup_path already recorded), overwrite with seed.
       - assume_yes=False: prompt "malformed config (backup at <path>). Overwrite? y/N".
         "n" → return success=False with backup location in message, no further writes.
         "y" → overwrite with seed.
    5. Ensure data is dict with mcpServers dict key.
       If "testrail" already in mcpServers:
         - assume_yes=True: overwrite silently (info log).
         - assume_yes=False: prompt "testrail MCP already configured. Overwrite? y/N".
           "n" → success=False.
           "y" → overwrite.
    6. Update data["mcpServers"]["testrail"] = _build_mcp_entry(...).
    7. _atomic_write_json(path, data, make_backup=False) — already backed up in step 3.

    Security: api_key is NEVER logged — only used inside _build_mcp_entry's return value
    which is written to JSON on disk.
    """
    if dry_run:
        logger.info(
            "DRY-RUN: would write mcpServers.testrail to %s (ref=%s)",
            path,
            ref,
        )
        return WriteResult(
            target="claude-desktop",
            success=True,
            config_path=path,
            backup_path=None,
            message=f"DRY-RUN: would write mcpServers.testrail to {path}",
        )

    # Step 2: mkdir -p parent
    path.parent.mkdir(parents=True, exist_ok=True)

    # Step 3: backup BEFORE parse (ADR D2 invariant)
    backup_path: Path | None = None
    if path.exists():
        backup_path = _backup_file(path)
        text = path.read_text(encoding="utf-8")
    else:
        text = ""  # sentinel — file missing, skip parse

    # Step 4: parse or seed
    data: dict[str, Any]
    if not path.exists() and not text:
        # File was missing — seed
        data = {"mcpServers": {}}
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Malformed — backup already exists; prompt or auto-overwrite
            if assume_yes:
                logger.warning(
                    "Existing config at %s is malformed JSON. "
                    "Overwriting with empty seed (backup at %s).",
                    path,
                    backup_path,
                )
                data = {"mcpServers": {}}
            else:
                raw = (
                    input(
                        f"Existing config is malformed JSON (backup at {backup_path}). "
                        "Overwrite? [y/N]: "
                    )
                    .strip()
                    .lower()
                )
                if raw != "y":
                    return WriteResult(
                        target="claude-desktop",
                        success=False,
                        config_path=path,
                        backup_path=backup_path,
                        message=(
                            f"Aborted: malformed config preserved. Backup is at {backup_path}."
                        ),
                    )
                data = {"mcpServers": {}}

    # Step 5: ensure mcpServers dict; handle existing testrail entry
    if not isinstance(data, dict):
        data = {"mcpServers": {}}
    if not isinstance(data.get("mcpServers"), dict):
        data["mcpServers"] = {}

    mcp_servers: dict[str, Any] = data["mcpServers"]

    if "testrail" in mcp_servers:
        choice = _prompt_existing_entry(assume_yes)
        if choice == "keep":
            return WriteResult(
                target="claude-desktop",
                success=True,
                config_path=path,
                backup_path=backup_path,
                message=f"Kept existing 'testrail' Desktop entry in {path} (kept per user choice).",
            )
        if choice == "abort":
            return WriteResult(
                target="claude-desktop",
                success=False,
                config_path=path,
                backup_path=backup_path,
                message="Aborted: user declined to overwrite existing 'testrail' Desktop entry.",
            )
        # choice == "replace" — fall through to overwrite

    # Step 6: update entry
    mcp_servers["testrail"] = _build_mcp_entry(ref, url, username, api_key)
    data["mcpServers"] = mcp_servers

    # Step 7: atomic write (make_backup=False — we already backed up in step 3)
    _atomic_write_json(path, data, make_backup=False)
    logger.info("Wrote mcpServers.testrail to Claude Desktop config at %s", path)

    return WriteResult(
        target="claude-desktop",
        success=True,
        config_path=path,
        backup_path=backup_path,
        message=f"Wrote mcpServers.testrail to {path}",
    )


# ---------------------------------------------------------------------------
# Step 6.1 — TestRail ping with error classification
# ---------------------------------------------------------------------------


class PingResult(Enum):
    """Classification of a _ping_testrail() call result.

    OK       — 200, credentials valid.
    REPROMPT — 401, wrong credentials; caller should re-prompt the API key.
    WARN     — 403, 5xx, or network/timeout error; caller warns and continues
               (ADR D6: 403 is WARN because Check Point's TestRail sometimes
               gates get_projects per-user; the MCP may still work).
    """

    OK = "ok"
    REPROMPT = "reprompt"
    WARN = "warn"


def _http_get(url: str, *, auth: tuple[str, str], timeout: float) -> httpx.Response:
    """Thin seam around httpx.get — patched in tests via fake_testrail_ping fixture.

    Extracted as a named function so tests can monkeypatch src.installer._http_get
    without patching httpx.get globally. httpx is lazy-imported here (not at module
    top) so `testrail-mcp-install --help` stays snappy for users who never reach the
    network-ping path.
    """
    import httpx  # noqa: PLC0415  — runtime dep already present (pyproject.toml:24)

    return httpx.get(url, auth=auth, timeout=timeout)


def _ping_testrail(url: str, username: str, api_key: str) -> _PingOutcome:
    """GET {url}/index.php?/api/v2/get_projects with Basic auth.

    Returns a `_PingOutcome` with a status label, actionable hint, and — on
    success — the project_count parsed from the JSON array. Security: api_key
    is NEVER logged; only the outcome classification is reported.

    Timeout: 5 seconds (ADR D6). The function never raises.

    Mapping:
        200          -> ok         (retry=False)
        401          -> unauthorized (retry=True — caller re-prompts for key)
        403          -> permission (retry=False — MCP may still work)
        404          -> server     (retry=False — wrong URL or API v2 off)
        5xx          -> server     (retry=False)
        ConnectError -> network    (retry=False)
        TimeoutExc   -> timeout    (retry=False)
        other        -> network    (retry=False)

    See also: PingResult (legacy enum) is retained for the small number of
    tests that imported it directly; production callers use _PingOutcome.
    """
    endpoint = f"{url.rstrip('/')}/index.php?/api/v2/get_projects"

    # Import httpx lazily so --help stays snappy for users who never ping.
    # Only used for exception types; the request itself goes through _http_get.
    try:
        import httpx  # noqa: PLC0415

        connect_error: type[BaseException] = httpx.ConnectError
        timeout_error: type[BaseException] = httpx.TimeoutException
    except ImportError:
        # Shouldn't happen — httpx is a declared runtime dep (pyproject.toml)
        # — but be defensive so a busted install doesn't crash the wizard.
        connect_error = ConnectionError
        timeout_error = TimeoutError

    try:
        response = _http_get(endpoint, auth=(username, api_key), timeout=5)
    except timeout_error as exc:
        logger.info("TestRail ping timed out (%s) — WARN, continuing.", exc)
        return _PingOutcome(
            status="timeout",
            hint=(
                "Connection to TestRail timed out. Your network may be slow, "
                "or the TestRail instance is unreachable. Check VPN/firewall "
                "and try again."
            ),
            retry=False,
        )
    except connect_error as exc:
        logger.info("TestRail ping connect error (%s) — WARN, continuing.", exc)
        return _PingOutcome(
            status="network",
            hint=(
                f"Cannot reach TestRail at {url}. Check the URL spelling, your "
                "network connection, and VPN/proxy settings."
            ),
            retry=False,
        )
    except Exception as exc:  # noqa: BLE001 — defensive
        logger.info(
            "TestRail ping failed with a network error (%s: %s) — WARN, continuing.",
            type(exc).__name__,
            exc,
        )
        return _PingOutcome(
            status="network",
            hint=(
                f"Unexpected network error contacting TestRail ({type(exc).__name__}). "
                "Check network connectivity and retry."
            ),
            retry=False,
        )

    code: int = response.status_code
    if code == 200:
        count: int | None = None
        try:
            body = response.json()
            if isinstance(body, list):
                count = len(body)
            elif isinstance(body, dict):
                # Some TestRail instances paginate projects under a wrapper.
                for key in ("projects", "items", "results"):
                    value = body.get(key)
                    if isinstance(value, list):
                        count = len(value)
                        break
        except Exception:  # noqa: BLE001 — status 200 is enough; count is best-effort
            count = None
        return _PingOutcome(status="ok", project_count=count, http_code=200, retry=False)

    if code == 401:
        return _PingOutcome(
            status="unauthorized",
            http_code=401,
            retry=True,
            hint=(
                "Credentials rejected by TestRail. Double-check your API key — "
                "generate a fresh one under My Settings → API Keys if needed."
            ),
        )

    if code == 403:
        logger.info("TestRail ping returned HTTP 403 — continuing with WARN.")
        return _PingOutcome(
            status="permission",
            http_code=403,
            retry=False,
            hint=(
                "TestRail returned 403 Forbidden. Your account may lack API "
                "access — ask your TestRail admin to enable it."
            ),
        )

    if code == 404:
        logger.info("TestRail ping returned HTTP 404 — continuing with WARN.")
        return _PingOutcome(
            status="server",
            http_code=404,
            retry=False,
            hint=(
                f"TestRail endpoint not found at {url}. Double-check the URL, "
                "and confirm API v2 is enabled on this instance."
            ),
        )

    if 500 <= code < 600:
        logger.info("TestRail ping returned HTTP %d — continuing with WARN.", code)
        return _PingOutcome(
            status="server",
            http_code=code,
            retry=False,
            hint=f"TestRail server error (HTTP {code}). Try again later.",
        )

    logger.info("TestRail ping returned HTTP %d — continuing with WARN.", code)
    return _PingOutcome(
        status="server",
        http_code=code,
        retry=False,
        hint=f"Unexpected HTTP {code} from TestRail. Proceeding; check the URL.",
    )


# ---------------------------------------------------------------------------
# Detection helpers (Phase 3)
# ---------------------------------------------------------------------------

_CLAUDE_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")


def _claude_code_version_probe(bin_path: str) -> _ClientDetection:
    """Run `<bin_path> --version` and return a fully populated _ClientDetection.

    Returns installed=False if the subprocess fails or times out.
    Uses the absolute bin_path as the first arg so non-PATH installs work.
    """
    try:
        result = subprocess.run(
            [bin_path, "--version"],
            capture_output=True,
            timeout=2,
            check=False,
            text=True,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return _ClientDetection(installed=False, label="Claude Code", path=bin_path)
    if result.returncode != 0:
        return _ClientDetection(installed=False, label="Claude Code", path=bin_path)
    match = _CLAUDE_VERSION_RE.search(result.stdout or "")
    version = match.group(1) if match else None
    return _ClientDetection(installed=True, label="Claude Code", version=version, path=bin_path)


def _claude_code_details() -> _ClientDetection:
    """Layered detection for Claude Code CLI — first-hit-wins across all known install locations.

    Probe order (stop at first hit):

    All platforms:
      1. path             : shutil.which("claude") — cheapest, handles the expected case
      2. installer-fallback: ~/.claude/local/claude (macOS/Linux) or
                             %USERPROFILE%\\.claude\\local\\claude.exe (Windows)
      3. alt-install (Unix only): ~/.local/bin/claude
      4. npm-global       : %APPDATA%\\npm\\claude.cmd (Windows, gated on npm present) or
                            $(npm config get prefix)/bin/claude (Unix, gated on npm present)

    Windows-only (probes 5-7):
      5. install-binary   : %LOCALAPPDATA%\\Programs\\Claude\\claude.exe,
                            %ProgramFiles%\\Claude\\claude.exe
      6. running-process  : tasklist /FI "IMAGENAME eq claude.exe" /FO CSV
      7. registry         : winreg.OpenKey(HKCU, "Software\\\\Anthropic\\\\ClaudeCode")

    When a fallback path hits, the absolute path is used for `--version` so the
    version string and install location both appear in the result.
    Every probe is wrapped in try/except — any error is a miss.
    """
    # --- Probe 1: PATH ---
    try:
        path = shutil.which("claude")
        if path is not None:
            det = _claude_code_version_probe(path)
            if det.installed:
                det.detected_via = "path"
                _emit_probe("path", hit=True, path=path)
                return det
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("path", hit=False)

    # --- Probe 2: official installer fallback ---
    try:
        if sys.platform == "win32":
            userprofile = os.environ.get("USERPROFILE", "")
            fallback = Path(userprofile, ".claude", "local", "claude.exe") if userprofile else None
        else:
            fallback = Path.home() / ".claude" / "local" / "claude"
        if fallback is not None and fallback.is_file():
            det = _claude_code_version_probe(str(fallback))
            if det.installed:
                det.detected_via = "installer-fallback"
                _emit_probe("installer-fallback", hit=True, path=str(fallback))
                return det
            # File exists but version probe failed — still report as found
            _emit_probe("installer-fallback", hit=True, path=str(fallback))
            return _ClientDetection(
                installed=True,
                label="Claude Code",
                path=str(fallback),
                detected_via="installer-fallback",
            )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("installer-fallback", hit=False)

    # --- Probe 3: Unix alt install (~/.local/bin/claude) ---
    if sys.platform != "win32":
        try:
            alt = Path.home() / ".local" / "bin" / "claude"
            if alt.is_file():
                det = _claude_code_version_probe(str(alt))
                if det.installed:
                    det.detected_via = "alt-install"
                    _emit_probe("alt-install", hit=True, path=str(alt))
                    return det
                _emit_probe("alt-install", hit=True, path=str(alt))
                return _ClientDetection(
                    installed=True,
                    label="Claude Code",
                    path=str(alt),
                    detected_via="alt-install",
                )
        except Exception:  # noqa: BLE001
            pass
        _emit_probe("alt-install", hit=False)

    # --- Probe 4: npm global ---
    try:
        npm_path = shutil.which("npm")
        if npm_path is not None:
            if sys.platform == "win32":
                appdata = os.environ.get("APPDATA", "")
                npm_cmd = Path(appdata, "npm", "claude.cmd") if appdata else None
                if npm_cmd is not None and npm_cmd.is_file():
                    det = _claude_code_version_probe(str(npm_cmd))
                    if det.installed:
                        det.detected_via = "npm-global"
                        _emit_probe("npm-global", hit=True, path=str(npm_cmd))
                        return det
                    _emit_probe("npm-global", hit=True, path=str(npm_cmd))
                    return _ClientDetection(
                        installed=True,
                        label="Claude Code",
                        path=str(npm_cmd),
                        detected_via="npm-global",
                    )
            else:
                # Unix: ask npm for its prefix
                npm_result = subprocess.run(
                    [npm_path, "config", "get", "prefix"],
                    capture_output=True,
                    timeout=2,
                    check=False,
                    text=True,
                )
                if npm_result.returncode == 0:
                    prefix = (npm_result.stdout or "").strip()
                    npm_claude = Path(prefix, "bin", "claude") if prefix else None
                    if npm_claude is not None and npm_claude.is_file():
                        det = _claude_code_version_probe(str(npm_claude))
                        if det.installed:
                            det.detected_via = "npm-global"
                            _emit_probe("npm-global", hit=True, path=str(npm_claude))
                            return det
                        _emit_probe("npm-global", hit=True, path=str(npm_claude))
                        return _ClientDetection(
                            installed=True,
                            label="Claude Code",
                            path=str(npm_claude),
                            detected_via="npm-global",
                        )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("npm-global", hit=False)

    # --- Windows-only probes ---
    if sys.platform == "win32":
        # Probe 5: install-binary
        localappdata = os.environ.get("LOCALAPPDATA", "")
        programfiles = os.environ.get("PROGRAMFILES", "")
        binary_candidates = [
            Path(localappdata, "Programs", "Claude", "claude.exe") if localappdata else None,
            Path(programfiles, "Claude", "claude.exe") if programfiles else None,
        ]
        for candidate in binary_candidates:
            try:
                if candidate is not None and candidate.is_file():
                    det = _claude_code_version_probe(str(candidate))
                    if det.installed:
                        det.detected_via = "install-binary"
                        _emit_probe("install-binary", hit=True, path=str(candidate))
                        return det
                    _emit_probe("install-binary", hit=True, path=str(candidate))
                    return _ClientDetection(
                        installed=True,
                        label="Claude Code",
                        path=str(candidate),
                        detected_via="install-binary",
                    )
            except Exception:  # noqa: BLE001
                pass
        _emit_probe("install-binary", hit=False)

        # Probe 6: running process (lowercase claude.exe — distinct from Desktop's Claude.exe)
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq claude.exe", "/FO", "CSV"],
                capture_output=True,
                timeout=2,
                check=False,
                text=True,
            )
            if result.returncode == 0 and '"claude.exe"' in (result.stdout or ""):
                _emit_probe("running-process", hit=True)
                return _ClientDetection(
                    installed=True,
                    label="Claude Code",
                    detected_via="running-process",
                )
        except Exception:  # noqa: BLE001
            pass
        _emit_probe("running-process", hit=False)

        # Probe 7: registry
        try:
            import winreg  # noqa: PLC0415

            winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Anthropic\\ClaudeCode")
            _emit_probe("registry", hit=True)
            return _ClientDetection(
                installed=True,
                label="Claude Code",
                detected_via="registry",
            )
        except Exception:  # noqa: BLE001
            pass
        _emit_probe("registry", hit=False)

    return _ClientDetection(installed=False, label="Claude Code")


def _detect_claude_code() -> bool:
    """Return True iff Claude Code CLI is present via any known probe.

    Thin bool wrapper around _claude_code_details() for backward compatibility
    with the 100+ tests that monkeypatch this function to True/False.
    NEVER raises.
    """
    return _claude_code_details().installed


def _claude_desktop_config_path() -> Path | None:
    """Return the expected Claude Desktop config path for this OS.

    Returns the Path even if the file doesn't exist yet — the installer's
    writer (Step 5.1) handles the missing-file case with mkdir -p + seed.
    Returns None only for unsupported platforms.

    ADR D2 path map:
    - darwin : ~/Library/Application Support/Claude/claude_desktop_config.json
    - win32  : $APPDATA/Claude/claude_desktop_config.json
    - linux  : ~/.config/Claude/claude_desktop_config.json
    """
    platform = sys.platform
    if platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    if platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    if platform.startswith("linux"):
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    return None


def _claude_desktop_details() -> _ClientDetection:
    """Layered detection for Claude Desktop — first-hit-wins across all known install locations.

    Probe order (same for each platform, stop at first hit):

    Windows:
      1. config-dir     : %APPDATA%\\Claude\\ OR %LOCALAPPDATA%\\Claude\\ exists
      2. install-binary : %LOCALAPPDATA%\\Programs\\Claude\\Claude.exe,
                          %ProgramFiles%\\Claude\\Claude.exe,
                          %ProgramFiles(x86)%\\Claude\\Claude.exe
      3. msix-package   : glob %LOCALAPPDATA%\\Packages\\*Claude*\\
      4. running-process: tasklist /FI "IMAGENAME eq Claude.exe" /FO CSV
      5. registry       : winreg.OpenKey(HKCU, "Software\\\\Claude")

    macOS:
      1. config-dir    : ~/Library/Application Support/Claude/ exists
      2. install-binary: /Applications/Claude.app exists
      3. running-process: pgrep -f 'Claude.app' returns 0

    Linux:
      1. config-dir    : ~/.config/Claude/ exists
      2. desktop-file  : /usr/share/applications/claude.desktop or
                         ~/.local/share/applications/claude.desktop exists

    Every probe is wrapped in try/except — any error is treated as a miss.
    Returns _ClientDetection(installed=False, label="Claude Desktop") when all probes miss.
    """
    if sys.platform == "win32":
        return _claude_desktop_details_windows()
    if sys.platform == "darwin":
        return _claude_desktop_details_macos()
    if sys.platform.startswith("linux"):
        return _claude_desktop_details_linux()
    return _ClientDetection(installed=False, label="Claude Desktop")


def _claude_desktop_details_windows() -> _ClientDetection:
    """Windows-specific layered Claude Desktop detection."""
    import glob as _glob  # noqa: PLC0415

    # Probe 1: config-dir
    try:
        appdata = os.environ.get("APPDATA", "")
        if appdata and Path(appdata, "Claude").is_dir():
            _emit_probe("config-dir", hit=True, path=str(Path(appdata, "Claude")))
            return _ClientDetection(
                installed=True,
                label="Claude Desktop",
                path=str(Path(appdata, "Claude")),
                detected_via="config-dir",
            )
    except Exception:  # noqa: BLE001
        pass
    try:
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata and Path(localappdata, "Claude").is_dir():
            _emit_probe("config-dir", hit=True, path=str(Path(localappdata, "Claude")))
            return _ClientDetection(
                installed=True,
                label="Claude Desktop",
                path=str(Path(localappdata, "Claude")),
                detected_via="config-dir",
            )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("config-dir", hit=False)

    # Probe 2: install-binary
    localappdata = os.environ.get("LOCALAPPDATA", "")
    programfiles = os.environ.get("PROGRAMFILES", "")
    programfiles_x86 = os.environ.get("PROGRAMFILES(X86)", "")
    binary_candidates = [
        Path(localappdata, "Programs", "Claude", "Claude.exe") if localappdata else None,
        Path(programfiles, "Claude", "Claude.exe") if programfiles else None,
        Path(programfiles_x86, "Claude", "Claude.exe") if programfiles_x86 else None,
    ]
    for candidate in binary_candidates:
        try:
            if candidate is not None and candidate.is_file():
                _emit_probe("install-binary", hit=True, path=str(candidate))
                return _ClientDetection(
                    installed=True,
                    label="Claude Desktop",
                    path=str(candidate),
                    detected_via="install-binary",
                )
        except Exception:  # noqa: BLE001
            pass
    _emit_probe("install-binary", hit=False)

    # Probe 3: MSIX/Store package
    try:
        if localappdata:
            pattern = str(Path(localappdata, "Packages", "*Claude*"))
            matches = _glob.glob(pattern)
            if any(Path(m).is_dir() for m in matches):
                _emit_probe("msix-package", hit=True, path=matches[0])
                return _ClientDetection(
                    installed=True,
                    label="Claude Desktop",
                    path=matches[0],
                    detected_via="msix-package",
                )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("msix-package", hit=False)

    # Probe 4: running process
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Claude.exe", "/FO", "CSV"],
            capture_output=True,
            timeout=2,
            check=False,
            text=True,
        )
        if result.returncode == 0 and '"Claude.exe"' in (result.stdout or ""):
            _emit_probe("running-process", hit=True)
            return _ClientDetection(
                installed=True,
                label="Claude Desktop",
                detected_via="running-process",
            )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("running-process", hit=False)

    # Probe 5: registry (Windows-only import)
    try:
        if sys.platform == "win32":
            import winreg  # noqa: PLC0415

            winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Claude")
            _emit_probe("registry", hit=True)
            return _ClientDetection(
                installed=True,
                label="Claude Desktop",
                detected_via="registry",
            )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("registry", hit=False)

    return _ClientDetection(installed=False, label="Claude Desktop")


def _claude_desktop_details_macos() -> _ClientDetection:
    """macOS-specific layered Claude Desktop detection."""
    # Probe 1: config-dir
    try:
        config_dir = Path.home() / "Library" / "Application Support" / "Claude"
        if config_dir.is_dir():
            _emit_probe("config-dir", hit=True, path=str(config_dir))
            return _ClientDetection(
                installed=True,
                label="Claude Desktop",
                path=str(config_dir),
                detected_via="config-dir",
            )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("config-dir", hit=False)

    # Probe 2: install-binary (.app bundle)
    try:
        app_bundle = Path("/Applications/Claude.app")
        if app_bundle.is_dir():
            _emit_probe("install-binary", hit=True, path=str(app_bundle))
            return _ClientDetection(
                installed=True,
                label="Claude Desktop",
                path=str(app_bundle),
                detected_via="install-binary",
            )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("install-binary", hit=False)

    # Probe 3: running process
    try:
        result = subprocess.run(
            ["pgrep", "-f", "Claude.app"],
            capture_output=True,
            timeout=2,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            _emit_probe("running-process", hit=True)
            return _ClientDetection(
                installed=True,
                label="Claude Desktop",
                detected_via="running-process",
            )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("running-process", hit=False)

    return _ClientDetection(installed=False, label="Claude Desktop")


def _claude_desktop_details_linux() -> _ClientDetection:
    """Linux-specific layered Claude Desktop detection."""
    # Probe 1: config-dir
    try:
        config_dir = Path.home() / ".config" / "Claude"
        if config_dir.is_dir():
            _emit_probe("config-dir", hit=True, path=str(config_dir))
            return _ClientDetection(
                installed=True,
                label="Claude Desktop",
                path=str(config_dir),
                detected_via="config-dir",
            )
    except Exception:  # noqa: BLE001
        pass
    _emit_probe("config-dir", hit=False)

    # Probe 2: desktop-file
    desktop_candidates = [
        Path("/usr/share/applications/claude.desktop"),
        Path.home() / ".local" / "share" / "applications" / "claude.desktop",
    ]
    for candidate in desktop_candidates:
        try:
            if candidate.is_file():
                _emit_probe("desktop-file", hit=True, path=str(candidate))
                return _ClientDetection(
                    installed=True,
                    label="Claude Desktop",
                    path=str(candidate),
                    detected_via="desktop-file",
                )
        except Exception:  # noqa: BLE001
            pass
    _emit_probe("desktop-file", hit=False)

    return _ClientDetection(installed=False, label="Claude Desktop")


def _claude_desktop_detected() -> bool:  # noqa: D401
    """True iff Claude Desktop is detected via any probe on this machine.

    Thin bool wrapper around _claude_desktop_details() for backward compatibility
    with the 100+ tests that monkeypatch this function to True/False.
    Per ADR D5 additive contract: preserved as a bool helper.
    """
    return _claude_desktop_details().installed


# ---------------------------------------------------------------------------
# Client-selection menu (ADR D1 / Phase 3.3)
# ---------------------------------------------------------------------------

# Maps --client flag values to internal short keys
_CLIENT_FLAG_MAP: dict[str, set[str]] = {
    "claude-code": {"code"},
    "claude-desktop": {"desktop"},
    "both": {"code", "desktop"},
}


def _print_detection_summary() -> None:
    """Show the user what the wizard found on their machine — before the menu.

    Only prints the detected/not-detected line for each of the two clients
    (Claude Code, Claude Desktop). Uses the richer `_*_details()` helpers so
    we can surface version/path info. Safe to call unconditionally; all
    output goes to stderr via `_emit`.
    """
    code = _claude_code_details()
    desktop = _claude_desktop_details()

    if code.installed:
        extra = f" v{code.version}" if code.version else ""
        where = f" at {code.path}" if code.path else ""
        _emit(_ok(f"{code.label} detected{extra}{where}"))
    else:
        _emit(_fail(f"{code.label} not detected"))

    if desktop.installed:
        where = f" (config dir: {desktop.path})" if desktop.path else ""
        _emit(_ok(f"{desktop.label} detected{where}"))
    else:
        _emit(_fail(f"{desktop.label} not detected"))


def _choose_clients(args: argparse.Namespace) -> set[str]:
    """Return {'code', 'desktop'}, a subset, or exit 1 with guidance.

    Precedence:
    1. --client flag set  → honour flag, warn if chosen client not detected.
    2. Both detected      → interactive menu [1/2/3].
    3. One detected       → auto-select + info log (no menu).
    4. Neither detected   → exit 1 with guidance.

    Return set uses short keys 'code' and 'desktop' (Step 6.2 dispatch).
    """
    code_detected = _detect_claude_code()
    desktop_detected = _claude_desktop_detected()

    # --- Precedence 1: explicit --client flag ---
    if args.client is not None:
        chosen = _CLIENT_FLAG_MAP[args.client]
        # Warn for each chosen client that is not detected
        if "code" in chosen and not code_detected:
            logger.warning(
                "--client includes 'code' but Claude Code CLI was not detected on PATH. "
                "The config entry will still be written, but Claude Code may not load it."
            )
        if "desktop" in chosen and not desktop_detected:
            logger.warning(
                "--client includes 'desktop' but Claude Desktop was not detected "
                "(parent config directory missing). "
                "The config entry will still be written."
            )
        return chosen

    # --- Precedence 4: neither detected ---
    if not code_detected and not desktop_detected:
        _emit()
        _emit(_fail("No Claude client detected on this machine."))
        _emit()
        _emit("  Pick one before re-running the wizard:")
        _emit()
        _emit(_c("  Claude Code (CLI)", _ANSI_BOLD))
        _emit("    Best for terminal / IDE workflows. Command: `claude` in your shell.")
        _emit("    Install: https://claude.ai/download")
        _emit()
        _emit(_c("  Claude Desktop (GUI)", _ANSI_BOLD))
        _emit("    Best for a visual chat app. No CLI required.")
        _emit("    Install: https://claude.ai/download")
        _emit()
        _emit(
            "  Or, if one is already installed, pass --client claude-code / "
            "--client claude-desktop to override detection."
        )
        _emit()
        # OS-specific guidance for common detection misses
        if sys.platform == "win32":
            _emit(
                "  Windows note: MS Store / Packaged App installs and roaming-profile"
                " configurations are sometimes missed by detection."
            )
            _emit(
                "  Re-run with --client claude-desktop (or --client claude-code) to"
                " bypass detection and write the config anyway."
            )
            _emit("  Run --diagnose for a full probe report you can paste in Slack.")
        elif sys.platform == "darwin":
            _emit(
                "  macOS note: detection looks for /Applications/Claude.app and the"
                " Claude CLI on PATH."
            )
            _emit(
                "  Re-run with --client claude-desktop or --client claude-code to"
                " bypass detection. Run --diagnose for a probe report."
            )
        else:
            # Linux and any other platform
            _emit(
                "  Linux note: detection looks for claude.desktop at"
                " /usr/share/applications/claude.desktop and"
                " ~/.local/share/applications/claude.desktop."
            )
            _emit(
                "  Re-run with --client claude-desktop or --client claude-code to"
                " bypass detection. Run --diagnose for a probe report."
            )
        sys.exit(1)

    # --- Precedence 2 & 3: interactive menu showing only detected clients ---
    # Build the menu entries for each detected client
    entries: list[tuple[str, str, set[str]]] = []  # (key, label, result_set)
    if code_detected:
        entries.append(("1", "Claude Code", {"code"}))
    if desktop_detected:
        entries.append(("2", "Claude Desktop", {"desktop"}))

    # stdout intentional: interactive menu must interleave with input() prompts.
    # Logging would be suppressed at default level and break the UX. Tests capture via capsys.
    print("Which client(s) should the TestRail MCP be configured for?")
    for key, label, _ in entries:
        print(f"  {key}) {label}")
    if code_detected and desktop_detected:
        print("  3) Both")

    valid_choices: dict[str, set[str]] = {k: v for k, _, v in entries}
    if code_detected and desktop_detected:
        valid_choices["3"] = {"code", "desktop"}

    suffix = "/3" if code_detected and desktop_detected else ""
    prompt_range = "/".join(k for k, _, _ in entries) + suffix
    while True:
        raw = input(f"Select [{prompt_range}]: ").strip()
        if raw in valid_choices:
            return valid_choices[raw]
        logger.warning(
            "Invalid selection %r — choose from: %s.", raw, ", ".join(sorted(valid_choices))
        )


def _prompt_scope() -> str:
    """Interactively prompt for Claude Code scope: personal (user) or project.

    Only called when Claude Code is a target AND --scope was not passed AND
    --yes was not passed. Personal -> ~/.claude.json (available in every
    project); Project -> ./.mcp.json (only this directory).

    Prints a short explanation of each option so less-technical teammates
    understand the implication — what files get touched and which
    directories/projects will see the MCP.
    """
    print("\nWhere should the TestRail MCP be configured in Claude Code?")
    print("  1) Personal  — written to ~/.claude.json")
    print("                 Available in every project you open with Claude Code.")
    print("  2) Project   — written to ./.mcp.json in the current directory")
    print("                 Only this project will see the TestRail MCP.")
    while True:
        raw = input("Select [1/2]: ").strip()
        if raw == "1":
            return "user"
        if raw == "2":
            return "project"
        logger.warning("Invalid selection %r — choose 1 or 2.", raw)


def _confirm_write(
    *,
    chosen: set[str],
    scope: str,
    dry_run: bool,
) -> bool:
    """Show what the wizard is about to touch and return True iff user confirms.

    Default [Y/n] is Yes — single Enter = proceed. Suppressed under --yes or
    --dry-run (callers don't invoke this in those modes, but the early-return
    is defensive).
    """
    if dry_run:
        _emit(_c("  (dry-run — no files will be written)", _ANSI_DIM))
        return True
    _emit("About to write:")
    if "code" in chosen:
        if scope == "user":
            _emit("  - Claude Code: `claude mcp add --scope user testrail ...`")
            _emit("                 (fallback: write ~/.claude.json)")
        else:
            _emit("  - Claude Code: `claude mcp add --scope project testrail ...`")
            _emit("                 (fallback: write ./.mcp.json)")
    if "desktop" in chosen:
        desktop_path = _claude_desktop_config_path()
        _emit(f"  - Claude Desktop: {desktop_path} (backup will be saved alongside)")
    while True:
        raw = input("Continue? [Y/n]: ").strip().lower()
        if raw in ("", "y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        logger.warning("Please answer y or n.")


# ---------------------------------------------------------------------------
# Credential helpers (ADR D4)
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_API_KEY_MIN_LEN = 20


def _redact(key: str) -> str:
    """Return a redacted representation — NEVER log the raw key value.

    Format: ``*** (N chars)`` where N is the length of the original key.
    Used in summary log lines only.
    """
    return f"*** ({len(key)} chars)"


_URL_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.[A-Za-z]{2,}(?::\d+)?(?:/.*)?$")

# Hostname must contain at least one dot (rudimentary TLD check).
_HOST_HAS_DOT_RE = re.compile(r"^[A-Za-z0-9._-]+\.[A-Za-z]{2,}")


def _normalize_testrail_url(raw: str) -> tuple[str, list[str]]:
    """Normalize a raw TestRail URL string entered by the user.

    Accepts:
      - ``company.testrail.io``                → https://company.testrail.io
      - ``https://company.testrail.io/``       → https://company.testrail.io
      - ``https://company.testrail.io/index.php?/suites/...`` → base URL + note
      - ``http://company.testrail.io``         → https://... + note

    Raises ``ValueError`` (user-facing message) for:
      - empty / whitespace-only
      - non-http(s) scheme (file://, ftp://, …)
      - no dot in host (notaurl, https://, https://nodot)

    Returns ``(normalized_url, notes)`` where ``notes`` is a (possibly empty)
    list of human-readable strings describing what was changed.
    """
    stripped = raw.strip()
    if not stripped:
        raise ValueError("URL cannot be empty. Enter something like 'company.testrail.io'.")

    notes: list[str] = []

    # If there's no scheme, add https:// so urlsplit parses the host correctly.
    if "://" not in stripped:
        # Bare hostname (or hostname/path) — auto-prefix
        to_parse = f"https://{stripped}"
        auto_prefixed = True
    else:
        to_parse = stripped
        auto_prefixed = False

    parts = urlsplit(to_parse)
    scheme = parts.scheme.lower()

    # Reject unsupported schemes (file://, ftp://, …)
    if scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme {scheme!r}. Use 'https://company.testrail.io'.")

    host = parts.netloc or parts.path  # empty netloc happens for 'https://'
    # Strip port for the dot-check only
    host_no_port = host.split(":")[0]

    if not host_no_port or not _HOST_HAS_DOT_RE.match(host_no_port):
        raise ValueError(
            f"Cannot resolve a hostname with a TLD from {raw!r}. "
            "Try 'company.testrail.io' or 'https://company.testrail.io'."
        )

    # Upgrade http → https
    if not auto_prefixed and scheme == "http":
        notes.append("upgraded http → https")

    # Drop path / query / fragment
    has_path = bool(parts.path and parts.path.rstrip("/"))
    has_query = bool(parts.query)
    has_fragment = bool(parts.fragment)
    if has_path or has_query or has_fragment:
        notes.append("dropped path/query")

    normalized = f"https://{host}"
    return normalized, notes


def _prompt_url() -> str:
    """Interactively prompt for the TestRail URL via _normalize_testrail_url.

    Accepted inputs (all normalized by _normalize_testrail_url):
      https://company.testrail.io           — passes through
      https://company.testrail.io/          — trailing slash stripped
      company.testrail.io                   — auto-prefixed with 'https://'
      http://company.testrail.io            — upgraded to https:// + Normalized notice
      https://company.testrail.io/index.php?/suites/...  — path/query stripped + notice

    Rejected inputs (ValueError from normalizer → re-prompts):
      (empty string / whitespace)           — required
      file://, ftp://, ...                  — unsupported scheme
      notaurl / https:// / https://nodot    — no valid hostname/TLD

    Echoes the resolved URL back to the user on success; emits a 'Normalized:'
    warning when path/query was dropped or http was upgraded.
    """
    prompt_text = "TestRail URL (e.g. company.testrail.io): "
    while True:
        raw = input(prompt_text).strip()
        try:
            resolved, notes = _normalize_testrail_url(raw)
        except ValueError as exc:
            logger.warning("%s", exc)
            continue
        if notes:
            _emit(_warn(f"Normalized: {resolved}  ({'; '.join(notes)})"))
        _emit(_c(f"  Resolved: {resolved}", _ANSI_DIM))
        return resolved


def _prompt_username() -> str:
    """Interactively prompt for a username (non-empty string).

    Warns (does NOT block) if the value doesn't look like an email address
    — TestRail allows non-email usernames in self-hosted deployments (ADR D4).
    """
    while True:
        raw = input("TestRail username (email): ").strip()
        if raw:
            if not _EMAIL_RE.match(raw):
                logger.warning(
                    "Username %r does not look like an email address. "
                    "Proceeding — some self-hosted TestRail instances accept non-email usernames.",
                    raw,
                )
            return raw
        logger.warning("Username cannot be empty. Please try again.")


def _prompt_api_key(*, url: str | None = None) -> str:
    """Prompt via getpass (masked input) until a key of >= 20 chars is entered.

    When `url` is provided, first prints a hint pointing the user at their
    TestRail instance's API-keys settings page (`/index.php?/mysettings`)
    so they don't have to go hunting. Never logs the raw key.

    Re-prompts on short input; user aborts with Ctrl-C.
    """
    if url:
        _emit(
            _c(
                f"  → get yours at {url.rstrip('/')}/index.php?/mysettings",
                _ANSI_DIM,
            )
        )
    while True:
        raw = getpass.getpass("TestRail API key (input hidden): ")
        if len(raw) >= _API_KEY_MIN_LEN:
            return raw
        logger.warning(
            "API key is too short (%d chars). Minimum length is %d. Please try again.",
            len(raw),
            _API_KEY_MIN_LEN,
        )


def _resolve_credentials(
    args: argparse.Namespace,
) -> tuple[str, str, str]:
    """Resolve (url, username, api_key) with precedence: flag > env > prompt.

    Per ADR-001 D4:
    - Flag takes highest precedence (avoids shell-history exposure when possible,
      but user explicitly supplied it so honour it).
    - Env var is second (user exported it in their shell, doesn't land in history).
    - Interactive prompt is the fallback (getpass for api_key; input for url/username).

    Validation:
    - URL: must start with https://; trailing slash stripped; re-prompt on failure.
    - Username: accepts any non-empty string; warns (not blocks) if not email format.
    - API key: minimum 20 chars; re-prompt on failure.

    SECURITY CONTRACT: the raw api_key value is NEVER written to any log line.
    Use _redact(key) for summary output.
    """
    # --- URL ---
    if args.url:
        try:
            url, notes = _normalize_testrail_url(args.url)
        except ValueError as exc:
            logger.warning(
                "Supplied --url %r is not a valid TestRail URL (%s). "
                "Falling through to interactive prompt.",
                args.url,
                exc,
            )
            url = _prompt_url()
        else:
            if notes:
                _emit(_warn(f"Normalized: {url}  ({'; '.join(notes)})"))
    else:
        env_url = os.environ.get("TESTRAIL_URL", "").strip()
        if env_url:
            try:
                url, notes = _normalize_testrail_url(env_url)
            except ValueError as exc:
                logger.warning(
                    "TESTRAIL_URL env var %r is not a valid TestRail URL (%s). "
                    "Falling through to interactive prompt.",
                    env_url,
                    exc,
                )
                url = _prompt_url()
            else:
                if notes:
                    _emit(_warn(f"Normalized: {url}  ({'; '.join(notes)})"))
                logger.info("Using URL from environment")
        else:
            url = _prompt_url()

    # --- Username ---
    if args.username:
        username: str = args.username.strip()
        if not _EMAIL_RE.match(username):
            logger.warning(
                "Username %r does not look like an email address. "
                "Proceeding — some self-hosted TestRail instances accept non-email usernames.",
                username,
            )
    else:
        env_username = os.environ.get("TESTRAIL_USERNAME", "").strip()
        if env_username:
            logger.info("Using USERNAME from environment")
            username = env_username
        else:
            username = _prompt_username()

    # --- API key ---
    if args.api_key:
        api_key: str = args.api_key
        if len(api_key) < _API_KEY_MIN_LEN:
            logger.warning(
                "Supplied --api-key is too short (%d chars, minimum %d). "
                "Falling through to interactive prompt.",
                len(api_key),
                _API_KEY_MIN_LEN,
            )
            api_key = _prompt_api_key(url=url)
    else:
        env_key = os.environ.get("TESTRAIL_API_KEY", "").strip()
        if env_key:
            if len(env_key) < _API_KEY_MIN_LEN:
                logger.warning(
                    "TESTRAIL_API_KEY env var is too short (%d chars, minimum %d). "
                    "Falling through to interactive prompt.",
                    len(env_key),
                    _API_KEY_MIN_LEN,
                )
                api_key = _prompt_api_key(url=url)
            else:
                logger.info("Using API_KEY from environment")
                api_key = env_key
        else:
            api_key = _prompt_api_key(url=url)

    return url, username, api_key


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argparse parser with all 9 installer flags.

    Note: env-var reading for --api-key (TESTRAIL_API_KEY), --url (TESTRAIL_URL),
    and --username (TESTRAIL_USERNAME) is handled in _resolve_credentials() (Step 2.2),
    not here, because argparse does not natively read env vars.
    """
    parser = argparse.ArgumentParser(
        prog="testrail-mcp-install",
        description=(
            "Wizard installer for the TestRail MCP server.\n\n"
            "Detects Claude Code and/or Claude Desktop, prompts for credentials,\n"
            "optionally validates against TestRail, and writes the MCP config entry."
        ),
        epilog=(
            "Examples:\n"
            "  testrail-mcp-install                              # full interactive wizard\n"
            "  testrail-mcp-install --dry-run            # preview, no writes / no network\n"
            "  testrail-mcp-install --yes --client both          # CI / scripted install\n"
            "  testrail-mcp-install --client claude-code --scope project\n"
            "                                                    # add as project-scoped MCP\n"
            "\n"
            "Environment variables (read when the matching flag is omitted):\n"
            "  TESTRAIL_URL, TESTRAIL_USERNAME, TESTRAIL_API_KEY\n"
            "\n"
            "Set NO_COLOR=1 to disable colored output."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--client",
        choices=["claude-code", "claude-desktop", "both"],
        help=(
            "Which MCP client(s) to configure. "
            "If omitted, the wizard detects installed clients interactively."
        ),
    )
    parser.add_argument(
        "--scope",
        choices=["user", "project"],
        default=None,
        help=(
            "Claude Code config scope: 'user' (~/.claude.json) or "
            "'project' (./.mcp.json). If omitted, the wizard prompts interactively "
            "when Claude Code is a target; defaults to 'user' under --yes or for "
            "Claude Desktop-only installs."
        ),
    )
    parser.add_argument(
        "--url",
        help="TestRail instance URL (e.g. https://company.testrail.io). "
        "Also reads TESTRAIL_URL env var (flag takes precedence).",
    )
    parser.add_argument(
        "--username",
        help="TestRail login email. Also reads TESTRAIL_USERNAME env var.",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        help=(
            "TestRail API key. Also reads TESTRAIL_API_KEY env var. "
            "Flag takes precedence over env var; env var takes precedence over interactive prompt. "
            "Never echoed or logged in plain text."
        ),
    )
    parser.add_argument(
        "--no-validate",
        dest="no_validate",
        action="store_true",
        help="Skip the optional TestRail credentials ping. Implied by --dry-run.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Non-interactive mode: answer 'yes' to all confirmation prompts.",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help=(
            "Preview the planned changes without writing any file or calling any API. "
            "Implies --no-validate."
        ),
    )
    parser.add_argument(
        "--ref",
        default="main",
        help=(
            "Git ref (branch, tag, or SHA) to pin in the uvx --from URL. "
            "Default: 'main' (Resolution #3 — no v2.0.0 tag published yet). "
            "Flip to the release tag once one is pushed (see docs/RELEASE_CHECKLIST.md)."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help=(
            "Emit per-probe hit/miss lines during client detection. "
            "Format: [probe] <name>: hit <path> / [probe] <name>: miss. "
            "Compatible with --dry-run and --diagnose."
        ),
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help=(
            "Print a structured diagnostic report (System, Environment, Detection, "
            "UV cache, Network) and exit 0. Skips the normal wizard flow entirely. "
            "API key is always redacted. Compatible with --verbose."
        ),
    )

    return parser


# ---------------------------------------------------------------------------
# _diagnose() — read-only structured report (--diagnose flag)
# ---------------------------------------------------------------------------


def _diagnose() -> None:
    """Print a structured diagnostic report to stderr and exit 0.

    Sections:
    1. System     — OS, Python, package version, uv version
    2. Environment — env vars (api_key redacted via _redact)
    3. Detection  — run _claude_desktop_details() + _claude_code_details() probes
    4. UV cache   — write-test: create + delete a temp file, time the round-trip
    5. Network    — HEAD raw.githubusercontent.com; HEAD TESTRAIL_URL if set

    Exit 0 always (report, not a gate).  Works with --verbose (verbose=True before
    calling _diagnose() means probe emit calls fire inline).
    """
    _emit()
    _emit("=== Diagnose Report ===")
    _emit()

    # ------------------------------------------------------------------
    # Section 1: System
    # ------------------------------------------------------------------
    _emit("--- System ---")
    _emit(f"OS: {platform.platform()}")
    _emit(f"Python: {sys.version.split()[0]}")
    _emit(f"Package version: {_package_version()}")
    _emit(f"uv version: {_get_uv_version()}")
    _emit()

    # ------------------------------------------------------------------
    # Section 2: Environment
    # ------------------------------------------------------------------
    _emit("--- Environment ---")
    for var in ("TESTRAIL_URL", "TESTRAIL_USERNAME", "TESTRAIL_MCP_REF", "UV_CACHE_DIR"):
        val = os.environ.get(var, "(not set)")
        _emit(f"{var}: {val}")

    api_key_raw = os.environ.get("TESTRAIL_API_KEY", "")
    if api_key_raw:
        _emit(f"TESTRAIL_API_KEY: {_redact(api_key_raw)}")
    else:
        _emit("TESTRAIL_API_KEY: (not set)")

    for var in ("APPDATA", "LOCALAPPDATA", "USERPROFILE", "HOME"):
        val = os.environ.get(var, "(not set)")
        _emit(f"{var}: {val}")
        # Windows reparse-point detection for APPDATA and LOCALAPPDATA
        if sys.platform == "win32" and var in ("APPDATA", "LOCALAPPDATA") and val != "(not set)":
            try:
                realpath = os.path.realpath(val)
                if realpath != val:
                    _emit(f"  (redirected to {realpath})")
            except Exception:  # noqa: BLE001
                pass
    _emit()

    # ------------------------------------------------------------------
    # Section 3: Detection
    # ------------------------------------------------------------------
    _emit("--- Detection ---")
    try:
        desktop = _claude_desktop_details()
        _emit(
            f"Claude Desktop: {desktop.installed} "
            f"(via {desktop.detected_via}, path={desktop.path}, version={desktop.version})"
        )
    except Exception as exc:  # noqa: BLE001
        _emit(f"Claude Desktop: ERROR ({exc})")

    try:
        code = _claude_code_details()
        _emit(
            f"Claude Code: {code.installed} "
            f"(via {code.detected_via}, path={code.path}, version={code.version})"
        )
    except Exception as exc:  # noqa: BLE001
        _emit(f"Claude Code: ERROR ({exc})")
    _emit()

    # ------------------------------------------------------------------
    # Section 4: UV cache write-test
    # ------------------------------------------------------------------
    _emit("--- UV cache ---")
    cache_dir = os.environ.get("UV_CACHE_DIR", "")
    if not cache_dir:
        cache_dir = tempfile.gettempdir()
    _emit(f"Cache dir: {cache_dir}")
    try:
        start = time.monotonic()
        fd, tmp_path = tempfile.mkstemp(dir=cache_dir, suffix=".diagnose_tmp")
        os.close(fd)
        Path(tmp_path).unlink(missing_ok=True)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        _emit(f"write-test: OK ({elapsed_ms} ms)")
    except Exception as exc:  # noqa: BLE001
        _emit(f"write-test: FAILED ({exc})")
    _emit()

    # ------------------------------------------------------------------
    # Section 5: Network reachability
    # ------------------------------------------------------------------
    _emit("--- Network ---")

    def _head_probe(label: str, url: str) -> None:
        """Try a HEAD request and emit a reachable/unreachable line."""
        try:
            resp = _http_get(url, auth=("", ""), timeout=3.0)
            _emit(f"{label}: reachable (HTTP {resp.status_code})")
        except Exception as exc:  # noqa: BLE001
            _emit(f"{label}: unreachable ({exc})")

    _head_probe("raw.githubusercontent.com", "https://raw.githubusercontent.com/")

    testrail_url = os.environ.get("TESTRAIL_URL", "").strip()
    if testrail_url:
        try:
            normalized_url, _ = _normalize_testrail_url(testrail_url)
        except ValueError:
            normalized_url = testrail_url
        _head_probe(f"TESTRAIL_URL ({normalized_url})", normalized_url)
    else:
        _emit("TESTRAIL_URL: (not set — skipping reachability probe)")
    _emit()

    _emit("=== End of Diagnose Report ===")
    _emit()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Parse CLI args and run the installer wizard.

    Resolution #2: if args.dry_run is True, args.no_validate is forced True
    immediately after parsing — dry-run never touches the network.

    Flow (Step 6.2):
        1. Parse args
        2. --dry-run → force no_validate=True
        3. _resolve_credentials → (url, username, api_key)
        4. _choose_clients → set of {'code', 'desktop'}
        5. Unless no_validate: _ping_testrail loop (OK→proceed, REPROMPT→re-key, WARN→proceed)
        6. For each chosen client: call writer(s), collect WriteResult
        7. Print installation summary (redacted key, backup paths, ping result)
        8. sys.exit(0 if all success, else 1)

    KeyboardInterrupt exits 130 (POSIX SIGINT convention — ADR D6 Ctrl-C safety).
    """
    try:
        parser = _build_parser()
        args = parser.parse_args(argv)

        # Set module-level verbose flag BEFORE any detection runs.
        # Probe functions read _VERBOSE to decide whether to emit [probe] lines.
        global _VERBOSE  # noqa: PLW0603
        _VERBOSE = bool(getattr(args, "verbose", False))

        # --diagnose short-circuits everything else — no wizard, no writes, no ping.
        if getattr(args, "diagnose", False):
            _diagnose()
            return  # unreachable: _diagnose() calls sys.exit(0)

        # Resolution #2: --dry-run implies --no-validate
        if args.dry_run:
            args.no_validate = True

        # Welcome banner (suppressed under --yes for tidy CI logs)
        if not args.yes:
            version = _package_version()
            _emit(_c("━" * 58, _ANSI_CYAN))
            _emit(_c(f"  TestRail MCP Server — Installer  v{version}", _ANSI_BOLD))
            _emit(_c("━" * 58, _ANSI_CYAN))
            _emit("  Connects Claude Code / Claude Desktop to TestRail.")
            _emit("  ~1 minute.  Ctrl-C to abort (safe — nothing is written")
            _emit("  until you confirm at the end).")
            if args.dry_run:
                _emit(_c("  [DRY-RUN: no files will be written, no network calls]", _ANSI_YELLOW))
            else:
                _emit(_c("  Tip: use --dry-run to preview without writing.", _ANSI_DIM))
            _emit(_c("━" * 58, _ANSI_CYAN))
            _emit()

        # Step 1: Credentials
        if not args.yes:
            _emit(_step_label(1, 5, "Credentials"))
        url, username, api_key = _resolve_credentials(args)

        # Step 2: Client selection
        if not args.yes:
            _emit()
            _emit(_step_label(2, 5, "Client selection"))
            _print_detection_summary()
            _emit()
        chosen_clients = _choose_clients(args)

        # Step 3: Scope resolution (Claude Code only). Prompt interactively
        # when --scope is omitted and Claude Code is a target, unless --yes
        # is set. For Desktop-only installs, scope is unused but we set a
        # value so the summary line doesn't print 'None'.
        if args.scope is None:
            if "code" in chosen_clients and not args.yes:
                _emit()
                _emit(_step_label(3, 5, "Scope"))
                args.scope = _prompt_scope()
            else:
                args.scope = "user"

        # Step 4: optional TestRail ping
        ping_status_label = "skipped (--no-validate)"
        if args.dry_run:
            ping_status_label = "skipped (--dry-run)"
        elif not args.no_validate:
            _emit(_step_label(4, 5, "Validating TestRail credentials"))
            _emit(_c(f"  Connecting to {url}...", _ANSI_DIM))
            # Budget: the initial ping + up to 3 fresh-key re-prompts (4 total
            # pings worst-case). This matches "3 retries with a new key" in UX
            # copy. After the cap, we proceed with WARN so the user can still
            # complete the install and fix credentials later.
            MAX_RETRIES = 3
            attempts = 0
            while True:
                outcome = _ping_testrail(url, username, api_key)
                if outcome.status == "ok":
                    proj_str = (
                        f" — {outcome.project_count} project(s) visible"
                        if outcome.project_count is not None
                        else ""
                    )
                    _emit(_ok(f"Connected to TestRail{proj_str}."))
                    ping_status_label = (
                        f"OK ({outcome.project_count} projects)"
                        if outcome.project_count is not None
                        else "OK"
                    )
                    break
                if outcome.retry:
                    _emit(_warn(outcome.hint or "Credentials rejected."))
                    if attempts >= MAX_RETRIES:
                        _emit(
                            _fail(
                                f"Credentials still rejected after {attempts} retry "
                                f"attempt(s). Continuing so you can finish the install, "
                                f"but verify the API key in TestRail → My Settings → "
                                f"API Keys before using the MCP."
                            )
                        )
                        ping_status_label = f"FAILED (401 after {attempts} retries)"
                        break
                    attempts += 1
                    api_key = _prompt_api_key(url=url)
                    continue
                # Non-retry failure (network, server, permission, timeout)
                _emit(_warn(outcome.hint or f"TestRail ping WARN ({outcome.status})."))
                ping_status_label = f"WARN ({outcome.status})"
                break

        # Step 5: write to each chosen client (with pre-write confirmation)
        if not args.yes:
            _emit()
            _emit(_step_label(5, 5, "Write config"))
            if not _confirm_write(
                chosen=chosen_clients,
                scope=args.scope,
                dry_run=args.dry_run,
            ):
                _emit(_warn("Install cancelled by user. No files written."))
                sys.exit(0)
        results: list[WriteResult] = []
        for client in sorted(chosen_clients):  # sorted for deterministic order
            if client == "code":
                cli_result = _write_claude_code_via_cli(
                    scope=args.scope,
                    ref=args.ref,
                    url=url,
                    username=username,
                    api_key=api_key,
                    dry_run=args.dry_run,
                )
                if not cli_result.success and not args.dry_run:
                    # CLI failed — try JSON fallback
                    cli_result = _write_claude_code_via_json(
                        scope=args.scope,
                        ref=args.ref,
                        url=url,
                        username=username,
                        api_key=api_key,
                        dry_run=args.dry_run,
                        assume_yes=args.yes,
                    )
                results.append(cli_result)

            elif client == "desktop":
                desktop_path = _claude_desktop_config_path()
                if desktop_path is None:
                    logger.error(
                        "Claude Desktop config path could not be determined for this OS. "
                        "Skipping Desktop write."
                    )
                    results.append(
                        WriteResult(
                            target="claude-desktop",
                            success=False,
                            config_path=None,
                            backup_path=None,
                            message="Unsupported OS: could not determine Desktop config path.",
                        )
                    )
                else:
                    desktop_result = _write_claude_desktop(
                        path=desktop_path,
                        ref=args.ref,
                        url=url,
                        username=username,
                        api_key=api_key,
                        dry_run=args.dry_run,
                        assume_yes=args.yes,
                    )
                    results.append(desktop_result)

        # Step 7: print installation summary
        _print_summary(
            results=results,
            clients=chosen_clients,
            scope=args.scope,
            ref=args.ref,
            api_key=api_key,
            ping_status=ping_status_label,
        )

        # Step 8: exit 0 if all succeeded, else 1
        all_ok = all(r.success for r in results)
        sys.exit(0 if all_ok else 1)

    except KeyboardInterrupt:
        logger.info("Installation cancelled by user (Ctrl-C). No files written.")
        sys.exit(130)


_SUMMARY_BOX_WIDTH = 62


def _box_line(text: str) -> str:
    """One row of the summary box.

    ANSI sequences are zero-width in rendering, so we measure width off the
    stripped form. If the visible content exceeds the inner box width we
    truncate with an ellipsis rather than letting the closing `│` fall out
    of alignment on long paths/messages (kody review finding).
    """
    display_text = re.sub(r"\033\[[0-9;]*m", "", text)
    inner_width = _SUMMARY_BOX_WIDTH - 3  # 3 chars of chrome: "│ " + "│"
    if len(display_text) > inner_width:
        # Truncate the raw text conservatively. If the string contains ANSI
        # sequences we still slice on bytes; the closing reset is lost but the
        # visible alignment stays correct (cosmetic tradeoff).
        overflow = len(display_text) - inner_width + 1  # +1 for the ellipsis
        trimmed = text[: max(0, len(text) - overflow)] + "…"
        display_text = re.sub(r"\033\[[0-9;]*m", "", trimmed)
        text = trimmed
    padding = max(0, inner_width - len(display_text))
    return f"│ {text}{' ' * padding}│"


def _print_summary(
    *,
    results: list[WriteResult],
    clients: set[str],
    scope: str,
    ref: str,
    api_key: str,
    ping_status: str,
) -> None:
    """Log a human-readable installation summary to stderr.

    Security: api_key is only shown as _redact(api_key) — NEVER raw.

    Format: box-drawn light Unicode (U+2500 range). Modern terminals on
    macOS, Linux, and Windows (pwsh 7+, Terminal) render these correctly.
    """
    client_labels = ", ".join(sorted(clients)) if clients else "(none)"
    all_ok = all(r.success for r in results) if results else False
    header_tag = (
        _c("✓ Installation Complete", _ANSI_GREEN)
        if all_ok
        else _c("✗ Installation Incomplete", _ANSI_RED)
    )

    top = "┌" + "─" * (_SUMMARY_BOX_WIDTH - 2) + "┐"
    divider = "├" + "─" * (_SUMMARY_BOX_WIDTH - 2) + "┤"
    bottom = "└" + "─" * (_SUMMARY_BOX_WIDTH - 2) + "┘"

    _emit()
    _emit(top)
    _emit(_box_line(header_tag))
    _emit(divider)
    _emit(_box_line(f"  Clients:       {client_labels}"))
    _emit(_box_line(f"  Scope:         {scope}"))
    _emit(_box_line(f"  Source ref:    {ref}"))
    _emit(_box_line(f"  TestRail:      {ping_status}"))
    _emit(_box_line(f"  API key:       {_redact(api_key)}"))
    if results:
        _emit(divider)
        for result in results:
            icon = _ok("OK") if result.success else _fail("FAIL")
            config_str = str(result.config_path) if result.config_path else "(no path)"
            _emit(_box_line(f"  {icon} [{result.target}]  {config_str}"))
            if result.backup_path:
                _emit(_box_line(f"      backup: {result.backup_path}"))
            if result.message:
                _emit(_box_line(f"      {result.message}"))
    _emit(bottom)
    _emit()
    if all_ok and "code" in clients:
        _emit(
            _c("Next: ", _ANSI_BOLD)
            + "run "
            + _c("`claude mcp list`", _ANSI_CYAN)
            + " — you should see "
            + _c("testrail", _ANSI_CYAN)
            + " in the output."
        )
    elif all_ok and "desktop" in clients:
        _emit(
            _c("Next: ", _ANSI_BOLD)
            + "restart Claude Desktop completely (Quit and reopen). "
            + "The `testrail` MCP server should appear in the tools list."
        )
    elif not all_ok:
        _emit(
            _warn(
                "Some writes failed — see messages above. Review the backup "
                "paths to roll back if needed."
            )
        )


# ---------------------------------------------------------------------------
# Console-script entry point (wired in pyproject.toml Step 8.2)
# ---------------------------------------------------------------------------


def run() -> None:
    """Synchronous entry point for uvx / console_scripts."""
    main()


if __name__ == "__main__":
    run()
