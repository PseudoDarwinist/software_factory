"""
Unit tests for upload API endpoints
"""

import json
import pytest
from unittest.mock import patch, MagicMock

try:
    from src.models import db
    from src.models.upload_session import UploadSession
    from src.models.uploaded_file import UploadedFile
    from src.models.mission_control_project import MissionControlProject
    from src.api.upload import calculate_completeness_score
except ImportError:
    from models import db
    from models.upload_session import UploadSession
    from models.uploaded_file import UploadedFile
    from models.mission_control_project import MissionControlProject
    from api.upload import calculate_completeness_score


class TestUploadSessionAPI:
    """Test upload session management endpoints"""
    
    def test_create_session_success(self, client, sample_project):
        """Test successful session creation"""
        data = {
            'project_id': sample_project.id,
            'description': 'Test upload session'
        }
        
        response = client.post('/api/upload/session', 
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        
        assert 'session_id' in response_data
        assert response_data['project_id'] == sample_project.id
        assert response_data['description'] == 'Test upload session'
        assert response_data['status'] == 'active'
        assert response_data['progress'] == 0.0
        assert 'completeness_score' in response_data
    
    def test_create_session_missing_project_id(self, client):
        """Test session creation without project_id"""
        data = {'description': 'Test session'}
        
        response = client.post('/api/upload/session',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'project_id is required' in response_data['error']
    
    def test_create_session_invalid_project(self, client):
        """Test session creation with non-existent project"""
        data = {
            'project_id': 'non-existent-project',
            'description': 'Test session'
        }
        
        response = client.post('/api/upload/session',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert 'Project not found' in response_data['error']
    
    def test_update_session_status_success(self, client, sample_session):
        """Test successful status update"""
        data = {'status': 'reading'}
        
        response = client.put(f'/api/upload/session/{sample_session.id}/status',
                            data=json.dumps(data),
                            content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['status'] == 'reading'
        assert response_data['progress'] == 0.25
        assert 'updated_at' in response_data
    
    def test_update_session_status_invalid_status(self, client, sample_session):
        """Test status update with invalid status"""
        data = {'status': 'invalid_status'}
        
        response = client.put(f'/api/upload/session/{sample_session.id}/status',
                            data=json.dumps(data),
                            content_type='application/json')
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'Invalid status' in response_data['error']
    
    def test_update_session_status_missing_status(self, client, sample_session):
        """Test status update without status field"""
        data = {}
        
        response = client.put(f'/api/upload/session/{sample_session.id}/status',
                            data=json.dumps(data),
                            content_type='application/json')
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'status is required' in response_data['error']
    
    def test_update_session_status_not_found(self, client):
        """Test status update for non-existent session"""
        data = {'status': 'reading'}
        
        response = client.put('/api/upload/session/non-existent/status',
                            data=json.dumps(data),
                            content_type='application/json')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert 'Session not found' in response_data['error']
    
    def test_get_session_success(self, client, sample_session):
        """Test successful session retrieval"""
        response = client.get(f'/api/upload/session/{sample_session.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['session_id'] == str(sample_session.id)
        assert response_data['project_id'] == sample_session.project_id
        assert response_data['status'] == sample_session.status
        assert 'progress' in response_data
        assert 'file_count' in response_data
        assert 'completeness_score' in response_data
    
    def test_get_session_not_found(self, client):
        """Test retrieval of non-existent session"""
        response = client.get('/api/upload/session/non-existent')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert 'Session not found' in response_data['error']
    
    def test_update_ai_analysis_success(self, client, sample_session):
        """Test successful AI analysis update"""
        data = {
            'analysis': 'This is a comprehensive analysis with goals, risks, and competitors mentioned.'
        }
        
        response = client.put(f'/api/upload/session/{sample_session.id}/ai-analysis',
                            data=json.dumps(data),
                            content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['status'] == 'ready'
        assert response_data['progress'] == 1.0
        assert 'completeness_score' in response_data
    
    def test_update_ai_analysis_missing_analysis(self, client, sample_session):
        """Test AI analysis update without analysis field"""
        data = {}
        
        response = client.put(f'/api/upload/session/{sample_session.id}/ai-analysis',
                            data=json.dumps(data),
                            content_type='application/json')
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'analysis is required' in response_data['error']
    
    def test_update_combined_content_success(self, client, sample_session):
        """Test successful combined content update"""
        data = {'content': 'Combined content from all uploaded files'}
        
        response = client.put(f'/api/upload/session/{sample_session.id}/combined-content',
                            data=json.dumps(data),
                            content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['session_id'] == str(sample_session.id)
        assert 'updated_at' in response_data


class TestCompletenessScoring:
    """Test PRD completeness scoring logic"""
    
    def test_calculate_completeness_score_empty_analysis(self):
        """Test completeness scoring with empty analysis"""
        session = MagicMock()
        session.ai_analysis = None
        
        score = calculate_completeness_score(session)
        
        assert score['goals_numbered'] is False
        assert score['risks_covered'] is False
        assert score['competitors_mentioned'] == 0
        assert score['overall_score'] == 0.0
    
    def test_calculate_completeness_score_with_goals(self):
        """Test completeness scoring with numbered goals"""
        session = MagicMock()
        session.ai_analysis = "Goal 1: Improve user experience. Goal 2: Increase conversion rates."
        
        score = calculate_completeness_score(session)
        
        assert score['goals_numbered'] is True
        assert score['overall_score'] > 0.0
    
    def test_calculate_completeness_score_with_risks(self):
        """Test completeness scoring with risk coverage"""
        session = MagicMock()
        session.ai_analysis = "We need to consider accessibility and privacy risks in this feature."
        
        score = calculate_completeness_score(session)
        
        assert score['risks_covered'] is True
        assert score['overall_score'] > 0.0
    
    def test_calculate_completeness_score_with_competitors(self):
        """Test completeness scoring with competitor mentions"""
        session = MagicMock()
        session.ai_analysis = "Our main competitor offers similar features. Alternative solutions exist."
        
        score = calculate_completeness_score(session)
        
        assert score['competitors_mentioned'] >= 2
        assert score['overall_score'] > 0.0
    
    def test_calculate_completeness_score_full_analysis(self):
        """Test completeness scoring with comprehensive analysis"""
        session = MagicMock()
        session.ai_analysis = """
        Goal 1: Improve user experience by 25%.
        Goal 2: Increase conversion rates by 15%.
        
        We must address accessibility risks for users with disabilities.
        Privacy concerns around data collection need careful consideration.
        
        Our main competitor offers similar functionality.
        Alternative solutions in the market include various options.
        """
        
        score = calculate_completeness_score(session)
        
        assert score['goals_numbered'] is True
        assert score['risks_covered'] is True
        assert score['competitors_mentioned'] >= 2
        assert score['overall_score'] == 1.0


class TestProgressTracking:
    """Test progress tracking functionality"""
    
    def test_progress_stages(self, sample_session):
        """Test progress calculation for different stages"""
        # Test active stage
        sample_session.status = 'active'
        assert sample_session.get_progress_stage() == 0.0
        
        # Test reading stage
        sample_session.status = 'reading'
        assert sample_session.get_progress_stage() == 0.25
        
        # Test extracting stage
        sample_session.status = 'extracting'
        assert sample_session.get_progress_stage() == 0.50
        
        # Test drafting stage
        sample_session.status = 'drafting'
        assert sample_session.get_progress_stage() == 0.75
        
        # Test ready stage
        sample_session.status = 'ready'
        assert sample_session.get_progress_stage() == 1.0
    
    def test_session_with_files_progress(self, client, sample_session_with_files):
        """Test progress calculation with files"""
        response = client.get(f'/api/upload/session/{sample_session_with_files.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        # Progress should combine session stage and file processing
        assert 'progress' in response_data
        assert response_data['file_count'] > 0
        assert 'completed_files' in response_data
        assert 'error_files' in response_data


class TestPRDCreation:
    """Test PRD creation and retrieval functionality"""
    
    @patch('src.services.ai_broker.get_ai_broker')
    def test_analyze_session_creates_prd(self, mock_get_ai_broker, client, sample_session_with_files):
        """Test that analyzing session files creates a PRD record"""
        # Mock AI broker response
        mock_ai_broker = MagicMock()
        mock_ai_broker.analyze_uploaded_files.return_value = {
            'success': True,
            'analysis': '''
            # Product Requirements Document
            
            ## Problem
            Users need a better way to manage their tasks and improve productivity.
            
            ## Goals
            1. Increase user productivity by 25%
            2. Reduce task completion time by 30%
            3. Improve user satisfaction scores
            
            ## Risks
            - Accessibility concerns for users with disabilities
            - Privacy risks around data collection
            
            ## Competitive Analysis
            - Competitor A offers similar task management features
            - Alternative B provides basic productivity tools
            
            ## Open Questions
            - How will we measure productivity improvements?
            - What data privacy measures are needed?
            - Should we integrate with existing calendar systems?
            ''',
            'model_used': 'claude-opus-4',
            'processing_time': 5.2,
            'tokens_used': 1500
        }
        mock_get_ai_broker.return_value = mock_ai_broker
        
        # Make request to analyze session
        data = {
            'preferred_model': 'claude-opus-4',
            'created_by': 'test_user'
        }
        
        response = client.post(f'/api/upload/session/{sample_session_with_files.id}/analyze',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)['data']
        
        # Verify response includes PRD information
        assert response_data['status'] == 'success'
        assert response_data['model_used'] == 'claude-opus-4'
        assert 'prd_info' in response_data
        assert response_data['prd_info'] is not None
        assert response_data['prd_info']['version'] == 'v0'
        assert response_data['prd_info']['status'] == 'draft'
        assert response_data['prd_info']['id'] is not None
        
        # Verify PRD was created in database
        try:
            from src.models.prd import PRD
        except ImportError:
            from models.prd import PRD
        
        prd_record = PRD.get_latest_for_session(str(sample_session_with_files.id))
        assert prd_record is not None, f"PRD record should have been created for session {sample_session_with_files.id}"
        assert prd_record.version == 'v0'
        assert prd_record.status == 'draft'
        assert prd_record.md_uri is not None
        assert prd_record.json_uri is not None
        assert len(prd_record.sources) > 0
    
    def test_session_context_includes_prd_info(self, client, sample_session):
        """Test that session context endpoint returns PRD information"""
        # Create a PRD record for the session
        try:
            from src.models.prd import PRD
        except ImportError:
            from models.prd import PRD
        
        prd_record = PRD.create_draft(
            project_id=str(sample_session.project_id),
            draft_id=str(sample_session.id),
            md_content="# Test PRD Content",
            json_summary={'problem': {'text': 'Test problem', 'sources': ['S1']}},
            sources=['S1', 'S2'],
            created_by='test_user'
        )
        
        # Get session context
        response = client.get(f'/api/upload/session/context/{sample_session.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)['data']
        
        # Verify PRD information is included
        assert 'prd_info' in response_data
        assert response_data['prd_info'] is not None
        assert response_data['prd_info']['id'] == str(prd_record.id)
        assert response_data['prd_info']['version'] == 'v0'
        assert response_data['prd_info']['status'] == 'draft'
        assert response_data['prd_info']['has_markdown'] is True
        assert response_data['prd_info']['has_json_summary'] is True
        assert response_data['prd_info']['sources'] == ['S1', 'S2']
        assert response_data['prd_info']['created_by'] == 'test_user'
    
    def test_session_context_without_prd(self, client, sample_session):
        """Test session context when no PRD exists"""
        response = client.get(f'/api/upload/session/context/{sample_session.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)['data']
        
        # Verify PRD info is None when no PRD exists
        assert 'prd_info' in response_data
        assert response_data['prd_info'] is None
    
    @patch('src.services.ai_broker.get_ai_broker')
    def test_analyze_session_handles_prd_creation_failure(self, mock_get_ai_broker, client, sample_session_with_files):
        """Test that analysis continues even if PRD creation fails"""
        # Mock AI broker response
        mock_ai_broker = MagicMock()
        mock_ai_broker.analyze_uploaded_files.return_value = {
            'success': True,
            'analysis': 'Simple analysis without proper structure',
            'model_used': 'claude-opus-4',
            'processing_time': 2.1,
            'tokens_used': 800
        }
        mock_get_ai_broker.return_value = mock_ai_broker
        
        # Mock PRD creation to fail
        with patch('src.models.prd.PRD.create_draft', side_effect=Exception("Database error")):
            response = client.post(f'/api/upload/session/{sample_session_with_files.id}/analyze',
                                 data=json.dumps({'preferred_model': 'claude-opus-4'}),
                                 content_type='application/json')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)['data']
        
        # Verify analysis succeeded despite PRD creation failure
        assert response_data['status'] == 'success'
        assert response_data['model_used'] == 'claude-opus-4'
        assert response_data['prd_info'] is None  # PRD creation failed