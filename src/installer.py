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
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
# Repository constant (Step 4.1)
# ---------------------------------------------------------------------------

REPO_URL = "git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git"


def _build_uvx_from(ref: str) -> str:
    """Return 'git+https://.../repo.git@<ref>' — the uvx --from target."""
    return f"{REPO_URL}@{ref}"


# ---------------------------------------------------------------------------
# WriteResult dataclass (Step 4.1)
# ---------------------------------------------------------------------------

@dataclass
class WriteResult:
    """Outcome of a single config-write attempt."""

    target: str                    # "claude-code-cli", "claude-code-json", "claude-desktop"
    success: bool
    config_path: Path | None       # where the config landed (or would have)
    backup_path: Path | None       # timestamped .bak, if a backup was taken
    message: str                   # human summary


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
        "claude", "mcp", "add",
        "--scope", scope,
        "testrail",
        "-e", f"TESTRAIL_URL={url}",
        "-e", f"TESTRAIL_USERNAME={username}",
        "-e", f"TESTRAIL_API_KEY={api_key}",
        "--",
        "uvx", "--from", _build_uvx_from(ref),
        "testrail-mcp",
    ]


def _redact_command_for_log(cmd: list[str]) -> list[str]:
    """Return a copy of cmd with any 'TESTRAIL_API_KEY=<val>' rewritten to 'TESTRAIL_API_KEY=***'."""
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
        # Clean up temp file on failure
        try:
            Path(tmp_str).unlink(missing_ok=True)
        except OSError:
            pass
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
            target_path, scope, ref,
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
        if assume_yes:
            logger.info("Overwriting existing 'testrail' MCP entry (--yes mode).")
        else:
            raw = input("Overwrite existing 'testrail' MCP entry? [y/N]: ").strip().lower()
            if raw != "y":
                return WriteResult(
                    target="claude-code-json",
                    success=False,
                    config_path=target_path,
                    backup_path=None,
                    message="Aborted: user declined to overwrite existing 'testrail' entry.",
                )

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
            path, ref,
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
                    path, backup_path,
                )
                data = {"mcpServers": {}}
            else:
                raw = input(
                    f"Existing config is malformed JSON (backup at {backup_path}). "
                    "Overwrite? [y/N]: "
                ).strip().lower()
                if raw != "y":
                    return WriteResult(
                        target="claude-desktop",
                        success=False,
                        config_path=path,
                        backup_path=backup_path,
                        message=(
                            f"Aborted: malformed config preserved. "
                            f"Backup is at {backup_path}."
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
        if assume_yes:
            logger.info("Overwriting existing 'testrail' Desktop MCP entry (--yes mode).")
        else:
            raw = input(
                "testrail MCP is already configured in Claude Desktop. Overwrite? [y/N]: "
            ).strip().lower()
            if raw != "y":
                return WriteResult(
                    target="claude-desktop",
                    success=False,
                    config_path=path,
                    backup_path=backup_path,
                    message="Aborted: user declined to overwrite existing 'testrail' Desktop entry.",
                )

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


def _ping_testrail(url: str, username: str, api_key: str) -> PingResult:
    """GET {url}/index.php?/api/v2/get_projects with Basic auth.

    Security: api_key is NEVER logged — only the result classification is reported.
    Timeout: exactly 5 seconds (ADR D6).
    Mapping:
        200 → OK
        401 → REPROMPT
        403 → WARN (partial permission — MCP may still work)
        5xx / other → WARN
        network/timeout error → WARN (warn + continue, ADR D6)
    """
    endpoint = f"{url.rstrip('/')}/index.php?/api/v2/get_projects"
    try:
        response = _http_get(endpoint, auth=(username, api_key), timeout=5)
        status: int = response.status_code
        if status == 200:
            return PingResult.OK
        if status == 401:
            return PingResult.REPROMPT
        # 403, 404, 5xx, any other — warn and continue
        logger.info(
            "TestRail ping returned HTTP %d — treating as WARN and continuing.", status
        )
        return PingResult.WARN
    except Exception as exc:
        logger.info(
            "TestRail ping failed with a network/timeout error (%s: %s) — "
            "treating as WARN and continuing.",
            type(exc).__name__,
            exc,
        )
        return PingResult.WARN


# ---------------------------------------------------------------------------
# Detection helpers (Phase 3)
# ---------------------------------------------------------------------------

def _detect_claude_code() -> bool:
    """Return True iff `claude` CLI is present AND `claude --version` exits 0.

    Detection sequence (ADR D1 steps 1-2):
    1. shutil.which("claude") — if None, return False immediately.
    2. subprocess.run(["claude", "--version"], timeout=2) — return True only when
       returncode == 0.

    Any subprocess.TimeoutExpired or FileNotFoundError returns False.
    NEVER raises.
    """
    if shutil.which("claude") is None:
        return False
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            timeout=2,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


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
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    if platform.startswith("linux"):
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    return None


def _claude_desktop_detected() -> bool:  # noqa: D401
    """True iff the OS-specific Claude Desktop config parent directory exists.

    Per ADR D5 additive contract: detection != file existence.
    The parent directory check confirms that Claude Desktop has been installed
    (it creates the parent dir on first launch); the config file itself may not
    exist until first launch or until we create it in Step 5.1.
    """
    path = _claude_desktop_config_path()
    if path is None:
        return False
    return path.parent.is_dir()


# ---------------------------------------------------------------------------
# Client-selection menu (ADR D1 / Phase 3.3)
# ---------------------------------------------------------------------------

# Maps --client flag values to internal short keys
_CLIENT_FLAG_MAP: dict[str, set[str]] = {
    "claude-code": {"code"},
    "claude-desktop": {"desktop"},
    "both": {"code", "desktop"},
}


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
        logger.error(
            "Neither Claude Code nor Claude Desktop was detected.\n"
            "  • Claude Code: install via https://claude.ai/download (CLI: `claude`)\n"
            "  • Claude Desktop: install via https://claude.ai/download\n"
            "Re-run the installer after installation, or pass --client to override."
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

    prompt_range = "/".join(k for k, _, _ in entries) + ("/3" if code_detected and desktop_detected else "")
    while True:
        raw = input(f"Select [{prompt_range}]: ").strip()
        if raw in valid_choices:
            return valid_choices[raw]
        logger.warning("Invalid selection %r — choose from: %s.", raw, ", ".join(sorted(valid_choices)))


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


def _prompt_url() -> str:
    """Interactively prompt until a valid https:// URL is supplied.

    Strips trailing slash.  Re-prompts indefinitely; user aborts with Ctrl-C.
    """
    while True:
        raw = input("TestRail URL (https://...): ").strip().rstrip("/")
        if raw.startswith("https://"):
            return raw
        logger.warning("URL must start with https://. Got: %r — please try again.", raw)


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


def _prompt_api_key() -> str:
    """Prompt via getpass (masked input) until a key of >= 20 chars is entered.

    Re-prompts on short input; user aborts with Ctrl-C.
    """
    while True:
        raw = getpass.getpass("TestRail API key: ")
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
        url: str = args.url.rstrip("/")
        if not url.startswith("https://"):
            logger.warning(
                "Supplied --url %r does not start with https://. "
                "Falling through to interactive prompt.",
                url,
            )
            url = _prompt_url()
    else:
        env_url = os.environ.get("TESTRAIL_URL", "").strip().rstrip("/")
        if env_url:
            if not env_url.startswith("https://"):
                logger.warning(
                    "TESTRAIL_URL env var %r does not start with https://. "
                    "Falling through to interactive prompt.",
                    env_url,
                )
                url = _prompt_url()
            else:
                logger.info("Using URL from environment")
                url = env_url
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
            api_key = _prompt_api_key()
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
                api_key = _prompt_api_key()
            else:
                logger.info("Using API_KEY from environment")
                api_key = env_key
        else:
            api_key = _prompt_api_key()

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
            "optionally validates against TestRail, and writes the MCP config entry.\n\n"
            "Use --dry-run to preview changes without writing any files.\n"
            "Use --yes for non-interactive / CI mode (all prompts answered 'yes')."
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
        default="user",
        help=(
            "Claude Code config scope: 'user' (~/.claude.json) or "
            "'project' (./.mcp.json). Default: user."
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

    return parser


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

        # Resolution #2: --dry-run implies --no-validate
        if args.dry_run:
            args.no_validate = True

        # Step 3: credential resolution
        url, username, api_key = _resolve_credentials(args)

        # Step 4: client selection
        chosen_clients = _choose_clients(args)

        # Step 5: optional TestRail ping
        ping_status_label = "skipped (--no-validate)"
        if args.dry_run:
            ping_status_label = "skipped (--dry-run)"
        elif not args.no_validate:
            while True:
                ping_result = _ping_testrail(url, username, api_key)
                if ping_result == PingResult.OK:
                    ping_status_label = "OK"
                    break
                if ping_result == PingResult.REPROMPT:
                    logger.warning(
                        "TestRail returned 401 — credentials rejected. "
                        "Please re-enter the API key."
                    )
                    api_key = _prompt_api_key()
                    # loop again with new key
                else:  # WARN
                    ping_status_label = "WARN (network or permission error)"
                    break

        # Step 6: write to each chosen client
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
                    results.append(WriteResult(
                        target="claude-desktop",
                        success=False,
                        config_path=None,
                        backup_path=None,
                        message="Unsupported OS: could not determine Desktop config path.",
                    ))
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
    """
    client_labels = ", ".join(sorted(clients))
    lines = [
        "Installation summary:",
        f"  Clients: {{{client_labels}}}",
        f"  Scope: {scope}",
        f"  Ref: {ref}",
        f"  TestRail ping: {ping_status}",
        f"  API key: {_redact(api_key)}",
        "",
    ]
    for result in results:
        status_icon = "OK" if result.success else "FAILED"
        config_str = str(result.config_path) if result.config_path else "(no path)"
        backup_str = (
            f"(backup: {result.backup_path})" if result.backup_path else "(no backup)"
        )
        lines.append(
            f"  [{result.target}] {status_icon} → {config_str} {backup_str}"
        )

    logger.info("\n".join(lines))


# ---------------------------------------------------------------------------
# Console-script entry point (wired in pyproject.toml Step 8.2)
# ---------------------------------------------------------------------------

def run() -> None:
    """Synchronous entry point for uvx / console_scripts."""
    main()


if __name__ == "__main__":
    run()
