# TestRail MCP Server - User Guide

**Version 1.5.0 - Setup and Usage Instructions**

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
3. Using the 64 available tools effectively
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
cd /path/to/<your-repo>
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

### 🗂️ Managing Test Plans

**Create a Test Plan**
```
"Create a test plan in project 1:
- Name: 'Sprint 24 Release Testing'
- Description: 'Comprehensive testing for Sprint 24 release'
- Milestone ID: 5"
```

**View Test Plans**
```
"List all test plans in project 1"
"Show me test plan 42 details"
"Get test plans for project 1 with limit 50"
```

**Update Plans**
```
"Update test plan 15 with new name 'Sprint 25 Testing'"
"Update plan 20: set milestone to 10 and description to 'Updated scope'"
```

**Manage Plan Lifecycle**
```
"Close test plan 42"
"Delete test plan 99"
```

**Advanced: Create Plan with Test Run Entries**
```
"Create a test plan in project 1:
- Name: 'Q1 2026 Release Testing'
- Description: 'Comprehensive testing for Q1 release'
- Include entries for suite 10 and suite 15"
```

#### Plan Entries

Add test runs to existing plans:

```json
{
  "tool": "add_plan_entry",
  "arguments": {
    "plan_id": "123",
    "suite_id": "1",
    "name": "Browser Tests",
    "include_all": "true"
  }
}
```

Update plan entries:

```json
{
  "tool": "update_plan_entry",
  "arguments": {
    "plan_id": "123",
    "entry_id": "e1f2a3b4",
    "name": "Updated Browser Tests"
  }
}
```

Delete plan entries:

```json
{
  "tool": "delete_plan_entry",
  "arguments": {
    "plan_id": "123",
    "entry_id": "e1f2a3b4"
  }
}
```

### 🔍 Advanced Filtering (v1.4.0)

The TestRail MCP Server supports advanced filtering for `get_cases`, `get_runs`, and `get_results` operations to help you query large datasets more efficiently.

#### Filtering Test Cases

**Filter by Priority**
```
"Get all high-priority test cases in project 1"
"Show me test cases with priority 2 in section 10"
```

**Filter by Type**
```
"Get all automated test cases in project 1"
"Show me regression test cases in suite 5"
```

**Filter by Date Range**
```
"Get test cases created in the last 30 days from project 1"
"Show me test cases updated after timestamp 1704067200"
```

**Multiple Filters Combined**
```
"Get test cases in project 1:
- Priority: High
- Type: Automated
- Created after: <timestamp>
- Limit: 50"
```

**Available Filters for get_cases**:
- `created_by` - User ID who created the case
- `created_after` / `created_before` - Unix timestamp for creation date range
- `updated_by` - User ID who last updated the case
- `updated_after` / `updated_before` - Unix timestamp for update date range
- `priority_id` - Filter by priority IDs (comma-separated for multiple)
- `type_id` - Filter by case type IDs (comma-separated for multiple)
- `milestone_id` - Filter by milestone IDs (comma-separated for multiple)

#### Filtering Test Runs

**Filter by Completion Status**
```
"Get all active test runs in project 1"
"Show me completed runs from the last month"
```

**Filter by Milestone**
```
"Get test runs for milestone 5"
"Show me runs associated with Sprint 24"
```

**Filter by Creation Date**
```
"Get runs created in the last week in project 1"
"Show me runs created after timestamp 1704067200"
```

**Available Filters for get_runs**:
- `created_by` - User ID who created the run
- `created_after` / `created_before` - Unix timestamp for creation date range
- `milestone_id` - Filter by milestone IDs (comma-separated for multiple)
- `is_completed` - Filter by completion status (true/false)

#### Filtering Test Results

**Filter by Status**
```
"Get all failed results from run 50"
"Show me passed test results for case 100"
```

**Filter by Date Range**
```
"Get results from the last 7 days for run 50"
"Show me results created after timestamp 1704067200"
```

