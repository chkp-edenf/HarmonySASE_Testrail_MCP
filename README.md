# 🧪 TestRail MCP Server

**Connect AI assistants to your TestRail instance**

[![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)](reference/CHANGELOG.md)
[![MCP Protocol](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)

> Talk to your AI assistant about test cases, and watch it create, update, and manage them in TestRail—all through natural conversation.

---

## 🌟 Highlights

- 🎯 **61 Complete Tools** - Full CRUD for projects, suites, sections, cases, runs, tests, results, plans, users, milestones, and configurations
- 🌍 **100% Portable** - Works with ANY TestRail instance (no hardcoded custom fields!)
- 🧠 **Smart Field Handling** - Say "Regression" instead of memorizing numeric IDs  
- ⚡ **Auto Rate-Limited** - Built-in throttling (180 req/min) protects your API quota
- 🔒 **Secure by Default** - Non-root Docker, environment variables only, no persistent storage
- 📦 **Zero Setup Friction** - Docker image builds in 30 seconds, connects in 5 minutes

**Five minutes from clone to "Ask your AI: Show me all test cases"** → [Quick Start](#-quick-start)

---

## ℹ️ Overview

### What Problem Does This Solve?

Your QA team spends hours clicking through TestRail to:
- Create dozens of test cases with repetitive data entry
- Update bulk test cases when requirements change  
- Find and analyze test results across multiple runs
- Document test executions with consistent formatting

**This MCP server eliminates that friction.** Your AI assistant becomes a TestRail power user—creating, reading, updating, and deleting resources through simple conversation.

### How It Works

```
You → "Create 10 test cases for the login flow with priority Critical"
      ↓
   Your AI (Claude/Copilot) understands the request
      ↓
   MCP Server translates to TestRail API calls
      ↓
   TestRail creates the test cases
      ↓
You ← "Created 10 test cases in section 'Login Tests'"
```

The Model Context Protocol (MCP) is a standard that lets AI assistants securely call external tools. This server implements 61 TestRail tools that your AI can use—no TestRail expertise required!

### Why Use This vs TestRail UI?

| Task | TestRail UI | With MCP Server |
|------|-------------|-----------------|
| Create 50 test cases | 30-45 min (repetitive clicking) | 2 min (one AI request) |
| Update custom fields on 100 cases | 15-20 min (bulk edit form) | 1 min ("update all cases in section X") |
| Find all failed tests from last week | 5-10 min (filters + exports) | 30 sec ("show failed tests from last 7 days") |
| Document test run results | 10 min (copy/paste to docs) | Instant (AI formats as table/report) |

**Perfect for:** QA teams, Test Automation Engineers, Release Managers, anyone who works with TestRail daily

### Who Built This?

This MCP server was created to solve real workflow friction experienced by QA teams managing large test suites. After watching testers spend hours on repetitive TestRail tasks, we built a better way.

**Version 1.5.0** adds Users (3), Milestones (5), and Configurations (3) support for enhanced team collaboration and multi-platform testing, bringing total tools to 61. See [CHANGELOG](reference/CHANGELOG.md) for details.

---

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** ([download](https://www.docker.com/products/docker-desktop))
- **TestRail Account** with API access
- **AI Client**: Claude Desktop or VS Code with GitHub Copilot

### 1. Get Your TestRail API Key

1. Log in to TestRail → Click your avatar → **My Settings**
2. Scroll to **API Keys** → Click **Add Key**  
3. Copy the key (you won't see it again!)

[Full API key instructions](https://support.gurock.com/hc/en-us/articles/7077039051284)

### 2. Build & Run

```bash
# Clone and build
git clone <your-repo-url>
cd HarmonySASE_Testrail_MCP
docker build -t testrail_mcp .

# Configure your AI client
# See USER_GUIDE.md for Claude Desktop or VS Code setup
```

### 3. Test It!

Ask your AI:
```
"Get all TestRail projects"
```

If you see your projects list, you're ready! 🎉

**Full setup guide:** [USER_GUIDE.md](USER_GUIDE.md) (step-by-step with screenshots)

---

## 💡 Usage Examples

### Creating Test Cases

```
You: "Create 5 test cases in section 'API Tests' for the User Registration endpoint"

AI uses: add_case (5 times)
Result: 5 new test cases with auto-generated titles and IDs
```

### Using Custom Fields (Works with ANY TestRail instance!)

```
You: "Create a test case with custom fields: test_phase='Regression', platforms='Win,Mac'"

AI uses: add_case with custom_fields parameter
Result: Test case created with your instance's specific custom fields
```

The MCP automatically discovers your custom fields via `get_case_fields` and converts human-readable names to IDs!

### Bulk Operations

```
You: "Update all test cases in suite 3 to priority 'High'"

AI uses: get_cases → update_cases (bulk)
Result: All cases updated in one API call
```

### Analyzing Results

```
You: "Show me all failed tests from test run 142"

AI uses: get_results_for_run
Result: Formatted table with test names, statuses, and failure comments
```

**See more:** [reference/QUICK_REFERENCE.md](reference/QUICK_REFERENCE.md)

---

## ⬇️ Installation

### Docker (Recommended)

```bash
docker build -t testrail_mcp .
```

**System Requirements:**
- Docker Desktop 4.0+
- 100MB disk space
- Network access to your TestRail instance

**Platform Support:** ✅ macOS  ✅ Linux  ✅ Windows

### Configuration

Add to your AI client's MCP config (Claude Desktop example):

```json
{
  "mcpServers": {
    "testrail": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TESTRAIL_URL=https://your-company.testrail.io",
        "-e", "TESTRAIL_USERNAME=your-email@company.com",
        "-e", "TESTRAIL_API_KEY=your-key-here",
        "testrail_mcp"
      ]
    }
  }
}
```

**Replace:**
- `https://your-company.testrail.io` → Your TestRail URL
- `your-email@company.com` → Your TestRail login email
- `your-key-here` → API key from Prerequisites step

**Full configuration guide:** [USER_GUIDE.md](USER_GUIDE.md)

---

## 🛠️ Available Tools

<details>
<summary><strong>61 Tools Organized by Category</strong></summary>

### Projects (2 tools)
- `get_projects` - List all projects
- `get_project` - Get project details

### Suites (5 tools)
- `get_suites`, `get_suite` - View test suites
- `add_suite`, `update_suite`, `delete_suite` - Manage suites

### Sections (6 tools)
- `get_sections`, `get_section` - View sections
- `add_section`, `update_section`, `delete_section`, `move_section` - Organize sections

### Test Cases (10 tools)
- `get_cases`, `get_case` - Browse test cases
- `add_case`, `update_case`, `delete_case` - CRUD operations
- `get_case_history` - View change history
- `copy_cases_to_section`, `move_cases_to_section` - Reorganize
- `update_cases`, `delete_cases` - Bulk operations

### Test Runs (6 tools)
- `get_runs`, `get_run` - View test runs
- `add_run`, `update_run`, `close_run`, `delete_run` - Manage test execution

### Tests (2 tools)
- `get_tests`, `get_test` - View tests in a run

### Results (5 tools)
- `get_results`, `get_results_for_case`, `get_results_for_run` - Query results
- `add_result`, `add_results` - Record test outcomes

### Test Plans (9 tools)
- `get_plans`, `get_plan` - View test plans
- `add_plan`, `update_plan`, `close_plan`, `delete_plan` - Manage test plans
- `add_plan_entry`, `update_plan_entry`, `delete_plan_entry` - Manage plan entries (test runs within plans)

### Users (3 tools)
- `get_users` - List all users (with optional active filter)
- `get_user` - Get user by ID
- `get_user_by_email` - Lookup user by email

### Milestones (5 tools)
- `get_milestones`, `get_milestone` - View milestones
- `add_milestone`, `update_milestone`, `delete_milestone` - Manage release cycles and sprint tracking

### Configurations (3 tools)
- `get_configs` - List configuration groups for multi-platform testing
- `add_config_group` - Create config groups (Browsers, OS, Devices)
- `add_config` - Add configurations to groups

### Metadata & Health (5 tools)
- `get_case_fields` - **Run this first!** (discovers custom fields, populates 3 caches)
- `get_statuses` - View test statuses (populates status cache)
- `get_case_types`, `get_priorities` - View case types and priorities
- `get_server_health` - Monitor server health, cache status, and rate limiter stats

</details>

**Pro tip:** Run `get_case_fields` to populate field, priority, and case type caches. Run `get_statuses` to populate the status cache.

---

## 🏗️ Architecture

```
┌─────────────────┐
│   AI Assistant  │  (Claude Desktop, VS Code Copilot)
│  (User facing)  │
└────────┬────────┘
         │ MCP Protocol (stdio JSON-RPC)
         │
┌────────▼────────┐
│   MCP Server    │  (This project - Docker container)
│   61 Tools      │
└────────┬────────┘
         │ HTTP + Auth
         │
┌────────▼────────┐
│  TestRail API   │  (Your TestRail instance)
│    REST v2      │
└─────────────────┘
```

### Key Components

- **Client Layer** (`src/client/api/`) - HTTP client with rate limiting
- **Server Layer** (`src/server/api/`) - MCP tool handlers  
- **Shared Layer** (`src/shared/schemas/`) - Pydantic validation models
- **Four Independent Caches** - In-memory metadata (24h TTL, ephemeral)
  - Field Cache (`field_cache.py`) - Custom field mappings
  - Status Cache (`status_cache.py`) - Test status mappings  
  - Priority Cache (`priority_cache.py`) - Priority mappings
  - Case Type Cache (`case_type_cache.py`) - Case type mappings
- **Rate Limiter** - Token bucket algorithm (180 req/min)

**Design Principles:**
- Stateless handlers (no side effects)
- Single persistent HTTP connection
- Auto field name→ID conversion
- Fail-fast validation

---

## 🔐 Security

This MCP server follows security best practices:

✅ **No Hardcoded Credentials** - Environment variables only  
✅ **Non-Root Container** - Runs as user `mcpuser` (UID 1000)  
✅ **Ephemeral Cache** - In-memory only, cleared on restart  
✅ **Rate Limiting** - Prevents API quota exhaustion  
✅ **Input Validation** - Pydantic schemas validate all inputs  
✅ **Minimal Image** - Python slim base, no unnecessary packages

**Credential Handling:**
- API key passed via environment variable
- Never logged or stored
- Not included in Docker image

---

## 📚 Documentation

### Getting Started
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete setup guide (start here!)
- **[reference/QUICK_REFERENCE.md](reference/QUICK_REFERENCE.md)** - Command cheat sheet

### Comprehensive Documentation
- **[docs/README.md](docs/README.md)** - 📚 Master documentation index
  - [Project Overview](docs/overview/PROJECT_OVERVIEW.md) - Business value & use cases
  - [Architecture](docs/architecture/ARCHITECTURE.md) - Technical design & patterns
  - [Integration Guide](docs/guides/integration/INTEGRATION_GUIDE.md) - TestRail API integration
  - [Deployment](docs/guides/deployment/DEPLOYMENT.md) - Operations & security
  - [Testing Strategy](docs/guides/testing/TESTING_STRATEGY.md) - QA approach
  - [Development](docs/development/DEVELOPMENT.md) - Contributing & development

### Reference
- **[reference/FEATURE_COVERAGE.md](reference/FEATURE_COVERAGE.md)** - Tool inventory & roadmap
- **[reference/CHANGELOG.md](reference/CHANGELOG.md)** - Version history
- **[tests/TESTING_CHECKLIST.md](tests/TESTING_CHECKLIST.md)** - Test suite

---

## 🧪 Testing

Comprehensive test suite with **61 test scripts** (one per tool) and **Makefile orchestration** for fast, organized testing:

```bash
# Quick validation (3 critical tests, ~5s)
make test

# Full test suite (43 tests, ~32s)
make test-all

# Specific categories
make test-metadata
make test-cases
```

**61 test scripts** organized by category:
- Metadata (priorities, statuses, case types, fields)
- Projects, Suites, Sections
- Test Cases (CRUD + bulk operations)
- Test Runs, Plans & Tests
- Results
- Users, Milestones, Configurations

**Features:**
- ⚡ **76% faster** than running individual tests (single container approach)
- 🎯 **Organized categories** with clear pass/fail reporting
- 🔄 **CI/CD ready** with structured output
- 📚 **Detailed guide:** [MAKEFILE_GUIDE.md](MAKEFILE_GUIDE.md)

**All tests use `[AUTOTEST]` prefix for easy cleanup!**

---

## 🗺️ Roadmap

### ✅ v1.5.0 (Current - Released Jan 14, 2026)
- **Users & Roles API** - 3 new tools for user management and assignment workflows
- **Milestones API** - 5 new tools for release management and timeline tracking
- **Configurations API** - 3 new tools for multi-platform testing support
- 61 total tools covering ~87% of TestRail API v2
- Enhanced documentation with comprehensive use cases and examples

### ✅ v1.4.0 (Released Jan 14, 2026)
- **Advanced Filtering** - Date ranges, user filters, priority/type/milestone filtering
- **Automatic Retry Logic** - Exponential backoff for transient failures
- **Enhanced Health Monitoring** - Comprehensive operational metrics

### ✅ v1.3.0 (Released Jan 13, 2026)
- **Plan Entries Support** - 3 new tools for managing test runs within plans

### ✅ v1.2.0 (Released Jan 13, 2026)
- **Test Plans Support** - 6 new tools for complete CRUD operations

### ✅ v1.1.0 (Released Jan 9, 2026)
- **100% Portable** - No hardcoded custom fields, works with any TestRail instance

### 🌟 Future (v2.0+)
- Attachments support for test cases and results
- Advanced analytics and reporting

**See [FEATURE_COVERAGE.md](reference/FEATURE_COVERAGE.md) for detailed roadmap**

---

## 💬 Contributing & Feedback

We'd love to hear from you!

- **Found a bug?** [Open an issue](https://github.com/your-org/testrail-mcp/issues)
- **Have a feature request?** [Start a discussion](https://github.com/your-org/testrail-mcp/discussions)
- **Want to contribute?** See [reference/AGENTS.md](reference/AGENTS.md) for development guide

**Questions?** Check [USER_GUIDE.md](USER_GUIDE.md) or ask in Discussions!

---

## 📄 License

[Add your license here]

---

## 🙏 Acknowledgments

- Built on the [Model Context Protocol](https://modelcontextprotocol.io) by Anthropic
- Integrates with [TestRail REST API v2](https://www.gurock.com/testrail/docs/api)
- Inspired by QA teams everywhere fighting repetitive work

---

**Ready to supercharge your TestRail workflow?** → [Get Started](USER_GUIDE.md)
