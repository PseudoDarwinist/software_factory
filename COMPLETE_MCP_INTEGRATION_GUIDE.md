# Complete MCP Integration Guide - Software Factory

## 🎯 Overview

Software Factory now has **complete MCP integration** covering the entire Think → Define → Plan → Build workflow, allowing you to use any MCP-compatible coding assistant (Claude Code, Cursor, etc.) to manage your software development lifecycle.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           SOFTWARE FACTORY MCP ECOSYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  THINK STAGE           DEFINE STAGE           PLAN STAGE            BUILD STAGE     │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐    │
│  │ 💡 Ideas    │────► │ 📝 Specs    │────► │ 📋 Tasks    │────► │ ⚡ Code     │    │
│  │             │      │             │      │             │      │             │    │
│  │ MCP Tools:  │      │ MCP Tools:  │      │ MCP Tools:  │      │ MCP Tools:  │    │
│  │ • get_ideas │      │ • generate_ │      │ • get_task_ │      │ • get_task_ │    │
│  │   _without_ │      │   missing_  │      │   context   │      │   repo_info │    │
│  │   specs     │      │   specs     │      │ • update_   │      │ • mark_     │    │
│  │ • get_spec_ │      │ • update_   │      │   task_     │      │   complete  │    │
│  │   status    │      │   spec_     │      │   status    │      │             │    │
│  └─────────────┘      │   artifact  │      └─────────────┘      └─────────────┘    │
│                       └─────────────┘                                              │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                          MCP SERVER OPTIONS                                │   │
│  │                                                                             │   │
│  │  1. Built-in MCP Server (src.mcp.server)                                  │   │
│  │     • For working ON Software Factory itself                              │   │
│  │     • Full database access and context                                    │   │
│  │                                                                             │   │
│  │  2. Standalone MCP Server (standalone_mcp_server.py)                      │   │
│  │     • For working on EXTERNAL projects                                    │   │
│  │     • Connects to Software Factory via HTTP API                          │   │
│  │     • Can run from any directory                                          │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 🔧 MCP Tools by Stage

### **Think Stage Tools**
- **`get_ideas_without_specs(project_id?)`** - Find ideas ready for specification
- **`get_ideas_with_incomplete_specs(project_id?)`** - Find partially specified ideas
- **`get_spec_generation_status(idea_id, project_id)`** - Check spec completion

### **Define Stage Tools**  
- **`generate_missing_specs_for_idea(idea_id, project_id, spec_types?, context?)`** - Generate specs
- **`update_specification_artifact(project_id, spec_id, type, content, reason?)`** - Update specs
- **`create_requirements(project_id, feature_name, content, idea_id?)`** - Create requirements.md
- **`create_design(project_id, spec_id, content)`** - Create design.md
- **`create_tasks(project_id, spec_id, content)`** - Create tasks.md

### **Plan Stage Tools**
- **`get_project_tasks(project_id, status_filter?)`** - Get task Kanban cards
- **`get_task_context(task_id)`** - Get comprehensive task context
- **`get_task_repository_info(task_id)`** - Get repo/branch info for task

### **Build Stage Tools**
- **`update_task_status(task_id, status, message?)`** - Update task progress
- **`mark_task_complete(task_id, notes?, pr_url?)`** - Complete task with PR link
- **`get_current_directory()`** - Check local working environment
- **`mark_task_complete_with_local_work(task_id, notes, files?, commit?)`** - Complete with local details

## 📋 Configuration Setup

### Your Updated MCP Config

```json
{
  "mcpServers": {
    "software-factory": {
      "command": "python3",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/Users/chetansingh/Documents/AI_Project/Software_Factory",
      "env": {
        "PYTHONPATH": "/Users/chetansingh/Documents/AI_Project/Software_Factory",
        "DATABASE_URL": "postgresql://sf_user:sf_password@localhost/software_factory",
        "FLASK_ENV": "development"
      },
      "disabled": false,
      "autoApprove": [
        "list_projects", "get_project_context", "create_requirements",
        "create_design", "create_tasks", "get_idea_details",
        "get_project_tasks", "get_task_context", "get_task_repository_info",
        "mark_task_complete", "update_task_status",
        "get_ideas_without_specs", "get_ideas_with_incomplete_specs",
        "update_specification_artifact", "generate_missing_specs_for_idea",
        "get_spec_generation_status"
      ]
    },
    "sf-external-tasks": {
      "command": "python3",
      "args": ["/Users/chetansingh/Documents/AI_Project/Software_Factory/standalone_mcp_server.py"],
      "env": {
        "SF_BASE_URL": "http://localhost:8000",
        "PYTHONPATH": "/Users/chetansingh/Documents/AI_Project/Software_Factory"
      },
      "disabled": false,
      "autoApprove": [
        "get_current_directory", "list_software_factory_projects",
        "get_project_tasks_for_current_work", "get_task_implementation_context",
        "update_software_factory_task", "mark_task_complete_with_local_work",
        "get_mcp_server_info"
      ]
    }
  }
}
```

## 🚀 Usage Examples

### **Complete Workflow Example**

