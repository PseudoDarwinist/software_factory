"""
MCP External API Blueprint
REST endpoints specifically for external MCP server integration
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
import logging

try:
    from ..models import (
        MissionControlProject, FeedItem, SpecificationArtifact,
        ArtifactType, ArtifactStatus, db
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import (
        MissionControlProject, FeedItem, SpecificationArtifact,
        ArtifactType, ArtifactStatus, db
    )

logger = logging.getLogger(__name__)

# Create blueprint
mcp_external_bp = Blueprint('mcp_external', __name__)


@mcp_external_bp.route('/api/mcp/projects', methods=['GET'])
def get_projects_for_mcp():
    """Get all Mission Control projects for MCP external server"""
    try:
        projects = MissionControlProject.query.order_by(MissionControlProject.created_at.desc()).all()
        
        return jsonify({
            'projects': [project.to_dict() for project in projects],
            'total': len(projects)
        })
        
    except Exception as e:
        logger.error(f"Failed to get projects for MCP: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_external_bp.route('/api/mcp/ideas/without-specs', methods=['GET'])
def get_ideas_without_specs():
    """Get ideas (FeedItems) in Define stage that don't have specifications yet"""
    try:
        project_id = request.args.get('project_id')
        
        # Build query for ideas in Define stage only
        query = FeedItem.query.filter_by(kind=FeedItem.KIND_IDEA)
        
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        ideas = query.order_by(FeedItem.created_at.desc()).all()
        
        # Filter for Define stage ideas without specifications
        ideas_without_specs = []
        for idea in ideas:
            # Only include ideas in Define stage
            stage = idea.meta_data.get('stage') if idea.meta_data else None
            if stage != 'define':
                continue  # Skip ideas not in Define stage
            
            # Check if this idea has any specifications
            spec_id = f"spec_{idea.id}"
            specs = SpecificationArtifact.query.filter_by(spec_id=spec_id).all()
            
            if not specs:  # No specifications exist for this idea
                ideas_without_specs.append({
                    'id': idea.id,
                    'project_id': idea.project_id,
                    'title': idea.title,
                    'summary': idea.summary,
                    'severity': idea.severity,
                    'stage': stage,
                    'created_at': idea.created_at.isoformat() if idea.created_at else None,
                    'has_specs': False,
                    'ready_for_spec_generation': True
                })
        
        return jsonify({
            'ideas_without_specs': ideas_without_specs,
            'count': len(ideas_without_specs)
        })
        
    except Exception as e:
        logger.error(f"Failed to get ideas without specs: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_external_bp.route('/api/mcp/ideas/incomplete-specs', methods=['GET'])
def get_ideas_with_incomplete_specs():
    """Get ideas in Define stage that have some but not all specifications"""
    try:
        project_id = request.args.get('project_id')
        
        # Get all ideas
        query = FeedItem.query.filter_by(kind=FeedItem.KIND_IDEA)
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        ideas = query.all()
        
        incomplete_ideas = []
        for idea in ideas:
            # Only include ideas in Define stage
            stage = idea.meta_data.get('stage') if idea.meta_data else None
            if stage != 'define':
                continue  # Skip ideas not in Define stage
            
            spec_id = f"spec_{idea.id}"
            specs = SpecificationArtifact.query.filter_by(spec_id=spec_id).all()
            
            if specs and len(specs) < 3:  # Has some but not all 3 specs
                existing_types = [spec.artifact_type.value for spec in specs]
                missing_types = []
                for artifact_type in ['requirements', 'design', 'tasks']:
                    if artifact_type not in existing_types:
                        missing_types.append(artifact_type)
                
                incomplete_ideas.append({
                    'id': idea.id,
                    'project_id': idea.project_id,
                    'title': idea.title,
                    'summary': idea.summary,
                    'severity': idea.severity,
                    'stage': stage,
                    'created_at': idea.created_at.isoformat() if idea.created_at else None,
                    'existing_specs': existing_types,
                    'missing_specs': missing_types,
                    'completion_percentage': round((len(specs) / 3) * 100)
                })
        
        return jsonify({
            'ideas_with_incomplete_specs': incomplete_ideas,
            'count': len(incomplete_ideas)
        })
        
    except Exception as e:
        logger.error(f"Failed to get ideas with incomplete specs: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_external_bp.route('/api/mcp/specs/generate', methods=['POST'])
def generate_specifications():
    """Generate specifications for an idea"""
    try:
        data = request.get_json()
        
        idea_id = data.get('idea_id')
        project_id = data.get('project_id')
        spec_types = data.get('spec_types', ['requirements', 'design', 'tasks'])
        context = data.get('context', '')
        
        if not idea_id or not project_id:
            return jsonify({'error': 'idea_id and project_id are required'}), 400
        
        # Verify the idea exists
        idea = FeedItem.query.get(idea_id)
        if not idea:
            return jsonify({'error': 'Idea not found'}), 404
        
        spec_id = f"spec_{idea_id}"
        generated_specs = []
        
        # Generate each requested specification type
        for spec_type in spec_types:
            try:
                artifact_type = ArtifactType(spec_type)
                
                # Generate spec content based on type and context
                content = generate_spec_content(idea, artifact_type, context)
                
                # Create the artifact
                artifact = SpecificationArtifact.create_artifact(
                    spec_id=spec_id,
                    project_id=project_id,
                    artifact_type=artifact_type,
                    content=content,
                    created_by='mcp_external_assistant',
                    ai_generated=True,
                    ai_model_used='claude_via_mcp',
                    context_sources=['idea_context', 'external_project_context']
                )
                
                generated_specs.append({
                    'artifact_type': spec_type,
                    'artifact_id': artifact.id,
                    'status': 'ai_draft',
                    'generated': True
                })
                
            except ValueError as e:
                logger.error(f"Invalid artifact type: {spec_type}")
                continue
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'idea_id': idea_id,
            'spec_id': spec_id,
            'generated_specs': generated_specs,
            'message': f'Generated {len(generated_specs)} specifications'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to generate specifications: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_external_bp.route('/api/mcp/specs/update', methods=['PUT'])
def update_specification():
    """Update an existing specification"""
    try:
        data = request.get_json()
        
        project_id = data.get('project_id')
        spec_id = data.get('spec_id')
        artifact_type = data.get('artifact_type')
        new_content = data.get('new_content')
        update_reason = data.get('update_reason', 'Updated via MCP')
        
        if not all([project_id, spec_id, artifact_type, new_content]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Find the artifact
        artifact_id = f"{spec_id}_{artifact_type}"
        artifact = SpecificationArtifact.query.get(artifact_id)
        
        if not artifact:
            return jsonify({'error': 'Specification artifact not found'}), 404
        
        # Store previous status
        previous_status = artifact.status.value
        
        # Update the content
        artifact.update_content(
            new_content=new_content,
            updated_by='mcp_external_assistant'
        )
        
        return jsonify({
            'success': True,
            'spec_id': spec_id,
            'artifact_type': artifact_type,
            'previous_status': previous_status,
            'new_status': artifact.status.value,
            'update_reason': update_reason,
            'message': f'Updated {artifact_type}.md specification'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update specification: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_external_bp.route('/api/mcp/specs/status', methods=['GET'])
def get_spec_status():
    """Get specification status for an idea"""
    try:
        idea_id = request.args.get('idea_id')
        project_id = request.args.get('project_id')
        
        if not idea_id or not project_id:
            return jsonify({'error': 'idea_id and project_id are required'}), 400
        
        # Get the idea
        idea = FeedItem.query.get(idea_id)
        if not idea:
            return jsonify({'error': 'Idea not found'}), 404
        
        spec_id = f"spec_{idea_id}"
        specs = SpecificationArtifact.query.filter_by(spec_id=spec_id).all()
        
        # Build specification status
        specifications = {}
        for artifact_type in ['requirements', 'design', 'tasks']:
            spec = next((s for s in specs if s.artifact_type.value == artifact_type), None)
            if spec:
                specifications[artifact_type] = {
                    'exists': True,
                    'status': spec.status.value,
                    'last_updated': spec.updated_at.isoformat() if spec.updated_at else None
                }
            else:
                specifications[artifact_type] = {
                    'exists': False,
                    'status': None,
                    'last_updated': None
                }
        
        # Calculate completion status
        total_specs = 3
        completed_specs = len([s for s in specifications.values() if s['exists']])
        completion_percentage = round((completed_specs / total_specs) * 100)
        
        missing_specs = [k for k, v in specifications.items() if not v['exists']]
        ready_for_freeze = (
            completed_specs == total_specs and
            all(s.status != ArtifactStatus.AI_DRAFT for s in specs)
        )
        
        return jsonify({
            'idea_id': idea_id,
            'project_id': project_id,
            'idea_title': idea.title,
            'spec_id': spec_id,
            'specifications': specifications,
            'completion_status': {
                'total_specs': total_specs,
                'completed_specs': completed_specs,
                'completion_percentage': completion_percentage,
                'ready_for_freeze': ready_for_freeze,
                'missing_specs': missing_specs
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get spec status: {e}")
        return jsonify({'error': str(e)}), 500


def generate_spec_content(idea: FeedItem, artifact_type: ArtifactType, context: str = '') -> str:
    """Generate specification content based on idea and type"""
    
    if artifact_type == ArtifactType.REQUIREMENTS:
        return f"""# Requirements for {idea.title}

## Overview
{idea.summary}

## Context
{context}

## User Stories
- As a user, I want [user story based on {idea.title}]
- As a user, I need [functionality described in the idea]

## Acceptance Criteria
- [ ] [Criteria based on the idea requirements]
- [ ] [Additional technical requirements]
- [ ] [Quality and performance requirements]

## Technical Requirements
- Implementation approach: [To be defined based on project context]
- Integration points: [To be defined]
- Data requirements: [To be defined]

## Notes
Generated from idea: {idea.id}
Severity: {idea.severity}
Created: {idea.created_at.isoformat() if idea.created_at else 'Unknown'}
"""

    elif artifact_type == ArtifactType.DESIGN:
        return f"""# Design for {idea.title}

## Overview
Technical design for implementing: {idea.summary}

## Context
{context}

## Architecture
- Component design: [To be defined based on project architecture]
- Data flow: [To be defined]
- Integration points: [To be defined]

## API Design
- Endpoints: [To be defined]
- Request/Response formats: [To be defined]
- Authentication: [To be defined]

## Database Schema
- Tables/Collections: [To be defined]
- Relationships: [To be defined]
- Indexes: [To be defined]

## Implementation Notes
- Technology stack: [Based on project context]
- Dependencies: [To be defined]
- Testing approach: [To be defined]

## Notes
Generated from idea: {idea.id}
Based on requirements for: {idea.title}
"""

    elif artifact_type == ArtifactType.TASKS:
        return f"""# Implementation Tasks for {idea.title}

## Overview
Breaking down the implementation of: {idea.summary}

## Context
{context}

## Task Breakdown

### Task 1: Setup and Planning
- [ ] Review requirements and design documents
- [ ] Set up development environment
- [ ] Create feature branch

### Task 2: Core Implementation
- [ ] Implement core functionality for {idea.title}
- [ ] Add necessary data models
- [ ] Create API endpoints (if applicable)

### Task 3: Integration
- [ ] Integrate with existing systems
- [ ] Add error handling
- [ ] Implement logging

### Task 4: Testing
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Manual testing

### Task 5: Documentation and Deployment
- [ ] Update documentation
- [ ] Code review
- [ ] Deploy to staging
- [ ] Deploy to production

## Estimated Effort
Total: [To be estimated based on complexity]

## Dependencies
- [List any dependencies on other tasks or systems]

## Notes
Generated from idea: {idea.id}
Severity: {idea.severity} (affects priority)
"""

    else:
        return f"# {artifact_type.value.title()} for {idea.title}\n\nContent to be defined."