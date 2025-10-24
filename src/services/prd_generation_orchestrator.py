"""
Enhanced PRD Generation Orchestrator - Multi-stage PRD generation pipeline
Coordinates comprehensive PRD generation using template-driven, multi-stage approach
"""

import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Handle both relative and absolute imports
try:
    from .ai_broker import get_ai_broker, AIRequest, TaskType, Priority
    from .template_loader import TemplateLoader
    from ..models import PRD, db
except ImportError:
    try:
        from services.ai_broker import get_ai_broker, AIRequest, TaskType, Priority
        from services.template_loader import TemplateLoader
        from models import PRD, db
    except ImportError:
        # For testing without full app context
        def get_ai_broker():
            return None
        
        class AIRequest:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        class TaskType:
            DOCUMENTATION = "documentation"
            ARCHITECTURE = "architecture"
            PLANNING = "planning"
        
        class Priority:
            NORMAL = "normal"
        
        from template_loader import TemplateLoader
        
        # Mock PRD and db for testing
        class PRD:
            @classmethod
            def create_draft(cls, **kwargs):
                class MockPRD:
                    def __init__(self):
                        self.id = "mock-prd-id"
                return MockPRD()
        
        class db:
            pass

logger = logging.getLogger(__name__)


class GenerationStage(Enum):
    """PRD generation stages"""
    PRODUCT_SPEC = "product_spec"
    TECHNICAL_SPEC = "technical_spec"
    DIAGRAMS = "diagrams"
    IMPLEMENTATION_PLAN = "implementation_plan"


@dataclass
class GenerationConfig:
    """Configuration for PRD generation stages and dependencies"""
    stages: List[GenerationStage] = field(default_factory=lambda: [
        GenerationStage.PRODUCT_SPEC,
        GenerationStage.TECHNICAL_SPEC,
        GenerationStage.DIAGRAMS,
        GenerationStage.IMPLEMENTATION_PLAN
    ])
    stage_dependencies: Dict[GenerationStage, List[GenerationStage]] = field(default_factory=lambda: {
        GenerationStage.PRODUCT_SPEC: [],
        GenerationStage.TECHNICAL_SPEC: [GenerationStage.PRODUCT_SPEC],
        GenerationStage.DIAGRAMS: [GenerationStage.TECHNICAL_SPEC],
        GenerationStage.IMPLEMENTATION_PLAN: [GenerationStage.TECHNICAL_SPEC, GenerationStage.DIAGRAMS]
    })
    max_retries: int = 3
    timeout_seconds: float = 300.0
    fallback_enabled: bool = True


@dataclass
class GenerationResult:
    """Result from a generation stage"""
    stage: GenerationStage
    success: bool
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    processing_time: float = 0.0
    model_used: Optional[str] = None


