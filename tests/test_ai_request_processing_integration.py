"""
Integration tests for AI request processing and batching
"""

import pytest
import tempfile
import os
import json
import base64
from unittest.mock import Mock, patch, MagicMock
from src.services.ai_broker import AIBroker, get_ai_broker


class TestAIRequestProcessingIntegration:
    """Integration tests for AI request processing with real file scenarios"""
    
    def setup_method(self):
        """Set up test fixtures with realistic file scenarios"""
        self.broker = get_ai_broker()
        self.session_id = "integration-test-session"
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create realistic test files
        self._create_test_files()
    
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_files(self):
        """Create realistic test files for integration testing"""
        # Create a mock PDF with realistic content
        self.pdf_path = os.path.join(self.temp_dir, "requirements_doc.pdf")
        with open(self.pdf_path, 'wb') as f:
            # Create a small PDF-like binary content
            pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
            pdf_content += b"Mock requirements document content for PRD generation"
            f.write(pdf_content)
        
        # Create a mock image file
        self.image_path = os.path.join(self.temp_dir, "ui_mockup.png")
        with open(self.image_path, 'wb') as f:
            # Create a small PNG-like binary content
            png_header = b'\x89PNG\r\n\x1a\n'
            png_content = png_header + b"Mock UI mockup image data for analysis"
            f.write(png_content)
        
        # Create URL content file
        self.url_path = os.path.join(self.temp_dir, "competitor_analysis.txt")
        with open(self.url_path, 'w', encoding='utf-8') as f:
            f.write("""
            Competitor Analysis - Feature Comparison
            
            Our main competitors offer the following features:
            1. User authentication and authorization
            2. Real-time collaboration tools
            3. Advanced analytics dashboard
            4. Mobile-responsive design
            5. API integrations with third-party services
            
            Key differentiators we should focus on:
            - Better user experience
            - Faster performance
            - More intuitive interface
            - Advanced AI-powered features
            """)
        
        # Create a large file to test batching limits
        self.large_file_path = os.path.join(self.temp_dir, "large_spec.txt")
        with open(self.large_file_path, 'w', encoding='utf-8') as f:
            # Create content that would exceed token limits if not properly batched
            large_content = "Technical specification section. " * 1000
            f.write(large_content)
    
    def test_multi_file_batch_processing(self):
        """Test processing multiple files in a single batch request"""
        files = [
            {
                'file_path': self.pdf_path,
                'file_type': 'pdf',
                'filename': 'requirements_doc.pdf'
            },
            {
                'file_path': self.image_path,
                'file_type': 'png',
                'filename': 'ui_mockup.png'
            },
            {
                'file_path': self.url_path,
                'file_type': 'url',
                'filename': 'competitor_analysis.url'
            }
        ]
        
        # Mock successful AI response for batch processing
        mock_analysis_result = {
            'success': True,
            'analysis': """
            # Product Requirements Document
            
            ## Executive Summary
            Based on the uploaded requirements document [S1], UI mockup [S2], and competitor analysis [S3], 
            this PRD outlines a comprehensive solution for user collaboration platform.
            
            ## Problem Statement
            Current solutions lack intuitive user experience and advanced AI features as identified in [S3].
            
            ## Solution Overview
            The proposed solution addresses these gaps with:
            - Enhanced user interface as shown in [S2]
            - Core requirements from [S1]
            - Competitive advantages over existing solutions [S3]
            """,
            'model_used': 'claude-opus-4',
            'provider': 'model_garden',
            'processing_time': 8.5,
            'tokens_used': 2500
        }
        
        with patch.object(self.broker, '_execute_file_analysis', return_value=mock_analysis_result):
            result = self.broker.analyze_uploaded_files(self.session_id, files, preferred_model='claude-opus-4')
        
        # Verify batch processing results
        assert result['success'] is True
        assert result['model_used'] == 'claude-opus-4'
        assert '[S1]' in result['analysis']  # PDF reference
        assert '[S2]' in result['analysis']  # Image reference
        assert '[S3]' in result['analysis']  # URL reference
        assert result['processing_time'] > 0
        assert result['tokens_used'] > 0
    
    def test_model_fallback_chain_integration(self):
        """Test complete model fallback chain when models fail"""
        files = [
            {
                'file_path': self.pdf_path,
                'file_type': 'pdf',
                'filename': 'test_doc.pdf'
            }
        ]
        
        # Mock progressive model failures and final success
        call_count = 0
        def mock_execute_analysis(model_id, processed_files, session_id):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:  # First two models fail
                return {
                    'success': False,
                    'error': f'Model {model_id} temporarily unavailable',
                    'model_used': model_id
                }
            else:  # Third model succeeds
                return {
                    'success': True,
                    'analysis': f'PRD generated successfully by {model_id}',
                    'model_used': model_id,
                    'provider': 'model_garden',
                    'processing_time': 5.0,
                    'tokens_used': 1500
                }
        
        with patch.object(self.broker, '_execute_file_analysis', side_effect=mock_execute_analysis):
            result = self.broker.analyze_uploaded_files(self.session_id, files)
        
        # Verify fallback worked
        assert result['success'] is True
        assert call_count == 3  # Tried 3 models before success
        assert 'PRD generated successfully' in result['analysis']
    
    def test_base64_encoding_integration(self):
        """Test base64 encoding for binary files"""
        files = [
            {
                'file_path': self.pdf_path,
                'file_type': 'pdf',
                'filename': 'test.pdf'
            }
        ]
        
        # Capture the prepared files to verify base64 encoding
        prepared_files = []
        
        def mock_execute_analysis(model_id, processed_files, session_id):
            nonlocal prepared_files
            prepared_files = processed_files
            return {
                'success': True,
                'analysis': 'Test analysis',
                'model_used': model_id,
                'provider': 'model_garden',
                'processing_time': 1.0,
                'tokens_used': 100
            }
        
        with patch.object(self.broker, '_execute_file_analysis', side_effect=mock_execute_analysis):
            result = self.broker.analyze_uploaded_files(self.session_id, files)
        
        # Verify base64 encoding
        assert len(prepared_files) == 1
        prepared_file = prepared_files[0]
        assert prepared_file['file_type'] == 'pdf'
        assert prepared_file['media_type'] == 'application/pdf'
        assert 'content' in prepared_file
        
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(prepared_file['content'])
            assert b'PDF' in decoded  # Should contain PDF header
        except Exception:
            pytest.fail("Base64 content is not valid")
    
    def test_prd_prompt_optimization(self):
        """Test PRD generation prompt optimization for document analysis"""
        files = [
            {
                'filename': 'business_requirements.pdf',
                'file_type': 'pdf'
            },
            {
                'filename': 'user_research.png',
                'file_type': 'png'
            }
        ]
        
        prompt = self.broker._create_prd_generation_prompt(files)
        
        # Verify prompt contains all required PRD sections
        required_sections = [
            'Executive Summary',
            'Problem Statement',
            'Solution Overview',
            'User Stories & Requirements',
            'Technical Considerations',
            'Success Metrics',
            'Implementation Roadmap'
        ]
        
        for section in required_sections:
            assert section in prompt, f"Missing required section: {section}"
        
        # Verify file references
        assert 'business_requirements.pdf' in prompt
        assert 'user_research.png' in prompt
        assert 'PDF' in prompt
        assert 'PNG' in prompt
        
        # Verify source attribution guidance
        assert '[S1], [S2], [S3]' in prompt
        
        # Verify analysis guidelines
        assert 'Extract and synthesize information from ALL uploaded files' in prompt
        assert 'actionable, specific requirements' in prompt
    
    @patch('requests.post')
    def test_claude_api_integration(self, mock_post):
        """Test Claude API integration with file processing"""
        # Mock successful Claude API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': """
                    # Product Requirements Document
                    
                    ## Executive Summary
                    Based on the uploaded files, this PRD outlines a comprehensive solution.
                    
                    ## Problem Statement
                    The analysis of [S1] reveals key user pain points that need addressing.
                    """
                }
            }],
            'usage': {
                'total_tokens': 2000
            }
        }
        mock_post.return_value = mock_response
        
        files = [
            {
                'filename': 'requirements.pdf',
                'file_type': 'pdf',
                'content': base64.b64encode(b'Mock PDF content').decode('utf-8'),
                'size': 1024
            }
        ]
        
        result = self.broker._execute_claude_analysis("Test prompt", files)
        
        # Verify API call
        assert mock_post.called
        call_args = mock_post.call_args
        
        # Verify request structure
        assert call_args[1]['json']['model'] == 'claude-opus-4'
        assert call_args[1]['json']['temperature'] == 0.7
        assert call_args[1]['json']['max_tokens'] == 4000
        
        # Verify response processing
        assert result['success'] is True
        assert 'Product Requirements Document' in result['content']
        assert result['tokens_used'] == 2000
        assert result['processing_time'] > 0
    
    @patch('requests.post')
    def test_gemini_api_integration(self, mock_post):
        """Test Gemini API integration with file processing"""
        # Mock successful Gemini API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': """
                    # PRD: Enhanced User Experience Platform
                    
                    ## Overview
                    This document outlines requirements for a next-generation platform.
                    
                    ## Key Features
                    - Real-time collaboration [S1]
                    - Advanced analytics [S2]
                    """
                }
            }],
            'usage': {
                'total_tokens': 1800
            }
        }
        mock_post.return_value = mock_response
        
        files = [
            {
                'filename': 'feature_specs.url',
                'file_type': 'url',
                'content': 'Feature specification content from URL',
                'size': 512
            }
        ]
        
        result = self.broker._execute_gemini_analysis("Test prompt", files)
        
        # Verify API call
        assert mock_post.called
        call_args = mock_post.call_args
        
        # Verify request structure
        assert call_args[1]['json']['model'] == 'gemini-2.5-flash'
        assert 'feature_specs.url' in call_args[1]['json']['messages'][0]['content']
        
        # Verify response processing
        assert result['success'] is True
        assert 'Enhanced User Experience Platform' in result['content']
        assert result['tokens_used'] == 1800
    
    @patch('requests.post')
    def test_gpt4o_api_integration(self, mock_post):
        """Test GPT-4o API integration with file processing"""
        # Mock successful GPT-4o API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': """
                    # Product Requirements Document
                    
                    ## Executive Summary
                    Comprehensive analysis of uploaded materials reveals opportunity for innovation.
                    
                    ## Technical Architecture
                    Based on [S1] technical specifications and [S2] user interface designs.
                    """
                }
            }],
            'usage': {
                'total_tokens': 2200
            }
        }
        mock_post.return_value = mock_response
        
        files = [
            {
                'filename': 'tech_specs.pdf',
                'file_type': 'pdf',
                'content': base64.b64encode(b'Technical specifications').decode('utf-8'),
                'size': 2048
            },
            {
                'filename': 'ui_design.png',
                'file_type': 'png',
                'content': base64.b64encode(b'UI design mockup').decode('utf-8'),
                'size': 1536
            }
        ]
        
        result = self.broker._execute_gpt4o_analysis("Test prompt", files)
        
        # Verify API call
        assert mock_post.called
        call_args = mock_post.call_args
        
        # Verify request structure
        assert call_args[1]['json']['model'] == 'gpt-4o'
        assert 'tech_specs.pdf' in call_args[1]['json']['messages'][0]['content']
        assert 'ui_design.png' in call_args[1]['json']['messages'][0]['content']
        
        # Verify response processing
        assert result['success'] is True
        assert 'Technical Architecture' in result['content']
        assert result['tokens_used'] == 2200
    
    def test_error_handling_integration(self):
        """Test comprehensive error handling in request processing"""
        # Test with non-existent files
        files = [
            {
                'file_path': '/nonexistent/file.pdf',
                'file_type': 'pdf',
                'filename': 'missing.pdf'
            }
        ]
        
        result = self.broker.analyze_uploaded_files(self.session_id, files)
        
        assert result['success'] is False
        assert 'No files could be processed' in result['error']
    
    def test_large_file_handling(self):
        """Test handling of large files that might exceed token limits"""
        files = [
            {
                'file_path': self.large_file_path,
                'file_type': 'url',
                'filename': 'large_specification.url'
            }
        ]
        
        # Mock response that handles large content
        mock_result = {
            'success': True,
            'analysis': 'PRD generated from large specification document with appropriate content summarization',
            'model_used': 'claude-opus-4',
            'provider': 'model_garden',
            'processing_time': 12.0,
            'tokens_used': 3500
        }
        
        with patch.object(self.broker, '_execute_file_analysis', return_value=mock_result):
            result = self.broker.analyze_uploaded_files(self.session_id, files)
        
        assert result['success'] is True
        assert result['tokens_used'] > 0
        assert result['processing_time'] > 0
    
    def test_model_specific_formatting(self):
        """Test that different models receive appropriately formatted requests"""
        files = [
            {
                'file_path': self.pdf_path,
                'file_type': 'pdf',
                'filename': 'test.pdf'
            }
        ]
        
        # Test each model gets called with appropriate formatting
        models_to_test = ['claude-opus-4', 'gemini-2.5-flash', 'gpt-4o']
        
        for model in models_to_test:
            # Mock the specific execution method for each model
            if model == 'claude-opus-4':
                mock_method_name = '_execute_claude_analysis'
            elif model == 'gemini-2.5-flash':
                mock_method_name = '_execute_gemini_analysis'
            elif model == 'gpt-4o':
                mock_method_name = '_execute_gpt4o_analysis'
            
            with patch.object(self.broker, mock_method_name, return_value={
                'success': True,
                'content': f'Response from {model}',
                'processing_time': 1.0,
                'tokens_used': 100
            }) as mock_exec:
                
                result = self.broker._execute_file_analysis(model, [{'filename': 'test.pdf', 'file_type': 'pdf'}], self.session_id)
                
                if result['success']:
                    assert mock_exec.called
                    assert f'Response from {model}' in result.get('analysis', result.get('content', ''))


class TestAIRequestBatchingEdgeCases:
    """Test edge cases in AI request batching and processing"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.broker = get_ai_broker()
    
    def test_empty_file_list_batching(self):
        """Test batching with empty file list"""
        result = self.broker.analyze_uploaded_files("test-session", [])
        
        assert result['success'] is False
        assert 'No files could be processed' in result['error']
    
    def test_mixed_file_types_batching(self):
        """Test batching with mixed supported and unsupported file types"""
        # Create temporary files
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create supported file
            pdf_path = os.path.join(temp_dir, "supported.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(b"PDF content")
            
            # Create unsupported file path (doesn't exist)
            unsupported_path = "/nonexistent/unsupported.txt"
            
            files = [
                {
                    'file_path': pdf_path,
                    'file_type': 'pdf',
                    'filename': 'supported.pdf'
                },
                {
                    'file_path': unsupported_path,
                    'file_type': 'txt',
                    'filename': 'unsupported.txt'
                }
            ]
            
            # Mock successful processing of the supported file
            with patch.object(self.broker, '_execute_file_analysis', return_value={
                'success': True,
                'analysis': 'Analysis of supported file',
                'model_used': 'claude-opus-4',
                'provider': 'model_garden',
                'processing_time': 1.0,
                'tokens_used': 100
            }):
                result = self.broker.analyze_uploaded_files("test-session", files)
            
            # Should succeed with the one processable file
            assert result['success'] is True
            assert 'Analysis of supported file' in result['analysis']
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_all_files_fail_preparation(self):
        """Test when all files fail during preparation"""
        files = [
            {
                'file_path': '/nonexistent1.pdf',
                'file_type': 'pdf',
                'filename': 'missing1.pdf'
            },
            {
                'file_path': '/nonexistent2.jpg',
                'file_type': 'jpg',
                'filename': 'missing2.jpg'
            }
        ]
        
        result = self.broker.analyze_uploaded_files("test-session", files)
        
        assert result['success'] is False
        assert 'No files could be processed' in result['error']
    
    def test_request_timeout_handling(self):
        """Test handling of request timeouts"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create test file
            pdf_path = os.path.join(temp_dir, "test.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(b"PDF content")
            
            files = [
                {
                    'file_path': pdf_path,
                    'file_type': 'pdf',
                    'filename': 'test.pdf'
                }
            ]
            
            # Mock timeout error - all models fail
            with patch.object(self.broker, '_execute_file_analysis', side_effect=Exception("Request timeout")):
                result = self.broker.analyze_uploaded_files("test-session", files)
            
            assert result['success'] is False
            # The error message will be about all models failing since all models throw the timeout exception
            assert 'All AI models failed' in result['error']
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)