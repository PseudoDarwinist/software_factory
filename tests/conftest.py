"""
Pytest configuration and fixtures for upload models tests
"""

import pytest
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Import models directly to avoid complex app initialization
from src.models.base import db
from src.models.upload_session import UploadSession
from src.models.uploaded_file import UploadedFile
from src.models.mission_control_project import MissionControlProject
from src.models.prd import PRD


@pytest.fixture
def app():
    """Create minimal test Flask application"""
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key'
    })
    
    # Initialize database with app
    db.init_app(app)
    
    # Register upload blueprint for API tests
    try:
        from src.api.upload import upload_bp
        app.register_blueprint(upload_bp)
    except ImportError:
        from api.upload import upload_bp
        app.register_blueprint(upload_bp)
    
    return app


@pytest.fixture
def app_context(app):
    """Create application context for tests"""
    with app.app_context():
        # Create all tables
        db.create_all()
        yield app
        # Clean up
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_context):
    """Create test client with app context"""
    return app_context.test_client()


@pytest.fixture
def sample_project(app_context):
    """Create a sample project for testing"""
    import uuid
    project = MissionControlProject(
        id=str(uuid.uuid4()),
        name='Test Project',
        description='A test project for upload functionality'
    )
    db.session.add(project)
    db.session.commit()
    return project


@pytest.fixture
def sample_session(app_context, sample_project):
    """Create a sample upload session for testing"""
    session = UploadSession.create(
        project_id=sample_project.id,
        description='Test upload session'
    )
    db.session.commit()
    return session


@pytest.fixture
def sample_uploaded_file(app_context, sample_session):
    """Create a sample uploaded file for testing"""
    file_record = UploadedFile.create(
        session_id=sample_session.id,
        filename='test_document.pdf',
        file_type='pdf',
        file_size=1024000,  # 1MB
        file_path='/uploads/test_document.pdf',
        page_count=10
    )
    db.session.commit()
    return file_record


@pytest.fixture
def sample_session_with_files(app_context, sample_project):
    """Create a sample session with multiple files for testing"""
    session = UploadSession.create(
        project_id=sample_project.id,
        description='Test session with files'
    )
    db.session.commit()
    
    # Add multiple files
    files = []
    for i in range(3):
        file_record = UploadedFile.create(
            session_id=session.id,
            filename=f'test_file_{i+1}.pdf',
            file_type='pdf',
            file_size=1024000 * (i+1),
            file_path=f'/uploads/test_file_{i+1}.pdf',
            page_count=10 * (i+1)
        )
        files.append(file_record)
    
    # Mark some files as complete
    files[0].complete_processing('Extracted text from file 1')
    files[1].complete_processing('Extracted text from file 2')
    # Leave files[2] as pending
    
    db.session.commit()
    return session