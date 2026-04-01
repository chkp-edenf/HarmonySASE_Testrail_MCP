# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TestRail MCP Server v2.0.0 - A Model Context Protocol server that connects AI assistants to TestRail instances, providing 15 consolidated action-based tools covering all TestRail API v2 operations. This server enables AI assistants to create, read, update, and delete TestRail resources through natural conversation.

**Key Capabilities:**
- 15 consolidated MCP tools (action-based) covering 65+ operations across 12 resource categories
- Attachment support - upload screenshots and files to cases, results, runs, plans
- 100% portable - works with any TestRail instance (no hardcoded custom fields)
- Smart field handling - automatic conversion between human-readable names and numeric IDs
- Auto rate-limited - 180 req/min with token bucket algorithm
- Four independent in-memory caches (24h TTL) for metadata
- Installed via `uvx` (no Docker required)

## Development Commands

### Running (via uvx from local source)
```bash
# Configure in .mcp.json (or your AI client's MCP config):
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

# After code changes, clear uvx cache:
uv cache clean testrail-mcp --force
# Then restart the MCP connection in your AI client
```

## Architecture

**Three-Layer Design:**

1. **Client Layer** (`src/client/api/`)
   - `base_client.py` - HTTP client with auth, rate limiting, retry logic
   - Resource-specific clients: `cases.py`, `runs.py`, `plans.py`, etc.
   - Persistent HTTP connection reused across requests
   - Automatic retry with exponential backoff (GET requests only): 1s → 2s → 4s

2. **Server Layer** (`src/server/api/`)
   - `stdio.py` - Entry point, MCP server initialization
   - `tools.py` - 15 consolidated action-based tool definitions
   - Tool handlers: `cases.py`, `runs.py`, `plans.py`, etc.
   - `rate_limiter.py` - Token bucket (180 req/min)
   - Four cache modules: `field_cache.py`, `status_cache.py`, `priority_cache.py`, `case_type_cache.py`
   - `health.py` - Server health monitoring and cache status
   - `metrics.py` - Request/cache metrics tracking

3. **Shared Layer** (`src/shared/schemas/`)
   - Pydantic models for validation: `cases.py`, `runs.py`, `results.py`, etc.
   - Ensures type safety and request validation

**Entry Point Flow (stdio):**
```
stdio.py → validates env vars → normalizes TestRail URL →
creates TestRailClient with rate_limiter → registers tools →
routes tool calls to handlers
```


## Critical Implementation Patterns

### Cache Warming
**IMPORTANT:** Always populate caches before operations requiring field lookups:

```python
# Cache population sequence
1. get_case_fields     # Populates field_cache, priority_cache, case_type_cache
2. get_statuses        # Populates status_cache
```

The four independent caches:
- **Field Cache** - Custom field name→ID mappings and required fields
- **Status Cache** - Test status name→ID mappings (Passed, Failed, etc.)
- **Priority Cache** - Priority name→ID mappings (Critical, High, Medium, Low)
- **Case Type Cache** - Case type name→ID mappings (Functional, Automated, etc.)

Cache TTL: 24 hours in-memory, cleared on container restart.

### Custom Field Handling
The server automatically converts human-readable field names to TestRail IDs:

```python
# User provides: {"test_phase": "Regression", "platforms": "Win,Mac"}
# Server converts to: {"custom_test_phase": 123, "custom_platforms": "Win,Mac"}
```

This portability design means NO hardcoded custom field IDs.

### Rate Limiting
Token bucket algorithm enforces 180 req/min:
- Auto-applied to all API requests
- No configuration needed
- Prevents TestRail API quota exhaustion

### URL Normalization
TestRail uses non-standard URL format:
```
https://instance.testrail.io/index.php?/api/v2/endpoint&param1=val1&param2=val2
```

The server normalizes URLs automatically in `stdio.py` and `base_client.py`.

## Tool Organization

**15 consolidated action-based tools across 12 categories:**

| Tool | Actions | Description |
|------|---------|-------------|
| `testrail_projects` | list, get | Project discovery and details |
| `testrail_suites` | list, get, add, update, delete | Test suite CRUD |
| `testrail_sections` | list, get, add, update, delete, move | Section management |
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

**Tool Pattern:** Each tool uses an `action` parameter to select the operation. All tools include action-specific required field validation with clear error messages.

**Tool Discovery:** Descriptions include ACTIONS listing with per-action required/optional parameters, TIPS, and cross-references to related tools.

## Environment Variables

