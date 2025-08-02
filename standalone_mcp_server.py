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
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import MCP library
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import Tool
except ImportError:
    print("Error: MCP library not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Initialize FastMCP server
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
        """Get ideas that don't have specifications yet"""
        try:
            response = self.session.get(f"{self.base_url}/api/ideas?without_specs=true")
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
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
    
    def update_spec(self, spec_id: str, updates: Dict) -> Dict:
        """Update a specification"""
        try:
            response = self.session.patch(f"{self.base_url}/api/specs/{spec_id}", json=updates)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to update spec: {e}")
            return {}
    
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
                result += f"Description: {idea.get('description', 'N/A')}\n"
                result += f"Priority: {idea.get('priority', 'N/A')}\n"
                result += f"Created: {idea.get('created_at', 'N/A')}\n"
                result += "---\n"
            else:
                result += f"Invalid idea data: {idea}\n---\n"
        
        return result
    except Exception as e:
        logger.error(f"Error in get_ideas_without_specs_external: {e}")
        return f"Error retrieving ideas: {str(e)}"

@mcp.tool()
def generate_specs_for_external_project(idea_id: str, project_context: str = "") -> str:
    """Generate specifications for an idea in the context of external project work"""
    try:
        git_info = get_git_info()
        
        # Add git context to project context
        full_context = f"External project: {git_info['repository_name']} ({git_info['current_branch']})"
        if project_context:
            full_context += f"\n\nAdditional context: {project_context}"
        
        result = sf_client.generate_spec(idea_id, full_context)
        
        if result.get('success'):
            spec_id = result.get('spec_id', 'N/A')
            return f"Successfully generated specification {spec_id} for idea {idea_id}"
        else:
            return f"Failed to generate spec for idea {idea_id}: {result.get('error', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error in generate_specs_for_external_project: {e}")
        return f"Error generating spec for idea {idea_id}: {str(e)}"

@mcp.tool()
def update_spec_from_external_project(spec_id: str, field: str, value: str) -> str:
    """Update a specification from external project work"""
    try:
        git_info = get_git_info()
        
        # Add git context to updates
        updates = {
            field: value,
            "updated_from": f"{git_info['repository_name']} ({git_info['current_branch']})"
        }
        
        result = sf_client.update_spec(spec_id, updates)
        
        if result.get('success'):
            return f"Successfully updated specification {spec_id}: {field} = {value}"
        else:
            return f"Failed to update spec {spec_id}: {result.get('error', 'Unknown error')}"
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
        result += "• generate_specs_for_external_project - Generate specs for an idea\n"
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