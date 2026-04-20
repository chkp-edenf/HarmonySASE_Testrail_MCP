"""Tests for src/installer.py — wizard installer for TestRail MCP.

TDD RED phase: tests written before implementation exists.
Steps 1.3 (red) + 2.1 (green) per plan-001-wizard-installer.md.
Steps 2.2 (green) + 2.3 (green) per plan-001-wizard-installer.md.
"""
from __future__ import annotations

import pytest


def test_installer_module_imports() -> None:
    """src.installer must be importable (red: ModuleNotFoundError until Step 2.1)."""
    import src.installer  # noqa: F401, PLC0415


def test_installer_main_exits_0_on_dry_run() -> None:
    """main() with --dry-run + --yes must exit 0 without touching any files."""
    import src.installer  # noqa: PLC0415

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main([
            "--dry-run", "--yes",
            "--client", "both",
            "--scope", "user",
            "--url", "https://x.testrail.io",
            "--username", "u@x.com",
            "--api-key", "A" * 40,
            "--no-validate",
        ])
    assert exc_info.value.code == 0


def test_installer_help_text_lists_all_flags(capsys: pytest.CaptureFixture[str]) -> None:
    """--help must mention all 9 CLI flags defined in _build_parser()."""
    import src.installer  # noqa: PLC0415

    with pytest.raises(SystemExit):
        src.installer.main(["--help"])

    captured = capsys.readouterr()
    out = captured.out + captured.err
    for flag in [
        "--client",
        "--scope",
        "--url",
        "--username",
        "--api-key",
        "--no-validate",
        "--yes",
        "--dry-run",
        "--ref",
    ]:
        assert flag in out, f"missing {flag!r} in --help output"


# ---------------------------------------------------------------------------
# Step 2.2 — Credential precedence resolution (7 tests, RED first)
# ---------------------------------------------------------------------------

def test_api_key_flag_beats_env(monkeypatch: pytest.MonkeyPatch, fake_prompts: object) -> None:
    """Flag F*40 beats env E*40 — ADR D4 precedence: flag > env > prompt."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("TESTRAIL_API_KEY", "E" * 40)
    monkeypatch.setenv("TESTRAIL_URL", "https://env.testrail.io")
    monkeypatch.setenv("TESTRAIL_USERNAME", "env@example.com")

    args = src.installer._build_parser().parse_args([
        "--url", "https://x.testrail.io",
        "--username", "u@x.com",
        "--api-key", "F" * 40,
    ])
    _url, _user, key = src.installer._resolve_credentials(args)
    assert key == "F" * 40, "flag must win over env var"


def test_api_key_env_beats_prompt(monkeypatch: pytest.MonkeyPatch, fake_prompts: object) -> None:
    """Env E*40 beats interactive prompt — prompt (getpass) must NOT be called."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("TESTRAIL_API_KEY", "E" * 40)
    monkeypatch.setenv("TESTRAIL_URL", "https://env.testrail.io")
    monkeypatch.setenv("TESTRAIL_USERNAME", "env@example.com")
    # fake_prompts queue is intentionally empty — any call to input/getpass would
    # raise AssertionError from the fixture's assert_exhausted guard.

    args = src.installer._build_parser().parse_args([])
    _url, _user, key = src.installer._resolve_credentials(args)
    assert key == "E" * 40, "env var must win over interactive prompt"


def test_api_key_prompt_when_missing(monkeypatch: pytest.MonkeyPatch, fake_prompts) -> None:
    """No flag, no env → getpass prompt fires; P*40 is consumed and returned."""
    import src.installer  # noqa: PLC0415

    monkeypatch.delenv("TESTRAIL_API_KEY", raising=False)
    monkeypatch.setenv("TESTRAIL_URL", "https://env.testrail.io")
    monkeypatch.setenv("TESTRAIL_USERNAME", "env@example.com")

    fake_prompts.push("P" * 40)

    args = src.installer._build_parser().parse_args([])
    _url, _user, key = src.installer._resolve_credentials(args)
    assert key == "P" * 40


def test_url_reprompt_on_invalid(monkeypatch: pytest.MonkeyPatch, fake_prompts) -> None:
    """Invalid URL (ftp://x) triggers re-prompt; valid https URL accepted with trailing / stripped."""
    import src.installer  # noqa: PLC0415

    monkeypatch.delenv("TESTRAIL_URL", raising=False)
    monkeypatch.setenv("TESTRAIL_USERNAME", "env@example.com")
    monkeypatch.setenv("TESTRAIL_API_KEY", "E" * 40)

    fake_prompts.push("ftp://x")                          # rejected
    fake_prompts.push("https://ok.testrail.io/")          # accepted; trailing / stripped

    args = src.installer._build_parser().parse_args([])
    url, _user, _key = src.installer._resolve_credentials(args)
    assert url == "https://ok.testrail.io", f"expected trailing slash stripped, got {url!r}"


