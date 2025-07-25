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
            requirements_md = self._generate_requirements(idea_content, ai_context, project_context)
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
    
    def _generate_requirements(self, idea_content: str, ai_context: str, project_context: ProjectContext = None) -> Optional[str]:
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
            
            # Create clean DefineAgent prompt with only system map context
            clean_prompt = self._create_clean_define_agent_prompt(idea_content, ai_context)
            
            # Try Claude Code SDK first as primary option
            logger.info("Trying Claude Code SDK as primary AI provider")
            try:
                try:
                    from ..services.claude_code_service import ClaudeCodeService
                except ImportError:
                    from services.claude_code_service import ClaudeCodeService
                
                # Get the correct repository path for this project  
                repo_path = self._get_project_repository_path(project_context)
                logger.info(f"Using repository path for Claude Code SDK: {repo_path}")
                
                claude_service = ClaudeCodeService(repo_path)
                logger.info(f"Claude Code SDK service created, checking availability...")
                
                if claude_service.is_available():
                    logger.info("✅ Claude Code SDK is available, using as primary provider")
                    
                    result = claude_service.create_specification(idea_content, ai_context)
                    logger.info(f"Claude Code SDK result: success={result.get('success')}")
                    
                    if result.get('success'):
                        logger.info("✅ Claude Code SDK successfully generated requirements")
                        return result.get('output', '')
                    else:
                        logger.error(f"❌ Claude Code SDK failed: {result.get('error')}")
                else:
                    logger.warning("❌ Claude Code SDK not available, trying AI Broker fallback")
            
            except Exception as e:
                logger.error(f"Claude Code SDK primary attempt failed: {e}")
            
            # Fallback to AI Broker with other models
            logger.info("Falling back to AI Broker (Model Garden + Goose)")
            ai_request = AIRequest(
                request_id=f"requirements_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=clean_prompt,  # Clean DefineAgent prompt only
                priority=Priority.HIGH,
                max_tokens=32000,
                timeout_seconds=300.0,
                preferred_models=['claude-opus-4'],  # Use Model Garden Anthropic model only
                metadata={'agent': self.config.agent_id, 'type': 'requirements', 'approach': 'clean_define_agent'}
            )
            
            logger.info(f"Submitting clean DefineAgent request with models: {ai_request.preferred_models}")
            logger.info(f"Request ID: {ai_request.request_id}, Clean prompt length: {len(clean_prompt)}")
            
            response = self.ai_broker.submit_request_sync(ai_request, timeout=120.0)
            
            # The clean prompt should work for both GooseAI and Model Garden
            # No need for fallback with different prompts since we've eliminated layering
            
            if hasattr(response, 'error_message') and response.error_message:
                logger.error(f"AI response error: {response.error_message}")
            if not response.success:
                logger.error(f"AI request failed - Response: {response.__dict__}")
            
            if response.success:
                logger.info(f"Generated repository-aware requirements using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate requirements: {response.error_message}")
                
                # Try Claude Code SDK as final fallback when AI Broker fails
                if "Request timed out" in str(response.error_message) or "Model Garden" in str(response.error_message):
                    logger.info("Attempting Claude Code SDK fallback for DefineAgent")
                    try:
                        try:
                            from ..services.claude_code_service import ClaudeCodeService
                        except ImportError:
                            from services.claude_code_service import ClaudeCodeService
                        
                        # Get the correct repository path for this project
                        repo_path = self._get_project_repository_path(project_context)
                        logger.info(f"Using repository path for Claude Code SDK: {repo_path}")
                        
                        claude_service = ClaudeCodeService(repo_path)
                        
                        if claude_service.is_available():
                            logger.info("Using Claude Code SDK to generate requirements")
                            
                            # Extract system context from ai_context
                            system_context = ai_context if ai_context else ""
                            
                            result = claude_service.create_specification(idea_content, system_context)
                            
                            if result.get('success'):
                                logger.info("Claude Code SDK generated requirements")
                                return result.get('output', '')
                            else:
                                logger.error(f"Claude Code SDK failed: {result.get('error')}")
                        else:
                            logger.warning("Claude Code SDK not available for fallback")
                    
                    except ImportError:
                        logger.warning("Claude Code SDK not installed")
                    except Exception as e:
                        logger.error(f"Claude Code SDK fallback error: {e}")
                
                return None
                
        except Exception as e:
            logger.error(f"Error generating requirements: {e}")
            return None
    
    def _create_clean_define_agent_prompt(self, idea_content: str, ai_context: str) -> str:
        """Create ultra-simple prompt for GooseAI to handle without timeout"""
        
        # Ultra-minimal prompt under 1000 characters
        simple_prompt = f"""Analyze repository and create requirements.md for: {idea_content}

1. Examine codebase structure (src/, package.json, etc.)
2. Create requirements.md with:
   - Executive Summary
   - 3-5 User Stories  
   - 5-8 Functional Requirements (REQ-001 format)
   - Technical Implementation (files to modify)
   - Acceptance Criteria

Output complete requirements.md document."""
        
        return simple_prompt
    
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
            if response.success:
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
    
    def get_project_context(self, project_id: str) -> ProjectContext:
        """
        Retrieve and cache the project context.
        This ensures we are not repeatedly querying the database for the same information.
        """
        # Simple caching mechanism
        if hasattr(self, '_project_context_cache') and self._project_context_cache.get('project_id') == project_id:
            return self._project_context_cache['context']

        logger.info(f"Fetching project context for project_id: {project_id}")
        # Import here to avoid circular dependency at module level
        try:
            from ..models.mission_control_project import MissionControlProject
            from ..models.system_map import SystemMap
        except ImportError:
            from models.mission_control_project import MissionControlProject
            from models.system_map import SystemMap

        project = MissionControlProject.query.get(project_id)
        system_map_data = SystemMap.query.filter_by(project_id=project_id).first()

        context = ProjectContext(
            project_id=project_id,
            project_name=project.name if project else "Unknown Project",
            repo_url=project.repo_url if project else None,
            system_map=system_map_data.content if system_map_data else None
        )
        
        # Cache the result
        self._project_context_cache = {'project_id': project_id, 'context': context}
        
        return context

    def _get_project_repository_path(self, project_context: ProjectContext) -> str:
        """
        Get the local filesystem path for the project's repository.
        If the repository is remote, it will be cloned to a temporary directory.
        If it has been cloned before, the existing path will be returned.
        """
        if not project_context or not project_context.repo_url:
            logger.error("CRITICAL: No repository URL found in project context. Cannot proceed.")
            raise ValueError("Repository URL is missing from the project context.")

        try:
            import tempfile
            import hashlib
            from git import Repo

            # Create a consistent directory name from a hash of the repo URL
            repo_hash = hashlib.md5(project_context.repo_url.encode()).hexdigest()
            clone_dir = os.path.join(tempfile.gettempdir(), f"sf_project_clone_{repo_hash}")

            if os.path.exists(clone_dir):
                logger.info(f"Found existing repository clone at: {clone_dir}")
                # Optional: You could add logic here to pull latest changes
                return clone_dir
            
            # If the directory doesn't exist, clone the repository
            logger.info(f"Cloning repository {project_context.repo_url} into {clone_dir}")
            Repo.clone_from(project_context.repo_url, clone_dir, depth=1)
            logger.info(f"Successfully cloned repository.")
            return clone_dir

        except ImportError:
            logger.error("GitPython is not installed. Please install it with 'pip install GitPython'.")
            raise
        except Exception as e:
            logger.error(f"Failed to get project repository path: {e}")
            raise

    def _generate_design(self, requirements_content: str, ai_context: str, project_context: ProjectContext = None) -> Optional[str]:
        """Generate design.md. Try Claude Code SDK first, then fall back to AI Broker"""
        try:
            # --------------------------------------------
            # 1) Try Claude Code SDK / CLI (local) first
            # --------------------------------------------
            try:
                from ..services.claude_code_service import ClaudeCodeService  # type: ignore
            except ImportError:
                from services.claude_code_service import ClaudeCodeService  # type: ignore

            repo_path = self._get_project_repository_path(project_context)
            claude_service = ClaudeCodeService(repo_path)

            if claude_service.is_available():
                logger.info("Using Claude Code SDK for design generation")

                claude_prompt = f"""You are a senior software architect. Your task is to create a detailed `design.md` document based on the provided requirements.

=== APPROVED REQUIREMENTS ===
{requirements_content}

=== PROJECT CONTEXT ===
{ai_context}

TASK:
Create a comprehensive `design.md` document that extends the existing architecture, references concrete files/modules, and follows project conventions.

Follow this exact format:

# Design Document

## 1. Overview
A brief, high-level summary of the technical approach. Mention key architectural decisions and how the new feature integrates with the existing system.

## 2. Component Architecture
A breakdown of the new or modified components. Use a Mermaid diagram to illustrate relationships where helpful.

```mermaid
graph TD
    A[User via Frontend] --> B(API Endpoint: /api/new-feature);
    B --> C{{NewFeatureService}};
    C --> D[ExistingAuthService];
    C --> E[Database Models];
```

## 3. Database Design
Details of any new database tables, columns, or relationships. Include schema definitions.

**`new_feature` table:**
- `id`: PK
- `user_id`: FK to `users.id`
- `data`: TEXT
- `created_at`: TIMESTAMP

## 4. API Endpoints
Specification for any new or modified API endpoints.

- **`POST /api/new-feature`**
  - **Description**: Creates a new feature record.
  - **Request Body**: `{{ "data": "string" }}`
  - **Response**: `201 Created`

## 5. File Changes
A list of files that will be created or modified.

- **`CREATE`**: `src/services/new_feature_service.py`
- **`MODIFY`**: `src/api/routes.py` (to add new endpoint)
- **`MODIFY`**: `src/models/user.py` (if relationships are added)

Your design should be concrete, referencing the project's existing patterns and file structure.
"""

                result = claude_service.execute_task(claude_prompt)
                if result.get("success"):
                    logger.info("Claude Code SDK succeeded for design generation")
                    return result.get("output", "")
                else:
                    logger.warning(f"Claude Code SDK failed for design: {result.get('error')}")
            else:
                logger.info("Claude Code SDK not available – falling back to AI Broker")

            # -----------------------------------------------------------------
            # 2) Fallback – AI Broker with preferred Anthropic model, then Goose
            # -----------------------------------------------------------------
            prompt = f"""You are a senior software architect with full filesystem access to analyze this repository.\n\n{ai_context}\n\nINSTRUCTIONS:\n1. **ANALYZE THE REPOSITORY**: Use your filesystem access to examine\n   - Current architecture and design patterns\n   - Database schemas and data models\n   - API structures and service patterns\n   - UI/UX components and design systems\n   - Integration patterns and middleware\n\n2. **CREATE REPOSITORY-AWARE DESIGN**: Generate design.md that:\n   - Extends existing architectural patterns\n   - Integrates with current data models and APIs\n   - Follows established design conventions\n   - References specific files and components\n   - Uses the same technology stack\n\nCreate a design.md document with this structure:\n\n# Design Document\n\n## Overview\n- Feature overview and architectural approach\n- Integration with existing system components\n- Key design decisions and rationale\n\n## Architecture\n- High-level architecture diagram (Mermaid if applicable)\n- Component relationships and data flow\n- Integration points with existing services\n\n## Components and Interfaces\n- Detailed component specifications\n- API endpoints and data contracts\n- Database schema changes\n- UI/UX component specifications\n\n## Data Models\n- Entity relationships and schemas\n- Data validation and constraints\n- Migration strategies for existing data\n\n## Error Handling\n- Error scenarios and handling strategies\n- Logging and monitoring approaches\n- Fallback mechanisms\n\n## Testing Strategy\n- Unit testing approach\n- Integration testing plans\n- End-to-end testing scenarios\n\nGenerate a comprehensive, repository-aware design document."""
            
            ai_request = AIRequest(
                request_id=f"design_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=32000,
                timeout_seconds=300.0,
                preferred_models=["claude-opus-4"],
                metadata={"agent": self.config.agent_id, "type": "design"}
            )
            
            logger.info("Generating design document with AI Broker fallback")
            response = self.ai_broker.submit_request_sync(ai_request, timeout=120.0)
            
            if response.success:
                logger.info(f"Generated design document using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate design document via AI Broker: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating design document: {e}")
            return None
    
    # ------------------------------------------------------------
    # Update _generate_tasks with similar Claude-first strategy
    # ------------------------------------------------------------
    def _generate_tasks(self, requirements_content: str, design_content: str, ai_context: str, project_context: ProjectContext = None) -> Optional[str]:
        """Generate tasks.md. Try Claude Code SDK first, then AI Broker"""
        try:
            # 1) Try Claude Code SDK first
            try:
                from ..services.claude_code_service import ClaudeCodeService  # type: ignore
            except ImportError:
                from services.claude_code_service import ClaudeCodeService  # type: ignore

            repo_path = self._get_project_repository_path(project_context)
            claude_service = ClaudeCodeService(repo_path)

            if claude_service.is_available():
                logger.info("Using Claude Code SDK for tasks generation")

                claude_prompt = f"""You are an expert technical project manager. Your task is to create a detailed implementation plan in a `tasks.md` file based on the provided requirements and design documents.

=== APPROVED REQUIREMENTS ===
{requirements_content}

=== APPROVED DESIGN ===
{design_content}

=== PROJECT CONTEXT ===
{ai_context}

TASK:
Create a markdown checklist of all user stories from the requirements document. For each user story, create a set of small, one-story-point sub-tasks (with unchecked checkboxes) that break down the story into concrete implementation steps.

Follow this exact format:

# Implementation Plan

- [ ] **User Story: As a user, I want to connect my Gmail account securely, so that the application can access my emails.**
  - [ ] Implement the backend OAuth2 flow for Google API authentication in `src/services/auth_service.py`.
  - [ ] Create a new API endpoint `/api/gmail/auth/start` to initiate the OAuth flow.
  - [ ] Create a callback endpoint `/api/gmail/auth/callback` to handle the response from Google.
  - [ ] Securely store the user's refresh and access tokens in the database.
  - [ ] Build a frontend component in `src/components/` that presents the "Connect to Gmail" button.

- [ ] **User Story: As a user, I want the application to automatically scan my inbox and identify booking confirmation emails.**
  - [ ] Create a background job in `src/services/background.py` to periodically fetch new emails using the Gmail API.
  - [ ] Implement a parsing function that uses regex or a classification model to identify booking emails from their content.
  - [ ] Define a `Booking` data model in `src/models/booking.py` to store extracted information.
  - [ ] Write unit tests for the email parsing logic.

Ensure the top-level items are the user stories, and the sub-tasks are the specific technical steps to implement them.
"""

                result = claude_service.execute_task(claude_prompt)
                if result.get("success"):
                    logger.info("Claude Code SDK succeeded for tasks generation")
                    return result.get("output", "")
                else:
                    logger.warning(f"Claude Code SDK failed for tasks: {result.get('error')}")
            else:
                logger.info("Claude Code SDK not available – falling back to AI Broker")

            # 2) Fallback to AI Broker
            prompt = f"""You are a senior technical lead with full filesystem access to analyze this repository.\n\n{ai_context}\n\nINSTRUCTIONS:\n1. **ANALYZE THE REPOSITORY**: Use your filesystem access to examine current code organization, testing frameworks, and build processes.\n2. **CREATE IMPLEMENTATION PLAN**: Generate tasks.md where each checklist item is a discrete coding task that references requirements and builds incrementally.\n\nGenerate a comprehensive tasks.md document."""
            
            ai_request = AIRequest(
                request_id=f"tasks_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=32000,
                timeout_seconds=300.0,
                preferred_models=["claude-opus-4"],
                metadata={"agent": self.config.agent_id, "type": "tasks"}
            )
            
            logger.info("Generating tasks document with AI Broker fallback")
            response = self.ai_broker.submit_request_sync(ai_request, timeout=120.0)
            
            if response.success:
                logger.info(f"Generated tasks document using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate tasks document via AI Broker: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating tasks document: {e}")
            return None
    
    def generate_design_document(self, spec_id: str, project_id: str, requirements_content: str) -> Optional[str]:
        """Generate design document based on approved requirements"""
        if not self.ai_broker:
            logger.warning("AI broker not available, cannot generate design document")
            return None
        
        try:
            # Get project context
            project_context = self.get_project_context(project_id)
            
            # Prepare context for design generation
            ai_context = self._prepare_design_context(requirements_content, project_context)
            
            # Generate design document
            design_content = self._generate_design(requirements_content, ai_context, project_context)
            
            return design_content
            
        except Exception as e:
            logger.error(f"Failed to generate design document: {e}")
            return None
    
    def generate_tasks_document(self, spec_id: str, project_id: str, requirements_content: str, design_content: str) -> Optional[str]:
        """Generate tasks document based on approved requirements and design"""
        if not self.ai_broker:
            logger.warning("AI broker not available, cannot generate tasks document")
            return None
        
        try:
            # Get project context
            project_context = self.get_project_context(project_id)
            
            # Prepare context for tasks generation
            ai_context = self._prepare_tasks_context(requirements_content, design_content, project_context)
            
            # Generate tasks document
            tasks_content = self._generate_tasks(requirements_content, design_content, ai_context, project_context)
            
            return tasks_content
            
        except Exception as e:
            logger.error(f"Failed to generate tasks document: {e}")
            return None
    
    def _prepare_design_context(self, requirements_content: str, project_context: ProjectContext) -> str:
        """Prepare context for design document generation"""
        context_parts = []
        
        context_parts.append("=== REPOSITORY ANALYSIS FOR DESIGN ===")
        context_parts.append("You have full filesystem access to analyze this repository for design decisions.")
        context_parts.append("Focus on:")
        context_parts.append("- Existing architectural patterns and components")
        context_parts.append("- Database schemas and data models")
        context_parts.append("- API patterns and service structures")
        context_parts.append("- UI/UX patterns and component libraries")
        context_parts.append("")
        
        # Add project system map if available
        if project_context.system_map:
            context_parts.append("=== PROJECT SYSTEM MAP ===")
            context_parts.append(str(project_context.system_map))
            context_parts.append("")
        
        context_parts.append("=== APPROVED REQUIREMENTS ===")
        context_parts.append(requirements_content)
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _prepare_tasks_context(self, requirements_content: str, design_content: str, project_context: ProjectContext) -> str:
        """Prepare context for tasks document generation"""
        context_parts = []
        
        context_parts.append("=== REPOSITORY ANALYSIS FOR IMPLEMENTATION ===")
        context_parts.append("You have full filesystem access to analyze this repository for implementation planning.")
        context_parts.append("Focus on:")
        context_parts.append("- Existing code patterns and conventions")
        context_parts.append("- Testing frameworks and patterns")
        context_parts.append("- Build and deployment processes")
        context_parts.append("- File organization and module structure")
        context_parts.append("")
        
        # Add project system map if available
        if project_context.system_map:
            context_parts.append("=== PROJECT SYSTEM MAP ===")
            context_parts.append(str(project_context.system_map))
            context_parts.append("")
        
        context_parts.append("=== APPROVED REQUIREMENTS ===")
        context_parts.append(requirements_content)
        context_parts.append("")
        
        context_parts.append("=== APPROVED DESIGN ===")
        context_parts.append(design_content)
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _generate_design(self, requirements_content: str, ai_context: str, project_context: ProjectContext = None) -> Optional[str]:
        """Generate design.md using Claude Code SDK first, then AI Broker fallback"""
        try:
            # Try Claude Code SDK first as primary option
            logger.info("Trying Claude Code SDK for design generation")
            try:
                try:
                    from ..services.claude_code_service import ClaudeCodeService
                except ImportError:
                    from services.claude_code_service import ClaudeCodeService
                
                # Get the correct repository path for this project  
                repo_path = self._get_project_repository_path(project_context)
                logger.info(f"Using repository path for Claude Code SDK: {repo_path}")
                
                claude_service = ClaudeCodeService(repo_path)
                
                if claude_service.is_available():
                    logger.info("Using Claude Code SDK for design generation")
                    
                    # Create simplified design-specific prompt
                    design_prompt = f"""Create a design document based on these requirements:

{requirements_content}

Generate a design.md with:
1. System Architecture Overview
2. Key Components and APIs
3. Database Design
4. Integration Points

Keep it concise and focused on the core design decisions."""
                    
                    logger.info("Calling Claude Code SDK create_specification for design...")
                    result = claude_service.create_specification(design_prompt, ai_context)
                    logger.info(f"Claude Code SDK design result: {result.get('success')}, error: {result.get('error', 'None')}")
                    
                    if result.get('success'):
                        logger.info("✅ Claude Code SDK successfully generated design document")
                        return result.get('output', '')
                    else:
                        logger.error(f"❌ Claude Code SDK design failed: {result.get('error')}")
                else:
                    logger.warning("Claude Code SDK not available for design generation")
            
            except Exception as e:
                logger.error(f"Claude Code SDK design generation failed: {e}")
            
            # Fallback to AI Broker
            logger.info("Falling back to AI Broker for design generation")
            prompt = f"""Create a design document based on these requirements:

{requirements_content}

Generate a concise design.md with system architecture, components, and integration points."""
            
            ai_request = AIRequest(
                request_id=f"design_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=32000,
                timeout_seconds=300.0,
                preferred_models=['claude-opus-4'],
                metadata={'agent': self.config.agent_id, 'type': 'design'}
            )
            
            logger.info(f"Generating design document with AI Broker")
            response = self.ai_broker.submit_request_sync(ai_request, timeout=120.0)
            
            if response.success:
                logger.info(f"Generated design document using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate design document: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating design document: {e}")
            return None
    
    def _generate_tasks(self, requirements_content: str, design_content: str, ai_context: str, project_context: ProjectContext = None) -> Optional[str]:
        """Generate tasks.md using Claude Code SDK first, then AI Broker fallback"""
        try:
            # Try Claude Code SDK first as primary option
            logger.info("Trying Claude Code SDK for tasks generation")
            try:
                try:
                    from ..services.claude_code_service import ClaudeCodeService
                except ImportError:
                    from services.claude_code_service import ClaudeCodeService
                
                # Get the correct repository path for this project  
                repo_path = self._get_project_repository_path(project_context)
                logger.info(f"Using repository path for Claude Code SDK: {repo_path}")
                
                claude_service = ClaudeCodeService(repo_path)
                
                if claude_service.is_available():
                    logger.info("Using Claude Code SDK for tasks generation")
                    
                    # Create tasks-specific prompt
                    tasks_prompt = f"""Based on the approved requirements and design, create a comprehensive implementation plan with actionable coding tasks.

APPROVED REQUIREMENTS:
{requirements_content}

APPROVED DESIGN:
{design_content}

CONTEXT:
{ai_context}

Generate a tasks.md document with:
- Specific coding tasks that can be executed
- References to files that need to be created or modified
- Test-driven development approach
- Incremental implementation steps
- Integration with existing codebase patterns"""
                    
                    result = claude_service.create_specification(tasks_prompt, ai_context)
                    
                    if result.get('success'):
                        logger.info("✅ Claude Code SDK successfully generated tasks document")
                        return result.get('output', '')
                    else:
                        logger.error(f"Claude Code SDK failed: {result.get('error')}")
                else:
                    logger.warning("Claude Code SDK not available for tasks generation")
            
            except Exception as e:
                logger.error(f"Claude Code SDK tasks generation failed: {e}")
            
            # Fallback to AI Broker
            logger.info("Falling back to AI Broker for tasks generation")
            prompt = f"""You are a senior technical lead with full filesystem access to analyze this repository.

{ai_context}

APPROVED REQUIREMENTS:
{requirements_content}

APPROVED DESIGN:
{design_content}

Convert the approved requirements and design into actionable coding tasks. Focus ONLY on tasks that involve writing, modifying, or testing code."""
            
            ai_request = AIRequest(
                request_id=f"tasks_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=32000,
                timeout_seconds=300.0,
                preferred_models=['claude-opus-4'],
                metadata={'agent': self.config.agent_id, 'type': 'tasks'}
            )
            
            logger.info(f"Generating tasks document with AI Broker")
            response = self.ai_broker.submit_request_sync(ai_request, timeout=120.0)
            
            if response.success:
                logger.info(f"Generated tasks document using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate tasks document: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating tasks document: {e}")
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