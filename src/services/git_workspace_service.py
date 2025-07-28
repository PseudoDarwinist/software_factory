"""
Git Workspace Service
Manages local Git clones and branch creation for task execution
"""

import os
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GitWorkspaceService:
    """Service for managing task-specific Git workspaces"""
    
    def __init__(self, base_runs_dir: str = "runs"):
        self.base_runs_dir = Path(base_runs_dir)
        self.base_runs_dir.mkdir(exist_ok=True)
        
        # Create .gitignore for runs directory
        gitignore_path = self.base_runs_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("# Task execution workspaces\n*\n")
    
    def create_task_workspace(self, task_id: str, repo_url: str, github_token: str, 
                            branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
        """
        Create a task-specific workspace with local clone and branch
        
        Args:
            task_id: Unique task identifier
            repo_url: GitHub repository URL
            github_token: GitHub Personal Access Token
            branch_name: Name of branch to create
            base_branch: Base branch to checkout from (default: main)
        
        Returns:
            Dict with workspace_path, branch_name, and success status
        """
        try:
            # Create task-specific directory
            workspace_path = self.base_runs_dir / f"task-{task_id}"
            
            # Clean up existing workspace if it exists
            if workspace_path.exists():
                logger.info(f"Cleaning up existing workspace: {workspace_path}")
                shutil.rmtree(workspace_path)
            
            workspace_path.mkdir(parents=True)
            
            # Prepare authenticated repo URL
            auth_repo_url = self._add_auth_to_url(repo_url, github_token)
            
            # Step 1: Shallow clone the repository
            logger.info(f"Cloning repository {repo_url} to {workspace_path}")
            clone_result = subprocess.run([
                "git", "clone", "--depth=1", "--branch", base_branch,
                auth_repo_url, str(workspace_path)
            ], capture_output=True, text=True, timeout=60)
            
            if clone_result.returncode != 0:
                error_msg = clone_result.stderr.strip()
                
                # Provide more helpful error messages
                if "does not exist" in error_msg:
                    raise Exception(f"Repository '{repo_url}' does not exist or is not accessible. Please check the repository URL and GitHub token permissions.")
                elif "Permission denied" in error_msg:
                    raise Exception(f"Permission denied accessing repository '{repo_url}'. Please check the GitHub token has the required permissions.")
                elif "Authentication failed" in error_msg:
                    raise Exception(f"Authentication failed for repository '{repo_url}'. Please check the GitHub token is valid.")
                else:
                    raise Exception(f"Git clone failed: {error_msg}")
            
            # Step 2: Create and checkout new branch
            logger.info(f"Creating branch {branch_name} from {base_branch}")
            
            # Create new branch
            branch_result = subprocess.run([
                "git", "checkout", "-b", branch_name
            ], cwd=workspace_path, capture_output=True, text=True, timeout=30)
            
            if branch_result.returncode != 0:
                raise Exception(f"Branch creation failed: {branch_result.stderr}")
            
            # Step 3: Push branch to remote to create it on GitHub
            logger.info(f"Pushing branch {branch_name} to remote")
            push_result = subprocess.run([
                "git", "push", "-u", "origin", branch_name
            ], cwd=workspace_path, capture_output=True, text=True, timeout=30)
            
            if push_result.returncode != 0:
                raise Exception(f"Branch push failed: {push_result.stderr}")
            
            # Step 4: Verify workspace is ready
            if not (workspace_path / ".git").exists():
                raise Exception("Git repository not properly initialized")
            
            logger.info(f"Successfully created workspace for task {task_id}")
            
            return {
                'success': True,
                'workspace_path': str(workspace_path.absolute()),
                'branch_name': branch_name,
                'base_branch': base_branch,
                'repo_url': repo_url,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Git operation timed out for task {task_id}: {e}")
            return {
                'success': False,
                'error': f'Git operation timed out: {str(e)}',
                'workspace_path': None
            }
        except Exception as e:
            logger.error(f"Failed to create workspace for task {task_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'workspace_path': None
            }
    
    def cleanup_task_workspace(self, task_id: str) -> bool:
        """
        Clean up a task workspace
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            workspace_path = self.base_runs_dir / f"task-{task_id}"
            
            if workspace_path.exists():
                logger.info(f"Cleaning up workspace: {workspace_path}")
                shutil.rmtree(workspace_path)
                return True
            else:
                logger.info(f"Workspace does not exist: {workspace_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cleanup workspace for task {task_id}: {e}")
            return False
    
    def get_workspace_path(self, task_id: str) -> Optional[Path]:
        """
        Get the workspace path for a task
        
        Args:
            task_id: Task identifier
        
        Returns:
            Path to workspace if it exists, None otherwise
        """
        workspace_path = self.base_runs_dir / f"task-{task_id}"
        return workspace_path if workspace_path.exists() else None
    
    def list_workspaces(self) -> Dict[str, Dict[str, Any]]:
        """
        List all active workspaces
        
        Returns:
            Dict mapping task_id to workspace info
        """
        workspaces = {}
        
        try:
            for workspace_dir in self.base_runs_dir.iterdir():
                if workspace_dir.is_dir() and workspace_dir.name.startswith("task-"):
                    task_id = workspace_dir.name[5:]  # Remove "task-" prefix
                    
                    # Get basic info about the workspace
                    git_dir = workspace_dir / ".git"
                    if git_dir.exists():
                        try:
                            # Get current branch
                            branch_result = subprocess.run([
                                "git", "branch", "--show-current"
                            ], cwd=workspace_dir, capture_output=True, text=True, timeout=10)
                            
                            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
                            
                            # Get last commit info
                            commit_result = subprocess.run([
                                "git", "log", "-1", "--format=%H %s"
                            ], cwd=workspace_dir, capture_output=True, text=True, timeout=10)
                            
                            last_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
                            
                            workspaces[task_id] = {
                                'path': str(workspace_dir.absolute()),
                                'current_branch': current_branch,
                                'last_commit': last_commit,
                                'created_at': datetime.fromtimestamp(workspace_dir.stat().st_ctime).isoformat()
                            }
                            
                        except Exception as e:
                            logger.warning(f"Failed to get info for workspace {task_id}: {e}")
                            workspaces[task_id] = {
                                'path': str(workspace_dir.absolute()),
                                'error': str(e)
                            }
                            
        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
        
        return workspaces
    
    def cleanup_all_workspaces(self) -> Dict[str, bool]:
        """
        Clean up all workspaces (for maintenance)
        
        Returns:
            Dict mapping task_id to cleanup success status
        """
        results = {}
        
        try:
            for workspace_dir in self.base_runs_dir.iterdir():
                if workspace_dir.is_dir() and workspace_dir.name.startswith("task-"):
                    task_id = workspace_dir.name[5:]  # Remove "task-" prefix
                    results[task_id] = self.cleanup_task_workspace(task_id)
                    
        except Exception as e:
            logger.error(f"Failed to cleanup all workspaces: {e}")
        
        return results
    
    def _add_auth_to_url(self, repo_url: str, github_token: str) -> str:
        """
        Add authentication token to GitHub URL
        
        Args:
            repo_url: Original repository URL (can be full URL or owner/repo format)
            github_token: GitHub Personal Access Token
        
        Returns:
            Authenticated URL
        """
        if repo_url.startswith("https://github.com/"):
            # Convert https://github.com/owner/repo to https://token@github.com/owner/repo
            return repo_url.replace("https://github.com/", f"https://{github_token}@github.com/")
        elif repo_url.startswith("git@github.com:"):
            # Convert SSH to HTTPS with token
            repo_path = repo_url.replace("git@github.com:", "")
            return f"https://{github_token}@github.com/{repo_path}"
        elif "/" in repo_url and not repo_url.startswith("http"):
            # Handle owner/repo format - convert to full HTTPS URL with token
            return f"https://{github_token}@github.com/{repo_url}"
        else:
            # Assume it's already a properly formatted URL
            return repo_url
    
    def get_runs_directory_info(self) -> Dict[str, Any]:
        """
        Get information about the runs directory
        
        Returns:
            Dict with directory info and hygiene recommendations
        """
        try:
            total_size = 0
            workspace_count = 0
            
            for workspace_dir in self.base_runs_dir.iterdir():
                if workspace_dir.is_dir():
                    workspace_count += 1
                    # Calculate directory size
                    for file_path in workspace_dir.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
            
            # Convert bytes to MB
            total_size_mb = total_size / (1024 * 1024)
            
            return {
                'runs_directory': str(self.base_runs_dir.absolute()),
                'workspace_count': workspace_count,
                'total_size_mb': round(total_size_mb, 2),
                'hygiene_recommendations': [
                    f"Run cleanup after completing tasks to save disk space",
                    f"Current usage: {workspace_count} workspaces, {total_size_mb:.1f} MB",
                    f"Each workspace contains a shallow clone (~5-50 MB typically)"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get runs directory info: {e}")
            return {
                'runs_directory': str(self.base_runs_dir.absolute()),
                'error': str(e)
            }


# Global instance
_git_workspace_service = None


def get_git_workspace_service() -> GitWorkspaceService:
    """Get the global Git workspace service instance"""
    global _git_workspace_service
    if _git_workspace_service is None:
        _git_workspace_service = GitWorkspaceService()
    return _git_workspace_service