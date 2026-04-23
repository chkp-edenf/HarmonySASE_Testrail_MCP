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
        src.installer.main(
            [
                "--dry-run",
                "--yes",
                "--client",
                "both",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
                "--no-validate",
            ]
        )
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

    args = src.installer._build_parser().parse_args(
        [
            "--url",
            "https://x.testrail.io",
            "--username",
            "u@x.com",
            "--api-key",
            "F" * 40,
        ]
    )
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
    """Invalid URL (ftp://x) triggers re-prompt; valid https URL accepted."""
    import src.installer  # noqa: PLC0415

    monkeypatch.delenv("TESTRAIL_URL", raising=False)
    monkeypatch.setenv("TESTRAIL_USERNAME", "env@example.com")
    monkeypatch.setenv("TESTRAIL_API_KEY", "E" * 40)

    fake_prompts.push("ftp://x")  # rejected
    fake_prompts.push("https://ok.testrail.io/")  # accepted; trailing / stripped

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
        "email" in record.message.lower()
        for record in caplog.records
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

    fake_prompts.push("short")  # 5 chars — rejected
    fake_prompts.push("A" * 40)  # 40 chars — accepted

    args = src.installer._build_parser().parse_args([])
    with caplog.at_level(logging.WARNING, logger="src.installer"):
        _url, _user, key = src.installer._resolve_credentials(args)

    assert key == "A" * 40
    assert any(
        "20" in record.message
        or "length" in record.message.lower()
        or "short" in record.message.lower()
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
        src.installer.main(
            [
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--no-validate",
            ]
        )

    assert exc_info.value.code == 130, f"expected exit 130 on Ctrl-C, got {exc_info.value.code}"
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
    assert result is True, (
        "_detect_claude_code() must return True when CLI is present and --version exits 0"
    )


def test_detect_claude_code_absent(
    fake_claude_cli,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """`_detect_claude_code()` returns False when PATH and all fallback probes miss.

    HOME is redirected to tmp_path so the installer-fallback (~/.claude/local/claude)
    and alt-install (~/.local/bin/claude) paths resolve to non-existent dirs.
    """
    import src.installer  # noqa: PLC0415

    fake_claude_cli.present = False
    monkeypatch.setenv("HOME", str(tmp_path))
    # Also ensure npm probe doesn't hit by returning None for npm too
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = src.installer._detect_claude_code()
    assert result is False, "_detect_claude_code() must return False when `claude` is not on PATH"


def test_detect_claude_code_version_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """`_detect_claude_code()` returns False when PATH probe fires but --version fails.

    HOME is redirected to tmp_path so fallback paths resolve to non-existent dirs.
    subprocess.run is stubbed to return returncode=1 for any --version call so all
    version probes fail regardless of which binary path the probe constructs.
    """
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    # shutil.which returns 'claude' path for 'claude', None for everything else
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/local/bin/claude" if name == "claude" else None
    )

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "--version" in args:
            return CompletedProcess(args, 1, stdout="", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._detect_claude_code()
    assert result is False, (
        "_detect_claude_code() must return False when --version exits 1 and all fallbacks miss"
    )


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
    """On darwin, if all probes miss, _claude_desktop_detected() returns False.

    _claude_desktop_config_path() still returns the expected path shape (detection != path shape).
    HOME is redirected to tmp_path so config-dir probe misses; /Applications/Claude.app
    is suppressed (may genuinely exist on dev machine); pgrep returns non-zero.
    """
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Suppress probe 2: /Applications/Claude.app may exist on this machine
    _orig_is_dir = type(tmp_path).is_dir

    def fake_is_dir(self) -> bool:  # type: ignore[no-untyped-def]
        if str(self) == "/Applications/Claude.app":
            return False
        return _orig_is_dir(self)

    monkeypatch.setattr(type(tmp_path), "is_dir", fake_is_dir)

    # Suppress probe 3: pgrep returns non-zero
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kw: CompletedProcess(args, 1, stdout="", stderr=""),
    )

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
    """--client flag wins over detection; menu skipped; WARNING logged for undetected client."""
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
        "code" in record.message.lower()
        or "claude code" in record.message.lower()
        or "not detected" in record.message.lower()
        or "detected" in record.message.lower()
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
# Step 3.5 — _prompt_scope (4 tests)
# ---------------------------------------------------------------------------


def test_prompt_scope_personal_returns_user(fake_prompts) -> None:
    """Prompt input '1' (Personal) -> scope='user'."""
    import src.installer  # noqa: PLC0415

    fake_prompts.push("1")
    assert src.installer._prompt_scope() == "user"


def test_prompt_scope_project_returns_project(fake_prompts) -> None:
    """Prompt input '2' (Project) -> scope='project'."""
    import src.installer  # noqa: PLC0415

    fake_prompts.push("2")
    assert src.installer._prompt_scope() == "project"


def test_prompt_scope_reprompts_on_invalid(
    fake_prompts,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Invalid selection logs a warning and re-prompts until valid input."""
    import logging  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    fake_prompts.push("bogus")
    fake_prompts.push("")
    fake_prompts.push("2")
    with caplog.at_level(logging.WARNING, logger="src.installer"):
        assert src.installer._prompt_scope() == "project"
    assert any(
        "invalid selection" in record.message.lower()
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ), "expected a WARNING about invalid selection"


def test_scope_omitted_triggers_prompt_for_claude_code(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts,
    fake_claude_cli,
) -> None:
    """main() with --client claude-code and no --scope -> _prompt_scope fires."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    # Prompt queue: scope choice ("2"), then pre-write confirm ("y")
    fake_prompts.push("2")
    fake_prompts.push("y")

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(
            [
                "--client",
                "claude-code",
                "--url",
                "https://x.testrail.io",
                "--username",
                "x@y.com",
                "--api-key",
                "K" * 40,
                "--no-validate",
                "--ref",
                "main",
            ]
        )

    assert exc_info.value.code == 0
    # Subprocess args must include --scope project (the prompted choice)
    mcp_add_calls = [call for call in fake_claude_cli.calls if call[:3] == ["claude", "mcp", "add"]]
    assert len(mcp_add_calls) == 1
    args = mcp_add_calls[0]
    assert "--scope" in args and args[args.index("--scope") + 1] == "project"


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
        "claude",
        "mcp",
        "add",
        "--scope",
        "user",
        "testrail",
        "-e",
        "TESTRAIL_URL=https://x.testrail.io",
        "-e",
        "TESTRAIL_USERNAME=u@x.com",
        "-e",
        f"TESTRAIL_API_KEY={key}",
        "--",
        "uvx",
        "--from",
        "git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git@main",
        "testrail-mcp",
    ]
    assert captured == expected, (
        f"captured args mismatch:\n  got:      {captured}\n  expected: {expected}"
    )


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
    mcp_add_calls = [
        c for c in fake_claude_cli.calls if len(c) >= 3 and c[:3] == ["claude", "mcp", "add"]
    ]
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
    config_path.write_text(
        json.dumps({"mcpServers": {"other": {"command": "echo", "args": ["x"]}}})
    )

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
    assert config_path.read_bytes() == original_bytes, (
        "file must be unchanged when user answers 'n'"
    )

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
    assert result.backup_path.read_bytes() == original_bytes, (
        "backup must be byte-for-byte copy of original"
    )


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
    assert config_path.read_bytes() == original_bytes, (
        "file must be unchanged when user answers 'n'"
    )

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
    assert config_path.read_bytes() == bad_content, (
        "original malformed bytes must be intact after 'n'"
    )
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

    import contextlib  # noqa: PLC0415

    backup_existed_at_parse_time: list[bool] = []

    def spy_loads(text: str, **kwargs: object) -> object:
        # Check whether any *.bak.* file exists in the parent dir RIGHT NOW
        bak_files = list(config_path.parent.glob(f"{config_path.name}.bak.*"))
        backup_existed_at_parse_time.append(len(bak_files) > 0)
        raise json.JSONDecodeError("simulated", text, 0)

    monkeypatch.setattr(json, "loads", spy_loads)

    # assume_yes=True: malformed JSON is handled gracefully (no re-raise).
    # We only care that the backup existed when json.loads was called —
    # the function may succeed or raise; either outcome is acceptable here.
    with contextlib.suppress(SystemExit, OSError):
        src.installer._write_claude_desktop(
            path=config_path,
            ref=_EXPECTED_REF,
            url=_EXPECTED_URL,
            username=_EXPECTED_USERNAME,
            api_key=_EXPECTED_KEY,
            dry_run=False,
            assume_yes=True,
        )

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
    import json
    import os

    import src.installer  # noqa: PLC0415

    original_data = {"mcpServers": {"existing": {"command": "old", "args": []}}}
    config_path = tmp_path / "claude_desktop_config.json"
    config_path.write_text(json.dumps(original_data))
    pre_write_bytes = config_path.read_bytes()

    import contextlib  # noqa: PLC0415

    call_count = [0]

    def crashing_replace(src: str, dst: str) -> None:
        call_count[0] += 1
        raise OSError("simulated crash")

    monkeypatch.setattr(os, "replace", crashing_replace)

    with contextlib.suppress(OSError):
        src.installer._write_claude_desktop(
            path=config_path,
            ref=_EXPECTED_REF,
            url=_EXPECTED_URL,
            username=_EXPECTED_USERNAME,
            api_key=_EXPECTED_KEY,
            dry_run=False,
            assume_yes=True,
        )

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
    import json
    import logging

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
    """HTTP 200 → outcome.status == 'ok', retry=False."""
    import src.installer  # noqa: PLC0415

    mock_response = type("R", (), {"status_code": 200, "json": lambda self: []})()
    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: mock_response)

    outcome = src.installer._ping_testrail("https://x.testrail.io", "u@x.com", "K" * 40)
    assert outcome.status == "ok"
    assert outcome.retry is False
    assert outcome.http_code == 200