def test_username_warn_not_block_on_non_email(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts: object,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Non-email username logs WARNING but does NOT block resolution."""
    import logging

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("TESTRAIL_URL", "https://env.testrail.io")
    monkeypatch.setenv("TESTRAIL_USERNAME", "admin")
    monkeypatch.setenv("TESTRAIL_API_KEY", "E" * 40)

    args = src.installer._build_parser().parse_args(["--username", "admin"])
    with caplog.at_level(logging.WARNING, logger="src.installer"):
        _url, user, _key = src.installer._resolve_credentials(args)

    assert user == "admin", "non-email username must still be returned"
    assert any(
        "email" in record.message.lower() for record in caplog.records
        if record.levelno >= logging.WARNING
    ), "expected a WARNING mentioning email format"


def test_api_key_short_rejected(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Key shorter than 20 chars triggers a warning + re-prompt; A*40 accepted second try."""
    import logging

    import src.installer  # noqa: PLC0415

    monkeypatch.delenv("TESTRAIL_API_KEY", raising=False)
    monkeypatch.setenv("TESTRAIL_URL", "https://env.testrail.io")
    monkeypatch.setenv("TESTRAIL_USERNAME", "env@example.com")

    fake_prompts.push("short")       # 5 chars — rejected
    fake_prompts.push("A" * 40)      # 40 chars — accepted

    args = src.installer._build_parser().parse_args([])
    with caplog.at_level(logging.WARNING, logger="src.installer"):
        _url, _user, key = src.installer._resolve_credentials(args)

    assert key == "A" * 40
    assert any(
        "20" in record.message or "length" in record.message.lower() or "short" in record.message.lower()
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ), "expected a WARNING about minimum key length"


def test_api_key_never_logged_raw(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts: object,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Raw API key X*40 must never appear in any log output or captured stdout/stderr."""
    import logging

    import src.installer  # noqa: PLC0415

    raw_key = "X" * 40
    monkeypatch.setenv("TESTRAIL_URL", "https://env.testrail.io")
    monkeypatch.setenv("TESTRAIL_USERNAME", "env@example.com")
    monkeypatch.setenv("TESTRAIL_API_KEY", raw_key)

    args = src.installer._build_parser().parse_args([])
    with caplog.at_level(logging.DEBUG, logger="src.installer"):
        src.installer._resolve_credentials(args)

    captured = capsys.readouterr()
    all_output = caplog.text + captured.out + captured.err
    assert raw_key not in all_output, "raw API key must never appear in any log/stdio output"


# ---------------------------------------------------------------------------
# Step 2.3 — Ctrl-C clean-exit handler (1 test, RED first)
# ---------------------------------------------------------------------------

def test_ctrl_c_at_prompt_exits_clean_no_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ctrl-C (KeyboardInterrupt) at first prompt must exit 130 and write no files."""
    import src.installer  # noqa: PLC0415

    # Force HOME into tmp_path so any accidental write would land here
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("TESTRAIL_URL", raising=False)

    def raise_kb(*args: object, **kwargs: object) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", raise_kb)
    monkeypatch.setattr("getpass.getpass", raise_kb)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main([
            "--client", "claude-code",
            "--scope", "user",
            "--no-validate",
        ])

    assert exc_info.value.code == 130, (
        f"expected exit 130 on Ctrl-C, got {exc_info.value.code}"
    )
    # Confirm no config file written anywhere under tmp_path
    assert list(tmp_path.rglob("*.json")) == [], (
        f"expected no JSON files written, found: {list(tmp_path.rglob('*.json'))}"
    )


# ---------------------------------------------------------------------------
# Step 3.1 — Claude Code CLI detection (3 tests, RED first)
# ---------------------------------------------------------------------------

def test_detect_claude_code_present(fake_claude_cli) -> None:
    """_detect_claude_code() returns True when `claude` is on PATH and --version exits 0."""
    import src.installer  # noqa: PLC0415

    # fake_claude_cli defaults: present=True, version_returncode=0
    result = src.installer._detect_claude_code()
    assert result is True, "_detect_claude_code() must return True when CLI is present and --version exits 0"


def test_detect_claude_code_absent(fake_claude_cli) -> None:
    """`_detect_claude_code()` returns False when shutil.which returns None."""
    import src.installer  # noqa: PLC0415

    fake_claude_cli.present = False
    result = src.installer._detect_claude_code()
    assert result is False, "_detect_claude_code() must return False when `claude` is not on PATH"


def test_detect_claude_code_version_fails(fake_claude_cli) -> None:
    """`_detect_claude_code()` returns False when `claude --version` exits non-zero."""
    import src.installer  # noqa: PLC0415

    fake_claude_cli.present = True
    fake_claude_cli.version_returncode = 1
    result = src.installer._detect_claude_code()
    assert result is False, "_detect_claude_code() must return False when --version exits 1"


# ---------------------------------------------------------------------------
# Step 3.2 — Claude Desktop detection (4 tests, RED first)
# ---------------------------------------------------------------------------

def test_detect_claude_desktop_macos_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """On darwin, _claude_desktop_detected() returns True when the parent dir exists.

    _claude_desktop_config_path() must return a path ending in
    'Application Support/Claude/claude_desktop_config.json'.
    """
    import sys  # noqa: PLC0415
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create the parent directory that Claude Desktop would create on install
    parent = tmp_path / "Library" / "Application Support" / "Claude"
    parent.mkdir(parents=True)

    path = src.installer._claude_desktop_config_path()
    assert path is not None
    assert path.name == "claude_desktop_config.json"
    assert "Application Support" in str(path)
    assert "Claude" in str(path)

    assert src.installer._claude_desktop_detected() is True


def test_detect_claude_desktop_windows_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """On win32, path is $APPDATA/Claude/claude_desktop_config.json."""
    import sys  # noqa: PLC0415
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata_dir = tmp_path / "AppData" / "Roaming"
    appdata_dir.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata_dir))

    # Create the parent dir that Claude Desktop would create
    parent = appdata_dir / "Claude"
    parent.mkdir(parents=True)

    path = src.installer._claude_desktop_config_path()
    assert path is not None
    assert path.name == "claude_desktop_config.json"
    assert "Claude" in str(path)

    assert src.installer._claude_desktop_detected() is True


def test_detect_claude_desktop_linux_xdg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """On linux, path is ~/.config/Claude/claude_desktop_config.json."""
    import sys  # noqa: PLC0415
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create the parent dir that Claude Desktop would create
    parent = tmp_path / ".config" / "Claude"
    parent.mkdir(parents=True)

    path = src.installer._claude_desktop_config_path()
    assert path is not None
    assert path.name == "claude_desktop_config.json"
    assert ".config" in str(path)
    assert "Claude" in str(path)

    assert src.installer._claude_desktop_detected() is True


def test_detect_claude_desktop_absent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """On darwin, if parent dir is missing, _claude_desktop_detected() returns False.

    _claude_desktop_config_path() still returns the expected path shape (detection != path shape).
    """
    import sys  # noqa: PLC0415
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Parent dir intentionally NOT created
    path = src.installer._claude_desktop_config_path()
    assert path is not None, "_claude_desktop_config_path() must always return a path on darwin"
    assert path.name == "claude_desktop_config.json"

    assert src.installer._claude_desktop_detected() is False


# ---------------------------------------------------------------------------
# Step 3.3 — Client-selection menu (4 tests, RED first)
# ---------------------------------------------------------------------------

def test_menu_skips_undetected_clients(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts,
) -> None:
    """Menu only shows detected clients; picking an undetected client is not offered.

    Setup: claude-code absent, claude-desktop present.
    Push "2" (desktop) — should succeed immediately.
    """
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr("src.installer._detect_claude_code", lambda: False)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: True)

    args = src.installer._build_parser().parse_args([])  # no --client flag
    fake_prompts.push("2")  # only desktop is option 2; code is not shown

    result = src.installer._choose_clients(args)
    assert result == {"desktop"}, f"expected {{'desktop'}}, got {result!r}"


def test_menu_flag_overrides_menu(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts: object,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """--client flag wins over detection; menu is NOT shown; WARNING logged for undetected client."""
    import logging  # noqa: PLC0415
    import src.installer  # noqa: PLC0415

    # Only desktop is detected; but flag says claude-code
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: False)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: True)

    args = src.installer._build_parser().parse_args(["--client", "claude-code"])

    with caplog.at_level(logging.WARNING, logger="src.installer"):
        result = src.installer._choose_clients(args)

    assert result == {"code"}, f"expected {{'code'}}, got {result!r}"
    # fake_prompts queue must remain empty (no prompt consumed)
    # Warning must mention the undetected client
    assert any(
        "code" in record.message.lower() or "claude code" in record.message.lower()
        or "not detected" in record.message.lower() or "detected" in record.message.lower()
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ), "expected a WARNING about undetected client"


