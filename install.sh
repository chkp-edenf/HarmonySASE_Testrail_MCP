#!/bin/sh
# TestRail MCP Server — one-liner wizard installer (macOS / Linux).
#
# Usage (curl-bash):
#   curl -LsSf https://raw.githubusercontent.com/chkp-edenf/HarmonySASE_Testrail_MCP/main/install.sh | sh
#
# Usage (local, with flags):
#   sh install.sh --client claude-code --scope user --dry-run
#
# Env vars (all optional):
#   TESTRAIL_MCP_REF    git ref to install from (default: main).
#   TESTRAIL_API_KEY    TestRail API key — set this before running to avoid
#                       shell-history leak (the installer reads it automatically).
#   TESTRAIL_URL        TestRail URL — same rationale.
#   TESTRAIL_USERNAME   TestRail login.
#
# Behavior:
#   1. Ensure `uv` is installed (from astral.sh). Prompts for consent if missing.
#   2. Exec `uvx --from git+<repo>@<ref> testrail-mcp-install "$@"` (forwards flags).
#
# Exit codes:
#   0   installer completed
#   1   uv install failed OR user declined uv install
#
# Notes:
#   POSIX-sh compatible. No bashisms. Minimum uv: 0.4.x (any release with `uvx`).

set -eu

REPO_URL="https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git"
DEFAULT_REF="main"
REF="${TESTRAIL_MCP_REF:-$DEFAULT_REF}"

log()  { printf '[install.sh] %s\n' "$*" >&2; }
die()  { printf '[install.sh] ERROR: %s\n' "$*" >&2; exit 1; }

# When invoked via `curl ... | sh`, stdin is the pipe from curl — already at EOF
# by the time we'd try to prompt. Reading from /dev/tty bypasses this and talks
# to the real terminal. Env var TESTRAIL_MCP_AUTO_YES=1 skips the consent prompt
# entirely (for CI / unattended installs).
tty_available() {
    # Test `-r /dev/tty` passes on macOS even when open(2) would fail. Actually
    # try to open it for reading; silence the error and surface via exit code.
    ( : < /dev/tty ) 2>/dev/null
}

prompt_consent() {
    if [ "${TESTRAIL_MCP_AUTO_YES:-}" = "1" ]; then
        return 0
    fi
    if ! tty_available; then
        die "Cannot prompt for consent — no terminal attached. Install uv manually (https://docs.astral.sh/uv/getting-started/installation/) then re-run, or re-run with TESTRAIL_MCP_AUTO_YES=1."
    fi
    printf '[install.sh] Proceed with uv install? [y/N] ' >/dev/tty
    read -r reply </dev/tty
    case "$reply" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) die "uv install declined. See https://docs.astral.sh/uv/getting-started/installation/" ;;
    esac
}

if ! command -v uv >/dev/null 2>&1; then
    log "uv is not installed. It is required to run the wizard."
    log "uv will be installed via the official astral.sh script."
    prompt_consent
    curl -LsSf https://astral.sh/uv/install.sh | sh </dev/null || die "uv install failed."
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv >/dev/null 2>&1 || die "uv installed but not on PATH. Open a new shell and retry."
    log "uv installed: $(uv --version)"
fi

log "Running TestRail MCP wizard from git+${REPO_URL}@${REF}"
# Rebind stdin to /dev/tty so the wizard's input()/getpass.getpass() prompts
# reach the user's terminal even under `curl ... | sh`. If there's no TTY (CI),
# the wizard will fail at the first prompt unless all credentials are passed
# via flags or env vars (TESTRAIL_URL / TESTRAIL_USERNAME / TESTRAIL_API_KEY).
if tty_available; then
    exec uvx --from "git+${REPO_URL}@${REF}" testrail-mcp-install "$@" </dev/tty
else
    exec uvx --from "git+${REPO_URL}@${REF}" testrail-mcp-install "$@"
fi