def test_ping_401_returns_reprompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 401 → outcome.retry=True, status='unauthorized', hint is set."""
    import src.installer  # noqa: PLC0415

    mock_response = type("R", (), {"status_code": 401})()
    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: mock_response)

    outcome = src.installer._ping_testrail("https://x.testrail.io", "u@x.com", "K" * 40)
    assert outcome.status == "unauthorized"
    assert outcome.retry is True
    assert outcome.hint is not None
    assert "API" in outcome.hint.upper() or "key" in outcome.hint.lower()


def test_ping_403_returns_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 403 → outcome.status='permission', retry=False (permissions-level WARN)."""
    import src.installer  # noqa: PLC0415

    mock_response = type("R", (), {"status_code": 403})()
    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: mock_response)

    outcome = src.installer._ping_testrail("https://x.testrail.io", "u@x.com", "K" * 40)
    assert outcome.status == "permission"
    assert outcome.retry is False


def test_ping_network_error_returns_warn(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """httpx.ConnectError → outcome.status='network' + an INFO log (no stack trace)."""
    import logging

    import httpx

    import src.installer  # noqa: PLC0415

    def raise_connect(*a: object, **kw: object) -> None:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("src.installer._http_get", raise_connect)

    with caplog.at_level(logging.INFO, logger="src.installer"):
        outcome = src.installer._ping_testrail("https://x.testrail.io", "u@x.com", "K" * 40)

    assert outcome.status == "network"
    assert outcome.retry is False
    assert any(
        "network" in r.message.lower()
        or "connect" in r.message.lower()
        or "error" in r.message.lower()
        or "warn" in r.message.lower()
        for r in caplog.records
    ), "expected an INFO/WARNING log about the network failure"


def test_ping_timeout_returns_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    """httpx.TimeoutException → outcome.status='timeout', retry=False."""
    import httpx

    import src.installer  # noqa: PLC0415

    def raise_timeout(*a: object, **kw: object) -> None:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("src.installer._http_get", raise_timeout)

    outcome = src.installer._ping_testrail("https://x.testrail.io", "u@x.com", "K" * 40)
    assert outcome.status == "timeout"
    assert outcome.retry is False


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
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    mock_ping = MagicMock()
    monkeypatch.setattr("src.installer._ping_testrail", mock_ping)
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(
            [
                "--dry-run",
                "--yes",
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
            ]
        )

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

    with (
        caplog.at_level(logging.INFO, logger="src.installer"),
        pytest.raises(SystemExit) as exc_info,
    ):
        src.installer.main(
            [
                "--dry-run",
                "--yes",
                "--client",
                "both",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
            ]
        )

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
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Successful real run prints an Installation summary containing all expected fields.

    Summary moved from logger.info to stderr print() via _emit so it renders
    reliably over ANSI/Unicode on all terminals. Tests combine caplog + capsys
    to cover both channels.
    """
    import logging
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    # Mock CLI writer to return success without touching real claude CLI
    mock_cli = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-code-cli",
            success=True,
            config_path=None,
            backup_path=None,
            message="mocked success",
        )
    )
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)

    api_key = "F" * 40
    with (
        caplog.at_level(logging.INFO, logger="src.installer"),
        pytest.raises(SystemExit) as exc_info,
    ):
        src.installer.main(
            [
                "--no-validate",
                "--yes",
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                api_key,
            ]
        )

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    all_output = caplog.text + captured.err + captured.out
    assert "installation" in all_output.lower(), "expected 'Installation' header in summary output"
    # API key must NOT appear raw
    assert api_key not in all_output, "raw API key must not appear in summary"
    # Redacted form or length indicator must be there
    assert "***" in all_output or "chars" in all_output, (
        "expected redacted key representation in summary"
    )


def test_main_happy_path_writes_both_clients(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """--no-validate --yes --client both: both writers called; exit 0."""
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    desktop_path = tmp_path / "desktop_config.json"
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_config_path", lambda: desktop_path)

    mock_cli = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-code-cli",
            success=True,
            config_path=None,
            backup_path=None,
            message="ok",
        )
    )
    mock_desktop = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-desktop",
            success=True,
            config_path=desktop_path,
            backup_path=None,
            message="ok",
        )
    )
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)
    monkeypatch.setattr("src.installer._write_claude_desktop", mock_desktop)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(
            [
                "--no-validate",
                "--yes",
                "--client",
                "both",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
            ]
        )

    assert exc_info.value.code == 0
    assert mock_cli.call_count == 1, "CLI writer must be called exactly once"
    assert mock_desktop.call_count == 1, "Desktop writer must be called exactly once"


def test_main_cli_failure_falls_back_to_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """If _write_claude_code_via_cli returns success=False, JSON fallback is called."""
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    mock_cli = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-code-cli",
            success=False,
            config_path=None,
            backup_path=None,
            message="cli failed",
        )
    )
    mock_json = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-code-json",
            success=True,
            config_path=tmp_path / ".claude.json",
            backup_path=None,
            message="json ok",
        )
    )
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)
    monkeypatch.setattr("src.installer._write_claude_code_via_json", mock_json)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(
            [
                "--no-validate",
                "--yes",
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
            ]
        )

    assert exc_info.value.code == 0
    assert mock_cli.call_count == 1, "CLI writer must be attempted once"
    assert mock_json.call_count == 1, "JSON fallback must be called after CLI failure"


def test_main_ping_reprompt_loop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fake_prompts,
) -> None:
    """ping → REPROMPT once, then OK: _prompt_api_key called once between the two pings."""
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    new_key = "B" * 40
    ping_call_count = [0]

    def ping_side_effect(url: str, username: str, api_key: str):
        ping_call_count[0] += 1
        if ping_call_count[0] == 1:
            return src.installer._PingOutcome(
                status="unauthorized", retry=True, hint="credentials rejected"
            )
        return src.installer._PingOutcome(status="ok", project_count=1)

    monkeypatch.setattr("src.installer._ping_testrail", ping_side_effect)

    mock_cli = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-code-cli",
            success=True,
            config_path=None,
            backup_path=None,
            message="ok",
        )
    )
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)

    # fake_prompts queue: one API key re-prompt
    fake_prompts.push(new_key)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(
            [
                "--yes",  # no --no-validate, so ping runs
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
            ]
        )

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

    with (
        caplog.at_level(logging.INFO, logger="src.installer"),
        pytest.raises(SystemExit) as exc_info,
    ):
        src.installer.main(
            [
                "--dry-run",
                "--yes",
                "--client",
                "both",
                "--no-validate",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "E" * 40,
            ]
        )

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
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_PingOutcome with non-OK non-retry status does NOT abort — wizard continues and exits 0."""
    import logging
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)
    monkeypatch.setattr(
        "src.installer._ping_testrail",
        lambda *a: src.installer._PingOutcome(status="permission", retry=False, hint="403"),
    )
    mock_cli = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-code-cli",
            success=True,
            config_path=None,
            backup_path=None,
            message="ok",
        )
    )
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)

    with (
        caplog.at_level(logging.INFO, logger="src.installer"),
        pytest.raises(SystemExit) as exc_info,
    ):
        src.installer.main(
            [
                "--yes",  # no --no-validate → ping is called
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
            ]
        )

    assert exc_info.value.code == 0, "WARN ping must not abort installation"
    assert mock_cli.call_count == 1, "writer must be called after WARN ping"
    captured = capsys.readouterr()
    all_output = caplog.text + captured.err + captured.out
    # Summary must surface the WARN status (or the hint) to the user.
    assert (
        "warn" in all_output.lower()
        or "permission" in all_output.lower()
        or "installation" in all_output.lower()
    )


def test_main_desktop_path_none_skips_gracefully(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """If _claude_desktop_config_path() returns None, desktop write is skipped (not crash)."""

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: False)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_config_path", lambda: None)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(
            [
                "--no-validate",
                "--yes",
                "--client",
                "claude-desktop",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
            ]
        )

    # exit 1 because the desktop write is reported as failure (path unknown)
    assert exc_info.value.code == 1, (
        f"expected exit 1 when desktop path is None, got {exc_info.value.code}"
    )


