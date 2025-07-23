"""
Define Agent - Context-aware specification generation from promoted ideas
Subscribes to idea.promoted events and publishes spec.frozen events
"""

import logging
import uuid
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from .base import BaseAgent, AgentConfig, EventProcessingResult, ProjectContext
    from ..events.domain_events import IdeaPromotedEvent, SpecFrozenEvent
    from ..events.base import BaseEvent
    from ..services.ai_broker import AIBroker, AIRequest, TaskType, Priority
    from ..services.vector_context_service import get_vector_context_service
    from ..models.specification_artifact import SpecificationArtifact, ArtifactType, ArtifactStatus
    from ..models.base import db
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from agents.base import BaseAgent, AgentConfig, EventProcessingResult, ProjectContext
    from events.domain_events import IdeaPromotedEvent, SpecFrozenEvent
    from events.base import BaseEvent
    from services.ai_broker import AIBroker, AIRequest, TaskType, Priority
    from services.vector_context_service import get_vector_context_service
    from models.specification_artifact import SpecificationArtifact, ArtifactType, ArtifactStatus
    from models.base import db

logger = logging.getLogger(__name__)


class DefineAgent(BaseAgent):
    """
    Define Agent for context-aware specification generation
    
    Responsibilities:
    - Process idea.promoted events
    - Retrieve similar specs and documentation using pgvector
    - Generate comprehensive specifications using Claude
    - Track AI-draft vs Human-reviewed status
    - Publish spec.frozen events
    - Optional Notion sync integration
    """
    
    def __init__(self, event_bus, ai_broker: Optional[AIBroker] = None):
        config = AgentConfig(
            agent_id="define_agent",
            name="Define Agent",
            description="Generates comprehensive specifications from promoted ideas using AI and context",
            event_types=["idea.promoted"],
            max_concurrent_events=2,
            retry_attempts=3,
            timeout_seconds=180.0  # 3 minutes for spec generation
        )
        
        super().__init__(config, event_bus)
        self.ai_broker = ai_broker
        self.vector_context_service = get_vector_context_service()
        
        # Specification templates
        self.requirements_template = """# Requirements Document

## Introduction

{introduction}

## Requirements

{requirements_content}
"""
        
        self.design_template = """# Design Document

## Overview

{overview}

## Architecture

{architecture}

## Components and Interfaces

{components}

## Data Models

{data_models}

## Error Handling

{error_handling}

## Testing Strategy

{testing_strategy}
"""
        
        self.tasks_template = """# Implementation Plan

{tasks_content}
"""
    
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process idea.promoted events and generate specifications"""
        start_time = datetime.utcnow()
        
        try:
            if not isinstance(event, IdeaPromotedEvent):
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=0.0,
                    error_message="Event is not an IdeaPromotedEvent"
                )
            
            logger.info(f"Processing idea promotion for idea {event.aggregate_id} in project {event.project_id}")
            
            # Get project context
            project_context = self.get_project_context(event.project_id)
            
            # Get the original idea content from the event or retrieve it
            idea_content = self._get_idea_content(event)
            if not idea_content:
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    error_message="Could not retrieve idea content"
                )
            
            # Retrieve context using pgvector
            context_data = self._retrieve_context(idea_content, event.project_id, project_context)
            
            # Generate specifications using AI
            specifications = self._generate_specifications(
                idea_content=idea_content,
                project_context=project_context,
                context_data=context_data,
                promoted_by=event.promoted_by
            )
            
            if not specifications:
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    error_message="Failed to generate specifications"
                )
            
            # Create spec ID based on the idea ID
            spec_id = f"spec_{event.aggregate_id}"
            
            # Store specifications (in a real implementation, you'd save to database)
            self._store_specifications(spec_id, event.project_id, specifications)
            
            # Create spec.frozen event
            spec_frozen_event = SpecFrozenEvent(
                spec_id=spec_id,
                project_id=event.project_id,
                frozen_by=f"define_agent:{event.promoted_by}"
            )
            
            # Add metadata about the generation process
            spec_frozen_event.original_idea_id = event.aggregate_id
            spec_frozen_event.promoted_by = event.promoted_by
            spec_frozen_event.ai_generated = True
            spec_frozen_event.human_reviewed = False  # Initially AI-generated, not human_reviewed
            spec_frozen_event.context_sources = context_data.get('sources', [])
            spec_frozen_event.generation_agent = self.config.agent_id
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Generated specifications for idea {event.aggregate_id} as spec {spec_id}")
            
            # Optional: Sync to Notion if configured
            self._notion_sync_if_configured(spec_id, event.project_id, specifications)
            
            return EventProcessingResult(
                success=True,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=processing_time,
                result_data={
                    'spec_id': spec_id,
                    'idea_id': event.aggregate_id,
                    'specifications_generated': list(specifications.keys()),
                    'context_sources_count': len(context_data.get('sources', [])),
                    'ai_generated': True
                },
                generated_events=[spec_frozen_event]
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Failed to process idea promotion: {e}")
            
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=processing_time,
                error_message=str(e)
            )
    
    def _get_idea_content(self, event: IdeaPromotedEvent) -> Optional[str]:
        """Retrieve the original idea content"""
        try:
            # First try to get from event if it was added by the bridge
            if hasattr(event, 'idea_content'):
                return event.idea_content
            
            # Try to get from database using the idea_id
            try:
                from ..models.feed_item import FeedItem
            except ImportError:
                from models.feed_item import FeedItem
            
            feed_item = FeedItem.query.get(event.aggregate_id)
            if feed_item:
                return f"Title: {feed_item.title}\n\nDescription: {feed_item.summary or 'No description provided'}"
            
            # Fallback to basic info
            return f"Promoted idea {event.aggregate_id} from project {event.project_id}"
            
        except Exception as e:
            logger.error(f"Failed to retrieve idea content: {e}")
            return None
    
    def _retrieve_context(self, idea_content: str, project_id: str, 
                         project_context: ProjectContext) -> Dict[str, Any]:
        """Retrieve relevant context using pgvector and other sources"""
        context_data = {
            'similar_specs': [],
            'related_docs': [],
            'similar_code': [],
            'sources': []
        }
        
        try:
            if self.vector_context_service:
                # Find similar specifications
                similar_specs = self.vector_context_service.find_similar_specs(
                    query=idea_content,
                    project_id=project_id,
                    limit=3
                )
                context_data['similar_specs'] = similar_specs
                if similar_specs:
                    context_data['sources'].extend([f"spec:{spec.get('document_id', 'unknown')}" for spec in similar_specs])
                
                # Find related documentation
                related_docs = self.vector_context_service.find_related_docs(
                    query=idea_content,
                    project_id=project_id,
                    limit=2
                )
                context_data['related_docs'] = related_docs
                if related_docs:
                    context_data['sources'].extend([f"doc:{doc.get('document_id', 'unknown')}" for doc in related_docs])
                
                # Find similar code for implementation context
                similar_code = self.vector_context_service.find_similar_code(
                    query=idea_content,
                    project_id=project_id,
                    limit=3
                )
                context_data['similar_code'] = similar_code
                if similar_code:
                    context_data['sources'].extend([f"code:{code.get('document_id', 'unknown')}" for code in similar_code])
            
            # Add project system map context
            if project_context.system_map:
                context_data['system_map'] = project_context.system_map
                context_data['sources'].append('system_map')
            
            logger.info(f"Retrieved context with {len(context_data['sources'])} sources for project {project_id}")
            
        except Exception as e:
            logger.warning(f"Failed to retrieve some context: {e}")
        
        return context_data
    
    def _generate_specifications(self, idea_content: str, project_context: ProjectContext,
                               context_data: Dict[str, Any], promoted_by: str) -> Optional[Dict[str, str]]:
        """Generate comprehensive specifications using AI"""
        if not self.ai_broker:
            logger.warning("AI broker not available, cannot generate specifications")
            return None
        
        try:
            # Prepare context for AI
            ai_context = self._prepare_ai_context(idea_content, project_context, context_data)
            
            # Generate only requirements.md first (sequential workflow like Kiro)
            requirements_md = self._generate_requirements(idea_content, ai_context)
            if not requirements_md:
                return None
            
            # Store requirements first and wait for user approval
            # Design and tasks will be generated in separate user-triggered actions
            design_md = None
            tasks_md = None
            
            return {
                'requirements': requirements_md,
                'design': design_md,
                'tasks': tasks_md
            }
            
        except Exception as e:
            logger.error(f"Failed to generate specifications: {e}")
            return None
    
    def _prepare_ai_context(self, idea_content: str, project_context: ProjectContext,
                           context_data: Dict[str, Any]) -> str:
        """Prepare comprehensive context for AI specification generation with Kiro-style repository awareness"""
        context_parts = []
        
        # Add Kiro-style repository analysis instruction
        context_parts.append("=== REPOSITORY ANALYSIS INSTRUCTION ===")
        context_parts.append("You have full filesystem access to analyze this repository. Before generating specifications:")
        context_parts.append("1. Examine the project structure and existing patterns")
        context_parts.append("2. Review similar features and their implementations")
        context_parts.append("3. Understand the technology stack and dependencies")
        context_parts.append("4. Identify integration points and existing APIs")
        context_parts.append("5. Follow established coding conventions and patterns")
        context_parts.append("")
        
        # Add project information
        if project_context.system_map:
            context_parts.append("=== PROJECT SYSTEM MAP ===")
            context_parts.append(str(project_context.system_map))
            context_parts.append("")
        
        # Add similar specifications with enhanced context
        if context_data.get('similar_specs'):
            context_parts.append("=== SIMILAR SPECIFICATIONS (Reference These Patterns) ===")
            for spec in context_data['similar_specs']:
                context_parts.append(f"[{spec.get('relevance_reason', 'Similar spec')}]")
                context_parts.append(spec.get('content', '')[:500] + "...")
                context_parts.append("")
        
        # Add related documentation with enhanced context
        if context_data.get('related_docs'):
            context_parts.append("=== RELATED DOCUMENTATION (Follow These Patterns) ===")
            for doc in context_data['related_docs']:
                context_parts.append(f"[{doc.get('relevance_reason', 'Related doc')}]")
                context_parts.append(doc.get('content', '')[:300] + "...")
                context_parts.append("")
        
        # Add similar code for implementation context
        if context_data.get('similar_code'):
            context_parts.append("=== SIMILAR CODE PATTERNS (Extend These Implementations) ===")
            for code in context_data['similar_code']:
                context_parts.append(f"[{code.get('relevance_reason', 'Similar code')}]")
                context_parts.append(code.get('content', '')[:200] + "...")
                context_parts.append("")
        
        # Add repository discovery context
        context_parts.append("=== REPOSITORY CONTEXT DISCOVERY ===")
        context_parts.append("Use your filesystem access to discover and reference:")
        context_parts.append("- package.json/requirements.txt (technology stack)")
        context_parts.append("- Database migrations and models")
        context_parts.append("- API routes and middleware patterns")
        context_parts.append("- Component structures and design patterns")
        context_parts.append("- Testing patterns and infrastructure")
        context_parts.append("- Documentation and README files")
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _generate_requirements(self, idea_content: str, ai_context: str) -> Optional[str]:
        """Generate requirements.md using AI Broker with enhanced repository-aware context"""
        try:
            # Enhanced Kiro-style prompt that leverages repository access
            prompt = f"""You are a senior product manager and business analyst with full filesystem access to analyze this repository.