**Available Filters for get_results**:
- `created_by` - User ID who created the result
- `created_after` / `created_before` - Unix timestamp for creation date range
- `status_id` - Filter by status IDs (comma-separated for multiple)

#### Best Practices for Filtering

1. **Use Timestamps Wisely**: Convert dates to Unix timestamps for precise filtering
   ```bash
   # 30 days ago
   date -d "30 days ago" +%s
   ```

2. **Combine Filters**: Use multiple filters together for more targeted results
   ```
   "Get high-priority automated test cases created in the last month from project 1"
   ```

3. **Limit Results**: Always specify a reasonable limit to avoid overwhelming responses
   ```
   "Get filtered cases with limit 25"
   ```

4. **Comma-Separated IDs**: For multiple values, use comma-separated lists
   ```
   "Get cases with priority_id: 1,2 (High and Medium)"
   "Get cases with type_id: 1,3 (Automated and Functional)"
   ```

### 👥 User Management (v1.5.0)

The Users API enables you to query user information for user assignment, team coordination, and user activity reporting.

#### Getting All Users

**List all active users:**
```
"Get all active users from TestRail"
"Show me all active TestRail users"
```

**List all users (including inactive):**
```
"Get all users from TestRail"
"List all TestRail users"
```

#### Getting Specific User

**By User ID:**
```
"Get user with ID 5"
"Show me details for user 10"
```

**By Email:**
```
"Find user with email john.doe@company.com"
"Lookup user by email alice@example.com"
```

#### Use Cases

**Assigning Test Cases:**
```
"Create test run in project 1, assign to user 5"
"Update test case 100, assign to user with email bob@company.com"
```

**Team Coordination:**
```
"Get all active users and show their roles"
"List team members for assignment"
```

**User Activity Reports:**
```
"Show me all users and their active status"
"Get user 5 details including role information"
```

#### User Information Returned

Each user object includes:
- **ID** - Numeric user identifier
- **Name** - Full name
- **Email** - Email address
- **Active Status** - Whether user is active
- **Role** - User role name (e.g., "Tester", "Lead")
- **Role ID** - Numeric role identifier

#### Examples

**Example 1: Find assignable users**
```
"Get all active users from TestRail"
```

Response includes all active users with their IDs for assignment to cases and runs.

**Example 2: Lookup user for assignment**
```
"Find user with email sarah@company.com"
```

Returns user details including ID, which you can then use to assign test cases or runs.

**Example 3: Get user details by ID**
```
"Get details for user 8"
```

Shows complete user information including name, email, role, and active status.

### 📅 Milestone Management (v1.5.0)

The Milestones API enables you to manage release cycles, sprint tracking, and timeline coordination for structured test execution.

#### Getting Milestones

**List all milestones in a project:**
```
"Get all milestones from project 1"
"Show me milestones for project 5"
```

**Filter milestones by status:**
```
"Get completed milestones from project 1"
"Show me active milestones in project 3"
"List all started milestones in project 1"
```

#### Getting Specific Milestone

**By Milestone ID:**
```
"Get milestone with ID 10"
"Show me details for milestone 25"
```

#### Creating Milestones

**Simple milestone:**
```
"Create milestone in project 1 named 'Release 2.0'"
"Add milestone to project 5: 'Sprint 24'"
```

**With dates and description:**
```
"Create milestone in project 1:
- Name: 'Q1 2026 Release'
- Description: 'First quarter feature release'
- Start date: 1704067200
- Due date: 1711929600"
```

**Hierarchical milestones:**
```
"Create milestone in project 1:
- Name: 'Sprint 24.1'
- Parent milestone: 10
- Due date: 1709251200"
```

#### Updating Milestones

**Update milestone details:**
```
"Update milestone 15:
- Name: 'Q1 2026 Release - Updated'
- Description: 'Extended scope for Q1'
- Due date: 1712534400"
```

**Mark milestone status:**
```
"Update milestone 20: mark as started"
"Update milestone 25: mark as completed"
"Set milestone 30 to completed with new due date"
```