def test_menu_both_selected(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts,
) -> None:
    """Both detected; user picks '3' (Both) -> returns {'code', 'desktop'}."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: True)

    args = src.installer._build_parser().parse_args([])
    fake_prompts.push("3")

    result = src.installer._choose_clients(args)
    assert result == {"code", "desktop"}, f"expected {{'code', 'desktop'}}, got {result!r}"


def test_menu_neither_detected_exits(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts: object,
) -> None:
    """Neither client detected and no --client flag -> exit 1 with guidance."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr("src.installer._detect_claude_code", lambda: False)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    args = src.installer._build_parser().parse_args([])

    with pytest.raises(SystemExit) as exc_info:
        src.installer._choose_clients(args)

    assert exc_info.value.code == 1, (
        f"expected exit 1 when neither client detected, got {exc_info.value.code}"
    )


# ---------------------------------------------------------------------------
# Step 4.1 — `claude mcp add` subprocess writer (6 tests, RED first)
# ---------------------------------------------------------------------------

def test_claude_cli_writer_invokes_with_correct_args(fake_claude_cli) -> None:
    """_write_claude_code_via_cli invokes subprocess with exact expected arg list."""
    import src.installer  # noqa: PLC0415

    key = "K" * 40
    result = src.installer._write_claude_code_via_cli(
        scope="user",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key=key,
        dry_run=False,
    )

    assert result.success is True
    # Exactly one call recorded
    assert len(fake_claude_cli.calls) == 1
    captured = fake_claude_cli.calls[0]
    # NOTE: server name `testrail` MUST precede all `-e` flags — see
    # _build_claude_cli_command docstring. `-e` is variadic in claude mcp add.
    expected = [
        "claude", "mcp", "add",
        "--scope", "user",
        "testrail",
        "-e", "TESTRAIL_URL=https://x.testrail.io",
        "-e", "TESTRAIL_USERNAME=u@x.com",
        "-e", f"TESTRAIL_API_KEY={key}",
        "--",
        "uvx", "--from",
        "git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git@main",
        "testrail-mcp",
    ]
    assert captured == expected, f"captured args mismatch:\n  got:      {captured}\n  expected: {expected}"


def test_claude_cli_writer_redacts_api_key_in_logs(
    fake_claude_cli,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log output must contain TESTRAIL_API_KEY=*** and NOT the raw key value."""
    import logging
    import src.installer  # noqa: PLC0415

    key = "K" * 40
    with caplog.at_level(logging.DEBUG, logger="src.installer"):
        src.installer._write_claude_code_via_cli(
            scope="user",
            ref="main",
            url="https://x.testrail.io",
            username="u@x.com",
            api_key=key,
            dry_run=False,
        )

    assert key not in caplog.text, "raw API key must never appear in logs"
    assert "TESTRAIL_API_KEY=***" in caplog.text, "redacted key form must appear in logs"


def test_claude_cli_writer_respects_scope_project(fake_claude_cli) -> None:
    """scope='project' appears as '--scope project' in the subprocess args."""
    import src.installer  # noqa: PLC0415

    src.installer._write_claude_code_via_cli(
        scope="project",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
    )

    assert len(fake_claude_cli.calls) == 1
    args = fake_claude_cli.calls[0]
    assert "--scope" in args
    idx = args.index("--scope")
    assert args[idx + 1] == "project"


def test_claude_cli_writer_respects_ref_override(fake_claude_cli) -> None:
    """ref='feat/wizard-installer' appears in the uvx --from URL."""
    import src.installer  # noqa: PLC0415

    ref = "feat/wizard-installer"
    src.installer._write_claude_code_via_cli(
        scope="user",
        ref=ref,
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
    )

    assert len(fake_claude_cli.calls) == 1
    args_str = " ".join(fake_claude_cli.calls[0])
    expected_fragment = f"git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git@{ref}"
    assert expected_fragment in args_str, (
        f"expected fragment {expected_fragment!r} not found in args: {fake_claude_cli.calls[0]}"
    )


def test_claude_cli_writer_dry_run_no_subprocess(fake_claude_cli) -> None:
    """dry_run=True must not invoke subprocess; result.success is True."""
    import src.installer  # noqa: PLC0415

    result = src.installer._write_claude_code_via_cli(
        scope="user",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=True,
    )

    # No subprocess invocation
    mcp_add_calls = [c for c in fake_claude_cli.calls if len(c) >= 3 and c[:3] == ["claude", "mcp", "add"]]
    assert len(mcp_add_calls) == 0, "dry_run=True must not invoke claude mcp add"
    assert result.success is True
    assert "would run" in result.message.lower() or "dry" in result.message.lower()


def test_claude_cli_writer_nonzero_exit_reports_failure(fake_claude_cli) -> None:
    """Non-zero exit from claude mcp add → result.success=False with stderr snippet."""
    import src.installer  # noqa: PLC0415

    fake_claude_cli.mcp_add_returncode = 1
    fake_claude_cli.mcp_add_stderr = "permission denied: cannot write config"

    result = src.installer._write_claude_code_via_cli(
        scope="user",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
    )

    assert result.success is False
    assert "permission denied" in result.message or "cannot write config" in result.message


# ---------------------------------------------------------------------------
# Step 4.2 — Claude Code JSON fallback (8 tests, RED first)
# ---------------------------------------------------------------------------

def test_json_fallback_user_scope_writes_home_claude_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """user scope → ~/.claude.json (with HOME patched to tmp_path)."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))

    result = src.installer._write_claude_code_via_json(
        scope="user",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=True,
    )

    assert result.success is True
    config_path = tmp_path / ".claude.json"
    assert config_path.exists(), "~/.claude.json must be created for user scope"
    import json
    data = json.loads(config_path.read_text())
    assert "mcpServers" in data
    assert "testrail" in data["mcpServers"]
    assert data["mcpServers"]["testrail"]["env"]["TESTRAIL_URL"] == "https://x.testrail.io"


def test_json_fallback_project_scope_writes_local_mcp_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """project scope → ./.mcp.json in cwd."""
    import src.installer  # noqa: PLC0415

    monkeypatch.chdir(tmp_path)

    result = src.installer._write_claude_code_via_json(
        scope="project",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=True,
    )

    assert result.success is True
    config_path = tmp_path / ".mcp.json"
    assert config_path.exists(), ".mcp.json must be created for project scope"
    import json
    data = json.loads(config_path.read_text())
    assert data["mcpServers"]["testrail"]["env"]["TESTRAIL_URL"] == "https://x.testrail.io"


def test_json_fallback_preserves_other_mcpservers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Existing mcpServers.other must survive after testrail is added."""
    import json
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    config_path = tmp_path / ".claude.json"
    config_path.write_text(json.dumps({"mcpServers": {"other": {"command": "echo", "args": ["x"]}}}))

    src.installer._write_claude_code_via_json(
        scope="user",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=True,
    )

    data = json.loads(config_path.read_text())
    assert "other" in data["mcpServers"], "other MCP entry must be preserved"
    assert "testrail" in data["mcpServers"], "testrail must be added"


def test_json_fallback_preserves_top_level_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Top-level keys other than mcpServers (e.g. experimentalFeatures) must survive."""
    import json
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    config_path = tmp_path / ".claude.json"
    config_path.write_text(json.dumps({"experimentalFeatures": True, "mcpServers": {}}))

    src.installer._write_claude_code_via_json(
        scope="user",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=True,
    )

    data = json.loads(config_path.read_text())
    assert data.get("experimentalFeatures") is True, "top-level keys must be preserved"
    assert "testrail" in data["mcpServers"]


def test_json_fallback_prompts_on_existing_testrail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fake_prompts,
) -> None:
    """Existing testrail entry + assume_yes=False → prompt; 'n' aborts, 'y' overwrites."""
    import json
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    config_path = tmp_path / ".claude.json"
    original_entry = {"command": "old-cmd", "args": [], "env": {"TESTRAIL_URL": "https://old.io"}}
    config_path.write_text(json.dumps({"mcpServers": {"testrail": original_entry}}))
    original_bytes = config_path.read_bytes()

    # --- 'n' branch: must abort, file unchanged ---
    fake_prompts.push("n")
    result_no = src.installer._write_claude_code_via_json(
        scope="user",
        ref="main",
        url="https://new.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=False,
    )
    assert result_no.success is False
    assert config_path.read_bytes() == original_bytes, "file must be unchanged when user answers 'n'"

    # --- 'y' branch: must overwrite ---
    fake_prompts.push("y")
    result_yes = src.installer._write_claude_code_via_json(
        scope="user",
        ref="main",
        url="https://new.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=False,
    )
    assert result_yes.success is True
    data = json.loads(config_path.read_text())
    assert data["mcpServers"]["testrail"]["env"]["TESTRAIL_URL"] == "https://new.testrail.io"