class PRDGenerationOrchestrator:
    """
    Orchestrates multi-stage PRD generation using comprehensive template system
    
    This class coordinates the generation of comprehensive PRDs by breaking down
    the task into focused stages, each handled by specialized generators.
    """
    
    def __init__(self, config: Optional[GenerationConfig] = None):
        self.config = config or GenerationConfig()
        self.template_loader = TemplateLoader()
        self.ai_broker = get_ai_broker()
        
        # Initialize stage generators
        self.stage_generators = {
            GenerationStage.PRODUCT_SPEC: ProductSpecGenerator(),
            GenerationStage.TECHNICAL_SPEC: TechnicalSpecGenerator(),
            GenerationStage.DIAGRAMS: DiagramGenerator(),
            GenerationStage.IMPLEMENTATION_PLAN: ImplementationPlanGenerator()
        }
        
        logger.info("PRD Generation Orchestrator initialized")
    
    def generate_comprehensive_prd(self, upload_data: Dict[str, Any], 
                                 session_id: str,
                                 conversation_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point for comprehensive PRD generation
        
        Args:
            upload_data: Data from uploaded files and analysis
            session_id: Session identifier for tracking
            conversation_context: Optional conversation history for context
            
        Returns:
            Dict containing generated PRD content and metadata
        """
        try:
            logger.info(f"Starting comprehensive PRD generation for session {session_id}")
            
            # Load and validate template
            template = self.template_loader.load_comprehensive_template()
            if not template:
                raise Exception("Failed to load comprehensive PRD template")
            
            # Execute generation pipeline
            results = self._execute_generation_pipeline(upload_data, template, conversation_context)
            
            # Combine results into final PRD
            final_prd = self._combine_results(results, template)
            
            # Store PRD in database
            prd_record = self._store_prd(final_prd, upload_data, session_id, results)
            
            return {
                'success': True,
                'prd_content': final_prd['content'],
                'prd_id': str(prd_record.id),
                'session_id': session_id,
                'generation_metadata': {
                    'stages_completed': [r.stage.value for r in results if r.success],
                    'total_processing_time': sum(r.processing_time for r in results),
                    'models_used': list(set(r.model_used for r in results if r.model_used)),
                    'template_version': template.get('version', '1.0'),
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"PRD generation failed for session {session_id}: {e}")
            
            if self.config.fallback_enabled:
                return self._generate_fallback_prd(upload_data, session_id, str(e))
            else:
                return {
                    'success': False,
                    'error': f'PRD generation failed: {str(e)}',
                    'session_id': session_id
                }
    
    def _execute_generation_pipeline(self, upload_data: Dict[str, Any], 
                                   template: Dict[str, Any],
                                   conversation_context: Optional[str] = None) -> List[GenerationResult]:
        """
        Execute the multi-stage generation pipeline
        
        Args:
            upload_data: Input data for generation
            template: Loaded PRD template
            conversation_context: Optional conversation history
            
        Returns:
            List of generation results from each stage
        """
        results = []
        stage_outputs = {}  # Store outputs for dependent stages
        
        for stage in self.config.stages:
            try:
                # Check dependencies
                dependencies_met = self._check_stage_dependencies(stage, results)
                if not dependencies_met:
                    logger.warning(f"Dependencies not met for stage {stage.value}, skipping")
                    continue
                
                # Get generator for this stage
                generator = self.stage_generators.get(stage)
                if not generator:
                    logger.error(f"No generator found for stage {stage.value}")
                    continue
                
                # Prepare context for this stage
                stage_context = {
                    'upload_data': upload_data,
                    'template': template,
                    'conversation_context': conversation_context,
                    'previous_outputs': stage_outputs
                }
                
                # Execute stage generation
                logger.info(f"Executing generation stage: {stage.value}")
                result = generator.generate(stage_context)
                results.append(result)
                
                # Store output for dependent stages
                if result.success:
                    stage_outputs[stage] = result.content
                    logger.info(f"Stage {stage.value} completed successfully")
                else:
                    logger.warning(f"Stage {stage.value} failed: {result.error_message}")
                
            except Exception as e:
                logger.error(f"Error in stage {stage.value}: {e}")
                results.append(GenerationResult(
                    stage=stage,
                    success=False,
                    content="",
                    error_message=str(e)
                ))
        
        return results
    
    def _check_stage_dependencies(self, stage: GenerationStage, 
                                results: List[GenerationResult]) -> bool:
        """Check if dependencies for a stage are satisfied"""
        dependencies = self.config.stage_dependencies.get(stage, [])
        if not dependencies:
            return True
        
        completed_stages = {r.stage for r in results if r.success}
        return all(dep in completed_stages for dep in dependencies)
    
    def _combine_results(self, results: List[GenerationResult], 
                        template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine results from all stages into final PRD
        
        Args:
            results: Results from generation stages
            template: Original template structure
            
        Returns:
            Combined PRD content
        """
        combined_content = []
        metadata = {
            'generation_stages': {},
            'template_sections': template.get('sections', [])
        }
        
        # Process results in order
        for result in results:
            if result.success and result.content:
                combined_content.append(f"<!-- Generated by {result.stage.value} -->")
                combined_content.append(result.content)
                combined_content.append("")  # Add spacing
                
                # Store metadata
                metadata['generation_stages'][result.stage.value] = {
                    'success': True,
                    'processing_time': result.processing_time,
                    'model_used': result.model_used,
                    'content_length': len(result.content)
                }
            else:
                # Add placeholder for failed stages
                placeholder = self._generate_stage_placeholder(result.stage, template)
                combined_content.append(placeholder)
                
                metadata['generation_stages'][result.stage.value] = {
                    'success': False,
                    'error': result.error_message,
                    'placeholder_added': True
                }
        
        return {
            'content': '\n'.join(combined_content),
            'metadata': metadata
        }
    
    def _generate_stage_placeholder(self, stage: GenerationStage, 
                                  template: Dict[str, Any]) -> str:
        """Generate placeholder content for failed stages"""
        placeholders = {
            GenerationStage.PRODUCT_SPEC: """
## Product Specification

### Introduction & Vision
*This section can be enhanced using the AI chat feature. Click to generate comprehensive introduction and vision statement.*

### Target Audience & User Personas
*This section can be enhanced using the AI chat feature. Click to generate detailed user personas.*

### User Stories / Use Cases
*This section can be enhanced using the AI chat feature. Click to generate specific user stories.*

### Functional Requirements
*This section can be enhanced using the AI chat feature. Click to generate detailed functional requirements.*
""",
            GenerationStage.TECHNICAL_SPEC: """
## Technical Specification

### System Overview
*This section can be enhanced using the AI chat feature. Click to generate technical architecture overview.*

### High-Level Architecture
*This section can be enhanced using the AI chat feature. Click to generate system architecture description.*
""",
            GenerationStage.DIAGRAMS: """
### Architecture Diagrams

#### Components Diagram
```mermaid
%% This diagram can be generated using the AI chat feature
flowchart TD
    A[Component A] --> B[Component B]
    B --> C[Component C]
```

#### Entity Relationship Diagram
```mermaid
%% This diagram can be generated using the AI chat feature
erDiagram
    USERS ||--o{ PROJECTS : owns
    PROJECTS ||--o{ DOCUMENTS : contains
```
""",
            GenerationStage.IMPLEMENTATION_PLAN: """
## Implementation Plan

### Phase 1: Foundation
*This section can be enhanced using the AI chat feature. Click to generate detailed implementation phases.*

### Phase 2: Core Features
*This section can be enhanced using the AI chat feature. Click to generate specific implementation tasks.*
"""
        }
        
        return placeholders.get(stage, f"*{stage.value} content can be generated using the AI chat feature.*")
    
    def _store_prd(self, final_prd: Dict[str, Any], upload_data: Dict[str, Any], 
                  session_id: str, results: List[GenerationResult]) -> PRD:
        """Store generated PRD in database"""
        try:
            # Extract project ID from upload data
            project_id = upload_data.get('project_id', 'default-project')
            
            # Create sources list from upload data
            sources = []
            if 'files' in upload_data:
                sources = [f['name'] for f in upload_data['files'] if 'name' in f]
            
            # Create JSON summary from metadata
            # Derive block document v1 from final markdown for persistence (lazy import to avoid circular)
            blocks_v1 = []
            try:
                from ..api.prd_editor import convert_markdown_to_editorjs, editorjs_to_blocks_v1  # type: ignore
            except Exception:
                try:
                    from api.prd_editor import convert_markdown_to_editorjs, editorjs_to_blocks_v1  # type: ignore
                except Exception:
                    convert_markdown_to_editorjs = None
                    editorjs_to_blocks_v1 = None
            try:
                if convert_markdown_to_editorjs and editorjs_to_blocks_v1:
                    ej = convert_markdown_to_editorjs(final_prd['content'])
                    blocks_v1 = editorjs_to_blocks_v1(ej)
            except Exception:
                blocks_v1 = []

            json_summary = {
                'generation_metadata': final_prd['metadata'],
                'sources': sources,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'block_document': {'meta': {'version': 'v1'}, 'blocks': blocks_v1}
            }
            
            # Create PRD record
            prd = PRD.create_draft(
                project_id=project_id,
                draft_id=session_id,
                md_content=final_prd['content'],
                json_summary=json_summary,
                sources=sources,
                created_by='prd_generation_orchestrator'
            )
            
            logger.info(f"Stored PRD {prd.id} for session {session_id}")
            return prd
            
        except Exception as e:
            logger.error(f"Failed to store PRD: {e}")
            raise
    
    def _generate_fallback_prd(self, upload_data: Dict[str, Any], 
                             session_id: str, error_message: str) -> Dict[str, Any]:
        """Generate basic fallback PRD when main generation fails"""
        try:
            template = self.template_loader.load_comprehensive_template()
            
            fallback_content = f"""# Product Requirements Document

## Generation Notice
This PRD was generated using fallback mode due to an error in the main generation pipeline.
Error: {error_message}

## Product Specification

### Introduction & Vision
*This section can be enhanced using the AI chat feature to generate comprehensive content based on your uploaded files.*

### Target Audience & User Personas
*This section can be enhanced using the AI chat feature to generate detailed user personas.*

### User Stories / Use Cases
*This section can be enhanced using the AI chat feature to generate specific user stories and use cases.*

### Functional Requirements
*This section can be enhanced using the AI chat feature to generate detailed functional requirements.*

## Technical Specification

### System Overview
*This section can be enhanced using the AI chat feature to generate technical architecture overview.*

### High-Level Architecture
*This section can be enhanced using the AI chat feature to generate system architecture description.*

## Implementation Plan
*This section can be enhanced using the AI chat feature to generate phased implementation approach.*

---
*Generated in fallback mode. Use the chat interface to enhance any section with AI-generated content.*
"""
            
            # Store fallback PRD
            project_id = upload_data.get('project_id', 'default-project')
            sources = [f['name'] for f in upload_data.get('files', []) if 'name' in f]
            
            # Persist blocks derived from fallback markdown for consistency (lazy import)
            blocks_v1 = []
            try:
                from ..api.prd_editor import convert_markdown_to_editorjs, editorjs_to_blocks_v1  # type: ignore
            except Exception:
                try:
                    from api.prd_editor import convert_markdown_to_editorjs, editorjs_to_blocks_v1  # type: ignore
                except Exception:
                    convert_markdown_to_editorjs = None
                    editorjs_to_blocks_v1 = None
            try:
                if convert_markdown_to_editorjs and editorjs_to_blocks_v1:
                    ej = convert_markdown_to_editorjs(fallback_content)
                    blocks_v1 = editorjs_to_blocks_v1(ej)
            except Exception:
                blocks_v1 = []

            prd = PRD.create_draft(
                project_id=project_id,
                draft_id=session_id,
                md_content=fallback_content,
                json_summary={'fallback': True, 'error': error_message, 'block_document': {'meta': {'version': 'v1'}, 'blocks': blocks_v1}},
                sources=sources,
                created_by='prd_generation_orchestrator_fallback'
            )
            
            return {
                'success': True,
                'prd_content': fallback_content,
                'prd_id': str(prd.id),
                'session_id': session_id,
                'fallback': True,
                'error': error_message
            }
            
        except Exception as e:
            logger.error(f"Fallback PRD generation failed: {e}")
            return {
                'success': False,
                'error': f'Both main and fallback PRD generation failed: {str(e)}',
                'session_id': session_id
            }


class BaseStageGenerator:
    """Base class for stage-specific generators"""
    
    def __init__(self):
        self.ai_broker = get_ai_broker()
    
    def generate(self, context: Dict[str, Any]) -> GenerationResult:
        """Generate content for this stage"""
        raise NotImplementedError("Subclasses must implement generate method")
    
    def _create_ai_request(self, instruction: str, task_type: TaskType = TaskType.DOCUMENTATION,
                          priority: Priority = Priority.NORMAL) -> AIRequest:
        """Create AI request with common settings"""
        return AIRequest(
            request_id=f"prd_gen_{task_type.value}_{datetime.now().timestamp()}",
            task_type=task_type,
            instruction=instruction,
            priority=priority,
            max_tokens=4000,
            timeout_seconds=300.0,
            retry_attempts=3
        )


class ProductSpecGenerator(BaseStageGenerator):
    """Generates product specification sections"""
    
    def generate(self, context: Dict[str, Any]) -> GenerationResult:
        """Generate product specification content"""
        start_time = datetime.now()
        
        try:
            upload_data = context['upload_data']
            template = context['template']
            conversation_context = context.get('conversation_context', '')
            
            # Build product spec prompt
            prompt = self._build_product_spec_prompt(upload_data, template, conversation_context)
            
            # Create AI request
            ai_request = self._create_ai_request(prompt, TaskType.DOCUMENTATION)
            
            # Execute request
            if self.ai_broker:
                response = self.ai_broker.submit_request_sync(ai_request)
                
                if response.success:
                    processing_time = (datetime.now() - start_time).total_seconds()
                    return GenerationResult(
                        stage=GenerationStage.PRODUCT_SPEC,
                        success=True,
                        content=response.content,
                        processing_time=processing_time,
                        model_used=response.model_used,
                        metadata={'tokens_used': response.tokens_used}
                    )
                else:
                    return GenerationResult(
                        stage=GenerationStage.PRODUCT_SPEC,
                        success=False,
                        content="",
                        error_message=response.error_message,
                        processing_time=(datetime.now() - start_time).total_seconds()
                    )
            else:
                raise Exception("AI Broker not available")
                
        except Exception as e:
            return GenerationResult(
                stage=GenerationStage.PRODUCT_SPEC,
                success=False,
                content="",
                error_message=str(e),
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _build_product_spec_prompt(self, upload_data: Dict[str, Any], 
                                 template: Dict[str, Any], 
                                 conversation_context: str) -> str:
        """Build prompt for product specification generation"""
        
        # Extract file information
        file_info = ""
        if 'files' in upload_data:
            file_descriptions = []
            for file_data in upload_data['files']:
                if 'analysis' in file_data:
                    file_descriptions.append(f"- {file_data['name']}: {file_data['analysis']}")
            file_info = '\n'.join(file_descriptions)
        
        prompt = f"""Generate an extremely comprehensive Product Specification for a PRD that matches enterprise-level documentation standards. This should be as detailed and professional as documents used by major tech companies.

UPLOADED FILES ANALYSIS:
{file_info}

CONVERSATION CONTEXT:
{conversation_context}

Generate the following Product Specification sections with exhaustive detail:

## Product Specification

### Introduction & Vision
Generate 5-6 detailed paragraphs covering:
- **Problem Statement**: What specific business/user problem does this solve? Include market research data or pain points from uploaded files
- **Solution Overview**: How does your product uniquely address this problem?
- **Vision Statement**: Where do you see this product in 2-3 years?
- **Market Opportunity**: Size of addressable market, competitive landscape
- **Core Value Proposition**: What makes this product essential?
- **Success Definition**: What does success look like quantifiably?

### Target Audience & User Personas
Generate 6-8 comprehensive user personas with:
- **Primary Personas** (3-4): Main target users
- **Secondary Personas** (2-3): Important but not primary users  
- **Anti-Personas** (1-2): Who this product is NOT for

For each persona include:
- Demographics (age, role, company size, location)
- Behavioral patterns and technology comfort level
- Pain points and frustrations (minimum 4 per persona)
- Goals and motivations (minimum 5 per persona)  
- Preferred communication channels
- Budget authority and decision-making process
- Day-in-the-life scenarios
- Success metrics they care about

### User Journey Mapping
Generate detailed user journeys showing:
- **Awareness Stage**: How users discover the need
- **Consideration Stage**: How they evaluate solutions
- **Purchase/Adoption Stage**: Decision and onboarding process
- **Usage Stage**: Daily/weekly interaction patterns
- **Advocacy Stage**: How they become champions

### User Stories & Use Cases
Generate 25-30 detailed user stories organized by:
- **Core Workflow Stories** (8-10 stories)
- **Administrative Stories** (5-7 stories)
- **Integration Stories** (4-6 stories)
- **Mobile/Accessibility Stories** (3-5 stories)
- **Advanced Feature Stories** (5-7 stories)

Format: "As a [specific persona], I want to [specific action] so that [business outcome with metrics]"
Include acceptance criteria for each story.

### Functional Requirements
Generate 8-10 major functional requirement categories:
- **Core Features** (the must-haves)
- **User Management & Authentication**
- **Data Management & Storage**
- **Integration Capabilities**
- **Reporting & Analytics**
- **Mobile/Cross-platform Support**
- **Search & Discovery**
- **Collaboration Features**
- **Automation & Workflow**
- **Customization & Configuration**

For each category provide:
- Overview description
- 5-8 specific sub-requirements
- Business justification
- Priority level (P0, P1, P2)
- Dependencies on other requirements
- Acceptance criteria with measurable outcomes

### Non-Functional Requirements

#### Performance & Scalability
- Page load times: specific targets (e.g., <2s for 95% of requests)
- Concurrent user capacity with degradation curves
- Data processing throughput requirements
- API response time SLAs
- Database query performance benchmarks
- Caching strategy requirements

#### Reliability & Availability
- Uptime targets (99.9%, 99.99%, etc.)
- Mean Time To Recovery (MTTR) requirements
- Disaster recovery objectives (RTO, RPO)
- Backup and data retention policies
- Error handling and graceful degradation
- Monitoring and alerting requirements

#### Security & Compliance
- Authentication mechanisms (SSO, 2FA, etc.)
- Authorization and role-based access control
- Data encryption requirements (at rest, in transit)
- Compliance requirements (GDPR, SOC2, HIPAA, etc.)
- Penetration testing requirements
- Data privacy and retention policies
- Audit logging requirements

#### Usability & Accessibility
- Accessibility compliance (WCAG 2.1 AA)
- Cross-browser compatibility matrix
- Mobile responsiveness requirements
- Internationalization and localization needs
- User onboarding completion rates
- Help documentation and training requirements

#### Compatibility & Integration
- Browser support matrix
- Mobile platform requirements
- API versioning strategy
- Third-party integration requirements
- Data import/export capabilities
- Legacy system compatibility

### Success Metrics & KPIs
Generate 12-15 specific, measurable success metrics:

#### User Adoption Metrics
- User activation rate within first 7 days
- Monthly active users (MAU) growth targets
- Feature adoption rates by user segment
- User retention curves (Day 1, 7, 30, 90)

#### Business Impact Metrics  
- Revenue impact or cost savings
- Operational efficiency improvements
- Customer satisfaction scores
- Market share or competitive positioning
- Time-to-value for new users

#### Technical Performance Metrics
- System availability and uptime
- Performance benchmarks achievement
- Security incident frequency
- Data accuracy and integrity metrics

Each metric should include:
- Baseline current state
- Target values with timelines
- Measurement methodology
- Responsibility for tracking

### Assumptions & Dependencies
Document critical assumptions and external dependencies:
- Technology stack assumptions
- Resource availability (team, budget, timeline)
- External system dependencies
- Market condition assumptions
- User behavior assumptions

### Risk Assessment
Identify and document key risks:
- Technical risks and mitigation strategies
- Market/competitive risks
- Resource/timeline risks
- Compliance/regulatory risks

CRITICAL REQUIREMENTS:
- Generate enterprise-level detail that could be presented to executive stakeholders
- Include specific metrics, numbers, and measurable criteria throughout
- Reference information from uploaded files wherever possible
- Ensure each section is comprehensive enough to guide development teams
- Use professional business language while remaining clear and actionable
- Include quantitative targets and success criteria
- Make it comprehensive enough to serve as the single source of truth for product development

Generate the complete, exhaustive Product Specification now:"""
        
        return prompt


class TechnicalSpecGenerator(BaseStageGenerator):
    """
    Generates technical specification sections with enhanced prompt engineering
    and validation for technical content completeness and accuracy
    """
    
    def __init__(self):
        super().__init__()
        self.required_sections = [
            'system_overview',
            'architectural_drivers', 
            'high_level_architecture',
            'data_architecture',
            'component_blueprint',
            'ui_ux_requirements',
            'security_rbac',
            'devops_requirements'
        ]
        self.technical_keywords = [
            'architecture', 'component', 'service', 'database', 'api',
            'security', 'performance', 'scalability', 'deployment'
        ]
    
    def generate(self, context: Dict[str, Any]) -> GenerationResult:
        """Generate technical specification content with enhanced validation"""
        start_time = datetime.now()
        
        try:
            upload_data = context['upload_data']
            template = context['template']
            previous_outputs = context.get('previous_outputs', {})
            
            # Get product spec context if available
            product_spec_content = previous_outputs.get(GenerationStage.PRODUCT_SPEC, '')
            
            # Analyze technical complexity from product spec
            technical_complexity = self._analyze_technical_complexity(product_spec_content, upload_data)
            
            # Build enhanced technical spec prompt
            prompt = self._build_enhanced_technical_spec_prompt(
                upload_data, template, product_spec_content, technical_complexity
            )
            
            # Create AI request with appropriate model selection
            ai_request = self._create_ai_request(prompt, TaskType.ARCHITECTURE)
            
            # Execute request
            if self.ai_broker:
                response = self.ai_broker.submit_request_sync(ai_request)
                
                if response.success:
                    # Validate technical content completeness
                    validation_result = self._validate_technical_content(response.content)
                    
                    processing_time = (datetime.now() - start_time).total_seconds()
                    return GenerationResult(
                        stage=GenerationStage.TECHNICAL_SPEC,
                        success=True,
                        content=response.content,
                        processing_time=processing_time,
                        model_used=response.model_used,
                        metadata={
                            'tokens_used': response.tokens_used,
                            'validation_score': validation_result['score'],
                            'missing_sections': validation_result['missing_sections'],
                            'technical_complexity': technical_complexity
                        }
                    )
                else:
                    return GenerationResult(
                        stage=GenerationStage.TECHNICAL_SPEC,
                        success=False,
                        content="",
                        error_message=response.error_message,
                        processing_time=(datetime.now() - start_time).total_seconds()
                    )
            else:
                raise Exception("AI Broker not available")
                
        except Exception as e:
            return GenerationResult(
                stage=GenerationStage.TECHNICAL_SPEC,
                success=False,
                content="",
                error_message=str(e),
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _analyze_technical_complexity(self, product_spec_content: str, 
                                    upload_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze technical complexity from product specification and uploaded files"""
        complexity = {
            'level': 'medium',  # low, medium, high
            'domains': [],
            'technologies': [],
            'integrations': [],
            'scale_indicators': []
        }
        
        content_lower = product_spec_content.lower()
        
        # Analyze complexity indicators
        if any(keyword in content_lower for keyword in ['microservice', 'distributed', 'cloud', 'kubernetes']):
            complexity['level'] = 'high'
            complexity['domains'].append('distributed_systems')
        
        if any(keyword in content_lower for keyword in ['ai', 'machine learning', 'ml', 'neural']):
            complexity['domains'].append('ai_ml')
        
        if any(keyword in content_lower for keyword in ['real-time', 'streaming', 'websocket']):
            complexity['domains'].append('real_time')
        
        if any(keyword in content_lower for keyword in ['mobile', 'ios', 'android']):
            complexity['domains'].append('mobile')
        
        # Analyze file types for technology hints
        if 'files' in upload_data:
            for file_data in upload_data['files']:
                file_name = file_data.get('name', '').lower()
                if file_name.endswith(('.py', '.js', '.ts', '.java', '.go')):
                    if 'backend' not in complexity['technologies']:
                        complexity['technologies'].append('backend')
                elif file_name.endswith(('.html', '.css', '.jsx', '.vue')):
                    if 'frontend' not in complexity['technologies']:
                        complexity['technologies'].append('frontend')
                elif file_name.endswith(('.sql', '.db')):
                    if 'database' not in complexity['technologies']:
                        complexity['technologies'].append('database')
        
        return complexity
    
    def _build_enhanced_technical_spec_prompt(self, upload_data: Dict[str, Any], 
                                            template: Dict[str, Any], 
                                            product_spec_content: str,
                                            technical_complexity: Dict[str, Any]) -> str:
        """Build enhanced prompt for technical specification generation with complexity awareness"""
        
        # Extract file information with technical focus
        file_info = ""
        technical_files = []
        if 'files' in upload_data:
            for file_data in upload_data['files']:
                if 'analysis' in file_data:
                    file_info += f"- {file_data['name']}: {file_data['analysis']}\n"
                    # Identify technical files
                    file_name = file_data.get('name', '').lower()
                    if any(ext in file_name for ext in ['.py', '.js', '.ts', '.java', '.sql', '.yaml', '.json']):
                        technical_files.append(file_data)
        
        # Build complexity-aware technical guidance
        complexity_guidance = self._get_complexity_guidance(technical_complexity)
        
        # Build technology-specific sections
        tech_sections = self._get_technology_sections(technical_complexity)
        
        prompt = f"""Generate comprehensive Technical Specification sections for a PRD based on the product specification and uploaded files.

PRODUCT SPECIFICATION CONTEXT:
{product_spec_content[:2500]}

UPLOADED FILES ANALYSIS:
{file_info}

TECHNICAL COMPLEXITY ANALYSIS:
- Complexity Level: {technical_complexity['level']}
- Technical Domains: {', '.join(technical_complexity['domains'])}
- Technology Stack: {', '.join(technical_complexity['technologies'])}

{complexity_guidance}

Generate the following Technical Specification sections with detailed, architecture-focused content:

## Technical Specification

### System Overview
Generate 3-4 detailed paragraphs explaining:
- High-level system architecture and design philosophy
- Key technical components and their interactions
- Technology stack decisions and rationale
- System boundaries and external interfaces
- Performance and scalability considerations

### Architectural Drivers
#### Goals
Generate 6-8 specific technical goals including:
- Performance targets (response times, throughput)
- Scalability requirements (concurrent users, data volume)
- Reliability targets (uptime, error rates)
- Security objectives
- Maintainability and extensibility goals

#### Constraints
Generate technical constraints including:
- Technology limitations and dependencies
- Resource constraints (budget, timeline, team)
- Compliance and regulatory requirements
- Integration constraints with existing systems
- Performance and infrastructure limitations

### High-Level Architecture
Generate detailed architecture description including:
- System architecture pattern (monolithic, microservices, serverless)
- Component interaction patterns and communication protocols
- Data flow architecture and processing pipelines
- External system integrations and APIs
- Deployment architecture and infrastructure requirements

{tech_sections}

### Data Architecture and Models
Generate comprehensive data architecture including:
- Database design approach and technology choices
- Data modeling strategy (relational, document, graph)
- Data storage and retrieval patterns
- Data consistency and transaction requirements
- Data migration and versioning strategy
- Backup and disaster recovery approach

### Component Blueprint & Class Diagram
Generate detailed component architecture including:
- Modular system design and component boundaries
- Service interfaces and contracts
- Dependency management and injection patterns
- Component lifecycle and state management
- Inter-component communication patterns
- Error handling and fault tolerance strategies

### User Interface / User Experience Key Requirements
Generate detailed UI/UX technical specifications including:
- Frontend architecture and technology stack
- Responsive design and cross-platform requirements
- Accessibility compliance (WCAG 2.1 AA)
- Performance requirements (load times, interactions)
- Browser compatibility and progressive enhancement
- Offline capabilities and data synchronization

### Mathematical Specifications and Formulas
Generate performance formulas and calculations including:
- Capacity planning formulas
- Performance metrics calculations
- Resource utilization models
- Cost optimization equations
- Scaling algorithms and thresholds

### Security and RBAC
Generate comprehensive security architecture including:
- Authentication and authorization mechanisms
- Role-based access control (RBAC) design
- Data encryption (at rest and in transit)
- API security and rate limiting
- Security monitoring and incident response
- Compliance requirements (GDPR, SOC2, etc.)

### DevOps Requirements
Generate deployment and infrastructure requirements including:
- CI/CD pipeline design and automation
- Infrastructure as Code (IaC) approach
- Containerization and orchestration strategy
- Monitoring, logging, and observability
- Backup and disaster recovery procedures
- Environment management (dev, staging, prod)

### Implementation, Validation and Verification Strategy
Generate testing and validation approaches including:
- Testing strategy (unit, integration, e2e)
- Performance testing and load testing approach
- Security testing and vulnerability assessment
- Code quality and review processes
- Deployment validation and rollback procedures

CRITICAL REQUIREMENTS:
- Be extremely detailed and technically accurate
- Use specific information from the product specification and uploaded files
- Include concrete technical decisions with clear rationale
- Provide specific metrics, numbers, and measurable criteria
- Focus on implementation-ready technical details
- Ensure consistency with product requirements
- Include industry best practices and standards
- Generate substantial, comprehensive content for each section

Generate the complete Technical Specification now:"""
        
        return prompt
    
    def _get_complexity_guidance(self, technical_complexity: Dict[str, Any]) -> str:
        """Get complexity-specific guidance for technical specification"""
        level = technical_complexity['level']
        domains = technical_complexity['domains']
        
        guidance = "COMPLEXITY-SPECIFIC GUIDANCE:\n"
        
        if level == 'high':
            guidance += """- Focus on distributed system patterns and microservices architecture
- Include detailed service mesh and API gateway specifications
- Address data consistency and eventual consistency patterns
- Include comprehensive monitoring and observability requirements
- Detail container orchestration and cloud-native patterns"""
        elif level == 'medium':
            guidance += """- Balance between monolithic and modular architecture
- Include clear service boundaries and API specifications
- Address caching and performance optimization strategies
- Include standard monitoring and logging requirements
- Detail deployment automation and scaling strategies"""
        else:
            guidance += """- Focus on simple, maintainable architecture patterns
- Include clear component separation and interfaces
- Address basic performance and security requirements
- Include standard deployment and monitoring practices
- Detail straightforward scaling and maintenance approaches"""
        
        if 'ai_ml' in domains:
            guidance += "\n- Include ML model deployment and inference architecture"
            guidance += "\n- Address data pipeline and feature engineering requirements"
        
        if 'real_time' in domains:
            guidance += "\n- Include real-time data processing and streaming architecture"
            guidance += "\n- Address WebSocket and event-driven patterns"
        
        if 'mobile' in domains:
            guidance += "\n- Include mobile-specific architecture and offline capabilities"
            guidance += "\n- Address mobile API design and synchronization patterns"
        
        return guidance
    
    def _get_technology_sections(self, technical_complexity: Dict[str, Any]) -> str:
        """Get technology-specific sections based on complexity analysis"""
        sections = ""
        
        if 'ai_ml' in technical_complexity['domains']:
            sections += """
### AI/ML Architecture
Generate AI/ML specific architecture including:
- Model training and inference pipeline
- Feature engineering and data preprocessing
- Model versioning and deployment strategies
- A/B testing and model performance monitoring
- Data labeling and annotation workflows"""
        
        if 'real_time' in technical_complexity['domains']:
            sections += """
### Real-time Processing Architecture
Generate real-time processing specifications including:
- Event streaming and message queue architecture
- WebSocket connection management and scaling
- Real-time data processing pipelines
- Event sourcing and CQRS patterns
- Real-time monitoring and alerting systems"""
        
        if 'mobile' in technical_complexity['domains']:
            sections += """
### Mobile Architecture
Generate mobile-specific architecture including:
- Cross-platform development strategy
- Offline-first architecture and data synchronization
- Push notification and background processing
- Mobile security and device management
- App store deployment and update strategies"""
        
        return sections
    
    def _validate_technical_content(self, content: str) -> Dict[str, Any]:
        """Validate technical content completeness and accuracy"""
        validation_result = {
            'score': 0.0,
            'missing_sections': [],
            'technical_depth_score': 0.0,
            'completeness_score': 0.0
        }
        
        content_lower = content.lower()
        
        # Check for required sections
        section_scores = []
        for section in self.required_sections:
            section_keywords = {
                'system_overview': ['system', 'architecture', 'overview', 'components'],
                'architectural_drivers': ['goals', 'constraints', 'requirements'],
                'high_level_architecture': ['architecture', 'components', 'services'],
                'data_architecture': ['database', 'data', 'storage', 'model'],
                'component_blueprint': ['component', 'class', 'module', 'interface'],
                'ui_ux_requirements': ['ui', 'ux', 'interface', 'user experience'],
                'security_rbac': ['security', 'authentication', 'authorization', 'rbac'],
                'devops_requirements': ['devops', 'deployment', 'ci/cd', 'infrastructure']
            }
            
            keywords = section_keywords.get(section, [])
            if any(keyword in content_lower for keyword in keywords):
                section_scores.append(1.0)
            else:
                validation_result['missing_sections'].append(section)
                section_scores.append(0.0)
        
        validation_result['completeness_score'] = sum(section_scores) / len(section_scores)
        
        # Check technical depth
        technical_indicators = 0
        for keyword in self.technical_keywords:
            if keyword in content_lower:
                technical_indicators += content_lower.count(keyword)
        
        validation_result['technical_depth_score'] = min(1.0, technical_indicators / 20.0)
        
        # Overall score
        validation_result['score'] = (
            validation_result['completeness_score'] * 0.7 + 
            validation_result['technical_depth_score'] * 0.3
        )
        
        return validation_result


class DiagramGenerator(BaseStageGenerator):
    """Generates Mermaid diagrams for technical sections"""
    
    def generate(self, context: Dict[str, Any]) -> GenerationResult:
        """Generate diagram content"""
        start_time = datetime.now()
        
        try:
            upload_data = context['upload_data']
            previous_outputs = context.get('previous_outputs', {})
            
            # Get technical spec context if available
            technical_spec_content = previous_outputs.get(GenerationStage.TECHNICAL_SPEC, '')
            product_spec_content = previous_outputs.get(GenerationStage.PRODUCT_SPEC, '')
            
            # Build diagram generation prompt
            prompt = self._build_diagram_prompt(upload_data, technical_spec_content, product_spec_content)
            
            # Create AI request
            ai_request = self._create_ai_request(prompt, TaskType.ARCHITECTURE)
            
            # Execute request
            if self.ai_broker:
                response = self.ai_broker.submit_request_sync(ai_request)
                
                if response.success:
                    processing_time = (datetime.now() - start_time).total_seconds()
                    return GenerationResult(
                        stage=GenerationStage.DIAGRAMS,
                        success=True,
                        content=response.content,
                        processing_time=processing_time,
                        model_used=response.model_used,
                        metadata={'tokens_used': response.tokens_used}
                    )
                else:
                    return GenerationResult(
                        stage=GenerationStage.DIAGRAMS,
                        success=False,
                        content="",
                        error_message=response.error_message,
                        processing_time=(datetime.now() - start_time).total_seconds()
                    )
            else:
                raise Exception("AI Broker not available")
                
        except Exception as e:
            return GenerationResult(
                stage=GenerationStage.DIAGRAMS,
                success=False,
                content="",
                error_message=str(e),
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _build_diagram_prompt(self, upload_data: Dict[str, Any], 
                            technical_spec_content: str, 
                            product_spec_content: str) -> str:
        """Build prompt for diagram generation"""
        
        prompt = f"""Generate extremely comprehensive and professional Mermaid diagrams that match enterprise architecture documentation standards. These diagrams should be detailed enough for development teams to implement from.

TECHNICAL SPECIFICATION CONTEXT:
{technical_spec_content[:2500]}

PRODUCT SPECIFICATION CONTEXT:
{product_spec_content[:2000]}

ADDITIONAL CONTEXT:
{', '.join([f['name'] for f in upload_data.get('files', [])])}

Generate the following detailed Mermaid diagrams:

## Architecture Diagrams

### System Architecture Overview
```mermaid
flowchart TB
    %% External Actors and Systems
    User[👤 End Users<br/>Web/Mobile]
    Admin[👨‍💼 System Admin<br/>Dashboard]
    API_Consumer[🔗 API Consumers<br/>3rd Party Apps]
    
    %% Load Balancer and Gateway
    LB[🌐 Load Balancer<br/>nginx/ALB]
    Gateway[🚪 API Gateway<br/>Rate Limiting/Auth]
    
    %% Frontend Layer
    WebApp[💻 Web Application<br/>React/Vue/Angular]
    MobileApp[📱 Mobile Apps<br/>iOS/Android/PWA]
    AdminUI[⚙️ Admin Dashboard<br/>Management Interface]
    
    %% Application Services Layer
    AuthService[🔐 Authentication Service<br/>JWT/OAuth2]
    CoreAPI[⚡ Core API Service<br/>Business Logic]
    NotificationService[📧 Notification Service<br/>Email/Push/SMS]
    FileService[📁 File Storage Service<br/>Upload/Processing]
    AnalyticsService[📊 Analytics Service<br/>Metrics/Reporting]
    
    %% Data Processing Layer
    MessageQueue[📮 Message Queue<br/>Redis/RabbitMQ]
    BackgroundWorker[⚙️ Background Workers<br/>Async Processing]
    DataProcessor[🔄 Data Processing<br/>ETL/Transformations]
    
    %% Data Storage Layer
    MainDB[(🗃️ Primary Database<br/>PostgreSQL/MySQL)]
    CacheDB[(⚡ Cache Layer<br/>Redis/Memcached)]
    FileStorage[(📦 File Storage<br/>S3/MinIO)]
    SearchDB[(🔍 Search Engine<br/>Elasticsearch)]
    AnalyticsDB[(📈 Analytics DB<br/>ClickHouse/BigQuery)]
    
    %% External Services
    EmailProvider[📧 Email Service<br/>SendGrid/AWS SES]
    PaymentGateway[💳 Payment Gateway<br/>Stripe/PayPal]
    CloudProvider[☁️ Cloud Services<br/>AWS/GCP/Azure]
    
    %% Monitoring and Logging
    Monitoring[📊 Monitoring<br/>Prometheus/Grafana]
    Logging[📝 Logging<br/>ELK Stack/Fluentd]
    
    %% User Flow
    User --> LB
    Admin --> LB
    API_Consumer --> Gateway
    
    LB --> WebApp
    LB --> MobileApp
    LB --> AdminUI
    
    %% API Gateway Flow
    Gateway --> AuthService
    Gateway --> CoreAPI
    
    %% Application Service Interactions
    WebApp --> AuthService
    WebApp --> CoreAPI
    MobileApp --> AuthService
    MobileApp --> CoreAPI
    AdminUI --> CoreAPI
    
    CoreAPI --> NotificationService
    CoreAPI --> FileService
    CoreAPI --> AnalyticsService
    CoreAPI --> MessageQueue
    
    %% Background Processing
    MessageQueue --> BackgroundWorker
    BackgroundWorker --> DataProcessor
    BackgroundWorker --> NotificationService
    
    %% Data Layer Connections
    AuthService --> MainDB
    CoreAPI --> MainDB
    CoreAPI --> CacheDB
    FileService --> FileStorage
    AnalyticsService --> AnalyticsDB
    DataProcessor --> MainDB
    DataProcessor --> SearchDB
    
    %% External Service Connections
    NotificationService --> EmailProvider
    CoreAPI --> PaymentGateway
    FileStorage --> CloudProvider
    
    %% Monitoring Connections
    AuthService -.-> Monitoring
    CoreAPI -.-> Monitoring
    MainDB -.-> Monitoring
    
    AuthService -.-> Logging
    CoreAPI -.-> Logging
    BackgroundWorker -.-> Logging

    %% Styling
    classDef userClass fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef serviceClass fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef dataClass fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef externalClass fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class User,Admin,API_Consumer userClass
    class AuthService,CoreAPI,NotificationService,FileService,AnalyticsService,BackgroundWorker,DataProcessor serviceClass
    class MainDB,CacheDB,FileStorage,SearchDB,AnalyticsDB dataClass
    class EmailProvider,PaymentGateway,CloudProvider,Monitoring,Logging externalClass
```

### Detailed Component Interaction Diagram
```mermaid
flowchart LR
    %% Frontend Components
    subgraph "Frontend Layer"
        UI[User Interface<br/>- Login/Registration<br/>- Dashboard<br/>- Feature Modules]
        StateManager[State Management<br/>- Redux/Vuex<br/>- Local Storage<br/>- Session Management]
        HTTPClient[HTTP Client<br/>- Axios/Fetch<br/>- Request Interceptors<br/>- Error Handling]
    end
    
    %% API Layer
    subgraph "API Gateway & Services"
        Gateway[API Gateway<br/>- Authentication<br/>- Rate Limiting<br/>- Request Routing]
        
        subgraph "Microservices"
            UserService[User Service<br/>- User Management<br/>- Profile Updates<br/>- Preferences]
            AuthService[Auth Service<br/>- Login/Logout<br/>- Token Management<br/>- Password Reset]
            BusinessService[Business Logic Service<br/>- Core Features<br/>- Business Rules<br/>- Validations]
            NotificationService[Notification Service<br/>- Email Templates<br/>- Push Notifications<br/>- SMS Gateway]
            FileService[File Service<br/>- Upload/Download<br/>- File Processing<br/>- Metadata Management]
        end
    end
    
    %% Data Layer
    subgraph "Data & Storage"
        Database[(Primary Database<br/>- User Data<br/>- Business Data<br/>- Audit Logs)]
        Cache[(Cache Layer<br/>- Session Cache<br/>- Query Cache<br/>- Application Cache)]
        FileStore[(File Storage<br/>- User Uploads<br/>- Generated Files<br/>- Backups)]
        SearchIndex[(Search Index<br/>- Full Text Search<br/>- Faceted Search<br/>- Auto-complete)]
    end
    
    %% External Systems
    subgraph "External Integrations"
        EmailProvider[Email Provider<br/>- Transactional Emails<br/>- Marketing Emails<br/>- Delivery Tracking]
        PaymentGateway[Payment Gateway<br/>- Payment Processing<br/>- Subscription Management<br/>- Refunds]
        ThirdPartyAPI[Third Party APIs<br/>- Data Sources<br/>- External Services<br/>- Webhooks]
    end
    
    %% Connections
    UI --> StateManager
    StateManager --> HTTPClient
    HTTPClient --> Gateway
    
    Gateway --> AuthService
    Gateway --> UserService
    Gateway --> BusinessService
    Gateway --> NotificationService
    Gateway --> FileService
    
    UserService --> Database
    AuthService --> Database
    BusinessService --> Database
    BusinessService --> Cache
    FileService --> FileStore
    BusinessService --> SearchIndex
    
    NotificationService --> EmailProvider
    BusinessService --> PaymentGateway
    BusinessService --> ThirdPartyAPI
    
    AuthService --> Cache
    UserService --> Cache
```

### Data Flow and Process Diagram
```mermaid
flowchart TD
    %% User Actions
    UserAction[👤 User Action<br/>Login/Create/Update/Delete]
    
    %% Input Validation
    Validation{🔍 Input Validation<br/>- Schema Validation<br/>- Business Rules<br/>- Security Checks}
    
    %% Authentication & Authorization
    Auth{🔐 Authentication & Authorization<br/>- JWT Token Validation<br/>- Role-based Access<br/>- Permission Checks}
    
    %% Business Logic Processing
    BusinessLogic[⚙️ Business Logic Processing<br/>- Core Operations<br/>- Data Transformations<br/>- Rule Engine]
    
    %% Data Operations
    DataOps{💾 Data Operations<br/>Which type of operation?}
    
    %% Different Data Paths
    CreateData[➕ Create Operation<br/>- Generate ID<br/>- Set Timestamps<br/>- Create Record]
    
    UpdateData[✏️ Update Operation<br/>- Validate Changes<br/>- Merge Data<br/>- Update Record]
    
    DeleteData[🗑️ Delete Operation<br/>- Soft/Hard Delete<br/>- Cascade Rules<br/>- Archive Data]
    
    ReadData[📖 Read Operation<br/>- Query Database<br/>- Apply Filters<br/>- Check Permissions]
    
    %% Post-processing
    PostProcess[🔄 Post Processing<br/>- Event Triggers<br/>- Notifications<br/>- Audit Logging]
    
    %% Cache Management
    CacheUpdate[⚡ Cache Management<br/>- Update Cache<br/>- Invalidate Old Data<br/>- Set TTL]
    
    %% Response
    Response[📤 Response<br/>- Format Data<br/>- Add Metadata<br/>- Return Result]
    
    %% Error Handling
    Error[❌ Error Handling<br/>- Log Error<br/>- Notify Admin<br/>- Return Error Response]
    
    %% Flow
    UserAction --> Validation
    Validation -->|Valid| Auth
    Validation -->|Invalid| Error
    
    Auth -->|Authorized| BusinessLogic
    Auth -->|Unauthorized| Error
    
    BusinessLogic --> DataOps
    
    DataOps -->|Create| CreateData
    DataOps -->|Read| ReadData
    DataOps -->|Update| UpdateData
    DataOps -->|Delete| DeleteData
    
    CreateData --> PostProcess
    ReadData --> Response
    UpdateData --> PostProcess
    DeleteData --> PostProcess
    
    PostProcess --> CacheUpdate
    CacheUpdate --> Response
    
    %% Error paths
    BusinessLogic -->|Error| Error
    CreateData -->|Error| Error
    UpdateData -->|Error| Error
    DeleteData -->|Error| Error
    ReadData -->|Error| Error
```

### Entity Relationship Diagram (ERD)
```mermaid
erDiagram
    %% User Management
    USERS {
        uuid id PK
        varchar email UK
        varchar first_name
        varchar last_name
        varchar password_hash
        varchar phone
        enum status
        timestamp created_at
        timestamp updated_at
        timestamp last_login
        json preferences
        varchar profile_image_url
        boolean email_verified
        boolean phone_verified
    }
    
    USER_ROLES {
        uuid id PK
        varchar name UK
        varchar description
        json permissions
        timestamp created_at
        timestamp updated_at
    }
    
    USER_ROLE_ASSIGNMENTS {
        uuid user_id PK,FK
        uuid role_id PK,FK
        timestamp assigned_at
        uuid assigned_by FK
        timestamp expires_at
    }
    
    %% Authentication & Sessions
    USER_SESSIONS {
        uuid id PK
        uuid user_id FK
        varchar token_hash
        varchar ip_address
        varchar user_agent
        timestamp created_at
        timestamp expires_at
        timestamp last_accessed
        boolean is_active
    }
    
    PASSWORD_RESET_TOKENS {
        uuid id PK
        uuid user_id FK
        varchar token_hash
        timestamp created_at
        timestamp expires_at
        boolean used
    }
    
    %% Core Business Entities
    PROJECTS {
        uuid id PK
        varchar name
        text description
        uuid owner_id FK
        enum status
        json metadata
        timestamp created_at
        timestamp updated_at
        timestamp deadline
        decimal budget
        varchar priority
    }
    
    PROJECT_MEMBERS {
        uuid project_id PK,FK
        uuid user_id PK,FK
        enum role
        json permissions
        timestamp joined_at
        uuid invited_by FK
        boolean is_active
    }
    
    TASKS {
        uuid id PK
        uuid project_id FK
        varchar title
        text description
        uuid assigned_to FK
        uuid created_by FK
        enum status
        enum priority
        timestamp created_at
        timestamp updated_at
        timestamp due_date
        timestamp completed_at
        integer estimated_hours
        integer actual_hours
        json custom_fields
    }
    
    TASK_DEPENDENCIES {
        uuid id PK
        uuid task_id FK
        uuid depends_on_task_id FK
        enum dependency_type
        timestamp created_at
    }
    
    %% File Management
    FILES {
        uuid id PK
        varchar original_name
        varchar stored_name
        varchar mime_type
        bigint file_size
        varchar storage_path
        varchar hash_md5
        varchar hash_sha256
        uuid uploaded_by FK
        timestamp uploaded_at
        boolean is_deleted
        json metadata
    }
    
    FILE_ASSOCIATIONS {
        uuid id PK
        uuid file_id FK
        varchar entity_type
        uuid entity_id
        enum association_type
        timestamp created_at
    }
    
    %% Notifications & Communications
    NOTIFICATIONS {
        uuid id PK
        uuid user_id FK
        varchar type
        varchar title
        text content
        json data
        boolean is_read
        timestamp created_at
        timestamp read_at
        enum priority
        varchar source_entity_type
        uuid source_entity_id
    }
    
    EMAIL_LOGS {
        uuid id PK
        uuid user_id FK
        varchar to_email
        varchar subject
        text content
        enum status
        varchar external_id
        timestamp sent_at
        timestamp delivered_at
        timestamp opened_at
        integer retry_count
        text error_message
    }
    
    %% Audit and Logging
    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        varchar entity_type
        uuid entity_id
        enum action
        json old_values
        json new_values
        varchar ip_address
        varchar user_agent
        timestamp created_at
        json metadata
    }
    
    API_LOGS {
        uuid id PK
        uuid user_id FK
        varchar method
        varchar endpoint
        integer status_code
        integer response_time
        bigint request_size
        bigint response_size
        varchar ip_address
        varchar user_agent
        timestamp created_at
        text error_message
    }
    
    %% System Configuration
    SYSTEM_SETTINGS {
        varchar key PK
        text value
        varchar data_type
        text description
        boolean is_public
        timestamp updated_at
        uuid updated_by FK
    }
    
    %% Relationships
    USERS ||--o{ USER_ROLE_ASSIGNMENTS : has
    USER_ROLES ||--o{ USER_ROLE_ASSIGNMENTS : assigned_to
    USERS ||--o{ USER_SESSIONS : creates
    USERS ||--o{ PASSWORD_RESET_TOKENS : requests
    USERS ||--o{ PROJECTS : owns
    USERS ||--o{ PROJECT_MEMBERS : member_of
    PROJECTS ||--o{ PROJECT_MEMBERS : has_members
    PROJECTS ||--o{ TASKS : contains
    USERS ||--o{ TASKS : assigned
    USERS ||--o{ TASKS : created
    TASKS ||--o{ TASK_DEPENDENCIES : depends_on
    TASKS ||--o{ TASK_DEPENDENCIES : blocks
    USERS ||--o{ FILES : uploads
    FILES ||--o{ FILE_ASSOCIATIONS : associated_with
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ EMAIL_LOGS : sent_to
    USERS ||--o{ AUDIT_LOGS : performs
    USERS ||--o{ API_LOGS : makes_requests
    USERS ||--o{ SYSTEM_SETTINGS : updates
```

### Class Diagram - Core Application Structure
```mermaid
classDiagram
    %% User Management Classes
    class User {
        +UUID id
        +String email
        +String firstName
        +String lastName
        +String passwordHash
        +UserStatus status
        +DateTime createdAt
        +DateTime updatedAt
        +List~Role~ roles
        +authenticate(password): boolean
        +updateProfile(data): void
        +assignRole(role): void
        +hasPermission(permission): boolean
        +getActiveSessions(): List~Session~
    }
    
    class Role {
        +UUID id
        +String name
        +String description
        +List~Permission~ permissions
        +addPermission(permission): void
        +removePermission(permission): void
        +hasPermission(permission): boolean
    }
    
    class Permission {
        +String name
        +String resource
        +String action
        +Map~String, Any~ constraints
        +checkConstraints(context): boolean
    }
    
    class Session {
        +UUID id
        +UUID userId
        +String tokenHash
        +DateTime createdAt
        +DateTime expiresAt
        +String ipAddress
        +String userAgent
        +boolean isValid(): boolean
        +extend(): void
        +revoke(): void
    }
    
    %% Core Business Logic Classes
    class Project {
        +UUID id
        +String name
        +String description
        +UUID ownerId
        +ProjectStatus status
        +DateTime createdAt
        +List~Task~ tasks
        +List~User~ members
        +addMember(user, role): void
        +removeMember(user): void
        +createTask(taskData): Task
        +getProgress(): ProjectProgress
    }
    
    class Task {
        +UUID id
        +String title
        +String description
        +UUID projectId
        +UUID assignedTo
        +TaskStatus status
        +Priority priority
        +DateTime dueDate
        +Integer estimatedHours
        +updateStatus(status): void
        +assignTo(user): void
        +addDependency(task): void
        +getTimeTracking(): TimeTracking
    }
    
    class TaskDependency {
        +UUID taskId
        +UUID dependsOnTaskId
        +DependencyType type
        +DateTime createdAt
        +isBlocking(): boolean
        +canResolve(): boolean
    }
    
    %% Service Layer Classes
    class UserService {
        -UserRepository userRepo
        -PasswordService passwordService
        -EmailService emailService
        +createUser(userData): User
        +authenticateUser(email, password): User
        +updateUser(id, userData): User
        +deleteUser(id): void
        +resetPassword(email): void
        +verifyEmail(token): boolean
    }
    
    class ProjectService {
        -ProjectRepository projectRepo
        -TaskRepository taskRepo
        -NotificationService notificationService
        +createProject(projectData): Project
        +updateProject(id, projectData): Project
        +deleteProject(id): void
        +addProjectMember(projectId, userId, role): void
        +getProjectAnalytics(projectId): ProjectAnalytics
    }
    
    class TaskService {
        -TaskRepository taskRepo
        -UserService userService
        -NotificationService notificationService
        +createTask(taskData): Task
        +updateTask(id, taskData): Task
        +assignTask(taskId, userId): void
        +completeTask(taskId): void
        +getTaskDependencies(taskId): List~Task~
        +calculateCriticalPath(projectId): List~Task~
    }
    
    class NotificationService {
        -EmailService emailService
        -PushNotificationService pushService
        -NotificationRepository notificationRepo
        +sendNotification(userId, notification): void
        +markAsRead(notificationId): void
        +getUnreadCount(userId): Integer
        +subscribeToChannel(userId, channel): void
    }
    
    %% Repository Layer Classes
    class UserRepository {
        <<interface>>
        +findById(id): User
        +findByEmail(email): User
        +save(user): User
        +delete(id): void
        +findByRole(role): List~User~
    }
    
    class ProjectRepository {
        <<interface>>
        +findById(id): Project
        +findByOwner(ownerId): List~Project~
        +save(project): Project
        +delete(id): void
        +findByMember(userId): List~Project~
    }
    
    class TaskRepository {
        <<interface>>
        +findById(id): Task
        +findByProject(projectId): List~Task~
        +findByAssignee(userId): List~Task~
        +save(task): Task
        +delete(id): void
        +findOverdueTasks(): List~Task~
    }
    
    %% Data Transfer Objects
    class UserDTO {
        +String email
        +String firstName
        +String lastName
        +List~String~ roleNames
        +DateTime lastLogin
    }
    
    class ProjectDTO {
        +String name
        +String description
        +String status
        +Integer taskCount
        +Integer completedTasks
        +Double progressPercentage
    }
    
    class TaskDTO {
        +String title
        +String description
        +String status
        +String priority
        +String assigneeName
        +DateTime dueDate
        +Boolean isOverdue
    }
    
    %% Relationships
    User ||--o{ Session : creates
    User ||--o{ Role : has
    Role ||--o{ Permission : contains
    User ||--o{ Project : owns
    Project ||--o{ Task : contains
    Task ||--o{ TaskDependency : has
    User ||--o{ Task : assigned
    
    UserService --> UserRepository : uses
    UserService --> User : manages
    ProjectService --> ProjectRepository : uses
    ProjectService --> Project : manages
    TaskService --> TaskRepository : uses
    TaskService --> Task : manages
    
    UserService --> NotificationService : uses
    ProjectService --> NotificationService : uses
    TaskService --> NotificationService : uses
    
    %% Styling
    classDef entityClass fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef serviceClass fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef repositoryClass fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef dtoClass fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class User,Role,Permission,Session,Project,Task,TaskDependency entityClass
    class UserService,ProjectService,TaskService,NotificationService serviceClass
    class UserRepository,ProjectRepository,TaskRepository repositoryClass
    class UserDTO,ProjectDTO,TaskDTO dtoClass
```

REQUIREMENTS FOR ALL DIAGRAMS:
- Use proper Mermaid syntax with correct indentation and structure
- Include comprehensive details that match enterprise-level documentation
- Add styling classes for visual appeal and clarity
- Include specific attributes, methods, and relationships based on the specifications
- Ensure diagrams are implementable and technically accurate
- Add meaningful comments and descriptions
- Make diagrams detailed enough for development teams to understand the architecture
- Include error handling, security, and monitoring aspects where relevant
- Show data flow, dependencies, and interaction patterns clearly

Generate all diagrams with this level of detail and professionalism."""
        
        return prompt


class ImplementationPlanGenerator(BaseStageGenerator):
    """Generates implementation plan and file structure"""
    
    def generate(self, context: Dict[str, Any]) -> GenerationResult:
        """Generate implementation plan content"""
        start_time = datetime.now()
        
        try:
            upload_data = context['upload_data']
            previous_outputs = context.get('previous_outputs', {})
            
            # Get context from previous stages
            technical_spec_content = previous_outputs.get(GenerationStage.TECHNICAL_SPEC, '')
            product_spec_content = previous_outputs.get(GenerationStage.PRODUCT_SPEC, '')
            
            # Build implementation plan prompt
            prompt = self._build_implementation_prompt(upload_data, technical_spec_content, product_spec_content)
            
            # Create AI request
            ai_request = self._create_ai_request(prompt, TaskType.PLANNING)
            
            # Execute request
            if self.ai_broker:
                response = self.ai_broker.submit_request_sync(ai_request)
                
                if response.success:
                    processing_time = (datetime.now() - start_time).total_seconds()
                    return GenerationResult(
                        stage=GenerationStage.IMPLEMENTATION_PLAN,
                        success=True,
                        content=response.content,
                        processing_time=processing_time,
                        model_used=response.model_used,
                        metadata={'tokens_used': response.tokens_used}
                    )
                else:
                    return GenerationResult(
                        stage=GenerationStage.IMPLEMENTATION_PLAN,
                        success=False,
                        content="",
                        error_message=response.error_message,
                        processing_time=(datetime.now() - start_time).total_seconds()
                    )
            else:
                raise Exception("AI Broker not available")
                
        except Exception as e:
            return GenerationResult(
                stage=GenerationStage.IMPLEMENTATION_PLAN,
                success=False,
                content="",
                error_message=str(e),
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _build_implementation_prompt(self, upload_data: Dict[str, Any], 
                                   technical_spec_content: str, 
                                   product_spec_content: str) -> str:
        """Build prompt for implementation plan generation"""
        
        prompt = f"""Generate comprehensive Implementation Plan and File Structure based on the technical and product specifications.

TECHNICAL SPECIFICATION CONTEXT:
{technical_spec_content[:1500]}...

PRODUCT SPECIFICATION CONTEXT:
{product_spec_content[:1000]}...

Generate the following implementation sections:

## Files Tree
```
project-root/
├── src/
│   ├── components/
│   │   ├── [Generate specific component files]
│   ├── services/
│   │   ├── [Generate specific service files]
│   ├── models/
│   │   ├── [Generate specific model files]
│   ├── utils/
│   └── [Generate other necessary directories and files]
├── tests/
│   ├── [Generate test file structure]
├── docs/
├── config/
└── [Generate other root-level files and directories]
```

## Implementation Plan

### Phase 1: Foundation Setup
**Duration**: [Estimate timeline]
**Deliverables**:
- [Generate specific deliverables]
- [Generate setup tasks]
- [Generate infrastructure setup]

**Tasks**:
1. [Generate specific implementation tasks]
2. [Generate configuration tasks]
3. [Generate initial setup tasks]

### Phase 2: Core Development
**Duration**: [Estimate timeline]
**Deliverables**:
- [Generate core feature deliverables]
- [Generate API development tasks]
- [Generate database implementation]

**Tasks**:
1. [Generate specific development tasks]
2. [Generate integration tasks]
3. [Generate testing tasks]

### Phase 3: Integration & Testing
**Duration**: [Estimate timeline]
**Deliverables**:
- [Generate integration deliverables]
- [Generate testing deliverables]
- [Generate deployment preparation]

**Tasks**:
1. [Generate integration tasks]
2. [Generate comprehensive testing tasks]
3. [Generate performance optimization tasks]

### Phase 4: Deployment & Launch
**Duration**: [Estimate timeline]
**Deliverables**:
- [Generate deployment deliverables]
- [Generate monitoring setup]
- [Generate documentation]

**Tasks**:
1. [Generate deployment tasks]
2. [Generate monitoring tasks]
3. [Generate launch preparation tasks]

REQUIREMENTS:
- Generate realistic timelines and milestones
- Include specific file names and directory structures
- Create actionable tasks with clear deliverables
- Consider dependencies between phases
- Include testing and quality assurance tasks

Generate the complete Implementation Plan now:"""
        
        return prompt


# Global orchestrator instance
_orchestrator: Optional[PRDGenerationOrchestrator] = None


def get_prd_generation_orchestrator(config: Optional[GenerationConfig] = None) -> PRDGenerationOrchestrator:
    """Get the global PRD generation orchestrator instance"""
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = PRDGenerationOrchestrator(config)
    
    return _orchestrator