#### Deleting Milestones

```
"Delete milestone 99"
"Remove milestone with ID 105"
```

#### Use Cases

**Structured Release Cycles:**
```
"Create milestone 'Release 3.0' in project 1 with due date in 60 days"
"Get all milestones for project 1 to plan releases"
```

**Sprint/Iteration Tracking:**
```
"Create milestone 'Sprint 25' under parent milestone 10"
"Show all active milestones to track current sprints"
```

**Timeline Management:**
```
"Create test run in project 1 for milestone 15"
"Get all runs for milestone 20 to see testing progress"
```

**Milestone-based Filtering:**
```
"Get test cases for milestone 15"
"Show test runs associated with milestone 20"
```

#### Milestone Information Returned

Each milestone object includes:
- **ID** - Numeric milestone identifier
- **Name** - Milestone name
- **Description** - Optional description
- **Project ID** - Associated project
- **Status** - Started/completed flags
- **Dates** - Start date, due date, completion dates (Unix timestamps)
- **Parent ID** - For hierarchical milestones
- **URL** - Direct link to milestone in TestRail

#### Working with Unix Timestamps

Milestone dates use Unix timestamps (seconds since epoch):

```bash
# Get timestamp for 30 days from now
date -d "+30 days" +%s

# Get timestamp for specific date
date -d "2026-03-31" +%s

# Convert timestamp to readable date
date -d @1711929600
```

#### Examples

**Example 1: Create release milestone**
```
"Create milestone in project 1:
- Name: 'Release 2.5.0'
- Description: 'Mid-year feature release'
- Due date: 1719792000"
```

**Example 2: Track sprint progress**
```
"Get all started milestones from project 1"
```
Returns all milestones currently in progress for sprint tracking.

**Example 3: Update milestone timeline**
```
"Update milestone 15:
- Due date: 1722470400
- Description: 'Extended timeline due to scope changes'"
```

**Example 4: Complete milestone**
```
"Update milestone 20: set as completed"
```

Marks the milestone as finished, automatically recording completion timestamp.

### 🔧 Multi-Platform Testing Configurations (v1.5.0)

The Configurations API enables you to manage test configurations for multi-platform testing scenarios, allowing you to run tests across different browsers, operating systems, devices, and environments.

#### What are Configurations?

Configurations in TestRail are organized into **Configuration Groups** that contain individual **Configurations**:

- **Configuration Group**: A category of configurations (e.g., "Browsers", "Operating Systems", "Devices")
- **Configuration**: A specific option within a group (e.g., "Chrome", "Firefox", "Safari" within "Browsers")

These configurations enable **matrix testing** - running the same tests across multiple platform combinations.

#### Getting Configurations

**List all configuration groups for a project:**
```
"Get all configurations from project 1"
"Show me config groups for project 5"
```

This returns all configuration groups with their nested configurations.

#### Creating Configuration Groups

**Create a new configuration group:**
```
"Create config group in project 1 named 'Browsers'"
"Add configuration group 'Operating Systems' to project 3"
```

**Common configuration group examples:**
- **Browsers** - Chrome, Firefox, Safari, Edge
- **Operating Systems** - Windows 11, macOS Sonoma, Ubuntu 22.04
- **Devices** - iPhone 15, Samsung Galaxy S24, iPad Pro
- **Environments** - Development, Staging, Production
- **API Versions** - v1.0, v2.0, v3.0

#### Adding Configurations

**Add configurations to a group:**
```
"Add config 'Chrome' to group 10"
"Add config 'Windows 11' to group 15"
```

**Example: Setting up browser testing**
```
"Create config group 'Browsers' in project 1"
# Then add individual browsers:
"Add config 'Chrome' to group 20"
"Add config 'Firefox' to group 20"
"Add config 'Safari' to group 20"
"Add config 'Edge' to group 20"
```

#### Use Cases

