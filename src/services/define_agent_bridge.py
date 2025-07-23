"""
Define Agent Bridge - Integrates DefineAgent with the current AI agent system
"""

import logging
from typing import Optional, Dict, Any

try:
    from ..agents.define_agent import create_define_agent
    from ..services.ai_broker import get_ai_broker
    from ..services.ai_agents import BaseAIAgent, AgentType, AgentAlert
    from ..events.event_router import EventBus
    from ..events.event_store import EventStore
    from ..events.domain_events import IdeaPromotedEvent
    from ..models.feed_item import FeedItem
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from agents.define_agent import create_define_agent
    from services.ai_broker import get_ai_broker
    from services.ai_agents import BaseAIAgent, AgentType, AgentAlert
    from events.event_router import EventBus
    from events.event_store import EventStore
    from events.domain_events import IdeaPromotedEvent
    from models.feed_item import FeedItem

logger = logging.getLogger(__name__)

class DefineAgentBridge(BaseAIAgent):
    """Bridge to integrate DefineAgent with the current AI agent system"""
    
    def __init__(self):
        super().__init__(AgentType.DEFINE_AGENT)
        self.define_agent = None
        self.event_bus = None
        self.initialize()
        
    def _subscribe_to_events(self):
        """Subscribe to relevant events"""
        # This is called by BaseAIAgent.start()
        pass
    
    def analyze(self, event_data: Dict[str, Any]) -> Optional[AgentAlert]:
        """Analyze events and return alerts if needed"""
        # This is required by BaseAIAgent
        return None  # DefineAgent doesn't generate alerts, it generates specifications
    
    def initialize(self):
        """Initialize the DefineAgent"""
        try:
            # Get AI broker
            ai_broker = get_ai_broker()
            if not ai_broker:
                logger.warning("AI broker not available, DefineAgent will have limited functionality")
            
            # Create event bus (simplified for this bridge)
            event_store = EventStore()
            self.event_bus = EventBus(event_store)
            
            # Create DefineAgent
            self.define_agent = create_define_agent(self.event_bus, ai_broker)
            
            # Subscribe to idea.promoted events
            self.event_bus.subscribe("idea.promoted", self._handle_idea_promoted)
            
            self.is_active = True
            logger.info("DefineAgent bridge initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize DefineAgent bridge: {e}")
            self.is_active = False
    
    def _handle_idea_promoted(self, event_data):
        """Handle idea.promoted events"""
        try:
            if not self.define_agent:
                logger.warning("DefineAgent not available")
                return
            
            # Convert event data to IdeaPromotedEvent if needed
            if isinstance(event_data, dict):
                event = IdeaPromotedEvent(
                    idea_id=event_data.get('idea_id'),
                    project_id=event_data.get('project_id'),
                    promoted_by=event_data.get('promoted_by', 'user')
                )
            else:
                event = event_data
            
            # Process the event
            result = self.define_agent.process_event(event)
            
            if result.success:
                logger.info(f"DefineAgent successfully processed idea {event.aggregate_id}")
            else:
                logger.error(f"DefineAgent failed to process idea {event.aggregate_id}: {result.error_message}")
                
        except Exception as e:
            logger.error(f"Error handling idea.promoted event: {e}")
    
    def process_idea_promotion(self, idea_id: str, project_id: str, promoted_by: str = 'user'):
        """Manually process an idea promotion"""
        try:
            if not self.define_agent:
                logger.warning("DefineAgent not available")
                return False
            
            # Ensure we're running within Flask application context
            from flask import current_app
            
            def _process_with_context():
                # Get the actual idea content from the database
                feed_item = FeedItem.query.get(idea_id)
                if not feed_item:
                    logger.error(f"Feed item {idea_id} not found")
                    return False
                
                # Create IdeaPromotedEvent with actual idea content
                event = IdeaPromotedEvent(
                    idea_id=idea_id,
                    project_id=project_id,
                    promoted_by=promoted_by
                )
                
                # Add idea content to the event for the DefineAgent to use
                event.idea_content = f"Title: {feed_item.title}\n\nDescription: {feed_item.summary or 'No description provided'}"
                
                # Process the event
                result = self.define_agent.process_event(event)
                
                if result.success:
                    logger.info(f"DefineAgent successfully processed idea {idea_id}")
                    return True
                else:
                    logger.error(f"DefineAgent failed to process idea {idea_id}: {result.error_message}")
                    return False
            
            # Try to run within current app context, or create one if needed
            try:
                # If we're already in an app context, just run
                if current_app:
                    return _process_with_context()
            except RuntimeError:
                # We're outside app context, need to create one
                pass
            
            # Create app context
            try:
                from ..app import create_app
                app = create_app()
            except ImportError:
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                from app import create_app
                app = create_app()
            
            with app.app_context():
                return _process_with_context()
                
        except Exception as e:
            logger.error(f"Error processing idea promotion: {e}")
            return False

# Global instance
_define_agent_bridge = None

def get_define_agent_bridge() -> DefineAgentBridge:
    """Get the global DefineAgent bridge instance"""
    global _define_agent_bridge
    if _define_agent_bridge is None:
        _define_agent_bridge = DefineAgentBridge()
    return _define_agent_bridge

def init_define_agent_bridge():
    """Initialize the DefineAgent bridge"""
    bridge = get_define_agent_bridge()
    logger.info(f"DefineAgent bridge initialized: {'active' if bridge.is_active else 'inactive'}")
    return bridge