#### **Think → Define**
```
Developer: "Show me ideas that need specifications"
Claude: [Calls get_ideas_without_specs()]

Found 3 ideas without specs:
• OAuth login for mobile app (severity: amber)
• Push notifications (severity: red)  
• Offline data sync (severity: info)

Developer: "Generate complete specifications for OAuth login idea"
Claude: [Calls generate_missing_specs_for_idea()]

✅ Generated complete specifications:
• requirements.md - User stories and acceptance criteria
• design.md - Technical architecture and API design
• tasks.md - Implementation breakdown with 8 tasks

Developer: "Update the OAuth requirements to include Apple Sign-In"
Claude: [Calls update_specification_artifact()]

✅ Updated requirements.md
Status reset to 'AI Draft' for human review
```

#### **Plan → Build (External Project)**
```
# Working in external React Native project
cd /Users/dev/my-react-native-app

Developer: "Get ready tasks from Software Factory that I can work on here"
Claude: [Calls get_project_tasks_for_current_work()]

Found 2 ready tasks for Mobile App project:
• Task 1.1: Implement OAuth login service
• Task 1.2: Create login UI components

Working in: /Users/dev/my-react-native-app

Developer: "Get implementation context for OAuth login task"
Claude: [Calls get_task_implementation_context()]

**From Software Factory:**
- Requirements: OAuth with Google/Apple
- Files to modify: src/auth/OAuthService.js, src/components/LoginScreen.js
- Acceptance criteria: JWT tokens, secure storage, error handling

**Your Local Environment:**  
- React Native project with existing auth structure
- Git repo: https://github.com/dev/my-react-native-app
- Current branch: feature/oauth-login

Developer: "Help me implement OAuth service based on this context"
Claude: [Implements OAuthService.js with full context]

Developer: "Mark task complete with OAuth implementation"
Claude: [Calls mark_task_complete_with_local_work()]

✅ Task marked complete in Software Factory
- Files: OAuthService.js, LoginScreen.js, AuthTests.js
- Commit: abc123def456
- Repository: https://github.com/dev/my-react-native-app
```

## 🎯 Use Cases Solved

### **1. Think Stage Management**
- **Problem**: Hard to track which ideas need specifications  
- **Solution**: `get_ideas_without_specs()` shows all ideas ready for Define stage

### **2. Batch Spec Generation**
- **Problem**: Creating requirements, design, and tasks separately is tedious
- **Solution**: `generate_missing_specs_for_idea()` creates all three specs at once

### **3. Spec Quality Improvement** 
- **Problem**: Need to update existing specs but hard to track changes
- **Solution**: `update_specification_artifact()` with tracked update reasons

### **4. Cross-Project Development**
- **Problem**: Want to use Software Factory for task management but implement in different codebases
- **Solution**: Standalone MCP server bridges SF tasks to any project directory

### **5. Repository Context Integration**
- **Problem**: Coding assistants lack context about file structure and requirements
- **Solution**: `get_task_context()` provides comprehensive implementation context

## 🔄 Workflow States & Transitions

### **Specification Status Flow**
```
AI Draft → Human Reviewed → Frozen
   ↑              ↑           ↑
   │              │           └─ Ready for Plan stage
   │              └─ Manual review completed  
   └─ Generated via MCP or updated
```

### **Task Status Flow**
```
Ready → Running → Review → Done
  ↑       ↑        ↑      ↑
  │       │        │      └─ Completed via MCP
  │       │        └─ PR created, awaiting approval
  │       └─ Started via Plan UI or MCP
  └─ Generated from frozen specs
```

## 🧪 Testing & Validation

### **Test Your Setup**
```bash
# Test built-in MCP server (for SF development)
cd /Software_Factory
python test_think_define_mcp.py

# Test standalone MCP server (for external projects) 
cd /any-external-project
python /Software_Factory/test_standalone_mcp.py
```

### **Verify Configuration**
```bash
# Check MCP server registration
claude mcp list

# Test specific tools
claude mcp test software-factory get_ideas_without_specs
```

## 🌟 Key Benefits Achieved

✅ **Complete SDLC Coverage** - MCP tools for all 4 stages  
✅ **Bring Your Own Assistant** - Works with Claude Code, Cursor, any MCP client  
✅ **Cross-Project Development** - Use SF for any codebase  
✅ **Non-Breaking Integration** - Existing workflows preserved  
✅ **Rich Context** - Full project/task/spec context available to assistants  
✅ **Quality Control** - All MCP updates trigger proper review workflows  
✅ **Bi-directional Sync** - Local changes update Software Factory  
✅ **Repository Awareness** - Assistants understand codebase structure  

## 🎉 What You Can Now Do

1. **Manage Ideas**: Find and process Think stage ideas into specifications
2. **Generate Specs**: Create complete requirements, design, and task docs with AI
3. **Update Specifications**: Improve existing specs with tracked changes
4. **Cross-Project Tasks**: Implement SF tasks in any external project
5. **Context-Rich Development**: Coding assistants have full SF context
6. **Seamless Workflow**: Complete Think → Define → Plan → Build flow via MCP
7. **Quality Assurance**: All changes maintain proper review and approval states

Your Software Factory is now **fully MCP-enabled** across the entire development lifecycle! 🚀