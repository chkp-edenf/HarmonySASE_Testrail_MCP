# TestRail MCP Server

**Connect AI assistants to your TestRail instance via the Model Context Protocol**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)]()
[![MCP Protocol](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)]()

> Talk to your AI assistant about test cases, and watch it create, update, and manage them in TestRail — all through natural conversation.

---

## Highlights

- **15 Consolidated Tools** covering 65+ operations across 12 resource categories
- **Attachment Support** — upload screenshots and files to cases, results, runs, plans
- **100% Portable** — works with ANY TestRail instance (no hardcoded custom fields)
- **Smart Field Handling** — say "Regression" instead of memorizing numeric IDs
- **Auto Rate-Limited** — built-in throttling (180 req/min) protects your API quota
- **Zero Setup Friction** — one `uvx` command, no Docker required

---

## Quick Install (Wizard)

One-liner installers that detect your AI client, prompt for your TestRail credentials, optionally validate them, and write the MCP config for you — backing up any existing config first. Non-interactive mode available via flags.

**macOS / Linux**
```sh
curl -LsSf https://raw.githubusercontent.com/chkp-edenf/HarmonySASE_Testrail_MCP/main/install.sh | sh
```

**Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/chkp-edenf/HarmonySASE_Testrail_MCP/main/install.ps1 | iex
```

The wizard walks you through picking Claude Code / Claude Desktop / both, entering the TestRail URL + login + API key, and writes the config.

> **Prefer manual config?** The step-by-step Quick Start below still works — the wizard is optional.

---

## Quick Start

### 1. Get Your TestRail API Key

1. Log in to TestRail → click your avatar → **My Settings**
2. Scroll to **API Keys** → click **Add Key**
3. Copy the key (you won't see it again)

### 2. Configure Your AI Client

Add this to your MCP client configuration:

```json
{
  "mcpServers": {
    "testrail": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git", "testrail-mcp"],
      "env": {
        "TESTRAIL_URL": "https://your-instance.testrail.io",
        "TESTRAIL_USERNAME": "your-email@company.com",
        "TESTRAIL_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Replace** the three env values with your TestRail credentials.

| AI Client | Config File Location |
|-----------|---------------------|
| **Claude Code** | `.mcp.json` in your project root, or `~/.claude/mcp.json` globally |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |
| **VS Code (Copilot)** | `~/.vscode/mcp.json` or workspace `.vscode/mcp.json` |
| **Cursor** | Cursor Settings → MCP Servers |

### 3. Test It

Ask your AI:
```
"Get all TestRail projects"
```

If you see your projects list, you're ready.

### 4. Warm the Cache (Important)

Before creating or updating test cases, run these to populate metadata caches:

```
"Get case fields from TestRail"
"Get statuses from TestRail"
```

This enables natural language field values (e.g., "High" instead of priority ID 2).

---

## Available Tools

**15 consolidated action-based tools:**

| Tool | Actions | Description |
|------|---------|-------------|
| `testrail_projects` | list, get | Project discovery and details |
| `testrail_suites` | list, get, add, update, delete | Test suite management |
| `testrail_sections` | list, get, add, update, delete, move | Section/folder organization |
| `testrail_cases` | list, get, get_by_ids, add, update, delete, history, bulk_update, bulk_delete, copy_to_section, move_to_section | Test case management (11 actions) |
| `testrail_tests` | list, get | Test instances in runs |
| `testrail_runs` | list, get, add, update, close, delete | Test run management |
| `testrail_plans` | list, get, add, update, close, delete | Test plan management |
| `testrail_plan_entries` | add, update, delete | Plan entry management |
| `testrail_results` | get_for_test, get_for_case, get_for_run, add_for_test, add_for_case, bulk_add_for_tests, bulk_add_for_cases | Result submission and querying |
| `testrail_milestones` | list, get, add, update, delete | Milestone management |
| `testrail_users` | list, get, get_by_email | User lookup |
| `testrail_configs` | list_groups, add_group, add_config | Multi-platform configs |
| `testrail_metadata` | case_fields, case_types, priorities, statuses, templates | Reference data discovery |
| `testrail_attachments` | upload, list, get, delete | File/image attachments |
| `testrail_health` | *(standalone)* | Server health monitoring |

Each tool uses an `action` parameter to select the operation.

---

## Usage Examples

### Creating Test Cases

```
You: "Create 5 test cases in section 'API Tests' for the User Registration endpoint"
AI: Creates 5 cases with auto-generated titles — done in seconds.
```

### Smart Custom Fields

```
You: "Create a test case with priority High, type Regression, platform Mac"
AI: Automatically converts names to IDs using the cached metadata.
```

### Bulk Operations

```
You: "Update all test cases in suite 3 to priority Critical"
AI: Fetches cases, then bulk-updates in one API call.
```

### Uploading Screenshots to Test Cases

```
You: "Upload this screenshot to test case 12345 and add it to the expected result"
AI: 1. Uploads via testrail_attachments
    2. Updates the step's expected result with an HTML <img> tag
```

**Important:** TestRail rich text fields use HTML. To embed uploaded images, use:
```html
<img src="index.php?/attachments/get/{attachment_id}" />
```

### Analyzing Results

```
You: "Show me all failed tests from test run 142"
AI: Queries results, formats as a readable table.
```

---

## Architecture

```
┌─────────────────┐
│   AI Assistant   │  (Claude Code, Claude Desktop, VS Code, Cursor)
└────────┬─────────┘
         │ MCP Protocol (stdio JSON-RPC)
┌────────▼─────────┐
│   MCP Server     │  (This project — runs via uvx)
│   15 Tools       │
└────────┬─────────┘
         │ HTTPS + Basic Auth
┌────────▼─────────┐
│  TestRail API v2 │  (Your TestRail instance)
└──────────────────┘
```

**Three-layer design:**
- **Client Layer** (`src/client/api/`) — HTTP client with auth, rate limiting, retry, file upload
- **Server Layer** (`src/server/api/`) — MCP tool handlers, caches, rate limiter
- **Shared Layer** (`src/shared/schemas/`) — Pydantic validation models

**Four independent caches** (24h TTL, in-memory):
- Field Cache — custom field name→ID mappings
- Status Cache — test status name→ID mappings
- Priority Cache — priority name→ID mappings
- Case Type Cache — case type name→ID mappings

---

## Security

- **No hardcoded credentials** — environment variables only
- **No persistent storage** — caches are in-memory, cleared on restart
- **Rate limiting** — 180 req/min prevents API quota exhaustion
- **Input validation** — Pydantic schemas validate all inputs
- **Attachment security** — blocked sensitive paths (.ssh, .env, credentials), allowed file types only
- **Never commit credentials** — use `.env` files or MCP client env config

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TESTRAIL_URL` | Yes | Your TestRail instance URL (e.g., `https://your-instance.testrail.io`) |
| `TESTRAIL_USERNAME` | Yes | Your TestRail login email |
| `TESTRAIL_API_KEY` | Yes | API key from TestRail My Settings |

---

## Development (Running from Source)

For local development, point uvx to the local repo:

```json
{
  "mcpServers": {
    "testrail": {
      "command": "uvx",
      "args": ["--from", "/path/to/local/repo", "testrail-mcp"],
      "env": {
        "TESTRAIL_URL": "https://your-instance.testrail.io",
        "TESTRAIL_USERNAME": "your-email@company.com",
        "TESTRAIL_API_KEY": "your-api-key"
      }
    }
  }
}
```

**After code changes:** clear the uvx cache and restart the MCP server:
```bash
uv cache clean harmonysase-testrail-mcp --force
```

---

## Troubleshooting

### "Connection Error" or server fails to start
1. Verify your TestRail URL, username, and API key are correct
2. Ensure your TestRail instance is reachable from your machine
3. Check that `uvx` is installed: `uvx --version`

### "Missing required fields" when creating test cases
Run `testrail_metadata` (action: `case_fields`) to populate the cache first.

### Custom field values not recognized
1. Run `testrail_metadata` (action: `case_fields`) to see valid values
2. Check spelling — the system converts to lowercase for matching
3. Use numeric IDs as fallback

### Changes to MCP server code not taking effect
The uvx cache needs clearing:
```bash
uv cache clean harmonysase-testrail-mcp --force
```
Then restart the MCP connection in your AI client.

---

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** — Complete setup and usage guide
- **[CLAUDE.md](CLAUDE.md)** — AI assistant guidance for this codebase

---

## Acknowledgments

- Built on the [Model Context Protocol](https://modelcontextprotocol.io) by Anthropic
- Integrates with [TestRail REST API v2](https://www.gurock.com/testrail/docs/api)

---

**Ready to supercharge your TestRail workflow?** → [Get Started](#quick-start)
