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
            
            # Generate requirements.md
            requirements_md = self._generate_requirements(idea_content, ai_context)
            if not requirements_md:
                return None
            
            # Generate design.md
            design_md = self._generate_design(idea_content, requirements_md, ai_context)
            if not design_md:
                return None
            
            # Generate tasks.md
            tasks_md = self._generate_tasks(idea_content, requirements_md, design_md, ai_context)
            if not tasks_md:
                return None
            
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
        """Prepare comprehensive context for AI specification generation"""
        context_parts = []
        
        # Add project information
        if project_context.system_map:
            context_parts.append("=== PROJECT SYSTEM MAP ===")
            context_parts.append(str(project_context.system_map))
        
        # Add similar specifications
        if context_data.get('similar_specs'):
            context_parts.append("=== SIMILAR SPECIFICATIONS ===")
            for spec in context_data['similar_specs']:
                context_parts.append(f"[{spec.get('relevance_reason', 'Similar spec')}]")
                context_parts.append(spec.get('content', '')[:500] + "...")
        
        # Add related documentation
        if context_data.get('related_docs'):
            context_parts.append("=== RELATED DOCUMENTATION ===")
            for doc in context_data['related_docs']:
                context_parts.append(f"[{doc.get('relevance_reason', 'Related doc')}]")
                context_parts.append(doc.get('content', '')[:300] + "...")
        
        # Add similar code for implementation context
        if context_data.get('similar_code'):
            context_parts.append("=== SIMILAR CODE PATTERNS ===")
            for code in context_data['similar_code']:
                context_parts.append(f"[{code.get('relevance_reason', 'Similar code')}]")
                context_parts.append(code.get('content', '')[:200] + "...")
        
        return "\n\n".join(context_parts)
    
    def _generate_requirements(self, idea_content: str, ai_context: str) -> Optional[str]:
        """Generate requirements.md using AI"""
        try:
            prompt = f"""You are a senior product manager and business analyst. Create a comprehensive requirements document for the following feature request.

FEATURE REQUEST:
{idea_content}

PROJECT CONTEXT:
{ai_context}

Create a requirements.md document with the following structure:

# Requirements Document

## 1. Executive Summary
- Brief overview of the feature and its business value
- Key stakeholders and target users
- Success metrics and KPIs

## 2. Business Requirements
### 2.1 Business Objectives
- Primary business goals this feature addresses
- Expected ROI and business impact
- Alignment with company strategy

### 2.2 User Stories
For each major user type, write stories in format:
**As a [user type], I want [capability] so that [benefit]**

## 3. Functional Requirements
### 3.1 Core Functionality
List numbered requirements using EARS format:
- **REQ-001**: WHEN [trigger condition] THEN the system SHALL [required behavior]
- **REQ-002**: WHEN [trigger condition] THEN the system SHALL [required behavior]

### 3.2 User Interface Requirements
- Screen layouts and navigation flows
- Input validation and error handling
- Accessibility requirements (WCAG 2.1 AA compliance)

### 3.3 Integration Requirements
- External system integrations
- API requirements and data formats
- Third-party service dependencies

## 4. Non-Functional Requirements
### 4.1 Performance Requirements
- Response time requirements
- Throughput and scalability targets
- Resource utilization limits

### 4.2 Security Requirements
- Authentication and authorization
- Data protection and privacy
- Compliance requirements (GDPR, SOX, etc.)

### 4.3 Reliability Requirements
- Availability targets (uptime %)
- Error handling and recovery
- Backup and disaster recovery

## 5. Acceptance Criteria
For each requirement, define testable acceptance criteria:
- **Given** [initial context]
- **When** [action is performed]
- **Then** [expected outcome]

## 6. Constraints and Assumptions
### 6.1 Technical Constraints
- Technology stack limitations
- Infrastructure constraints
- Legacy system dependencies

### 6.2 Business Constraints
- Budget limitations
- Timeline constraints
- Resource availability

## 7. Risks and Mitigation
- Identified risks and their impact
- Mitigation strategies
- Contingency plans

Generate a professional, comprehensive requirements document following this exact structure."""
            
            ai_request = AIRequest(
                request_id=f"requirements_{uuid.uuid4().hex[:8]}",
                task_type=TaskType.DOCUMENTATION,
                instruction=prompt,
                priority=Priority.HIGH,
                max_tokens=3000,
                timeout_seconds=300.0,
                preferred_models=['claude-opus-4'],
                metadata={'agent': self.config.agent_id, 'type': 'requirements'}
            )
            
            logger.info(f"Submitting AI request with model: {ai_request.preferred_models}, timeout: 300s")
            logger.info(f"Request ID: {ai_request.request_id}, Task type: {ai_request.task_type}")
            logger.info(f"Prompt length: {len(prompt)} characters")
            
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
                logger.info(f"Generated requirements using {response.model_used}")
                return response.content
            else:
                logger.error(f"Failed to generate requirements: {response.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating requirements: {e}")
            return None
    
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
                max_tokens=4000,
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
                max_tokens=3000,
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
                if spec_type in artifact_type_mapping:
                    artifact_type = artifact_type_mapping[spec_type]
                    
                    # Create specification artifact
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