{ai_context}

FEATURE REQUEST:
{idea_content}

INSTRUCTIONS:
1. **ANALYZE THE REPOSITORY FIRST**: Use your filesystem access to examine:
   - Project structure and organization patterns
   - Existing similar features and their implementation
   - Technology stack (package.json, requirements.txt, etc.)
   - Database schemas and models
   - API patterns and routing structures
   - Component architectures and relationships
   - Testing patterns and infrastructure

2. **GENERATE REPOSITORY-AWARE REQUIREMENTS**: Create requirements.md that:
   - References actual files, classes, and patterns from the codebase
   - Follows established architectural patterns
   - Integrates with existing APIs and data models
   - Uses the same technology stack and conventions
   - Mentions specific files that need modification or creation

Create a requirements.md document with the following structure:

# Requirements Document

## 1. Repository Analysis Summary
- **Current Architecture**: Key patterns and structures found in codebase
- **Similar Features**: Existing implementations to reference or extend
- **Integration Points**: Specific files/components that need modification
- **Technology Stack**: Confirmed from repository analysis

## 2. Executive Summary
- Brief overview of the feature and its business value
- Integration with existing system architecture
- Key stakeholders and target users  
- Success metrics and KPIs

## 3. Business Requirements
### 3.1 Business Objectives
- Primary business goals this feature addresses
- Expected ROI and business impact
- Alignment with company strategy