**Browser Compatibility Testing**
```
"Create config group 'Browsers' in project 1"
"Add configs: Chrome, Firefox, Safari, Edge"
```
Run your test suite across all major browsers to ensure compatibility.

**Cross-Platform Desktop Apps**
```
"Create config group 'Operating Systems' in project 1"
"Add configs: Windows 11, macOS Sonoma, Ubuntu 22.04"
```
Test your desktop application on different OS platforms.

**Mobile Device Testing**
```
"Create config group 'Mobile Devices' in project 1"
"Add configs: iPhone 15 Pro, Samsung Galaxy S24, iPad Pro"
```
Verify mobile app functionality across device types and screen sizes.

**API Version Testing**
```
"Create config group 'API Versions' in project 1"
"Add configs: v1.0, v2.0, v3.0"
```
Ensure backward compatibility across API versions.

**Environment Testing**
```
"Create config group 'Environments' in project 1"
"Add configs: Development, Staging, Production"
```
Test across different deployment environments.

#### Using Configurations in Test Plans

Once configured, you can use configurations when creating test plan entries:

```
"Add plan entry to plan 50:
- Suite ID: 10
- Config IDs: 1,2,3"
```

This creates test runs for each configuration (e.g., one run for Chrome, one for Firefox, one for Safari).

#### Configuration Information Returned

Each configuration group includes:
- **ID** - Numeric group identifier
- **Name** - Group name (e.g., "Browsers")
- **Project ID** - Associated project
- **Configs** - Array of configurations within the group

Each configuration includes:
- **ID** - Numeric configuration identifier
- **Name** - Configuration name (e.g., "Chrome")
- **Group ID** - Parent group identifier

#### Examples

**Example 1: Complete browser testing setup**
```
1. "Create config group 'Browsers' in project 1"
   # Returns group_id: 10

2. "Add config 'Chrome' to group 10"
3. "Add config 'Firefox' to group 10"
4. "Add config 'Safari' to group 10"
5. "Add config 'Edge' to group 10"

6. "Get all configurations from project 1"
   # Verify all browsers are configured
```

**Example 2: Multi-platform matrix testing**
```
# Set up OS configurations
"Create config group 'Operating Systems' in project 1"
"Add configs: Windows 11, macOS, Linux to group 15"

# Set up browser configurations
"Create config group 'Browsers' in project 1"
"Add configs: Chrome, Firefox to group 16"

# Use in test plan for matrix: 3 OS × 2 Browsers = 6 test runs
"Create test plan with configurations for all OS/browser combinations"
```

**Example 3: View existing configurations**
```
"Get all configurations from project 1"
```
Shows all configuration groups and their nested configurations for the project.

#### Best Practices

1. **Organize by Category** - Create separate groups for different aspects (browsers, OS, devices)
2. **Use Clear Names** - Name configs clearly (e.g., "Chrome 120" vs just "Chrome")
3. **Start Small** - Begin with critical platforms, expand coverage over time
4. **Document Versions** - Include version numbers when relevant (e.g., "iOS 17.2")
5. **Plan Matrix Size** - Remember: groups multiply (2 browsers × 3 OS = 6 runs)

#### Important Notes

⚠️ **No Delete API**: TestRail API v2 doesn't provide endpoints to delete configurations or configuration groups via API. Use the TestRail web interface to remove configurations if needed, or use the `[AUTOTEST]` prefix for test configurations to identify them for manual cleanup.

⚠️ **Matrix Multiplication**: When using multiple configuration groups in a test plan, the number of test runs multiplies (e.g., 3 browsers × 4 OS × 2 environments = 24 test runs).

⚠️ **Project Scope**: Configurations are project-specific and cannot be shared across projects.

---

## Filtering and Pagination

The TestRail MCP server supports comprehensive filtering and pagination across all GET tools. Filters allow AI agents to query specific subsets of data efficiently.

### Filter Types

- **✅ API-supported filters**: Efficient server-side filtering (recommended)
- **🔧 Client-side filters**: Requires fetching all data first, then filtering (use with caution on large datasets)

