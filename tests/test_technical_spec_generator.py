"""
Unit tests for TechnicalSpecGenerator
Tests technical specification generation with various scenarios and validation
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

# Handle imports for testing
try:
    from src.services.prd_generation_orchestrator import (
        TechnicalSpecGenerator, GenerationResult, GenerationStage
    )
    from src.services.ai_broker import AIResponse
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    from services.prd_generation_orchestrator import (
        TechnicalSpecGenerator, GenerationResult, GenerationStage
    )
    from services.ai_broker import AIResponse


class TestTechnicalSpecGenerator(unittest.TestCase):
    """Test cases for TechnicalSpecGenerator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.generator = TechnicalSpecGenerator()
        
        # Mock AI broker
        self.mock_ai_broker = Mock()
        self.generator.ai_broker = self.mock_ai_broker
        
        # Sample context data
        self.sample_context = {
            'upload_data': {
                'files': [
                    {
                        'name': 'app.py',
                        'analysis': 'Flask web application with REST API endpoints'
                    },
                    {
                        'name': 'models.py', 
                        'analysis': 'SQLAlchemy database models for user and project entities'
                    },
                    {
                        'name': 'requirements.txt',
                        'analysis': 'Python dependencies including Flask, SQLAlchemy, Redis'
                    }
                ]
            },
            'template': {
                'sections': ['technical_spec', 'architecture', 'implementation']
            },
            'previous_outputs': {
                GenerationStage.PRODUCT_SPEC: """
                ## Product Specification
                
                ### Introduction & Vision
                A comprehensive project management platform that enables teams to collaborate
                on software development projects with AI-powered assistance.
                
                ### Functional Requirements
                - User authentication and authorization
                - Project creation and management
                - Real-time collaboration features
                - AI-powered code analysis and suggestions
                - Integration with external tools (GitHub, Slack)
                """
            }
        }
    
    def test_analyze_technical_complexity_high(self):
        """Test technical complexity analysis for high complexity systems"""
        product_spec = """
        The system uses microservices architecture with Kubernetes orchestration.
        It includes machine learning models for real-time recommendations and
        distributed data processing with Apache Kafka streaming.
        """
        
        upload_data = {
            'files': [
                {'name': 'docker-compose.yml', 'analysis': 'Container orchestration'},
                {'name': 'ml_model.py', 'analysis': 'Neural network implementation'}
            ]
        }
        
        complexity = self.generator._analyze_technical_complexity(product_spec, upload_data)
        
        self.assertEqual(complexity['level'], 'high')
        self.assertIn('distributed_systems', complexity['domains'])
        self.assertIn('ai_ml', complexity['domains'])
        self.assertIn('real_time', complexity['domains'])
    
    def test_analyze_technical_complexity_medium(self):
        """Test technical complexity analysis for medium complexity systems"""
        product_spec = """
        A web application with REST API backend and React frontend.
        Uses PostgreSQL database with Redis caching layer.
        """
        
        upload_data = {
            'files': [
                {'name': 'app.py', 'analysis': 'Flask web application'},
                {'name': 'frontend.js', 'analysis': 'React components'}
            ]
        }
        
        complexity = self.generator._analyze_technical_complexity(product_spec, upload_data)
        
        self.assertEqual(complexity['level'], 'medium')
        self.assertIn('backend', complexity['technologies'])
        self.assertIn('frontend', complexity['technologies'])
    
    def test_build_enhanced_technical_spec_prompt(self):
        """Test enhanced technical specification prompt building"""
        technical_complexity = {
            'level': 'high',
            'domains': ['distributed_systems', 'ai_ml'],
            'technologies': ['backend', 'frontend'],
            'integrations': [],
            'scale_indicators': []
        }
        
        prompt = self.generator._build_enhanced_technical_spec_prompt(
            self.sample_context['upload_data'],
            self.sample_context['template'],
            self.sample_context['previous_outputs'][GenerationStage.PRODUCT_SPEC],
            technical_complexity
        )
        
        # Check that prompt includes key elements
        self.assertIn('Technical Specification', prompt)
        self.assertIn('System Overview', prompt)
        self.assertIn('High-Level Architecture', prompt)
        self.assertIn('Security and RBAC', prompt)
        self.assertIn('DevOps Requirements', prompt)
        
        # Check complexity-specific content
        self.assertIn('Complexity Level: high', prompt)
        self.assertIn('distributed_systems', prompt)
        self.assertIn('microservices architecture', prompt)
        
        # Check file analysis inclusion
        self.assertIn('app.py', prompt)
        self.assertIn('Flask web application', prompt)
    
    def test_get_complexity_guidance_high(self):
        """Test complexity guidance for high complexity systems"""
        technical_complexity = {
            'level': 'high',
            'domains': ['distributed_systems', 'ai_ml', 'real_time']
        }
        
        guidance = self.generator._get_complexity_guidance(technical_complexity)
        
        self.assertIn('microservices architecture', guidance)
        self.assertIn('service mesh', guidance)
        self.assertIn('ML model deployment', guidance)
        self.assertIn('real-time data processing', guidance)
    
    def test_get_complexity_guidance_medium(self):
        """Test complexity guidance for medium complexity systems"""
        technical_complexity = {
            'level': 'medium',
            'domains': ['mobile']
        }
        
        guidance = self.generator._get_complexity_guidance(technical_complexity)
        
        self.assertIn('modular architecture', guidance)
        self.assertIn('service boundaries', guidance)
        self.assertIn('mobile-specific architecture', guidance)
    
    def test_get_technology_sections(self):
        """Test technology-specific sections generation"""
        technical_complexity = {
            'domains': ['ai_ml', 'real_time', 'mobile']
        }
        
        sections = self.generator._get_technology_sections(technical_complexity)
        
        self.assertIn('AI/ML Architecture', sections)
        self.assertIn('Real-time Processing Architecture', sections)
        self.assertIn('Mobile Architecture', sections)
        self.assertIn('Model training and inference', sections)
        self.assertIn('Event streaming', sections)
        self.assertIn('Cross-platform development', sections)
    
    def test_validate_technical_content_complete(self):
        """Test validation of complete technical content"""
        complete_content = """
        ## Technical Specification
        
        ### System Overview
        The system architecture follows a microservices pattern with clear component boundaries.
        
        ### Architectural Drivers
        #### Goals
        - High performance with sub-100ms response times
        - Scalability to handle 10,000 concurrent users
        
        #### Constraints
        - Must integrate with existing legacy systems
        
        ### High-Level Architecture
        The architecture consists of multiple services communicating via REST APIs.
        
        ### Data Architecture and Models
        PostgreSQL database with normalized schema design for optimal performance.
        
        ### Component Blueprint & Class Diagram
        Modular component design with clear interfaces and dependency injection.
        
        ### User Interface / User Experience Key Requirements
        Responsive web interface with accessibility compliance.
        
        ### Security and RBAC
        JWT-based authentication with role-based authorization system.
        
        ### DevOps Requirements
        CI/CD pipeline with automated testing and deployment to Kubernetes.
        """
        
        validation = self.generator._validate_technical_content(complete_content)
        
        self.assertGreater(validation['score'], 0.8)
        self.assertEqual(len(validation['missing_sections']), 0)
        self.assertGreater(validation['completeness_score'], 0.9)
        self.assertGreater(validation['technical_depth_score'], 0.5)
    
    def test_validate_technical_content_incomplete(self):
        """Test validation of incomplete technical content"""
        incomplete_content = """
        ## Technical Specification
        
        ### System Overview
        Basic system description.
        
        ### Security and RBAC
        Some security measures.
        """
        
        validation = self.generator._validate_technical_content(incomplete_content)
        
        self.assertLess(validation['score'], 0.5)
        self.assertGreater(len(validation['missing_sections']), 0)
        self.assertLess(validation['completeness_score'], 0.5)
    
    def test_generate_success(self):
        """Test successful technical specification generation"""
        # Mock successful AI response
        mock_response = AIResponse(
            request_id="test-123",
            success=True,
            content="""
            ## Technical Specification
            
            ### System Overview
            Comprehensive system architecture with microservices pattern.
            
            ### Architectural Drivers
            #### Goals
            - Performance: Sub-100ms response times
            - Scalability: 10,000 concurrent users
            
            ### High-Level Architecture
            Distributed architecture with API gateway and service mesh.
            
            ### Data Architecture and Models
            PostgreSQL with Redis caching layer for optimal performance.
            
            ### Component Blueprint & Class Diagram
            Modular design with clear component boundaries and interfaces.
            
            ### User Interface / User Experience Key Requirements
            React-based SPA with responsive design and accessibility.
            
            ### Security and RBAC
            OAuth 2.0 with JWT tokens and role-based access control.
            
            ### DevOps Requirements
            Kubernetes deployment with CI/CD pipeline and monitoring.
            """,
            model_used="claude-sonnet-3.5",
            provider="model_garden",
            processing_time=15.2,
            tokens_used=2500,
            cost_estimate=0.075
        )
        
        self.mock_ai_broker.submit_request_sync.return_value = mock_response
        
        result = self.generator.generate(self.sample_context)
        
        self.assertTrue(result.success)
        self.assertEqual(result.stage, GenerationStage.TECHNICAL_SPEC)
        self.assertIn("Technical Specification", result.content)
        self.assertEqual(result.model_used, "claude-sonnet-3.5")
        self.assertGreater(result.metadata['validation_score'], 0.8)
        self.assertEqual(len(result.metadata['missing_sections']), 0)
    
    def test_generate_ai_failure(self):
        """Test handling of AI generation failure"""
        # Mock failed AI response
        mock_response = AIResponse(
            request_id="test-123",
            success=False,
            content="",
            model_used="",
            provider="",
            processing_time=5.0,
            tokens_used=0,
            cost_estimate=0.0,
            error_message="Model timeout"
        )
        
        self.mock_ai_broker.submit_request_sync.return_value = mock_response
        
        result = self.generator.generate(self.sample_context)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Model timeout")
        self.assertEqual(result.content, "")
    
    def test_generate_no_ai_broker(self):
        """Test handling when AI broker is not available"""
        self.generator.ai_broker = None
        
        result = self.generator.generate(self.sample_context)
        
        self.assertFalse(result.success)
        self.assertIn("AI Broker not available", result.error_message)
    
    def test_generate_exception_handling(self):
        """Test exception handling during generation"""
        # Mock AI broker to raise exception
        self.mock_ai_broker.submit_request_sync.side_effect = Exception("Network error")
        
        result = self.generator.generate(self.sample_context)
        
        self.assertFalse(result.success)
        self.assertIn("Network error", result.error_message)
        self.assertGreater(result.processing_time, 0)
    
    def test_required_sections_completeness(self):
        """Test that all required sections are defined"""
        expected_sections = [
            'system_overview',
            'architectural_drivers', 
            'high_level_architecture',
            'data_architecture',
            'component_blueprint',
            'ui_ux_requirements',
            'security_rbac',
            'devops_requirements'
        ]
        
        self.assertEqual(self.generator.required_sections, expected_sections)
    
    def test_technical_keywords_coverage(self):
        """Test that technical keywords cover key areas"""
        expected_keywords = [
            'architecture', 'component', 'service', 'database', 'api',
            'security', 'performance', 'scalability', 'deployment'
        ]
        
        for keyword in expected_keywords:
            self.assertIn(keyword, self.generator.technical_keywords)


