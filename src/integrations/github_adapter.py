"""
GitHub integration adapter for webhook processing and event translation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from ..core.events import Event, EventType, create_event
    from ..services.webhook_service import WebhookConfig
except ImportError:
    from core.events import Event, EventType, create_event
    from services.webhook_service import WebhookConfig


logger = logging.getLogger(__name__)


def create_github_repository_event(
    repository_id: str,
    action: str,
    repository_data: Dict[str, Any],
    sender: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Event:
    """Create a GitHub repository event."""
    return create_event(
        EventType.USER_ACTION,
        source="github",
        correlation_id=correlation_id,
        user_id=sender.get('login') if sender else None,
        github_event_type="repository",
        action=action,
        repository={
            'id': repository_data.get('id'),
            'name': repository_data.get('name'),
            'full_name': repository_data.get('full_name'),
            'html_url': repository_data.get('html_url'),
            'clone_url': repository_data.get('clone_url'),
            'default_branch': repository_data.get('default_branch'),
            'language': repository_data.get('language'),
            'description': repository_data.get('description')
        },
        sender={
            'login': sender.get('login'),
            'id': sender.get('id'),
            'type': sender.get('type')
        }
    )


def create_github_pull_request_event(
    pull_request_id: str,
    action: str,
    pull_request_data: Dict[str, Any],
    repository_data: Dict[str, Any],
    sender: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Event:
    """Create a GitHub pull request event."""
    return create_event(
        EventType.USER_ACTION,
        source="github",
        correlation_id=correlation_id,
        user_id=sender.get('login') if sender else None,
        github_event_type="pull_request",
        action=action,
        pull_request={
            'id': pull_request_data.get('id'),
            'number': pull_request_data.get('number'),
            'title': pull_request_data.get('title'),
            'body': pull_request_data.get('body'),
            'state': pull_request_data.get('state'),
            'html_url': pull_request_data.get('html_url'),
            'head': {
                'ref': pull_request_data.get('head', {}).get('ref'),
                'sha': pull_request_data.get('head', {}).get('sha')
            },
            'base': {
                'ref': pull_request_data.get('base', {}).get('ref'),
                'sha': pull_request_data.get('base', {}).get('sha')
            },
            'user': {
                'login': pull_request_data.get('user', {}).get('login'),
                'id': pull_request_data.get('user', {}).get('id')
            }
        },
        repository={
            'id': repository_data.get('id'),
            'name': repository_data.get('name'),
            'full_name': repository_data.get('full_name')
        },
        sender={
            'login': sender.get('login'),
            'id': sender.get('id')
        }
    )


def create_github_push_event(
    repository_id: str,
    ref: str,
    commits: list,
    repository_data: Dict[str, Any],
    pusher: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Event:
    """Create a GitHub push event."""
    return create_event(
        EventType.USER_ACTION,
        source="github",
        correlation_id=correlation_id,
        user_id=pusher.get('name') if pusher else None,
        github_event_type="push",
        ref=ref,
        commits=[
            {
                'id': commit.get('id'),
                'message': commit.get('message'),
                'author': commit.get('author'),
                'url': commit.get('url'),
                'added': commit.get('added', []),
                'removed': commit.get('removed', []),
                'modified': commit.get('modified', [])
            }
            for commit in commits
        ],
        repository={
            'id': repository_data.get('id'),
            'name': repository_data.get('name'),
            'full_name': repository_data.get('full_name')
        },
        pusher={
            'name': pusher.get('name'),
            'email': pusher.get('email')
        }
    )


class GitHubAdapter:
    """Adapter for GitHub webhook integration."""
    
    def __init__(self):
        self.webhook_secret = None
    
    def configure(self, webhook_secret: Optional[str] = None):
        """Configure the GitHub adapter."""
        self.webhook_secret = webhook_secret
        logger.info("GitHub adapter configured")
    
    def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[Event]:
        """Process GitHub webhook payload and return appropriate event."""
        try:
            # Get the GitHub event type from headers
            github_event = headers.get('X-GitHub-Event', headers.get('x-github-event'))
            if not github_event:
                logger.warning("No GitHub event type found in headers")
                return None
            
            logger.info(f"Processing GitHub webhook: {github_event}")
            
            # Route to appropriate handler
            if github_event == 'repository':
                return self._handle_repository_event(payload)
            elif github_event == 'pull_request':
                return self._handle_pull_request_event(payload)
            elif github_event == 'push':
                return self._handle_push_event(payload)
            elif github_event == 'ping':
                return self._handle_ping_event(payload)
            else:
                logger.info(f"Unhandled GitHub event type: {github_event}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing GitHub webhook: {e}")
            return None
    
    def _handle_repository_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle GitHub repository events."""
        action = payload.get('action')
        repository = payload.get('repository', {})
        sender = payload.get('sender', {})
        
        if not action or not repository:
            logger.warning("Invalid repository event payload")
            return None
        
        return create_github_repository_event(
            repository_id=str(repository.get('id')),
            action=action,
            repository_data=repository,
            sender=sender
        )
    
    def _handle_pull_request_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle GitHub pull request events."""
        action = payload.get('action')
        pull_request = payload.get('pull_request', {})
        repository = payload.get('repository', {})
        sender = payload.get('sender', {})
        
        if not action or not pull_request:
            logger.warning("Invalid pull request event payload")
            return None
        
        return create_github_pull_request_event(
            pull_request_id=str(pull_request.get('id')),
            action=action,
            pull_request_data=pull_request,
            repository_data=repository,
            sender=sender
        )
    
    def _handle_push_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle GitHub push events."""
        ref = payload.get('ref')
        commits = payload.get('commits', [])
        repository = payload.get('repository', {})
        pusher = payload.get('pusher', {})
        
        if not ref or not repository:
            logger.warning("Invalid push event payload")
            return None
        
        return create_github_push_event(
            repository_id=str(repository.get('id')),
            ref=ref,
            commits=commits,
            repository_data=repository,
            pusher=pusher
        )
    
    def _handle_ping_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle GitHub ping events (webhook verification)."""
        logger.info("Received GitHub ping event - webhook is configured correctly")
        return None
    
    def get_outbound_webhook_config(
        self,
        name: str,
        url: str,
        secret: Optional[str] = None,
        events: Optional[list] = None
    ) -> WebhookConfig:
        """Get webhook configuration for sending events to GitHub."""
        if events is None:
            events = [
                'project.created',
                'project.updated',
                'build.completed',
                'build.failed'
            ]
        
        return WebhookConfig(
            name=name,
            url=url,
            secret=secret,
            events=events,
            headers={
                'User-Agent': 'SoftwareFactory-GitHub-Integration/1.0'
            },
            timeout=30,
            max_retries=3,
            retry_delay=60
        )
    
    def format_outbound_payload(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for outbound GitHub webhooks."""
        return {
            'action': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'software-factory',
            'data': payload
        }