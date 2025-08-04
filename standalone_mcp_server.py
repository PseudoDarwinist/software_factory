#!/usr/bin/env python3
"""
Standalone MCP Server for External Projects
Connects to Software Factory via HTTP API to access tasks and workflow context
while working in external project directories.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import MCP library
try:
    from mcp.server.fastmcp import FastMCP, Context
    from mcp.types import Tool, TextContent, SamplingMessage, CreateMessageRequest, CreateMessageResult
    from mcp.shared.exceptions import McpError
except ImportError:
    print("Error: MCP library not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Initialize FastMCP server with sampling capability
mcp = FastMCP("software-factory-external")

class SoftwareFactoryClient:
    """Client to communicate with Software Factory API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_projects(self) -> List[Dict]:
        """Get all projects from Software Factory"""
        try:
            response = self.session.get(f"{self.base_url}/api/mission-control/projects")
            response.raise_for_status()
            data = response.json()
            # Handle the API response format which has a 'data' field
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, list):
                return data
            else:
                logger.error(f"Unexpected response format: {data}")
                return []
        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            return []
    
    def get_project_tasks(self, project_id: str, status: str = None) -> List[Dict]:
        """Get tasks for a specific project, optionally filtered by status"""
        try:
            url = f"{self.base_url}/api/tasks?project_id={project_id}"
            if status:
                url += f"&status={status}"
            
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Handle the API response format which might have a 'tasks' field
            if isinstance(data, dict) and 'tasks' in data:
                return data['tasks']
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, list):
                return data
            else:
                logger.error(f"Unexpected response format: {data}")
                return []
        except Exception as e:
            logger.error(f"Failed to get project tasks: {e}")
            return []
    
    def get_task_detail(self, task_id: str) -> Dict:
        """Get detailed information about a specific task"""
        try:
            response = self.session.get(f"{self.base_url}/api/tasks/{task_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get task detail: {e}")
            return {}
    
    def update_task(self, task_id: str, updates: Dict) -> Dict:
        """Update a task with new information"""
        try:
            response = self.session.patch(f"{self.base_url}/api/tasks/{task_id}/update-field", json=updates)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to update task: {e}")
            return {}
    
    def mark_task_complete(self, task_id: str, completion_notes: str = "") -> Dict:
        """Mark a task as complete"""
        try:
            data = {"status": "completed", "completion_notes": completion_notes}
            response = self.session.patch(f"{self.base_url}/api/tasks/{task_id}/update-field", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to mark task complete: {e}")
            return {}
    
    def get_ideas_without_specs(self) -> List[Dict]:
        """Get ideas that don't have specifications yet (Define phase only)"""
        try:
            response = self.session.get(f"{self.base_url}/api/mcp/ideas/without-specs")
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'ideas_without_specs' in data:
                return data['ideas_without_specs']
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error(f"Failed to get ideas without specs: {e}")
            return []
    
    def generate_spec(self, idea_id: str, project_context: str = "") -> Dict:
        """Generate a specification for an idea"""
        try:
            data = {"idea_id": idea_id, "project_context": project_context}
            response = self.session.post(f"{self.base_url}/api/specs/generate", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to generate spec: {e}")
            return {}
    
    def update_spec_with_payload(self, payload: Dict) -> Dict:
        """Update a specification using the correct MCP API endpoint with full payload"""
        try:
            response = self.session.put(f"{self.base_url}/api/mcp/specs/update", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to update spec: {e}")
            return {"success": False, "error": str(e)}
    
    def update_spec(self, spec_id: str, updates: Dict) -> Dict:
        """Legacy update method - kept for compatibility"""
        return {"success": False, "error": "Use update_spec_with_payload instead"}
    
    def create_spec_from_idea(self, idea_id: str, spec_data: Dict) -> Dict:
        """Create a new specification from an idea"""
        try:
            # Use the existing generate_spec endpoint
            context = spec_data.get("updated_from", "External MCP generation")
            response = self.session.post(f"{self.base_url}/api/ideas/{idea_id}/generate-spec", 
                                       json={"context": context})
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                # Now update the created spec with our content
                spec_id = result.get('spec_id')
                if spec_id:
                    update_response = self.session.patch(f"{self.base_url}/api/specs/{spec_id}", json=spec_data)
                    if update_response.status_code == 200:
                        return {"success": True, "spec_id": spec_id, "message": "Spec created and updated"}
            
            return result
        except Exception as e:
            logger.error(f"Failed to create spec from idea: {e}")
            return {"success": False, "error": str(e)}
    
    def get_spec_status(self, spec_id: str) -> Dict:
        """Get the status of a specification"""
        try:
            response = self.session.get(f"{self.base_url}/api/specs/{spec_id}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get spec status: {e}")
            return {}

# Initialize client
sf_client = SoftwareFactoryClient()

def get_git_info() -> Dict[str, str]:
    """Get current git repository information"""
    try:
        cwd = os.getcwd()
        
        try:
            remote_url = subprocess.check_output(
                ["git", "remote", "get-url", "origin"], 
                cwd=cwd, 
                stderr=subprocess.DEVNULL,
                timeout=5
            ).decode().strip()
        except:
            remote_url = "unknown"
        
        try:
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"], 
                cwd=cwd, 
                stderr=subprocess.DEVNULL,
                timeout=5
            ).decode().strip()
        except:
            branch = "unknown"
        
        repo_name = remote_url.split("/")[-1].replace(".git", "") if remote_url != "unknown" else "unknown"
        
        return {
            "repository_url": remote_url,
            "current_branch": branch,
            "repository_name": repo_name,
            "working_directory": cwd
        }
    except Exception as e:
        logger.error(f"Failed to get git info: {e}")
        return {
            "repository_url": "unknown",
            "current_branch": "unknown", 
            "repository_name": "unknown",
            "working_directory": os.getcwd()
        }

@mcp.tool()
def get_available_projects() -> str:
    """Get all available projects from Software Factory"""
    try:
        logger.info("Starting get_available_projects")
        projects = sf_client.get_projects()
        logger.info(f"Retrieved projects: {projects}")
        logger.info(f"Projects type: {type(projects)}")
        
        if not projects:
            return "No projects found or failed to connect to Software Factory"
        
        result = "Available Software Factory Projects:\n\n"
        for i, project in enumerate(projects):
            logger.info(f"Processing project {i}: {project} (type: {type(project)})")
            if isinstance(project, dict):
                result += f"ID: {project.get('id', 'N/A')}\n"
                result += f"Name: {project.get('name', 'N/A')}\n"
                result += f"Description: {project.get('description', 'N/A')}\n"
                result += f"Health: {project.get('health', 'N/A')}\n"
                result += f"Repo URL: {project.get('repoUrl', 'N/A')}\n"
                result += "---\n"
            else:
                logger.error(f"Project is not a dict: {type(project)} - {project}")
                result += f"Invalid project data: {project}\n---\n"
        
        logger.info(f"Returning result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in get_available_projects: {e}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        return f"Error retrieving projects: {str(e)}"

@mcp.tool()
def get_project_tasks_for_external_work(project_id: str, status: str = None) -> str:
    """Get tasks for a specific project to understand work context for external development
    
    Args:
        project_id: The project ID to get tasks for
        status: Optional status filter (e.g., 'ready', 'in_progress', 'completed')
    """
    try:
        tasks = sf_client.get_project_tasks(project_id, status)
        git_info = get_git_info()
        
        logger.info(f"Retrieved {len(tasks)} tasks for project {project_id} with status filter: {status}")
        
        if not tasks:
            status_msg = f" with status '{status}'" if status else ""
            return f"No tasks found for project {project_id}{status_msg} or failed to connect to Software Factory"
        
        status_msg = f" (Status: {status})" if status else ""
        result = f"Tasks for Project {project_id}{status_msg}:\n"
        result += f"Current Git Context: {git_info['repository_name']} ({git_info['current_branch']})\n"
        result += f"Working Directory: {git_info['working_directory']}\n\n"
        
        for task in tasks:
            if isinstance(task, dict):
                result += f"Task ID: {task.get('id', 'N/A')}\n"
                result += f"Task Number: {task.get('task_number', 'N/A')}\n"
                result += f"Title: {task.get('title', 'N/A')}\n"
                result += f"Description: {task.get('description', 'N/A')}\n"
                result += f"Status: {task.get('status', 'N/A')}\n"
                result += f"Priority: {task.get('priority', 'N/A')}\n"
                result += f"Stage: {task.get('stage', 'N/A')}\n"
                result += f"Assignee: {task.get('assignee', 'N/A')}\n"
                result += f"Estimate: {task.get('estimate', 'N/A')}\n"
                result += "---\n"
            else:
                logger.error(f"Task is not a dict: {type(task)} - {task}")
                result += f"Invalid task data: {task}\n---\n"
        
        return result
    except Exception as e:
        logger.error(f"Error in get_project_tasks_for_external_work: {e}")
        return f"Error retrieving tasks for project {project_id}: {str(e)}"

@mcp.tool()
def get_current_git_context() -> str:
    """Get current git repository context for external project work"""
    git_info = get_git_info()
    
    result = "Current Git Context:\n\n"
    result += f"Repository URL: {git_info['repository_url']}\n"
    result += f"Repository Name: {git_info['repository_name']}\n"
    result += f"Current Branch: {git_info['current_branch']}\n"
    result += f"Working Directory: {git_info['working_directory']}\n"
    
    # Get recent commits
    try:
        recent_commits = subprocess.check_output(
            ["git", "log", "--oneline", "-5"], 
            cwd=git_info['working_directory'], 
            stderr=subprocess.DEVNULL,
            timeout=5
        ).decode().strip()
        result += f"\nRecent Commits:\n{recent_commits}\n"
    except Exception:
        result += "\nRecent Commits: Unable to retrieve\n"
    
    # Get current status
    try:
        git_status = subprocess.check_output(
            ["git", "status", "--porcelain"], 
            cwd=git_info['working_directory'], 
            stderr=subprocess.DEVNULL,
            timeout=5
        ).decode().strip()
        if git_status:
            result += f"\nWorking Directory Status:\n{git_status}\n"
        else:
            result += f"\nWorking Directory: Clean\n"
    except Exception:
        result += "\nWorking Directory Status: Unable to retrieve\n"
    
    return result

@mcp.tool()
def get_current_directory() -> str:
    """Get the current working directory"""
    try:
        cwd = os.getcwd()
        git_info = get_git_info()
        
        result = f"Current Working Directory: {cwd}\n"
        result += f"Git Repository: {git_info['repository_name']}\n"
        result += f"Current Branch: {git_info['current_branch']}\n"
        result += f"Repository URL: {git_info['repository_url']}\n"
        
        return result
    except Exception as e:
        logger.error(f"Error in get_current_directory: {e}")
        return f"Error getting current directory: {str(e)}"

@mcp.tool()
def list_software_factory_projects() -> str:
    """List all Software Factory projects (alias for get_available_projects)"""
    return get_available_projects()

@mcp.tool()
def get_project_tasks_for_current_work(project_id: str, status: str = None) -> str:
    """Get tasks for current work context (alias for get_project_tasks_for_external_work)"""
    return get_project_tasks_for_external_work(project_id, status)

@mcp.tool()
def get_task_implementation_context(task_id: str) -> str:
    """Get detailed context for implementing a specific task"""
    try:
        task_detail = sf_client.get_task_detail(task_id)
        git_info = get_git_info()
        
        if not task_detail:
            return f"Task {task_id} not found or failed to connect to Software Factory"
        
        result = f"Task Implementation Context for {task_id}:\n\n"
        result += f"Current Git Context: {git_info['repository_name']} ({git_info['current_branch']})\n"
        result += f"Working Directory: {git_info['working_directory']}\n\n"
        
        result += f"Task Details:\n"
        result += f"ID: {task_detail.get('id', 'N/A')}\n"
        result += f"Title: {task_detail.get('title', 'N/A')}\n"
        result += f"Description: {task_detail.get('description', 'N/A')}\n"
        result += f"Status: {task_detail.get('status', 'N/A')}\n"
        result += f"Priority: {task_detail.get('priority', 'N/A')}\n"
        result += f"Assignee: {task_detail.get('assigned_to', 'N/A')}\n"
        result += f"Estimate: {task_detail.get('effort_estimate_hours', 'N/A')} hours\n"
        result += f"Dependencies: {task_detail.get('depends_on', [])}\n"
        result += f"Related Files: {task_detail.get('related_files', [])}\n"
        result += f"Related Components: {task_detail.get('related_components', [])}\n"
        
        if task_detail.get('requirements_refs'):
            result += f"Requirements References: {task_detail.get('requirements_refs', [])}\n"
        
        return result
    except Exception as e:
        logger.error(f"Error in get_task_implementation_context: {e}")
        return f"Error retrieving task context for {task_id}: {str(e)}"

@mcp.tool()
def update_software_factory_task(task_id: str, field: str, value: str) -> str:
    """Update a specific field of a Software Factory task"""
    try:
        updates = {field: value}
        result = sf_client.update_task(task_id, updates)
        
        if result.get('success'):
            return f"Successfully updated task {task_id}: {field} = {value}"
        else:
            return f"Failed to update task {task_id}: {result.get('error', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error in update_software_factory_task: {e}")
        return f"Error updating task {task_id}: {str(e)}"

@mcp.tool()
def mark_task_complete_with_local_work(task_id: str, completion_notes: str = "") -> str:
    """Mark a task as complete with notes about local work done"""
    try:
        git_info = get_git_info()
        
        # Add git context to completion notes
        full_notes = f"Completed in {git_info['repository_name']} on branch {git_info['current_branch']}"
        if completion_notes:
            full_notes += f"\n\nNotes: {completion_notes}"
        
        result = sf_client.mark_task_complete(task_id, full_notes)
        
        if result.get('success'):
            return f"Successfully marked task {task_id} as complete"
        else:
            return f"Failed to mark task {task_id} as complete: {result.get('error', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error in mark_task_complete_with_local_work: {e}")
        return f"Error marking task {task_id} as complete: {str(e)}"

@mcp.tool()
def get_ideas_without_specs_external() -> str:
    """Get ideas that don't have specifications yet for external project work"""
    try:
        ideas = sf_client.get_ideas_without_specs()
        
        if not ideas:
            return "No ideas without specifications found or failed to connect to Software Factory"
        
        result = "Ideas Without Specifications:\n\n"
        for idea in ideas:
            if isinstance(idea, dict):
                result += f"ID: {idea.get('id', 'N/A')}\n"
                result += f"Title: {idea.get('title', 'N/A')}\n"
                result += f"Summary: {idea.get('summary', idea.get('description', 'N/A'))}\n"
                result += f"Stage: {idea.get('stage', 'define')}\n"
                result += f"Priority: {idea.get('severity', idea.get('priority', 'N/A'))}\n"
                result += f"Created: {idea.get('created_at', 'N/A')}\n"
                result += "---\n"
            else:
                result += f"Invalid idea data: {idea}\n---\n"
        
        return result
    except Exception as e:
        logger.error(f"Error in get_ideas_without_specs_external: {e}")
        return f"Error retrieving ideas: {str(e)}"

def generate_comprehensive_requirements(
    idea_title: str,
    idea_summary: str,
    project_context: str,
    git_info: dict
) -> str:
    """Generate comprehensive requirements using EARS and IEEE 830 standards"""
    
    repo_name = git_info.get('repository_name', 'Unknown Project')
    current_branch = git_info.get('current_branch', 'unknown')
    
    return f"""# Requirements Specification: {idea_title}

## Document Information
- **Project**: {repo_name}
- **Branch**: {current_branch}
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Framework**: EARS (Easy Approach to Requirements Syntax) + IEEE 830

## 1. Overview

### 1.1 Problem Statement
{idea_summary}

**Context**: {project_context}

### 1.2 Stakeholder Analysis
- **Primary Users**: End users requiring {idea_title.lower()} functionality
- **System Administrators**: Responsible for deployment and maintenance
- **Development Team**: Implementation and testing
- **Business Stakeholders**: ROI and feature adoption tracking

### 1.3 Success Metrics (SMART Criteria)
- **Specific**: {idea_title} functionality fully operational
- **Measurable**: 95% feature adoption rate within 30 days
- **Achievable**: Based on current system architecture capabilities
- **Relevant**: Addresses identified user pain points
- **Time-bound**: Implementation complete within current sprint cycle

## 2. Functional Requirements (EARS Format)

### FR-001: Core Functionality
**WHEN** a user initiates {idea_title.lower()}
**THE SYSTEM SHALL** provide the requested functionality
**WHERE** the user has appropriate permissions
**SO THAT** the business objective is achieved

### FR-002: Input Validation
**WHEN** invalid input is provided
**THE SYSTEM SHALL** display clear error messages
**AND** guide the user to correct input format
**SO THAT** user experience remains positive

### FR-003: Data Persistence
**WHEN** {idea_title.lower()} operations are performed
**THE SYSTEM SHALL** persist all relevant data
**WHERE** data integrity constraints are met
**SO THAT** information is available for future operations

### FR-004: Integration Points
**WHEN** {idea_title.lower()} interacts with existing system components
**THE SYSTEM SHALL** maintain data consistency
**AND** preserve existing functionality
**SO THAT** system reliability is maintained

## 3. Non-Functional Requirements

### NFR-001: Performance Requirements
- **Response Time**: 95% of operations complete within 2 seconds
- **Throughput**: Support minimum 100 concurrent users
- **Scalability**: Linear performance degradation up to 1000 users

### NFR-002: Reliability Requirements
- **Availability**: 99.9% uptime during business hours
- **Error Rate**: Less than 0.1% of operations result in errors
- **Recovery Time**: System recovery within 5 minutes of failure

### NFR-003: Security Requirements
- **Authentication**: All operations require valid user authentication
- **Authorization**: Role-based access control implementation
- **Data Protection**: Encryption of sensitive data at rest and in transit
- **Audit Trail**: Complete logging of all user actions

### NFR-004: Usability Requirements
- **Learning Curve**: New users productive within 15 minutes
- **Accessibility**: WCAG 2.1 AA compliance
- **Mobile Responsiveness**: Full functionality on mobile devices
- **Browser Support**: Compatible with latest 2 versions of major browsers

## 4. Technical Constraints

### TC-001: Technology Stack Alignment
**THE SYSTEM SHALL** utilize existing technology stack components
**WHERE** integration is technically feasible
**SO THAT** maintenance overhead is minimized

### TC-002: Database Compatibility
**THE SYSTEM SHALL** work with current database schema
**WHERE** modifications are backward compatible
**SO THAT** existing data integrity is preserved

### TC-003: API Consistency
**THE SYSTEM SHALL** follow established API patterns
**WHERE** new endpoints are required
**SO THAT** client integration remains consistent

## 5. Acceptance Criteria

### AC-001: Functional Validation
- [ ] All functional requirements are implemented and tested
- [ ] Integration with existing systems is seamless
- [ ] User workflows are intuitive and efficient
- [ ] Error handling provides meaningful feedback

### AC-002: Performance Validation
- [ ] Response time requirements are met under normal load
- [ ] System remains stable under peak load conditions
- [ ] Resource utilization is within acceptable limits
- [ ] Scalability targets are achieved

### AC-003: Security Validation
- [ ] Security requirements are implemented and verified
- [ ] Penetration testing shows no critical vulnerabilities
- [ ] Data protection measures are effective
- [ ] Audit logging captures all required events

## 6. Risk Assessment

### High Risk Items
- **Integration Complexity**: Potential conflicts with existing system components
- **Performance Impact**: New functionality may affect existing performance
- **Data Migration**: Existing data may require transformation

### Mitigation Strategies
- **Phased Implementation**: Gradual rollout to minimize impact
- **Comprehensive Testing**: Extensive testing in staging environment
- **Rollback Plan**: Ability to quickly revert changes if issues arise

## 7. Dependencies

### Internal Dependencies
- Database schema modifications approved
- API gateway configuration updated
- Authentication service integration complete

### External Dependencies
- Third-party service availability
- Network infrastructure capacity
- Security compliance approval

---

*This requirements specification follows EARS (Easy Approach to Requirements Syntax) and IEEE 830 standards for comprehensive, unambiguous requirements documentation.*
"""

def generate_comprehensive_design(
    idea_title: str,
    idea_summary: str,
    project_context: str,
    git_info: dict
) -> str:
    """Generate comprehensive design using architectural patterns and best practices"""
    
    repo_name = git_info.get('repository_name', 'Unknown Project')
    current_branch = git_info.get('current_branch', 'unknown')
    
    return f"""# Technical Design Specification: {idea_title}

## Document Information
- **Project**: {repo_name}
- **Branch**: {current_branch}
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Architecture Patterns**: Clean Architecture, SOLID Principles, Domain-Driven Design

## 1. Architecture Overview

### 1.1 Design Philosophy
This design follows **Clean Architecture** principles to ensure:
- **Independence**: Business logic independent of frameworks and external concerns
- **Testability**: All components can be tested in isolation
- **Maintainability**: Clear separation of concerns and dependencies
- **Scalability**: Architecture supports horizontal and vertical scaling

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Web UI    │  │   REST API  │  │   GraphQL   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Use Cases │  │  Controllers│  │  Validators │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                    Domain Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Entities   │  │   Services  │  │ Repositories│     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                Infrastructure Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Database   │  │   Cache     │  │  External   │     │
│  │             │  │             │  │   APIs      │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Component Interaction Flow

1. **Request Initiation**: User interaction triggers request through presentation layer
2. **Input Validation**: Application layer validates and sanitizes input
3. **Business Logic**: Domain layer processes business rules and logic
4. **Data Persistence**: Infrastructure layer handles data storage and retrieval
5. **Response Formation**: Results flow back through layers to user interface

## 2. Detailed Component Design

### 2.1 Domain Layer Design

#### 2.1.1 Core Entities
```python
class {idea_title.replace(' ', '')}Entity:
    \"\"\"Core business entity for {idea_title.lower()}\"\"\"
    
    def __init__(self, id: str, **kwargs):
        self.id = id
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        # Additional domain-specific attributes
    
    def validate(self) -> bool:
        \"\"\"Domain validation logic\"\"\"
        pass
    
    def apply_business_rules(self) -> None:
        \"\"\"Apply domain-specific business rules\"\"\"
        pass
```

#### 2.1.2 Domain Services
```python
class {idea_title.replace(' ', '')}DomainService:
    \"\"\"Domain service for complex business logic\"\"\"
    
    def __init__(self, repository: {idea_title.replace(' ', '')}Repository):
        self._repository = repository
    
    def execute_business_logic(self, entity: {idea_title.replace(' ', '')}Entity) -> Result:
        \"\"\"Execute complex domain logic\"\"\"
        pass
```

#### 2.1.3 Repository Interfaces
```python
from abc import ABC, abstractmethod

class {idea_title.replace(' ', '')}Repository(ABC):
    \"\"\"Repository interface for data access\"\"\"
    
    @abstractmethod
    def save(self, entity: {idea_title.replace(' ', '')}Entity) -> None:
        pass
    
    @abstractmethod
    def find_by_id(self, id: str) -> Optional[{idea_title.replace(' ', '')}Entity]:
        pass
    
    @abstractmethod
    def find_by_criteria(self, criteria: dict) -> List[{idea_title.replace(' ', '')}Entity]:
        pass
```

### 2.2 Application Layer Design

#### 2.2.1 Use Cases
```python
class {idea_title.replace(' ', '')}UseCase:
    \"\"\"Application use case for {idea_title.lower()}\"\"\"
    
    def __init__(self, 
                 repository: {idea_title.replace(' ', '')}Repository,
                 domain_service: {idea_title.replace(' ', '')}DomainService):
        self._repository = repository
        self._domain_service = domain_service
    
    def execute(self, request: {idea_title.replace(' ', '')}Request) -> {idea_title.replace(' ', '')}Response:
        \"\"\"Execute the use case\"\"\"
        # 1. Validate input
        # 2. Load domain entities
        # 3. Apply business logic
        # 4. Persist changes
        # 5. Return response
        pass
```

#### 2.2.2 DTOs and Request/Response Models
```python
@dataclass
class {idea_title.replace(' ', '')}Request:
    \"\"\"Request DTO for {idea_title.lower()} operations\"\"\"
    # Request fields based on requirements
    pass

@dataclass
class {idea_title.replace(' ', '')}Response:
    \"\"\"Response DTO for {idea_title.lower()} operations\"\"\"
    success: bool
    data: Optional[dict]
    errors: List[str]
```

### 2.3 Infrastructure Layer Design

#### 2.3.1 Database Schema
```sql
-- {idea_title.lower().replace(' ', '_')} table
CREATE TABLE {idea_title.lower().replace(' ', '_')} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Domain-specific columns
    CONSTRAINT valid_data CHECK (/* domain constraints */)
);

-- Indexes for performance
CREATE INDEX idx_{idea_title.lower().replace(' ', '_')}_created_at 
ON {idea_title.lower().replace(' ', '_')} (created_at);
```

#### 2.3.2 Repository Implementation
```python
class Postgres{idea_title.replace(' ', '')}Repository({idea_title.replace(' ', '')}Repository):
    \"\"\"PostgreSQL implementation of repository\"\"\"
    
    def __init__(self, db_session: Session):
        self._session = db_session
    
    def save(self, entity: {idea_title.replace(' ', '')}Entity) -> None:
        # Implementation with proper transaction handling
        pass
```

## 3. API Design

### 3.1 RESTful Endpoints
```
POST   /api/v1/{idea_title.lower().replace(' ', '-')}     # Create
GET    /api/v1/{idea_title.lower().replace(' ', '-')}     # List
GET    /api/v1/{idea_title.lower().replace(' ', '-')}/{{id}} # Get by ID
PUT    /api/v1/{idea_title.lower().replace(' ', '-')}/{{id}} # Update
DELETE /api/v1/{idea_title.lower().replace(' ', '-')}/{{id}} # Delete
```

### 3.2 Request/Response Schemas
```json
// POST Request Schema
{{
  "type": "object",
  "properties": {{
    // Schema based on requirements
  }},
  "required": ["field1", "field2"]
}}

// Response Schema
{{
  "type": "object",
  "properties": {{
    "success": {{"type": "boolean"}},
    "data": {{"type": "object"}},
    "errors": {{
      "type": "array",
      "items": {{"type": "string"}}
    }}
  }}
}}
```

## 4. Security Design

### 4.1 Authentication & Authorization
- **JWT-based authentication** for stateless security
- **Role-based access control (RBAC)** for fine-grained permissions
- **API rate limiting** to prevent abuse
- **Input sanitization** at all entry points

### 4.2 Data Protection
- **Encryption at rest** using AES-256
- **TLS 1.3** for data in transit
- **Sensitive data masking** in logs
- **Regular security audits** and penetration testing

## 5. Performance Considerations

### 5.1 Caching Strategy
- **Application-level caching** using Redis
- **Database query optimization** with proper indexing
- **CDN integration** for static assets
- **Connection pooling** for database efficiency

### 5.2 Monitoring & Observability
- **Structured logging** with correlation IDs
- **Metrics collection** using Prometheus
- **Distributed tracing** with OpenTelemetry
- **Health checks** for all components

## 6. Deployment Architecture

### 6.1 Containerization
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {idea_title.lower().replace(' ', '-')}-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {idea_title.lower().replace(' ', '-')}-service
  template:
    metadata:
      labels:
        app: {idea_title.lower().replace(' ', '-')}-service
    spec:
      containers:
      - name: app
        image: {idea_title.lower().replace(' ', '-')}:latest
        ports:
        - containerPort: 8000
```

---

*This design specification follows Clean Architecture principles, SOLID design principles, and industry best practices for scalable, maintainable software systems.*
"""

def generate_comprehensive_tasks(
    idea_title: str,
    idea_summary: str,
    project_context: str,
    git_info: dict
) -> str:
    """Generate comprehensive task breakdown using agile methodologies"""
    
    repo_name = git_info.get('repository_name', 'Unknown Project')
    current_branch = git_info.get('current_branch', 'unknown')
    
    return f"""# Implementation Tasks: {idea_title}

## Document Information
- **Project**: {repo_name}
- **Branch**: {current_branch}
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Methodology**: Agile/Scrum with Story Point Estimation

## 1. Epic Breakdown

### Epic: {idea_title} Implementation
**Description**: {idea_summary}
**Business Value**: High
**Story Points**: 34 (Large Epic)
**Sprint Allocation**: 3 sprints

## 2. User Stories and Tasks

### 🎯 Sprint 1: Foundation & Core Domain (13 Story Points)

#### US-001: Domain Model Implementation
**As a** developer
**I want** to implement the core domain model
**So that** business logic is properly encapsulated

**Story Points**: 5
**Priority**: Must Have
**Dependencies**: None

##### Tasks:
- **T-001.1**: Design and implement core entities
  - **Effort**: 4 hours
  - **Assignee**: Senior Developer
  - **Files**: `src/domain/entities/{idea_title.lower().replace(' ', '_')}.py`
  - **Acceptance Criteria**:
    - [ ] Entity classes follow domain-driven design principles
    - [ ] All business rules are encapsulated in entities
    - [ ] Unit tests achieve 95% coverage

- **T-001.2**: Implement domain services
  - **Effort**: 3 hours
  - **Assignee**: Senior Developer
  - **Files**: `src/domain/services/{idea_title.lower().replace(' ', '_')}_service.py`
  - **Acceptance Criteria**:
    - [ ] Complex business logic is handled by domain services
    - [ ] Services are stateless and testable
    - [ ] Integration with entities is seamless

- **T-001.3**: Create repository interfaces
  - **Effort**: 2 hours
  - **Assignee**: Mid-level Developer
  - **Files**: `src/domain/repositories/{idea_title.lower().replace(' ', '_')}_repository.py`
  - **Acceptance Criteria**:
    - [ ] Repository interfaces follow repository pattern
    - [ ] Abstractions are technology-agnostic
    - [ ] Mock implementations available for testing

#### US-002: Database Schema & Infrastructure
**As a** system administrator
**I want** proper database schema and infrastructure
**So that** data is stored reliably and efficiently

**Story Points**: 5
**Priority**: Must Have
**Dependencies**: US-001

##### Tasks:
- **T-002.1**: Design database schema
  - **Effort**: 3 hours
  - **Assignee**: Database Developer
  - **Files**: `migrations/001_create_{idea_title.lower().replace(' ', '_')}_tables.sql`
  - **Acceptance Criteria**:
    - [ ] Schema supports all domain requirements
    - [ ] Proper indexing for performance
    - [ ] Foreign key constraints maintain data integrity

- **T-002.2**: Implement repository concrete classes
  - **Effort**: 4 hours
  - **Assignee**: Mid-level Developer
  - **Files**: `src/infrastructure/repositories/postgres_{idea_title.lower().replace(' ', '_')}_repository.py`
  - **Acceptance Criteria**:
    - [ ] Repository implements domain interface
    - [ ] Proper transaction handling
    - [ ] Error handling and logging

- **T-002.3**: Database migration scripts
  - **Effort**: 2 hours
  - **Assignee**: DevOps Engineer
  - **Files**: `scripts/migrate.py`, `alembic/versions/*.py`
  - **Acceptance Criteria**:
    - [ ] Migration scripts are idempotent
    - [ ] Rollback procedures are tested
    - [ ] Migration works in all environments

#### US-003: Application Layer Implementation
**As a** developer
**I want** application layer components
**So that** use cases are properly orchestrated

**Story Points**: 3
**Priority**: Must Have
**Dependencies**: US-001, US-002

##### Tasks:
- **T-003.1**: Implement use cases
  - **Effort**: 4 hours
  - **Assignee**: Senior Developer
  - **Files**: `src/application/use_cases/{idea_title.lower().replace(' ', '_')}_use_cases.py`
  - **Acceptance Criteria**:
    - [ ] Use cases orchestrate domain logic
    - [ ] Input validation is comprehensive
    - [ ] Error handling provides meaningful messages

- **T-003.2**: Create DTOs and request/response models
  - **Effort**: 2 hours
  - **Assignee**: Mid-level Developer
  - **Files**: `src/application/dtos/{idea_title.lower().replace(' ', '_')}_dtos.py`
  - **Acceptance Criteria**:
    - [ ] DTOs are properly validated
    - [ ] Serialization/deserialization works correctly
    - [ ] Documentation is comprehensive

### 🚀 Sprint 2: API & Integration (13 Story Points)

#### US-004: REST API Implementation
**As a** client application
**I want** RESTful API endpoints
**So that** I can interact with the system programmatically

**Story Points**: 8
**Priority**: Must Have
**Dependencies**: US-003

##### Tasks:
- **T-004.1**: Implement API controllers
  - **Effort**: 6 hours
  - **Assignee**: Full-stack Developer
  - **Files**: `src/presentation/controllers/{idea_title.lower().replace(' ', '_')}_controller.py`
  - **Acceptance Criteria**:
    - [ ] All CRUD operations are supported
    - [ ] Proper HTTP status codes are returned
    - [ ] Request/response validation is implemented

- **T-004.2**: API documentation with OpenAPI
  - **Effort**: 3 hours
  - **Assignee**: Technical Writer
  - **Files**: `docs/api/openapi.yaml`
  - **Acceptance Criteria**:
    - [ ] Complete API documentation
    - [ ] Interactive documentation available
    - [ ] Examples for all endpoints

- **T-004.3**: API integration tests
  - **Effort**: 4 hours
  - **Assignee**: QA Engineer
  - **Files**: `tests/integration/test_{idea_title.lower().replace(' ', '_')}_api.py`
  - **Acceptance Criteria**:
    - [ ] All endpoints are tested
    - [ ] Edge cases are covered
    - [ ] Performance benchmarks are established

#### US-005: Authentication & Authorization
**As a** system administrator
**I want** proper security controls
**So that** only authorized users can access the system

**Story Points**: 5
**Priority**: Must Have
**Dependencies**: US-004

##### Tasks:
- **T-005.1**: Implement JWT authentication
  - **Effort**: 4 hours
  - **Assignee**: Security Developer
  - **Files**: `src/infrastructure/auth/jwt_auth.py`
  - **Acceptance Criteria**:
    - [ ] JWT tokens are properly generated and validated
    - [ ] Token expiration is handled correctly
    - [ ] Refresh token mechanism is implemented

- **T-005.2**: Role-based access control
  - **Effort**: 3 hours
  - **Assignee**: Security Developer
  - **Files**: `src/infrastructure/auth/rbac.py`
  - **Acceptance Criteria**:
    - [ ] Roles and permissions are properly defined
    - [ ] Access control is enforced at API level
    - [ ] Admin interface for role management

### 🎨 Sprint 3: Frontend & Polish (8 Story Points)

#### US-006: User Interface Implementation
**As a** end user
**I want** an intuitive user interface
**So that** I can easily use the {idea_title.lower()} functionality

**Story Points**: 5
**Priority**: Should Have
**Dependencies**: US-004

##### Tasks:
- **T-006.1**: Design UI components
  - **Effort**: 4 hours
  - **Assignee**: UI/UX Designer
  - **Files**: `frontend/src/components/{idea_title.replace(' ', '')}/*.tsx`
  - **Acceptance Criteria**:
    - [ ] Components follow design system
    - [ ] Responsive design for all screen sizes
    - [ ] Accessibility standards are met

- **T-006.2**: Implement frontend logic
  - **Effort**: 6 hours
  - **Assignee**: Frontend Developer
  - **Files**: `frontend/src/pages/{idea_title.replace(' ', '')}/*.tsx`
  - **Acceptance Criteria**:
    - [ ] All user workflows are implemented
    - [ ] Error handling provides user feedback
    - [ ] Loading states are properly managed

#### US-007: Testing & Quality Assurance
**As a** product owner
**I want** comprehensive testing
**So that** the system is reliable and bug-free

**Story Points**: 3
**Priority**: Must Have
**Dependencies**: All previous stories

##### Tasks:
- **T-007.1**: End-to-end testing
  - **Effort**: 4 hours
  - **Assignee**: QA Engineer
  - **Files**: `tests/e2e/test_{idea_title.lower().replace(' ', '_')}_workflows.py`
  - **Acceptance Criteria**:
    - [ ] All user workflows are tested
    - [ ] Cross-browser compatibility verified
    - [ ] Performance under load is acceptable

- **T-007.2**: Security testing
  - **Effort**: 3 hours
  - **Assignee**: Security Engineer
  - **Files**: `tests/security/test_{idea_title.lower().replace(' ', '_')}_security.py`
  - **Acceptance Criteria**:
    - [ ] Penetration testing completed
    - [ ] No critical security vulnerabilities
    - [ ] Security audit report generated

## 3. Definition of Done

### Code Quality Standards
- [ ] Code review completed by senior developer
- [ ] Unit test coverage ≥ 90%
- [ ] Integration tests pass
- [ ] Static code analysis passes (SonarQube)
- [ ] Security scan passes (SAST/DAST)

### Documentation Standards
- [ ] API documentation updated
- [ ] Code comments are comprehensive
- [ ] Architecture decision records (ADRs) updated
- [ ] User documentation updated

### Deployment Standards
- [ ] Feature deployed to staging environment
- [ ] Performance benchmarks met
- [ ] Monitoring and alerting configured
- [ ] Rollback procedure tested

## 4. Risk Management

### Technical Risks
- **Database Performance**: Mitigation through proper indexing and query optimization
- **API Rate Limiting**: Mitigation through caching and efficient algorithms
- **Security Vulnerabilities**: Mitigation through security reviews and automated scanning

### Schedule Risks
- **Dependency Delays**: Mitigation through parallel development where possible
- **Resource Availability**: Mitigation through cross-training and knowledge sharing
- **Scope Creep**: Mitigation through strict change control process

## 5. Success Metrics

### Development Metrics
- **Velocity**: Target 13 story points per sprint
- **Quality**: <5% defect rate in production
- **Performance**: API response time <200ms for 95% of requests

### Business Metrics
- **User Adoption**: 80% of target users actively using feature within 30 days
- **User Satisfaction**: >4.5/5 rating in user feedback
- **Business Value**: Measurable improvement in key business metrics

---

*This task breakdown follows Agile/Scrum methodologies with proper story point estimation, clear acceptance criteria, and comprehensive risk management.*
"""

def generate_basic_spec_template(
    spec_type: str,
    idea_title: str,
    idea_summary: str,
    project_context: dict
) -> str:
    """Generate a basic specification template when MCP sampling is not available"""
    
    git_info = project_context.get('git_context', {})
    repo_name = git_info.get('repository_name', 'Unknown Project')
    
    if spec_type == "requirements":
        return f"""# Requirements for {idea_title}

## Overview
{idea_summary}

**Project Context:** {repo_name}

## Functional Requirements
- [ ] Define core functionality for {idea_title.lower()}
- [ ] Specify user interaction patterns
- [ ] Define integration points with existing system
- [ ] Establish data requirements

## Technical Requirements
- [ ] API specifications
- [ ] Database schema changes (if needed)
- [ ] Security considerations
- [ ] Performance requirements

## Acceptance Criteria
- [ ] Feature works as specified
- [ ] Integration tests pass
- [ ] Documentation is complete
- [ ] Security review completed

*Note: This is a basic template. For detailed AI-generated specifications, use an MCP client that supports sampling (like Claude Desktop).*
"""
    
    elif spec_type == "design":
        return f"""# Design for {idea_title}

## Overview
{idea_summary}

**Project Context:** {repo_name}

## Architecture
- [ ] High-level component design
- [ ] Data flow specifications
- [ ] API endpoint definitions
- [ ] Database schema updates

## Implementation Strategy
- [ ] Development phases
- [ ] Risk mitigation approaches
- [ ] Testing strategy
- [ ] Deployment considerations

## Technical Specifications
- [ ] Service interfaces
- [ ] Data models
- [ ] Error handling patterns
- [ ] Logging and monitoring

*Note: This is a basic template. For detailed AI-generated specifications, use an MCP client that supports sampling (like Claude Desktop).*
"""
    
    elif spec_type == "tasks":
        return f"""# Tasks for {idea_title}

## Overview
{idea_summary}

**Project Context:** {repo_name}

## Development Tasks

### Backend Tasks
- [ ] **Task 1.1**: Implement core API endpoints
  - Estimated effort: 4-6 hours
  - Dependencies: Requirements finalized
  
- [ ] **Task 1.2**: Add database migrations
  - Estimated effort: 2-3 hours
  - Dependencies: Schema design approved

### Frontend Tasks  
- [ ] **Task 2.1**: Create UI components
  - Estimated effort: 3-4 hours
  - Dependencies: Design mockups ready
  
- [ ] **Task 2.2**: Integrate with backend APIs
  - Estimated effort: 2-3 hours
  - Dependencies: Backend endpoints available

### Testing Tasks
- [ ] **Task 3.1**: Write unit tests
  - Estimated effort: 3-4 hours
  - Dependencies: Core functionality complete
  
- [ ] **Task 3.2**: Add integration tests
  - Estimated effort: 2-3 hours
  - Dependencies: All components integrated

*Note: This is a basic template. For detailed AI-generated specifications, use an MCP client that supports sampling (like Claude Desktop).*
"""
    
    else:
        return f"""# {spec_type.title()} for {idea_title}

## Overview
{idea_summary}

**Project Context:** {repo_name}

*Note: This is a basic template. For detailed AI-generated specifications, use an MCP client that supports sampling (like Claude Desktop).*
"""

async def generate_spec_with_mcp_sampling(
    session,
    spec_type: str,
    idea_title: str,
    idea_summary: str,
    project_context: dict,
    git_context: dict
) -> str:
    """Generate a specification document using MCP sampling (client's local model)
    
    Args:
        session: MCP session with sampling capability
        spec_type: Type of spec to generate ('requirements', 'design', 'tasks')
        idea_title: Title of the idea
        idea_summary: Summary of the idea
        project_context: Project context
        git_context: Current git repository context
    
    Returns:
        Generated specification content as markdown
    """
    try:
        # Build comprehensive prompt for spec generation
        git_info_text = f"Git Repository: {git_context['repository_name']} ({git_context['current_branch']})\nWorking Directory: {git_context['working_directory']}"
        
        if spec_type == "requirements":
            prompt = f"""You are a Product Owner creating detailed technical requirements for a software feature.

Feature: {idea_title}
Description: {idea_summary}

Project Context:
{git_info_text}
{json.dumps(project_context, indent=2)}

Generate a comprehensive requirements.md document that includes:

## Overview
- Clear problem statement
- User stories and acceptance criteria
- Success metrics

## Functional Requirements
- Detailed feature specifications
- User interaction flows
- Business rules and constraints

## Technical Requirements
- Integration points with existing codebase
- Data requirements
- Performance requirements
- Security considerations

## Non-Functional Requirements
- Scalability
- Reliability
- Usability
- Compliance

Format as professional markdown with clear headers and bullet points."""
            
        elif spec_type == "design":
            prompt = f"""You are a Technical Lead creating a detailed design document for a software feature.

Feature: {idea_title}
Description: {idea_summary}

Project Context:
{git_info_text}
{json.dumps(project_context, indent=2)}

Generate a comprehensive design.md document that includes:

## Architecture Overview
- High-level design approach
- Component architecture
- Data flow diagrams (described in text)

## Technical Design
- API specifications
- Database schema changes
- Service interactions
- Error handling

## Implementation Strategy
- Development phases
- Risk mitigation
- Testing approach
- Deployment considerations

## Interface Specifications
- API endpoints
- Request/response formats
- Frontend components
- State management

Format as professional markdown with clear technical specifications."""
            
        elif spec_type == "tasks":
            prompt = f"""You are an Engineering Manager breaking down a feature into detailed development tasks.

Feature: {idea_title}
Description: {idea_summary}

Project Context:
{git_info_text}
{json.dumps(project_context, indent=2)}

Generate a comprehensive tasks.md document that includes:

## Task Breakdown
Break the feature into specific, actionable tasks with:

### Backend Tasks
- API endpoint implementation
- Database migrations
- Service layer changes
- Authentication/authorization

### Frontend Tasks
- Component development
- State management
- UI/UX implementation
- Integration with APIs

### Testing Tasks
- Unit tests
- Integration tests
- E2E tests
- Performance tests

### DevOps Tasks
- Infrastructure changes
- Deployment updates
- Monitoring setup

For each task include:
- Task number (1.1, 1.2, etc.)
- Clear description
- Estimated effort (in hours)
- Dependencies
- Acceptance criteria
- Files likely to be modified

Format as professional markdown with numbered tasks and clear specifications."""
        else:
            raise ValueError(f"Unsupported spec type: {spec_type}")
        
        # Create sampling request using proper FastMCP format
        messages = [
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt)
            )
        ]
        
        # Request sampling from client's local model
        # This uses the MCP client's available models (Claude Code, Cursor, etc.)
        result = await session.create_message(
            messages=messages,
            max_tokens=4000,
            system_prompt="You are an expert software development professional. Generate high-quality, actionable specifications.",
            model_preferences={
                "hints": [
                    {"name": "claude-3-sonnet"},
                    {"name": "claude"},
                    {"name": "gpt-4"}
                ],
                "intelligencePriority": 0.9,  # High intelligence for spec generation
                "speedPriority": 0.3,        # Quality over speed
                "costPriority": 0.4          # Moderate cost consideration
            }
        )
        
        if result and result.content and result.content.type == "text":
            return result.content.text
        else:
            raise McpError("Sampling request failed or returned invalid content")
            
    except Exception as e:
        logger.error(f"Error in generate_spec_with_mcp_sampling: {e}")
        # Fallback to basic template if sampling fails
        return f"# {spec_type.title()} for {idea_title}\n\n{idea_summary}\n\n*Note: MCP sampling failed, using basic template*"

