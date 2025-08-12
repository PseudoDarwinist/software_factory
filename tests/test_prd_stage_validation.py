"""
Integration tests for PRD requirement validation during stage transitions.

Tests the implementation of task 2: Add PRD requirement validation when dragging ideas to Define phase.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

try:
    from src.app import create_app
    from src.models import db
    from src.models.feed_item import FeedItem
    from src.models.mission_control_project import MissionControlProject
    from src.models.prd import PRD
    from src.models.upload_session import UploadSession
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from src.app import create_app
    from src.models import db
    from src.models.feed_item import FeedItem
    from src.models.mission_control_project import MissionControlProject
    from src.models.prd import PRD
    from src.models.upload_session import UploadSession


@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        # Initialize the database
        db.init_app(app)
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_project():
    """Create a test project"""
    project = MissionControlProject.create(
        name="Test Project",
        description="Test project for PRD validation"
    )
    db.session.commit()
    return project


@pytest.fixture
def test_feed_item(test_project):
    """Create a test feed item"""
    feed_item = FeedItem.create(
        title="Test Feature Idea",
        summary="A test feature that needs a PRD",
        project_id=test_project.id
    )
    db.session.commit()
    return feed_item


@pytest.fixture
def test_upload_session(test_project):
    """Create a test upload session"""
    session = UploadSession.create(
        project_id=str(test_project.id),
        description="Test PRD upload session"
    )
    db.session.commit()
    return session


class TestPRDStageValidation:
    """Test PRD requirement validation for Define stage transitions"""

    def test_move_to_define_without_prd_fails(self, client, test_feed_item, test_project):
        """Test that moving to Define stage fails when no PRD exists"""
        response = client.post(f'/api/idea/{test_feed_item.id}/move-stage', 
                             json={
                                 'targetStage': 'define',
                                 'fromStage': 'think',
                                 'projectId': str(test_project.id)
                             })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'PRD_REQUIRED'
        assert 'error_details' in data
        assert data['error_details']['requirement_type'] == 'prd_missing'

    def test_move_to_define_with_draft_prd_fails(self, client, test_feed_item, test_project, test_upload_session):
        """Test that moving to Define stage fails when only draft PRD exists"""
        # Create a draft PRD
        prd = PRD.create_draft(
            project_id=str(test_project.id),
            draft_id=str(test_upload_session.id),
            md_content="# Test PRD\n\nThis is a draft PRD.",
            json_summary={'problem': {'text': 'Test problem'}},
            created_by='test_user'
        )
        assert prd.status == 'draft'
        
        response = client.post(f'/api/idea/{test_feed_item.id}/move-stage', 
                             json={
                                 'targetStage': 'define',
                                 'fromStage': 'think',
                                 'projectId': str(test_project.id)
                             })
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'PRD_REQUIRED'

    def test_move_to_define_with_frozen_prd_succeeds(self, client, test_feed_item, test_project, test_upload_session):
        """Test that moving to Define stage succeeds when frozen PRD exists"""
        # Create and freeze a PRD
        prd = PRD.create_draft(
            project_id=str(test_project.id),
            draft_id=str(test_upload_session.id),
            md_content="# Test PRD\n\nThis is a complete PRD.",
            json_summary={'problem': {'text': 'Test problem'}},
            created_by='test_user'
        )
        prd.freeze_version('test_user')
        assert prd.status == 'frozen'
        
        response = client.post(f'/api/idea/{test_feed_item.id}/move-stage', 
                             json={
                                 'targetStage': 'define',
                                 'fromStage': 'think',
                                 'projectId': str(test_project.id)
                             })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_move_to_other_stages_bypasses_prd_check(self, client, test_feed_item, test_project):
        """Test that moving to non-Define stages doesn't require PRD"""
        # Test moving to Plan stage without PRD
        response = client.post(f'/api/idea/{test_feed_item.id}/move-stage', 
                             json={
                                 'targetStage': 'plan',
                                 'fromStage': 'think',
                                 'projectId': str(test_project.id)
                             })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_prd_status_endpoint_no_prd(self, client, test_project):
        """Test PRD status endpoint when no PRD exists"""
        response = client.get(f'/api/project/{test_project.id}/prd-status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['has_frozen_prd'] is False
        assert data['data']['prd_status'] == 'missing'
        assert data['data']['can_move_to_define'] is False

    def test_prd_status_endpoint_with_draft_prd(self, client, test_project, test_upload_session):
        """Test PRD status endpoint when draft PRD exists"""
        # Create a draft PRD
        PRD.create_draft(
            project_id=str(test_project.id),
            draft_id=str(test_upload_session.id),
            md_content="# Test PRD\n\nThis is a draft PRD.",
            created_by='test_user'
        )
        
        response = client.get(f'/api/project/{test_project.id}/prd-status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['has_frozen_prd'] is False
        assert data['data']['prd_status'] == 'draft'
        assert data['data']['can_move_to_define'] is False
        assert len(data['data']['upload_sessions']) > 0

    def test_prd_status_endpoint_with_frozen_prd(self, client, test_project, test_upload_session):
        """Test PRD status endpoint when frozen PRD exists"""
        # Create and freeze a PRD
        prd = PRD.create_draft(
            project_id=str(test_project.id),
            draft_id=str(test_upload_session.id),
            md_content="# Test PRD\n\nThis is a complete PRD.",
            created_by='test_user'
        )
        prd.freeze_version('test_user')
        
        response = client.get(f'/api/project/{test_project.id}/prd-status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['has_frozen_prd'] is True
        assert data['data']['prd_status'] == 'frozen'
        assert data['data']['can_move_to_define'] is True
        assert data['data']['latest_prd'] is not None

    def test_prd_validation_handles_multiple_sessions(self, client, test_project):
        """Test PRD validation with multiple upload sessions"""
        # Create multiple upload sessions with PRDs
        session1 = UploadSession.create(
            project_id=str(test_project.id),
            description="First session"
        )
        session2 = UploadSession.create(
            project_id=str(test_project.id),
            description="Second session"
        )
        db.session.commit()
        
        # Create PRDs in both sessions
        prd1 = PRD.create_draft(
            project_id=str(test_project.id),
            draft_id=str(session1.id),
            md_content="# First PRD",
            created_by='test_user'
        )
        
        prd2 = PRD.create_draft(
            project_id=str(test_project.id),
            draft_id=str(session2.id),
            md_content="# Second PRD",
            created_by='test_user'
        )
        
        # Freeze the second PRD (more recent)
        prd2.freeze_version('test_user')
        
        response = client.get(f'/api/project/{test_project.id}/prd-status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['has_frozen_prd'] is True
        assert data['data']['prd_status'] == 'frozen'
        assert len(data['data']['upload_sessions']) == 2

    def test_prd_validation_error_handling(self, client, test_feed_item):
        """Test PRD validation handles errors gracefully"""
        # Test with invalid project ID
        response = client.post(f'/api/idea/{test_feed_item.id}/move-stage', 
                             json={
                                 'targetStage': 'define',
                                 'fromStage': 'think',
                                 'projectId': 'invalid-project-id'
                             })
        
        # Should fail due to invalid project, not PRD validation
        assert response.status_code in [400, 404]

    def test_prd_validation_with_missing_feed_item(self, client, test_project):
        """Test PRD validation with non-existent feed item"""
        response = client.post('/api/idea/invalid-item-id/move-stage', 
                             json={
                                 'targetStage': 'define',
                                 'fromStage': 'think',
                                 'projectId': str(test_project.id)
                             })
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error'].lower()

    def test_prd_validation_preserves_existing_functionality(self, client, test_feed_item, test_project):
        """Test that PRD validation doesn't break existing stage transitions"""
        # Test that the basic stage transition still works for non-Define stages
        stages_to_test = ['think', 'plan', 'build', 'validate']
        
        for target_stage in stages_to_test:
            response = client.post(f'/api/idea/{test_feed_item.id}/move-stage', 
                                 json={
                                     'targetStage': target_stage,
                                     'fromStage': 'think',
                                     'projectId': str(test_project.id)
                                 })
            
            assert response.status_code == 200, f"Failed to move to {target_stage}"
            data = json.loads(response.data)
            assert data['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])