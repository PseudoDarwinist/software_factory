"""
Tests for upload processing status API
"""

import json
from unittest.mock import patch

try:
    from src.models import db
    from src.models.upload_session import UploadSession
    from src.models.uploaded_file import UploadedFile
except ImportError:
    from models import db
    from models.upload_session import UploadSession
    from models.uploaded_file import UploadedFile


class TestProcessingStatusAPI:
    """Test processing status endpoints"""
    
    def test_get_status_no_files(self, client, sample_session):
        """Test status for session with no files"""
        response = client.get(f'/api/upload/status/{sample_session.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['session_id'] == str(sample_session.id)
        assert response_data['overall_status'] == 'no_files'
        assert response_data['progress_percentage'] == 0.0
        assert response_data['total_files'] == 0
        assert len(response_data['files']) == 0
    
    def test_get_status_with_files(self, client, sample_session_with_files):
        """Test status for session with files"""
        response = client.get(f'/api/upload/status/{sample_session_with_files.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['session_id'] == str(sample_session_with_files.id)
        assert response_data['total_files'] == 3
        assert response_data['completed_files'] == 2
        assert response_data['pending_files'] == 1
        assert response_data['progress_percentage'] > 0
        assert len(response_data['files']) == 3
        
        # Check file details structure
        for file_info in response_data['files']:
            assert 'id' in file_info
            assert 'filename' in file_info
            assert 'file_type' in file_info
            assert 'source_id' in file_info
            assert 'processing_status' in file_info
            assert 'can_retry' in file_info
    
    def test_get_status_all_complete(self, client, sample_session, app_context):
        """Test status when all files are complete"""
        # Create files and mark them as complete
        files = []
        for i in range(3):
            file_record = UploadedFile.create(
                session_id=sample_session.id,
                filename=f'test_{i+1}.pdf',
                file_type='pdf',
                file_size=1024,
                file_path=f'/uploads/test_{i+1}.pdf'
            )
            file_record.complete_processing(f'Extracted text {i+1}')
            files.append(file_record)
        
        db.session.commit()
        
        response = client.get(f'/api/upload/status/{sample_session.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['overall_status'] == 'complete'
        assert response_data['progress_percentage'] == 100.0
        assert response_data['completed_files'] == 3
        assert response_data['error_files'] == 0
    
    def test_get_status_with_errors(self, client, sample_session, app_context):
        """Test status when some files have errors"""
        # Create files with mixed statuses
        file1 = UploadedFile.create(
            session_id=sample_session.id,
            filename='success.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/uploads/success.pdf'
        )
        file1.complete_processing('Success')
        
        file2 = UploadedFile.create(
            session_id=sample_session.id,
            filename='error.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/uploads/error.pdf'
        )
        file2.mark_processing_error()
        
        db.session.commit()
        
        response = client.get(f'/api/upload/status/{sample_session.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['overall_status'] == 'partial_error'
        assert response_data['completed_files'] == 1
        assert response_data['error_files'] == 1
        assert response_data['progress_percentage'] == 50.0
        
        # Check that error files have can_retry flag
        error_file = next(f for f in response_data['files'] if f['processing_status'] == 'error')
        assert error_file['can_retry'] is True
    
    def test_get_status_all_errors(self, client, sample_session, app_context):
        """Test status when all files have errors"""
        # Create files with errors
        for i in range(2):
            file_record = UploadedFile.create(
                session_id=sample_session.id,
                filename=f'error_{i+1}.pdf',
                file_type='pdf',
                file_size=1024,
                file_path=f'/uploads/error_{i+1}.pdf'
            )
            file_record.mark_processing_error()
        
        db.session.commit()
        
        response = client.get(f'/api/upload/status/{sample_session.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['overall_status'] == 'error'
        assert response_data['error_files'] == 2
        assert response_data['completed_files'] == 0
        assert response_data['progress_percentage'] == 0.0
    
    def test_get_status_processing(self, client, sample_session, app_context):
        """Test status when files are processing"""
        file_record = UploadedFile.create(
            session_id=sample_session.id,
            filename='processing.pdf',
            file_type='pdf',
            file_size=1024,
            file_path='/uploads/processing.pdf'
        )
        file_record.update_processing_status('processing')
        
        db.session.commit()
        
        response = client.get(f'/api/upload/status/{sample_session.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['overall_status'] == 'processing'
        assert response_data['processing_files'] == 1
    
    def test_get_status_session_not_found(self, client):
        """Test status for non-existent session"""
        response = client.get('/api/upload/status/non-existent')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert 'Session not found' in response_data['error']


class TestRetryProcessing:
    """Test file processing retry functionality"""
    
    def test_retry_file_success(self, client, sample_uploaded_file):
        """Test successful file retry"""
        # Mark file as error first
        sample_uploaded_file.mark_processing_error()
        db.session.commit()
        
        response = client.post(f'/api/upload/retry/{sample_uploaded_file.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        assert response_data['file_id'] == str(sample_uploaded_file.id)
        assert response_data['processing_status'] == 'pending'
        assert 'queued for retry' in response_data['message']
        
        # Verify file status was updated in database
        db.session.refresh(sample_uploaded_file)
        assert sample_uploaded_file.processing_status == 'pending'
    
    def test_retry_file_not_found(self, client):
        """Test retry for non-existent file"""
        response = client.post('/api/upload/retry/non-existent')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert 'File not found' in response_data['error']
    
    def test_retry_file_not_in_error_state(self, client, sample_uploaded_file):
        """Test retry for file not in error state"""
        # File is in pending state by default
        response = client.post(f'/api/upload/retry/{sample_uploaded_file.id}')
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'not in error state' in response_data['error']


class TestStatusAggregation:
    """Test status aggregation logic"""
    
    def test_progress_calculation(self, sample_session, app_context):
        """Test progress percentage calculation"""
        # Create 4 files with different statuses
        files = []
        statuses = ['complete', 'complete', 'error', 'pending']
        
        for i, status in enumerate(statuses):
            file_record = UploadedFile.create(
                session_id=sample_session.id,
                filename=f'test_{i+1}.pdf',
                file_type='pdf',
                file_size=1024,
                file_path=f'/uploads/test_{i+1}.pdf'
            )
            
            if status == 'complete':
                file_record.complete_processing(f'Text {i+1}')
            elif status == 'error':
                file_record.mark_processing_error()
            elif status == 'processing':
                file_record.update_processing_status('processing')
            # pending is default
            
            files.append(file_record)
        
        db.session.commit()
        
        # Calculate expected progress: 2 complete out of 4 = 50%
        progress = sample_session.get_processing_progress()
        assert progress == 50.0
    
    def test_file_validation_in_status(self, client, sample_session, app_context):
        """Test that validation errors are included in status for error files"""
        # Create a file that would fail validation
        file_record = UploadedFile.create(
            session_id=sample_session.id,
            filename='large.pdf',
            file_type='pdf',
            file_size=35 * 1024 * 1024,  # 35MB - exceeds Claude limit
            file_path='/uploads/large.pdf',
            page_count=150  # Exceeds page limit
        )
        file_record.mark_processing_error()
        
        db.session.commit()
        
        response = client.get(f'/api/upload/status/{sample_session.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        
        error_file = response_data['files'][0]
        assert error_file['processing_status'] == 'error'
        assert 'validation_errors' in error_file
        assert len(error_file['validation_errors']) > 0
        assert any('32MB limit' in error for error in error_file['validation_errors'])
        assert any('100 page limit' in error for error in error_file['validation_errors'])