### 3.2 User Stories
Write 5-8 key user stories in format:
**As a [user type], I want [capability] so that [benefit]**

## 4. Functional Requirements
### 4.1 Core Functionality
List 8-12 numbered requirements using EARS format:
- **REQ-001**: WHEN [trigger condition] THEN the system SHALL [required behavior]
- Reference specific existing patterns/files where applicable

### 4.2 API Requirements
- Endpoint specifications following existing API patterns
- Request/response formats matching current schemas
- Authentication/authorization using existing middleware

### 4.3 Database Requirements
- Table schemas following existing migration patterns
- Relationships with existing entities
- Data access patterns matching current repository structure

### 4.4 UI/UX Requirements
- Component specifications following existing UI patterns
- Integration with current design system
- User interface workflows

## 5. Non-Functional Requirements
### 5.1 Performance & Scalability
### 5.2 Security & Compliance  
### 5.3 Reliability & Availability

## 6. Implementation Context
### 6.1 Files to Modify
- List specific files that need changes
- Explain integration points with existing code

### 6.2 New Files to Create
- Specify new components/modules needed
- Follow existing naming conventions and patterns

### 6.3 Dependencies and Integration
- New packages/libraries needed
- Version compatibility with existing stack
- Integration with existing services

## 7. Acceptance Criteria (5-8 criteria)
**Given** [context] **When** [action] **Then** [outcome]

## 8. Technical Constraints and Considerations
- Architecture limitations and opportunities
- Technology constraints and requirements
- Integration requirements and dependencies

