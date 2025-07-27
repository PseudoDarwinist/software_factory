"""
Claude Code Task Service
Executes tasks using Claude Code SDK with proper Git workspace setup
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from .git_workspace_service import get_git_workspace_service
    from .claude_code_service import ClaudeCodeService
    from ..models.task import Task, TaskStatus
    from ..models.mission_control_project import MissionControlProject
    from ..models.base import db
except ImportError:
    from services.git_workspace_service import get_git_workspace_service
    from services.claude_code_service import ClaudeCodeService
    from models.task import Task, TaskStatus
    from models.mission_control_project import MissionControlProject
    from models.base import db

logger = logging.getLogger(__name__)


class ClaudeCodeTaskService:
    """Service for executing tasks with Claude Code SDK"""
    
    def __init__(self):
        self.git_workspace_service = get_git_workspace_service()
    
    def execute_task(self, task_id: str, agent_id: str, context_options: Dict[str, Any] = None, 
                    base_branch: str = "main") -> Dict[str, Any]:
        """
        Execute a task using Claude Code SDK with proper Git workspace
        
        Args:
            task_id: Task identifier
            agent_id: Claude Code sub-agent to use
            context_options: Context configuration
            base_branch: Base branch to work from
        
        Returns:
            Dict with execution results
        """
        try:
            # Get task and project info
            task = Task.query.get(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}
            
            project = MissionControlProject.query.get(task.project_id)
            if not project:
                return {'success': False, 'error': f'Project {task.project_id} not found'}
            
            if not project.repo_url or not project.github_token:
                return {'success': False, 'error': 'Project missing GitHub configuration'}
            
            # Update task progress
            task.add_progress_message("Setting up Git workspace...", 10)
            
            # Step 1: Create Git workspace
            workspace_result = self.git_workspace_service.create_task_workspace(
                task_id=task_id,
                repo_url=project.repo_url,
                github_token=project.github_token,
                branch_name=task.branch_name or f"feature/task-{task_id}",
                base_branch=base_branch
            )
            
            if not workspace_result['success']:
                task.add_progress_message(f"Workspace setup failed: {workspace_result['error']}", 0)
                return {
                    'success': False,
                    'error': f"Failed to create workspace: {workspace_result['error']}"
                }
            
            workspace_path = workspace_result['workspace_path']
            branch_name = workspace_result['branch_name']
            
            # Update task with branch info
            task.branch_name = branch_name
            db.session.commit()
            
            task.add_progress_message(f"Workspace ready at {workspace_path}", 20)
            task.add_progress_message(f"Branch {branch_name} created and pushed", 30)
            
            # Step 2: Prepare task context
            task.add_progress_message("Gathering task context...", 40)
            task_context = self._prepare_task_context(task, project, context_options)
            
            # Step 3: Execute with Claude Code SDK
            task.add_progress_message(f"Starting {agent_id} execution...", 50)
            
            claude_service = ClaudeCodeService(workspace_path)
            
            if not claude_service.is_available():
                return {
                    'success': False,
                    'error': 'Claude Code SDK not available'
                }
            
            # Execute the task with Claude Code
            execution_result = self._execute_with_claude_code(
                claude_service=claude_service,
                task=task,
                agent_id=agent_id,
                task_context=task_context,
                workspace_path=workspace_path
            )
            
            if execution_result['success']:
                task.add_progress_message("Task execution completed successfully", 90)
                task.add_progress_message("Creating pull request...", 95)
                
                # TODO: Create PR (task 11.10)
                # For now, just mark as review
                task.status = TaskStatus.REVIEW
                task.add_progress_message("Ready for review", 100)
                
                return {
                    'success': True,
                    'workspace_path': workspace_path,
                    'branch_name': branch_name,
                    'execution_result': execution_result
                }
            else:
                task.add_progress_message(f"Execution failed: {execution_result['error']}", 0)
                task.status = TaskStatus.FAILED
                
                return {
                    'success': False,
                    'error': execution_result['error'],
                    'workspace_path': workspace_path
                }
                
        except Exception as e:
            logger.error(f"Task execution failed for {task_id}: {e}")
            
            # Update task status
            try:
                task = Task.query.get(task_id)
                if task:
                    task.add_progress_message(f"Execution error: {str(e)}", 0)
                    task.status = TaskStatus.FAILED
                    db.session.commit()
            except:
                pass
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _prepare_task_context(self, task: Task, project: MissionControlProject, 
                            context_options: Dict[str, Any]) -> str:
        """
        Prepare context for Claude Code execution
        
        Args:
            task: Task object
            project: Project object
            context_options: Context configuration
        
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add task information
        context_parts.append("=== TASK INFORMATION ===")
        context_parts.append(f"Task ID: {task.id}")
        context_parts.append(f"Task Number: {task.task_number}")
        context_parts.append(f"Title: {task.title}")
        context_parts.append(f"Description: {task.description or 'No description provided'}")
        
        if task.goal_line:
            context_parts.append(f"Goal: {task.goal_line}")
        
        if task.requirements_refs:
            context_parts.append(f"Requirements: {', '.join(task.requirements_refs)}")
        
        context_parts.append("")
        
        # Add project context
        context_parts.append("=== PROJECT CONTEXT ===")
        context_parts.append(f"Project: {project.name}")
        context_parts.append(f"Repository: {project.repo_url}")
        
        if project.description:
            context_parts.append(f"Description: {project.description}")
        
        context_parts.append("")
        
        # Add context options guidance
        if context_options:
            context_parts.append("=== CONTEXT GUIDANCE ===")
            
            if context_options.get('spec_files'):
                context_parts.append("- Review specification files for requirements and design")
            
            if context_options.get('requirements'):
                context_parts.append("- Follow requirements.md for functional specifications")
            
            if context_options.get('design'):
                context_parts.append("- Follow design.md for architectural guidance")
            
            if context_options.get('task'):
                context_parts.append("- Focus on the specific task requirements above")
            
            if context_options.get('code_paths'):
                context_parts.append("- Examine existing code patterns and follow established conventions")
            
            context_parts.append("")
        
        # Add execution instructions
        context_parts.append("=== EXECUTION INSTRUCTIONS ===")
        context_parts.append("1. Analyze the repository structure and existing patterns")
        context_parts.append("2. Implement the task requirements following established conventions")
        context_parts.append("3. Write or update tests as appropriate")
        context_parts.append("4. Ensure code quality and consistency with existing codebase")
        context_parts.append("5. Commit changes with clear, descriptive messages")
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _execute_with_claude_code(self, claude_service: ClaudeCodeService, task: Task, 
                                agent_id: str, task_context: str, workspace_path: str) -> Dict[str, Any]:
        """
        Execute task using Claude Code SDK
        
        Args:
            claude_service: Claude Code service instance
            task: Task object
            agent_id: Sub-agent identifier
            task_context: Prepared context
            workspace_path: Path to Git workspace
        
        Returns:
            Execution result
        """
        try:
            # Map agent_id to Claude Code sub-agent
            agent_mapping = {
                'feature-builder': 'feature-builder',
                'test-runner': 'test-runner', 
                'code-reviewer': 'code-reviewer',
                'debugger': 'debugger',
                'design-to-code': 'design-to-code'
            }
            
            claude_agent = agent_mapping.get(agent_id, 'feature-builder')
            
            # Create the prompt for Claude Code
            prompt = f"""You are a {claude_agent} working on a specific task.

{task_context}

Please implement the task requirements. Use your filesystem access to:
1. Examine the existing codebase structure
2. Understand the current patterns and conventions
3. Implement the required functionality
4. Write appropriate tests
5. Commit your changes

Focus on quality, maintainability, and consistency with the existing codebase."""
            
            # Update progress
            task.add_progress_message(f"Executing {claude_agent}...", 60)
            
            # Execute with Claude Code SDK
            # Note: This uses the existing ClaudeCodeService.create_specification method
            # In a full implementation, you might want a more specific method for task execution
            result = claude_service.create_specification(prompt, task_context)
            
            if result.get('success'):
                task.add_progress_message("Code generation completed", 80)
                return {
                    'success': True,
                    'output': result.get('output', ''),
                    'agent_used': claude_agent
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'agent_used': claude_agent
                }
                
        except Exception as e:
            logger.error(f"Claude Code execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_task_workspace(self, task_id: str) -> bool:
        """
        Clean up workspace for a completed task
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if cleanup successful
        """
        return self.git_workspace_service.cleanup_task_workspace(task_id)
    
    def get_workspace_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workspace information for a task
        
        Args:
            task_id: Task identifier
        
        Returns:
            Workspace info or None if not found
        """
        workspace_path = self.git_workspace_service.get_workspace_path(task_id)
        if not workspace_path:
            return None
        
        return {
            'task_id': task_id,
            'workspace_path': str(workspace_path),
            'exists': workspace_path.exists()
        }


# Global instance
_claude_code_task_service = None


def get_claude_code_task_service() -> ClaudeCodeTaskService:
    """Get the global Claude Code task service instance"""
    global _claude_code_task_service
    if _claude_code_task_service is None:
        _claude_code_task_service = ClaudeCodeTaskService()
    return _claude_code_task_service