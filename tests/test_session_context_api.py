"""
API tests for session context endpoint
"""

import pytest
import json
from unittest.mock import patch, Mock
from src.models import db
from src.models.upload_session import UploadSession
from src.models.uploaded_file import UploadedFile


class TestSessionContextAPI:
    """Test session context API endpoint"""
    
    def test_get_session_context_success(self, client, sample_session_with_files):
        """Test successful session context retrieval"""
        # Update session with AI analysis
        sample_session_with_files.update_ai_analysis('Generated PRD based on uploaded files')
        sample_session_with_files.update_ai_model_used('claude-opus-4')
        sample_session_with_files.update_prd_preview('PRD Preview: Executive Summary...')
        sample_session_with_files.update_completeness_score({
            'goals_numbered': True,
            'risks_covered': True,
            'competitors_mentioned': 2,
            'overall_score': 1.0
        })
        
        response = client.get(f'/api/upload/session/context/{sample_session_with_files.id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify session data
        assert data['session_id'] == str(sample_session_with_files.id)
        assert data['project_id'] == sample_session_with_files.project_id
        assert data['description'] == 'Test session with files'
        assert data['ai_model_used'] == 'claude-opus-4'
        assert data['ai_analysis'] == 'Generated PRD based on uploaded files'
        assert data['prd_preview'] == 'PRD Preview: Executive Summary...'
        
        # Verify completeness score
        assert data['completeness_score']['overall_score'] == 1.0
        assert data['completeness_score']['goals_numbered'] is True
        assert data['completeness_score']['risks_covered'] is True
        
        # Verify processing stats
        stats = data['processing_stats']
        assert stats['total_files'] == 3
        assert stats['completed_files'] == 2  # Only 2 files are completed in fixture
        assert stats['error_files'] == 0
        assert round(stats['success_rate'], 2) == 66.67  # 2/3 * 100
        
        # Verify file metadata
        files = data['files']
        assert len(files) == 3
        
        # Check that download URLs are present
        for file in files:
            assert 'download_url' in file
            assert file['download_url'].startswith('/api/upload/files/download/')
    
    def test_get_session_context_not_found(self, client):
        """Test session context retrieval for non-existent session"""
        response = client.get('/api/upload/session/context/nonexistent-session')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Session not found'
    
    def test_get_session_context_project_not_found(self, client, app_context):
        """Test session context retrieval when project doesn't exist"""
        # Create session with non-existent project
        orphan_session = UploadSession.create(
            project_id='nonexistent-project',
            description='Orphan session'
        )
        db.session.commit()
        
        response = client.get(f'/api/upload/session/context/{orphan_session.id}')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Project not found'
    
    def test_get_session_context_empty_session(self, client, sample_project):
        """Test session context retrieval for session with no files"""
        # Create empty session
        empty_session = UploadSession.create(
            project_id=sample_project.id,
            description='Empty session'
        )
        db.session.commit()
        
        response = client.get(f'/api/upload/session/context/{empty_session.id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['session_id'] == str(empty_session.id)
        assert data['processing_stats']['total_files'] == 0
        assert data['processing_stats']['completed_files'] == 0
        assert data['processing_stats']['success_rate'] == 0
        assert data['files'] == []
    
    def test_get_session_context_no_ai_analysis(self, client, sample_session):
        """Test session context retrieval for session without AI analysis"""
        response = client.get(f'/api/upload/session/context/{sample_session.id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['ai_model_used'] is None
        assert data['ai_analysis'] is None
        assert data['prd_preview'] is None
        assert data['combined_content'] is None
    
    def test_file_download_not_found(self, client):
        """Test file download for non-existent file"""
        response = client.get('/api/upload/files/download/nonexistent-file')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'File not found'


class TestSessionAnalysisAPI:
    """Test session analysis API endpoint"""
    
    @patch('src.services.ai_broker.get_ai_broker')
    def test_analyze_session_files_success(self, mock_get_broker, client, sample_session_with_files):
        """Test successful session file analysis"""
        # Mock AI broker
        mock_broker = Mock()
        mock_broker.analyze_uploaded_files.return_value = {
            'success': True,
            'analysis': 'Generated PRD based on uploaded files',
            'model_used': 'claude-opus-4',
            'processing_time': 8.5,
            'tokens_used': 2500
        }
        mock_get_broker.return_value = mock_broker
        
        response = client.post(
            f'/api/upload/session/{sample_session_with_files.id}/analyze',
            json={'preferred_model': 'claude-opus-4'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert data['model_used'] == 'claude-opus-4'
        assert data['processing_time'] == 8.5
        assert data['tokens_used'] == 2500
        
        # Verify AI broker was called correctly
        mock_broker.analyze_uploaded_files.assert_called_once()
        call_args = mock_broker.analyze_uploaded_files.call_args
        assert call_args[1]['session_id'] == str(sample_session_with_files.id)
        assert call_args[1]['preferred_model'] == 'claude-opus-4'
        assert len(call_args[1]['files']) == 2  # Only completed files
    
    def test_analyze_session_files_not_found(self, client):
        """Test analysis for non-existent session"""
        response = client.post('/api/upload/session/nonexistent/analyze')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Session not found'
    
    def test_analyze_session_files_no_completed_files(self, client, sample_session):
        """Test analysis for session with no completed files"""
        response = client.post(f'/api/upload/session/{sample_session.id}/analyze')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'No completed files to analyze'
    
    @patch('src.services.ai_broker.get_ai_broker')
    def test_analyze_session_files_ai_failure(self, mock_get_broker, client, sample_session_with_files):
        """Test analysis when AI processing fails"""
        # Mock AI broker failure
        mock_broker = Mock()
        mock_broker.analyze_uploaded_files.return_value = {
            'success': False,
            'error': 'All AI models failed to process the files',
            'model_used': None,
            'analysis': None
        }
        mock_get_broker.return_value = mock_broker
        
        response = client.post(
            f'/api/upload/session/{sample_session_with_files.id}/analyze',
            json={}  # Send empty JSON to fix content-type issue
        )
        
        assert response.status_code == 500  # AI failure returns 500
        data = json.loads(response.data)
        
        assert data['status'] == 'error'
        assert data['error'] == 'All AI models failed to process the files'