"""
Unit tests for DefineAgent PRD integration
Tests the enhanced AI model prompts that include PRD context during requirements.md generation
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the classes we need to test
try:
    from src.agents.define_agent import DefineAgent
    from src.agents.base import ProjectContext
    from src.events.domain_events import IdeaPromotedEvent
    from src.models.specification_artifact import SpecificationArtifact, ArtifactType
    from src.models.prd import PRD
    from src.services.ai_broker import AIBroker
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from agents.define_agent import DefineAgent
    from agents.base import ProjectContext
    from events.domain_events import IdeaPromotedEvent
    from models.specification_artifact import SpecificationArtifact, ArtifactType
    from models.prd import PRD
    from services.ai_broker import AIBroker


class TestDefineAgentPRDIntegration:
    """Test PRD context integration in DefineAgent"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_event_bus = Mock()
        self.mock_ai_broker = Mock(spec=AIBroker)
        self.define_agent = DefineAgent(self.mock_event_bus, self.mock_ai_broker)
        
        # Sample project context
        self.project_context = ProjectContext(
            project_id="test_project_123",
            repo_url="https://github.com/test/repo.git",
            system_map={"components": ["api", "database"], "dependencies": ["flask", "postgresql"]}
        )
        
        # Sample PRD context
        self.prd_context = {
            'version': 'v1',
            'status': 'frozen',
            'md_content': '# PRD Content\n\n## Business Goals\n- Increase user engagement\n- Reduce support tickets',
            'summary': {
                'goals': {'items': ['Increase user engagement', 'Reduce support tickets']},
                'audience': {'text': 'Primary: End users, Secondary: Support staff'},
                'problem': {'text': 'Users struggle with complex workflows'}
            },
            'business_goals': ['Increase user engagement', 'Reduce support tickets'],
            'user_personas': 'Primary: End users, Secondary: Support staff',
            'success_metrics': 'Users struggle with complex workflows',
            'sources': ['upload_session_123']
        }
    
    def test_get_prd_context_with_frozen_prd(self, app_context):
        """Test _get_prd_context retrieves frozen PRD successfully"""
        # Mock PRD query
        mock_prd = Mock()
        mock_prd.version = 'v1'
        mock_prd.status = 'frozen'
        mock_prd.md_uri = '# PRD Content'
        mock_prd.sources = ['upload_session_123']
        mock_prd.get_summary.return_value = {
            'goals': {'items': ['Increase user engagement']},
            'audience': {'text': 'End users'},
            'problem': {'text': 'Complex workflows'}
        }
        
        # Mock the PRD class directly since it's imported at module level
        with patch.object(PRD, 'query') as mock_query:
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = mock_prd
            
            result = self.define_agent._get_prd_context("test_project_123")
            
            assert result is not None
            assert result['version'] == 'v1'
            assert result['status'] == 'frozen'
            assert result['business_goals'] == ['Increase user engagement']
            assert result['user_personas'] == 'End users'
            assert result['success_metrics'] == 'Complex workflows'
    
    def test_get_prd_context_no_prd_found(self, app_context):
        """Test _get_prd_context returns None when no PRD exists"""
        with patch.object(PRD, 'query') as mock_query:
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = None
            
            result = self.define_agent._get_prd_context("test_project_123")
            
            assert result is None
    
    def test_retrieve_context_includes_prd(self, app_context):
        """Test _retrieve_context includes PRD context in results"""
        # Mock the _get_prd_context method
        with patch.object(self.define_agent, '_get_prd_context', return_value=self.prd_context):
            # Mock vector context service
            self.define_agent.vector_context_service = Mock()
            self.define_agent.vector_context_service.find_similar_specs.return_value = []
            self.define_agent.vector_context_service.find_related_docs.return_value = []
            self.define_agent.vector_context_service.find_similar_code.return_value = []
            
            result = self.define_agent._retrieve_context(
                "Test idea content", 
                "test_project_123", 
                self.project_context
            )
            
            assert 'prd_context' in result
            assert result['prd_context'] == self.prd_context
            assert 'prd:v1' in result['sources']
            assert 'system_map' in result['sources']
    
    def test_prepare_ai_context_includes_prd_section(self, app_context):
        """Test _prepare_ai_context includes PRD section when PRD context is available"""
        context_data = {
            'prd_context': self.prd_context,
            'sources': ['prd:v1', 'system_map']
        }
        
        result = self.define_agent._prepare_ai_context(
            "Test idea content",
            self.project_context,
            context_data
        )
        
        assert "=== PRODUCT REQUIREMENTS DOCUMENT (PRIMARY BUSINESS CONTEXT) ===" in result
        assert "PRD Version: v1 (frozen)" in result
        assert "Business Goals:" in result
        assert "Increase user engagement" in result
        assert "Target Users: Primary: End users, Secondary: Support staff" in result
        assert "ENSURE ALIGNMENT with the PRD business goals and user personas above" in result
    
    def test_prepare_ai_context_without_prd(self, app_context):
        """Test _prepare_ai_context works without PRD context"""
        context_data = {
            'sources': ['system_map']
        }
        
        result = self.define_agent._prepare_ai_context(
            "Test idea content",
            self.project_context,
            context_data
        )
        
        assert "=== PRODUCT REQUIREMENTS DOCUMENT" not in result
        assert "=== REPOSITORY ANALYSIS INSTRUCTION ===" in result
        assert "=== PROJECT SYSTEM MAP ===" in result
    
    def test_generate_requirements_includes_prd_instruction(self, app_context):
        """Test _generate_requirements includes PRD alignment instruction in prompt"""
        ai_context = """=== PRODUCT REQUIREMENTS DOCUMENT (PRIMARY BUSINESS CONTEXT) ===
PRD Version: v1 (frozen)
Business Goals:
- Increase user engagement
Target Users: End users"""
        
        # Mock AI broker response
        mock_response = Mock()
        mock_response.success = True
        mock_response.content = "# Requirements Document\n\nTest requirements content"
        mock_response.model_used = "claude-opus-4"
        self.mock_ai_broker.submit_request_sync.return_value = mock_response
        
        result = self.define_agent._generate_requirements(
            "Test idea content",
            ai_context,
            self.project_context
        )
        
        # Verify AI broker was called
        assert self.mock_ai_broker.submit_request_sync.called
        call_args = self.mock_ai_broker.submit_request_sync.call_args[0][0]
        
        # Check that the prompt includes PRD alignment instruction
        assert "ALIGN WITH BUSINESS CONTEXT" in call_args.instruction
        assert "must align with the Product Requirements Document" in call_args.instruction
        assert "Explicitly connects to PRD business goals and user personas" in call_args.instruction
    
    def test_store_specifications_includes_context_sources(self, app_context):
        """Test _store_specifications includes PRD version in context_sources"""
        context_data = {
            'sources': ['prd:v1', 'system_map', 'spec:similar_123']
        }
        
        specifications = {
            'requirements': '# Requirements\n\nTest requirements content'
        }
        
        with patch.object(SpecificationArtifact, 'query') as mock_query:
            with patch('src.models.base.db') as mock_db:
                mock_artifact = Mock()
                mock_query.get.return_value = None  # No existing artifact
                with patch.object(SpecificationArtifact, 'create_artifact', return_value=mock_artifact) as mock_create:
                    
                    self.define_agent._store_specifications(
                        "spec_test_123",
                        "test_project_123", 
                        specifications,
                        context_data
                    )
                    
                    # Verify create_artifact was called with context_sources
                    mock_create.assert_called_once()
                    call_kwargs = mock_create.call_args[1]
                    assert call_kwargs['context_sources'] == ['prd:v1', 'system_map', 'spec:similar_123']
    
    def test_process_event_with_prd_context_end_to_end(self, app_context):
        """Test complete event processing with PRD context integration"""
        # Create test event
        event = IdeaPromotedEvent(
            idea_id="idea_123",
            project_id="test_project_123",
            promoted_by="user_123"
        )
        
        # Mock dependencies
        with patch.object(self.define_agent, 'get_project_context', return_value=self.project_context):
            with patch.object(self.define_agent, '_get_idea_content', return_value="Test idea content"):
                with patch.object(self.define_agent, '_get_prd_context', return_value=self.prd_context):
                    with patch.object(self.define_agent, '_store_specifications') as mock_store:
                        # Mock vector context service
                        self.define_agent.vector_context_service = Mock()
                        self.define_agent.vector_context_service.find_similar_specs.return_value = []
                        self.define_agent.vector_context_service.find_related_docs.return_value = []
                        self.define_agent.vector_context_service.find_similar_code.return_value = []
                        
                        # Mock AI broker response
                        mock_response = Mock()
                        mock_response.success = True
                        mock_response.content = "# Requirements Document\n\nTest requirements"
                        mock_response.model_used = "claude-opus-4"
                        self.mock_ai_broker.submit_request_sync.return_value = mock_response
                        
                        result = self.define_agent.process_event(event)
                        
                        # Verify successful processing
                        assert result.success is True
                        assert result.result_data['ai_generated'] is True
                        
                        # Verify store_specifications was called with context data
                        mock_store.assert_called_once()
                        call_args = mock_store.call_args
                        # Check if context_data was passed (should be 4th positional arg or in kwargs)
                        if len(call_args[0]) > 3:
                            context_data = call_args[0][3]  # Fourth positional argument
                            assert 'prd:v1' in context_data['sources']
                        elif 'context_data' in call_args[1]:
                            context_data = call_args[1]['context_data']  # Keyword argument
                            assert 'prd:v1' in context_data['sources']
    
    def test_context_sources_tracking_in_specification_artifact(self, app_context):
        """Test that context sources are properly tracked in SpecificationArtifact"""
        context_sources = ['prd:v1', 'system_map', 'spec:similar_123']
        
        # Test creating artifact with context sources
        with patch('src.models.base.db') as mock_db:
            artifact = SpecificationArtifact.create_artifact(
                spec_id="spec_test_123",
                project_id="test_project_123",
                artifact_type=ArtifactType.REQUIREMENTS,
                content="Test requirements content",
                created_by="define_agent",
                ai_generated=True,
                ai_model_used="claude-opus-4",
                context_sources=context_sources
            )
            
            assert artifact.context_sources == context_sources
            assert artifact.ai_generated is True
            assert artifact.ai_model_used == "claude-opus-4"


if __name__ == '__main__':
    pytest.main([__file__])