def test_json_fallback_atomic_rename_used(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """os.replace must be called exactly once with the final config path as target."""
    import os
    from unittest.mock import MagicMock
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))

    real_replace = os.replace
    mock_replace = MagicMock(side_effect=real_replace)
    monkeypatch.setattr(os, "replace", mock_replace)

    src.installer._write_claude_code_via_json(
        scope="user",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=True,
    )

    assert mock_replace.call_count == 1
    # Second arg of os.replace is the final destination
    final_dest = mock_replace.call_args[0][1]
    assert str(final_dest) == str(tmp_path / ".claude.json")


def test_json_fallback_backup_created_when_file_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """When the target file exists, a .bak.<ts> backup must be created alongside it."""
    import json
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    config_path = tmp_path / ".claude.json"
    original_content = json.dumps({"mcpServers": {}})
    config_path.write_text(original_content)
    original_bytes = config_path.read_bytes()

    result = src.installer._write_claude_code_via_json(
        scope="user",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=True,
    )

    assert result.backup_path is not None
    assert result.backup_path.exists(), "backup file must exist on disk"
    assert result.backup_path.read_bytes() == original_bytes, "backup must be byte-for-byte copy of original"


def test_json_fallback_api_key_not_in_logs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Raw API key must never appear in any log or captured output during JSON write."""
    import logging
    import src.installer  # noqa: PLC0415

    key = "Z" * 40
    monkeypatch.setenv("HOME", str(tmp_path))

    with caplog.at_level(logging.DEBUG, logger="src.installer"):
        src.installer._write_claude_code_via_json(
            scope="user",
            ref="main",
            url="https://x.testrail.io",
            username="u@x.com",
            api_key=key,
            dry_run=False,
            assume_yes=True,
        )

    captured = capsys.readouterr()
    all_output = caplog.text + captured.out + captured.err
    assert key not in all_output, "raw API key must never appear in logs or stdio"


def test_json_fallback_dry_run_no_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """dry_run=True must not write any file; result.success=True with descriptive message."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    config_path = tmp_path / ".claude.json"
    # File does not exist yet

    result = src.installer._write_claude_code_via_json(
        scope="user",
        ref="main",
        url="https://x.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=True,
        assume_yes=True,
    )

    assert result.success is True
    assert not config_path.exists(), "dry_run=True must not create any file"
    assert result.message, "result.message must be non-empty"


# ---------------------------------------------------------------------------
# Step 5.1 — _write_claude_desktop (9 tests, RED first)
#
# The `fake_claude_desktop_config` fixture is parametrized over
# ["missing", "empty", "preserves_other", "malformed"].
# Tests that use it run 4 times (once per param).
#
# Tests that need a SPECIFIC param use their own manual setup inside tmp_path
# (or only call the parametrized fixture for one of its shapes).
# ---------------------------------------------------------------------------

_EXPECTED_KEY = "A" * 40
_EXPECTED_URL = "https://x.testrail.io"
_EXPECTED_USERNAME = "u@x.com"
_EXPECTED_REF = "main"


def _expected_entry(ref: str = _EXPECTED_REF) -> dict:
    """Return the canonical mcpServers.testrail entry shape written by _write_claude_desktop."""
    import src.installer  # noqa: PLC0415
    uvx_from = src.installer._build_uvx_from(ref)
    return {
        "command": "uvx",
        "args": ["--from", uvx_from, "testrail-mcp"],
        "env": {
            "TESTRAIL_URL": _EXPECTED_URL,
            "TESTRAIL_USERNAME": _EXPECTED_USERNAME,
            "TESTRAIL_API_KEY": _EXPECTED_KEY,
        },
    }


# ------------------------------------------------------------------
# Test 1 — missing file: parent created, seed written, no backup
# ------------------------------------------------------------------

def test_desktop_missing_file_creates_parent_and_writes_seed(
    tmp_path,
) -> None:
    """When file doesn't exist (and parent is absent), mkdir -p + write seed.

    No backup must be created (nothing to back up).
    """
    import json
    import src.installer  # noqa: PLC0415

    # The config lives in a sub-directory that does NOT exist yet
    config_path = tmp_path / "Claude" / "claude_desktop_config.json"
    # Confirm parent is absent
    assert not config_path.parent.exists(), "parent dir must be absent before call"

    result = src.installer._write_claude_desktop(
        path=config_path,
        ref=_EXPECTED_REF,
        url=_EXPECTED_URL,
        username=_EXPECTED_USERNAME,
        api_key=_EXPECTED_KEY,
        dry_run=False,
        assume_yes=True,
    )

    assert result.success is True
    assert config_path.parent.exists(), "parent directory must be created by the writer"
    assert config_path.exists(), "config file must be created"
    data = json.loads(config_path.read_text())
    assert data == {"mcpServers": {"testrail": _expected_entry()}}, (
        f"unexpected file content: {data}"
    )
    # No backup — file didn't exist before
    assert result.backup_path is None, "no backup expected when file did not exist"
    bak_files = list(config_path.parent.glob("*.bak.*"))
    assert bak_files == [], f"unexpected backup files: {bak_files}"


# ------------------------------------------------------------------
# Test 2 — empty mcpServers: testrail added, backup created
# ------------------------------------------------------------------

