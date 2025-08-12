"""
Unit tests for AI Broker file analysis functionality
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from src.services.ai_broker import AIBroker, get_ai_broker


class TestAIBrokerFileAnalysis:
    """Test AI Broker file analysis methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.broker = AIBroker()
        self.session_id = "test-session-123"
        
        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test PDF file (mock)
        self.pdf_path = os.path.join(self.temp_dir, "test.pdf")
        with open(self.pdf_path, 'wb') as f:
            f.write(b"Mock PDF content")
        
        # Create test image file (mock)
        self.image_path = os.path.join(self.temp_dir, "test.jpg")
        with open(self.image_path, 'wb') as f:
            f.write(b"Mock JPEG content")
        
        # Create test URL content file
        self.url_path = os.path.join(self.temp_dir, "url_content.txt")
        with open(self.url_path, 'w') as f:
            f.write("Mock URL content from webpage")
    
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_analyze_uploaded_files_success(self):
        """Test successful file analysis"""
        files = [
            {
                'file_path': self.pdf_path,
                'file_type': 'pdf',
                'filename': 'test.pdf'
            },
            {
                'file_path': self.image_path,
                'file_type': 'jpg',
                'filename': 'test.jpg'
            }
        ]
        
        # Mock successful AI response
        mock_response = {
            'success': True,
            'content': 'Generated PRD content based on uploaded files',
            'processing_time': 5.0,
            'tokens_used': 1500
        }
        
        with patch.object(self.broker, '_execute_file_analysis', return_value={
            'success': True,
            'analysis': mock_response['content'],
            'model_used': 'claude-opus-4',
            'provider': 'model_garden',
            'processing_time': mock_response['processing_time'],
            'tokens_used': mock_response['tokens_used']
        }):
            result = self.broker.analyze_uploaded_files(self.session_id, files)
        
        assert result['success'] is True
        assert result['analysis'] == mock_response['content']
        assert result['model_used'] == 'claude-opus-4'
        assert result['processing_time'] == mock_response['processing_time']
        assert result['tokens_used'] == mock_response['tokens_used']
    
    def test_analyze_uploaded_files_no_files(self):
        """Test analysis with no processable files"""
        files = []
        
        result = self.broker.analyze_uploaded_files(self.session_id, files)
        
        assert result['success'] is False
        assert 'No files could be processed' in result['error']
        assert result['model_used'] is None
    
    def test_analyze_uploaded_files_all_models_fail(self):
        """Test analysis when all AI models fail"""
        files = [
            {
                'file_path': self.pdf_path,
                'file_type': 'pdf',
                'filename': 'test.pdf'
            }
        ]
        
        # Mock all models failing
        with patch.object(self.broker, '_execute_file_analysis', return_value={
            'success': False,
            'error': 'Model failed',
            'model_used': 'claude-opus-4'
        }):
            result = self.broker.analyze_uploaded_files(self.session_id, files)
        
        assert result['success'] is False
        assert 'All AI models failed' in result['error']
        assert result['model_used'] is None
    
    def test_prepare_pdf_file(self):
        """Test PDF file preparation"""
        result = self.broker._prepare_pdf_file(self.pdf_path, "test.pdf")
        
        assert result is not None
        assert result['filename'] == "test.pdf"
        assert result['file_type'] == 'pdf'
        assert result['media_type'] == 'application/pdf'
        assert 'content' in result
        assert result['size'] > 0
    
    def test_prepare_image_file(self):
        """Test image file preparation"""
        result = self.broker._prepare_image_file(self.image_path, "test.jpg", "jpg")
        
        assert result is not None
        assert result['filename'] == "test.jpg"
        assert result['file_type'] == 'jpg'
        assert result['media_type'] == 'image/jpeg'
        assert 'content' in result
        assert result['size'] > 0
    
    def test_prepare_url_content(self):
        """Test URL content preparation"""
        result = self.broker._prepare_url_content(self.url_path, "webpage.url")
        
        assert result is not None
        assert result['filename'] == "webpage.url"
        assert result['file_type'] == 'url'
        assert result['media_type'] == 'text/plain'
        assert result['content'] == "Mock URL content from webpage"
        assert result['size'] > 0
    
    def test_prepare_file_nonexistent(self):
        """Test file preparation with non-existent file"""
        file_info = {
            'file_path': '/nonexistent/file.pdf',
            'file_type': 'pdf',
            'filename': 'nonexistent.pdf'
        }
        
        result = self.broker._prepare_file_for_ai(file_info)
        
        assert result is None
    
    def test_prepare_file_unsupported_type(self):
        """Test file preparation with unsupported file type"""
        # Create a test file with unsupported type
        unsupported_path = os.path.join(self.temp_dir, "test.txt")
        with open(unsupported_path, 'w') as f:
            f.write("Test content")
        
        file_info = {
            'file_path': unsupported_path,
            'file_type': 'txt',
            'filename': 'test.txt'
        }
        
        result = self.broker._prepare_file_for_ai(file_info)
        
        assert result is None
    
    def test_get_model_fallback_chain_default(self):
        """Test default model fallback chain"""
        chain = self.broker._get_model_fallback_chain()
        
        expected_chain = ['claude-opus-4', 'gemini-2.5-flash', 'gpt-4o', 'claude-sonnet-3.5']
        assert chain == expected_chain
    
    def test_get_model_fallback_chain_preferred(self):
        """Test model fallback chain with preferred model"""
        chain = self.broker._get_model_fallback_chain('gemini-2.5-flash')
        
        assert chain[0] == 'gemini-2.5-flash'
        assert 'claude-opus-4' in chain
        assert 'gpt-4o' in chain
        assert len(chain) == 4
    
    def test_create_prd_generation_prompt(self):
        """Test PRD generation prompt creation"""
        files = [
            {
                'filename': 'requirements.pdf',
                'file_type': 'pdf'
            },
            {
                'filename': 'mockup.jpg',
                'file_type': 'jpg'
            }
        ]
        
        prompt = self.broker._create_prd_generation_prompt(files)
        
        assert 'requirements.pdf' in prompt
        assert 'mockup.jpg' in prompt
        assert 'PDF' in prompt
        assert 'JPG' in prompt
        assert 'Executive Summary' in prompt
        assert 'Problem Statement' in prompt
        assert 'User Stories' in prompt
        assert '[S1], [S2], [S3]' in prompt
    
    @patch('requests.post')
    def test_execute_claude_analysis_success(self, mock_post):
        """Test successful Claude analysis"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Generated PRD from Claude'
                }
            }],
            'usage': {
                'total_tokens': 1500
            }
        }
        mock_post.return_value = mock_response
        
        files = [
            {
                'filename': 'test.pdf',
                'file_type': 'pdf',
                'content': 'base64content',
                'size': 1024
            }
        ]
        
        result = self.broker._execute_claude_analysis("Test prompt", files)
        
        assert result['success'] is True
        assert result['content'] == 'Generated PRD from Claude'
        assert result['tokens_used'] == 1500
        assert result['processing_time'] > 0
    
    @patch('requests.post')
    def test_execute_claude_analysis_failure(self, mock_post):
        """Test Claude analysis failure"""
        # Mock API failure
        mock_post.side_effect = Exception("API Error")
        
        files = [
            {
                'filename': 'test.pdf',
                'file_type': 'pdf',
                'content': 'base64content',
                'size': 1024
            }
        ]
        
        result = self.broker._execute_claude_analysis("Test prompt", files)
        
        assert result['success'] is False
        assert 'API Error' in result['error']
        assert result['content'] is None
    
    @patch('requests.post')
    def test_execute_gemini_analysis_success(self, mock_post):
        """Test successful Gemini analysis"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Generated PRD from Gemini'
                }
            }],
            'usage': {
                'total_tokens': 1200
            }
        }
        mock_post.return_value = mock_response
        
        files = [
            {
                'filename': 'webpage.url',
                'file_type': 'url',
                'content': 'URL content',
                'size': 512
            }
        ]
        
        result = self.broker._execute_gemini_analysis("Test prompt", files)
        
        assert result['success'] is True
        assert result['content'] == 'Generated PRD from Gemini'
        assert result['tokens_used'] == 1200
    
    @patch('requests.post')
    def test_execute_gpt4o_analysis_success(self, mock_post):
        """Test successful GPT-4o analysis"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Generated PRD from GPT-4o'
                }
            }],
            'usage': {
                'total_tokens': 1800
            }
        }
        mock_post.return_value = mock_response
        
        files = [
            {
                'filename': 'image.png',
                'file_type': 'png',
                'content': 'base64content',
                'size': 2048
            }
        ]
        
        result = self.broker._execute_gpt4o_analysis("Test prompt", files)
        
        assert result['success'] is True
        assert result['content'] == 'Generated PRD from GPT-4o'
        assert result['tokens_used'] == 1800
    
    def test_execute_text_only_analysis_success(self):
        """Test successful text-only analysis fallback"""
        files = [
            {
                'filename': 'webpage.url',
                'file_type': 'url',
                'content': 'URL content for analysis',
                'size': 512
            }
        ]
        
        # Mock ModelGardenIntegration
        with patch('src.services.ai_broker.ModelGardenIntegration') as mock_mg:
            mock_instance = Mock()
            mock_instance.execute_task.return_value = {
                'success': True,
                'output': 'Text-only analysis result'
            }
            mock_mg.return_value = mock_instance
            
            result = self.broker._execute_text_only_analysis('claude-sonnet-3.5', "Test prompt", files)
        
        assert result['success'] is True
        assert result['content'] == 'Text-only analysis result'
    
    def test_execute_file_analysis_model_not_found(self):
        """Test file analysis with non-existent model"""
        files = [
            {
                'filename': 'test.pdf',
                'file_type': 'pdf',
                'content': 'content',
                'size': 1024
            }
        ]
        
        result = self.broker._execute_file_analysis('nonexistent-model', files, self.session_id)
        
        assert result['success'] is False
        assert 'Model nonexistent-model not found' in result['error']
        assert result['model_used'] == 'nonexistent-model'
    
    def test_execute_file_analysis_unsupported_provider(self):
        """Test file analysis with unsupported provider"""
        files = [
            {
                'filename': 'test.pdf',
                'file_type': 'pdf',
                'content': 'content',
                'size': 1024
            }
        ]
        
        # Mock a model with unsupported provider
        with patch.object(self.broker.model_selector, 'model_configs', {
            'test-model': Mock(provider='unsupported_provider')
        }):
            result = self.broker._execute_file_analysis('test-model', files, self.session_id)
        
        assert result['success'] is False
        assert 'Provider unsupported_provider not supported' in result['error']
        assert result['model_used'] == 'test-model'


class TestAIBrokerIntegration:
    """Integration tests for AI Broker file analysis"""
    
    def test_get_ai_broker_singleton(self):
        """Test that get_ai_broker returns singleton instance"""
        broker1 = get_ai_broker()
        broker2 = get_ai_broker()
        
        assert broker1 is broker2
        assert hasattr(broker1, 'analyze_uploaded_files')
    
    def test_analyze_uploaded_files_method_exists(self):
        """Test that analyze_uploaded_files method exists and is callable"""
        broker = get_ai_broker()
        
        assert hasattr(broker, 'analyze_uploaded_files')
        assert callable(getattr(broker, 'analyze_uploaded_files'))
    
    def test_file_preparation_methods_exist(self):
        """Test that all file preparation methods exist"""
        broker = get_ai_broker()
        
        methods = [
            '_prepare_file_for_ai',
            '_prepare_pdf_file',
            '_prepare_image_file',
            '_prepare_url_content'
        ]
        
        for method in methods:
            assert hasattr(broker, method)
            assert callable(getattr(broker, method))
    
    def test_ai_execution_methods_exist(self):
        """Test that all AI execution methods exist"""
        broker = get_ai_broker()
        
        methods = [
            '_execute_file_analysis',
            '_execute_claude_analysis',
            '_execute_gemini_analysis',
            '_execute_gpt4o_analysis',
            '_execute_text_only_analysis'
        ]
        
        for method in methods:
            assert hasattr(broker, method)
            assert callable(getattr(broker, method))