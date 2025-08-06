"""
GitHub Pull Request Service
Handles creation and management of GitHub pull requests
"""

import logging
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitHubPRService:
    """Service for creating and managing GitHub pull requests"""
    
    def __init__(self):
        self.api_base = "https://api.github.com"
    
    def _parse_repo_url(self, repo_url: str) -> tuple:
        """
        Parse repository URL to extract owner and repo name
        
        Args:
            repo_url: GitHub repository URL (https://github.com/owner/repo or owner/repo)
        
        Returns:
            Tuple of (owner, repo)
        """
        if repo_url.startswith('https://github.com/'):
            # Full URL format
            parsed = urlparse(repo_url)
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1].replace('.git', '')
        elif '/' in repo_url and not repo_url.startswith('http'):
            # owner/repo format
            parts = repo_url.split('/')
            if len(parts) >= 2:
                return parts[0], parts[1].replace('.git', '')
        
        raise ValueError(f"Invalid repository URL format: {repo_url}")
    
    def create_pull_request(self, repo_url: str, github_token: str, branch_name: str, 
                          title: str, body: str, base_branch: str = "main", 
                          draft: bool = True) -> Dict[str, Any]:
        """
        Create a pull request on GitHub
        
        Args:
            repo_url: Repository URL
            github_token: GitHub access token
            branch_name: Source branch name
            title: PR title
            body: PR description
            base_branch: Target branch (default: main)
            draft: Whether to create as draft PR
        
        Returns:
            Dict with PR creation result
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            
            # Prepare PR data
            pr_data = {
                "title": title,
                "body": body,
                "head": branch_name,
                "base": base_branch,
                "draft": draft
            }
            
            # Make API request
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.api_base}/repos/{owner}/{repo}/pulls"
            
            logger.info(f"Creating PR: {title} ({branch_name} -> {base_branch})")
            
            response = requests.post(url, json=pr_data, headers=headers, timeout=30)
            
            if response.status_code == 201:
                pr_info = response.json()
                logger.info(f"PR created successfully: {pr_info['html_url']}")
                
                return {
                    'success': True,
                    'pr_url': pr_info['html_url'],
                    'pr_number': pr_info['number'],
                    'pr_id': pr_info['id'],
                    'api_url': pr_info['url']
                }
            else:
                error_msg = f"Failed to create PR: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Error creating PR: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def update_pull_request(self, repo_url: str, github_token: str, pr_number: int, 
                          title: str = None, body: str = None, state: str = None) -> Dict[str, Any]:
        """
        Update an existing pull request
        
        Args:
            repo_url: Repository URL
            github_token: GitHub access token
            pr_number: PR number to update
            title: New title (optional)
            body: New body (optional)
            state: New state - 'open' or 'closed' (optional)
        
        Returns:
            Dict with update result
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            
            # Prepare update data
            update_data = {}
            if title is not None:
                update_data['title'] = title
            if body is not None:
                update_data['body'] = body
            if state is not None:
                update_data['state'] = state
            
            if not update_data:
                return {'success': True, 'message': 'No updates provided'}
            
            # Make API request
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.api_base}/repos/{owner}/{repo}/pulls/{pr_number}"
            
            logger.info(f"Updating PR #{pr_number} in {owner}/{repo}")
            
            response = requests.patch(url, json=update_data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                pr_info = response.json()
                logger.info(f"PR updated successfully: {pr_info['html_url']}")
                
                return {
                    'success': True,
                    'pr_url': pr_info['html_url'],
                    'pr_number': pr_info['number']
                }
            else:
                error_msg = f"Failed to update PR: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Error updating PR: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def convert_draft_to_ready(self, repo_url: str, github_token: str, pr_number: int) -> Dict[str, Any]:
        """
        Convert a draft PR to ready for review
        
        Args:
            repo_url: Repository URL
            github_token: GitHub access token
            pr_number: PR number to convert
        
        Returns:
            Dict with conversion result
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            
            # Use GraphQL API for draft conversion (REST API doesn't support this)
            graphql_url = "https://api.github.com/graphql"
            
            # First, get the PR node ID
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            pr_url = f"{self.api_base}/repos/{owner}/{repo}/pulls/{pr_number}"
            pr_response = requests.get(pr_url, headers=headers, timeout=30)
            
            if pr_response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Failed to get PR info: {pr_response.status_code}"
                }
            
            pr_data = pr_response.json()
            node_id = pr_data['node_id']
            
            # Convert draft to ready using GraphQL
            mutation = """
            mutation($pullRequestId: ID!) {
              markPullRequestReadyForReview(input: {pullRequestId: $pullRequestId}) {
                pullRequest {
                  id
                  isDraft
                }
              }
            }
            """
            
            graphql_headers = {
                'Authorization': f'token {github_token}',
                'Content-Type': 'application/json'
            }
            
            graphql_data = {
                'query': mutation,
                'variables': {'pullRequestId': node_id}
            }
            
            logger.info(f"Converting draft PR #{pr_number} to ready for review")
            
            response = requests.post(graphql_url, json=graphql_data, headers=graphql_headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'errors' not in result:
                    logger.info(f"PR #{pr_number} converted to ready for review")
                    return {
                        'success': True,
                        'pr_number': pr_number,
                        'message': 'PR converted to ready for review'
                    }
                else:
                    error_msg = f"GraphQL errors: {result['errors']}"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg
                    }
            else:
                error_msg = f"Failed to convert draft PR: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"Error converting draft PR: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def merge_pull_request(self, repo_url: str, github_token: str, pr_number: int, 
                          merge_method: str = "squash", commit_title: str = None, 
                          commit_message: str = None) -> Dict[str, Any]:
        """
        Merge a pull request on GitHub
        
        Args:
            repo_url: Repository URL
            github_token: GitHub access token
            pr_number: PR number to merge
            merge_method: Merge method - 'merge', 'squash', or 'rebase' (default: squash)
            commit_title: Custom commit title (optional)
            commit_message: Custom commit message (optional)
        
        Returns:
            Dict with merge result
        """
        logger.info(f"🔧 GITHUB SERVICE - merge_pull_request called")
        logger.info(f"   - Repo URL: {repo_url}")
        logger.info(f"   - PR Number: {pr_number}")
        logger.info(f"   - Merge Method: {merge_method}")
        logger.info(f"   - Token: {github_token[:10]}... (length: {len(github_token)})")
        
        try:
            logger.info(f"🔍 Parsing repository URL...")
            owner, repo = self._parse_repo_url(repo_url)
            logger.info(f"   - Owner: {owner}")
            logger.info(f"   - Repo: {repo}")
            
            # Prepare merge data
            merge_data = {
                "merge_method": merge_method
            }
            
            if commit_title:
                merge_data["commit_title"] = commit_title
            if commit_message:
                merge_data["commit_message"] = commit_message
            
            logger.info(f"📦 Prepared merge data: {merge_data}")
            
            # Make API request
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/merge"
            logger.info(f"🌐 GitHub API URL: {url}")
            logger.info(f"📋 Request headers: {dict(headers)}")
            
            logger.info(f"🚀 Making PUT request to GitHub API...")
            response = requests.put(url, json=merge_data, headers=headers, timeout=30)
            
            logger.info(f"📨 GitHub API Response:")
            logger.info(f"   - Status Code: {response.status_code}")
            logger.info(f"   - Response Headers: {dict(response.headers)}")
            logger.info(f"   - Response Text: {response.text[:500]}...")
            
            if response.status_code == 200:
                merge_info = response.json()
                logger.info(f"PR #{pr_number} merged successfully: {merge_info.get('sha', 'unknown sha')}")
                
                return {
                    'success': True,
                    'merged': True,
                    'sha': merge_info.get('sha'),
                    'message': merge_info.get('message', 'Pull request merged successfully'),
                    'pr_number': pr_number
                }
            elif response.status_code == 405:
                # PR cannot be merged (conflicts, checks failing, etc.)
                error_data = response.json()
                error_msg = error_data.get('message', 'Pull request cannot be merged')
                logger.warning(f"PR #{pr_number} cannot be merged: {error_msg}")
                
                return {
                    'success': False,
                    'merged': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                    'pr_number': pr_number
                }
            elif response.status_code == 409:
                # PR already merged or closed
                error_data = response.json()
                error_msg = error_data.get('message', 'Pull request is already merged or closed')
                logger.info(f"PR #{pr_number} already merged or closed: {error_msg}")
                
                return {
                    'success': False,
                    'merged': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                    'pr_number': pr_number
                }
            else:
                error_msg = f"Failed to merge PR: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    'success': False,
                    'merged': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                    'pr_number': pr_number
                }
                
        except Exception as e:
            error_msg = f"Error merging PR: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'merged': False,
                'error': error_msg,
                'pr_number': pr_number
            }


# Singleton instance
_github_pr_service = None

def get_github_pr_service() -> GitHubPRService:
    """Get the singleton GitHub PR service instance"""
    global _github_pr_service
    if _github_pr_service is None:
        _github_pr_service = GitHubPRService()
    return _github_pr_service