### get_tests - Filter Tests in a Run

Filter tests by assignment, priority, type, and status:

**Example: Get untested tests assigned to a user**
```json
{
  "run_id": "7420",
  "status_id": 3,
  "assignedto_id": 5
}
```

**Example: Get high priority tests**
```json
{
  "run_id": "7420",
  "priority_id": 2
}
```

**Example: Pagination**
```json
{
  "run_id": "7420",
  "limit": 50,
  "offset": 0
}
```

**Available Filters:**
- `status_id` (integer) - ✅ Filter by status (1=passed, 2=blocked, 3=untested, etc.)
- `assignedto_id` (integer) - 🔧 Filter by assigned user ID
- `priority_id` (integer) - 🔧 Filter by priority level
- `type_id` (integer) - 🔧 Filter by test type
- `limit` (integer) - ✅ Limit number of results
- `offset` (integer) - ✅ Pagination offset

### get_cases - Filter Test Cases

**Example: Filter by section and priority**
```json
{
  "project_id": "1",
  "suite_id": "2",
  "section_id": "10",
  "priority_id": "1,2"
}
```

**Available Filters:**
- All existing filters (created_by, updated_by, priority_id, type_id, milestone_id, created_after, created_before)
- `section_id` (integer/string) - ✅ Filter by section
- `template_id` (integer/string) - ✅ Filter by template
- `offset` (integer) - ✅ Pagination offset

### get_runs - Filter Test Runs

**Example: Filter by suite and completion**
```json
{
  "project_id": "1",
  "suite_id": "2",
  "is_completed": 0
}
```

**Available Filters:**
- `created_by` (integer/string) - ✅ Filter by creator
- `is_completed` (integer/boolean) - ✅ Filter by completion status
- `milestone_id` (integer/string) - ✅ Filter by milestone
- `suite_id` (integer/string) - ✅ Filter by suite
- `offset` (integer) - ✅ Pagination offset

### get_plans - Filter Test Plans

**Example: Filter by milestone and date range**
```json
{
  "project_id": "1",
  "milestone_id": "5",
  "created_after": 1609459200,
  "created_before": 1640995199
}
```

**Available Filters:**
- `created_by` (integer/string) - ✅ Filter by creator
- `created_after` (integer) - ✅ Unix timestamp
- `created_before` (integer) - ✅ Unix timestamp
- `milestone_id` (integer/string) - ✅ Filter by milestone
- `is_completed` (integer/boolean) - ✅ Filter by completion status
- `limit` (integer) - ✅ Limit results
- `offset` (integer) - ✅ Pagination offset

### get_users - Filter Users

**Example: Find users by name or email**
```json
{
  "name": "john"
}
```

```json
{
  "email": "@example.com",
  "project_id": 1
}
```

**Available Filters:**
- `project_id` (integer) - ✅ Filter by project
- `name` (string) - 🔧 Substring search (case-insensitive)
- `email` (string) - 🔧 Substring search (case-insensitive)

### get_milestones - Filter Milestones

**Example: Find active milestones by name**
```json
{
  "project_id": "1",
  "is_completed": false,
  "name": "Sprint"
}
```

**Available Filters:**
- `is_completed` (boolean) - ✅ Filter by completion status
- `is_started` (boolean) - ✅ Filter by start status
- `name` (string) - 🔧 Substring search (case-insensitive)

### Performance Considerations

- **API-supported filters (✅)**: Process data on the TestRail server (fast, efficient)
- **Client-side filters (🔧)**: Fetch all data first, then filter (slower for large datasets)
- For large datasets (>1000 records), prefer API-supported filters
- Use pagination (`limit` and `offset`) to manage large result sets

---

## Testing & Validation

The TestRail MCP Server includes a comprehensive test suite with **64 test scripts** (one for each tool) to validate your deployment.

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
- **Plans** (9 tests) - Test plan management
- **Tests** (2 tests) - Test instance queries
- **Results** (5 tests) - Result recording
- **Users** (3 tests) - User queries
- **Milestones** (5 tests) - Milestone management
- **Configurations** (3 tests) - Multi-platform testing configs

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

