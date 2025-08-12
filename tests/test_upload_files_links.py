"""
Integration tests for file and link upload endpoints
"""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from io import BytesIO

try:
    from src.models import db
    from src.models.upload_session import UploadSession
    from src.models.uploaded_file import UploadedFile
except ImportError:
    from models import db
    from models.upload_session import UploadSession
    from models.uploaded_file import UploadedFile


class TestFileUpload:
    """Test file upload endpoints"""
    
    def test_upload_files_success(self, client, sample_session):
        """Test successful file upload"""
        # Create test file data
        test_file_data = b"This is a test PDF content"
        
        data = {
            'files': [(BytesIO(test_file_data), 'test.pdf')]
        }
        
        with patch('os.makedirs'), patch('werkzeug.datastructures.FileStorage.save'):
            response = client.post(f'/api/upload/files/{sample_session.id}',
                                 data=data,
                                 content_type='multipart/form-data')
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        
        assert response_data['session_id'] == str(sample_session.id)
        assert response_data['total_uploaded'] == 1
        assert len(response_data['uploaded_files']) == 1
        
        uploaded_file = response_data['uploaded_files'][0]
        assert uploaded_file['filename'] == 'test.pdf'
        assert uploaded_file['file_type'] == 'pdf'
        assert uploaded_file['source_id'] == 'S1'
    
    def test_upload_files_invalid_session(self, client):
        """Test file upload with invalid session"""
        test_file_data = b"Test content"
        
        data = {
            'files': [(BytesIO(test_file_data), 'test.pdf')]
        }
        
        response = client.post('/api/upload/files/invalid-session',
                             data=data,
                             content_type='multipart/form-data')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert 'Session not found' in response_data['error']
    
    def test_upload_files_no_files(self, client, sample_session):
        """Test file upload without files"""
        response = client.post(f'/api/upload/files/{sample_session.id}',
                             data={},
                             content_type='multipart/form-data')
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'No files provided' in response_data['error']
    
    def test_upload_files_unsupported_type(self, client, sample_session):
        """Test file upload with unsupported file type"""
        test_file_data = b"This is a test file"
        
        data = {
            'files': [(BytesIO(test_file_data), 'test.txt')]
        }
        
        response = client.post(f'/api/upload/files/{sample_session.id}',
                             data=data,
                             content_type='multipart/form-data')
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        
        assert response_data['total_uploaded'] == 0
        assert 'errors' in response_data
        assert any('Unsupported file type' in error for error in response_data['errors'])
    
    def test_upload_files_too_large(self, client, sample_session):
        """Test file upload with file too large"""
        # Create a file larger than 10MB
        large_file_data = b"x" * (11 * 1024 * 1024)  # 11MB
        
        data = {
            'files': [(BytesIO(large_file_data), 'large.pdf')]
        }
        
        response = client.post(f'/api/upload/files/{sample_session.id}',
                             data=data,
                             content_type='multipart/form-data')
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        
        assert response_data['total_uploaded'] == 0
        assert 'errors' in response_data
        assert any('Exceeds 10MB limit' in error for error in response_data['errors'])
    
    def test_upload_multiple_files(self, client, sample_session):
        """Test uploading multiple files"""
        test_files = [
            (BytesIO(b"PDF content 1"), 'test1.pdf'),
            (BytesIO(b"Image content"), 'test.jpg'),
            (BytesIO(b"PNG content"), 'test.png')
        ]
        
        data = {'files': test_files}
        
        with patch('os.makedirs'), patch('werkzeug.datastructures.FileStorage.save'):
            response = client.post(f'/api/upload/files/{sample_session.id}',
                                 data=data,
                                 content_type='multipart/form-data')
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        
        assert response_data['total_uploaded'] == 3
        assert len(response_data['uploaded_files']) == 3
        
        # Check source IDs are assigned correctly
        source_ids = [f['source_id'] for f in response_data['uploaded_files']]
        assert 'S1' in source_ids
        assert 'S2' in source_ids
        assert 'S3' in source_ids