**Required:**
- `TESTRAIL_URL` - TestRail instance URL (e.g., https://company.testrail.io)
- `TESTRAIL_USERNAME` - Login email
- `TESTRAIL_API_KEY` - API key from TestRail My Settings

**Validation:** `validate_environment()` in `stdio.py` checks all required vars at startup.

## Error Handling

Custom exception hierarchy in `src/client/api/exceptions.py`:
- `TestRailError` - Base exception
- `TestRailAPIError` - API errors (400-599)
- `TestRailAuthenticationError` - 401
- `TestRailPermissionError` - 403
- `TestRailNotFoundError` - 404
- `TestRailRateLimitError` - 429
- `TestRailServerError` - 500+
- `TestRailTimeoutError` - Request timeout
- `TestRailNetworkError` - Network issues

Retry logic (v1.4.0): Automatic retry with exponential backoff for GET requests on transient failures.

## Filtering and Pagination

Most GET tools support comprehensive filtering:
- **API-supported filters:** priority_id, type_id, milestone_id, created_by, is_completed, etc.
- **Date filters:** created_after, created_before (Unix timestamp or ISO 8601)
- **Pagination:** limit/offset for result sets

Example: `get_cases` with filters:
```json
{
  "project_id": "1",
  "suite_id": "5872",
  "priority_id": [1, 2],
  "created_after": "2024-01-01T00:00:00Z",
  "limit": 100,
  "offset": 0
}
```

## Common Development Tasks

### Adding a New Action to an Existing Tool
1. Add the action to the tool's `enum` list in `src/server/api/tools.py`
2. Add any new properties to the tool's `inputSchema`
3. Add the action handler in `src/server/api/<resource>.py`
4. Add routing in the dispatcher function (`handle_testrail_<resource>`)
5. Add client method in `src/client/api/<resource>.py` if needed

### Adding a New Tool (New Resource)
1. Create client in `src/client/api/<resource>.py`
2. Register client in `src/client/api/__init__.py` (TestRailClient.__init__)
3. Create handler with dispatcher in `src/server/api/<resource>.py`
4. Define Tool() in `src/server/api/tools.py`
5. Register dispatcher in `src/server/api/__init__.py`
6. Create Pydantic schemas in `src/shared/schemas/<resource>.py`

### Debugging
1. Verify cache population: Call `testrail_health`
2. Warm caches: Call `testrail_metadata` with actions: case_fields, statuses
3. Clear caches: Restart the MCP server connection
4. Clear uvx cache after code changes: `uv cache clean testrail-mcp --force`

## Key Files Reference

**Core Server:**
- `src/stdio.py` - Entry point (stdio mode)
- `src/server/api/tools.py` - 15 consolidated tool definitions
- `src/server/api/__init__.py` - Tool handler registry (16 dispatchers)
- `src/client/api/base_client.py` - HTTP client with auth, rate limiting, retry, file upload
- `src/client/api/attachments.py` - Attachments API client
- `src/server/api/rate_limiter.py` - Rate limiting implementation
- `src/server/api/*_cache.py` - Four cache implementations

**Configuration:**
- `pyproject.toml` - Package metadata and dependencies (mcp, httpx, pydantic)
- `mcp_config_example.json` - MCP client configuration template
- `.env.example` - Environment variable template

**Documentation:**
- `README.md` - Project overview and quick start
- `USER_GUIDE.md` - Complete setup and usage guide
- `CLAUDE.md` - AI assistant guidance

## Important Notes

- **Cache warming is critical** - Always populate caches before field-dependent operations (use `testrail_metadata` actions: case_fields, statuses)
- **Rate limiter** - Global 180 req/min per container
- **Custom fields are dynamic** - Never hardcode field IDs, always use cache lookups
- **All test resources should use `[AUTOTEST]` prefix** for easy cleanup

## Rich Text & Attachments

### HTML, Not Markdown
All TestRail rich text fields (preconditions, steps, expected results, comments) use **HTML**. Markdown syntax like `**bold**` or `![](url)` renders as plain text.

```html
<!-- CORRECT -->
<p>Step description with <b>bold</b> text</p>
<br />
<img src="index.php?/attachments/get/1000003243" />

<!-- WRONG — rendered as plain text -->
**bold text**
![](index.php?/attachments/get/1000003243)
```

### Embedding Images in Cases (2-Step Process)
1. **Upload** the image via `testrail_attachments` (action: upload, entity_type: case)
2. **Update** the case field with an HTML `<img>` tag:
   ```html
   <img src="index.php?/attachments/get/{attachment_id}" />
   ```

### Updating Steps (custom_steps_separated)
When updating `custom_steps_separated`, you **MUST send ALL steps** in the array. Omitted steps are deleted. Always:
1. GET the case first to read current steps
2. Modify only the target step(s)
3. Send the complete array back in the update

### Attachment IDs
Attachment IDs may be **numeric** (pre-7.1) or **alphanumeric UUIDs** (TestRail 7.1+). Always treat as strings, never cast to int.
