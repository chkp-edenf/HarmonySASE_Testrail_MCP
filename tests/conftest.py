"""Shared pytest fixtures for installer tests.

Fixtures:
- fake_claude_cli      — patches shutil.which + subprocess.run; captures invocation args.
- fake_claude_desktop_config — parametrized across 4 config states (missing/empty/preserves_other/malformed).
- fake_prompts         — replaces builtins.input + getpass.getpass with a FIFO queue.
- fake_testrail_ping   — patches src.installer._http_get seam; stub raises NotImplementedError
                         until Step 6.1 wires a real implementation.
"""
from __future__ import annotations

import builtins
import collections
import getpass
import json
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Module-level state reset (kody WARN — avoid --verbose bleeding between tests)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_installer_module_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset module-level flags in src.installer between tests.

    `_VERBOSE` is written by main() when --verbose is passed. Without this
    reset, a test that invokes main() with --verbose would leave the flag
    True for any subsequent test calling probe helpers directly. All Phase 4
    tests go through main() so current order is safe, but this guards against
    a future direct-call unit test seeing spurious `[probe]` output.
    """
    try:
        import src.installer as _installer_mod  # noqa: PLC0415
    except ImportError:
        return
    monkeypatch.setattr(_installer_mod, "_VERBOSE", False, raising=False)


# ---------------------------------------------------------------------------
# fake_claude_cli
# ---------------------------------------------------------------------------

class _FakeClaude:
    """Helper returned by fake_claude_cli; tests inspect .calls."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.present: bool = True
        self.version_returncode: int = 0
        self.mcp_add_returncode: int = 0
        self.mcp_add_stdout: str = ""
        self.mcp_add_stderr: str = ""

    def which_side_effect(self, name: str) -> str | None:
        if name == "claude":
            return "/usr/local/bin/claude" if self.present else None
        return None  # passthrough for other tools

    def run_side_effect(self, args: list[str], **kwargs: Any) -> CompletedProcess:  # type: ignore[type-arg]
        self.calls.append(list(args))
        if args[:2] == ["claude", "--version"]:
            return CompletedProcess(args, self.version_returncode, stdout="2.1.114 (Claude Code)", stderr="")
        if len(args) >= 3 and args[:3] == ["claude", "mcp", "add"]:
            return CompletedProcess(
                args,
                self.mcp_add_returncode,
                stdout=self.mcp_add_stdout,
                stderr=self.mcp_add_stderr,
            )
        return CompletedProcess(args, 0, stdout="", stderr="")


@pytest.fixture()
def fake_claude_cli(monkeypatch: pytest.MonkeyPatch) -> _FakeClaude:
    """Monkey-patch shutil.which and subprocess.run for claude CLI simulation."""
    helper = _FakeClaude()
    monkeypatch.setattr("shutil.which", helper.which_side_effect)
    monkeypatch.setattr("subprocess.run", helper.run_side_effect)
    return helper


# ---------------------------------------------------------------------------
# fake_claude_desktop_config
# ---------------------------------------------------------------------------

_OTHER_MCP = {"command": "echo", "args": ["x"]}