def test_desktop_empty_mcpservers_merged(tmp_path) -> None:
    """Pre-seeded {'mcpServers':{}} → testrail added; backup file exists."""
    import json
    import src.installer  # noqa: PLC0415

    config_path = tmp_path / "claude_desktop_config.json"
    config_path.write_text(json.dumps({"mcpServers": {}}))

    result = src.installer._write_claude_desktop(
        path=config_path,
        ref=_EXPECTED_REF,
        url=_EXPECTED_URL,
        username=_EXPECTED_USERNAME,
        api_key=_EXPECTED_KEY,
        dry_run=False,
        assume_yes=True,
    )

    assert result.success is True
    data = json.loads(config_path.read_text())
    assert data == {"mcpServers": {"testrail": _expected_entry()}}
    # Backup must exist (file existed before the call)
    assert result.backup_path is not None
    assert result.backup_path.exists(), "backup file must exist on disk"


# ------------------------------------------------------------------
# Test 3 — preserves other MCPs
# ------------------------------------------------------------------

def test_desktop_preserves_other_mcps(tmp_path) -> None:
    """Existing mcpServers.other entry must survive; testrail added alongside."""
    import json
    import src.installer  # noqa: PLC0415

    other_entry = {"command": "echo", "args": ["x"]}
    config_path = tmp_path / "claude_desktop_config.json"
    config_path.write_text(json.dumps({"mcpServers": {"other": other_entry}}))

    result = src.installer._write_claude_desktop(
        path=config_path,
        ref=_EXPECTED_REF,
        url=_EXPECTED_URL,
        username=_EXPECTED_USERNAME,
        api_key=_EXPECTED_KEY,
        dry_run=False,
        assume_yes=True,
    )

    assert result.success is True
    data = json.loads(config_path.read_text())
    assert data["mcpServers"]["other"] == other_entry, "other MCP entry must be untouched"
    assert data["mcpServers"]["testrail"] == _expected_entry(), "testrail must be added"


# ------------------------------------------------------------------
# Test 4 — existing testrail: prompt 'n' aborts, 'y' overwrites
# ------------------------------------------------------------------

def test_desktop_existing_testrail_prompts_overwrite(
    tmp_path,
    fake_prompts,
) -> None:
    """Existing mcpServers.testrail + assume_yes=False → prompt; 'n' aborts, 'y' overwrites."""
    import json
    import src.installer  # noqa: PLC0415

    old_entry = {"command": "OLD", "args": []}
    config_path = tmp_path / "claude_desktop_config.json"
    config_path.write_text(json.dumps({"mcpServers": {"testrail": old_entry}}))
    original_bytes = config_path.read_bytes()

    # --- 'n' branch: must abort, file unchanged ---
    fake_prompts.push("n")
    result_no = src.installer._write_claude_desktop(
        path=config_path,
        ref=_EXPECTED_REF,
        url=_EXPECTED_URL,
        username=_EXPECTED_USERNAME,
        api_key=_EXPECTED_KEY,
        dry_run=False,
        assume_yes=False,
    )
    assert result_no.success is False
    assert config_path.read_bytes() == original_bytes, "file must be unchanged when user answers 'n'"

    # --- 'y' branch: must overwrite with new entry ---
    fake_prompts.push("y")
    result_yes = src.installer._write_claude_desktop(
        path=config_path,
        ref=_EXPECTED_REF,
        url=_EXPECTED_URL,
        username=_EXPECTED_USERNAME,
        api_key=_EXPECTED_KEY,
        dry_run=False,
        assume_yes=False,
    )
    assert result_yes.success is True
    data = json.loads(config_path.read_text())
    assert data["mcpServers"]["testrail"]["env"]["TESTRAIL_URL"] == _EXPECTED_URL


# ------------------------------------------------------------------
# Test 5 — malformed JSON: backup first, prompt; 'n' leaves file intact
# ------------------------------------------------------------------

def test_desktop_malformed_json_prompts_consent(
    tmp_path,
    fake_prompts,
) -> None:
    """Malformed JSON → backup created (before parse), then prompt.

    'n' → success=False, backup exists with original bytes, no seed written.
    'y' → seed written.
    """
    import src.installer  # noqa: PLC0415

    config_path = tmp_path / "claude_desktop_config.json"
    bad_content = b"not-json-at-all"
    config_path.write_bytes(bad_content)

    # --- 'n' branch ---
    fake_prompts.push("n")
    result_no = src.installer._write_claude_desktop(
        path=config_path,
        ref=_EXPECTED_REF,
        url=_EXPECTED_URL,
        username=_EXPECTED_USERNAME,
        api_key=_EXPECTED_KEY,
        dry_run=False,
        assume_yes=False,
    )
    assert result_no.success is False
    # Original file must be byte-for-byte intact
    assert config_path.read_bytes() == bad_content, "original malformed bytes must be intact after 'n'"
    # Backup must exist with the original content
    assert result_no.backup_path is not None
    assert result_no.backup_path.exists(), "backup file must exist even when user answers 'n'"
    assert result_no.backup_path.read_bytes() == bad_content, "backup must contain original bytes"

    # --- 'y' branch: overwrite with seed ---
    # The backup from the first call already exists; the second call creates a new one.
    fake_prompts.push("y")
    result_yes = src.installer._write_claude_desktop(
        path=config_path,
        ref=_EXPECTED_REF,
        url=_EXPECTED_URL,
        username=_EXPECTED_USERNAME,
        api_key=_EXPECTED_KEY,
        dry_run=False,
        assume_yes=False,
    )
    assert result_yes.success is True
    import json
    data = json.loads(config_path.read_text())
    assert "mcpServers" in data, "seed written after 'y' must have mcpServers key"
    assert "testrail" in data["mcpServers"]


# ------------------------------------------------------------------
# Test 6 — backup created BEFORE parse (sequence invariant)
# ------------------------------------------------------------------

