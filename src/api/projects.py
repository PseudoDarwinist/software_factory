"""
Projects API Blueprint
REST endpoints for project management operations
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
try:
    from ..models import Project, SystemMap, BackgroundJob, db
    from ..core.events import create_event, EventType
    from ..services.event_bus import publish_event
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import Project, SystemMap, BackgroundJob, db
    from core.events import create_event, EventType
    from services.event_bus import publish_event
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create blueprint
projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/api/projects', methods=['GET'])
def list_projects():
    """Get all projects with optional filtering and pagination"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 per page
        status = request.args.get('status')
        search = request.args.get('search')
        
        # Build query
        query = Project.query
        
        # Apply filters
        if status:
            query = query.filter(Project.status == status)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term),
                    Project.repository_url.ilike(search_term)
                )
            )
        
        # Order by most recent first
        query = query.order_by(Project.created_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        projects = [project.to_dict() for project in pagination.items]
        
        return jsonify({
            'projects': projects,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        return jsonify({'error': 'Failed to retrieve projects'}), 500


@projects_bp.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project by ID with detailed information"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get detailed project information
        project_data = project.to_dict()
        
        # Add system maps
        system_maps = [sm.to_dict() for sm in project.system_maps]
        project_data['system_maps'] = system_maps
        
        # Add recent conversations
        recent_conversations = [conv.to_dict() for conv in project.conversations[-5:]]  # Last 5
        project_data['recent_conversations'] = recent_conversations
        
        # Add active background jobs
        active_jobs = [job.to_dict() for job in project.background_jobs if job.is_active()]
        project_data['active_jobs'] = active_jobs
        
        return jsonify(project_data)
        
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}")
        return jsonify({'error': 'Failed to retrieve project'}), 500


@projects_bp.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Project name is required'}), 400
        
        # Check for duplicate names
        existing = Project.query.filter_by(name=name).first()
        if existing:
            return jsonify({'error': 'Project with this name already exists'}), 409
        
        # Create project
        project = Project.create(
            name=name,
            repository_url=data.get('repository_url', '').strip() or None,
            description=data.get('description', '').strip() or None
        )
        
        db.session.commit()
        
        # Publish project created event for real-time updates
        try:
            event = create_event(
                EventType.PROJECT_CREATED,
                project_name=project.name,
                project_id=project.id,
                created_by="user",  # TODO: Get actual user from session
                description=project.description,
                repository_url=project.repository_url,
                source="projects_api"
            )
            publish_event(event)
            logger.info(f"Published PROJECT_CREATED event for project {project.id}")
        except Exception as e:
            logger.error(f"Failed to publish PROJECT_CREATED event: {e}")
        
        # Start background job for repository processing if URL provided
        if project.repository_url:
            try:
                from ..services.background import get_job_manager
            except ImportError:
                from services.background import get_job_manager
            try:
                job_manager = get_job_manager()
                job_id = job_manager.submit_job(
                    job_type=BackgroundJob.TYPE_REPOSITORY_PROCESSING,
                    project_id=project.id,
                    repository_url=project.repository_url
                )
                logger.info(f"Repository processing job {job_id} submitted for project {project.id}")
            except Exception as e:
                logger.error(f"Failed to submit repository processing job for project {project.id}: {e}")
                # Continue without failing project creation
        
        logger.info(f"Created project {project.id}: {project.name}")
        return jsonify(project.to_dict()), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error creating project: {e}")
        return jsonify({'error': 'Project creation failed due to data conflict'}), 409
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create project: {e}")
        return jsonify({'error': 'Failed to create project'}), 500


@projects_bp.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update an existing project"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        # Update fields if provided
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'error': 'Project name cannot be empty'}), 400
            
            # Check for duplicate names (excluding current project)
            existing = Project.query.filter(
                Project.name == name,
                Project.id != project_id
            ).first()
            if existing:
                return jsonify({'error': 'Project with this name already exists'}), 409
            
            project.name = name
        
        if 'description' in data:
            project.description = data['description'].strip() or None
        
        if 'repository_url' in data:
            project.repository_url = data['repository_url'].strip() or None
        
        if 'status' in data:
            project.status = data['status']
        
        project.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Publish project updated event for real-time updates
        try:
            event = create_event(
                EventType.PROJECT_UPDATED,
                project_name=project.name,
                project_id=project.id,
                updated_by="user",  # TODO: Get actual user from session
                changes=list(data.keys()),
                source="projects_api"
            )
            publish_event(event)
            logger.info(f"Published PROJECT_UPDATED event for project {project.id}")
        except Exception as e:
            logger.error(f"Failed to publish PROJECT_UPDATED event: {e}")
        
        logger.info(f"Updated project {project.id}: {project.name}")
        return jsonify(project.to_dict())
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error updating project: {e}")
        return jsonify({'error': 'Project update failed due to data conflict'}), 409
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update project {project_id}: {e}")
        return jsonify({'error': 'Failed to update project'}), 500


