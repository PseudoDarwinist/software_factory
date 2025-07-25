#!/usr/bin/env python3
"""
Mock test for Define Agent that runs from within src directory
"""

import logging
from unittest.mock import Mock

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_define_agent_mock():
    """Test Define Agent with mocked AI responses"""
    try:
        logger.info("Starting Define Agent mock test from src directory")
        
        # Import Flask app first
        from app import create_app
        app = create_app()
        
        with app.app_context():
            logger.info("Testing Define Agent with mocked AI...")
            
            # Import modules (should work from src directory)
            import events.event_router as event_router_module
            import events.domain_events as domain_events_module
            import agents.define_agent as define_agent_module
            
            logger.info("✅ All modules imported successfully")
            
            # Create mocked AI broker
            mock_ai_broker = Mock()
            mock_response = Mock()
            mock_response.success = True
            mock_response.content = """# Requirements Document

## Introduction
This document outlines the requirements for a user authentication system.

## Requirements

### Requirement 1
**User Story:** As a user, I want to register an account, so that I can access the application.

#### Acceptance Criteria
1. WHEN a user provides valid registration information THEN the system SHALL create a new user account
2. WHEN a user provides invalid information THEN the system SHALL display appropriate error messages
"""
            mock_response.model_used = "claude-sonnet-3.5"
            mock_response.processing_time = 2.5
            mock_response.tokens_used = 150
            mock_response.cost_estimate = 0.01
            
            # Mock the submit_request_sync method to return our mock response
            mock_ai_broker.submit_request_sync.return_value = mock_response
            
            logger.info("Creating event bus...")
            event_bus = event_router_module.EventBus()
            
            logger.info("Creating Define Agent with mocked AI...")
            define_agent = define_agent_module.create_define_agent(event_bus, mock_ai_broker)
            
            logger.info("Testing agent configuration...")
            assert define_agent.config.agent_id == "define_agent"
            assert "idea.promoted" in define_agent.config.event_types
            logger.info("✅ Agent configuration correct")
            
            logger.info("Starting Define Agent...")
            define_agent.start()
            
            # Create test event
            logger.info("Creating test event...")
            test_event = domain_events_module.IdeaPromotedEvent(
                idea_id="mock_test_idea_123",
                project_id="1",
                promoted_by="mock_test_user",
                correlation_id="mock_test_correlation_123"
            )
            
            test_event.idea_content = "Add user authentication system with login, logout, and password reset."
            
            logger.info("Processing test event...")
            result = define_agent.process_event(test_event)
            
            logger.info(f"Processing result: Success={result.success}")
            
            if result.success:
                logger.info("✅ Define Agent successfully processed the event")
                logger.info(f"Processing time: {result.processing_time_seconds:.2f}s")
                logger.info(f"Generated events: {len(result.generated_events)}")
                
                # Verify AI broker was called
                assert mock_ai_broker.submit_request_sync.called
                call_count = mock_ai_broker.submit_request_sync.call_count
                logger.info(f"✅ AI broker was called {call_count} times (should be 3 for requirements, design, tasks)")
                
                # Check generated events
                if result.generated_events:
                    spec_frozen_event = result.generated_events[0]
                    logger.info(f"Generated spec.frozen event: {spec_frozen_event.aggregate_id}")
                    
                    # Verify event has required fields
                    assert hasattr(spec_frozen_event, 'requirements_md')
                    assert hasattr(spec_frozen_event, 'design_md')
                    assert hasattr(spec_frozen_event, 'tasks_md')
                    logger.info("✅ Generated event has all required fields")
                    
                    # Verify content is not empty
                    assert len(spec_frozen_event.requirements_md) > 0
                    assert len(spec_frozen_event.design_md) > 0
                    assert len(spec_frozen_event.tasks_md) > 0
                    logger.info("✅ Generated content is not empty")
                    
                    # Verify metadata
                    assert hasattr(spec_frozen_event, 'ai_generated')
                    assert hasattr(spec_frozen_event, 'human_reviewed')
                    assert spec_frozen_event.ai_generated == True
                    assert spec_frozen_event.human_reviewed == False
                    logger.info("✅ AI generation metadata correct")
                
                # Check result data
                if result.result_data:
                    assert 'spec_id' in result.result_data
                    assert 'ai_generated' in result.result_data
                    assert result.result_data['ai_generated'] == True
                    logger.info("✅ Result data contains expected fields")
                
            else:
                logger.error(f"❌ Define Agent failed: {result.error_message}")
                return False
            
            logger.info("Stopping Define Agent...")
            define_agent.stop()
            
            logger.info("✅ Define Agent mock test completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Mock test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_define_agent_mock()
    print(f"\n{'🎉 MOCK TEST PASSED' if success else '❌ MOCK TEST FAILED'}")
    exit(0 if success else 1)