def test_desktop_backup_created_before_parse(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backup file must exist on disk AT THE MOMENT json.loads is called.

    This verifies the ADR D2 sequence: backup → parse (not parse → backup).
    We inject a spy on json.loads that records whether a *.bak.* file exists
    at the moment it is called, then raises JSONDecodeError to exit early.
    """
    import json
    import src.installer  # noqa: PLC0415

    config_path = tmp_path / "claude_desktop_config.json"
    config_path.write_text("not-json-at-all")

    backup_existed_at_parse_time: list[bool] = []
    real_loads = json.loads

    def spy_loads(text: str, **kwargs: object) -> object:
        # Check whether any *.bak.* file exists in the parent dir RIGHT NOW
        bak_files = list(config_path.parent.glob(f"{config_path.name}.bak.*"))
        backup_existed_at_parse_time.append(len(bak_files) > 0)
        raise json.JSONDecodeError("simulated", text, 0)

    monkeypatch.setattr(json, "loads", spy_loads)

    # assume_yes=True: malformed JSON is handled gracefully (no re-raise).
    # We only care that the backup existed when json.loads was called —
    # the function may succeed or raise; either outcome is acceptable here.
    try:
        src.installer._write_claude_desktop(
            path=config_path,
            ref=_EXPECTED_REF,
            url=_EXPECTED_URL,
            username=_EXPECTED_USERNAME,
            api_key=_EXPECTED_KEY,
            dry_run=False,
            assume_yes=True,
        )
    except (SystemExit, OSError):
        pass  # either outcome is fine; we only care about backup timing

    assert backup_existed_at_parse_time, "json.loads spy was never called"
    assert backup_existed_at_parse_time[0] is True, (
        "backup must exist on disk BEFORE json.loads is called (ADR D2 sequence)"
    )


# ------------------------------------------------------------------
# Test 7 — atomic rename: original file preserved on crash
# ------------------------------------------------------------------

def test_desktop_atomic_rename_preserves_on_crash(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If os.replace raises OSError (simulated crash), original file must be unchanged."""
    import os
    import json
    import src.installer  # noqa: PLC0415

    original_data = {"mcpServers": {"existing": {"command": "old", "args": []}}}
    config_path = tmp_path / "claude_desktop_config.json"
    config_path.write_text(json.dumps(original_data))
    pre_write_bytes = config_path.read_bytes()

    real_replace = os.replace
    call_count = [0]

    def crashing_replace(src: str, dst: str) -> None:
        call_count[0] += 1
        raise OSError("simulated crash")

    monkeypatch.setattr(os, "replace", crashing_replace)

    try:
        src.installer._write_claude_desktop(
            path=config_path,
            ref=_EXPECTED_REF,
            url=_EXPECTED_URL,
            username=_EXPECTED_USERNAME,
            api_key=_EXPECTED_KEY,
            dry_run=False,
            assume_yes=True,
        )
    except OSError:
        pass  # expected — the crash propagates

    # Original file must be byte-for-byte unchanged
    assert config_path.read_bytes() == pre_write_bytes, (
        "original config must be byte-for-byte intact after simulated os.replace crash"
    )
    # Backup must exist (created before the crash)
    bak_files = list(config_path.parent.glob(f"{config_path.name}.bak.*"))
    assert len(bak_files) >= 1, "backup must exist even after crash"


# ------------------------------------------------------------------
# Test 8 — API key must not appear in logs (security)
# ------------------------------------------------------------------

def test_desktop_api_key_not_in_logs(
    tmp_path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Raw API key (Y*40) must never appear in any log or captured stdio output."""
    import logging
    import json
    import src.installer  # noqa: PLC0415

    key = "Y" * 40
    config_path = tmp_path / "claude_desktop_config.json"
    config_path.write_text(json.dumps({"mcpServers": {}}))

    with caplog.at_level(logging.DEBUG, logger="src.installer"):
        src.installer._write_claude_desktop(
            path=config_path,
            ref=_EXPECTED_REF,
            url=_EXPECTED_URL,
            username=_EXPECTED_USERNAME,
            api_key=key,
            dry_run=False,
            assume_yes=True,
        )

    captured = capsys.readouterr()
    all_output = caplog.text + captured.out + captured.err
    assert key not in all_output, "raw API key must never appear in any log or stdio output"


# ------------------------------------------------------------------
# Test 9 — dry-run: no writes, no backup
# ------------------------------------------------------------------

def test_desktop_dry_run_no_writes(tmp_path) -> None:
    """dry_run=True must not write any file or create any backup."""
    import src.installer  # noqa: PLC0415

    config_path = tmp_path / "subdir" / "claude_desktop_config.json"
    # Parent dir does NOT exist — dry-run must not create it

    result = src.installer._write_claude_desktop(
        path=config_path,
        ref=_EXPECTED_REF,
        url=_EXPECTED_URL,
        username=_EXPECTED_USERNAME,
        api_key=_EXPECTED_KEY,
        dry_run=True,
        assume_yes=True,
    )

    assert result.success is True
    assert not config_path.parent.exists(), "dry_run=True must not create parent directory"
    assert not config_path.exists(), "dry_run=True must not create config file"
    assert result.backup_path is None, "dry_run=True must not create any backup"


# ---------------------------------------------------------------------------
# Step 6.1 — _ping_testrail with error classification (9 tests, RED first)
# ---------------------------------------------------------------------------
# NOTE: fake_testrail_ping fixture extended in conftest.py from a stub to a
# configurable helper that supports push(status_code=...) and push(exception=...).
# Tests in this section use the updated fixture API.
# ---------------------------------------------------------------------------

def test_ping_200_returns_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 200 → _ping_testrail returns PingResult.OK."""
    import src.installer  # noqa: PLC0415

    mock_response = type("R", (), {"status_code": 200})()
    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: mock_response)

    result = src.installer._ping_testrail(
        "https://x.testrail.io", "u@x.com", "K" * 40
    )
    assert result == src.installer.PingResult.OK


def test_ping_401_returns_reprompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 401 → _ping_testrail returns PingResult.REPROMPT."""
    import src.installer  # noqa: PLC0415

    mock_response = type("R", (), {"status_code": 401})()
    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: mock_response)

    result = src.installer._ping_testrail(
        "https://x.testrail.io", "u@x.com", "K" * 40
    )
    assert result == src.installer.PingResult.REPROMPT


def test_ping_403_returns_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 403 → _ping_testrail returns PingResult.WARN (ADR D6: auth ok, lacking get_projects)."""
    import src.installer  # noqa: PLC0415

    mock_response = type("R", (), {"status_code": 403})()
    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: mock_response)

    result = src.installer._ping_testrail(
        "https://x.testrail.io", "u@x.com", "K" * 40
    )
    assert result == src.installer.PingResult.WARN