def test_main_all_fail_exits_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """If all writers report success=False, main exits 1."""
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    # Both CLI and JSON return failure
    mock_cli = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-code-cli",
            success=False,
            config_path=None,
            backup_path=None,
            message="cli fail",
        )
    )
    mock_json = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-code-json",
            success=False,
            config_path=None,
            backup_path=None,
            message="json fail",
        )
    )
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)
    monkeypatch.setattr("src.installer._write_claude_code_via_json", mock_json)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(
            [
                "--no-validate",
                "--yes",
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
            ]
        )

    assert exc_info.value.code == 1, (
        f"expected exit 1 when all writers fail, got {exc_info.value.code}"
    )


# ---------------------------------------------------------------------------
# Wizard UX polish tests (Tier 1/2/3 — see plan-003)
# ---------------------------------------------------------------------------


def test_use_color_off_when_no_color_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """NO_COLOR=1 disables colored output even if stderr is a TTY."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("NO_COLOR", "1")
    assert src.installer._use_color() is False
    # _c() should be a no-op under NO_COLOR
    assert src.installer._c("hello", src.installer._ANSI_GREEN) == "hello"


def test_c_wraps_with_ansi_when_color_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """_c() wraps text with the ANSI code when _use_color() is True."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr("src.installer._use_color", lambda: True)
    wrapped = src.installer._c("hello", src.installer._ANSI_GREEN)
    assert wrapped.startswith(src.installer._ANSI_GREEN)
    assert wrapped.endswith(src.installer._ANSI_RESET)
    assert "hello" in wrapped


def test_url_prompt_accepts_bare_hostname(fake_prompts) -> None:
    """Typing 'company.testrail.io' -> auto-prefixed to 'https://company.testrail.io'."""
    import src.installer  # noqa: PLC0415

    fake_prompts.push("company.testrail.io")
    assert src.installer._prompt_url() == "https://company.testrail.io"


def test_url_prompt_upgrades_http_to_https(
    fake_prompts,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """'http://x.testrail.io' is auto-upgraded to https; no re-prompt (plan-003 item A).

    Previously this test checked that http:// was *rejected*. plan-003 changes the
    behavior: http:// is now auto-normalized to https:// with a 'Normalized:' notice
    so users who paste http:// URLs don't get stuck in a re-prompt loop.
    """
    import logging  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    fake_prompts.push("http://example.testrail.io")
    # Only ONE value in the queue — if a re-prompt fires the fixture will raise.
    with caplog.at_level(logging.WARNING, logger="src.installer"):
        result = src.installer._prompt_url()
    assert result == "https://example.testrail.io", f"expected https upgrade, got {result!r}"
    captured = capsys.readouterr()
    all_output = captured.err + caplog.text
    has_notice = (
        "Normalized" in all_output or "normalized" in all_output or "http" in all_output.lower()
    )
    assert has_notice, "expected a notice about http→https upgrade"


def test_url_prompt_strips_trailing_slash(fake_prompts) -> None:
    """Trailing slash is stripped on both input forms."""
    import src.installer  # noqa: PLC0415

    fake_prompts.push("https://x.testrail.io/")
    assert src.installer._prompt_url() == "https://x.testrail.io"


def test_url_prompt_rejects_gibberish(
    fake_prompts,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Input without a dot is rejected with a hint and re-prompts."""
    import logging  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    fake_prompts.push("notaurl")
    fake_prompts.push("https://x.testrail.io")
    with caplog.at_level(logging.WARNING, logger="src.installer"):
        result = src.installer._prompt_url()
    assert result == "https://x.testrail.io"
    assert any(
        "url" in r.message.lower() or "notaurl" in r.message.lower()
        for r in caplog.records
        if r.levelno >= logging.WARNING
    )


def test_scope_prompt_description_shown(
    fake_prompts,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Scope prompt explains what Personal vs Project means (captured on stdout)."""
    import src.installer  # noqa: PLC0415

    fake_prompts.push("1")
    src.installer._prompt_scope()
    out = capsys.readouterr().out
    assert "Personal" in out
    assert "Project" in out
    # Critical word ensures we explain the effect, not just the name.
    assert "every project" in out.lower() or "all your projects" in out.lower()


def test_ping_ok_extracts_project_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 200 with a JSON array body populates outcome.project_count."""
    import src.installer  # noqa: PLC0415

    class _FakeResp:
        status_code = 200

        def json(self) -> list[dict]:
            return [{"id": i} for i in range(12)]

    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: _FakeResp())

    outcome = src.installer._ping_testrail("https://x.testrail.io", "u@x.com", "K" * 40)
    assert outcome.status == "ok"
    assert outcome.project_count == 12


def test_ping_ok_tolerates_non_array_body(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 200 with a non-list JSON body still reports status=ok (count=None is OK)."""
    import src.installer  # noqa: PLC0415

    class _FakeResp:
        status_code = 200

        def json(self) -> dict:
            return {"unexpected": "shape"}

    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: _FakeResp())

    outcome = src.installer._ping_testrail("https://x.testrail.io", "u@x.com", "K" * 40)
    assert outcome.status == "ok"
    assert outcome.project_count is None


def test_ping_500_returns_server_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 500 -> outcome.status='server', retry=False."""
    import src.installer  # noqa: PLC0415

    mock_response = type("R", (), {"status_code": 500})()
    monkeypatch.setattr("src.installer._http_get", lambda *a, **kw: mock_response)

    outcome = src.installer._ping_testrail("https://x.testrail.io", "u@x.com", "K" * 40)
    assert outcome.status == "server"
    assert outcome.http_code == 500
    assert outcome.retry is False
    assert outcome.hint is not None


def test_prewrite_confirmation_declined_exits_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fake_prompts,
    fake_claude_cli,
) -> None:
    """User types 'n' at the pre-write confirmation -> no write, exit 0."""
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    mock_cli = MagicMock()
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)

    # Queue: pre-write confirm "n"
    fake_prompts.push("n")

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(
            [
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--no-validate",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "K" * 40,
            ]
        )

    assert exc_info.value.code == 0, "declining the pre-write confirmation should exit 0"
    assert mock_cli.call_count == 0, "writer must not be called when user declines confirmation"


def test_existing_entry_prompt_keep(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fake_prompts,
) -> None:
    """Existing testrail entry + user picks 'k' -> file unchanged, result success=True."""
    import json

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    config_path = tmp_path / ".claude.json"
    original_entry = {"command": "old-cmd", "args": [], "env": {"TESTRAIL_URL": "https://old.io"}}
    config_path.write_text(json.dumps({"mcpServers": {"testrail": original_entry}}))
    original_bytes = config_path.read_bytes()

    fake_prompts.push("k")
    result = src.installer._write_claude_code_via_json(
        scope="user",
        ref="main",
        url="https://new.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=False,
    )

    assert result.success is True
    assert "kept" in result.message.lower() or "declined" in result.message.lower()
    assert config_path.read_bytes() == original_bytes, (
        "file must be unchanged when user picks 'keep'"
    )


def test_welcome_banner_suppressed_under_yes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--yes skips the welcome banner so CI logs stay tidy."""
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)
    monkeypatch.setattr(
        "src.installer._write_claude_code_via_cli",
        MagicMock(
            return_value=src.installer.WriteResult(
                target="claude-code-cli",
                success=True,
                config_path=None,
                backup_path=None,
                message="ok",
            )
        ),
    )

    with pytest.raises(SystemExit):
        src.installer.main(
            [
                "--yes",
                "--no-validate",
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "K" * 40,
            ]
        )

    captured = capsys.readouterr()
    # Banner line contains the version label. Under --yes, we expect it absent.
    assert "TestRail MCP Server — Installer" not in captured.err
    assert "━" * 10 not in captured.err


def test_welcome_banner_shown_without_yes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fake_prompts,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without --yes the banner IS printed to stderr."""
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)
    monkeypatch.setattr(
        "src.installer._write_claude_code_via_cli",
        MagicMock(
            return_value=src.installer.WriteResult(
                target="claude-code-cli",
                success=True,
                config_path=None,
                backup_path=None,
                message="ok",
            )
        ),
    )

    # Queue: pre-write confirm "y"
    fake_prompts.push("y")

    with pytest.raises(SystemExit):
        src.installer.main(
            [
                "--no-validate",
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "K" * 40,
            ]
        )

    captured = capsys.readouterr()
    assert "TestRail MCP Server — Installer" in captured.err


def test_help_epilog_mentions_examples(capsys: pytest.CaptureFixture[str]) -> None:
    """`--help` output includes the Examples block so flags are discoverable."""
    import src.installer  # noqa: PLC0415

    with pytest.raises(SystemExit):
        src.installer.main(["--help"])
    captured = capsys.readouterr()
    assert "Examples:" in captured.out
    assert "--dry-run" in captured.out
    assert "--yes" in captured.out


def test_main_ping_reprompt_cap_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fake_prompts,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Kody-flagged path: 4 consecutive 401s (initial + 3 retries) -> install
    continues with FAILED ping status, exit 0 (not 1)."""
    from unittest.mock import MagicMock

    import src.installer  # noqa: PLC0415

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    call_count = [0]

    def always_unauthorized(url: str, username: str, api_key: str):
        call_count[0] += 1
        return src.installer._PingOutcome(
            status="unauthorized", retry=True, hint="Credentials rejected."
        )

    monkeypatch.setattr("src.installer._ping_testrail", always_unauthorized)

    mock_cli = MagicMock(
        return_value=src.installer.WriteResult(
            target="claude-code-cli",
            success=True,
            config_path=None,
            backup_path=None,
            message="ok",
        )
    )
    monkeypatch.setattr("src.installer._write_claude_code_via_cli", mock_cli)

    # Queue three fresh API keys (one per retry).
    for _ in range(3):
        fake_prompts.push("Z" * 40)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(
            [
                "--yes",  # skip banner + confirm; still pings (no --no-validate)
                "--client",
                "claude-code",
                "--scope",
                "user",
                "--url",
                "https://x.testrail.io",
                "--username",
                "u@x.com",
                "--api-key",
                "A" * 40,
            ]
        )

    # After the cap fires, install continues — writer is still invoked.
    assert exc_info.value.code == 0
    assert mock_cli.call_count == 1
    # Exactly 4 pings: 1 initial + 3 retries with fresh keys.
    assert call_count[0] == 4, f"expected 4 pings, got {call_count[0]}"


