#!/usr/bin/env python3
"""
Integration test for the Define Agent - runs within the Flask app structure
"""

import logging
import uuid
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_define_agent_integration():
    """Test the Define Agent functionality within Flask app context"""
    try:
        logger.info("Starting Define Agent integration test")
        
        # Import modules (these should work within the src directory structure)
        from events.event_router import EventBus
        from events.domain_events import IdeaPromotedEvent
        from agents.define_agent import create_define_agent
        from services.ai_broker import get_ai_broker
        from services.vector_context_service import get_vector_context_service
        from models.base import db
        from models.specification_artifact import SpecificationArtifact
        
        logger.info("All modules imported successfully")
        
        # Initialize services
        logger.info("Initializing services...")
        
        # Get AI broker (should already be initialized by app)
        ai_broker = get_ai_broker()
        if not ai_broker:
            logger.error("AI broker not available")
            return False
        
        # Get vector context service
        vector_service = get_vector_context_service()
        if not vector_service:
            logger.warning("Vector context service not available - continuing without it")
        
        # Create event bus
        event_bus = EventBus()
        
        # Create Define Agent
        logger.info("Creating Define Agent...")
        define_agent = create_define_agent(event_bus, ai_broker)
        
        # Start the agent
        logger.info("Starting Define Agent...")
        define_agent.start()
        
        # Create a test idea.promoted event
        logger.info("Creating test idea.promoted event...")
        test_event = IdeaPromotedEvent(
            idea_id="test_idea_integration_123",
            project_id="1",
            promoted_by="integration_test_user",
            correlation_id=f"test_correlation_{uuid.uuid4().hex[:8]}"
        )
        
        # Add test content to the event
        test_event.idea_content = """
        We need to implement a real-time notification system for our application.
        Users should receive notifications for:
        - New messages and comments
        - System alerts and updates
        - Task assignments and completions
        - Security events and login attempts
        
        The system should support:
        - Push notifications for mobile devices
        - Email notifications with customizable frequency
        - In-app notification center with read/unread status
        - Notification preferences and filtering
        - Real-time WebSocket updates
        """
        
        logger.info("Processing test event...")
        result = define_agent.process_event(test_event)
        
        logger.info(f"Processing completed. Success: {result.success}")
        
        if result.success:
            logger.info("✅ Define Agent successfully processed the idea.promoted event")
            logger.info(f"Processing time: {result.processing_time_seconds:.2f} seconds")
            logger.info(f"Generated events: {len(result.generated_events)}")
            
            if result.generated_events:
                spec_frozen_event = result.generated_events[0]
                logger.info(f"Generated spec.frozen event: {spec_frozen_event.aggregate_id}")
                logger.info(f"Requirements length: {len(spec_frozen_event.requirements_md)} characters")
                logger.info(f"Design length: {len(spec_frozen_event.design_md)} characters")
                logger.info(f"Tasks length: {len(spec_frozen_event.tasks_md)} characters")
                
                # Check if specifications were stored in database
                try:
                    spec_id = spec_frozen_event.aggregate_id
                    artifacts = SpecificationArtifact.get_spec_artifacts(spec_id)
                    logger.info(f"Database artifacts created: {len(artifacts)}")
                    
                    for artifact in artifacts:
                        logger.info(f"- {artifact.artifact_type.value}: {artifact.status.value}")
                        
                except Exception as e:
                    logger.warning(f"Could not check database artifacts: {e}")
            
            # Test result data
            if result.result_data:
                logger.info("Result data:")
                for key, value in result.result_data.items():
                    logger.info(f"  {key}: {value}")
        else:
            logger.error(f"❌ Define Agent failed to process event: {result.error_message}")
        
        # Stop the agent
        logger.info("Stopping Define Agent...")
        define_agent.stop()
        
        logger.info("Define Agent integration test completed")
        return result.success
        
    except Exception as e:
        logger.error(f"Integration test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # This should be run from within the Flask app context
    from app import create_app
    
    app = create_app()
    with app.app_context():
        success = test_define_agent_integration()
        print(f"\nIntegration test {'PASSED' if success else 'FAILED'}")