## Server Health Monitoring (v1.4.0)

The TestRail MCP Server includes comprehensive health monitoring to help you track server performance, diagnose issues, and understand operational metrics.

### Checking Server Health

Ask your AI:
```
"Check TestRail server health"
```

or

```
"Get server health status"
```

### Health Check Response

The health check provides detailed operational insights:

```json
{
  "status": "healthy",
  "caches": {
    "field_cache": {
      "loaded": true,
      "entries": 12
    },
    "status_cache": {
      "loaded": true,
      "entries": 7
    },
    "priority_cache": {
      "loaded": true,
      "entries": 5
    },
    "case_type_cache": {
      "loaded": true,
      "entries": 6
    }
  },
  "rate_limiter": {
    "current_tokens": 175,
    "max_tokens": 180,
    "capacity_percent": 97.22
  },
  "connection": "ready",
  "uptime_seconds": 8542.35,
  "uptime_formatted": "2h 22m 22s",
  "metrics": {
    "requests": {
      "total": 1247,
      "successful": 1198,
      "failed": 49,
      "error_rate": 3.93
    },
    "cache": {
      "hits": 856,
      "misses": 142,
      "hit_rate": 85.77
    },
    "timing": {
      "last_api_call": "2026-01-14T07:25:18Z",
      "seconds_since_last_call": 12.45
    }
  }
}
```

### Understanding Health Metrics

**Status Indicators**
- `healthy` - All caches loaded and operational
- `degraded` - One or more caches not initialized
- `connection: "ready"` - Server ready to handle requests

**Cache Information**
- Shows which caches are loaded (field, status, priority, case_type)
- Displays number of entries in each cache
- Helps diagnose cache-related issues

**Rate Limiter Stats**
- `current_tokens` - Available API calls in current window
- `max_tokens` - Maximum allowed (180 per minute)
- `capacity_percent` - Available capacity percentage

**Uptime Tracking**
- `uptime_seconds` - Server runtime in seconds
- `uptime_formatted` - Human-readable format (e.g., "2h 22m 22s")

**Request Metrics**
- `total` - Total API calls made
- `successful` - Successfully completed requests
- `failed` - Failed requests
- `error_rate` - Percentage of failed requests

**Cache Performance**
- `hits` - Cache lookups that found data
- `misses` - Cache lookups that didn't find data
- `hit_rate` - Cache effectiveness percentage (higher is better)

**Timing Information**
- `last_api_call` - ISO 8601 timestamp of last successful API call
- `seconds_since_last_call` - Time elapsed since last call

### Using Health Metrics

**Diagnose Performance Issues**
```
"Check server health - is cache working properly?"
```
- Look at `hit_rate` - Should be >70% for good performance
- Low hit rates may indicate cache isn't being used effectively

**Monitor Error Rates**
```
"What's the current error rate?"
```
- Check `error_rate` in metrics
- High error rates (>5%) indicate connectivity or configuration issues

**Check Rate Limiting**
```
"Are we hitting rate limits?"
```
- Look at `capacity_percent` in rate_limiter
- Values <20% mean you're close to rate limit
- Server automatically handles rate limiting with retries

**Verify Cache Status**
```
"Is the field cache loaded?"
```
- Check `caches.field_cache.loaded` status
- If false, run `get_case_fields` to populate

### Best Practices

1. **Check health after container restart** - Verify all caches initialized
2. **Monitor error rates** - Sustained high error rates need investigation
3. **Watch cache hit rates** - Low rates mean cache may need warming up
4. **Check uptime** - Confirms server stability and session duration
5. **Use before troubleshooting** - First step when diagnosing issues

### Troubleshooting with Health Check

