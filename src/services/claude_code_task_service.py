"""
Claude Code Task Service
Executes tasks using Claude Code SDK with proper Git workspace setup
"""

import os
import logging
import subprocess
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from .git_workspace_service import get_git_workspace_service
    from .claude_code_service import ClaudeCodeService
    from .github_pr_service import get_github_pr_service
    from ..models.task import Task, TaskStatus
    from ..models.mission_control_project import MissionControlProject
    from ..models.base import db
except ImportError:
    from services.git_workspace_service import get_git_workspace_service
    from services.claude_code_service import ClaudeCodeService
    from services.github_pr_service import get_github_pr_service
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
            
            # Update task progress with detailed setup information
            task.add_progress_message("🛠️ Setting up Git workspace...", 10)
            task.add_progress_message(f"📋 Repository: {project.repo_url}", 12)
            
            # Step 1: Create Git workspace
            branch_name_display = task.branch_name or f"feature/task-{task_id}"
            task.add_progress_message(f"🌿 Preparing branch: {branch_name_display}", 15)
            
            workspace_result = self.git_workspace_service.create_task_workspace(
                task_id=task_id,
                repo_url=project.repo_url,
                github_token=project.github_token,
                branch_name=branch_name_display,
                base_branch=base_branch
            )
            
            if not workspace_result['success']:
                task.add_progress_message(f"❌ Workspace setup failed: {workspace_result['error']}", 0)
                return {
                    'success': False,
                    'error': f"Failed to create workspace: {workspace_result['error']}"
                }
            
            workspace_path = workspace_result['workspace_path']
            branch_name = workspace_result['branch_name']
            
            # Update task with branch info
            task.branch_name = branch_name
            db.session.commit()
            
            task.add_progress_message(f"✅ Workspace created: {workspace_path}", 20)
            task.add_progress_message(f"🌿 Branch '{branch_name}' created from '{base_branch}'", 25)
            task.add_progress_message(f"📤 Branch pushed to remote repository", 30)
            
            # Step 2: Prepare task context
            task.add_progress_message("📋 Gathering task context and requirements...", 40)
            task_context = self._prepare_task_context(task, project, context_options)
            task.add_progress_message(f"📄 Context prepared: {len(task_context)} characters", 45)
            
            # Step 3: Execute with Claude Code SDK
            task.add_progress_message(f"🤖 Launching {agent_id} sub agent...", 50)
            task.add_progress_message(f"🔍 Looking for .claude/agents/{agent_id}.md configuration", 52)
            
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

            # --- NEW: auto-commit & push if agent produced uncommitted changes ---
            try:
                if execution_result.get("success"):
                    # Correctly access files_changed and commits from the execution_result dictionary
                    files_changed = execution_result.get("files_changed")
                    commits = execution_result.get("commits")

                    if files_changed and not commits:
                        task.add_progress_message("Auto-committing agent changes…", 82)
                        # Reuse the already-imported subprocess module instead of re-importing

                        # Stage all changes
                        subprocess.run(["git", "add", "-A"], cwd=workspace_path, check=True)
                        # Commit
                        commit_msg = f"feat: implement task {task.task_number} via {agent_id} sub-agent"
                        subprocess.run(["git", "commit", "-m", commit_msg], cwd=workspace_path, check=True)
                        # Push to remote
                        subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=workspace_path, check=True)

                        # Refresh commit list for later PR description
                        # Get the base branch dynamically
                        base_branch_result = subprocess.run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'], cwd=workspace_path, capture_output=True, text=True)
                        if base_branch_result.returncode == 0:
                            base_branch = base_branch_result.stdout.strip().split('/')[-1]
                        else:
                            base_branch = 'main'  # fallback
                        
                        git_log = subprocess.run([
                            "git", "log", f"{base_branch}..HEAD", "--oneline", "-n", "5"], cwd=workspace_path, capture_output=True, text=True
                        )
                        if git_log.returncode == 0 and git_log.stdout.strip():
                            new_commits = [line.strip() for line in git_log.stdout.strip().split("\n")]
                            # Correctly update the commits list in the existing result dictionary
                            execution_result["commits"] = new_commits
                        task.add_progress_message("Changes committed and pushed", 85)
            except Exception as auto_commit_exc:
                logger.warning("Auto-commit failed: %s", auto_commit_exc)
                task.add_progress_message("Auto-commit failed; branch may have no changes", 85)
            # --- END auto-commit block ---

            # Abort early if there are still no commits on the feature branch –
            # attempting to open a PR would fail with the GitHub 422 we saw.
            commits_for_pr = execution_result.get("commits")
            # Ensure the remote branch contains all new commits before we open a PR. Without
            # this extra push, the GitHub API will return a 422 error ("No commits between …")
            # if the branch was created earlier but the agent only committed locally.
            if commits_for_pr:
                try:
                    subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=workspace_path, check=True)
                    task.add_progress_message("Latest commits pushed to remote", 88)
                except subprocess.CalledProcessError as push_exc:
                    logger.warning("Failed to push commits for PR creation: %s", push_exc)
                    task.add_progress_message("Warning: could not push commits to remote – PR creation may fail", 88)
            
            if execution_result["success"] and not commits_for_pr:
                warn_msg = (
                    "Sub-agent finished without producing any commits – "
                    "skipping PR creation. Review the task logs or retry."
                )
                task.add_progress_message(warn_msg, 100)
                task.status = TaskStatus.FAILED
                task.set_error("Agent produced no changes; PR not created")
                return {
                    "success": False,
                    "error": "No commits were created by the agent.",
                    "workspace_path": workspace_path,
                    "branch_name": branch_name,
                }

            if execution_result['success']:
                task.add_progress_message("✅ Agent execution completed successfully!", 90)
                task.add_progress_message("📋 Creating pull request...", 95)
                
                # Create PR (task 11.10)
                pr_result = self._create_pull_request(task, project, branch_name, base_branch)
                
                if pr_result['success']:
                    task.pr_url = pr_result['pr_url']
                    task.pr_number = pr_result.get('pr_number') # Store PR number
                    task.status = TaskStatus.REVIEW
                    task.add_progress_message(f"🎉 Pull request created successfully!", 98)
                    task.add_progress_message(f"🔗 PR URL: {pr_result['pr_url']}", 100)
                    task.add_progress_message(f"📋 Task moved to Review stage - ready for code review!", 100)
                    
                    return {
                        'success': True,
                        'workspace_path': workspace_path,
                        'branch_name': branch_name,
                        'pr_url': pr_result['pr_url'],
                        'execution_result': execution_result
                    }
                else:
                    # PR creation failed, task execution is considered failed.
                    error_msg = f"Task completed but PR creation failed: {pr_result['error']}"
                    task.set_error(error_msg) # This sets status to FAILED and commits
                    task.add_progress_message(f"❌ {error_msg}", 100)
                    
                    return {
                        'success': False, # Critical change: return success: False
                        'error': pr_result['error'],
                        'workspace_path': workspace_path,
                        'branch_name': branch_name,
                        'pr_error': pr_result['error'],
                        'execution_result': execution_result
                    }
            else:
                task.add_progress_message(f"❌ Agent execution failed: {execution_result['error']}", 0)
                task.set_error(execution_result['error']) # This sets status to FAILED
                
                return {
                    'success': False,
                    'error': execution_result['error'],
                    'workspace_path': workspace_path
                }
                
        except Exception as e:
            logger.error(f"Task execution failed for {task_id}: {e}")
            import traceback
            logger.error(f"Task execution traceback: {traceback.format_exc()}")
            
            # Update task status with user-friendly error
            try:
                task = Task.query.get(task_id)
                if task:
                    # Provide a more user-friendly error message
                    user_error = self._format_user_friendly_error(str(e))
                    task.add_progress_message(f"Task failed: {user_error}", 0)
                    task.set_error(f"Task execution failed: {str(e)}")
                    db.session.commit()
            except Exception as inner_e:
                logger.error(f"Failed to update task error status: {inner_e}")
                pass
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_pull_request(self, task: Task, project: MissionControlProject, 
                           branch_name: str, base_branch: str) -> Dict[str, Any]:
        """
        Create a pull request for the completed task
        
        Args:
            task: Task object
            project: Project object
            branch_name: Source branch name
            base_branch: Target branch name
        
        Returns:
            Dict with PR creation result
        """
        try:
            github_pr_service = get_github_pr_service()
            
            # Generate PR title and body
            pr_title = f"Task {task.task_number}: {task.title}"
            
            pr_body = f"""## Task Implementation

**Task ID:** {task.id}
**Task Number:** {task.task_number}
**Agent:** {task.agent or 'Unknown'}

### Description
{task.description or 'No description provided'}

### Changes Made
This PR implements the changes required for the above task using automated agent execution.

### Review Notes
- This is a draft PR created automatically by the agent
- Please review the changes and run tests before merging
- The task will be marked as complete once this PR is merged

---
*Generated automatically by Software Factory*"""
            
            # Create the PR as a draft
            pr_result = github_pr_service.create_pull_request(
                repo_url=project.repo_url,
                github_token=project.github_token,
                branch_name=branch_name,
                title=pr_title,
                body=pr_body,
                base_branch=base_branch,
                draft=True  # Start as draft
            )
            
            if pr_result['success']:
                logger.info(f"Created PR for task {task.id}: {pr_result['pr_url']}")
                
                # Store PR info in task (if pr_number column exists)
                try:
                    task.pr_number = pr_result.get('pr_number')
                except AttributeError:
                    # pr_number column doesn't exist yet - migration not applied
                    logger.warning("pr_number column not found - migration may not be applied")
                db.session.commit()
                
                # TODO: Add webhook listener for CI/CD status to auto-convert draft to ready
                # For now, PR stays as draft until manually converted
                
                return pr_result
            else:
                logger.error(f"Failed to create PR for task {task.id}: {pr_result['error']}")
                return pr_result
                
        except Exception as e:
            error_msg = f"Error creating PR for task {task.id}: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def _format_user_friendly_error(self, error_message: str) -> str:
        """Format error message to be more user-friendly"""
        
        # Common error patterns and their user-friendly versions
        error_mappings = {
            'No such file or directory': 'Required file not found',
            'Permission denied': 'Permission denied - check file permissions',
            'Connection refused': 'Unable to connect to service',
            'Timeout': 'Operation timed out',
            'Authentication failed': 'Authentication failed - check credentials',
            'Repository not found': 'GitHub repository not accessible',
            'Branch already exists': 'Branch name already exists',
            'Claude Code CLI not found': 'Claude Code CLI not installed or not in PATH',
            'API rate limit exceeded': 'API rate limit exceeded - please try again later'
        }
        
        # Check for known patterns
        for pattern, friendly_msg in error_mappings.items():
            if pattern.lower() in error_message.lower():
                return friendly_msg
        
        # If no specific pattern matches, clean up the message
        cleaned_error = error_message
        
        # Remove common technical prefixes
        prefixes = ['Error: ', 'Exception: ', 'RuntimeError: ', 'ValueError: ']
        for prefix in prefixes:
            if cleaned_error.startswith(prefix):
                cleaned_error = cleaned_error[len(prefix):]
                break
        
        # Limit length and remove stack traces
        if len(cleaned_error) > 200:
            cleaned_error = cleaned_error[:200] + "..."
        
        return cleaned_error
    
    def _execute_claude_with_progress(self, cmd: list, workspace_path: str, env: dict, 
                                    task: Task, agent_name: str) -> subprocess.CompletedProcess:
        """
        Execute Claude Code with progress updates to improve UX
        """
        import threading
        import time
        
        # Progress messages to show during execution
        progress_messages = [
            (30, f"{agent_name} is analyzing the repository structure..."),
            (60, f"{agent_name} is understanding existing code patterns..."),
            (90, f"{agent_name} is implementing the requested changes..."),
            (120, f"{agent_name} is writing tests for the new functionality..."),
            (180, f"{agent_name} is reviewing and refining the implementation..."),
            (240, f"{agent_name} is making final adjustments and commits..."),
            (300, f"{agent_name} is completing the task (this may take a few more minutes)..."),
            (420, f"{agent_name} is still working on complex implementation details..."),
            (600, f"{agent_name} is finalizing the implementation (almost done)..."),
        ]
        
        # Start the subprocess
        process = subprocess.Popen(
            cmd,
            cwd=workspace_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Ensure we have access to the Flask application context inside the
        # background monitoring thread. We capture the current app object here
        # (while we *are* within an application context) so it can be pushed
        # again from the new thread.
        try:
            from flask import current_app  # Local import to avoid hard dependency at module load time
            _app_ctx = current_app._get_current_object()
        except Exception:  # pragma: no cover – fallback if called without an app context
            _app_ctx = None
        
        # Progress monitoring thread
        def monitor_progress():
            import time
            start_time = time.time()
            message_index = 0
            
            while process.poll() is None:  # While process is running
                elapsed = time.time() - start_time
                
                # Show progress messages based on elapsed time
                if (
                    message_index < len(progress_messages)
                    and elapsed >= progress_messages[message_index][0]
                ):
                    _, message = progress_messages[message_index]
                    progress_percent = min(75 + (message_index * 3), 95)  # 75-95%

                    try:
                        # Re-enter the Flask app context so that we have a valid
                        # SQLAlchemy session bound to this thread before we hit
                        # the database.
                        if _app_ctx is not None:
                            with _app_ctx.app_context():
                                from ..models.task import Task as _Task  # local import to avoid circular deps
                                task_obj = _Task.query.get(task.id)
                                if task_obj:
                                    task_obj.add_progress_message(message, progress_percent)
                        else:
                            # Fallback – attempt the update directly (may fail if app ctx required)
                            task.add_progress_message(message, progress_percent)
                    except Exception as progress_exc:
                        logger.warning(
                            "Failed to record progress for task %s: %s", task.id, progress_exc
                        )
                    
                    message_index += 1
                
                # Check every 30 seconds
                time.sleep(30)
                
                # Safety timeout (15 minutes)
                if elapsed > 900:
                    logger.warning("Claude Code execution exceeded 15 minutes, terminating")
                    process.terminate()
                    break
        
        # Start progress monitoring
        progress_thread = threading.Thread(target=monitor_progress, daemon=True)
        progress_thread.start()
        
        # Wait for completion with timeout
        try:
            # Set timeout to 15 minutes (900 seconds) to match progress monitoring
            stdout, stderr = process.communicate(timeout=900)
            
            # Create a result object similar to subprocess.run
            result = subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr
            )
            
            return result
            
        except subprocess.TimeoutExpired:
            logger.error(f"Claude Code execution timed out after 15 minutes for {agent_name}")
            process.terminate()
            
            # Return a failed result
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr=f"Claude Code execution timed out after 15 minutes"
            )
        except Exception as e:
            logger.error(f"Error during Claude Code execution: {e}")
            process.terminate()
            
            # Return a failed result
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr=f"Execution error: {str(e)}"
            )
    
    def convert_pr_to_ready(self, task_id: str) -> Dict[str, Any]:
        """
        Convert a draft PR to ready for review when tests pass
        
        Args:
            task_id: Task identifier
        
        Returns:
            Dict with conversion result
        """
        try:
            task = Task.query.get(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}
            
            project = MissionControlProject.query.get(task.project_id)
            if not project:
                return {'success': False, 'error': f'Project {task.project_id} not found'}
            
            if not task.pr_number:
                return {'success': False, 'error': 'Task has no associated PR'}
            
            github_pr_service = get_github_pr_service()
            
            result = github_pr_service.convert_draft_to_ready(
                repo_url=project.repo_url,
                github_token=project.github_token,
                pr_number=task.pr_number
            )
            
            if result['success']:
                task.add_progress_message("PR converted to ready for review", 100)
                logger.info(f"PR #{task.pr_number} for task {task_id} converted to ready")
            
            return result
            
        except Exception as e:
            error_msg = f"Error converting PR to ready for task {task_id}: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
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
        Execute task using Claude Code SDK with specific sub-agent
        
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
            
            # Create the prompt that explicitly invokes the sub-agent
            prompt = f"""Use the {claude_agent} sub agent to implement task {task.task_number}.

{task_context}

CRITICAL REQUIREMENTS:
1. Examine the existing codebase structure and patterns
2. Implement the required functionality following established conventions
3. Write or update tests as appropriate
4. Ensure code quality and consistency
5. **MANDATORY: After making changes, you MUST commit them using git commands**

COMMIT WORKFLOW (REQUIRED):
After implementing the feature, you MUST:
1. Stage your changes: `git add .`
2. Commit with a descriptive message: `git commit -m "feat: implement task {task.task_number} - [brief description]"`

IMPORTANT: The task is NOT complete without git commits. You must create at least one commit with your changes.

The {claude_agent} sub agent should handle this task according to its specialized expertise and MUST commit all changes."""
            
            # Update progress
            task.add_progress_message(f"Launching {claude_agent} sub-agent...", 60)
            
            # Execute with Claude Code SDK using sub-agent
            result = self._execute_claude_code_with_sub_agent(
                claude_service=claude_service,
                agent_name=claude_agent,
                prompt=prompt,
                workspace_path=workspace_path,
                task=task
            )
            
            if result.get('success'):
                task.add_progress_message(f"{claude_agent} completed successfully", 80)
                return {
                    'success': True,
                    'output': result.get('output', ''),
                    'agent_used': claude_agent,
                    'commits': result.get('commits', []),
                    'files_changed': result.get('files_changed', [])
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'agent_used': claude_agent
                }
                
        except Exception as e:
            logger.error(f"Claude Code sub-agent execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_claude_code_with_sub_agent(self, claude_service: ClaudeCodeService, 
                                          agent_name: str, prompt: str, workspace_path: str, 
                                          task: Task) -> Dict[str, Any]:
        """
        Execute Claude Code SDK with specific sub-agent using command line interface
        
        Args:
            claude_service: Claude Code service instance
            agent_name: Name of the sub-agent to use
            prompt: Task prompt
            workspace_path: Path to Git workspace
            task: Task object for progress updates
        
        Returns:
            Execution result with commits and file changes
        """
        try:
            import subprocess
            import json
            import os
            import time
            
            # Update progress
            task.add_progress_message(f"Checking for .claude/agents/{agent_name}.md...", 65)
            
            # Check if sub-agent file exists in workspace
            agent_file = os.path.join(workspace_path, '.claude', 'agents', f'{agent_name}.md')
            if not os.path.exists(agent_file):
                logger.warning(f"Sub-agent file not found: {agent_file}, using default behavior")
                task.add_progress_message(f"Using default {agent_name} behavior (no custom agent file)", 67)
            else:
                task.add_progress_message(f"Found custom {agent_name} configuration", 67)
            
            # Prepare Claude Code command with streaming JSON output
            # Based on the test, stream-json works fine - let's use it properly
            cmd = [
                'claude', 
                '--output-format', 'stream-json',
                '--verbose',
                '--dangerously-skip-permissions',
                '--max-turns', '10',
                '-p', prompt
            ]
            
            task.add_progress_message(f"🔧 Executing: claude --output-format stream-json -p [prompt]", 71)

            env = os.environ.copy()

            task.add_progress_message(f"Launching {agent_name} sub-agent (streaming)…", 70)
            
            # First, test if Claude CLI is working
            task.add_progress_message("🧪 Testing Claude Code CLI availability...", 69)
            test_cmd = ['claude', '--version']
            try:
                test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
                if test_result.returncode == 0:
                    task.add_progress_message(f"✅ Claude CLI working: {test_result.stdout.strip()}", 70)
                    logger.info("Claude CLI test successful: %s", test_result.stdout.strip())
                else:
                    task.add_progress_message(f"⚠️ Claude CLI test failed (code {test_result.returncode}): {test_result.stderr.strip()}", 70)
                    logger.warning("Claude CLI test failed: %s", test_result.stderr.strip())
            except Exception as test_error:
                task.add_progress_message(f"❌ Claude CLI test error: {str(test_error)}", 70)
                logger.error("Claude CLI test error: %s", test_error)

            logger.info("Running Claude Code (stream-json): %s", ' '.join(cmd))
            logger.info("Working directory: %s", workspace_path)
            logger.info("Environment variables: PATH=%s", env.get('PATH', 'NOT_SET'))
            
            # Add timeout and better error handling
            process = subprocess.Popen(
                cmd,
                cwd=workspace_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,  # Unbuffered for immediate output
                env=env,
                universal_newlines=True
            )
            
            task.add_progress_message(f"🚀 Claude Code process started (PID: {process.pid})", 72)

            # Real-time streaming of stdout - both JSON events AND raw command output
            response_buffer = []
            session_id = None
            last_progress_time = time.time()
            progress_percent = 70

            timeout_seconds = 900  # 15-minute hard timeout

            try:
                import time, select
                import threading

                start_time = time.time()
                lines_read = 0
                last_activity = time.time()
                
                # Heartbeat monitor for long-running Claude Code execution
                heartbeat_count = [0]  # Use list to allow modification from nested function
                def heartbeat_monitor():
                    """Show periodic heartbeat messages during long Claude Code execution"""
                    try:
                        while process.poll() is None:
                            time.sleep(15)  # Every 15 seconds
                            elapsed = time.time() - start_time
                            heartbeat_count[0] += 1
                            
                            if elapsed < 300:  # Only for first 5 minutes
                                if heartbeat_count[0] == 1:
                                    task.add_progress_message("🤖 Claude Code is analyzing the repository...", 74)
                                elif heartbeat_count[0] == 2:
                                    task.add_progress_message("📋 Understanding requirements and existing patterns...", 76)
                                elif heartbeat_count[0] == 3:
                                    task.add_progress_message("⚡ Implementing changes based on specifications...", 78)
                                elif heartbeat_count[0] == 4:
                                    task.add_progress_message("🔧 Writing code and updating files...", 80)
                                elif heartbeat_count[0] == 5:
                                    task.add_progress_message("🧪 Creating or updating tests...", 82)
                                elif heartbeat_count[0] == 6:
                                    task.add_progress_message("💾 Preparing to commit changes...", 84)
                                elif heartbeat_count[0] >= 7:
                                    task.add_progress_message(f"⏳ Still working... ({int(elapsed)}s elapsed)", min(85 + heartbeat_count[0], 90))
                            else:
                                break
                    except Exception as e:
                        logger.error("Error in heartbeat monitor: %s", e)
                
                # Monitor stderr in a separate thread
                stderr_lines = []
                def monitor_stderr():
                    try:
                        while process.poll() is None:
                            line = process.stderr.readline()
                            if line:
                                stderr_lines.append(line.strip())
                                logger.warning("Claude Code stderr: %s", line.strip())
                                task.add_progress_message(f"⚠️ {line.strip()}", 73)
                    except Exception as e:
                        logger.error("Error monitoring stderr: %s", e)
                
                # Start monitoring threads
                heartbeat_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
                heartbeat_thread.start()
                stderr_thread = threading.Thread(target=monitor_stderr, daemon=True)
                stderr_thread.start()
                
                task.add_progress_message("🔍 Monitoring Claude Code output...", 73)
                logger.info("Starting output monitoring loop")
                
                while True:
                    # Check if process has finished
                    if process.poll() is not None:
                        logger.info("Process finished with return code: %s", process.returncode)
                        # Try to read any remaining output
                        remaining_output = process.stdout.read()
                        if remaining_output:
                            logger.info("Final output: %s", remaining_output[:500])
                            task.add_progress_message(f"📝 Final output: {remaining_output[:200]}...", 85)
                        break

                    # Check for output with a longer timeout for initial response
                    timeout = 30 if lines_read == 0 else 5  # Wait longer for first output
                    ready, _, _ = select.select([process.stdout], [], [], timeout)
                    
                    if ready:
                        try:
                            raw_line = process.stdout.readline()
                            if not raw_line:
                                continue
                            
                            lines_read += 1
                            last_activity = time.time()
                            
                            raw_line = raw_line.strip()
                            if not raw_line:
                                continue
                            
                            logger.debug("Claude Code output line %d: %s", lines_read, raw_line[:100])
                            
                            # Progress update for activity
                            if lines_read % 10 == 0:
                                task.add_progress_message(f"📊 Processing output... ({lines_read} lines)", min(73 + (lines_read // 10), 85))
                        except Exception as e:
                            logger.error("Error reading stdout line: %s", e)
                            continue
                    else:
                        # No output received in timeout period
                        current_time = time.time()
                        elapsed = current_time - start_time
                        
                        if lines_read == 0 and elapsed > 60:  # No output for 60 seconds
                            logger.warning("No output from Claude Code after %d seconds", elapsed)
                            task.add_progress_message(f"⏱️ Waiting for Claude Code response... ({int(elapsed)}s)", 73)
                        elif current_time - last_activity > 120:  # No activity for 2 minutes
                            logger.warning("No activity from Claude Code for %d seconds", current_time - last_activity)
                            task.add_progress_message(f"🤔 Claude Code seems quiet... checking process health", 75)
                            
                            # Check if process is still alive
                            if process.poll() is not None:
                                logger.error("Process died unexpectedly!")
                                break
                    
                    if not raw_line:
                        continue
                        
                        # Try to parse as JSON (stream-json format)
                        try:
                            evt = json.loads(raw_line)
                            logger.debug("Parsed JSON event: %s", evt.get('type', 'unknown'))
                            
                            event_type = evt.get('type')
                            
                            if event_type == 'system':
                                # System initialization event
                                session_id = evt.get('session_id', 'unknown')
                                model = evt.get('model', 'unknown')
                                task.add_progress_message(f"⚙️ Session started: {model} ({session_id[:8]}...)", min(progress_percent + 1, 95))
                                logger.info("Claude session started: %s", session_id)
                            
                            elif event_type == 'assistant':
                                # Assistant message
                                parts = evt['message']['content']
                                if parts and parts[0]['type'] == 'text':
                                    chunk_text = parts[0]['text'].strip()
                                    response_buffer.append(chunk_text)
                                    # Stream assistant messages with context
                                    task.add_progress_message(f"🤖 {agent_name}: {chunk_text[:200]}{'...' if len(chunk_text) > 200 else ''}", min(progress_percent + 1, 95))
                                    progress_percent = min(progress_percent + 1, 95)
                                    logger.info("Assistant message: %s", chunk_text[:100])
                            
                            elif event_type == 'tool_use':
                                # Tool execution started
                                tool_name = evt.get('name', 'unknown')
                                tool_input = evt.get('input', {})
                                task.add_progress_message(f"🔧 Executing tool: {tool_name}", min(progress_percent + 1, 95))
                                logger.info("Tool execution: %s with input: %s", tool_name, str(tool_input)[:100])
                            
                            elif event_type == 'tool_result':
                                # Tool execution completed
                                tool_name = evt.get('tool_name', 'unknown')
                                is_error = evt.get('is_error', False)
                                content = evt.get('content', '')
                                
                                if is_error:
                                    task.add_progress_message(f"❌ Tool {tool_name} failed: {content[:100]}", min(progress_percent + 1, 95))
                                    logger.warning("Tool failed: %s - %s", tool_name, content[:100])
                                else:
                                    # Parse tool output for important information
                                    enhanced_output = self._enhance_command_output(content, tool_name)
                                    if enhanced_output:
                                        task.add_progress_message(enhanced_output, min(progress_percent + 1, 95))
                                    else:
                                        task.add_progress_message(f"✅ {tool_name} completed", min(progress_percent + 1, 95))
                                    logger.info("Tool completed: %s", tool_name)
                            
                            elif event_type == 'result':
                                # Final result
                                session_id = evt.get('session_id', 'unknown')
                                duration_ms = evt.get('duration_ms', 0)
                                num_turns = evt.get('num_turns', 0)
                                result_text = evt.get('result', '')
                                
                                task.add_progress_message(f"✅ Session completed in {duration_ms/1000:.1f}s ({num_turns} turns)", min(progress_percent + 2, 95))
                                logger.info("Claude session completed: %s turns, %dms", num_turns, duration_ms)
                                
                                if result_text:
                                    response_buffer.append(result_text)
                            
                            else:
                                # Unknown event type - log for debugging
                                logger.debug("Unknown event type: %s", event_type)
                            
                            # Handle JSON events
                            if evt.get('type') == 'assistant':
                                parts = evt['message']['content']
                                if parts and parts[0]['type'] == 'text':
                                    chunk_text = parts[0]['text'].strip()
                                    response_buffer.append(chunk_text)
                                    # Stream assistant messages with context
                                    task.add_progress_message(f"🤖 {agent_name}: {chunk_text[:200]}{'...' if len(chunk_text) > 200 else ''}", min(progress_percent + 1, 95))
                                    progress_percent = min(progress_percent + 1, 95)
                                    logger.info("Assistant message: %s", chunk_text[:100])
                            elif evt.get('type') == 'result':
                                session_id = evt.get('session_id')
                                logger.info("Session completed: %s", session_id)
                            elif evt.get('type') == 'tool_use':
                                tool_name = evt.get('name', 'unknown')
                                task.add_progress_message(f"🔧 Executing: {tool_name}", min(progress_percent + 1, 95))
                                logger.info("Tool use: %s", tool_name)
                            elif evt.get('type') == 'tool_result':
                                tool_name = evt.get('tool_name', 'unknown')
                                is_error = evt.get('is_error', False)
                                if is_error:
                                    task.add_progress_message(f"❌ Tool {tool_name} failed", min(progress_percent + 1, 95))
                                else:
                                    task.add_progress_message(f"✅ Tool {tool_name} completed", min(progress_percent + 1, 95))
                                logger.info("Tool result: %s (error: %s)", tool_name, is_error)
                        except json.JSONDecodeError:
                            # This shouldn't happen with stream-json, but handle it gracefully
                            logger.warning("Non-JSON output from stream-json mode: %s", raw_line)
                            if raw_line:
                                # Try to extract useful information anyway
                                enhanced_line = self._enhance_command_output(raw_line, agent_name)
                                if enhanced_line:
                                    task.add_progress_message(enhanced_line, min(progress_percent + 1, 95))
                                else:
                                    task.add_progress_message(f"📝 {raw_line[:150]}{'...' if len(raw_line) > 150 else ''}", min(progress_percent + 1, 95))
                                progress_percent = min(progress_percent + 1, 95)

                    # Timeout check
                    if time.time() - start_time > timeout_seconds:
                        raise subprocess.TimeoutExpired(cmd, timeout_seconds)

                # Wait for stderr thread to finish
                stderr_thread.join(timeout=5)
                
                # Capture final stderr and return code
                stderr_data = '\n'.join(stderr_lines) if stderr_lines else ''
                returncode = process.returncode
                
                logger.info("Claude Code execution finished. Return code: %s, Lines processed: %d", returncode, lines_read)
                
                if lines_read == 0:
                    logger.error("No output received from Claude Code CLI!")
                    task.add_progress_message("❌ No output received from Claude Code - check configuration", 85)
                    
                    # Try to diagnose the issue
                    if returncode != 0:
                        task.add_progress_message(f"🔍 Claude Code exited with code {returncode}", 85)
                        if stderr_data:
                            task.add_progress_message(f"📋 Error output: {stderr_data[:300]}", 85)
                else:
                    task.add_progress_message(f"📊 Processed {lines_read} lines of output", 87)

            except subprocess.TimeoutExpired:
                logger.error("Claude Code execution timed out after %d seconds", timeout_seconds)
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                
                return {
                    'success': False,
                    'error': f'Claude Code execution timed out after {timeout_seconds} seconds',
                    'agent_used': agent_name,
                    'lines_processed': lines_read
                }
            except Exception as e:
                logger.error("Error during Claude Code execution: %s", e)
                process.terminate()
                return {
                    'success': False,
                    'error': f'Claude Code execution error: {str(e)}',
                    'agent_used': agent_name,
                    'lines_processed': 0
                }

            if returncode != 0:
                error_msg = f"Claude Code exited with code {returncode}"
                if stderr_data:
                    error_msg += f": {stderr_data}"
                elif lines_read == 0:
                    error_msg += ": No output received - possible authentication or configuration issue"
                
                logger.error("Claude Code failed: %s", error_msg)
                task.add_progress_message(f"❌ {error_msg}", 0)
                
                return {
                    'success': False,
                    'error': error_msg,
                    'agent_used': agent_name,
                    'lines_processed': lines_read
                }

            # After success – analyse repo for changes
            task.add_progress_message("📊 Analyzing repository changes...", 85)

            # Get detailed git status
            git_status = subprocess.run(['git', 'status', '--porcelain'], cwd=workspace_path, capture_output=True, text=True)
            files_changed = [line.strip() for line in git_status.stdout.strip().split('\n') if line.strip()] if git_status.returncode == 0 else []
            
            if files_changed:
                task.add_progress_message(f"📁 Files modified: {len(files_changed)} files", 87)
                for i, file_change in enumerate(files_changed[:5]):  # Show first 5 files
                    status_code = file_change[:2].strip()
                    filename = file_change[3:] if len(file_change) > 3 else file_change
                    status_emoji = "📝" if "M" in status_code else "➕" if "A" in status_code else "❌" if "D" in status_code else "📄"
                    task.add_progress_message(f"  {status_emoji} {filename}", 87)
                if len(files_changed) > 5:
                    task.add_progress_message(f"  ... and {len(files_changed) - 5} more files", 87)

            # Use base_branch..HEAD to get only new commits on this branch
            # First, get the base branch from git config or use 'main' as fallback
            base_branch_result = subprocess.run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'], cwd=workspace_path, capture_output=True, text=True)
            if base_branch_result.returncode == 0:
                base_branch = base_branch_result.stdout.strip().split('/')[-1]
            else:
                base_branch = 'main'  # fallback
            
            # Get commits with more detail
            git_log = subprocess.run(['git', 'log', f'{base_branch}..HEAD', '--oneline', '-n', '20'], cwd=workspace_path, capture_output=True, text=True)
            commits = [line.strip() for line in git_log.stdout.strip().split('\n') if line.strip()] if git_log.returncode == 0 else []
            
            if commits:
                task.add_progress_message(f"💾 Commits created: {len(commits)}", 89)
                for i, commit in enumerate(commits[:3]):  # Show first 3 commits
                    task.add_progress_message(f"  📝 {commit}", 89)
                if len(commits) > 3:
                    task.add_progress_message(f"  ... and {len(commits) - 3} more commits", 89)
            else:
                task.add_progress_message("⚠️ No commits found on feature branch", 89)

            full_text = '\n'.join(response_buffer)

            logger.info("Claude Code execution completed successfully with %s (%d files, %d commits)", agent_name, len(files_changed), len(commits))

            return {
                'success': True,
                'output': full_text,
                'session_id': session_id or 'unknown',
                'files_changed': files_changed,
                'commits': commits,
                'agent_used': agent_name
            }
                
        except subprocess.TimeoutExpired:
            logger.error(f"Claude Code execution timed out for {agent_name}")
            return {
                'success': False,
                'error': f"Claude Code execution timed out after 15 minutes",
                'agent_used': agent_name
            }
        except Exception as e:
            logger.error(f"Error executing Claude Code with {agent_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent_used': agent_name
            }
    
    def _enhance_command_output(self, raw_line: str, agent_name: str) -> Optional[str]:
        """
        Enhance raw command output for better user experience in live logs
        
        Args:
            raw_line: Raw output line from Claude Code CLI
            agent_name: Name of the agent being executed
        
        Returns:
            Enhanced output line or None if should be filtered out
        """
        if not raw_line.strip():
            return None
        
        line = raw_line.strip()
        
        # Git operations
        if "git checkout" in line.lower():
            return f"🌿 Creating new branch: {line.split()[-1] if line.split() else 'unknown'}"
        elif "git add" in line.lower():
            return f"📝 Staging changes for commit"
        elif "git commit" in line.lower():
            return f"💾 Creating commit: {line.split('-m')[-1].strip('"') if '-m' in line else 'changes'}"
        elif "git push" in line.lower():
            return f"📤 Pushing changes to remote repository"
        elif "git clone" in line.lower():
            return f"📦 Cloning repository"
        elif "git branch" in line.lower():
            return f"🌿 Branch operation: {line}"
        
        # File operations
        elif line.startswith("Creating") or line.startswith("Writing"):
            return f"📄 {line}"
        elif line.startswith("Reading") or line.startswith("Loading"):
            return f"📖 {line}"
        elif "mkdir" in line.lower():
            return f"📁 Creating directory: {line.split()[-1] if line.split() else 'unknown'}"
        
        # Test operations
        elif "test" in line.lower() and ("run" in line.lower() or "pass" in line.lower() or "fail" in line.lower()):
            return f"🧪 {line}"
        elif "npm test" in line.lower() or "pytest" in line.lower() or "jest" in line.lower():
            return f"🧪 Running tests: {line}"
        
        # Build operations
        elif "npm run" in line.lower() or "yarn" in line.lower() or "build" in line.lower():
            return f"🏗️ Build: {line}"
        
        # Installation operations
        elif "npm install" in line.lower() or "pip install" in line.lower() or "yarn add" in line.lower():
            return f"📦 Installing dependencies: {line}"
        
        # API/Network operations
        elif "curl" in line.lower() or "http" in line.lower() or "api" in line.lower():
            return f"🌐 API call: {line}"
        
        # Claude specific operations
        elif "claude" in line.lower() and not line.startswith("claude"):  # Avoid showing the command itself
            return f"🤖 Claude: {line}"
        
        # Error messages
        elif "error" in line.lower() or "failed" in line.lower() or "exception" in line.lower():
            return f"❌ Error: {line}"
        
        # Success messages
        elif "success" in line.lower() or "completed" in line.lower() or "done" in line.lower():
            return f"✅ {line}"
        
        # Important status updates
        elif line.startswith("[INFO]") or line.startswith("INFO:"):
            return f"ℹ️ {line.replace('[INFO]', '').replace('INFO:', '').strip()}"
        elif line.startswith("[WARN]") or line.startswith("WARN:") or line.startswith("WARNING:"):
            return f"⚠️ {line.replace('[WARN]', '').replace('WARN:', '').replace('WARNING:', '').strip()}"
        
        # File paths and important operations
        elif "/" in line and (".py" in line or ".js" in line or ".ts" in line or ".jsx" in line or ".tsx" in line or ".md" in line):
            return f"📄 Working with: {line}"
        
        # Show lines that seem to indicate progress or important operations
        elif len(line) > 10 and any(keyword in line.lower() for keyword in [
            "processing", "analyzing", "implementing", "generating", "updating", "modifying",
            "creating", "building", "testing", "deploying", "installing", "configuring"
        ]):
            return f"⚙️ {line}"
        
        # Filter out very verbose/debug lines but keep meaningful ones
        elif len(line) < 200 and not any(noise in line.lower() for noise in [
            "debug:", "trace:", "verbose:", "[debug]", "[trace]", "\x1b", "\033"
        ]):
            return f"🔧 {line}"
        
        return None
    
    def _is_important_output(self, line: str) -> bool:
        """
        Determine if output line is important enough to always show (bypass throttling)
        """
        if not line:
            return False
        
        line_lower = line.lower()
        
        # Always show these important operations
        important_keywords = [
            "git commit", "git push", "git checkout", "git clone", "git branch",
            "creating branch", "pushing to", "pull request", "pr created",
            "error", "failed", "exception", "success", "completed", "done",
            "test", "build", "deploy", "install"
        ]
        
        return any(keyword in line_lower for keyword in important_keywords)

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