@mcp.tool()
async def generate_specs_for_external_project(
    idea_id: str, 
    idea_title: str = None,
    idea_summary: str = None,
    spec_types: list = None,
    project_context: str = "",
    ctx: Context = None
) -> str:
    """Generate specifications for an external project using MCP sampling
    
    This tool uses the MCP client's local AI model to generate high-quality specs
    instead of relying on Software Factory's HTTP API templates.
    
    Args:
        idea_id: Unique identifier for the idea (required)
        idea_title: Title of the feature/idea (optional - will fetch if not provided)
        idea_summary: Description of the feature/idea (optional - will fetch if not provided)
        spec_types: List of spec types to generate ['requirements', 'design', 'tasks']
        project_context: Additional context for generation
    """
    spec_types = spec_types or ["requirements", "design", "tasks"]
    generated_specs = []
    
    try:
        # If title or summary not provided, fetch the idea details
        if not idea_title or not idea_summary:
            logger.info("📋 Fetching idea details from API...")
            ideas = sf_client.get_ideas_without_specs()
            logger.info(f"📋 Got {len(ideas)} ideas from API")
            
            idea_data = None
            for idea in ideas:
                if idea.get('id') == idea_id:
                    idea_data = idea
                    break
            
            if not idea_data:
                logger.error(f"❌ Idea {idea_id} not found in Define phase ideas")
                return json.dumps({
                    "success": False,
                    "error": f"Idea {idea_id} not found in Define phase ideas without specs",
                    "idea_id": idea_id,
                    "available_ideas": [idea.get('id') for idea in ideas]
                }, indent=2)
            
            logger.info(f"✅ Found idea data: {idea_data}")
            idea_title = idea_title or idea_data.get('title', 'Unknown Feature')
            idea_summary = idea_summary or idea_data.get('summary', idea_data.get('description', 'No description available'))
            logger.info(f"📝 Using title: {idea_title}")
            logger.info(f"📝 Using summary: {idea_summary[:100]}...")
        
        git_info = get_git_info()
        
        # Build project context for AI generation
        full_project_context = {
            "git_context": git_info,
            "additional_context": project_context,
            "idea_id": idea_id
        }
        
        # Check if we have sampling capability
        session = None
        client_supports_sampling = False
        
        # Get session from FastMCP Context parameter for MCP sampling
        try:
            logger.info(f"🔍 Checking context for sampling capability...")
            logger.info(f"   ctx is None: {ctx is None}")
            
            # Check if client supports sampling
            client_supports_sampling = False
            session = None
            
            if ctx and hasattr(ctx, 'session') and ctx.session:
                session = ctx.session
                client_supports_sampling = hasattr(session, 'create_message')
                logger.info(f"   ✅ Found session with create_message: {client_supports_sampling}")
            else:
                logger.warning(f"   ❌ No sampling session available - Kiro IDE may not support MCP sampling")
                logger.warning(f"   This is expected behavior for MCP clients that don't implement sampling")
                
        except Exception as session_error:
            logger.error(f"   Exception checking session: {session_error}")
            session = None
            client_supports_sampling = False
        
        if client_supports_sampling:
            logger.info(f"Using MCP sampling for external project specs - {idea_title}")
            
            for spec_type in spec_types:
                try:
                    logger.info(f"Generating {spec_type} spec using MCP client's local model")
                    # Generate spec using client's local model
                    ai_content = await generate_spec_with_mcp_sampling(
                        session,
                        spec_type,
                        idea_title,
                        idea_summary,
                        full_project_context,
                        git_info
                    )
                    
                    generated_specs.append({
                        "spec_type": spec_type,
                        "content": ai_content,
                        "generated_by": "mcp_sampling",
                        "success": True,
                        "content_length": len(ai_content)
                    })
                    
                except Exception as sampling_error:
                    logger.error(f"MCP sampling failed for {spec_type}: {sampling_error}")
                    # Fallback to basic template
                    fallback_content = f"# {spec_type.title()} for {idea_title}\n\n{idea_summary}\n\n*Note: MCP sampling failed, using basic template*"
                    
                    generated_specs.append({
                        "spec_type": spec_type,
                        "content": fallback_content,
                        "generated_by": "fallback_template",
                        "success": False,
                        "error": str(sampling_error)
                    })
        else:
            logger.warning("MCP client does not support sampling - using basic templates")
            logger.info("Note: Kiro IDE and many MCP clients don't yet support MCP sampling")
            logger.info("This is expected behavior - falling back to basic spec templates")
            
            # Generate basic templates for each spec type
            for spec_type in spec_types:
                basic_content = generate_basic_spec_template(spec_type, idea_title, idea_summary, full_project_context)
                
                generated_specs.append({
                    "spec_type": spec_type,
                    "content": basic_content,
                    "generated_by": "basic_template",
                    "success": True,
                    "content_length": len(basic_content),
                    "note": "MCP client does not support sampling - used basic template"
                })
        
        # Format results
        result = {
            "success": True,
            "idea_id": idea_id,
            "idea_title": idea_title,
            "git_context": git_info['repository_name'],
            "generated_specs": generated_specs,
            "sampling_used": client_supports_sampling,
            "message": f"Generated {len(spec_types)} specification documents using {'MCP sampling' if client_supports_sampling else 'Software Factory API'}"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        # Don't rely on logger - return error details directly
        import traceback
        full_traceback = traceback.format_exc()
        
        # Return detailed error information for debugging
        return json.dumps({
            "success": False,
            "error": f"Failed to generate specs: {str(e)}",
            "error_type": type(e).__name__,
            "idea_id": idea_id,
            "idea_title": idea_title,
            "traceback": full_traceback,
            "debug_info": {
                "function_reached": True,
                "parameters_received": {
                    "idea_id": idea_id,
                    "idea_title": idea_title,
                    "idea_summary": idea_summary,
                    "spec_types": spec_types,
                    "project_context": project_context
                }
            }
        }, indent=2)

@mcp.tool()
def update_spec_from_external_project(spec_id: str, field: str, value: str) -> str:
    """Update a specification from external project work
    
    Args:
        spec_id: The specification ID (or idea ID if spec doesn't exist yet)
        field: The artifact type (requirements, design, tasks)
        value: The new content for the specification
    """
    try:
        git_info = get_git_info()
        
        # The spec_id might actually be an idea_id, so we need to handle both cases
        # First, try to get the project_id from the available projects
        projects = sf_client.get_projects()
        if not projects:
            return "Error: No projects found in Software Factory"
        
        # Use the first project for now (could be improved to detect correct project)
        project_id = projects[0].get('id') if projects else 'default_project'
        
        # Prepare the update payload according to the API specification
        payload = {
            "project_id": project_id,
            "spec_id": spec_id,
            "artifact_type": field,
            "new_content": value,
            "update_reason": f"Updated from {git_info['repository_name']} ({git_info['current_branch']})"
        }
        
        logger.info(f"Attempting to update spec {spec_id} with artifact_type {field}")
        result = sf_client.update_spec_with_payload(payload)
        
        if result.get('success'):
            return f"Successfully updated specification {spec_id}: {field} updated with {len(value)} characters"
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Failed to update spec {spec_id}: {error_msg}")
            return f"Failed to update spec {spec_id}: {error_msg}"
    except Exception as e:
        logger.error(f"Error in update_spec_from_external_project: {e}")
        return f"Error updating spec {spec_id}: {str(e)}"

@mcp.tool()
def get_spec_status_for_implementation(spec_id: str) -> str:
    """Get the status of a specification for implementation planning"""
    try:
        status = sf_client.get_spec_status(spec_id)
        git_info = get_git_info()
        
        if not status:
            return f"Specification {spec_id} not found or failed to connect to Software Factory"
        
        result = f"Specification Status for {spec_id}:\n\n"
        result += f"Current Git Context: {git_info['repository_name']} ({git_info['current_branch']})\n\n"
        
        result += f"Status: {status.get('status', 'N/A')}\n"
        result += f"Title: {status.get('title', 'N/A')}\n"
        result += f"Description: {status.get('description', 'N/A')}\n"
        result += f"Progress: {status.get('progress', 'N/A')}\n"
        result += f"Last Updated: {status.get('updated_at', 'N/A')}\n"
        result += f"Tasks Generated: {status.get('tasks_generated', False)}\n"
        result += f"Ready for Implementation: {status.get('ready_for_implementation', False)}\n"
        
        return result
    except Exception as e:
        logger.error(f"Error in get_spec_status_for_implementation: {e}")
        return f"Error retrieving spec status for {spec_id}: {str(e)}"

@mcp.tool()
async def test_async_tool() -> str:
    """Simple test of async MCP tool functionality"""
    logger.info("🧪 test_async_tool called - this should appear in logs")
    return "Async tool test successful"

@mcp.tool()
async def generate_comprehensive_specs_with_kiro(
    idea_id: str,
    idea_title: str = None,
    idea_summary: str = None,
    spec_types: list = None,
    project_context: str = ""
) -> str:
    """Generate comprehensive specifications using Kiro's advanced frameworks (EARS, etc.)
    
    This tool creates detailed, professional specifications using structured methodologies
    including EARS (Easy Approach to Requirements Syntax) and other frameworks.
    """
    spec_types = spec_types or ["requirements", "design", "tasks"]
    generated_specs = []
    
    try:
        # If title or summary not provided, fetch the idea details
        if not idea_title or not idea_summary:
            logger.info("📋 Fetching idea details from API...")
            ideas = sf_client.get_ideas_without_specs()
            logger.info(f"📋 Got {len(ideas)} ideas from API")
            
            idea_data = None
            for idea in ideas:
                if idea.get('id') == idea_id:
                    idea_data = idea
                    break
            
            if not idea_data:
                logger.error(f"❌ Idea {idea_id} not found in Define phase ideas")
                return json.dumps({
                    "success": False,
                    "error": f"Idea {idea_id} not found in Define phase ideas without specs",
                    "idea_id": idea_id,
                    "available_ideas": [idea.get('id') for idea in ideas]
                }, indent=2)
            
            idea_title = idea_title or idea_data.get('title', 'Unknown Feature')
            idea_summary = idea_summary or idea_data.get('summary', idea_data.get('description', 'No description available'))
        
        git_info = get_git_info()
        
        # Generate comprehensive specs using structured frameworks
        for spec_type in spec_types:
            try:
                logger.info(f"Generating {spec_type} spec using comprehensive frameworks")
                
                if spec_type == "requirements":
                    content = generate_comprehensive_requirements(idea_title, idea_summary, project_context, git_info)
                elif spec_type == "design":
                    content = generate_comprehensive_design(idea_title, idea_summary, project_context, git_info)
                elif spec_type == "tasks":
                    content = generate_comprehensive_tasks(idea_title, idea_summary, project_context, git_info)
                else:
                    content = f"# {spec_type.title()} for {idea_title}\n\n{idea_summary}\n\n*Unsupported spec type*"
                
                generated_specs.append({
                    "spec_type": spec_type,
                    "content": content,
                    "generated_by": "kiro_comprehensive_framework",
                    "success": True,
                    "content_length": len(content),
                    "frameworks_used": ["EARS", "IEEE 830", "Agile User Stories", "Technical Architecture Patterns"]
                })
                
            except Exception as generation_error:
                logger.error(f"Comprehensive spec generation failed for {spec_type}: {generation_error}")
                fallback_content = f"# {spec_type.title()} for {idea_title}\n\n{idea_summary}\n\n*Note: Comprehensive generation failed, using basic template*"
                
                generated_specs.append({
                    "spec_type": spec_type,
                    "content": fallback_content,
                    "generated_by": "fallback_template",
                    "success": False,
                    "error": str(generation_error)
                })
        
        # Format results
        result = {
            "success": True,
            "idea_id": idea_id,
            "idea_title": idea_title,
            "git_context": git_info['repository_name'],
            "generated_specs": generated_specs,
            "comprehensive_generation_used": True,
            "frameworks_applied": ["EARS", "IEEE 830", "Agile User Stories", "Technical Architecture Patterns"],
            "message": f"Generated {len(spec_types)} comprehensive specification documents using advanced frameworks"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        import traceback
        full_traceback = traceback.format_exc()
        
        return json.dumps({
            "success": False,
            "error": f"Failed to generate comprehensive specs: {str(e)}",
            "error_type": type(e).__name__,
            "idea_id": idea_id,
            "idea_title": idea_title,
            "traceback": full_traceback
        }, indent=2)

@mcp.tool()
async def test_context_access(ctx: Context = None) -> str:
    """Test if Context is being passed and what it contains"""
    try:
        if ctx is None:
            return "❌ Context is None"
        
        result = f"✅ Context received: {type(ctx)}\n"
        result += f"   Has session: {hasattr(ctx, 'session')}\n"
        
        if hasattr(ctx, 'session'):
            session = ctx.session
            result += f"   Session type: {type(session)}\n"
            result += f"   Session has create_message: {hasattr(session, 'create_message')}\n"
            
            # Try to get more info about the session
            if hasattr(session, '__dict__'):
                result += f"   Session attributes: {list(session.__dict__.keys())}\n"
        
        # Check other context attributes
        if hasattr(ctx, '__dict__'):
            result += f"   Context attributes: {list(ctx.__dict__.keys())}\n"
            
        return result
        
    except Exception as e:
        return f"❌ Error testing context: {str(e)}"

@mcp.tool()
def get_mcp_server_info() -> str:
    """Get information about the MCP server and its capabilities"""
    try:
        git_info = get_git_info()
        
        result = "Software Factory External MCP Server Information:\n\n"
        result += f"Server Version: 1.0.0\n"
        result += f"Base URL: {sf_client.base_url}\n"
        result += f"Current Directory: {os.getcwd()}\n"
        result += f"Git Repository: {git_info['repository_name']}\n"
        result += f"Current Branch: {git_info['current_branch']}\n"
        result += f"Repository URL: {git_info['repository_url']}\n\n"
        
        result += "Available Tools:\n"
        result += "• get_available_projects - List all Software Factory projects\n"
        result += "• get_project_tasks_for_external_work - Get tasks for a project with optional status filter\n"
        result += "• get_current_git_context - Get current git repository context\n"
        result += "• get_current_directory - Get current working directory info\n"
        result += "• list_software_factory_projects - Alias for get_available_projects\n"
        result += "• get_project_tasks_for_current_work - Alias for get_project_tasks_for_external_work\n"
        result += "• get_task_implementation_context - Get detailed context for a specific task\n"
        result += "• update_software_factory_task - Update a task field\n"
        result += "• mark_task_complete_with_local_work - Mark a task as complete with local work notes\n"
        result += "• get_ideas_without_specs_external - Get ideas that need specifications\n"
        result += "• generate_specs_for_external_project - Generate specs using MCP sampling (AI-powered)\n"
        result += "• generate_comprehensive_specs_with_kiro - Generate comprehensive specs using Kiro's advanced frameworks (EARS, IEEE 830, etc.)\n"
        result += "• test_async_tool - Simple async tool test\n"
        result += "• update_spec_from_external_project - Update a specification\n"
        result += "• get_spec_status_for_implementation - Get specification status\n"
        result += "• get_mcp_server_info - This tool\n"
        
        # Test connection
        try:
            projects = sf_client.get_projects()
            result += f"\nConnection Status: ✅ Connected ({len(projects)} projects found)\n"
        except Exception:
            result += f"\nConnection Status: ❌ Connection failed\n"
        
        return result
    except Exception as e:
        logger.error(f"Error in get_mcp_server_info: {e}")
        return f"Error getting server info: {str(e)}"

def main():
    """Run the standalone MCP server"""
    logger.info("Starting Software Factory External MCP Server...")
    logger.info("This server provides Software Factory integration for external projects")
    
    # Test connection to Software Factory
    try:
        projects = sf_client.get_projects()
        logger.info(f"Connected to Software Factory. Found {len(projects)} projects.")
    except Exception as e:
        logger.warning(f"Could not connect to Software Factory: {e}")
        logger.info("Server will start anyway. Tools will return appropriate error messages.")
    
    # Get current git context
    git_info = get_git_info()
    logger.info(f"External project context: {git_info['repository_name']} ({git_info['current_branch']})")
    
    # FastMCP handles its own asyncio loop
    mcp.run()

if __name__ == "__main__":
    main()