@pytest.fixture(
    params=["missing", "empty", "preserves_other", "malformed"],
    ids=["missing", "empty", "preserves_other", "malformed"],
)
def fake_claude_desktop_config(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    """Return a Path inside tmp_path representing the desktop config in 4 states."""
    config_path = tmp_path / "claude_desktop_config.json"
    state: str = request.param

    if state == "missing":
        pass  # file intentionally absent
    elif state == "empty":
        config_path.write_text(json.dumps({"mcpServers": {}}))
    elif state == "preserves_other":
        config_path.write_text(json.dumps({"mcpServers": {"other": _OTHER_MCP}}))
    elif state == "malformed":
        config_path.write_text("not-json-at-all")

    return config_path


# ---------------------------------------------------------------------------
# fake_prompts
# ---------------------------------------------------------------------------

class _FakePrompts:
    """FIFO queue replacing builtins.input and getpass.getpass."""

    def __init__(self) -> None:
        self._queue: collections.deque[str] = collections.deque()

    def push(self, value: str) -> None:
        self._queue.append(value)

    def _pop(self, *args: Any, **kwargs: Any) -> str:
        if not self._queue:
            raise AssertionError("fake_prompts queue exhausted — more prompts fired than expected")
        return self._queue.popleft()

    def assert_exhausted(self) -> None:
        remaining = list(self._queue)
        if remaining:
            raise AssertionError(f"fake_prompts queue not exhausted; unused values: {remaining}")


@pytest.fixture()
def fake_prompts(monkeypatch: pytest.MonkeyPatch) -> _FakePrompts:
    """Replace builtins.input and getpass.getpass with a FIFO queue."""
    helper = _FakePrompts()
    monkeypatch.setattr(builtins, "input", helper._pop)
    monkeypatch.setattr(getpass, "getpass", helper._pop)
    yield helper
    helper.assert_exhausted()


# ---------------------------------------------------------------------------
# fake_testrail_ping
# ---------------------------------------------------------------------------
# Step 6.1 extension: replaced the _NotImplementedPing stub with a configurable
# helper that supports:
#   fake_testrail_ping.push(status_code=200)      — queue a successful HTTP response
#   fake_testrail_ping.push(exception=ConnectError("refused"))  — queue an exception
# Each push() enqueues one response; _http_get pops from the queue on each call.
# Queue exhaustion raises AssertionError (same pattern as _FakePrompts).
# ---------------------------------------------------------------------------

class _FakeHttpGet:
    """Configurable _http_get seam for testing _ping_testrail (Step 6.1)."""

    def __init__(self) -> None:
        self._queue: collections.deque[Any] = collections.deque()
        self.calls: list[tuple[str, dict]] = []  # (url, kwargs) per call

    def push(
        self,
        *,
        status_code: int | None = None,
        exception: BaseException | None = None,
    ) -> None:
        """Enqueue one response.  Exactly one of status_code or exception must be set."""
        if (status_code is None) == (exception is None):
            raise ValueError("push() requires exactly one of status_code or exception")
        if exception is not None:
            self._queue.append(("exc", exception))
        else:
            self._queue.append(("resp", status_code))

    def __call__(self, url: str, **kwargs: Any) -> Any:
        self.calls.append((url, kwargs))
        if not self._queue:
            raise AssertionError(
                "fake_testrail_ping queue exhausted — more _http_get calls than expected"
            )
        kind, payload = self._queue.popleft()
        if kind == "exc":
            raise payload  # type: ignore[misc]
        # Return a minimal response-like object with status_code
        return type("FakeResponse", (), {"status_code": payload})()

    def assert_exhausted(self) -> None:
        remaining = list(self._queue)
        if remaining:
            raise AssertionError(
                f"fake_testrail_ping queue not exhausted; unused items: {remaining}"
            )


@pytest.fixture()
def fake_testrail_ping(monkeypatch: pytest.MonkeyPatch) -> _FakeHttpGet:
    """Patch src.installer._http_get with a configurable queue-based fake.

    Step 6.1: replaced the NotImplementedError stub with a real helper.
    Usage in tests:
        fake_testrail_ping.push(status_code=200)
        fake_testrail_ping.push(exception=httpx.ConnectError("refused"))
    """
    helper = _FakeHttpGet()
    try:
        import src.installer as installer_mod  # noqa: PLC0415
        monkeypatch.setattr(installer_mod, "_http_get", helper)
    except (ImportError, AttributeError):
        # installer doesn't exist yet — fixture still valid, applied lazily
        pass
    yield helper
    # Note: we don't call assert_exhausted() here because tests that use inline
    # monkeypatch (not fake_testrail_ping) to control _http_get may not push anything.
    # Tests that DO use fake_testrail_ping should call .assert_exhausted() explicitly
    # if they need that guarantee.
