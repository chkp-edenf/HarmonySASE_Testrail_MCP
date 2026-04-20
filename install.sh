#!/bin/sh
# TestRail MCP Server — one-liner wizard installer (macOS / Linux).
#
# Usage (curl-bash):
#   curl -LsSf https://raw.githubusercontent.com/<your-org>/<your-repo>/main/install.sh | sh
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

REPO_URL="https://github.com/<your-org>/<your-repo>.git"
DEFAULT_REF="main"
REF="${TESTRAIL_MCP_REF:-$DEFAULT_REF}"

log()  { printf '[install.sh] %s\n' "$*" >&2; }
die()  { printf '[install.sh] ERROR: %s\n' "$*" >&2; exit 1; }

if ! command -v uv >/dev/null 2>&1; then
    log "uv is not installed. It is required to run the wizard."
    log "uv will be installed via the official astral.sh script."
    printf '[install.sh] Proceed with uv install? [y/N] ' >&2
    read -r reply
    case "$reply" in
        [yY]|[yY][eE][sS]) ;;
        *) die "uv install declined. See https://docs.astral.sh/uv/getting-started/installation/ for manual install." ;;
    esac
    curl -LsSf https://astral.sh/uv/install.sh | sh || die "uv install failed."
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv >/dev/null 2>&1 || die "uv installed but not on PATH. Open a new shell and retry."
    log "uv installed: $(uv --version)"
fi

log "Running TestRail MCP wizard from git+${REPO_URL}@${REF}"
exec uvx --from "git+${REPO_URL}@${REF}" testrail-mcp-install "$@"
