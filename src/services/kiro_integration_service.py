"""
Kiro Integration Service

This service provides integration with Kiro CLI for spec generation.
It handles subprocess communication, error handling, and timeout management.
"""

import os
import subprocess
import tempfile
import logging
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class KiroIntegrationService:
    """Service for integrating with Kiro CLI to generate specifications."""
    
    def __init__(self, workspace_path: Optional[str] = None, timeout: int = 120):
        """
        Initialize the Kiro Integration Service.
        
        Args:
            workspace_path: Path to the workspace directory (defaults to current directory)
            timeout: Timeout in seconds for Kiro commands (default: 120)
        """
        self.workspace_path = workspace_path or os.getcwd()
        self.timeout = timeout
        self.kiro_executable = self._find_kiro_executable()
        self._running_processes = set()  # Track running processes to prevent loops
    
    def _find_kiro_executable(self) -> Optional[str]:
        """Find the Kiro executable in the system PATH."""
        try:
            # Try common executable names
            for executable in ['kiro', 'kiro.exe']:
                result = subprocess.run(
                    ['which', executable] if os.name != 'nt' else ['where', executable],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return executable
            return None
        except Exception as e:
            logger.debug(f"Error finding Kiro executable: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        Check if Kiro CLI is available on the system.
        
        Returns:
            bool: True if Kiro is available, False otherwise
        """
        # TEMPORARILY DISABLED DUE TO INFINITE LOOP ISSUE
        # TODO: Fix the frontend loop before re-enabling
        # Silently return False to avoid log spam
        return False
        
        # Original code commented out:
        # if not self.kiro_executable:
        #     return False
        #     
        # try:
        #     result = subprocess.run(
        #         [self.kiro_executable, '--version'],
        #         capture_output=True,
        #         text=True,
        #         timeout=10,
        #         cwd=self.workspace_path
        #     )
        #     return result.returncode == 0
        # except Exception as e:
        #     logger.debug(f"Kiro availability check failed: {e}")
        #     return False
    
    def get_version(self) -> Optional[str]:
        """
        Get the version of Kiro CLI.
        
        Returns:
            str: Version string if available, None otherwise
        """
        if not self.is_available():
            return None
            
        try:
            result = subprocess.run(
                [self.kiro_executable, '--version'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.workspace_path
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"Failed to get Kiro version: {e}")
            return None
    
    def _execute_kiro_command(self, prompt: str, command_args: Optional[list] = None) -> Dict[str, Any]:
        """
        Execute a Kiro CLI command with the given prompt.
        
        Args:
            prompt: The prompt to send to Kiro
            command_args: Additional command arguments (defaults to ['chat'])
            
        Returns:
            dict: Result containing success status, content, and error information
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'Kiro CLI is not available on this system',
                'provider': 'kiro'
            }
        
        # Prevent concurrent executions that could cause loops
        if len(self._running_processes) > 0:
            return {
                'success': False,
                'error': 'Another Kiro process is already running. Please wait.',
                'provider': 'kiro'
            }
        
        # Use non-interactive mode to prevent opening new sessions
        # Try different command patterns to avoid GUI/session spawning
        if command_args is None:
            # Try headless mode first, fallback to basic chat if not supported
            command_args = ['--headless', 'chat']
        prompt_file = None
        
        try:
            # Create temporary prompt file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.md', 
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(prompt)
                prompt_file = f.name
            
            # Build command
            cmd = [self.kiro_executable] + command_args + ['--file', prompt_file]
            
            logger.info(f"Executing Kiro command: {' '.join(cmd[:2])} [with prompt file]")
            
            # Execute Kiro command with environment to prevent GUI spawning
            env = os.environ.copy()
            env.update({
                'DISPLAY': '',  # Prevent X11 GUI on Linux/Mac
                'KIRO_HEADLESS': '1',  # Custom flag for headless mode
                'NO_GUI': '1',  # Generic no-GUI flag
                'TERM': 'dumb',  # Prevent interactive terminal features
            })
            
            # Track this process to prevent concurrent executions
            process_id = id(prompt)  # Use prompt hash as process ID
            self._running_processes.add(process_id)
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=self.workspace_path,
                    env=env,
                    stdin=subprocess.DEVNULL,  # Prevent any interactive input
                    start_new_session=True  # Start in new process group for better control
                )
            finally:
                # Always remove from running processes
                self._running_processes.discard(process_id)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'content': result.stdout.strip(),
                    'provider': 'kiro',
                    'command': ' '.join(cmd[:2])
                }
            else:
                error_msg = result.stderr.strip() or f"Command failed with exit code {result.returncode}"
                logger.error(f"Kiro command failed: {error_msg}")
                
                # If headless mode failed, try fallback without headless
                if '--headless' in cmd and 'headless' in error_msg.lower():
                    logger.info("Headless mode not supported, trying fallback command")
                    fallback_cmd = [self.kiro_executable, 'chat', '--file', prompt_file]
                    
                    try:
                        fallback_result = subprocess.run(
                            fallback_cmd,
                            capture_output=True,
                            text=True,
                            timeout=self.timeout,
                            cwd=self.workspace_path,
                            env=env,
                            stdin=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        
                        if fallback_result.returncode == 0:
                            return {
                                'success': True,
                                'content': fallback_result.stdout.strip(),
                                'provider': 'kiro',
                                'command': ' '.join(fallback_cmd[:2])
                            }
                    except Exception as fallback_error:
                        logger.error(f"Fallback command also failed: {fallback_error}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'provider': 'kiro',
                    'command': ' '.join(cmd[:2])
                }
                
        except subprocess.TimeoutExpired:
            error_msg = f"Kiro command timed out after {self.timeout} seconds"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'provider': 'kiro'
            }
        except Exception as e:
            error_msg = f"Failed to execute Kiro command: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'provider': 'kiro'
            }
        finally:
            # Cleanup temporary file
            if prompt_file and os.path.exists(prompt_file):
                try:
                    os.unlink(prompt_file)
                except Exception as e:
                    logger.warning(f"Failed to cleanup prompt file {prompt_file}: {e}")
    
    def generate_requirements(self, github_url: str, idea_content: str) -> Dict[str, Any]:
        """
        Generate requirements.md using Kiro.
        
        Args:
            github_url: URL of the GitHub repository
            idea_content: The idea/feature description
            
        Returns:
            dict: Result containing generated requirements or error information
        """
        prompt = f"""Analyze this repository: {github_url}

Generate a detailed requirements.md document for this feature idea:
{idea_content}

First, examine the codebase structure, existing patterns, and technology stack to understand the context.

Create comprehensive EARS-formatted requirements covering all functionality with:

# Requirements Document

## Introduction
Brief overview of the feature and its purpose within the existing system.

## Requirements

### Requirement 1
**User Story:** As a [role], I want [feature], so that [benefit]

#### Acceptance Criteria
1. WHEN [event] THEN [system] SHALL [response]
2. IF [precondition] THEN [system] SHALL [response]

### Requirement 2
**User Story:** As a [role], I want [feature], so that [benefit]

#### Acceptance Criteria
1. WHEN [event] THEN [system] SHALL [response]
2. WHEN [event] AND [condition] THEN [system] SHALL [response]

[Continue with 5-8 requirements total]

Focus on creating requirements that are:
- Specific and testable using EARS format
- Aligned with existing codebase patterns
- Technically feasible within the current architecture
- Clear for both technical and non-technical stakeholders

Include edge cases, user experience considerations, technical constraints, and success criteria."""
        
        logger.info(f"Generating requirements for idea using Kiro (repo: {github_url})")
        return self._execute_kiro_command(prompt)
    
    def generate_design(self, github_url: str, idea_content: str, requirements_content: str) -> Dict[str, Any]:
        """
        Generate design.md using Kiro with requirements context.
        
        Args:
            github_url: URL of the GitHub repository
            idea_content: The idea/feature description
            requirements_content: Previously generated requirements
            
        Returns:
            dict: Result containing generated design or error information
        """
        prompt = f"""Repository: {github_url}

Based on these requirements:
{requirements_content}

Generate a detailed design.md document for this feature idea:
{idea_content}

Create a technical design with detailed architecture, components, APIs, data models, and error handling that:
- Follows existing architecture patterns
- Integrates with current APIs and data models  
- Addresses all requirements from the requirements document
- Includes component diagrams where appropriate
- Specifies data models and interfaces
- Covers error handling and testing strategies

# Technical Design Document

## Overview
High-level architecture and design approach

## Architecture
System architecture and component relationships

## Components and Interfaces
Detailed component specifications and API interfaces

## Data Models
Database schemas, data structures, and relationships

## Error Handling
Error scenarios, validation, and recovery strategies

## Testing Strategy
Unit, integration, and end-to-end testing approach

The design should be implementable by developers familiar with the existing codebase.

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

3. **GENERATE CONTEXTUAL SPECIFICATION**: Create a design.md that:
   - References actual files, classes, and patterns from the codebase
   - Follows established architectural patterns
   - Integrates with existing APIs and data models
   - Uses the same technology stack and conventions
   - Mentions specific files that need modification or creation
   - Provides implementation guidance based on existing patterns

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

Generate a detailed technical design that seamlessly integrates with the existing codebase architecture.
"""
        
        logger.info(f"Generating design for idea using Kiro (repo: {github_url})")
        return self._execute_kiro_command(prompt)
    
    def generate_tasks(self, github_url: str, idea_content: str, requirements_content: str, design_content: str) -> Dict[str, Any]:
        """
        Generate tasks.md using Kiro with full context.
        
        Args:
            github_url: URL of the GitHub repository
            idea_content: The idea/feature description
            requirements_content: Previously generated requirements
            design_content: Previously generated design
            
        Returns:
            dict: Result containing generated tasks or error information
        """
        prompt = f"""Repository: {github_url}

Requirements:
{requirements_content}

Design:
{design_content}

Generate a milestone-driven implementation plan for this feature idea:
{idea_content}

Convert the feature design into a series of actionable coding tasks that will implement each step in a test-driven manner. Prioritize best practices, incremental progress, and early testing, ensuring no big jumps in complexity at any stage. Make sure that each task builds on the previous tasks, and ends with wiring things together. There should be no hanging or orphaned code that isn't integrated into a previous step. Focus ONLY on tasks that involve writing, modifying, or testing code.

Create actionable coding tasks that:
- Build incrementally on existing codebase
- Follow test-driven development practices  
- Reference specific files and components from the repository
- Can be executed by a coding agent
- Are ordered logically with dependencies
- Include verification steps

Format as a numbered checklist with:
- Clear task descriptions
- Sub-tasks where appropriate (using decimal notation like 1.1, 1.2)
- Requirements references
- Specific file/component mentions

# Implementation Plan

- [ ] 1. Task description
  - Sub-task details
  - _Requirements: R1, R2_

- [ ] 2. Next task description
  - Sub-task details  
  - _Requirements: REQ-003_

Focus on tasks that involve writing, modifying, or testing code only.

DESIGN CONTEXT:
{design_content}

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

3. **GENERATE CONTEXTUAL SPECIFICATION**: Create a tasks.md that:
   - References actual files, classes, and patterns from the codebase
   - Follows established architectural patterns
   - Integrates with existing APIs and data models
   - Uses the same technology stack and conventions
   - Mentions specific files that need modification or creation
   - Provides implementation guidance based on existing patterns

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

Generate a detailed, actionable implementation plan that integrates seamlessly with the existing development workflow and codebase patterns.
"""
        
        logger.info(f"Generating tasks for idea using Kiro (repo: {github_url})")
        return self._execute_kiro_command(prompt)


# Singleton instance for global use
_kiro_service = None

def get_kiro_service() -> KiroIntegrationService:
    """Get the global Kiro integration service instance."""
    global _kiro_service
    if _kiro_service is None:
        _kiro_service = KiroIntegrationService()
    return _kiro_service