class TestLinkUpload:
    """Test link upload endpoints"""
    
    @patch('requests.head')
    @patch('requests.get')
    def test_upload_links_success(self, mock_get, mock_head, client, sample_session):
        """Test successful link upload"""
        # Mock successful URL validation
        mock_head.return_value.status_code = 200
        
        # Mock successful content fetch
        mock_response = MagicMock()
        mock_response.text = "This is content from the URL"
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        data = {
            'urls': ['https://example.com/page1', 'https://example.com/page2']
        }
        
        with patch('os.makedirs'), patch('builtins.open', create=True):
            response = client.post(f'/api/upload/links/{sample_session.id}',
                                 data=json.dumps(data),
                                 content_type='application/json')
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        
        assert response_data['session_id'] == str(sample_session.id)
        assert response_data['total_uploaded'] == 2
        assert len(response_data['uploaded_links']) == 2
        
        # Check that files are marked as complete
        for link in response_data['uploaded_links']:
            assert link['file_type'] == 'url'
            assert link['processing_status'] == 'complete'
            assert link['source_id'] in ['S1', 'S2']
    
    def test_upload_links_invalid_session(self, client):
        """Test link upload with invalid session"""
        data = {'urls': ['https://example.com']}
        
        response = client.post('/api/upload/links/invalid-session',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert 'Session not found' in response_data['error']
    
    def test_upload_links_no_urls(self, client, sample_session):
        """Test link upload without URLs"""
        data = {}
        
        response = client.post(f'/api/upload/links/{sample_session.id}',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'No URLs provided' in response_data['error']
    
    def test_upload_links_empty_list(self, client, sample_session):
        """Test link upload with empty URL list"""
        data = {'urls': []}
        
        response = client.post(f'/api/upload/links/{sample_session.id}',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'URLs must be provided as a non-empty list' in response_data['error']
    
    @patch('requests.head')
    def test_upload_links_invalid_url(self, mock_head, client, sample_session):
        """Test link upload with invalid URL"""
        mock_head.side_effect = Exception("Connection failed")
        
        data = {'urls': ['invalid-url', 'https://example.com']}
        
        response = client.post(f'/api/upload/links/{sample_session.id}',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        
        assert response_data['total_uploaded'] == 0
        assert 'errors' in response_data
        assert len(response_data['errors']) == 2  # Both URLs should fail
    
    @patch('requests.head')
    def test_upload_links_inaccessible_url(self, mock_head, client, sample_session):
        """Test link upload with inaccessible URL"""
        mock_head.return_value.status_code = 404
        
        data = {'urls': ['https://example.com/not-found']}
        
        response = client.post(f'/api/upload/links/{sample_session.id}',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        
        assert response_data['total_uploaded'] == 0
        assert 'errors' in response_data
        assert any('not accessible' in error for error in response_data['errors'])


class TestFileChipData:
    """Test file chip data structure and progress indicators"""
    
    def test_file_chip_data_structure(self, sample_uploaded_file):
        """Test that uploaded file provides correct chip data structure"""
        file_dict = sample_uploaded_file.to_dict()
        
        # Check required fields for file chip
        assert 'id' in file_dict
        assert 'filename' in file_dict
        assert 'file_type' in file_dict
        assert 'file_size' in file_dict
        assert 'source_id' in file_dict
        assert 'processing_status' in file_dict
        
        # Check source ID format
        assert file_dict['source_id'].startswith('S')
        assert file_dict['source_id'][1:].isdigit()
    
    def test_source_id_assignment(self, app_context, sample_session):
        """Test that source IDs are assigned sequentially"""
        files = []
        
        # Create multiple files
        for i in range(5):
            file_record = UploadedFile.create(
                session_id=sample_session.id,
                filename=f'test_{i+1}.pdf',
                file_type='pdf',
                file_size=1024,
                file_path=f'/uploads/test_{i+1}.pdf'
            )
            files.append(file_record)
        
        db.session.commit()
        
        # Check source IDs are sequential
        source_ids = [f.source_id for f in files]
        expected_ids = ['S1', 'S2', 'S3', 'S4', 'S5']
        
        assert source_ids == expected_ids
    
    def test_file_validation_methods(self, sample_uploaded_file):
        """Test file validation methods"""
        # Test PDF validation
        sample_uploaded_file.file_type = 'pdf'
        assert sample_uploaded_file.is_pdf_type()
        assert not sample_uploaded_file.is_image_type()
        assert not sample_uploaded_file.is_url_type()
        
        # Test image validation
        sample_uploaded_file.file_type = 'jpg'
        assert not sample_uploaded_file.is_pdf_type()
        assert sample_uploaded_file.is_image_type()
        assert not sample_uploaded_file.is_url_type()
        
        # Test URL validation
        sample_uploaded_file.file_type = 'url'
        assert not sample_uploaded_file.is_pdf_type()
        assert not sample_uploaded_file.is_image_type()
        assert sample_uploaded_file.is_url_type()
    
    def test_ai_processing_validation(self, sample_uploaded_file):
        """Test AI processing validation"""
        # Test valid PDF
        sample_uploaded_file.file_type = 'pdf'
        sample_uploaded_file.file_size = 5 * 1024 * 1024  # 5MB
        sample_uploaded_file.page_count = 50
        
        errors = sample_uploaded_file.validate_for_ai_processing()
        assert len(errors) == 0
        
        # Test PDF too large
        sample_uploaded_file.file_size = 35 * 1024 * 1024  # 35MB
        errors = sample_uploaded_file.validate_for_ai_processing()
        assert any('32MB limit' in error for error in errors)
        
        # Test PDF too many pages
        sample_uploaded_file.file_size = 5 * 1024 * 1024  # 5MB
        sample_uploaded_file.page_count = 150
        errors = sample_uploaded_file.validate_for_ai_processing()
        assert any('100 page limit' in error for error in errors)