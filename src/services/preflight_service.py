"""
Preflight Connection Service
Handles GitHub setup verification and Claude Code agents directory checking
"""

import os
import logging
import requests
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PreflightService:
    """Service for performing preflight checks before task execution"""
    
    def __init__(self):
        self.api_base = "https://api.github.com"
    
    def perform_preflight_checks(self, project_id: str, github_token: str, repo_url: str) -> Dict[str, Any]:
        """
        Perform comprehensive preflight checks for a project
        
        Args:
            project_id: Project identifier
            github_token: GitHub Personal Access Token
            repo_url: Repository URL
        
        Returns:
            Dictionary with check results and friendly status
        """
        try:
            # Initialize results
            results = {
                'project_id': project_id,
                'github_connected': False,
                'repo_accessible': False,
                'token_has_repo_scope': False,
                'base_branch': None,
                'base_branch_sha': None,
                'agents_directory_exists': False,
                'agents_count': 0,
                'friendly_status': 'Not connected',
                'errors': [],
                'warnings': []
            }
            
            # Check GitHub token and connectivity
            github_results = self._check_github_connectivity(github_token)
            results.update(github_results)
            
            # Check repository access if GitHub is connected
            if results['github_connected']:
                repo_results = self._check_repository_access(github_token, repo_url)
                results.update(repo_results)
                # Store the normalized repo name for friendly status
                if repo_url:
                    results['repo_name'] = self._extract_owner_repo(repo_url) or repo_url
            
            # Check Claude Code agents directory
            agents_results = self._check_agents_directory(repo_url, github_token)
            results.update(agents_results)
            
            # Generate friendly status
            results['friendly_status'] = self._generate_friendly_status(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing preflight checks: {e}")
            return {
                'project_id': project_id,
                'github_connected': False,
                'repo_accessible': False,
                'token_has_repo_scope': False,
                'base_branch': None,
                'base_branch_sha': None,
                'agents_directory_exists': False,
                'agents_count': 0,
                'friendly_status': f'Error: {str(e)}',
                'errors': [str(e)],
                'warnings': []
            }
    
    def _check_github_connectivity(self, github_token: str) -> Dict[str, Any]:
        """Check GitHub API connectivity and token validity"""
        results = {
            'github_connected': False,
            'token_has_repo_scope': False,
            'errors': [],
            'warnings': []
        }
        
        if not github_token:
            results['errors'].append('GitHub token not provided')
            return results
        
        try:
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Test API access and get user info
            response = requests.get(f'{self.api_base}/user', headers=headers, timeout=10)
            
            if response.status_code == 200:
                results['github_connected'] = True
                
                # Check token scopes
                scopes = response.headers.get('X-OAuth-Scopes', '')
                if 'repo' in scopes or 'public_repo' in scopes:
                    results['token_has_repo_scope'] = True
                else:
                    results['warnings'].append('GitHub token may not have repo scope')
                    
            elif response.status_code == 401:
                results['errors'].append('GitHub token is invalid or expired')
            else:
                results['errors'].append(f'GitHub API error: {response.status_code}')
                
        except requests.RequestException as e:
            results['errors'].append(f'GitHub API request failed: {str(e)}')
        except Exception as e:
            results['errors'].append(f'GitHub connectivity check failed: {str(e)}')
        
        return results
    
    def _check_repository_access(self, github_token: str, repo_url: str) -> Dict[str, Any]:
        """Check repository access and get default branch info"""
        results = {
            'repo_accessible': False,
            'base_branch': None,
            'base_branch_sha': None,
            'errors': [],
            'warnings': []
        }
        
        if not repo_url:
            results['warnings'].append('Repository URL not provided')
            return results
        
        try:
            # Extract owner/repo from URL
            owner_repo = self._extract_owner_repo(repo_url)
            if not owner_repo:
                results['errors'].append(f'Invalid repository URL format: {repo_url}')
                return results
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Get repository info
            repo_response = requests.get(
                f'{self.api_base}/repos/{owner_repo}',
                headers=headers,
                timeout=10
            )
            
            if repo_response.status_code == 200:
                repo_data = repo_response.json()
                results['repo_accessible'] = True
                results['base_branch'] = repo_data.get('default_branch', 'main')
                
                # Get the SHA of the default branch
                branch_response = requests.get(
                    f'{self.api_base}/repos/{owner_repo}/git/refs/heads/{results["base_branch"]}',
                    headers=headers,
                    timeout=10
                )
                
                if branch_response.status_code == 200:
                    results['base_branch_sha'] = branch_response.json()['object']['sha']
                else:
                    results['warnings'].append(f'Could not get SHA for branch {results["base_branch"]}')
                    
            elif repo_response.status_code == 404:
                results['errors'].append('Repository not found or not accessible')
            elif repo_response.status_code == 403:
                results['errors'].append('Repository access forbidden - check token permissions')
            else:
                results['errors'].append(f'Repository API error: {repo_response.status_code}')
                
        except Exception as e:
            results['errors'].append(f'Repository access check failed: {str(e)}')
        
        return results
    
    def _check_agents_directory(self, repo_url: str, github_token: str) -> Dict[str, Any]:
        """Check for .claude/agents/ directory and count sub-agent files"""
        results = {
            'agents_directory_exists': False,
            'agents_count': 0,
            'errors': [],
            'warnings': []
        }
        
        if not repo_url or not github_token:
            return results
        
        try:
            # Extract owner/repo from URL
            owner_repo = self._extract_owner_repo(repo_url)
            if not owner_repo:
                return results
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Check if .claude/agents directory exists
            agents_response = requests.get(
                f'{self.api_base}/repos/{owner_repo}/contents/.claude/agents',
                headers=headers,
                timeout=10
            )
            
            if agents_response.status_code == 200:
                results['agents_directory_exists'] = True
                
                # Count agent files (look for .md files)
                contents = agents_response.json()
                if isinstance(contents, list):
                    agent_files = [
                        item for item in contents 
                        if item.get('type') == 'file' and item.get('name', '').endswith('.md')
                    ]
                    results['agents_count'] = len(agent_files)
                else:
                    results['warnings'].append('.claude/agents exists but could not list contents')
                    
            elif agents_response.status_code == 404:
                # Directory doesn't exist - this is not an error, just no agents
                results['warnings'].append('.claude/agents directory not found')
            else:
                results['warnings'].append(f'Could not check .claude/agents directory: {agents_response.status_code}')
                
        except Exception as e:
            results['warnings'].append(f'Agents directory check failed: {str(e)}')
        
        return results
    
    def _extract_owner_repo(self, repo_url: str) -> Optional[str]:
        """Extract owner/repo from various GitHub URL formats"""
        try:
            if repo_url.startswith('https://github.com/'):
                path = repo_url.replace('https://github.com/', '')
                if path.endswith('.git'):
                    path = path[:-4]
                return path
            elif repo_url.startswith('git@github.com:'):
                path = repo_url.replace('git@github.com:', '')
                if path.endswith('.git'):
                    path = path[:-4]
                return path
            elif '/' in repo_url and not repo_url.startswith('http'):
                return repo_url
            else:
                return None
        except Exception:
            return None
    
    def _generate_friendly_status(self, results: Dict[str, Any]) -> str:
        """Generate a friendly status string from check results"""
        try:
            if not results['github_connected']:
                return 'Not connected to GitHub'
            
            if not results['repo_accessible']:
                return 'GitHub connected • Repository not accessible'
            
            # Build status components
            status_parts = ['Connected']
            
            # Add repo name if available
            if results.get('repo_name'):
                status_parts.append(results['repo_name'])
            
            # Add base branch
            if results.get('base_branch'):
                status_parts.append(f"base: {results['base_branch']}")
            
            # Add agents count
            agents_count = results.get('agents_count', 0)
            if agents_count > 0:
                agent_word = 'agent' if agents_count == 1 else 'agents'
                status_parts.append(f'{agents_count} sub {agent_word}')
            else:
                status_parts.append('no sub agents')
            
            return ' • '.join(status_parts)
            
        except Exception as e:
            logger.error(f"Error generating friendly status: {e}")
            return 'Status unknown'
    
    def update_project_connection_status(self, project_id: str, github_token: str, repo_url: str) -> Dict[str, Any]:
        """
        Update a project's connection status after performing preflight checks
        
        Args:
            project_id: Project identifier
            github_token: GitHub Personal Access Token
            repo_url: Repository URL
        
        Returns:
            Updated preflight check results
        """
        try:
            # Import here to avoid circular imports
            try:
                from ..models.mission_control_project import MissionControlProject
                from ..models.base import db
            except ImportError:
                from models.mission_control_project import MissionControlProject
                from models.base import db
            
            # Perform preflight checks
            results = self.perform_preflight_checks(project_id, github_token, repo_url)
            
            # Update project with connection status
            project = MissionControlProject.query.get(project_id)
            if project:
                project.connection_status = results['friendly_status']
                db.session.commit()
                results['project_updated'] = True
            else:
                results['errors'].append(f'Project {project_id} not found')
                results['project_updated'] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Error updating project connection status: {e}")
            return {
                'project_id': project_id,
                'friendly_status': f'Error: {str(e)}',
                'project_updated': False,
                'errors': [str(e)]
            }


# Global instance
_preflight_service = None


def get_preflight_service() -> PreflightService:
    """Get the global preflight service instance"""
    global _preflight_service
    if _preflight_service is None:
        _preflight_service = PreflightService()
    return _preflight_service