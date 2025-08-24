"""
Real Validation Detector - Detects actual validation processes in repositories
"""

import logging
import os
from typing import List, Dict, Optional

try:
    from ..integrations.github_adapter import GitHubAdapter
    from ..models.validation_run import ValidationRun
    from ..models.base import db
except ImportError:
    from integrations.github_adapter import GitHubAdapter
    from models.validation_run import ValidationRun
    from models.base import db

logger = logging.getLogger(__name__)


class RealValidationDetector:
    """Detects real validation processes in repositories"""
    
    def __init__(self):
        self.github_adapter = GitHubAdapter()
    
    def detect_and_populate_validation_checks(self, validation_run: ValidationRun, repo_url: str):
        """
        Detect real validation processes and populate validation run with actual checks
        """
        try:
            # Get the GitHub token from the project
            github_token = self._get_project_github_token(validation_run.project_id)
            if not github_token:
                logger.warning(f"No GitHub token found for project {validation_run.project_id}")
                return
            
            # Extract repo info from URL
            repo_info = self._parse_repo_url(repo_url)
            if not repo_info:
                logger.warning(f"Could not parse repository URL: {repo_url}")
                return
            
            owner, repo = repo_info
            logger.info(f"Detecting validation processes for {owner}/{repo}")
            
            # Configure GitHub adapter with project token
            self.github_adapter.configure(github_token=github_token)
            
            # Check for GitHub Actions workflows
            workflows = self._get_github_workflows(owner, repo)
            
            # Check for recent workflow runs triggered by this PR
            workflow_runs = self._get_workflow_runs_for_pr(owner, repo, validation_run.pr_number)
            
            # Add real validation checks based on what we find
            self._add_real_validation_checks(validation_run, workflows, workflow_runs)
            
        except Exception as e:
            logger.error(f"Error detecting validation processes: {e}")
    
    def _get_project_github_token(self, project_id: str) -> Optional[str]:
        """Get GitHub token from the project"""
        try:
            from ..models.mission_control_project import MissionControlProject
            
            project = MissionControlProject.query.get(project_id)
            if project and project.github_token:
                logger.info(f"Found GitHub token for project {project_id}")
                return project.github_token
            else:
                logger.warning(f"No GitHub token found for project {project_id}")
                return None
                
        except ImportError:
            try:
                from models.mission_control_project import MissionControlProject
                
                project = MissionControlProject.query.get(project_id)
                if project and project.github_token:
                    logger.info(f"Found GitHub token for project {project_id}")
                    return project.github_token
                else:
                    logger.warning(f"No GitHub token found for project {project_id}")
                    return None
            except Exception as e:
                logger.error(f"Error retrieving GitHub token for project {project_id}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving GitHub token for project {project_id}: {e}")
            return None
    
    def _parse_repo_url(self, repo_url: str) -> Optional[tuple]:
        """Parse GitHub repository URL to extract owner and repo name"""
        try:
            # Handle various GitHub URL formats
            if 'github.com' in repo_url:
                parts = repo_url.replace('https://github.com/', '').replace('http://github.com/', '').split('/')
                if len(parts) >= 2:
                    return parts[0], parts[1].replace('.git', '')
            return None
        except Exception:
            return None
    
    def _get_github_workflows(self, owner: str, repo: str) -> List[Dict]:
        """Get GitHub Actions workflows for the repository"""
        try:
            # Use GitHub API to get workflows
            workflows = self.github_adapter.get_workflows(owner, repo)
            return workflows or []
        except Exception as e:
            logger.warning(f"Could not fetch workflows for {owner}/{repo}: {e}")
            return []
    
    def _get_workflow_runs_for_pr(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """Get workflow runs triggered by the PR merge"""
        try:
            # Get recent workflow runs that might be related to this PR
            workflow_runs = self.github_adapter.get_recent_workflow_runs(owner, repo, limit=10)
            
            # Filter for runs that might be related to this PR
            # This is a simplified approach - in reality you'd match by commit SHA
            return workflow_runs or []
        except Exception as e:
            logger.warning(f"Could not fetch workflow runs for {owner}/{repo}: {e}")
            return []
    
    def _add_real_validation_checks(self, validation_run: ValidationRun, workflows: List[Dict], workflow_runs: List[Dict]):
        """Add real validation checks based on detected workflows and runs"""
        import datetime as _dt
        
        if not workflows and not workflow_runs:
            logger.info(f"No GitHub Actions found for validation run {validation_run.id}")
            return
        
        now_iso = _dt.datetime.utcnow().isoformat()
        
        # Add checks for each real workflow
        for workflow in workflows:
            workflow_name = workflow.get('name', 'Unknown Workflow')
            workflow_id = workflow.get('id')
            
            # Find corresponding workflow run
            matching_run = None
            for run in workflow_runs:
                if run.get('workflow_id') == workflow_id:
                    matching_run = run
                    break
            
            # Determine check type based on workflow name
            check_type = self._determine_check_type(workflow_name)
            
            # Determine status based on workflow run
            status = 'pending'
            metadata = {'workflow_name': workflow_name}
            
            if matching_run:
                run_status = matching_run.get('status', 'unknown')
                run_conclusion = matching_run.get('conclusion')
                
                if run_status == 'completed':
                    if run_conclusion == 'success':
                        status = 'success'
                    elif run_conclusion == 'failure':
                        status = 'error'
                    else:
                        status = 'warning'
                elif run_status == 'in_progress':
                    status = 'running'
                
                metadata.update({
                    'workflow_run_id': matching_run.get('id'),
                    'workflow_url': matching_run.get('html_url'),
                    'run_status': run_status,
                    'conclusion': run_conclusion
                })
            
            # Add the real validation check
            validation_run.add_validation_check(
                check_id=f"{validation_run.id}-workflow-{workflow_id}",
                name=workflow_name,
                check_type=check_type,
                status=status,
                metadata=metadata
            )
            
            logger.info(f"Added real validation check: {workflow_name} ({status})")
    
    def _determine_check_type(self, workflow_name: str) -> str:
        """Determine validation check type based on workflow name"""
        name_lower = workflow_name.lower()
        
        if any(keyword in name_lower for keyword in ['test', 'spec', 'unit', 'integration']):
            return 'test'
        elif any(keyword in name_lower for keyword in ['deploy', 'deployment', 'release']):
            return 'deployment'
        elif any(keyword in name_lower for keyword in ['security', 'scan', 'vulnerability', 'codeql']):
            return 'security'
        elif any(keyword in name_lower for keyword in ['build', 'compile']):
            return 'test'  # Build processes are often part of testing
        else:
            return 'monitoring'  # Default type


# Global instance
_real_validation_detector = None

def get_real_validation_detector():
    """Get the global real validation detector instance"""
    global _real_validation_detector
    if _real_validation_detector is None:
        _real_validation_detector = RealValidationDetector()
    return _real_validation_detector