Generate a comprehensive, repository-aware requirements document that demonstrates deep understanding of the existing codebase and seamlessly integrates with established patterns."""
            
            # Use your existing AI Broker pattern
            ai_request = AIRequest(
                request_id=f"requirements_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=32000,
                timeout_seconds=300.0,
                preferred_models=['goose-gemini', 'claude-opus-4'],  # Try Goose first, then fallback
                metadata={'agent': self.config.agent_id, 'type': 'requirements', 'approach': 'kiro_style'}
            )
            
            logger.info(f"Submitting enhanced AI request with models: {ai_request.preferred_models}")
            logger.info(f"Request ID: {ai_request.request_id}, Enhanced context length: {len(prompt)}")
            
            import time
            start_time = time.time()
            response = self.ai_broker.submit_request_sync(ai_request, timeout=300.0)
            elapsed_time = time.time() - start_time
            
            logger.info(f"AI response received after {elapsed_time:.2f}s - Success: {response.success}")
            logger.info(f"Response model: {getattr(response, 'model_used', 'unknown')}")
            logger.info(f"Response content length: {len(getattr(response, 'content', ''))}")
            
            if hasattr(response, 'error_message') and response.error_message:
                logger.error(f"AI response error: {response.error_message}")
            if not response.success:
                logger.error(f"AI request failed - Response: {response.__dict__}")
            
            if response.success:
                logger.info(f"Generated repository-aware requirements using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate requirements: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating requirements: {e}")
            return None
    
    def _generate_requirements_DUPLICATE(self, idea_content: str, ai_context: str) -> Optional[str]:
        """Generate requirements.md using AI Broker with enhanced repository-aware context"""
        try:
            # Enhanced Kiro-style prompt that leverages repository access
            prompt = f"""You are a senior product manager and business analyst with full filesystem access to analyze this repository.

{ai_context}

FEATURE REQUEST:
{idea_content}

INSTRUCTIONS:
1. **ANALYZE THE REPOSITORY FIRST**: Use your filesystem access to examine:
   - Project structure and organization patterns
   - Existing similar features and their implementation
   - Technology stack (package.json, requirements.txt, etc.)
   - Database schemas and models
   - API patterns and routing structures
   - Component architectures and relationships
   - Testing patterns and infrastructure

2. **GENERATE REPOSITORY-AWARE REQUIREMENTS**: Create requirements.md that:
   - References actual files, classes, and patterns from the codebase
   - Follows established architectural patterns
   - Integrates with existing APIs and data models
   - Uses the same technology stack and conventions
   - Mentions specific files that need modification or creation

Create a requirements.md document with the following structure:

# Requirements Document

## 1. Repository Analysis Summary
- **Current Architecture**: Key patterns and structures found in codebase
- **Similar Features**: Existing implementations to reference or extend
- **Integration Points**: Specific files/components that need modification
- **Technology Stack**: Confirmed from repository analysis

## 2. Executive Summary
- Brief overview of the feature and its business value
- Integration with existing system architecture
- Key stakeholders and target users  
- Success metrics and KPIs

## 3. Business Requirements
### 3.1 Business Objectives
- Primary business goals this feature addresses
- Expected ROI and business impact
- Alignment with company strategy

### 3.2 User Stories
Write 5-8 key user stories in format:
**As a [user type], I want [capability] so that [benefit]**

## 4. Functional Requirements
### 4.1 Core Functionality
List 8-12 numbered requirements using EARS format:
- **REQ-001**: WHEN [trigger condition] THEN the system SHALL [required behavior]
- Reference specific existing patterns/files where applicable

### 4.2 API Requirements
- Endpoint specifications following existing API patterns
- Request/response formats matching current schemas
- Authentication/authorization using existing middleware

### 4.3 Database Requirements
- Table schemas following existing migration patterns
- Relationships with existing entities
- Data access patterns matching current repository structure

### 4.4 User Interface Requirements
- Component specifications following existing UI patterns
- Integration with current design system
- User workflow specifications

## 5. Non-Functional Requirements
### 5.1 Performance & Scalability
### 5.2 Security & Compliance
### 5.3 Reliability & Availability

## 6. Implementation Context
### 6.1 Files to Modify
- List specific files that need changes
- Explain integration points with existing code

### 6.2 New Files to Create
- Specify new components/modules needed
- Follow existing naming conventions and patterns

### 6.3 Dependencies and Integration
- New packages/libraries needed
- Version compatibility with existing stack

## 7. Acceptance Criteria
Define 5-8 key acceptance criteria using Given/When/Then format:
- **Given** [initial context] **When** [action is performed] **Then** [expected outcome]

## 8. Technical Constraints and Considerations
- Architecture limitations and opportunities
- Technology constraints and requirements
- Integration requirements and dependencies

