# Standalone MCP Server Setup Guide

## 🎯 Problem Solved

**Before**: MCP server only worked inside Software Factory directory  
**After**: MCP server works from ANY project directory and connects to remote Software Factory

## 🏗️ Architecture

```
┌─────────────────────┐     HTTP API     ┌─────────────────────┐
│   Software Factory  │◄─────────────────│  Standalone MCP     │
│   (Web App)         │                  │  Server             │
│   localhost:8000    │                  │  (Bridge)           │
└─────────────────────┘                  └─────────────────────┘
                                                     ▲
                                              MCP Protocol
                                                     │
                                         ┌─────────────────────┐
                                         │   External Project  │
                                         │   + Cursor/Claude   │
                                         │   /any/directory/   │
                                         └─────────────────────┘
```

## 🚀 Setup Instructions

### Step 1: Start Software Factory
```bash
cd /path/to/software-factory
python src/app.py  # Make sure it's running on localhost:8000
```

### Step 2: Go to Your External Project
```bash
cd /path/to/your-other-project  # Any project directory
ls  # your-project-files.py, README.md, etc.
```

### Step 3: Connect Cursor to Standalone MCP Server
```bash
# From your external project directory
cursor mcp add sf-tasks -- python /path/to/software-factory/standalone_mcp_server.py

# Or for Claude Code:
claude mcp add sf-tasks -- python /path/to/software-factory/standalone_mcp_server.py
```

### Step 4: Use in Cursor/Claude Code
```
"List my Software Factory projects"
"Get tasks for project project_123 that I can work on here"  
"Get implementation context for task project_123_task_5"
"Help me implement this OAuth feature in this codebase"
"Mark task project_123_task_5 complete with files ['auth.py', 'test_auth.py']"
```

## 🔧 Available MCP Tools

### 1. Project Discovery
- **`list_software_factory_projects()`** - See all projects in Software Factory
- **`get_current_directory()`** - Check where you're working locally

### 2. Task Management  
- **`get_project_tasks_for_current_work(project_id, status)`** - Get tasks you can implement locally
- **`get_task_implementation_context(task_id)`** - Get full context for local implementation

### 3. Progress Updates
- **`update_software_factory_task(task_id, status, message)`** - Update task progress
- **`mark_task_complete_with_local_work(task_id, notes, files, commit)`** - Mark complete with local details

### 4. Information
- **`get_mcp_server_info()`** - Check server status and usage info

## 📋 Example Workflow

### Scenario: Implement Software Factory task in external React project

```bash
# 1. You're working on external React project
cd /Users/john/projects/my-react-app

# 2. Connect Cursor to Software Factory
cursor mcp add sf-tasks -- python /Users/john/software-factory/standalone_mcp_server.py

# 3. In Cursor, ask:
"List my Software Factory projects"
```

**Response:**
```json
{
  "projects": [
    {"id": "proj_123", "name": "Mobile App Features", "description": "New features for mobile app"}
  ]
}
```

```
"Get ready tasks for project proj_123 that I can implement here"
```

**Response:**
```json
{
  "software_factory_project": "proj_123",
  "local_working_directory": "/Users/john/projects/my-react-app",
  "tasks": [
    {
      "id": "proj_123_task_oauth",
      "title": "Add OAuth login component", 
      "description": "Implement OAuth login with Google",
      "likely_touches": ["src/components/Login.tsx", "src/auth/oauth.ts"]
    }
  ]
}
```

```
"Get implementation context for task proj_123_task_oauth"
```

**Response:**
```json
{
  "task_from_software_factory": {
    "requirements": "OAuth login with Google provider",
    "acceptance_criteria": "Users can log in with Google account",
    "design_notes": "Follow Material-UI design patterns"
  },
  "local_implementation_environment": {
    "working_directory": "/Users/john/projects/my-react-app",
    "is_git_repository": true,
    "git_info": {
      "current_branch": "feature/oauth-login",
      "remote_url": "https://github.com/john/my-react-app"
    },
    "suggested_approach": "Implement the OAuth requirements in this React project"
  }
}
```

```
"Help me implement OAuth login component based on this context"
```

**Cursor implements the feature with full context...**

```
"Mark task proj_123_task_oauth complete with files ['src/components/Login.tsx', 'src/auth/oauth.ts']"
```

**Response:**
```json
{
  "task_id": "proj_123_task_oauth",
  "marked_complete_from": "/Users/john/projects/my-react-app",
  "completion_notes": "OAuth login implemented",
  "local_context": {
    "files_modified": ["src/components/Login.tsx", "src/auth/oauth.ts"],
    "git_info": {
      "latest_commit": "abc123def456",
      "repository": "https://github.com/john/my-react-app"
    }
  }
}
```

## ⚙️ Configuration

### Environment Variables
```bash
# Optional: Set Software Factory URL (defaults to localhost:8000)
export SF_BASE_URL="http://localhost:8000"

# Optional: Set API key for authentication
export SF_API_KEY="your-api-key"
```

### Software Factory API Endpoints Used
- `GET /api/mission-control/projects` - List projects (✅ Fixed)
- `GET /api/tasks?project_id=X` - Get project tasks (✅ Fixed)
- `GET /api/tasks/{id}` - Get task details (✅ Working)
- `PATCH /api/tasks/{id}/update-field` - Update task status (✅ Fixed)

## 🚨 Troubleshooting

### "Connection Error"
- Make sure Software Factory is running on `localhost:8000`
- Check `SF_BASE_URL` environment variable
- Verify API endpoints are accessible

### "No Projects Found" 
- Make sure you have projects created in Software Factory
- Check if API authentication is required

### "MCP Server Not Found"
- Use absolute path to `standalone_mcp_server.py`
- Make sure Python dependencies are installed in Software Factory environment

## 🎉 Benefits

✅ **Work from any directory** - Not limited to Software Factory folder  
✅ **Cross-project development** - Use Software Factory to manage tasks for any codebase  
✅ **Preserve local workflow** - Keep using your preferred project structure  
✅ **Bi-directional sync** - Update Software Factory from external projects  
✅ **Rich context** - Get full task requirements in your local environment  
✅ **Git integration** - Automatically capture commit info and file changes

This solves your use case perfectly - you can now manage tasks in Software Factory but implement them in any project directory with your preferred coding assistant!