**Problem: Slow performance**
- Check `cache.hit_rate` - Should be >70%
- Low hit rate? Run cache initialization commands
- Check `rate_limiter.capacity_percent` - May be rate limited

**Problem: Frequent errors**
- Check `metrics.requests.error_rate` - High rate indicates issues
- Review `last_api_call` - Recent activity or stale connection?
- Verify `connection: "ready"` status

**Problem: Cache not working**
- Check all cache `loaded` statuses
- Run initialization: `get_case_fields`, `get_statuses`, `get_priorities`, `get_case_types`
- Verify `entries` count is >0 for each cache

---

## Automatic Retry for Transient Failures (v1.4.0)

The TestRail MCP Server includes intelligent retry logic to handle temporary network issues and server errors automatically, improving reliability without user intervention.

### How It Works

**GET requests** automatically retry on transient failures with exponential backoff:
- **Retry attempts**: Up to 3 attempts total
- **Backoff timing**: 1s → 2s → 4s (exponential)
- **Total max time**: ~7 seconds for all retries

**POST/PUT/DELETE requests** never retry automatically to prevent duplicate operations (e.g., creating the same test case twice).

### What Triggers a Retry

The system automatically retries GET requests when encountering:

✅ **Network Errors**
- Connection timeouts
- Connection resets
- DNS resolution failures
- General network connectivity issues

✅ **Server Errors (5xx)**
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout

✅ **Rate Limiting (429)**
- Too Many Requests errors
- Respects `Retry-After` header if provided

### What Does NOT Trigger a Retry

❌ **Client Errors (4xx)** - These indicate issues with the request itself:
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found

❌ **Successful Responses (2xx, 3xx)** - No retry needed

❌ **Non-GET Operations** - POST, PUT, DELETE never retry

### Understanding Retry Logs

When a retry occurs, you'll see messages in stderr:

```
[RETRY] Attempt 1/3 failed: NetworkError. Retrying in 1.0s...
[RETRY] Attempt 2/3 failed: 503 Server Error. Retrying in 2.0s...
```

**Log Format**:
- `[RETRY]` - Indicates automatic retry in progress
- `Attempt X/3` - Which attempt failed (1-based)
- Error type - What caused the failure
- `Retrying in Xs` - Wait time before next attempt

### Example Scenarios

**Scenario 1: Transient Network Error (Auto-Recovered)**
```bash
# User asks: "Get all test cases in project 1"

# Behind the scenes (in logs):
[RETRY] Attempt 1/3 failed: NetworkError. Retrying in 1.0s...
# Success on 2nd attempt

# User sees: Normal successful response (no indication of retry)
```

**Scenario 2: Permanent Error (No Retry)**
```bash
# User asks: "Get test case 999999" (doesn't exist)

# No retry attempts - fails immediately with:
Error: 404 Not Found - Resource not found
```

**Scenario 3: POST Operation (No Retry)**
```bash
# User asks: "Create a test case with title 'Login Test'"

# If network error occurs:
Error: NetworkError - Connection failed

# NO retries - prevents duplicate test cases
```

### Troubleshooting Retry Behavior

**Seeing frequent retry logs?**
- Check your network connection stability
- Verify TestRail server is not experiencing issues
- Consider if you're hitting rate limits (slow down requests)

**Retries still failing after 3 attempts?**
- Network issue is persistent (not transient)
- TestRail server may be down (check status page)
- Check firewall/proxy settings blocking connection

**Want to see retry logs in Claude Desktop?**
- Check: `~/Library/Logs/Claude/mcp*.log` (macOS)
- Or: Check Docker logs: `docker logs <container-id>`

### Best Practices

1. **Be patient with GET requests** - They may take up to ~7s with retries
2. **Don't spam retries** - If it fails after 3 attempts, investigate the root cause
3. **Check logs** - Retry logs help diagnose network issues
4. **POST/DELETE are safe** - They never retry, so you won't create duplicates

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
cd /path/to/<your-repo>
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

**Version**: 1.5.0
**Maintainer**: <your-org> Team
