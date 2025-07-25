"""
Kiro-Style Specification Generator
Mimics how Kiro works with steering documents and repository context
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class KiroStyleSpecGenerator:
    """
    Generates specifications using Kiro's approach:
    1. Automatic discovery of steering-like documents
    2. Repository-aware context building
    3. Goose + Claude Code for deep codebase understanding
    4. Fallback to Model Garden if needed
    """
    
    def __init__(self):
        self.ai_service = None
        self._initialize_ai_service()
    
    def _initialize_ai_service(self):
        """Initialize AI service for Goose and Model Garden"""
        try:
            from .ai_service import get_ai_service
            self.ai_service = get_ai_service()
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
    
    def generate_specification(self, idea_content: str, project_id: str, 
                             artifact_type: str = 'requirements') -> Optional[str]:
        """
        Generate specification using Kiro's approach
        
        Args:
            idea_content: The feature request or idea
            project_id: Project identifier
            artifact_type: 'requirements', 'design', or 'tasks'
        
        Returns:
            Generated specification content or None if failed
        """
        try:
            # Step 1: Discover steering-like documents (like Kiro's .kiro/steering/)
            steering_context = self._discover_steering_context(project_id)
            
            # Step 2: Build repository context
            repo_context = self._build_repository_context(project_id, idea_content)
            
            # Step 3: Create comprehensive context
            full_context = self._combine_contexts(steering_context, repo_context)
            
            # Step 4: Try Goose first (repository-aware)
            result = self._generate_with_goose(idea_content, full_context, artifact_type)
            if result:
                logger.info(f"Successfully generated {artifact_type} using Goose + Claude Code")
                return result
            
            # Step 5: Fallback to Model Garden
            logger.warning(f"Goose failed for {artifact_type}, falling back to Model Garden")
            result = self._generate_with_model_garden(idea_content, full_context, artifact_type)
            if result:
                logger.info(f"Successfully generated {artifact_type} using Model Garden fallback")
                return result
            
            logger.error(f"Both Goose and Model Garden failed for {artifact_type}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating {artifact_type} specification: {e}")
            return None
    
    def _discover_steering_context(self, project_id: str) -> Dict[str, Any]:
        """
        Discover steering-like documents automatically (like Kiro's approach)
        
        This mimics how Kiro reads .kiro/steering/*.md files
        """
        steering_context = {
            'product_info': None,
            'tech_stack': None,
            'architecture': None,
            'patterns': None,
            'business_domain': None
        }
        
        try:
            # In a real implementation, this would:
            # 1. Scan the repository for documentation files
            # 2. Look for README.md, docs/, architecture files
            # 3. Parse package.json/requirements.txt for tech stack
            # 4. Analyze existing code patterns
            
            # For now, we'll use project metadata and repository scanning via Goose
            steering_context['discovery_method'] = 'repository_scan'
            steering_context['project_id'] = project_id
            
            logger.info(f"Discovered steering context for project {project_id}")
            
        except Exception as e:
            logger.warning(f"Failed to discover steering context: {e}")
        
        return steering_context
    
    def _build_repository_context(self, project_id: str, idea_content: str) -> Dict[str, Any]:
        """
        Build repository context by analyzing the codebase
        """
        repo_context = {
            'similar_features': [],
            'relevant_files': [],
            'api_patterns': [],
            'database_models': [],
            'ui_components': [],
            'tech_stack_analysis': None
        }
        
        try:
            # This would be enhanced to actually scan the repository
            # For now, we'll let Goose do the heavy lifting
            repo_context['analysis_method'] = 'goose_repository_scan'
            repo_context['idea_content'] = idea_content
            
            logger.info(f"Built repository context for project {project_id}")
            
        except Exception as e:
            logger.warning(f"Failed to build repository context: {e}")
        
        return repo_context
    
    def _combine_contexts(self, steering_context: Dict[str, Any], 
                         repo_context: Dict[str, Any]) -> str:
        """
        Combine all contexts into a comprehensive prompt context
        """
        context_parts = []
        
        context_parts.append("=== KIRO-STYLE CONTEXT ANALYSIS ===")
        context_parts.append("You have full repository access like Kiro. Use it to understand:")
        context_parts.append("- Current codebase architecture and patterns")
        context_parts.append("- Existing similar features and implementations")
        context_parts.append("- Technology stack and dependencies")
        context_parts.append("- Database schemas and API patterns")
        context_parts.append("- UI components and design patterns")
        context_parts.append("")
        
        if steering_context.get('project_id'):
            context_parts.append(f"=== PROJECT CONTEXT ===")
            context_parts.append(f"Project ID: {steering_context['project_id']}")
            context_parts.append(f"Analysis Method: {steering_context.get('discovery_method', 'unknown')}")
            context_parts.append("")
        
        if repo_context.get('idea_content'):
            context_parts.append("=== REPOSITORY ANALYSIS REQUIRED ===")
            context_parts.append("Before generating the specification, analyze the repository to understand:")
            context_parts.append("1. Existing similar features or components")
            context_parts.append("2. Current architectural patterns and conventions")
            context_parts.append("3. Database models and API endpoints")
            context_parts.append("4. Frontend components and styling approaches")
            context_parts.append("5. Testing patterns and infrastructure")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _generate_with_goose(self, idea_content: str, context: str, 
                           artifact_type: str) -> Optional[str]:
        """
        Generate specification using Goose + Claude Code (repository-aware)
        """
        if not self.ai_service:
            logger.error("AI service not available")
            return None
        
        try:
            # Create Kiro-style prompt
            prompt = self._create_kiro_prompt(idea_content, context, artifact_type)
            
            # Business context for Goose
            business_context = {
                'domain': 'Software Development Lifecycle Platform',
                'useCase': f'Generate {artifact_type} specification with repository awareness',
                'targetAudience': 'Enterprise development teams',
                'keyRequirements': 'Repository-aware, contextual specifications that reference actual code',
                'successMetrics': 'Specifications that integrate seamlessly with existing codebase'
            }
            
            # GitHub repo info for repository scanning
            github_repo = {
                'connected': True,
                'name': 'Software Factory',
                'fullName': 'software-factory/main',
                'branch': 'main',
                'private': True
            }
            
            # Execute with Goose
            result = self.ai_service.execute_goose_task(
                instruction=prompt,
                business_context=business_context,
                github_repo=github_repo,
                role='business'
            )
            
            if result.get('success') and result.get('output'):
                return result['output']
            else:
                logger.error(f"Goose generation failed: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error with Goose generation: {e}")
            return None
    
    def _generate_with_model_garden(self, idea_content: str, context: str, 
                                  artifact_type: str) -> Optional[str]:
        """
        Fallback to Model Garden for specification generation
        """
        if not self.ai_service:
            logger.error("AI service not available")
            return None
        
        try:
            # Create prompt for Model Garden
            prompt = self._create_fallback_prompt(idea_content, context, artifact_type)
            
            # Product context for Model Garden
            product_context = {
                'productVision': 'AI-native Software Development Lifecycle Platform',
                'targetUsers': 'Enterprise development teams',
                'sprintGoal': f'Generate comprehensive {artifact_type} specification',
                'keyEpics': 'Context-aware specification generation',
                'acceptanceCriteria': 'Professional, actionable specifications'
            }
            
            # Execute with Model Garden
            result = self.ai_service.execute_model_garden_task(
                instruction=prompt,
                product_context=product_context,
                model='claude-opus-4',
                role='po'
            )
            
            if result.get('success') and result.get('output'):
                return result['output']
            else:
                logger.error(f"Model Garden generation failed: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error with Model Garden generation: {e}")
            return None
    
    def _create_kiro_prompt(self, idea_content: str, context: str, artifact_type: str) -> str:
        """
        Create a Kiro-style prompt that leverages repository access
        """
        base_prompt = f"""You are an AI assistant like Kiro, with full filesystem access to analyze the repository and understand the codebase.

{context}

FEATURE REQUEST:
{idea_content}

INSTRUCTIONS:
1. **ANALYZE THE REPOSITORY FIRST**: Use your filesystem access to examine:
   - Project structure and organization
   - Existing similar features and their implementation patterns
   - Technology stack (package.json, requirements.txt, etc.)
   - Database schemas and models
   - API patterns and routing structures
   - Component architectures and relationships
   - Testing patterns and infrastructure
   - Documentation and README files

2. **UNDERSTAND THE CONTEXT**: Like Kiro reads steering documents, understand:
   - The business domain and user workflows
   - Architectural patterns and conventions
   - Integration points and dependencies
   - Coding standards and best practices

3. **GENERATE CONTEXTUAL SPECIFICATION**: Create a {artifact_type}.md that:
   - References actual files, classes, and patterns from the codebase
   - Follows established architectural patterns
   - Integrates with existing APIs and data models
   - Uses the same technology stack and conventions
   - Mentions specific files that need modification or creation
   - Provides implementation guidance based on existing patterns
"""
        
        if artifact_type == 'requirements':
            return base_prompt + """

4. **REQUIREMENTS STRUCTURE**: Generate a comprehensive requirements.md with:

# Requirements Document

## 1. Repository Analysis Summary
- **Current Architecture**: Key patterns and structures found
- **Similar Features**: Existing implementations to reference
- **Integration Points**: Specific files/components to modify
- **Technology Stack**: Confirmed from repository analysis

## 2. Executive Summary
- Feature overview and business value
- Integration with existing system architecture
- Key stakeholders and success metrics

## 3. Business Requirements
### 3.1 User Stories (5-8 stories)
**As a [user], I want [capability] so that [benefit]**

### 3.2 Business Rules and Workflows
- Key business logic requirements
- Data validation rules
- User workflow specifications

## 4. Functional Requirements
### 4.1 Core Functionality (8-12 requirements)
**REQ-001**: WHEN [condition] THEN system SHALL [behavior]
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

        elif artifact_type == 'design':
            return base_prompt + """

4. **DESIGN STRUCTURE**: Generate a comprehensive design.md with:

# Technical Design Document

## 1. Repository Architecture Analysis
- **Current Patterns**: Architectural patterns identified in codebase
- **Similar Components**: Existing implementations to extend/reference
- **Integration Points**: Specific files and systems to integrate with
- **Technology Assessment**: Current stack and compatibility analysis

## 2. System Design Overview
### 2.1 Architecture Integration
- How this feature fits into existing architecture
- Components to reuse vs. create new
- Data flow integration with existing systems

### 2.2 Design Principles
- Consistency with existing patterns
- Scalability considerations
- Maintainability and extensibility

## 3. Detailed Technical Design
### 3.1 Backend Design
- API endpoints following existing patterns
- Database schema changes and migrations
- Business logic integration
- Service layer modifications

### 3.2 Frontend Design
- Component architecture following existing patterns
- State management integration
- UI/UX consistency with existing design system
- Routing and navigation updates

### 3.3 Data Design
- Database schema modifications
- Data migration strategies
- API contract specifications
- Caching and performance considerations

## 4. Implementation Strategy
### 4.1 Development Approach
- Phased implementation plan
- Integration with existing development workflow
- Testing strategy alignment

### 4.2 Risk Mitigation
- Technical risks and mitigation strategies
- Backward compatibility considerations
- Performance impact assessment

Generate a detailed technical design that seamlessly integrates with the existing codebase architecture."""

        elif artifact_type == 'tasks':
            return base_prompt + """

4. **TASKS STRUCTURE**: Generate a comprehensive tasks.md with:

# Implementation Tasks

## 1. Repository Integration Analysis
- **Existing Patterns**: Development and testing patterns to follow
- **Build Process**: Integration with current CI/CD and build systems
- **Code Organization**: Following existing module and component structure
- **Dependencies**: Compatibility with existing package management

## 2. Implementation Phases

### Phase 1: Foundation Setup
- [ ] **Environment Setup**
  - Configure development environment following existing patterns
  - Update dependencies and package configurations
  - Set up testing infrastructure extensions
  - _Effort: X hours_ | _Files: package.json, requirements.txt, etc._

### Phase 2: Backend Implementation
- [ ] **Database Changes**
  - Create migration scripts following existing patterns
  - Update ORM models and relationships
  - _Effort: X hours_ | _Files: migrations/, models/_

- [ ] **API Development**
  - Implement endpoints following existing API patterns
  - Add authentication/authorization using existing middleware
  - _Effort: X hours_ | _Files: api/, routes/_

### Phase 3: Frontend Implementation
- [ ] **Component Development**
  - Create UI components following existing design system
  - Integrate with existing state management
  - _Effort: X hours_ | _Files: components/, pages/_

### Phase 4: Integration & Testing
- [ ] **Testing Implementation**
  - Write tests following existing testing patterns
  - Integration with existing test suites
  - _Effort: X hours_ | _Files: tests/, __tests__/_

### Phase 5: Documentation & Deployment
- [ ] **Documentation Updates**
  - Update README and API documentation
  - Follow existing documentation patterns
  - _Effort: X hours_ | _Files: docs/, README.md_

## 3. Specific File Modifications
### 3.1 Files to Modify
- List specific existing files that need changes
- Explain the nature of modifications needed

### 3.2 New Files to Create
- Specify new files following existing naming conventions
- Explain their role in the overall architecture

## 4. Quality Assurance
### 4.1 Testing Strategy
- Unit tests following existing patterns
- Integration tests with existing systems
- End-to-end testing approach

### 4.2 Code Review Checklist
- Consistency with existing code style
- Integration with existing patterns
- Performance and security considerations

Generate a detailed, actionable implementation plan that integrates seamlessly with the existing development workflow and codebase patterns."""

        return base_prompt
    
    def _create_fallback_prompt(self, idea_content: str, context: str, artifact_type: str) -> str:
        """
        Create a fallback prompt for Model Garden when Goose is not available
        """
        return f"""You are a senior software architect and product manager. Generate a comprehensive {artifact_type} specification.

CONTEXT:
{context}

FEATURE REQUEST:
{idea_content}

Generate a professional, detailed {artifact_type}.md document that follows enterprise software development best practices. Focus on creating actionable, implementable specifications that would fit into a modern software development lifecycle platform.

The specification should be comprehensive, well-structured, and ready for implementation by a development team."""


# Global instance
_kiro_spec_generator = None


def get_kiro_spec_generator() -> KiroStyleSpecGenerator:
    """Get the global Kiro-style specification generator instance"""
    global _kiro_spec_generator
    if _kiro_spec_generator is None:
        _kiro_spec_generator = KiroStyleSpecGenerator()
    return _kiro_spec_generator