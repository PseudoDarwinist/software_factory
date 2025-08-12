"""
Unit tests for upload models
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.models import db, UploadSession, UploadedFile, MissionControlProject


class TestUploadSession:
    """Test cases for UploadSession model"""
    
    def test_create_upload_session(self, app_context):
        """Test creating a new upload session"""
        # Create a test project first
        project = MissionControlProject.create(
            id='test-project-1',
            name='Test Project',
            description='Test project for upload session'
        )
        db.session.commit()
        
        # Create upload session
        session = UploadSession.create(
            project_id='test-project-1',
            description='Test upload session'
        )
        db.session.commit()
        
        assert session.id is not None
        assert session.project_id == 'test-project-1'
        assert session.description == 'Test upload session'
        assert session.status == UploadSession.STATUS_ACTIVE
        assert session.created_at is not None
        assert session.updated_at is not None
    
    def test_upload_session_to_dict(self, app_context):
        """Test converting upload session to dictionary"""
        # Create a test project first
        project = MissionControlProject.create(
            id='test-project-2',
            name='Test Project 2',
            description='Test project for upload session'
        )
        db.session.commit()
        
        session = UploadSession.create(
            project_id='test-project-2',
            description='Test session'
        )
        db.session.commit()
        
        session_dict = session.to_dict()
        
        assert 'id' in session_dict
        assert session_dict['project_id'] == 'test-project-2'
        assert session_dict['description'] == 'Test session'
        assert session_dict['status'] == UploadSession.STATUS_ACTIVE
        assert 'created_at' in session_dict
        assert 'updated_at' in session_dict
        assert 'files' in session_dict
    
    def test_update_session_status(self, app_context):
        """Test updating session status"""
        # Create a test project first
        project = MissionControlProject.create(
            id='test-project-3',
            name='Test Project 3',
            description='Test project for upload session'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-3')
        db.session.commit()
        
        original_updated_at = session.updated_at
        
        session.update_status(UploadSession.STATUS_READING)
        
        assert session.status == UploadSession.STATUS_READING
        assert session.updated_at > original_updated_at
    
    def test_update_combined_content(self, app_context):
        """Test updating combined content"""
        # Create a test project first
        project = MissionControlProject.create(
            id='test-project-4',
            name='Test Project 4',
            description='Test project for upload session'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-4')
        db.session.commit()
        
        test_content = "This is test content from multiple files."
        session.update_combined_content(test_content)
        
        assert session.combined_content == test_content
    
    def test_update_ai_analysis(self, app_context):
        """Test updating AI analysis"""
        # Create a test project first
        project = MissionControlProject.create(
            id='test-project-5',
            name='Test Project 5',
            description='Test project for upload session'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-5')
        db.session.commit()
        
        test_analysis = "AI analysis results here."
        session.update_ai_analysis(test_analysis)
        
        assert session.ai_analysis == test_analysis
    
    def test_processing_progress_empty(self, app_context):
        """Test processing progress with no files"""
        # Create a test project first
        project = MissionControlProject.create(
            id='test-project-6',
            name='Test Project 6',
            description='Test project for upload session'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-6')
        db.session.commit()
        
        assert session.get_processing_progress() == 0.0
        assert session.is_processing_complete() == True
        assert session.has_processing_errors() == False
    
    def test_processing_progress_with_files(self, app_context):
        """Test processing progress with files"""
        # Create a test project first
        project = MissionControlProject.create(
            id='test-project-7',
            name='Test Project 7',
            description='Test project for upload session'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-7')
        db.session.commit()
        
        # Add test files
        file1 = UploadedFile.create(
            session_id=session.id,
            filename='test1.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/tmp/test1.pdf'
        )
        file2 = UploadedFile.create(
            session_id=session.id,
            filename='test2.jpg',
            file_type='jpg',
            file_size=2048,
            file_path='/tmp/test2.jpg'
        )
        db.session.commit()
        
        # Initially no files are complete
        assert session.get_processing_progress() == 0.0
        assert session.is_processing_complete() == False
        
        # Complete one file
        file1.complete_processing("Extracted text from PDF")
        
        assert session.get_processing_progress() == 50.0
        assert session.is_processing_complete() == False
        
        # Complete second file
        file2.complete_processing("Extracted text from image")
        
        assert session.get_processing_progress() == 100.0
        assert session.is_processing_complete() == True
    
    def test_file_counts(self, app_context):
        """Test file count methods"""
        # Create a test project first
        project = MissionControlProject.create(
            id='test-project-8',
            name='Test Project 8',
            description='Test project for upload session'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-8')
        db.session.commit()
        
        # Add test files
        file1 = UploadedFile.create(
            session_id=session.id,
            filename='test1.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/tmp/test1.pdf'
        )
        file2 = UploadedFile.create(
            session_id=session.id,
            filename='test2.jpg',
            file_type='jpg',
            file_size=2048,
            file_path='/tmp/test2.jpg'
        )
        db.session.commit()
        
        assert session.get_file_count() == 2
        assert session.get_completed_file_count() == 0
        assert session.get_error_file_count() == 0
        
        # Complete one file and error one
        file1.complete_processing("Extracted text")
        file2.mark_processing_error()
        
        assert session.get_completed_file_count() == 1
        assert session.get_error_file_count() == 1
        assert session.has_processing_errors() == True


class TestUploadedFile:
    """Test cases for UploadedFile model"""
    
    def test_create_uploaded_file(self, app_context):
        """Test creating a new uploaded file"""
        # Create a test project and session first
        project = MissionControlProject.create(
            id='test-project-file-1',
            name='Test Project File 1',
            description='Test project for uploaded file'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-file-1')
        db.session.commit()
        
        # Create uploaded file
        file_record = UploadedFile.create(
            session_id=session.id,
            filename='test.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/tmp/test.pdf'
        )
        db.session.commit()
        
        assert file_record.id is not None
        assert file_record.session_id == session.id
        assert file_record.filename == 'test.pdf'
        assert file_record.file_type == 'pdf'
        assert file_record.file_size == 1024
        assert file_record.file_path == '/tmp/test.pdf'
        assert file_record.processing_status == UploadedFile.STATUS_PENDING
        assert file_record.created_at is not None
    
    def test_uploaded_file_to_dict(self, app_context):
        """Test converting uploaded file to dictionary"""
        # Create a test project and session first
        project = MissionControlProject.create(
            id='test-project-file-2',
            name='Test Project File 2',
            description='Test project for uploaded file'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-file-2')
        db.session.commit()
        
        file_record = UploadedFile.create(
            session_id=session.id,
            filename='test.jpg',
            file_type='jpg',
            file_size=2048,
            file_path='/tmp/test.jpg'
        )
        db.session.commit()
        
        file_dict = file_record.to_dict()
        
        assert 'id' in file_dict
        assert file_dict['filename'] == 'test.jpg'
        assert file_dict['file_type'] == 'jpg'
        assert file_dict['file_size'] == 2048
        assert file_dict['processing_status'] == UploadedFile.STATUS_PENDING
        assert 'created_at' in file_dict
    
    def test_update_processing_status(self, app_context):
        """Test updating processing status"""
        # Create a test project and session first
        project = MissionControlProject.create(
            id='test-project-file-3',
            name='Test Project File 3',
            description='Test project for uploaded file'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-file-3')
        db.session.commit()
        
        file_record = UploadedFile.create(
            session_id=session.id,
            filename='test.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/tmp/test.pdf'
        )
        db.session.commit()
        
        file_record.update_processing_status(UploadedFile.STATUS_PROCESSING)
        
        assert file_record.processing_status == UploadedFile.STATUS_PROCESSING
    
    def test_complete_processing(self, app_context):
        """Test completing file processing"""
        # Create a test project and session first
        project = MissionControlProject.create(
            id='test-project-file-4',
            name='Test Project File 4',
            description='Test project for uploaded file'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-file-4')
        db.session.commit()
        
        file_record = UploadedFile.create(
            session_id=session.id,
            filename='test.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/tmp/test.pdf'
        )
        db.session.commit()
        
        extracted_text = "This is extracted text from the PDF."
        file_record.complete_processing(extracted_text)
        
        assert file_record.processing_status == UploadedFile.STATUS_COMPLETE
        assert file_record.extracted_text == extracted_text
    
    def test_mark_processing_error(self, app_context):
        """Test marking processing error"""
        # Create a test project and session first
        project = MissionControlProject.create(
            id='test-project-file-5',
            name='Test Project File 5',
            description='Test project for uploaded file'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-file-5')
        db.session.commit()
        
        file_record = UploadedFile.create(
            session_id=session.id,
            filename='test.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/tmp/test.pdf'
        )
        db.session.commit()
        
        file_record.mark_processing_error()
        
        assert file_record.processing_status == UploadedFile.STATUS_ERROR
    
    def test_file_type_checks(self, app_context):
        """Test file type checking methods"""
        # Create a test project and session first
        project = MissionControlProject.create(
            id='test-project-file-6',
            name='Test Project File 6',
            description='Test project for uploaded file'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-file-6')
        db.session.commit()
        
        # Test PDF file
        pdf_file = UploadedFile.create(
            session_id=session.id,
            filename='test.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/tmp/test.pdf'
        )
        
        assert pdf_file.is_supported_type() == True
        assert pdf_file.is_pdf_type() == True
        assert pdf_file.is_image_type() == False
        
        # Test image file
        jpg_file = UploadedFile.create(
            session_id=session.id,
            filename='test.jpg',
            file_type='jpg',
            file_size=2048,
            file_path='/tmp/test.jpg'
        )
        
        assert jpg_file.is_supported_type() == True
        assert jpg_file.is_pdf_type() == False
        assert jpg_file.is_image_type() == True
        
        db.session.commit()
    
    def test_file_size_mb(self, app_context):
        """Test file size in MB calculation"""
        # Create a test project and session first
        project = MissionControlProject.create(
            id='test-project-file-7',
            name='Test Project File 7',
            description='Test project for uploaded file'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-file-7')
        db.session.commit()
        
        # 1MB file
        file_record = UploadedFile.create(
            session_id=session.id,
            filename='test.pdf',
            file_type='pdf',
            file_size=1024 * 1024,  # 1MB
            file_path='/tmp/test.pdf'
        )
        db.session.commit()
        
        assert file_record.get_file_size_mb() == 1.0
    
    def test_class_methods(self, app_context):
        """Test class methods for querying files"""
        # Create a test project and session first
        project = MissionControlProject.create(
            id='test-project-file-8',
            name='Test Project File 8',
            description='Test project for uploaded file'
        )
        db.session.commit()
        
        session = UploadSession.create(project_id='test-project-file-8')
        db.session.commit()
        
        # Create test files
        file1 = UploadedFile.create(
            session_id=session.id,
            filename='test1.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/tmp/test1.pdf'
        )
        file2 = UploadedFile.create(
            session_id=session.id,
            filename='test2.jpg',
            file_type='jpg',
            file_size=2048,
            file_path='/tmp/test2.jpg'
        )
        db.session.commit()
        
        # Test get_by_session
        session_files = UploadedFile.get_by_session(session.id)
        assert len(session_files) == 2
        
        # Test get_pending_files
        pending_files = UploadedFile.get_pending_files(session.id)
        assert len(pending_files) == 2
        
        # Complete one file
        file1.complete_processing("Extracted text")
        
        # Test get_completed_files
        completed_files = UploadedFile.get_completed_files(session.id)
        assert len(completed_files) == 1
        
        # Test get_pending_files after completion
        pending_files = UploadedFile.get_pending_files(session.id)
        assert len(pending_files) == 1