def test_existing_entry_prompt_keep_desktop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fake_prompts,
) -> None:
    """Kody-flagged gap: cover the 'keep' branch in _write_claude_desktop too."""
    import json  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    desktop_path = tmp_path / "claude_desktop_config.json"
    original_entry = {"command": "old-cmd", "args": [], "env": {"TESTRAIL_URL": "https://old.io"}}
    desktop_path.write_text(json.dumps({"mcpServers": {"testrail": original_entry}}))

    fake_prompts.push("k")
    result = src.installer._write_claude_desktop(
        path=desktop_path,
        ref="main",
        url="https://new.testrail.io",
        username="u@x.com",
        api_key="K" * 40,
        dry_run=False,
        assume_yes=False,
    )

    assert result.success is True
    assert "kept" in result.message.lower()
    # The testrail entry must be the original, not the new values.
    data = json.loads(desktop_path.read_text())
    assert data["mcpServers"]["testrail"]["env"]["TESTRAIL_URL"] == "https://old.io"


def test_neither_detected_exit_message_mentions_both_options(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When neither client is detected, the exit message names both options clearly."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr("src.installer._detect_claude_code", lambda: False)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)
    args = src.installer._build_parser().parse_args([])

    with pytest.raises(SystemExit) as exc_info:
        src.installer._choose_clients(args)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert "Claude Code" in all_output
    assert "Claude Desktop" in all_output
    assert "claude.ai/download" in all_output


# ---------------------------------------------------------------------------
# Phase 1 — URL auto-normalize (plan-003-wizard-robustness.md, Step 1.1 + 1.2)
# TDD RED: tests written before _normalize_testrail_url() implementation exists.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Step 1.1 — Unit tests for _normalize_testrail_url()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected_url,expected_notes_contains",
    [
        # Bare hostname — auto-prefix https://
        (
            "company.testrail.io",
            "https://company.testrail.io",
            [],
        ),
        # Full https with trailing slash — strip it, no notes
        (
            "https://x.testrail.io/",
            "https://x.testrail.io",
            [],
        ),
        # Browser-tab URL with path + query — drop everything after host, emit note
        (
            "https://perimeter81.testrail.io/index.php?/suites/view/392&group_by=cases:section_id",
            "https://perimeter81.testrail.io",
            ["dropped path"],
        ),
        # http:// — upgrade to https + note
        (
            "http://x.testrail.io",
            "https://x.testrail.io",
            ["upgraded http"],
        ),
        # http:// with path — upgrade + drop path, both notes present
        (
            "http://company.testrail.io/index.php?/suites/view/1",
            "https://company.testrail.io",
            ["upgraded http", "dropped path"],
        ),
        # Bare hostname with trailing slash — auto-prefix + strip slash, no notes
        (
            "company.testrail.io/",
            "https://company.testrail.io",
            [],
        ),
    ],
)
def test_normalize_url_happy_path(
    raw: str,
    expected_url: str,
    expected_notes_contains: list[str],
) -> None:
    """_normalize_testrail_url() normalizes valid inputs and returns correct notes."""
    import src.installer  # noqa: PLC0415

    url, notes = src.installer._normalize_testrail_url(raw)
    assert url == expected_url, f"expected {expected_url!r}, got {url!r} for input {raw!r}"
    for fragment in expected_notes_contains:
        assert any(fragment in note for note in notes), (
            f"expected a note containing {fragment!r} for input {raw!r}; notes={notes!r}"
        )


def test_normalize_url_accepts_bare_hostname() -> None:
    """company.testrail.io -> ('https://company.testrail.io', [])."""
    import src.installer  # noqa: PLC0415

    url, notes = src.installer._normalize_testrail_url("company.testrail.io")
    assert url == "https://company.testrail.io"
    assert notes == []


def test_normalize_url_strips_trailing_slash() -> None:
    """https://x.testrail.io/ -> no notes, trailing slash stripped."""
    import src.installer  # noqa: PLC0415

    url, notes = src.installer._normalize_testrail_url("https://x.testrail.io/")
    assert url == "https://x.testrail.io"
    assert notes == []


def test_normalize_url_strips_path_and_query() -> None:
    """Browser-tab URL -> base URL + 'dropped path/query' note."""
    import src.installer  # noqa: PLC0415

    raw = "https://company.testrail.io/index.php?/suites/view/392&group_by=cases:section_id"
    url, notes = src.installer._normalize_testrail_url(raw)
    assert url == "https://company.testrail.io"
    assert any("dropped path" in n or "path" in n for n in notes), (
        f"expected a 'dropped path' note; got {notes!r}"
    )


def test_normalize_url_upgrades_http_to_https() -> None:
    """http://x.testrail.io -> ('https://x.testrail.io', ['upgraded http -> https'])."""
    import src.installer  # noqa: PLC0415

    url, notes = src.installer._normalize_testrail_url("http://x.testrail.io")
    assert url == "https://x.testrail.io"
    assert any("http" in n for n in notes), f"expected an http-upgrade note; got {notes!r}"


@pytest.mark.parametrize(
    "bad_input",
    [
        "",  # empty string
        "   ",  # whitespace only
    ],
)
def test_normalize_url_rejects_empty(bad_input: str) -> None:
    """Empty or whitespace-only input raises ValueError."""
    import src.installer  # noqa: PLC0415

    with pytest.raises(ValueError, match=r"(?i)empty|blank|url"):
        src.installer._normalize_testrail_url(bad_input)


@pytest.mark.parametrize(
    "bad_input",
    [
        "file:///etc/passwd",
        "ftp://x.testrail.io",
    ],
)
def test_normalize_url_rejects_non_http_scheme(bad_input: str) -> None:
    """file:// and ftp:// raise ValueError with user-facing message."""
    import src.installer  # noqa: PLC0415

    with pytest.raises(ValueError):
        src.installer._normalize_testrail_url(bad_input)


@pytest.mark.parametrize(
    "bad_input",
    [
        "notaurl",  # no dot — no TLD
        "https://",  # scheme but no host
        "https://nodot",  # no dot in host
    ],
)
def test_normalize_url_rejects_gibberish(bad_input: str) -> None:
    """Inputs with no valid host raise ValueError."""
    import src.installer  # noqa: PLC0415

    with pytest.raises(ValueError):
        src.installer._normalize_testrail_url(bad_input)


# ---------------------------------------------------------------------------
# Step 1.2 — Integration tests for the three call sites
# ---------------------------------------------------------------------------