def test_ping_network_error_returns_warn(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """httpx.ConnectError → PingResult.WARN + an INFO log (no stack trace)."""
    import logging
    import httpx
    import src.installer  # noqa: PLC0415

    def raise_connect(*a: object, **kw: object) -> None:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("src.installer._http_get", raise_connect)

    with caplog.at_level(logging.INFO, logger="src.installer"):
        result = src.installer._ping_testrail(
            "https://x.testrail.io", "u@x.com", "K" * 40
        )

    assert result == src.installer.PingResult.WARN
    assert any(
        "network" in r.message.lower() or "connect" in r.message.lower()
        or "error" in r.message.lower() or "warn" in r.message.lower()
        for r in caplog.records
    ), "expected an INFO/WARNING log about the network failure"


def test_ping_timeout_returns_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    """httpx.TimeoutException → PingResult.WARN."""
    import httpx
    import src.installer  # noqa: PLC0415

    def raise_timeout(*a: object, **kw: object) -> None:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("src.installer._http_get", raise_timeout)

    result = src.installer._ping_testrail(
        "https://x.testrail.io", "u@x.com", "K" * 40
    )
    assert result == src.installer.PingResult.WARN


def test_ping_uses_5s_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """_ping_testrail must call _http_get with timeout=5 (ADR D6 — 5-second timeout)."""
    import src.installer  # noqa: PLC0415

    captured_kwargs: list[dict] = []

    def spy_http_get(url: str, **kwargs: object) -> object:
        captured_kwargs.append(kwargs)
        return type("R", (), {"status_code": 200})()

    monkeypatch.setattr("src.installer._http_get", spy_http_get)

    src.installer._ping_testrail("https://x.testrail.io", "u@x.com", "K" * 40)

    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["timeout"] == 5, (
        f"expected timeout=5, got {captured_kwargs[0].get('timeout')!r}"
    )


def test_ping_uses_basic_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """_ping_testrail must call _http_get with auth=(username, api_key)."""
    import src.installer  # noqa: PLC0415

    captured_kwargs: list[dict] = []
    username = "u@x.com"
    api_key = "K" * 40

    def spy_http_get(url: str, **kwargs: object) -> object:
        captured_kwargs.append(kwargs)
        return type("R", (), {"status_code": 200})()

    monkeypatch.setattr("src.installer._http_get", spy_http_get)

    src.installer._ping_testrail("https://x.testrail.io", username, api_key)

    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["auth"] == (username, api_key), (
        f"expected auth={(username, api_key)!r}, got {captured_kwargs[0].get('auth')!r}"
    )


def test_ping_endpoint_url_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Endpoint must be {url.rstrip('/')}/index.php?/api/v2/get_projects.

    Test with a trailing-slash input URL to verify no double-slash.
    """
    import src.installer  # noqa: PLC0415

    captured_urls: list[str] = []

    def spy_http_get(url: str, **kwargs: object) -> object:
        captured_urls.append(url)
        return type("R", (), {"status_code": 200})()

    monkeypatch.setattr("src.installer._http_get", spy_http_get)

    src.installer._ping_testrail("https://x.testrail.io/", "u@x.com", "K" * 40)

    assert len(captured_urls) == 1
    assert captured_urls[0] == "https://x.testrail.io/index.php?/api/v2/get_projects", (
        f"unexpected endpoint URL: {captured_urls[0]!r}"
    )
    assert "//" not in captured_urls[0].split("://")[1], "double-slash must not appear in path"


def test_ping_never_logs_api_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The raw API key must never appear in any log or captured output during ping."""
    import logging
    import src.installer  # noqa: PLC0415

    api_key = "Q" * 40
    mock_response = type("R", (), {"status_code": 200})()
    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: mock_response)

    with caplog.at_level(logging.DEBUG, logger="src.installer"):
        src.installer._ping_testrail("https://x.testrail.io", "u@x.com", api_key)

    captured = capsys.readouterr()
    all_output = caplog.text + captured.out + captured.err
    assert api_key not in all_output, "raw API key must never appear in any log or stdio output"


# ---------------------------------------------------------------------------
# Step 6.2 — Wire ping + writers into main() (7 tests + 1 smoke, RED first)
# ---------------------------------------------------------------------------

def test_main_dry_run_implies_no_validate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With --dry-run, _ping_testrail must NOT be called (Resolution #2)."""
    import src.installer  # noqa: PLC0415
    from unittest.mock import MagicMock

    mock_ping = MagicMock()
    monkeypatch.setattr("src.installer._ping_testrail", mock_ping)
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main([
            "--dry-run", "--yes",
            "--client", "claude-code",
            "--scope", "user",
            "--url", "https://x.testrail.io",
            "--username", "u@x.com",
            "--api-key", "A" * 40,
        ])

    assert exc_info.value.code == 0
    assert mock_ping.call_count == 0, (
        f"_ping_testrail must NOT be called with --dry-run; called {mock_ping.call_count} time(s)"
    )


def test_main_both_clients_dry_run_prints_plan_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--dry-run --yes --client both --scope user: summary printed, no files created."""
    import logging
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: True)
    desktop_path = tmp_path / "desktop_config.json"
    monkeypatch.setattr("src.installer._claude_desktop_config_path", lambda: desktop_path)

    with caplog.at_level(logging.INFO, logger="src.installer"):
        with pytest.raises(SystemExit) as exc_info:
            src.installer.main([
                "--dry-run", "--yes",
                "--client", "both",
                "--scope", "user",
                "--url", "https://x.testrail.io",
                "--username", "u@x.com",
                "--api-key", "A" * 40,
            ])

    assert exc_info.value.code == 0

    # No actual files must have been created
    assert not (tmp_path / ".claude.json").exists(), "~/.claude.json must not be created in dry-run"
    assert not desktop_path.exists(), "desktop config must not be created in dry-run"
    assert not (tmp_path / ".mcp.json").exists(), ".mcp.json must not be created in dry-run"

    # Summary must appear in logs or capsys
    captured = capsys.readouterr()
    all_output = caplog.text + captured.out + captured.err
    assert "summary" in all_output.lower() or "dry" in all_output.lower(), (
        "expected summary or dry-run indication in output"
    )


def test_main_final_summary_printed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Successful real run prints an Installation summary containing all expected fields."""
    import logging
    import src.installer  # noqa: PLC0415
    from unittest.mock import MagicMock
    from pathlib import Path

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    # Mock CLI writer to return success without touching real claude CLI
    mock_cli = MagicMock(return_value=src.installer.WriteResult(
        target="claude-code-cli",
        success=True,
        config_path=None,
        backup_path=None,
        message="mocked success",
    ))
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)

    api_key = "F" * 40
    with caplog.at_level(logging.INFO, logger="src.installer"):
        with pytest.raises(SystemExit) as exc_info:
            src.installer.main([
                "--no-validate", "--yes",
                "--client", "claude-code",
                "--scope", "user",
                "--url", "https://x.testrail.io",
                "--username", "u@x.com",
                "--api-key", api_key,
            ])

    assert exc_info.value.code == 0

    # Summary must appear in logs
    all_log = caplog.text
    assert "summary" in all_log.lower(), "expected 'summary' in log output"
    # API key must NOT appear raw
    assert api_key not in all_log, "raw API key must not appear in summary"
    # Redacted form or length indicator must be there
    assert "***" in all_log or "chars" in all_log, (
        "expected redacted key representation in summary"
    )


def test_main_happy_path_writes_both_clients(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """--no-validate --yes --client both: both writers called; exit 0."""
    import src.installer  # noqa: PLC0415
    from unittest.mock import MagicMock
    from pathlib import Path

    monkeypatch.setenv("HOME", str(tmp_path))
    desktop_path = tmp_path / "desktop_config.json"
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_config_path", lambda: desktop_path)

    mock_cli = MagicMock(return_value=src.installer.WriteResult(
        target="claude-code-cli", success=True,
        config_path=None, backup_path=None, message="ok",
    ))
    mock_desktop = MagicMock(return_value=src.installer.WriteResult(
        target="claude-desktop", success=True,
        config_path=desktop_path, backup_path=None, message="ok",
    ))
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)
    monkeypatch.setattr("src.installer._write_claude_desktop", mock_desktop)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main([
            "--no-validate", "--yes",
            "--client", "both",
            "--scope", "user",
            "--url", "https://x.testrail.io",
            "--username", "u@x.com",
            "--api-key", "A" * 40,
        ])

    assert exc_info.value.code == 0
    assert mock_cli.call_count == 1, "CLI writer must be called exactly once"
    assert mock_desktop.call_count == 1, "Desktop writer must be called exactly once"