@projects_bp.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project and all associated data"""
    try:
        project = Project.query.get_or_404(project_id)
        project_name = project.name
        
        # Cancel any active background jobs
        active_jobs = BackgroundJob.query.filter(
            BackgroundJob.project_id == project_id,
            BackgroundJob.status.in_([BackgroundJob.STATUS_PENDING, BackgroundJob.STATUS_RUNNING])
        ).all()
        
        for job in active_jobs:
            job.status = BackgroundJob.STATUS_CANCELLED
            job.completed_at = datetime.utcnow()
        
        # Delete project (cascade will handle related records)
        db.session.delete(project)
        db.session.commit()
        
        # Publish project deleted event for real-time updates
        try:
            event = create_event(
                EventType.PROJECT_DELETED,
                project_name=project_name,
                project_id=project_id,
                deleted_by="user",  # TODO: Get actual user from session
                source="projects_api"
            )
            publish_event(event)
            logger.info(f"Published PROJECT_DELETED event for project {project_id}")
        except Exception as e:
            logger.error(f"Failed to publish PROJECT_DELETED event: {e}")
        
        logger.info(f"Deleted project {project_id}: {project_name}")
        return jsonify({'message': f'Project "{project_name}" deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete project {project_id}: {e}")
        return jsonify({'error': 'Failed to delete project'}), 500


@projects_bp.route('/api/projects/<int:project_id>/system-maps', methods=['GET'])
def get_project_system_maps(project_id):
    """Get all system maps for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        system_maps = SystemMap.query.filter_by(project_id=project_id)\
                                   .order_by(SystemMap.generated_at.desc())\
                                   .all()
        
        return jsonify({
            'project_id': project_id,
            'project_name': project.name,
            'system_maps': [sm.to_dict() for sm in system_maps]
        })
        
    except Exception as e:
        logger.error(f"Failed to get system maps for project {project_id}: {e}")
        return jsonify({'error': 'Failed to retrieve system maps'}), 500


@projects_bp.route('/api/projects/<int:project_id>/conversations', methods=['GET'])
def get_project_conversations(project_id):
    """Get all conversations for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        conversations = project.conversations
        conversations.sort(key=lambda x: x.updated_at, reverse=True)
        
        return jsonify({
            'project_id': project_id,
            'project_name': project.name,
            'conversations': [conv.to_dict() for conv in conversations]
        })
        
    except Exception as e:
        logger.error(f"Failed to get conversations for project {project_id}: {e}")
        return jsonify({'error': 'Failed to retrieve conversations'}), 500


@projects_bp.route('/api/projects/<int:project_id>/jobs', methods=['GET'])
def get_project_jobs(project_id):
    """Get all background jobs for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        jobs = BackgroundJob.query.filter_by(project_id=project_id)\
                                 .order_by(BackgroundJob.created_at.desc())\
                                 .all()
        
        return jsonify({
            'project_id': project_id,
            'project_name': project.name,
            'jobs': [job.to_dict() for job in jobs]
        })
        
    except Exception as e:
        logger.error(f"Failed to get jobs for project {project_id}: {e}")
        return jsonify({'error': 'Failed to retrieve background jobs'}), 500


# Error handlers for this blueprint
@projects_bp.errorhandler(404)
def project_not_found(error):
    return jsonify({'error': 'Project not found'}), 404


@projects_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@projects_bp.errorhandler(SQLAlchemyError)
def database_error(error):
    db.session.rollback()
    logger.error(f"Database error in projects API: {error}")
    return jsonify({'error': 'Database operation failed'}), 500