"""
GitHub Webhook Management Service
Handles registration and management of GitHub webhooks for task status updates
"""

import logging
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitHubWebhookService:
    """Service for managing GitHub webhooks for task status updates"""
    
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
    
    def create_webhook(self, repo_url: str, github_token: str, webhook_url: str, 
                      secret: str = None) -> Dict[str, Any]:
        """
        Create a webhook on GitHub repository for PR events
        
        Args:
            repo_url: Repository URL
            github_token: GitHub access token
            webhook_url: URL to receive webhook events
            secret: Optional webhook secret for verification
        
        Returns:
            Dict with webhook creation result
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            
            # Prepare webhook data
            webhook_data = {
                "name": "web",
                "active": True,
                "events": [
                    "pull_request",
                    "pull_request_review",
                    "push"
                ],
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "insecure_ssl": "0"
                }
            }
            
            if secret:
                webhook_data["config"]["secret"] = secret
            
            # Make API request
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.api_base}/repos/{owner}/{repo}/hooks"
            
            logger.info(f"Creating GitHub webhook for {owner}/{repo}")
            
            response = requests.post(url, json=webhook_data, headers=headers, timeout=30)
            
            if response.status_code == 201:
                webhook_info = response.json()
                logger.info(f"GitHub webhook created successfully: {webhook_info['id']}")
                
                return {
                    'success': True,
                    'webhook_id': webhook_info['id'],
                    'webhook_url': webhook_info['config']['url'],
                    'events': webhook_info['events'],
                    'active': webhook_info['active']
                }
            else:
                error_msg = f"Failed to create webhook: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Error creating GitHub webhook: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def list_webhooks(self, repo_url: str, github_token: str) -> Dict[str, Any]:
        """
        List existing webhooks for a repository
        
        Args:
            repo_url: Repository URL
            github_token: GitHub access token
        
        Returns:
            Dict with webhook list result
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            url = f"{self.api_base}/repos/{owner}/{repo}/hooks"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                webhooks = response.json()
                logger.info(f"Retrieved {len(webhooks)} webhooks for {owner}/{repo}")
                
                return {
                    'success': True,
                    'webhooks': [
                        {
                            'id': hook['id'],
                            'url': hook['config'].get('url'),
                            'events': hook['events'],
                            'active': hook['active'],
                            'created_at': hook['created_at'],
                            'updated_at': hook['updated_at']
                        }
                        for hook in webhooks
                    ]
                }
            else:
                error_msg = f"Failed to list webhooks: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Error listing GitHub webhooks: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def delete_webhook(self, repo_url: str, github_token: str, webhook_id: int) -> Dict[str, Any]:
        """
        Delete a webhook from a repository
        
        Args:
            repo_url: Repository URL
            github_token: GitHub access token
            webhook_id: ID of webhook to delete
        
        Returns:
            Dict with deletion result
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            url = f"{self.api_base}/repos/{owner}/{repo}/hooks/{webhook_id}"
            
            logger.info(f"Deleting GitHub webhook {webhook_id} for {owner}/{repo}")
            
            response = requests.delete(url, headers=headers, timeout=30)
            
            if response.status_code == 204:
                logger.info(f"GitHub webhook {webhook_id} deleted successfully")
                
                return {
                    'success': True,
                    'message': f'Webhook {webhook_id} deleted successfully'
                }
            else:
                error_msg = f"Failed to delete webhook: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Error deleting GitHub webhook: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def update_webhook(self, repo_url: str, github_token: str, webhook_id: int, 
                      webhook_url: str = None, events: list = None, 
                      active: bool = None, secret: str = None) -> Dict[str, Any]:
        """
        Update an existing webhook
        
        Args:
            repo_url: Repository URL
            github_token: GitHub access token
            webhook_id: ID of webhook to update
            webhook_url: New webhook URL (optional)
            events: New list of events (optional)
            active: New active status (optional)
            secret: New webhook secret (optional)
        
        Returns:
            Dict with update result
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            
            # Prepare update data
            update_data = {}
            
            if webhook_url is not None or secret is not None:
                config = {}
                if webhook_url is not None:
                    config['url'] = webhook_url
                    config['content_type'] = 'json'
                    config['insecure_ssl'] = '0'
                if secret is not None:
                    config['secret'] = secret
                update_data['config'] = config
            
            if events is not None:
                update_data['events'] = events
            
            if active is not None:
                update_data['active'] = active
            
            if not update_data:
                return {'success': True, 'message': 'No updates provided'}
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.api_base}/repos/{owner}/{repo}/hooks/{webhook_id}"
            
            logger.info(f"Updating GitHub webhook {webhook_id} for {owner}/{repo}")
            
            response = requests.patch(url, json=update_data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                webhook_info = response.json()
                logger.info(f"GitHub webhook {webhook_id} updated successfully")
                
                return {
                    'success': True,
                    'webhook_id': webhook_info['id'],
                    'webhook_url': webhook_info['config']['url'],
                    'events': webhook_info['events'],
                    'active': webhook_info['active']
                }
            else:
                error_msg = f"Failed to update webhook: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Error updating GitHub webhook: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def test_webhook(self, repo_url: str, github_token: str, webhook_id: int) -> Dict[str, Any]:
        """
        Test a webhook by triggering a ping event
        
        Args:
            repo_url: Repository URL
            github_token: GitHub access token
            webhook_id: ID of webhook to test
        
        Returns:
            Dict with test result
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            url = f"{self.api_base}/repos/{owner}/{repo}/hooks/{webhook_id}/pings"
            
            logger.info(f"Testing GitHub webhook {webhook_id} for {owner}/{repo}")
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code == 204:
                logger.info(f"GitHub webhook {webhook_id} test ping sent successfully")
                
                return {
                    'success': True,
                    'message': f'Test ping sent to webhook {webhook_id}'
                }
            else:
                error_msg = f"Failed to test webhook: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Error testing GitHub webhook: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }


# Singleton instance
_github_webhook_service = None

def get_github_webhook_service() -> GitHubWebhookService:
    """Get the singleton GitHub webhook service instance"""
    global _github_webhook_service
    if _github_webhook_service is None:
        _github_webhook_service = GitHubWebhookService()
    return _github_webhook_service