def test_main_cli_failure_falls_back_to_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """If _write_claude_code_via_cli returns success=False, JSON fallback is called."""
    import src.installer  # noqa: PLC0415
    from unittest.mock import MagicMock

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    mock_cli = MagicMock(return_value=src.installer.WriteResult(
        target="claude-code-cli", success=False,
        config_path=None, backup_path=None, message="cli failed",
    ))
    mock_json = MagicMock(return_value=src.installer.WriteResult(
        target="claude-code-json", success=True,
        config_path=tmp_path / ".claude.json", backup_path=None, message="json ok",
    ))
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)
    monkeypatch.setattr("src.installer._write_claude_code_via_json", mock_json)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main([
            "--no-validate", "--yes",
            "--client", "claude-code",
            "--scope", "user",
            "--url", "https://x.testrail.io",
            "--username", "u@x.com",
            "--api-key", "A" * 40,
        ])

    assert exc_info.value.code == 0
    assert mock_cli.call_count == 1, "CLI writer must be attempted once"
    assert mock_json.call_count == 1, "JSON fallback must be called after CLI failure"


def test_main_ping_reprompt_loop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fake_prompts,
) -> None:
    """ping → REPROMPT once, then OK: _prompt_api_key called once between the two pings."""
    import src.installer  # noqa: PLC0415
    from unittest.mock import MagicMock

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    new_key = "B" * 40
    ping_call_count = [0]

    def ping_side_effect(url: str, username: str, api_key: str) -> src.installer.PingResult:
        ping_call_count[0] += 1
        if ping_call_count[0] == 1:
            return src.installer.PingResult.REPROMPT
        return src.installer.PingResult.OK

    monkeypatch.setattr("src.installer._ping_testrail", ping_side_effect)

    mock_cli = MagicMock(return_value=src.installer.WriteResult(
        target="claude-code-cli", success=True,
        config_path=None, backup_path=None, message="ok",
    ))
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)

    # fake_prompts queue: one API key re-prompt
    fake_prompts.push(new_key)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main([
            "--yes",  # no --no-validate, so ping runs
            "--client", "claude-code",
            "--scope", "user",
            "--url", "https://x.testrail.io",
            "--username", "u@x.com",
            "--api-key", "A" * 40,
        ])

    assert exc_info.value.code == 0
    assert ping_call_count[0] == 2, (
        f"expected 2 ping calls (REPROMPT then OK), got {ping_call_count[0]}"
    )


# ---------------------------------------------------------------------------
# Integration smoke test — test_smoke_main_full_dry_run_on_tmp_home
# ---------------------------------------------------------------------------

def test_smoke_main_full_dry_run_on_tmp_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Full dry-run proof-of-life: no files created, exit 0, summary in output.

    Equivalent to plan Step 9.1 command 4 in automated form.
    Uses --no-validate so no network call is made.
    """
    import logging
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: True)
    desktop_path = tmp_path / "desktop.json"
    monkeypatch.setattr("src.installer._claude_desktop_config_path", lambda: desktop_path)

    with caplog.at_level(logging.INFO, logger="src.installer"):
        with pytest.raises(SystemExit) as exc_info:
            src.installer.main([
                "--dry-run", "--yes",
                "--client", "both",
                "--no-validate",
                "--scope", "user",
                "--url", "https://x.testrail.io",
                "--username", "u@x.com",
                "--api-key", "E" * 40,
            ])

    assert exc_info.value.code == 0, f"expected exit 0, got {exc_info.value.code}"

    # No files must have been created anywhere in tmp_path
    created_files = list(tmp_path.rglob("*"))
    assert created_files == [], f"expected no files created under tmp_path, found: {created_files}"

    # Summary or dry-run confirmation must appear in output
    captured = capsys.readouterr()
    all_output = caplog.text + captured.out + captured.err
    assert all_output.strip(), "expected some output from dry-run"


def test_main_ping_warn_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """PingResult.WARN does NOT abort — wizard continues and exits 0."""
    import logging
    import src.installer  # noqa: PLC0415
    from unittest.mock import MagicMock

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)
    monkeypatch.setattr(
        "src.installer._ping_testrail",
        lambda *a: src.installer.PingResult.WARN,
    )
    mock_cli = MagicMock(return_value=src.installer.WriteResult(
        target="claude-code-cli", success=True,
        config_path=None, backup_path=None, message="ok",
    ))
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)

    with caplog.at_level(logging.INFO, logger="src.installer"):
        with pytest.raises(SystemExit) as exc_info:
            src.installer.main([
                "--yes",  # no --no-validate → ping is called
                "--client", "claude-code",
                "--scope", "user",
                "--url", "https://x.testrail.io",
                "--username", "u@x.com",
                "--api-key", "A" * 40,
            ])

    assert exc_info.value.code == 0, "WARN ping must not abort installation"
    assert mock_cli.call_count == 1, "writer must be called after WARN ping"
    # Summary must mention WARN
    assert "warn" in caplog.text.lower() or "summary" in caplog.text.lower()


def test_main_desktop_path_none_skips_gracefully(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """If _claude_desktop_config_path() returns None, desktop write is skipped (not crash)."""
    import src.installer  # noqa: PLC0415
    from unittest.mock import MagicMock

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: False)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_config_path", lambda: None)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main([
            "--no-validate", "--yes",
            "--client", "claude-desktop",
            "--scope", "user",
            "--url", "https://x.testrail.io",
            "--username", "u@x.com",
            "--api-key", "A" * 40,
        ])

    # exit 1 because the desktop write is reported as failure (path unknown)
    assert exc_info.value.code == 1, (
        f"expected exit 1 when desktop path is None, got {exc_info.value.code}"
    )


def test_main_all_fail_exits_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """If all writers report success=False, main exits 1."""
    import src.installer  # noqa: PLC0415
    from unittest.mock import MagicMock

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    # Both CLI and JSON return failure
    mock_cli = MagicMock(return_value=src.installer.WriteResult(
        target="claude-code-cli", success=False,
        config_path=None, backup_path=None, message="cli fail",
    ))
    mock_json = MagicMock(return_value=src.installer.WriteResult(
        target="claude-code-json", success=False,
        config_path=None, backup_path=None, message="json fail",
    ))
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)
    monkeypatch.setattr("src.installer._write_claude_code_via_json", mock_json)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main([
            "--no-validate", "--yes",
            "--client", "claude-code",
            "--scope", "user",
            "--url", "https://x.testrail.io",
            "--username", "u@x.com",
            "--api-key", "A" * 40,
        ])

    assert exc_info.value.code == 1, (
        f"expected exit 1 when all writers fail, got {exc_info.value.code}"
    )