class TestTechnicalSpecGeneratorIntegration(unittest.TestCase):
    """Integration tests for TechnicalSpecGenerator"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.generator = TechnicalSpecGenerator()
    
    @patch('src.services.prd_generation_orchestrator.get_ai_broker')
    def test_full_generation_workflow(self, mock_get_ai_broker):
        """Test complete generation workflow with mocked AI broker"""
        # Mock AI broker
        mock_broker = Mock()
        mock_get_ai_broker.return_value = mock_broker
        
        # Mock successful response
        mock_response = AIResponse(
            request_id="integration-test",
            success=True,
            content="""
            ## Technical Specification
            
            ### System Overview
            The system implements a modern microservices architecture designed for scalability and maintainability.
            
            ### Architectural Drivers
            #### Goals
            - Achieve 99.9% uptime with automatic failover capabilities
            - Support horizontal scaling to handle 50,000+ concurrent users
            - Maintain sub-200ms API response times under normal load
            
            #### Constraints
            - Must integrate with existing legacy authentication system
            - Limited to current cloud infrastructure budget
            
            ### High-Level Architecture
            The architecture follows a distributed microservices pattern with API gateway, service mesh, and event-driven communication.
            
            ### Data Architecture and Models
            Multi-database approach with PostgreSQL for transactional data, Redis for caching, and Elasticsearch for search functionality.
            
            ### Component Blueprint & Class Diagram
            Service-oriented architecture with clear domain boundaries and standardized communication protocols.
            
            ### User Interface / User Experience Key Requirements
            Progressive web application with offline capabilities and WCAG 2.1 AA accessibility compliance.
            
            ### Security and RBAC
            Zero-trust security model with OAuth 2.0, JWT tokens, and fine-grained role-based access control.
            
            ### DevOps Requirements
            GitOps-based CI/CD with Kubernetes deployment, comprehensive monitoring, and automated rollback capabilities.
            """,
            model_used="claude-opus-4",
            provider="model_garden",
            processing_time=22.5,
            tokens_used=3200,
            cost_estimate=0.48
        )
        
        mock_broker.submit_request_sync.return_value = mock_response
        self.generator.ai_broker = mock_broker
        
        # Test context
        context = {
            'upload_data': {
                'files': [
                    {
                        'name': 'microservice_architecture.py',
                        'analysis': 'Microservice implementation with FastAPI and async processing'
                    },
                    {
                        'name': 'kubernetes_config.yaml',
                        'analysis': 'Kubernetes deployment configuration with service mesh'
                    }
                ]
            },
            'template': {'sections': ['technical_spec']},
            'previous_outputs': {
                GenerationStage.PRODUCT_SPEC: """
                Advanced project management platform with real-time collaboration,
                AI-powered insights, and enterprise-grade security requirements.
                Supports distributed teams with microservices architecture.
                """
            }
        }
        
        # Execute generation
        result = self.generator.generate(context)
        
        # Verify results
        self.assertTrue(result.success)
        self.assertEqual(result.stage, GenerationStage.TECHNICAL_SPEC)
        self.assertIn("microservices architecture", result.content)
        self.assertIn("Security and RBAC", result.content)
        self.assertEqual(result.model_used, "claude-opus-4")
        
        # Verify validation metadata
        self.assertIn('validation_score', result.metadata)
        self.assertIn('technical_complexity', result.metadata)
        self.assertGreater(result.metadata['validation_score'], 0.8)
        
        # Verify AI request was made correctly
        mock_broker.submit_request_sync.assert_called_once()
        call_args = mock_broker.submit_request_sync.call_args[0][0]
        self.assertIn("microservices", call_args.instruction)
        self.assertIn("Technical Specification", call_args.instruction)


if __name__ == '__main__':
    unittest.main()