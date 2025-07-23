#!/usr/bin/env python3
"""
Slack Feed Bridge - Converts Slack messages to Mission Control feed items
Listens for Slack message events and creates corresponding feed items in the Think stage
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from ..core.events import Event, EventType
    from ..models.feed_item import FeedItem
    from ..models.stage import Stage
    from ..models.mission_control_project import MissionControlProject
    from ..models.channel_mapping import ChannelMapping
    from ..models.base import db
    from .event_bus import get_event_bus
except ImportError:
    from core.events import Event, EventType
    from models.feed_item import FeedItem
    from models.stage import Stage
    from models.mission_control_project import MissionControlProject
    from models.channel_mapping import ChannelMapping
    from models.base import db
    from services.event_bus import get_event_bus


logger = logging.getLogger(__name__)


class SlackFeedBridge:
    """Bridge that converts Slack messages to Mission Control feed items"""
    
    def __init__(self):
        self.event_bus = get_event_bus()
        self.channel_project_mapping = {}  # Maps Slack channel IDs to project IDs
        self._setup_event_subscriptions()
    
    def _setup_event_subscriptions(self):
        """Subscribe to Slack message events"""
        if self.event_bus:
            # Subscribe to USER_ACTION events from Slack
            self.event_bus.subscribe(
                event_type="user.action",
                callback=self._handle_slack_event
            )
            logger.info("Slack feed bridge subscribed to user action events")
    
    def _handle_slack_event(self, event: Event) -> None:
        """Handle Slack events and convert to feed items"""
        try:
            # Check if this is a Slack message event
            if (event.source != "slack" or 
                event.data.get('slack_event_type') != 'message'):
                return
            
            # Extract message data
            channel = event.data.get('channel')
            user = event.data.get('user_id', event.user_id)
            text = event.data.get('text', '')
            timestamp = event.data.get('timestamp')
            
            if not text or not channel:
                logger.debug("Skipping Slack event - missing text or channel")
                return
            
            # Skip bot messages and system messages
            message_data = event.data.get('message_data', {})
            if (message_data.get('bot_id') or 
                message_data.get('subtype') == 'bot_message' or
                message_data.get('user') == 'USLACKBOT'):
                logger.debug("Skipping bot message")
                return
            
            # Determine project ID from channel
            project_id = self._get_project_for_channel(channel)
            
            # Skip if no project mapping found
            if not project_id:
                logger.info(f"Skipping message from unmapped channel: {channel}")
                return
            
            # Create feed item
            feed_item_id = f"slack_{channel}_{timestamp or datetime.utcnow().timestamp()}"
            
            # Create the feed item
            feed_item = FeedItem.create(
                id=feed_item_id,
                project_id=project_id,
                severity=FeedItem.SEVERITY_INFO,
                kind=FeedItem.KIND_IDEA,
                title=self._create_title_from_text(text),
                summary=text,
                actor=user or 'unknown',
                metadata={
                    'source': 'slack',
                    'channel': channel,
                    'timestamp': timestamp,
                    'original_event_id': event.event_id
                }
            )
            
            # Add to Think stage
            think_stage = Stage.get_or_create_for_project(project_id, Stage.STAGE_THINK)
            think_stage.add_item(feed_item.id)
            
            # Update project unread count
            project = MissionControlProject.query.get(project_id)
            if project:
                project.increment_unread_count()
            
            db.session.commit()
            
            logger.info(f"Created feed item from Slack message: {feed_item_id} in project {project_id}")
            
        except Exception as e:
            logger.error(f"Error handling Slack event: {e}")
            db.session.rollback()
    
    def _get_project_for_channel(self, channel_id: str) -> Optional[str]:
        """Get project ID for a Slack channel using database mappings"""
        try:
            # Import ChannelMapping here to avoid circular imports
            from ..models.channel_mapping import ChannelMapping
            
            # Check database for channel mapping
            project_id = ChannelMapping.get_project_for_channel(channel_id)
            
            if project_id:
                logger.info(f"Found mapping: channel {channel_id} -> project {project_id}")
                return project_id
            else:
                # No mapping found - ignore this message
                logger.info(f"No mapping found for channel {channel_id} - ignoring message")
                return None
                
        except Exception as e:
            logger.error(f"Error getting project for channel {channel_id}: {e}")
            return None
    
    def _create_title_from_text(self, text: str) -> str:
        """Create a title from Slack message text"""
        # Take first line or first 50 characters
        lines = text.strip().split('\n')
        first_line = lines[0].strip()
        
        if len(first_line) <= 50:
            return first_line
        
        # Truncate at word boundary
        words = first_line.split()
        title = ""
        for word in words:
            if len(title + word) <= 47:  # Leave room for "..."
                title += word + " "
            else:
                break
        
        return title.strip() + "..." if title else first_line[:47] + "..."
    
    def map_channel_to_project(self, channel_id: str, project_id: str):
        """Map a Slack channel to a specific project"""
        self.channel_project_mapping[channel_id] = project_id
        logger.info(f"Mapped Slack channel {channel_id} to project {project_id}")
    
    def get_channel_mappings(self) -> Dict[str, str]:
        """Get all channel to project mappings"""
        return self.channel_project_mapping.copy()


# Global instance
_slack_feed_bridge: Optional[SlackFeedBridge] = None


def init_slack_feed_bridge() -> SlackFeedBridge:
    """Initialize the global Slack feed bridge"""
    global _slack_feed_bridge
    _slack_feed_bridge = SlackFeedBridge()
    return _slack_feed_bridge


def get_slack_feed_bridge() -> Optional[SlackFeedBridge]:
    """Get the global Slack feed bridge instance"""
    return _slack_feed_bridge