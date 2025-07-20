"""
Figma integration adapter for design webhook processing and event translation.
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


def create_figma_file_event(
    file_key: str,
    event_type: str,
    file_data: Dict[str, Any],
    triggered_by: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Event:
    """Create a Figma file event."""
    return create_event(
        EventType.USER_ACTION,
        source="figma",
        correlation_id=correlation_id,
        user_id=triggered_by.get('handle') if triggered_by else None,
        figma_event_type="file",
        file_key=file_key,
        event_type=event_type,
        file_name=file_data.get('name'),
        file_url=f"https://www.figma.com/file/{file_key}",
        thumbnail_url=file_data.get('thumbnail_url'),
        last_modified=file_data.get('last_modified'),
        version=file_data.get('version'),
        triggered_by={
            'id': triggered_by.get('id'),
            'handle': triggered_by.get('handle'),
            'img_url': triggered_by.get('img_url')
        } if triggered_by else None
    )


def create_figma_comment_event(
    file_key: str,
    comment_id: str,
    comment_data: Dict[str, Any],
    file_data: Dict[str, Any],
    triggered_by: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Event:
    """Create a Figma comment event."""
    return create_event(
        EventType.USER_ACTION,
        source="figma",
        correlation_id=correlation_id,
        user_id=triggered_by.get('handle') if triggered_by else None,
        figma_event_type="comment",
        file_key=file_key,
        comment_id=comment_id,
        file_name=file_data.get('name'),
        file_url=f"https://www.figma.com/file/{file_key}",
        comment_text=comment_data.get('text'),
        comment_url=f"https://www.figma.com/file/{file_key}?node-id={comment_data.get('client_meta', {}).get('node_id', '')}",
        created_at=comment_data.get('created_at'),
        resolved_at=comment_data.get('resolved_at'),
        triggered_by={
            'id': triggered_by.get('id'),
            'handle': triggered_by.get('handle'),
            'img_url': triggered_by.get('img_url')
        } if triggered_by else None
    )


class FigmaAdapter:
    """Adapter for Figma webhook integration."""
    
    def __init__(self):
        self.access_token = None
        self.team_id = None
    
    def configure(self, access_token: Optional[str] = None, team_id: Optional[str] = None):
        """Configure the Figma adapter."""
        self.access_token = access_token
        self.team_id = team_id
        logger.info("Figma adapter configured")
    
    def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[Event]:
        """Process Figma webhook payload and return appropriate event."""
        try:
            logger.info("Processing Figma webhook")
            
            # Figma webhook structure
            event_type = payload.get('event_type')
            file_key = payload.get('file_key')
            triggered_by = payload.get('triggered_by', {})
            
            if not event_type or not file_key:
                logger.warning("Invalid Figma webhook payload")
                return None
            
            # Handle different event types
            if event_type in ['FILE_UPDATE', 'FILE_VERSION_UPDATE']:
                return self._handle_file_event(payload)
            elif event_type == 'FILE_COMMENT':
                return self._handle_comment_event(payload)
            elif event_type == 'LIBRARY_PUBLISH':
                return self._handle_library_event(payload)
            else:
                logger.info(f"Unhandled Figma event type: {event_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing Figma webhook: {e}")
            return None
    
    def _handle_file_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle Figma file events."""
        event_type = payload.get('event_type')
        file_key = payload.get('file_key')
        triggered_by = payload.get('triggered_by', {})
        
        # Get file information (this would typically come from the webhook payload)
        file_data = {
            'name': payload.get('file_name', 'Unknown File'),
            'thumbnail_url': payload.get('thumbnail_url'),
            'last_modified': payload.get('timestamp'),
            'version': payload.get('version_id')
        }
        
        # Map Figma event types to our event types
        event_mapping = {
            'FILE_UPDATE': 'updated',
            'FILE_VERSION_UPDATE': 'version_updated'
        }
        
        mapped_event = event_mapping.get(event_type, 'updated')
        
        return create_figma_file_event(
            file_key=file_key,
            event_type=mapped_event,
            file_data=file_data,
            triggered_by=triggered_by
        )
    
    def _handle_comment_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle Figma comment events."""
        file_key = payload.get('file_key')
        comment_id = payload.get('comment_id')
        triggered_by = payload.get('triggered_by', {})
        
        comment_data = {
            'text': payload.get('comment', {}).get('message', ''),
            'created_at': payload.get('timestamp'),
            'resolved_at': payload.get('comment', {}).get('resolved_at'),
            'client_meta': payload.get('comment', {}).get('client_meta', {})
        }
        
        file_data = {
            'name': payload.get('file_name', 'Unknown File')
        }
        
        return create_figma_comment_event(
            file_key=file_key,
            comment_id=comment_id,
            comment_data=comment_data,
            file_data=file_data,
            triggered_by=triggered_by
        )
    
    def _handle_library_event(self, payload: Dict[str, Any]) -> Optional[Event]:
        """Handle Figma library publish events."""
        # Treat library publish as a special file event
        file_key = payload.get('file_key')
        triggered_by = payload.get('triggered_by', {})
        
        file_data = {
            'name': payload.get('file_name', 'Unknown Library'),
            'last_modified': payload.get('timestamp'),
            'version': payload.get('version_id')
        }
        
        return create_figma_file_event(
            file_key=file_key,
            event_type='library_published',
            file_data=file_data,
            triggered_by=triggered_by
        )
    
    def get_file_info(self, file_key: str) -> Dict[str, Any]:
        """Get file information from Figma API."""
        if not self.access_token:
            return {'status': 'error', 'message': 'Figma access token not configured'}
        
        try:
            import requests
            
            url = f"https://api.figma.com/v1/files/{file_key}"
            headers = {
                'X-Figma-Token': self.access_token
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'success',
                    'file': data
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Figma API error: HTTP {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error getting Figma file info: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_outbound_webhook_config(
        self,
        name: str,
        url: str,
        events: Optional[list] = None
    ) -> WebhookConfig:
        """Get webhook configuration for sending events to Figma (if supported)."""
        # Note: Figma doesn't typically receive webhooks, but this could be used
        # for integration with Figma plugins or other services
        if events is None:
            events = [
                'project.created',
                'project.updated',
                'github.pull_request.opened',
                'build.completed'
            ]
        
        return WebhookConfig(
            name=name,
            url=url,
            events=events,
            headers={
                'User-Agent': 'SoftwareFactory-Figma-Integration/1.0',
                'Content-Type': 'application/json'
            },
            timeout=30,
            max_retries=3,
            retry_delay=60
        )
    
    def format_outbound_payload(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for outbound Figma webhooks."""
        return {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'software-factory',
            'data': payload
        }
    
    def create_comment(self, file_key: str, message: str, node_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a comment in a Figma file."""
        if not self.access_token:
            return {'status': 'error', 'message': 'Figma access token not configured'}
        
        try:
            import requests
            
            url = f"https://api.figma.com/v1/files/{file_key}/comments"
            headers = {
                'X-Figma-Token': self.access_token,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'message': message
            }
            
            if node_id:
                payload['client_meta'] = {
                    'node_id': node_id
                }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'success',
                    'comment': data
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Figma API error: HTTP {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error creating Figma comment: {e}")
            return {'status': 'error', 'message': str(e)}