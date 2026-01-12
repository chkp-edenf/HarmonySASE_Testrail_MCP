# TestRail MCP Server - User Guide

**Version 1.1.0 - Setup and Usage Instructions**

## 📋 Table of Contents
- [What You'll Learn](#what-youll-learn)
- [Prerequisites](#prerequisites)
- [Step 1: Get Your TestRail API Key](#step-1-get-your-testrail-api-key)
- [Step 2: Build the Docker Image](#step-2-build-the-docker-image)
- [Step 3: Configure Your AI Client](#step-3-configure-your-ai-client)
- [Step 4: Test the Connection](#step-4-test-the-connection)
- [Step 5: Populate the Cache](#step-5-populate-the-cache)
- [Common Workflows](#common-workflows)
- [Testing & Validation](#testing--validation)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## What You'll Learn

This guide will walk you through:
1. Setting up the TestRail MCP Server from scratch
2. Configuring it with Claude Desktop or VS Code
3. Using the 40 available tools effectively
4. Troubleshooting common issues

**Time Required:** 10-15 minutes

---

## Prerequisites

Before you begin, make sure you have:

✅ **Docker Desktop** installed and running
   - Download from: https://www.docker.com/products/docker-desktop
   - Verify: Run `docker --version` in terminal

✅ **TestRail Account** with access
   - You need login credentials to your TestRail instance
   - Example: https://your-company.testrail.io

✅ **One of these AI clients:**
   - Claude Desktop (recommended for beginners)
   - VS Code with GitHub Copilot
   - Any MCP-compatible client

---

## Step 1: Get Your TestRail API Key

1. **Log in to TestRail** (e.g., https://your-company.testrail.io)

2. **Navigate to your profile:**
   - Click your avatar (top right)
   - Select **"My Settings"**

3. **Generate API Key:**
   - Scroll to **"API Keys"** section
   - Click **"Add Key"**
   - Give it a name (e.g., "MCP Server")
   - **Copy the key** - you'll need it in Step 4

   ⚠️ **Important:** Save this key securely! You won't be able to see it again.

**Reference:** [TestRail API Documentation](https://support.gurock.com/hc/en-us/articles/7077039051284-Accessing-the-TestRail-API)

---

## Step 2: Build the Docker Image

Navigate to the project directory and build:

```bash
cd /path/to/HarmonySASE_Testrail_MCP
docker build -t testrail_mcp .
```

**Expected output:** Build progress, ending with "Successfully tagged testrail_mcp:latest"

**Verify the image:**
```bash
docker images | grep testrail_mcp
```

You should see:
```
testrail_mcp    latest    <image_id>    <time>    <size>
```

---

## Step 3: Configure Your AI Client

Choose your AI client and follow the corresponding setup:

### Option A: Claude Desktop (Recommended)

1. **Locate Claude's config file:**
   ```bash
   # macOS
   open ~/Library/Application\ Support/Claude/
   
   # Windows
   %APPDATA%\Claude\
   
   # Linux
   ~/.config/Claude/
   ```

2. **Edit `claude_desktop_config.json`:**
   
   If file doesn't exist, create it. Add this configuration:

   ```json
   {
     "mcpServers": {
       "testrail": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-e",
           "TESTRAIL_URL=https://your-company.testrail.io",
           "-e",
           "TESTRAIL_USERNAME=your-email@company.com",
           "-e",
           "TESTRAIL_API_KEY=your-api-key-here",
           "-v",
           "testrail_mcp"
         ]
       }
     }
   }
   ```

3. **Replace these values:**
   - `https://your-company.testrail.io` → Your TestRail URL
   - `your-email@company.com` → Your TestRail email
   - `your-api-key-here` → API key from Step 1

4. **Restart Claude Desktop** completely (Quit and reopen)

### Option B: VS Code (GitHub Copilot)

1. **Locate VS Code MCP config:**
   ```bash
   # macOS/Linux
   ~/Library/Application Support/Code/User/mcp.json
   
   # Windows
   %APPDATA%\Code\User\mcp.json
   ```

2. **Edit `mcp.json`:**
   
   ```json
   {
     "servers": {
       "testrail": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-e",
           "TESTRAIL_URL=https://your-company.testrail.io",
           "-e",
           "TESTRAIL_USERNAME=your-email@company.com",
           "-e",
           "TESTRAIL_API_KEY=your-api-key-here",
           "testrail_mcp"
         ]
       }
     }
   }
   ```

3. **Replace these values:**
   - `https://your-company.testrail.io` → Your TestRail URL
   - `your-email@company.com` → Your TestRail email
   - `your-api-key-here` → API key from Step 1

4. **Reload VS Code** (Cmd+Shift+P → "Reload Window")

---

## Step 4: Test the Connection

Now let's verify everything works!

### Test Command

Open your AI client and ask:

```
"Get all TestRail projects"
```

or

```
"List my TestRail projects"
```

### Expected Result

You should see a formatted list of your TestRail projects:

```
✅ Successfully retrieved projects

**TestRail Projects**

**Project #1: API Testing Suite**
ID: 1
Announcement: Project details here
URL: https://yoursite.testrail.io/index.php?/projects/overview/1
...
```

### If It Fails

See [Troubleshooting](#troubleshooting) section below.

---

## Step 5: Populate the Cache

**This is CRITICAL** - Run these commands first to enable natural language field values!

### Initialize Field, Priority, and Case Type Caches

Ask your AI:

```
"Get case fields from TestRail"
```

or

```
"Show me all TestRail case fields"
```

### What This Does

- Fetches all custom field definitions from TestRail
- Maps field values (e.g., "Mac" → ID 1, "Regression" → ID 3)
- Detects required fields per project  
- Caches everything for 24 hours in memory
- **Also populates priority and case type caches automatically**

### Initialize Status Cache

Ask your AI:

```
"Get statuses from TestRail"
```

or

```
"Show me all test statuses"
```

### What This Does

- Fetches all test status definitions from TestRail  
- Maps status names to IDs (e.g., "Passed" → ID 1, "Failed" → ID 5)
- Enables natural language status values when adding results
- Caches for 24 hours in memory (independent from field cache)

### Expected Output

```
✅ Successfully retrieved case fields

Found X field(s):

**custom_platforms** ⚠️ Required
  Values: Mac (1), Windows (2), Linux (3)

**custom_automationcoverage**
  Values: Mac_Automated (4), Win_Automated (5), ...

...
```

**Now you're ready!** You can use natural language field names in all commands.

---

## Common Workflows

### 🚀 Getting Started

**1. Initialize Cache (First Time)**
```
Ask AI: "Get case fields from TestRail"
```
This populates the cache with custom field mappings you'll need for creating test cases.

**2. Explore Your Structure**
```
"List all TestRail projects"
"Show me suites in project 1"
"Get sections in suite 1"
```

### ✍️ Creating Test Cases

**Method 1: Simple Case**
```
"Create a test case in section 10 with title 'Login Test'"
```

**Method 2: With Custom Fields (using natural language)**
```
"Create a test case:
- Section: 20
- Title: 'Check VPN connection on Mac'
- Platform: Mac
- Automation Coverage: Automated
- Test Phase: Regression"
```

The system automatically converts:
- `"Mac"` → Platform ID 3
- `"Mac_Automated"` → Automation Coverage ID 3
- `"Regression"` → Test Phase ID 1

**Method 3: With Full Details**
```
"Add test case to section 30:
- Title: 'Verify firewall rules'
- Preconditions: 'System configured, user logged in'
- Steps: '1. Open settings\\n2. Check configuration tab'
- Custom fields: priority=High, coverage=Manual"
```

### 🔄 Managing Test Runs

**Create & Execute**
```
1. "Create test run in project 1 named 'Sprint 24 Regression'"
2. "Add result to test 101: status=passed, comment='All checks passed'"
3. "Close test run 50"
```

**Bulk Results**
```
"Add multiple results to run 50:
- Test 201: passed
- Test 202: failed with comment 'Timeout error'
- Test 203: blocked"
```

### 🔍 Finding Information

**Search Cases**
```
"Get all test cases in section 20"
"Show me case 301 details"
"Get history of changes for case 302"
```

**Check Run Status**
```
"List all runs in project 1"
"Show results for run 60"
"Get test results for case 303"
```

### 📦 Organizing Tests

**Restructure**
```
"Move cases 401,402,403 to section 40"
"Copy cases from section 10 to section 50"
"Move section 30 under section 20"
```

**Bulk Operations**
```
"Update multiple cases in section 60: set priority to High"
"Delete cases 501,502,503"
```

---

## Testing & Validation

The TestRail MCP Server includes a comprehensive test suite with **40 test scripts** (one for each tool) to validate your deployment.

### Quick Validation

Test the most critical tool:
```bash
cd tests
source test_config.sh  # Configure credentials (prompts for API key)
bash metadata/test_get_case_fields.sh
```

### Full Test Suite

The test suite is organized by category:
- **Metadata** (4 tests) - Read-only, safe to run
- **Projects** (2 tests) - Read-only
- **Suites** (5 tests) - Create/read/update/delete
- **Sections** (6 tests) - Full CRUD + move operations
- **Cases** (10 tests) - Full CRUD + bulk operations
- **Runs** (6 tests) - Test run management
- **Tests** (2 tests) - Test instance queries
- **Results** (5 tests) - Result recording

### Recommended Testing Order

1. **Foundation** (start here):
   ```bash
   bash metadata/test_get_case_fields.sh  # Populates cache (REQUIRED!)
   bash metadata/test_get_statuses.sh
   bash projects/test_get_projects.sh
   ```

2. **Read Operations** (safe):
   ```bash
   bash suites/test_get_suites.sh
   bash sections/test_get_sections.sh
   bash cases/test_get_cases.sh
   ```

3. **Write Operations** (creates test data):
   ```bash
   bash suites/test_add_suite.sh
   bash sections/test_add_section.sh
   bash cases/test_add_case.sh
   ```

4. **Cleanup** (destructive, prompts for confirmation):
   ```bash
   bash cases/test_delete_case.sh
   bash sections/test_delete_section.sh
   bash suites/test_delete_suite.sh
   ```

### Complete Testing Documentation

See [`docs/guides/testing/TESTING_STRATEGY.md`](docs/guides/testing/TESTING_STRATEGY.md) for:
- Complete tool inventory
- Testing strategies and approaches
- Detailed testing phases
- Troubleshooting tips
- Security best practices

---

## Troubleshooting

### Issue: "Connection Error" or "Process exited with code 1"

**Symptoms**: Server fails to start or crashes immediately

**Solutions**:
1. Check Docker is running: `docker ps`
2. Check credentials are correct in config file
3. Test connection manually:
   ```bash
   docker run -it --rm \
     -e TESTRAIL_URL=https://your.testrail.io \
     -e TESTRAIL_USERNAME=your@email.com \
     -e TESTRAIL_API_KEY=your-key \
     testrail_mcp
   ```

### Issue: "Missing required fields" when creating test case

**Symptoms**: Error about missing custom_automationcoverage, custom_platforms, etc.

**Solution**:
1. Run `get_case_fields` first to populate cache
2. Check which fields are required (marked with ⚠️ REQUIRED)
3. Provide those fields when creating cases

### Issue: "Unknown field value" or "Could not resolve value"

**Symptoms**: Custom field value not recognized

**Solutions**:
1. Run `get_case_fields` to see valid values
2. Check spelling and case (system converts to lowercase)
3. Use numeric ID instead: `"custom_platforms": "3"` instead of `"Mac"`
4. Check if cache is stale (>24 hours) - it will auto-refresh

### Issue: "ModuleNotFoundError" in Docker logs

**Symptom**: Python import errors

**Solution**: Rebuild Docker image:
```bash
cd /path/to/HarmonySASE_Testrail_MCP
docker build -t testrail_mcp .
```

### Issue: Changes not taking effect

**Solution**: Restart the AI client:
- Claude Desktop: Quit and reopen
- VS Code: Run "Developer: Reload Window"

---

## FAQ

### Q: Do I need to run `get_case_fields` and `get_statuses` every time?
**A:** No! The four caches (field, status, priority, case_type) persist for 24 hours in memory. Only need to run if:
- First time using after container start
- Added new custom fields or statuses to TestRail
- Cache expired (>24 hours old)
- Container restarted

### Q: Does cache persist between container restarts?
**A:** No, all four caches (field, status, priority, case_type) are stored in memory only and cleared on restart. This ensures a fresh state and maximum simplicity. The first `get_case_fields` and `get_statuses` calls after restart will repopulate the caches automatically.

### Q: What happens if I provide an invalid field value?
**A:** The system will:
1. Try to resolve using cached mappings
2. Log a warning if unresolved
3. Skip that value and continue with others

### Q: Can I use this with multiple TestRail projects?
**A:** Yes! All of your projects are accessible through the same MCP server.

### Q: How do I add a new custom field?
**A:** Just use it! The system supports generic passthrough:
```
"Add case with custom_my_new_field='some value'"
```
Or add explicit handling in `add_case` handler for better validation.

### Q: Is my API key secure?
**A:** 
- ✅ Keys are passed as environment variables (not in code)
- ✅ Docker container is isolated
- ✅ Cache is in-memory only (no files, cleared on restart)
- ⚠️ Don't commit config files with keys to git!

### Q: What TestRail API version is supported?
**A:** TestRail API v2 (current stable version)

### Q: Can I use this in CI/CD pipelines?
**A:** Not recommended. This is designed for human-AI interaction. For automation, use TestRail's API directly or their official SDKs.

---

## Getting Help

**Check logs**:
- VS Code: Open "MCP" output channel
- Claude: Check `~/Library/Logs/Claude/`
- Docker: `docker logs <container-id>`

**Common commands**:
```bash
# Check Docker images
docker images | grep testrail

# See running containers
docker ps

# View container logs
docker logs <container-id>

# Rebuild after code changes
docker build -t testrail_mcp .
```

---

## Summary Checklist

✅ **Before First Use**:
- [ ] Docker installed and running
- [ ] TestRail API key generated
- [ ] Docker image built
- [ ] Config file updated with YOUR credentials
- [ ] AI client restarted
- [ ] Ran `get_case_fields` to initialize cache

✅ **For Each Test Case Creation**:
- [ ] Know your section_id
- [ ] Have required fields (platforms, automationcoverage, test_phase)
- [ ] Check field values with `get_case_fields` if unsure

✅ **Best Practices**:
- [ ] Run `get_case_fields` once after container starts
- [ ] Use natural language for field values ("Mac", "Win_Automated")
- [ ] Check required fields before creating cases
- [ ] Restart container if cache becomes stale

---

## Additional Documentation

For comprehensive documentation on the TestRail MCP Server, see the organized documentation in [`docs/`](docs/):

### 📖 Core Documentation
- **[Project Overview](docs/overview/PROJECT_OVERVIEW.md)** - System capabilities, features, and architecture overview
- **[Architecture](docs/architecture/ARCHITECTURE.md)** - Technical design, components, and data flow

### 🔧 Setup & Integration Guides
- **[Integration Guide](docs/guides/integration/INTEGRATION_GUIDE.md)** - MCP client setup (Claude Desktop, VS Code, Cline)
- **[Deployment Guide](docs/guides/deployment/DEPLOYMENT.md)** - Docker deployment and production configuration
- **[Testing Strategy](docs/guides/testing/TESTING_STRATEGY.md)** - Validation, test suite, and quality assurance

### 👨‍💻 Development Resources
- **[Development Guide](docs/development/DEVELOPMENT.md)** - Contributing, code structure, and development workflow
- **[Improvement Plan](docs/development/IMPROVEMENT_PLAN.md)** - Roadmap and planned enhancements

---

**Version**: 1.1.0
**Last Updated**: January 10, 2026
**Maintainer**: Harmony SASE Team