def test_url_prompt_normalizes_browser_tab_url(
    fake_prompts,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """_prompt_url(): browser-tab URL is normalized; returned value is the base URL;
    stderr contains 'Normalized:'."""
    import logging  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    browser_tab = "https://company.testrail.io/index.php?/suites/view/392&group_by=cases:section_id"
    fake_prompts.push(browser_tab)

    with caplog.at_level(logging.DEBUG, logger="src.installer"):
        result = src.installer._prompt_url()

    assert result == "https://company.testrail.io", f"expected base URL, got {result!r}"
    captured = capsys.readouterr()
    all_output = captured.err + caplog.text
    assert "Normalized" in all_output or "normalized" in all_output, (
        f"expected 'Normalized:' in stderr/logs; got:\n{all_output}"
    )


def test_url_flag_normalizes_browser_tab_url(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts: object,
    fake_testrail_ping,
) -> None:
    """--url with browser-tab URL: _resolve_credentials normalizes it;
    the resolved URL used for ping is the base URL."""
    import src.installer  # noqa: PLC0415

    browser_tab = "https://company.testrail.io/index.php?/suites/view/392"
    monkeypatch.setenv("TESTRAIL_USERNAME", "u@x.com")
    monkeypatch.setenv("TESTRAIL_API_KEY", "K" * 40)

    args = src.installer._build_parser().parse_args(["--url", browser_tab])
    url, _user, _key = src.installer._resolve_credentials(args)

    assert url == "https://company.testrail.io", f"expected normalized base URL, got {url!r}"


def test_url_env_normalizes_browser_tab_url(
    monkeypatch: pytest.MonkeyPatch,
    fake_prompts: object,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TESTRAIL_URL env var with browser-tab URL: _resolve_credentials normalizes it;
    the resolved URL is the base URL and 'Normalized:' appears in stderr/logs."""
    import logging  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    browser_tab = "https://company.testrail.io/index.php?/suites/view/392&group_by=cases:section_id"
    monkeypatch.setenv("TESTRAIL_URL", browser_tab)
    monkeypatch.setenv("TESTRAIL_USERNAME", "u@x.com")
    monkeypatch.setenv("TESTRAIL_API_KEY", "K" * 40)

    args = src.installer._build_parser().parse_args([])
    with caplog.at_level(logging.DEBUG, logger="src.installer"):
        url, _user, _key = src.installer._resolve_credentials(args)

    assert url == "https://company.testrail.io", (
        f"expected normalized base URL from env, got {url!r}"
    )
    captured = capsys.readouterr()
    all_output = captured.err + caplog.text
    assert "Normalized" in all_output or "normalized" in all_output, (
        f"expected 'Normalized:' warning in stderr/logs; got:\n{all_output}"
    )


# ---------------------------------------------------------------------------
# Phase 2 — Layered detection + CLI fallback (plan-003-wizard-robustness.md)
# TDD RED: tests written BEFORE rewriting _claude_desktop_detected,
# _claude_desktop_details, _detect_claude_code, _claude_code_details.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Step 2.1 — _ClientDetection.detected_via field
# ---------------------------------------------------------------------------


def test_client_detection_new_field_defaults_to_none() -> None:
    """_ClientDetection must have a detected_via field that defaults to None.

    This is a backward-compat guard: all existing code that constructs
    _ClientDetection without detected_via must keep working, and the __bool__
    method must remain unchanged.
    """
    import src.installer  # noqa: PLC0415

    # Construct without the new field — must not raise
    det = src.installer._ClientDetection(installed=True, label="Claude Code")
    assert det.detected_via is None, "detected_via must default to None"

    det_false = src.installer._ClientDetection(installed=False, label="Claude Desktop")
    assert det_false.detected_via is None

    # __bool__ must stay driven by .installed, not detected_via
    assert bool(det) is True
    assert bool(det_false) is False

    # With detected_via populated — bool still driven by installed
    det_with_via = src.installer._ClientDetection(
        installed=True, label="Claude Code", detected_via="path"
    )
    assert bool(det_with_via) is True
    assert det_with_via.detected_via == "path"


# ---------------------------------------------------------------------------
# Step 2.2 — Layered Claude Desktop detection
# ---------------------------------------------------------------------------
# All tests use sys.platform monkeypatch so macOS CI can cover Windows paths.
# subprocess.run, Path.is_dir / Path.exists, glob, and winreg are mocked
# individually per test so probes are independent.
# ---------------------------------------------------------------------------


class _SubprocessResult:
    """Minimal subprocess.CompletedProcess stand-in."""

    def __init__(self, returncode: int = 0, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def test_desktop_windows_config_dir_appdata_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 1a: %APPDATA%\\Claude\\ exists → detected_via='config-dir'."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata = tmp_path / "AppData" / "Roaming"
    claude_dir = appdata / "Claude"
    claude_dir.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "config-dir"


def test_desktop_windows_config_dir_localappdata_fallback_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 1b: LOCALAPPDATA\\Claude\\ hit → detected_via='config-dir'."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)  # dir exists but no Claude subdir
    localappdata = tmp_path / "AppData" / "Local"
    claude_local = localappdata / "Claude"
    claude_local.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "config-dir"


def test_desktop_windows_install_binary_hit_localappdata_programs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 2: LOCALAPPDATA\\Programs\\Claude\\Claude.exe → 'install-binary'."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)  # no Claude subdir
    localappdata = tmp_path / "AppData" / "Local"
    # Create the binary path
    binary_dir = localappdata / "Programs" / "Claude"
    binary_dir.mkdir(parents=True)
    (binary_dir / "Claude.exe").write_text("fake")
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "ProgramFiles"))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "ProgramFiles(x86)"))

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "install-binary"


def test_desktop_windows_install_binary_hit_programfiles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 2: %ProgramFiles%\\Claude\\Claude.exe found → detected_via='install-binary'."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    localappdata = tmp_path / "AppData" / "Local"
    localappdata.mkdir(parents=True)
    programfiles = tmp_path / "ProgramFiles"
    binary_dir = programfiles / "Claude"
    binary_dir.mkdir(parents=True)
    (binary_dir / "Claude.exe").write_text("fake")
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("PROGRAMFILES", str(programfiles))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "ProgramFiles(x86)"))

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "install-binary"


def test_desktop_windows_msix_package_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 3: LOCALAPPDATA\\Packages\\*Claude*\\ exists → detected_via='msix-package'."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    localappdata = tmp_path / "AppData" / "Local"
    packages_dir = localappdata / "Packages" / "AnthropicClaude_123abc"
    packages_dir.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "ProgramFiles"))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "ProgramFiles(x86)"))

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "msix-package"


def test_desktop_windows_tasklist_running_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 4: tasklist CSV row 'Claude.exe' present → detected_via='running-process'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    localappdata = tmp_path / "AppData" / "Local"
    localappdata.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "ProgramFiles"))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "ProgramFiles(x86)"))

    tasklist_output = (
        '"Image Name","PID","Session Name","Session#","Mem Usage"\r\n'
        '"Claude.exe","1234","Console","1","120,000 K"\r\n'
    )

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if "tasklist" in args[0] if isinstance(args, list) else args:
            return CompletedProcess(args, 0, stdout=tasklist_output, stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "running-process"


def test_desktop_windows_tasklist_no_match_miss(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 4: tasklist returns no Claude.exe row → probe misses, continues."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    localappdata = tmp_path / "AppData" / "Local"
    localappdata.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "ProgramFiles"))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "ProgramFiles(x86)"))

    tasklist_output = (
        '"Image Name","PID","Session Name","Session#","Mem Usage"\r\n'
        '"notepad.exe","999","Console","1","10,000 K"\r\n'
    )

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "tasklist" in args[0]:
            return CompletedProcess(args, 0, stdout=tasklist_output, stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    # Stub winreg so registry probe also misses

    fake_winreg = type(
        "winreg",
        (),
        {
            "HKEY_CURRENT_USER": 0,
            "OpenKey": staticmethod(lambda *a, **kw: (_ for _ in ()).throw(OSError("no key"))),
        },
    )()
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)

    result = src.installer._claude_desktop_details()

    assert result.installed is False


def test_desktop_windows_registry_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 5: winreg OpenKey Software\\Claude succeeds → detected_via='registry'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    localappdata = tmp_path / "AppData" / "Local"
    localappdata.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "ProgramFiles"))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "ProgramFiles(x86)"))

    # tasklist returns nothing — probe 4 misses
    tasklist_output = '"Image Name","PID"\r\n"notepad.exe","1"\r\n'

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "tasklist" in args[0]:
            return CompletedProcess(args, 0, stdout=tasklist_output, stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    # winreg: OpenKey succeeds (returns a fake handle object)
    class _FakeHandle:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    fake_winreg = type(
        "winreg",
        (),
        {
            "HKEY_CURRENT_USER": 0,
            "OpenKey": staticmethod(lambda *a, **kw: _FakeHandle()),
        },
    )()
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "registry"


def test_desktop_windows_all_probes_miss(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows: all five probes miss → installed=False, detected_via=None."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    localappdata = tmp_path / "AppData" / "Local"
    localappdata.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "ProgramFiles"))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "ProgramFiles(x86)"))

    tasklist_output = '"Image Name","PID"\r\n'

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "tasklist" in args[0]:
            return CompletedProcess(args, 0, stdout=tasklist_output, stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    fake_winreg = type(
        "winreg",
        (),
        {
            "HKEY_CURRENT_USER": 0,
            "OpenKey": staticmethod(lambda *a, **kw: (_ for _ in ()).throw(OSError("no key"))),
        },
    )()
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)

    result = src.installer._claude_desktop_details()

    assert result.installed is False
    assert result.detected_via is None


def test_desktop_macos_config_dir_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """macOS probe 1: ~/Library/Application Support/Claude/ exists → detected_via='config-dir'."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))

    app_support = tmp_path / "Library" / "Application Support" / "Claude"
    app_support.mkdir(parents=True)

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "config-dir"


def test_desktop_macos_app_bundle_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """macOS probe 2: /Applications/Claude.app exists → detected_via='install-binary'."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))
    # No config dir — probe 1 misses

    # Patch Path.is_dir to return True only for /Applications/Claude.app
    _orig_is_dir = type(tmp_path).is_dir

    def fake_is_dir(self) -> bool:  # type: ignore[no-untyped-def]
        if str(self) == "/Applications/Claude.app":
            return True
        return _orig_is_dir(self)

    monkeypatch.setattr(type(tmp_path), "is_dir", fake_is_dir)

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "install-binary"


def test_desktop_macos_pgrep_running_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """macOS probe 3: pgrep -f 'Claude.app' returns 0 → detected_via='running-process'.

    Probes 1 (config-dir) and 2 (install-binary /Applications/Claude.app) are
    suppressed by routing HOME to tmp_path (so probe 1 dir doesn't exist) and
    by stubbing Path.is_dir to return False for /Applications/Claude.app.
    """
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Suppress probe 2 (/Applications/Claude.app may genuinely exist on CI/dev)
    _orig_is_dir = type(tmp_path).is_dir

    def fake_is_dir(self) -> bool:  # type: ignore[no-untyped-def]
        if str(self) == "/Applications/Claude.app":
            return False
        return _orig_is_dir(self)

    monkeypatch.setattr(type(tmp_path), "is_dir", fake_is_dir)

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and args[0] == "pgrep":
            return CompletedProcess(args, 0, stdout="1234\n", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "running-process"


def test_desktop_macos_all_miss(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """macOS: all probes miss → installed=False."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))

    # Suppress probe 2 (/Applications/Claude.app may genuinely exist on CI/dev)
    _orig_is_dir = type(tmp_path).is_dir

    def fake_is_dir(self) -> bool:  # type: ignore[no-untyped-def]
        if str(self) == "/Applications/Claude.app":
            return False
        return _orig_is_dir(self)

    monkeypatch.setattr(type(tmp_path), "is_dir", fake_is_dir)

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_desktop_details()

    assert result.installed is False
    assert result.detected_via is None


def test_desktop_linux_config_dir_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Linux probe 1: ~/.config/Claude/ exists → detected_via='config-dir'."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("HOME", str(tmp_path))

    config_dir = tmp_path / ".config" / "Claude"
    config_dir.mkdir(parents=True)

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "config-dir"


def test_desktop_linux_desktop_file_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Linux probe 2: ~/.local/share/applications/claude.desktop → detected_via='desktop-file'."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("HOME", str(tmp_path))
    # No config dir — probe 1 misses

    # Patch Path.is_file to return True for the local desktop file
    _orig_is_file = type(tmp_path).is_file

    def fake_is_file(self) -> bool:  # type: ignore[no-untyped-def]
        if str(self).endswith("applications/claude.desktop"):
            return True
        return _orig_is_file(self)

    monkeypatch.setattr(type(tmp_path), "is_file", fake_is_file)

    result = src.installer._claude_desktop_details()

    assert result.installed is True
    assert result.detected_via == "desktop-file"


def test_desktop_linux_all_miss(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Linux: all probes miss → installed=False."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("HOME", str(tmp_path))
    # No config dir, no desktop file

    result = src.installer._claude_desktop_details()

    assert result.installed is False
    assert result.detected_via is None


# backward compat: _claude_desktop_detected() still returns bool
def test_desktop_detected_bool_still_returns_bool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """_claude_desktop_detected() must remain a bool-returning function for backward compat."""
    import sys  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))
    app_support = tmp_path / "Library" / "Application Support" / "Claude"
    app_support.mkdir(parents=True)

    result = src.installer._claude_desktop_detected()
    assert isinstance(result, bool)
    assert result is True


# ---------------------------------------------------------------------------
# Step 2.3 — Layered Claude Code CLI detection
# ---------------------------------------------------------------------------


def test_code_path_hit_no_regression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PATH probe: shutil.which('claude') hits → detected_via='path' (no regression)."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/local/bin/claude" if name == "claude" else None
    )

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and args[:2] == ["claude", "--version"]:
            return CompletedProcess(args, 0, stdout="2.1.114 (Claude Code)", stderr="")
        if isinstance(args, list) and args[0] == "/usr/local/bin/claude" and "--version" in args:
            return CompletedProcess(args, 0, stdout="2.1.114 (Claude Code)", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "path"
    assert result.version == "2.1.114"


def test_code_windows_installer_fallback_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 2: USERPROFILE\\.claude\\local\\claude.exe → 'installer-fallback'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("shutil.which", lambda name: None)  # PATH misses
    userprofile = tmp_path / "Users" / "idan"
    fallback_dir = userprofile / ".claude" / "local"
    fallback_dir.mkdir(parents=True)
    (fallback_dir / "claude.exe").write_text("fake")
    monkeypatch.setenv("USERPROFILE", str(userprofile))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "--version" in args:
            return CompletedProcess(args, 0, stdout="2.5.0 (Claude Code)", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "installer-fallback"


def test_code_macos_installer_fallback_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """macOS probe 2: ~/.claude/local/claude (PATH misses) → detected_via='installer-fallback'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setenv("HOME", str(tmp_path))
    fallback_dir = tmp_path / ".claude" / "local"
    fallback_dir.mkdir(parents=True)
    (fallback_dir / "claude").write_text("fake")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "--version" in args:
            return CompletedProcess(args, 0, stdout="2.5.0 (Claude Code)", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "installer-fallback"


def test_code_macos_alt_install_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """macOS/Linux probe 3: ~/.local/bin/claude found → detected_via='alt-install'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setenv("HOME", str(tmp_path))
    alt_dir = tmp_path / ".local" / "bin"
    alt_dir.mkdir(parents=True)
    (alt_dir / "claude").write_text("fake")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "--version" in args:
            return CompletedProcess(args, 0, stdout="2.5.0 (Claude Code)", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "alt-install"


def test_code_linux_npm_global_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Linux probe 4: npm global bin/claude found → detected_via='npm-global'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/npm" if name == "npm" else None)
    monkeypatch.setenv("HOME", str(tmp_path))

    npm_prefix = tmp_path / "npm-global"
    npm_bin = npm_prefix / "bin"
    npm_bin.mkdir(parents=True)
    (npm_bin / "claude").write_text("fake")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "npm" in args[0] and "config" in args:
            return CompletedProcess(args, 0, stdout=str(npm_prefix) + "\n", stderr="")
        if isinstance(args, list) and "--version" in args:
            return CompletedProcess(args, 0, stdout="2.5.0 (Claude Code)", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "npm-global"


def test_code_windows_npm_global_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 3: %APPDATA%\\npm\\claude.cmd found → detected_via='npm-global'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("shutil.which", lambda name: "/path/to/npm" if name == "npm" else None)
    appdata = tmp_path / "AppData" / "Roaming"
    npm_dir = appdata / "npm"
    npm_dir.mkdir(parents=True)
    (npm_dir / "claude.cmd").write_text("fake")
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "Users" / "idan"))

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "--version" in args:
            return CompletedProcess(args, 0, stdout="2.5.0 (Claude Code)", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "npm-global"


def test_code_windows_install_binary_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 4: LOCALAPPDATA\\Programs\\Claude\\claude.exe → 'install-binary'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("shutil.which", lambda name: None)
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    localappdata = tmp_path / "AppData" / "Local"
    binary_dir = localappdata / "Programs" / "Claude"
    binary_dir.mkdir(parents=True)
    (binary_dir / "claude.exe").write_text("fake")
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "Users" / "idan"))

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "--version" in args:
            return CompletedProcess(args, 0, stdout="2.5.0 (Claude Code)", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "install-binary"


def test_code_windows_tasklist_running_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 5: tasklist CSV 'claude.exe' (lowercase) → detected_via='running-process'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("shutil.which", lambda name: None)
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    localappdata = tmp_path / "AppData" / "Local"
    localappdata.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "Users" / "idan"))

    tasklist_output = '"Image Name","PID","Session Name"\r\n"claude.exe","5678","Console"\r\n'

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "tasklist" in args[0]:
            return CompletedProcess(args, 0, stdout=tasklist_output, stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    # winreg misses
    fake_winreg = type(
        "winreg",
        (),
        {
            "HKEY_CURRENT_USER": 0,
            "OpenKey": staticmethod(lambda *a, **kw: (_ for _ in ()).throw(OSError("no key"))),
        },
    )()
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "running-process"


def test_code_windows_registry_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Windows probe 6: winreg OpenKey Software\\Anthropic\\ClaudeCode → detected_via='registry'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("shutil.which", lambda name: None)
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    localappdata = tmp_path / "AppData" / "Local"
    localappdata.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "Users" / "idan"))

    # tasklist returns nothing
    tasklist_output = '"Image Name","PID"\r\n'

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "tasklist" in args[0]:
            return CompletedProcess(args, 0, stdout=tasklist_output, stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    class _FakeHandle:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    fake_winreg = type(
        "winreg",
        (),
        {
            "HKEY_CURRENT_USER": 0,
            "OpenKey": staticmethod(lambda *a, **kw: _FakeHandle()),
        },
    )()
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "registry"


def test_code_all_probes_miss(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """macOS/Linux: all probes miss → installed=False, detected_via=None."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setenv("HOME", str(tmp_path))

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_code_details()

    assert result.installed is False
    assert result.detected_via is None


def test_code_fallback_path_used_for_version_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """When installer-fallback hits, subprocess --version uses the absolute path, not 'claude'."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setenv("HOME", str(tmp_path))
    fallback_dir = tmp_path / ".claude" / "local"
    fallback_dir.mkdir(parents=True)
    fallback_bin = fallback_dir / "claude"
    fallback_bin.write_text("fake")

    version_calls: list[list[str]] = []

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and "--version" in args:
            version_calls.append(list(args))
            return CompletedProcess(args, 0, stdout="2.5.0 (Claude Code)", stderr="")
        return CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._claude_code_details()

    assert result.installed is True
    assert result.detected_via == "installer-fallback"
    assert len(version_calls) == 1, "expected exactly one --version subprocess call"
    # The first arg of the version call must be the absolute path, not bare 'claude'
    assert version_calls[0][0] == str(fallback_bin), (
        f"expected absolute path {fallback_bin!r} as first arg, got {version_calls[0][0]!r}"
    )


# backward compat: _detect_claude_code() still returns bool
def test_code_detected_bool_still_returns_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_detect_claude_code() must remain bool-returning for backward compat."""
    import sys  # noqa: PLC0415
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/local/bin/claude" if name == "claude" else None
    )

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        return CompletedProcess(args, 0, stdout="2.1.114 (Claude Code)", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = src.installer._detect_claude_code()
    assert isinstance(result, bool)
    assert result is True


def test_detection_parity() -> None:
    """_claude_code_details and _claude_desktop_details use overlapping probe-name vocabulary.

    Shared probe names used by BOTH functions (structural parity for --diagnose output):
      install-binary, running-process, registry

    Code-only (no Desktop equivalent):
      path, installer-fallback, alt-install, npm-global

    Desktop-only (no Code equivalent):
      config-dir, msix-package, desktop-file
    """
    import inspect  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    code_src = inspect.getsource(src.installer._claude_code_details)
    desktop_src = inspect.getsource(src.installer._claude_desktop_details)

    # Shared probes — must appear in BOTH
    shared_probes = ["install-binary", "running-process", "registry"]
    for probe in shared_probes:
        assert probe in code_src, f"probe name {probe!r} missing from _claude_code_details source"
        assert probe in desktop_src, (
            f"probe name {probe!r} missing from _claude_desktop_details source"
        )

    # Code-only probes
    code_only = ["path", "installer-fallback", "npm-global"]
    for probe in code_only:
        assert probe in code_src, f"probe name {probe!r} missing from _claude_code_details source"

    # Desktop-only probes
    desktop_only = ["config-dir", "msix-package", "desktop-file"]
    for probe in desktop_only:
        assert probe in desktop_src, (
            f"probe name {probe!r} missing from _claude_desktop_details source"
        )


# ---------------------------------------------------------------------------
# Phase 3 — OS-specific neither-detected exit message (plan-003, Step 3.1)
# TDD RED: tests written before OS-specific switch exists in _choose_clients().
# ---------------------------------------------------------------------------


def test_neither_detected_windows_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Windows: exit message mentions MS Store / Packaged App, --client, and --diagnose."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr("src.installer._detect_claude_code", lambda: False)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)
    monkeypatch.setattr("sys.platform", "win32")
    args = src.installer._build_parser().parse_args([])

    with pytest.raises(SystemExit) as exc_info:
        src.installer._choose_clients(args)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert "--client claude-desktop" in all_output, (
        "Windows message must mention --client claude-desktop override"
    )
    assert "--diagnose" in all_output, "Windows message must mention --diagnose for probe report"
    # MS Store / Packaged App installs are the common Windows detection miss
    assert "MS Store" in all_output or "Packaged App" in all_output, (
        "Windows message must mention MS Store or Packaged App install type"
    )


def test_neither_detected_macos_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """macOS: exit message mentions /Applications/Claude.app and --diagnose."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr("src.installer._detect_claude_code", lambda: False)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)
    monkeypatch.setattr("sys.platform", "darwin")
    args = src.installer._build_parser().parse_args([])

    with pytest.raises(SystemExit) as exc_info:
        src.installer._choose_clients(args)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert "/Applications/Claude.app" in all_output, (
        "macOS message must mention /Applications/Claude.app"
    )
    assert "--diagnose" in all_output, "macOS message must mention --diagnose for probe report"


def test_neither_detected_linux_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Linux: exit message mentions .desktop files and --diagnose."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr("src.installer._detect_claude_code", lambda: False)
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)
    monkeypatch.setattr("sys.platform", "linux")
    args = src.installer._build_parser().parse_args([])

    with pytest.raises(SystemExit) as exc_info:
        src.installer._choose_clients(args)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert ".desktop" in all_output, "Linux message must mention .desktop file paths"
    assert "--diagnose" in all_output, "Linux message must mention --diagnose for probe report"


# ---------------------------------------------------------------------------
# Phase 4, Step 4.1 — --verbose flag (plan-003)
# TDD RED: tests written before --verbose / _VERBOSE exist in installer.
# ---------------------------------------------------------------------------

_VERBOSE_ARGS = [
    "--dry-run",
    "--yes",
    "--client",
    "claude-code",
    "--scope",
    "user",
    "--url",
    "https://x.testrail.io",
    "--username",
    "u@x.com",
    "--api-key",
    "A" * 40,
    "--no-validate",
    "--verbose",
]

_NONVERBOSE_ARGS = [
    "--dry-run",
    "--yes",
    "--client",
    "claude-code",
    "--scope",
    "user",
    "--url",
    "https://x.testrail.io",
    "--username",
    "u@x.com",
    "--api-key",
    "A" * 40,
    "--no-validate",
]


def test_verbose_flag_in_help(capsys: pytest.CaptureFixture[str]) -> None:
    """--verbose must appear in --help output."""
    import src.installer  # noqa: PLC0415

    with pytest.raises(SystemExit):
        src.installer.main(["--help"])

    captured = capsys.readouterr()
    assert "--verbose" in (captured.out + captured.err), "--verbose missing from --help"


def test_verbose_flag_emits_desktop_probe_lines(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--verbose must emit [probe] lines for Claude Desktop detection probes.

    The detection functions themselves call _emit_probe() when _VERBOSE is True.
    We verify this by patching the desktop details function with one that calls
    _emit_probe (simulating what the real probe chain does when all probes miss).
    """
    import src.installer  # noqa: PLC0415

    def fake_desktop_details() -> src.installer._ClientDetection:
        # Simulate probe chain running with _VERBOSE=True: emit a probe miss
        src.installer._emit_probe("config-dir", hit=False)
        src.installer._emit_probe("install-binary", hit=False)
        return src.installer._ClientDetection(installed=False, label="Claude Desktop")

    def fake_code_details() -> src.installer._ClientDetection:
        src.installer._emit_probe("path", hit=True, path="/usr/local/bin/claude")
        return src.installer._ClientDetection(
            installed=True,
            label="Claude Code",
            path="/usr/local/bin/claude",
            detected_via="path",
        )

    monkeypatch.setattr("src.installer._claude_desktop_details", fake_desktop_details)
    monkeypatch.setattr("src.installer._claude_code_details", fake_code_details)
    # Do NOT mock the bool wrappers separately — they delegate to the detail functions
    # so that _detect_claude_code() → fake_code_details() and probe lines fire.

    verbose_desktop_args = [
        "--dry-run",
        "--yes",
        "--client",
        "claude-desktop",
        "--scope",
        "user",
        "--url",
        "https://x.testrail.io",
        "--username",
        "u@x.com",
        "--api-key",
        "A" * 40,
        "--no-validate",
        "--verbose",
    ]

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(verbose_desktop_args)

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert "[probe]" in all_output, "Expected [probe] lines in verbose output for Desktop detection"
    assert "config-dir" in all_output, "Expected config-dir probe name in verbose output"


def test_verbose_flag_emits_code_probe_lines(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--verbose must emit [probe] lines for Claude Code detection probes.

    The detection functions themselves call _emit_probe() when _VERBOSE is True.
    We verify by patching the code details function with one that calls _emit_probe.
    """
    import src.installer  # noqa: PLC0415

    def fake_code_details() -> src.installer._ClientDetection:
        # Simulate probe chain running with _VERBOSE=True: emit probe misses
        src.installer._emit_probe("path", hit=False)
        src.installer._emit_probe("installer-fallback", hit=False)
        return src.installer._ClientDetection(installed=False, label="Claude Code")

    def fake_desktop_details() -> src.installer._ClientDetection:
        src.installer._emit_probe("config-dir", hit=True, path="/home/user/.config/Claude")
        return src.installer._ClientDetection(
            installed=True,
            label="Claude Desktop",
            path="/home/user/.config/Claude",
            detected_via="config-dir",
        )

    monkeypatch.setattr("src.installer._claude_code_details", fake_code_details)
    monkeypatch.setattr("src.installer._claude_desktop_details", fake_desktop_details)
    # Do NOT mock the bool wrappers separately — they delegate to the detail functions
    # so that _claude_desktop_detected() → fake_desktop_details() and probe lines fire.

    verbose_code_args = [
        "--dry-run",
        "--yes",
        "--client",
        "claude-code",
        "--scope",
        "user",
        "--url",
        "https://x.testrail.io",
        "--username",
        "u@x.com",
        "--api-key",
        "A" * 40,
        "--no-validate",
        "--verbose",
    ]

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(verbose_code_args)

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert "[probe]" in all_output, "Expected [probe] lines in verbose output for Code detection"
    assert "path" in all_output, "Expected 'path' probe name in verbose output"


def test_verbose_flag_off_emits_no_probe_lines(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without --verbose, no [probe] lines should appear in output."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(
        "src.installer._claude_code_details",
        lambda: src.installer._ClientDetection(
            installed=True,
            label="Claude Code",
            path="/usr/local/bin/claude",
            detected_via="path",
        ),
    )
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr(
        "src.installer._claude_desktop_details",
        lambda: src.installer._ClientDetection(installed=False, label="Claude Desktop"),
    )
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(_NONVERBOSE_ARGS)

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert "[probe]" not in all_output, "No [probe] lines should appear without --verbose"


def test_verbose_with_dry_run_still_works(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--verbose combined with --dry-run must not regress dry-run behavior (exit 0)."""
    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(
        "src.installer._claude_code_details",
        lambda: src.installer._ClientDetection(
            installed=True,
            label="Claude Code",
            path="/usr/local/bin/claude",
            detected_via="path",
        ),
    )
    monkeypatch.setattr("src.installer._detect_claude_code", lambda: True)
    monkeypatch.setattr(
        "src.installer._claude_desktop_details",
        lambda: src.installer._ClientDetection(installed=False, label="Claude Desktop"),
    )
    monkeypatch.setattr("src.installer._claude_desktop_detected", lambda: False)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(_VERBOSE_ARGS)

    assert exc_info.value.code == 0, "--verbose + --dry-run must exit 0"


# ---------------------------------------------------------------------------
# Phase 4, Step 4.2 — --diagnose command (plan-003)
# TDD RED: tests written before _diagnose() / --diagnose exist in installer.
# ---------------------------------------------------------------------------


def _make_diagnose_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Apply standard mocks needed for --diagnose tests.

    Mocks out:
    - subprocess.run (for uv --version and detection probes)
    - _http_get (for network reachability probes)
    - _claude_code_details / _claude_desktop_details
    """
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(
        "src.installer._claude_code_details",
        lambda: src.installer._ClientDetection(
            installed=True,
            label="Claude Code",
            path="/usr/local/bin/claude",
            detected_via="path",
        ),
    )
    monkeypatch.setattr(
        "src.installer._claude_desktop_details",
        lambda: src.installer._ClientDetection(installed=False, label="Claude Desktop"),
    )

    def fake_subprocess_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if args and args[0] == "uv":
            return CompletedProcess(args, 0, stdout="uv 0.5.0 (abcdef1234 2026-01-01)\n", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_subprocess_run)

    def fake_http_get(url: str, **kwargs):  # type: ignore[no-untyped-def]
        resp = type("FakeResp", (), {"status_code": 200})()
        return resp

    monkeypatch.setattr("src.installer._http_get", fake_http_get)


def test_diagnose_exits_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--diagnose must exit 0 always (it's a report, not a gate)."""
    import src.installer  # noqa: PLC0415

    _make_diagnose_mocks(monkeypatch)
    monkeypatch.delenv("TESTRAIL_API_KEY", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(["--diagnose"])

    assert exc_info.value.code == 0


def test_diagnose_redacts_api_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--diagnose must never print the raw API key — only the redacted form."""
    import src.installer  # noqa: PLC0415

    raw_key = "S" * 40
    monkeypatch.setenv("TESTRAIL_API_KEY", raw_key)
    _make_diagnose_mocks(monkeypatch)

    with pytest.raises(SystemExit):
        src.installer.main(["--diagnose"])

    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert raw_key not in all_output, "Raw API key must never appear in --diagnose output"
    assert "***" in all_output, "Redacted form (***) must appear in --diagnose output"


def test_diagnose_includes_all_section_headers(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--diagnose output must include all 5 section headers."""
    import src.installer  # noqa: PLC0415

    _make_diagnose_mocks(monkeypatch)
    monkeypatch.delenv("TESTRAIL_API_KEY", raising=False)

    with pytest.raises(SystemExit):
        src.installer.main(["--diagnose"])

    captured = capsys.readouterr()
    all_output = captured.err + captured.out

    for header in ["System", "Environment", "Detection", "UV cache", "Network"]:
        assert header in all_output, f"Section header {header!r} missing from --diagnose output"


def test_diagnose_handles_network_timeout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--diagnose must continue and print 'unreachable' when network times out."""
    from subprocess import CompletedProcess  # noqa: PLC0415

    import src.installer  # noqa: PLC0415

    monkeypatch.setattr(
        "src.installer._claude_code_details",
        lambda: src.installer._ClientDetection(installed=False, label="Claude Code"),
    )
    monkeypatch.setattr(
        "src.installer._claude_desktop_details",
        lambda: src.installer._ClientDetection(installed=False, label="Claude Desktop"),
    )

    def fake_subprocess_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if args and args[0] == "uv":
            return CompletedProcess(args, 0, stdout="uv 0.5.0\n", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_subprocess_run)

    import httpx  # noqa: PLC0415

    def raising_http_get(url: str, **kwargs):  # type: ignore[no-untyped-def]
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("src.installer._http_get", raising_http_get)
    monkeypatch.delenv("TESTRAIL_API_KEY", raising=False)
    monkeypatch.delenv("TESTRAIL_URL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(["--diagnose"])

    assert exc_info.value.code == 0, "--diagnose must exit 0 even on network timeout"
    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert "unreachable" in all_output.lower() or "timeout" in all_output.lower(), (
        "--diagnose must report unreachable/timeout, not crash"
    )


def test_diagnose_handles_uv_cache_unwritable(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--diagnose must report write-test FAILED when cache dir is unwritable.

    Simulate an unwritable cache dir by patching tempfile.mkstemp to raise
    PermissionError, which is what happens when the dir is locked by OneDrive
    or Windows Defender (the real-world failure mode from plan-003).
    """
    import src.installer  # noqa: PLC0415

    _make_diagnose_mocks(monkeypatch)
    monkeypatch.delenv("TESTRAIL_API_KEY", raising=False)
    monkeypatch.setenv("UV_CACHE_DIR", "/nonexistent/uvcache")

    # Patch tempfile.mkstemp (the seam used by _diagnose's write-test) to raise PermissionError.
    # _make_diagnose_mocks patches subprocess.run so no real subprocess runs, meaning the
    # only mkstemp call in the test scope comes from _diagnose()'s UV cache write-test section.
    def _raising_mkstemp(*args: object, **kwargs: object) -> None:
        raise PermissionError("Access denied to cache dir")

    monkeypatch.setattr("tempfile.mkstemp", _raising_mkstemp)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(["--diagnose"])

    assert exc_info.value.code == 0, "--diagnose must exit 0 even when write-test fails"
    captured = capsys.readouterr()
    all_output = captured.err + captured.out
    assert "FAILED" in all_output or "failed" in all_output.lower(), (
        "--diagnose write-test must report FAILED when unwritable"
    )


def test_diagnose_short_circuits_wizard(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--diagnose must not call any writer, ping, or prompt — wizard is short-circuited."""
    import src.installer  # noqa: PLC0415

    write_calls: list[str] = []

    def track_write_cli(*args, **kwargs):  # type: ignore[no-untyped-def]
        write_calls.append("cli")
        raise AssertionError("_write_claude_code_via_cli must not be called under --diagnose")

    def track_write_json(*args, **kwargs):  # type: ignore[no-untyped-def]
        write_calls.append("json")
        raise AssertionError("_write_claude_code_via_json must not be called under --diagnose")

    def track_write_desktop(*args, **kwargs):  # type: ignore[no-untyped-def]
        write_calls.append("desktop")
        raise AssertionError("_write_claude_desktop must not be called under --diagnose")

    def track_ping(*args, **kwargs):  # type: ignore[no-untyped-def]
        write_calls.append("ping")
        raise AssertionError("_ping_testrail must not be called under --diagnose")

    monkeypatch.setattr("src.installer._write_claude_code_via_cli", track_write_cli)
    monkeypatch.setattr("src.installer._write_claude_code_via_json", track_write_json)
    monkeypatch.setattr("src.installer._write_claude_desktop", track_write_desktop)
    monkeypatch.setattr("src.installer._ping_testrail", track_ping)

    _make_diagnose_mocks(monkeypatch)
    monkeypatch.delenv("TESTRAIL_API_KEY", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        src.installer.main(["--diagnose"])

    assert exc_info.value.code == 0
    assert not write_calls, f"Unexpected calls under --diagnose: {write_calls}"