Generate a comprehensive, repository-aware requirements document that demonstrates deep understanding of the existing codebase and follows established patterns."""
            
            # Use your existing AI Broker pattern
            ai_request = AIRequest(
                request_id=f"requirements_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=32000,
                timeout_seconds=300.0,
                preferred_models=['goose-gemini', 'claude-opus-4'],  # Try Goose first, then fallback
                metadata={'agent': self.config.agent_id, 'type': 'requirements', 'approach': 'kiro_style'}
            )
            
            logger.info(f"Submitting enhanced AI request with models: {ai_request.preferred_models}")
            logger.info(f"Request ID: {ai_request.request_id}, Enhanced context length: {len(prompt)}")
            
            import time
            start_time = time.time()
            response = self.ai_broker.submit_request_sync(ai_request, timeout=300.0)
            elapsed_time = time.time() - start_time
            
            logger.info(f"AI response received after {elapsed_time:.2f}s - Success: {response.success}")
            logger.info(f"Response model: {getattr(response, 'model_used', 'unknown')}")
            logger.info(f"Response content length: {len(getattr(response, 'content', ''))}")
            
            if response.success:
                logger.info(f"Generated repository-aware requirements using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate requirements: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating requirements: {e}")
            return None
    
    def _generate_design(self, idea_content: str, requirements_md: str, ai_context: str) -> Optional[str]:
        """Generate design.md using Kiro-style approach"""
        try:
            from ..services.kiro_style_spec_generator import get_kiro_spec_generator
            kiro_generator = get_kiro_spec_generator()
            
            # Combine idea content with requirements for design context
            design_context = f"REQUIREMENTS:\n{requirements_md}\n\nORIGINAL IDEA:\n{idea_content}"
            
            project_id = getattr(self, 'current_project_id', 'unknown')
            design_content = kiro_generator.generate_specification(
                idea_content=design_context,
                project_id=project_id,
                artifact_type='design'
            )
            
            if design_content:
                logger.info("Successfully generated design using Kiro-style approach")
                return design_content
            else:
                logger.error("Failed to generate design with Kiro-style approach")
                return None
                
        except Exception as e:
            logger.error(f"Error generating design: {e}")
            return None
    
    def _generate_tasks(self, idea_content: str, requirements_md: str, 
                       design_md: str, ai_context: str) -> Optional[str]:
        """Generate tasks.md using Kiro-style approach"""
        try:
            from ..services.kiro_style_spec_generator import get_kiro_spec_generator
            kiro_generator = get_kiro_spec_generator()
            
            # Combine all context for tasks generation
            tasks_context = f"""REQUIREMENTS:
{requirements_md}

DESIGN:
{design_md}

