"""
Slack integration adapter for notifications and webhook processing.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from ..core.events import Event, EventType, create_event
    from ..services.webhook_service import WebhookConfig
except ImportError:
    from core.events import Event, EventType, create_event
    from services.webhook_service import WebhookConfig


logger = logging.getLogger(__name__)


def create_slack_message_event(
    channel: str,
    user: str,
    text: str,
    timestamp: str,
    message_data: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Event:
    """Create a Slack message event."""
    return create_event(
        EventType.USER_ACTION,
        source="slack",
        correlation_id=correlation_id,
        user_id=user,
        slack_event_type="message",
        channel=channel,
        text=text,
        timestamp=timestamp,
        message_data=message_data
    )


def create_slack_command_event(
    command: str,
    text: str,
    user_id: str,
    user_name: str,
    channel_id: str,
    channel_name: str,
    team_id: str,
    correlation_id: Optional[str] = None
) -> Event:
    """Create a Slack command event."""
    return create_event(
        EventType.USER_ACTION,
        source="slack",
        correlation_id=correlation_id,
        user_id=user_name,
        slack_event_type="command",
        command=command,
        text=text,
        user_id_slack=user_id,
        user_name=user_name,
        channel_id=channel_id,
        channel_name=channel_name,
        team_id=team_id
    )


class SlackAdapter:
    """Adapter for Slack webhook integration and notifications."""
    
    def __init__(self):
        self.bot_token = None
        self.signing_secret = None
        self.webhook_url = None
    
    def configure(
        self,
        bot_token: Optional[str] = None,
        signing_secret: Optional[str] = None,
        webhook_url: Optional[str] = None
    ):
        """Configure the Slack adapter."""
        self.bot_token = bot_token
        self.signing_secret = signing_secret
        self.webhook_url = webhook_url
        logger.info("Slack adapter configured")
    
    def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[Event]:
        """Process Slack webhook payload and return appropriate event."""
        try:
            logger.info("Processing Slack webhook")
            
            # Handle URL verification challenge
            if payload.get('type') == 'url_verification':
                logger.info("Slack URL verification challenge received")
                return None  # This should be handled at the API level
            
            # Handle event callbacks
            if payload.get('type') == 'event_callback':
                return self._handle_event_callback(payload)
            
            # Handle slash commands (these come as form data, not JSON)
            if 'command' in payload:
                return self._handle_slash_command(payload)
            
            # Handle interactive components
            if payload.get('type') == 'interactive_message':
                return self._handle_interactive_message(payload)
            
            logger.info(f"Unhandled Slack webhook type: {payload.get('type')}")
            return None
            
        except Exception as e:
            logger.error(f"Error processing Slack webhook: {e}")
            return None
    
    def _handle_event_callback(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle Slack event callback."""
        event = payload.get('event', {})
        event_type = event.get('type')
        
        if event_type == 'message':
            # Ignore bot messages to avoid loops
            if event.get('bot_id') or event.get('subtype') == 'bot_message':
                return None
            
            return create_slack_message_event(
                channel=event.get('channel'),
                user=event.get('user'),
                text=event.get('text', ''),
                timestamp=event.get('ts'),
                message_data=event
            )
        
        logger.info(f"Unhandled Slack event type: {event_type}")
        return None
    
    def _handle_slash_command(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle Slack slash command."""
        return create_slack_command_event(
            command=payload.get('command'),
            text=payload.get('text', ''),
            user_id=payload.get('user_id'),
            user_name=payload.get('user_name'),
            channel_id=payload.get('channel_id'),
            channel_name=payload.get('channel_name'),
            team_id=payload.get('team_id')
        )
    
    def _handle_interactive_message(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle Slack interactive message."""
        # This would handle button clicks, menu selections, etc.
        logger.info("Received Slack interactive message")
        return None
    
    def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[list] = None,
        attachments: Optional[list] = None
    ) -> Dict[str, Any]:
        """Send a message to Slack."""
        if not self.bot_token:
            return {'status': 'error', 'message': 'Slack bot token not configured'}
        
        try:
            import requests
            
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                'Authorization': f'Bearer {self.bot_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'channel': channel,
                'text': text
            }
            
            if blocks:
                payload['blocks'] = blocks
            if attachments:
                payload['attachments'] = attachments
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            result = response.json()
            
            if result.get('ok'):
                return {
                    'status': 'success',
                    'message': 'Message sent successfully',
                    'ts': result.get('ts')
                }
            else:
                return {
                    'status': 'error',
                    'message': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def send_webhook_message(self, text: str, blocks: Optional[list] = None) -> Dict[str, Any]:
        """Send a message using incoming webhook."""
        if not self.webhook_url:
            return {'status': 'error', 'message': 'Slack webhook URL not configured'}
        
        try:
            import requests
            
            payload = {'text': text}
            if blocks:
                payload['blocks'] = blocks
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return {'status': 'success', 'message': 'Webhook message sent successfully'}
            else:
                return {
                    'status': 'error',
                    'message': f'Webhook failed: HTTP {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error sending Slack webhook message: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_outbound_webhook_config(
        self,
        name: str,
        webhook_url: str,
        events: Optional[list] = None
    ) -> WebhookConfig:
        """Get webhook configuration for sending events to Slack."""
        if events is None:
            events = [
                'project.created',
                'project.updated',
                'build.completed',
                'build.failed',
                'github.pull_request.opened',
                'github.pull_request.merged',
                'jenkins.build.completed',
                'jenkins.build.failed'
            ]
        
        return WebhookConfig(
            name=name,
            url=webhook_url,
            events=events,
            headers={
                'User-Agent': 'SoftwareFactory-Slack-Integration/1.0',
                'Content-Type': 'application/json'
            },
            timeout=30,
            max_retries=3,
            retry_delay=60
        )
    
    def format_outbound_payload(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for outbound Slack webhooks."""
        # Create a user-friendly message based on event type
        text = self._format_event_message(event_type, payload)
        
        # Create rich blocks for better formatting
        blocks = self._create_event_blocks(event_type, payload)
        
        return {
            'text': text,
            'blocks': blocks
        }
    
    def _format_event_message(self, event_type: str, payload: Dict[str, Any]) -> str:
        """Format event into a readable Slack message."""
        if event_type == 'project.created':
            project_name = payload.get('name', 'Unknown Project')
            return f"🚀 New project created: *{project_name}*"
        
        elif event_type == 'build.completed':
            job_name = payload.get('job_name', 'Unknown Job')
            return f"✅ Build completed successfully: *{job_name}*"
        
        elif event_type == 'build.failed':
            job_name = payload.get('job_name', 'Unknown Job')
            return f"❌ Build failed: *{job_name}*"
        
        elif event_type == 'github.pull_request.opened':
            pr_title = payload.get('pull_request', {}).get('title', 'Unknown PR')
            repo_name = payload.get('repository', {}).get('name', 'Unknown Repo')
            return f"🔄 New pull request opened in *{repo_name}*: {pr_title}"
        
        elif event_type == 'github.pull_request.merged':
            pr_title = payload.get('pull_request', {}).get('title', 'Unknown PR')
            repo_name = payload.get('repository', {}).get('name', 'Unknown Repo')
            return f"🎉 Pull request merged in *{repo_name}*: {pr_title}"
        
        else:
            return f"📡 Event: {event_type}"
    
    def _create_event_blocks(self, event_type: str, payload: Dict[str, Any]) -> list:
        """Create Slack blocks for rich event formatting."""
        blocks = []
        
        # Header block
        header_text = self._format_event_message(event_type, payload)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": header_text
            }
        })
        
        # Add context based on event type
        if event_type.startswith('github.'):
            repo = payload.get('repository', {})
            if repo:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Repository: <{repo.get('html_url', '#')}|{repo.get('full_name', 'Unknown')}>"
                        }
                    ]
                })
        
        elif event_type.startswith('jenkins.'):
            build_url = payload.get('build_url')
            if build_url:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Build: <{build_url}|View in Jenkins>"
                        }
                    ]
                })
        
        # Add timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        })
        
        return blocks