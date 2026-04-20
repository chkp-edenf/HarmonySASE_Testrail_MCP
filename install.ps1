# TestRail MCP Server — one-liner wizard installer (Windows).
#
# Usage (irm-iex):
#   irm https://raw.githubusercontent.com/<your-org>/<your-repo>/main/install.ps1 | iex
#
# Usage (local, with flags):
#   .\install.ps1 --client claude-desktop --scope user --dry-run
#
# If PowerShell blocks script execution for this session:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#
# Env vars (all optional):
#   $env:TESTRAIL_MCP_REF    git ref to install from (default: main).
#   $env:TESTRAIL_API_KEY    TestRail API key — set before running to avoid
#                            shell-history leak (the installer reads it automatically).
#   $env:TESTRAIL_URL        TestRail URL.
#   $env:TESTRAIL_USERNAME   TestRail login.
#
# Minimum uv version: 0.4.x (any release with `uvx`).

$ErrorActionPreference = 'Stop'

$RepoUrl = 'https://github.com/<your-org>/<your-repo>.git'
$DefaultRef = 'main'
$Ref = if ($env:TESTRAIL_MCP_REF) { $env:TESTRAIL_MCP_REF } else { $DefaultRef }

function Write-Log([string]$Message) {
    Write-Host "[install.ps1] $Message" -ForegroundColor Cyan
}
function Write-Fail([string]$Message) {
    Write-Host "[install.ps1] ERROR: $Message" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Log 'uv is not installed. It is required to run the wizard.'
    Write-Log 'uv will be installed via the official astral.sh script.'
    $reply = Read-Host '[install.ps1] Proceed with uv install? [y/N]'
    if ($reply -notmatch '^(y|Y|yes|YES)$') {
        Write-Fail 'uv install declined. See https://docs.astral.sh/uv/getting-started/installation/ for manual install.'
    }
    try {
        Invoke-Expression (Invoke-RestMethod -UseBasicParsing -Uri 'https://astral.sh/uv/install.ps1')
    } catch {
        Write-Fail "uv install failed: $_"
    }
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Fail 'uv installed but not on PATH. Open a new shell and retry.'
    }
    Write-Log "uv installed: $(uv --version)"
}

Write-Log "Running TestRail MCP wizard from git+${RepoUrl}@${Ref}"
& uvx --from "git+${RepoUrl}@${Ref}" testrail-mcp-install @args
exit $LASTEXITCODE