ORIGINAL IDEA:
{idea_content}"""
            
            project_id = getattr(self, 'current_project_id', 'unknown')
            tasks_content = kiro_generator.generate_specification(
                idea_content=tasks_context,
                project_id=project_id,
                artifact_type='tasks'
            )
            
            if tasks_content:
                logger.info("Successfully generated tasks using Kiro-style approach")
                return tasks_content
            else:
                logger.error("Failed to generate tasks with Kiro-style approach")
                return None
                
        except Exception as e:
            logger.error(f"Error generating tasks: {e}")
            return None
    
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process idea.promoted events and generate specifications using Kiro approach"""
        start_time = datetime.utcnow()
        
        try:
            if not isinstance(event, IdeaPromotedEvent):
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=0.0,
                    error_message="Event is not an IdeaPromotedEvent"
                )
            
            logger.info(f"Processing idea promotion for idea {event.aggregate_id} in project {event.project_id}")
            
            # Store project ID for use in generation methods
            self.current_project_id = str(event.project_id)
            
            # Get project context
            project_context = self.get_project_context(event.project_id)
            
            # Get the original idea content from the event or retrieve it
            idea_content = self._get_idea_content(event)
            if not idea_content:
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    error_message="Could not retrieve idea content"
                )
            
            # Retrieve context using pgvector
            context_data = self._retrieve_context(idea_content, event.project_id, project_context)
            
            # Generate specifications using Kiro-style approach
            specifications = self._generate_specifications(
                idea_content=idea_content,
                project_context=project_context,
                context_data=context_data,
                promoted_by=event.promoted_by
            )
            
            if not specifications:
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    error_message="Failed to generate specifications"
                )
            
            # Create spec ID based on the idea ID
            spec_id = f"spec_{event.aggregate_id}"
            
            # Store specifications
            self._store_specifications(spec_id, event.project_id, specifications)
            
            # Create spec.frozen event
            spec_frozen_event = SpecFrozenEvent(
                spec_id=spec_id,
                project_id=event.project_id,
                frozen_by=f"define_agent:{event.promoted_by}"
            )
            
            # Add metadata about the generation process
            spec_frozen_event.original_idea_id = event.aggregate_id
            spec_frozen_event.promoted_by = event.promoted_by
            spec_frozen_event.ai_generated = True
            spec_frozen_event.human_reviewed = False
            spec_frozen_event.context_sources = context_data.get('sources', [])
            spec_frozen_event.generation_agent = self.config.agent_id
            spec_frozen_event.generation_method = 'kiro_style'  # New metadata
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Generated specifications for idea {event.aggregate_id} as spec {spec_id} using Kiro-style approach")
            
            return EventProcessingResult(
                success=True,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=processing_time,
                result_data={
                    'spec_id': spec_id,
                    'idea_id': event.aggregate_id,
                    'specifications_generated': list(specifications.keys()),
                    'context_sources_count': len(context_data.get('sources', [])),
                    'ai_generated': True,
                    'generation_method': 'kiro_style'
                },
                generated_events=[spec_frozen_event]
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Failed to process idea promotion: {e}")
            
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=processing_time,
                error_message=str(e)
            )
    
    # Remove the old implementation and replace with this comment
    # The old _generate_requirements method has been replaced above 


    def _generate_design(self, idea_content: str, requirements_md: str, ai_context: str) -> Optional[str]:
        """Generate design.md using AI"""
        try:
            prompt = f"""You are a senior software architect and technical lead. Create a comprehensive technical design document for the following feature.

FEATURE REQUEST:
{idea_content}

REQUIREMENTS:
{requirements_md}

PROJECT CONTEXT:
{ai_context}

Create a design.md document with the following structure:

# Technical Design Document

## 1. Overview
### 1.1 Purpose
- Brief description of the feature and its technical objectives
- Scope and boundaries of the implementation

### 1.2 Architecture Summary
- High-level architectural approach
- Key design decisions and rationale

## 2. System Architecture
### 2.1 Component Architecture
```mermaid
graph TB
    A[Frontend] --> B[API Gateway]
    B --> C[Business Logic]
    C --> D[Data Layer]
    D --> E[Database]
```

### 2.2 Data Flow
- Request/response flow diagrams
- Data transformation points
- Integration touchpoints

### 2.3 Technology Stack
- Programming languages and frameworks
- Databases and storage solutions
- Third-party services and libraries

## 3. Detailed Design
### 3.1 API Design
#### 3.1.1 Endpoints
```
POST /api/v1/resource
GET /api/v1/resource/{id}
PUT /api/v1/resource/{id}
DELETE /api/v1/resource/{id}
```

#### 3.1.2 Request/Response Schemas
```json
{{
  "field1": "string",
  "field2": "integer",
  "field3": {{
    "nested": "object"
  }}
}}
```

### 3.2 Database Design
#### 3.2.1 Entity Relationship Diagram
```mermaid
erDiagram
    USER ||--o{{ ORDER : places
    ORDER ||--|| LINE-ITEM : contains
    PRODUCT ||--o{{ LINE-ITEM : includes
```

#### 3.2.2 Table Schemas
```sql
CREATE TABLE example_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 Business Logic Components
- Service layer design
- Domain models and entities
- Business rules implementation

### 3.4 Security Design
- Authentication and authorization flows
- Data encryption and protection
- Input validation and sanitization
- Rate limiting and abuse prevention

## 4. Implementation Strategy
### 4.1 Development Phases
1. **Phase 1**: Core functionality
2. **Phase 2**: Integration and testing
3. **Phase 3**: Performance optimization

### 4.2 Migration Strategy
- Database migration scripts
- Backward compatibility considerations
- Rollback procedures

### 4.3 Deployment Strategy
- Environment configuration
- CI/CD pipeline integration
- Blue-green deployment approach

## 5. Performance Considerations
### 5.1 Performance Requirements
- Response time targets
- Throughput expectations
- Resource utilization limits

### 5.2 Optimization Strategies
- Caching strategies
- Database query optimization
- Load balancing approaches

### 5.3 Monitoring and Metrics
- Key performance indicators
- Logging and observability
- Alerting thresholds

## 6. Error Handling and Resilience
### 6.1 Error Scenarios
- Input validation errors
- System failures and timeouts
- External service failures

### 6.2 Recovery Strategies
- Retry mechanisms
- Circuit breaker patterns
- Graceful degradation

### 6.3 Logging and Debugging
- Structured logging format
- Error tracking and reporting
- Debug information capture

## 7. Testing Strategy
### 7.1 Unit Testing
- Test coverage targets
- Mock and stub strategies
- Test data management

### 7.2 Integration Testing
- API contract testing
- Database integration tests
- External service mocking

### 7.3 Performance Testing
- Load testing scenarios
- Stress testing parameters
- Performance benchmarks

## 8. Maintenance and Operations
### 8.1 Operational Procedures
- Deployment procedures
- Monitoring and alerting
- Backup and recovery

### 8.2 Documentation
- API documentation
- Operational runbooks
- Troubleshooting guides

Generate a professional, comprehensive technical design document following this exact structure with specific implementation details."""
            
            ai_request = AIRequest(
                request_id=f"design_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.ARCHITECTURE,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=8000,
                timeout_seconds=300.0,
                preferred_models=['claude-opus-4'],
                metadata={'agent': self.config.agent_id, 'type': 'design'}
            )
            
            response = self.ai_broker.submit_request_sync(ai_request, timeout=120.0)
            
            if response.success:
                logger.info(f"Generated design using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate design: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating design: {e}")
            return None
    
    def _generate_tasks(self, idea_content: str, requirements_md: str, 
                       design_md: str, ai_context: str) -> Optional[str]:
        """Generate tasks.md using AI"""
        try:
            prompt = f"""You are a senior engineering manager and technical lead. Create a comprehensive implementation plan that breaks down the feature into actionable development tasks.

FEATURE REQUEST:
{idea_content}

REQUIREMENTS:
{requirements_md}

TECHNICAL DESIGN:
{design_md}

PROJECT CONTEXT:
{ai_context}

Create a tasks.md document with the following structure:

# Implementation Tasks

## Overview
- Brief summary of the implementation approach
- Key milestones and deliverables
- Estimated timeline and effort

## Development Phases

### Phase 1: Foundation and Setup
- [ ] **1.1 Project Setup**
  - Set up development environment and dependencies
  - Configure build tools and CI/CD pipeline
  - Create project structure and base configurations
  - _Estimated effort: 0.5 days_
  - _Requirements: ENV-001, BUILD-001_

- [ ] **1.2 Database Schema**
  - Create database migration scripts
  - Implement entity models and relationships
  - Set up database connection and ORM configuration
  - _Estimated effort: 1 day_
  - _Requirements: DATA-001, DATA-002_

### Phase 2: Core Backend Implementation
- [ ] **2.1 API Layer**
  - Implement REST API endpoints
  - Add request/response validation
  - Configure authentication and authorization
  - _Estimated effort: 2 days_
  - _Requirements: API-001, API-002, SEC-001_

- [ ] **2.2 Business Logic**
  - Implement core business services
  - Add domain models and business rules
  - Integrate with external services
  - _Estimated effort: 3 days_
  - _Requirements: BUS-001, BUS-002, INT-001_

- [ ] **2.3 Data Access Layer**
  - Implement repository patterns
  - Add database queries and transactions
  - Implement caching strategies
  - _Estimated effort: 1.5 days_
  - _Requirements: DATA-003, PERF-001_

### Phase 3: Frontend Implementation
- [ ] **3.1 UI Components**
  - Create reusable UI components
  - Implement responsive design
  - Add accessibility features
  - _Estimated effort: 2 days_
  - _Requirements: UI-001, UI-002, ACC-001_

- [ ] **3.2 State Management**
  - Implement application state management
  - Add API integration layer
  - Handle loading and error states
  - _Estimated effort: 1.5 days_
  - _Requirements: UI-003, ERR-001_

- [ ] **3.3 User Workflows**
  - Implement complete user journeys
  - Add form validation and submission
  - Integrate with backend APIs
  - _Estimated effort: 2.5 days_
  - _Requirements: UX-001, UX-002_

### Phase 4: Testing and Quality Assurance
- [ ] **4.1 Unit Testing**
  - Write unit tests for business logic
  - Add API endpoint tests
  - Achieve 80%+ code coverage
  - _Estimated effort: 2 days_
  - _Requirements: TEST-001_

- [ ] **4.2 Integration Testing**
  - Write end-to-end API tests
  - Add database integration tests
  - Test external service integrations
  - _Estimated effort: 1.5 days_
  - _Requirements: TEST-002_

- [ ] **4.3 Frontend Testing**
  - Write component unit tests
  - Add user interaction tests
  - Perform cross-browser testing
  - _Estimated effort: 1.5 days_
  - _Requirements: TEST-003_

### Phase 5: Performance and Security
- [ ] **5.1 Performance Optimization**
  - Optimize database queries
  - Implement caching strategies
  - Add performance monitoring
  - _Estimated effort: 1 day_
  - _Requirements: PERF-001, PERF-002_

- [ ] **5.2 Security Hardening**
  - Implement security best practices
  - Add input validation and sanitization
  - Perform security testing
  - _Estimated effort: 1 day_
  - _Requirements: SEC-001, SEC-002_

### Phase 6: Deployment and Documentation
- [ ] **6.1 Deployment Preparation**
  - Create deployment scripts
  - Configure production environment
  - Set up monitoring and logging
  - _Estimated effort: 1 day_
  - _Requirements: OPS-001, MON-001_

- [ ] **6.2 Documentation**
  - Write API documentation
  - Create user guides
  - Document deployment procedures
  - _Estimated effort: 1 day_
  - _Requirements: DOC-001_

## Risk Mitigation Tasks
- [ ] **R.1 Dependency Management**
  - Audit third-party dependencies
  - Implement fallback mechanisms
  - Create dependency update strategy

- [ ] **R.2 Data Migration**
  - Create data migration scripts
  - Test migration procedures
  - Plan rollback strategies

## Definition of Done
Each task is considered complete when:
- [ ] Code is written and reviewed
- [ ] Unit tests are written and passing
- [ ] Integration tests are passing
- [ ] Documentation is updated
- [ ] Security review is completed
- [ ] Performance benchmarks are met

## Total Estimated Effort: 20-25 developer days

Generate a professional, comprehensive implementation plan following this exact structure with specific, actionable tasks."""
            
            ai_request = AIRequest(
                request_id=f"tasks_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.PLANNING,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=8000,
                timeout_seconds=300.0,
                preferred_models=['claude-opus-4'],
                metadata={'agent': self.config.agent_id, 'type': 'tasks'}
            )
            
            response = self.ai_broker.submit_request_sync(ai_request, timeout=120.0)
            
            if response.success:
                logger.info(f"Generated tasks using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate tasks: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating tasks: {e}")
            return None
    
    def _store_specifications(self, spec_id: str, project_id: str, specifications: Dict[str, str]):
        """Store generated specifications in the database"""
        try:
            logger.info(f"Storing specifications for spec {spec_id} in project {project_id}")
            
            # Map specification types to artifact types
            artifact_type_mapping = {
                'requirements': ArtifactType.REQUIREMENTS,
                'design': ArtifactType.DESIGN,
                'tasks': ArtifactType.TASKS
            }
            
            stored_artifacts = []
            
            for spec_type, content in specifications.items():
                if spec_type in artifact_type_mapping and content is not None:
                    artifact_type = artifact_type_mapping[spec_type]
                    
                    # Create specification artifact
                    logger.info(f"Storing {spec_type} artifact with {len(content)} characters")
                    logger.info(f"Content preview: {content[:100]}...")
                    logger.info(f"Content ending: ...{content[-100:]}")
                    
                    # Check if artifact already exists and update it, or create new one
                    artifact_id = f"{spec_id}_{artifact_type.value}"
                    existing_artifact = SpecificationArtifact.query.get(artifact_id)
                    
                    if existing_artifact:
                        # Update existing artifact
                        logger.info(f"Updating existing {spec_type} artifact")
                        existing_artifact.content = content
                        existing_artifact.updated_by = self.config.agent_id
                        existing_artifact.updated_at = datetime.utcnow()
                        existing_artifact.ai_model_used = "claude-opus-4"
                        artifact = existing_artifact
                    else:
                        # Create new artifact
                        logger.info(f"Creating new {spec_type} artifact")
                        artifact = SpecificationArtifact.create_artifact(
                            spec_id=spec_id,
                            project_id=project_id,  # Keep as string, don't convert to int
                            artifact_type=artifact_type,
                            content=content,
                            created_by=self.config.agent_id,
                            ai_generated=True,
                            ai_model_used="claude-opus-4",  # This would come from the AI response
                            context_sources=[]  # This would come from the context data
                        )
                    
                    stored_artifacts.append(artifact)
                    logger.debug(f"Created {spec_type} artifact: {len(content)} characters")
            
            # Commit all artifacts
            db.session.commit()
            logger.info(f"Successfully stored {len(stored_artifacts)} specification artifacts")
            
        except Exception as e:
            logger.error(f"Failed to store specifications: {e}")
            db.session.rollback()
            raise
    
    def _notion_sync_if_configured(self, spec_id: str, project_id: str, specifications: Dict[str, str]):
        """Optionally sync specifications to Notion if configured"""
        try:
            # Check if Notion sync is enabled for this project
            notion_sync_enabled = os.getenv('NOTION_SYNC_ENABLED', 'false').lower() == 'true'
            if not notion_sync_enabled:
                logger.debug(f"Notion sync disabled for spec {spec_id}")
                return
            
            # In a real implementation, you would:
            # 1. Check project settings for Notion integration
            # 2. Create or update Notion pages for each specification
            # 3. Handle authentication and API calls to Notion
            # 4. Track sync status and handle conflicts
            # 5. Update SpecificationArtifact records with Notion page IDs
            
            logger.info(f"Notion sync would be performed for spec {spec_id} (placeholder implementation)")
            
            # Placeholder for notion_sync functionality
            # This would integrate with Notion API to create/update pages
            # and track sync status in the SpecificationArtifact model
            
        except Exception as e:
            logger.warning(f"notion_sync failed for spec {spec_id}: {e}")


def create_define_agent(event_bus, ai_broker: Optional[AIBroker] = None) -> DefineAgent:
    """Factory function to create a Define Agent"""
    return DefineAgent(event_bus, ai_broker)