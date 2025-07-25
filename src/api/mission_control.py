"""
Mission Control API Blueprint
REST endpoints for Mission Control functionality
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
try:
    from ..models import (
        MissionControlProject, FeedItem, Stage, StageTransition, 
        ProductBrief, ChannelMapping, db
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import (
        MissionControlProject, FeedItem, Stage, StageTransition, 
        ProductBrief, ChannelMapping, db
    )
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Create blueprint
mission_control_bp = Blueprint('mission_control', __name__)


# Health check endpoint
@mission_control_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'data': {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
        },
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    })


# Projects endpoints
@mission_control_bp.route('/api/mission-control/projects', methods=['GET'])
def list_mission_control_projects():
    """Get all Mission Control projects"""
    try:
        projects = MissionControlProject.query.order_by(MissionControlProject.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'data': [project.to_dict() for project in projects],
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to list Mission Control projects: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve projects',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@mission_control_bp.route('/api/mission-control/projects/<project_id>', methods=['GET'])
def get_mission_control_project(project_id):
    """Get a specific Mission Control project by ID"""
    try:
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        return jsonify({
            'success': True,
            'data': project.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get Mission Control project {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve project',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@mission_control_bp.route('/api/mission-control/projects', methods=['POST'])
def create_mission_control_project():
    """Create a new Mission Control project"""
    try:
        data = request.get_json()
        
        # Enhanced debugging - log raw request data
        print(f"DEBUG: Raw request data: {data}")
        print(f"DEBUG: Request content type: {request.content_type}")
        print(f"DEBUG: Request method: {request.method}")
        logger.info(f"Raw project creation request: {data}")
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        name = data.get('name')
        repo_url = data.get('repoUrl')
        slack_channels = data.get('slackChannels', [])  # List of channel IDs
        
        # Enhanced debugging for each field
        print(f"DEBUG: Extracted fields - name: '{name}' (type: {type(name)})")
        print(f"DEBUG: Extracted fields - repo_url: '{repo_url}' (type: {type(repo_url)})")
        print(f"DEBUG: Extracted fields - slack_channels: {slack_channels} (type: {type(slack_channels)}, len: {len(slack_channels) if slack_channels else 'N/A'})")
        
        logger.info(f"Creating project with data: name={name}, repo_url={repo_url}, slack_channels={slack_channels}")
        print(f"DEBUG: Creating project with data: name={name}, repo_url={repo_url}, slack_channels={slack_channels}")
        
        if not name or not repo_url:
            return jsonify({
                'success': False,
                'error': 'Project name and repository URL are required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Generate new project ID
        project_id = f"project_{int(datetime.utcnow().timestamp() * 1000)}_{generate_random_id()}"
        
        # Create new project
        project = MissionControlProject.create(
            id=project_id,
            name=name,
            description=f"Project created from {repo_url}",
            repo_url=repo_url,
            metadata={
                'repoUrl': repo_url,
                'systemMapGenerated': False,
                'docsUploaded': False,
            }
        )
        
        db.session.commit()
        
        # Initialize stages for the project
        stage_types = [Stage.STAGE_THINK, Stage.STAGE_DEFINE, Stage.STAGE_PLAN, 
                      Stage.STAGE_BUILD, Stage.STAGE_VALIDATE]
        for stage_type in stage_types:
            Stage.get_or_create_for_project(project_id, stage_type)
        
        # Create channel mappings for Slack integration
        print(f"DEBUG: About to process slack_channels: {slack_channels}")
        if slack_channels:
            print(f"DEBUG: Processing {len(slack_channels)} slack channels: {slack_channels}")
            logger.info(f"Processing {len(slack_channels)} slack channels: {slack_channels}")
            for channel_id in slack_channels:
                if channel_id.strip():  # Skip empty channel IDs
                    try:
                        print(f"DEBUG: Creating mapping: {channel_id.strip()} -> {project_id}")
                        logger.info(f"Creating mapping: {channel_id.strip()} -> {project_id}")
                        ChannelMapping.set_mapping(channel_id.strip(), project_id)
                        print(f"DEBUG: Successfully created mapping for {channel_id.strip()}")
                        logger.info(f"Successfully created mapping for {channel_id.strip()}")
                        
                        # Verify mapping was saved
                        saved_mapping = ChannelMapping.query.filter_by(channel_id=channel_id.strip()).first()
                        if saved_mapping:
                            print(f"DEBUG: Verified mapping exists in DB: {saved_mapping.channel_id} -> {saved_mapping.project_id}")
                        else:
                            print(f"DEBUG: WARNING - Mapping not found in DB after creation: {channel_id.strip()}")
                            
                    except Exception as e:
                        print(f"DEBUG: Failed to create mapping for {channel_id}: {e}")
                        logger.error(f"Failed to create mapping for {channel_id}: {e}")
            logger.info(f"Finished processing channel mappings for project {project_id}")
        else:
            print("DEBUG: No slack channels provided or empty array")
            logger.info("No slack channels provided")
        
        # Trigger repository processing in background (like regular projects)
        logger.info(f"Repository processing check: repo_url='{repo_url}', type={type(repo_url)}, bool={bool(repo_url)}")
        print(f"DEBUG: Repository processing check: repo_url='{repo_url}', type={type(repo_url)}, bool={bool(repo_url)}")
        
        if repo_url and repo_url.strip():
            logger.info(f"About to start repository processing for project {project_id} with repo_url: {repo_url}")
            print(f"DEBUG: About to start repository processing for project {project_id} with repo_url: {repo_url}")
            try:
                logger.info(f"Starting repository processing setup for project {project_id}")
                print(f"DEBUG: Starting repository processing setup for project {project_id}")
                
                # Submit repository processing job directly with Mission Control project
                try:
                    from ..services.background import get_job_manager, BackgroundJob
                except ImportError:
                    # Fallback for direct execution
                    import sys
                    import os
                    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                    from services.background import get_job_manager, BackgroundJob
                
                logger.info(f"Submitting repository processing job for {name}")
                print(f"DEBUG: Submitting repository processing job for {name}")
                
                # Submit repository processing job using Mission Control project directly
                job_manager = get_job_manager()
                
                job_id = job_manager.submit_job(
                    job_type=BackgroundJob.TYPE_REPOSITORY_PROCESSING,
                    project_id=project_id,  # Use Mission Control project ID directly
                    repository_url=repo_url
                )
                
                logger.info(f"Repository processing job {job_id} submitted successfully")
                print(f"DEBUG: Repository processing job {job_id} submitted successfully")
                
                # Update status to in_progress
                project.update_system_map_status('in_progress')
                
                logger.info(f"System map status updated to in_progress for project {project_id}")
                print(f"DEBUG: System map status updated to in_progress for project {project_id}")
                
                logger.info(f"Repository processing setup completed for project {project_id}")
                
            except Exception as e:
                logger.error(f"Failed to submit repository processing job for project {project_id}: {e}", exc_info=True)
                print(f"DEBUG: ERROR in repository processing setup: {e}")
                import traceback
                traceback.print_exc()
                
                # Set status to failed so user knows something went wrong
                try:
                    project.update_system_map_status('failed')
                    logger.error(f"Set system map status to failed for project {project_id}")
                except:
                    pass
                
                # Don't fail project creation, just log the error
        else:
            logger.warning(f"Skipping repository processing for project {project_id} - repo_url is empty or None")
            print(f"DEBUG: Skipping repository processing for project {project_id} - repo_url is empty or None")
        
        logger.info(f"New Mission Control project created: {name} ({project_id})")
        
        return jsonify({
            'success': True,
            'data': project.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating Mission Control project: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create project',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@mission_control_bp.route('/api/mission-control/projects/<project_id>', methods=['DELETE'])
def delete_mission_control_project(project_id):
    """Delete a Mission Control project"""
    try:
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        project_name = project.name
        
        # Delete related data
        FeedItem.query.filter_by(project_id=project_id).delete()
        Stage.query.filter_by(project_id=project_id).delete()
        StageTransition.query.filter_by(project_id=project_id).delete()
        ProductBrief.query.filter_by(project_id=project_id).delete()
        
        # Delete project
        db.session.delete(project)
        db.session.commit()
        
        logger.info(f"Deleted Mission Control project: {project_name} ({project_id})")
        
        return jsonify({
            'success': True,
            'data': project.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting Mission Control project {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete project',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@mission_control_bp.route('/api/mission-control/projects/<project_id>/system-map', methods=['GET'])
def get_project_system_map(project_id):
    """Get system map for a project"""
    try:
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        if not project.meta_data or not project.meta_data.get('systemMapPath'):
            return jsonify({
                'success': False,
                'error': 'System map not generated yet'
            }), 404
        
        # In the original Node.js version, this loads from file system
        # For now, return a placeholder - this would be integrated with system map generation
        system_map_data = {
            'projectId': project_id,
            'generated': project.meta_data.get('systemMapGenerated', False),
            'status': project.system_map_status,
            'message': 'System map integration pending'
        }
        
        return jsonify({
            'success': True,
            'data': system_map_data
        })
        
    except Exception as e:
        logger.error(f"Failed to load system map for project {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load map'
        }), 500


# Feed endpoints
@mission_control_bp.route('/api/feed', methods=['GET'])
def get_feed():
    """Get feed items with filtering and pagination"""
    try:
        # Get query parameters
        project_id = request.args.get('projectId')
        severity = request.args.get('severity')
        unread = request.args.get('unread')
        limit = int(request.args.get('limit', 20))
        cursor = request.args.get('cursor')
        
        # Build query
        query = FeedItem.query
        
        if project_id:
            query = query.filter(FeedItem.project_id == project_id)
        
        if severity:
            query = query.filter(FeedItem.severity == severity)
        
        if unread == 'true':
            query = query.filter(FeedItem.unread == True)
        
        # Sort by creation time (newest first)
        query = query.order_by(FeedItem.created_at.desc())
        
        # Apply limit
        items = query.limit(limit).all()
        total_count = query.count()
        
        return jsonify({
            'success': True,
            'data': {
                'items': [item.to_dict() for item in items],
                'total': total_count,
                'page': 1,
                'pageSize': limit,
                'hasMore': total_count > limit,
            },
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get feed: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve feed',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@mission_control_bp.route('/api/feed/<item_id>/mark-read', methods=['POST'])
def mark_feed_item_read(item_id):
    """Mark a feed item as read"""
    try:
        feed_item = FeedItem.query.get(item_id)
        if not feed_item:
            return jsonify({
                'success': False,
                'error': 'Feed item not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        feed_item.mark_read()
        
        # Update project unread count
        project = MissionControlProject.query.get(feed_item.project_id)
        if project:
            project.decrement_unread_count()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to mark feed item {item_id} as read: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark item as read',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@mission_control_bp.route('/api/feed/<item_id>/action', methods=['POST'])
def perform_feed_item_action(item_id):
    """Perform an action on a feed item"""
    try:
        data = request.get_json()
        action = data.get('action') if data else None
        
        feed_item = FeedItem.query.get(item_id)
        if not feed_item:
            return jsonify({
                'success': False,
                'error': 'Feed item not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        logger.info(f'Performing action "{action}" on feed item {item_id}')
        
        # Update feed item with action result
        feed_item.summary = f'Action "{action}" completed'
        feed_item.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to perform action on feed item {item_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to perform action',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@mission_control_bp.route('/api/feed/import', methods=['POST'])
def import_feed_item():
    """Import external feed item (e.g., from Slack bridge)"""
    try:
        item_data = request.get_json()
        if not item_data or not item_data.get('id'):
            return jsonify({
                'success': False,
                'error': 'Invalid feed item'
            }), 400
        
        # Create feed item
        feed_item = FeedItem.create(
            id=item_data['id'],
            project_id=item_data.get('projectId', 'proj-1'),  # Default project
            severity=item_data.get('severity', FeedItem.SEVERITY_INFO),
            kind=item_data.get('kind', FeedItem.KIND_IDEA),
            title=item_data['title'],
            summary=item_data.get('summary'),
            actor=item_data.get('actor'),
            metadata=item_data.get('metadata', {})
        )
        
        # Auto-add to Think stage if it's an idea
        if feed_item.kind == FeedItem.KIND_IDEA:
            think_stage = Stage.get_or_create_for_project(feed_item.project_id, Stage.STAGE_THINK)
            think_stage.add_item(feed_item.id)
        
        # Update project unread count
        project = MissionControlProject.query.get(feed_item.project_id)
        if project:
            project.increment_unread_count()
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Import feed item error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500


# Channel mapping endpoints
@mission_control_bp.route('/api/channel-mapping/<channel_id>', methods=['GET'])
def get_channel_mapping(channel_id):
    """Get project mapping for a channel"""
    try:
        project_id = ChannelMapping.get_project_for_channel(channel_id)
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Channel mapping not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        return jsonify({
            'success': True,
            'data': {'projectId': project_id},
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get channel mapping for {channel_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve channel mapping',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@mission_control_bp.route('/api/slack/channels', methods=['GET'])
def get_slack_channels():
    """Get available Slack channels for project mapping"""
    try:
        # For now, return a mock list of common channels
        # In a real implementation, this would call the Slack API to get actual channels
        mock_channels = [
            {'id': 'C1234567890', 'name': 'general', 'description': 'General discussion'},
            {'id': 'C2345678901', 'name': 'random', 'description': 'Random conversations'},
            {'id': 'C3456789012', 'name': 'customer-support', 'description': 'Customer support discussions'},
            {'id': 'C4567890123', 'name': 'product-team', 'description': 'Product team coordination'},
            {'id': 'C5678901234', 'name': 'engineering', 'description': 'Engineering discussions'},
            {'id': 'C6789012345', 'name': 'design', 'description': 'Design team collaboration'},
            {'id': 'C7890123456', 'name': 'marketing', 'description': 'Marketing team updates'},
            {'id': 'C8901234567', 'name': 'sales', 'description': 'Sales team discussions'},
        ]
        
        return jsonify({
            'success': True,
            'data': mock_channels,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get Slack channels: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve Slack channels',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@mission_control_bp.route('/api/channel-mapping', methods=['POST'])
def create_channel_mapping():
    """Create or update channel mapping"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        channel_id = data.get('channelId')
        project_id = data.get('projectId')
        
        if not channel_id or not project_id:
            return jsonify({
                'success': False,
                'error': 'Channel ID and Project ID are required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Create or update mapping
        mapping = ChannelMapping.set_mapping(channel_id, project_id)
        
        return jsonify({
            'success': True,
            'data': mapping.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create channel mapping: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create channel mapping',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


def generate_random_id():
    """Generate a random ID string"""
    import random
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))


# Error handlers for this blueprint
@mission_control_bp.errorhandler(404)
def mission_control_not_found(error):
    return jsonify({
        'success': False,
        'error': 'Resource not found',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    }), 404


@mission_control_bp.errorhandler(400)
def mission_control_bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    }), 400


@mission_control_bp.errorhandler(SQLAlchemyError)
def mission_control_database_error(error):
    db.session.rollback()
    logger.error(f"Database error in Mission Control API: {error}")
    return jsonify({
        'success': False,
        'error': 'Database operation failed',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    }), 500