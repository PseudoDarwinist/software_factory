"""
Mission Control API Blueprint
REST endpoints for Mission Control functionality
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import text
try:
    from ..models import (
        MissionControlProject, FeedItem, Stage, StageTransition, 
        ProductBrief, ChannelMapping, SpecificationArtifact, ArtifactType, ArtifactStatus, db
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import (
        MissionControlProject, FeedItem, Stage, StageTransition, 
        ProductBrief, ChannelMapping, SpecificationArtifact, ArtifactType, ArtifactStatus, db
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
        github_token = data.get('githubToken')  # Optional GitHub token
        slack_channels = data.get('slackChannels', [])  # List of channel IDs
        
        # Enhanced debugging for each field
        print(f"DEBUG: Extracted fields - name: '{name}' (type: {type(name)})")
        print(f"DEBUG: Extracted fields - repo_url: '{repo_url}' (type: {type(repo_url)})")
        print(f"DEBUG: Extracted fields - github_token: {'***masked***' if github_token else 'None'} (provided: {bool(github_token)})")
        print(f"DEBUG: Extracted fields - slack_channels: {slack_channels} (type: {type(slack_channels)}, len: {len(slack_channels) if slack_channels else 'N/A'})")
        
        logger.info(f"Creating project with data: name={name}, repo_url={repo_url}, github_token={'***masked***' if github_token else 'None'}, slack_channels={slack_channels}")
        print(f"DEBUG: Creating project with data: name={name}, repo_url={repo_url}, github_token={'***masked***' if github_token else 'None'}, slack_channels={slack_channels}")
        
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
            github_token=github_token,  # Store GitHub token
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
    """Delete a Mission Control project and all related data"""
    try:
        logger.info(f"Starting deletion of Mission Control project: {project_id}")
        
        # Check if project exists
        project = db.session.get(MissionControlProject, project_id)
        if not project:
            logger.warning(f"Project not found for deletion: {project_id}")
            return jsonify({
                'success': False,
                'error': 'Project not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        project_name = project.name
        # Store project data before deletion
        project_data = project.to_dict()
        
        logger.info(f"Deleting all related data for project: {project_name} ({project_id})")
        
        # Simple approach: delete only the data we know exists based on the debug output
        # The debug showed that stage_transition has 21 records, so let's focus on that
        
        try:
            # Delete StageTransitions first (we know this has data)
            deleted_transitions = StageTransition.query.filter_by(project_id=project_id).delete(synchronize_session=False)
            logger.info(f"Deleted {deleted_transitions} StageTransition records for project {project_id}")
            
            # Delete other related data that might exist
            deleted_stages = Stage.query.filter_by(project_id=project_id).delete(synchronize_session=False)
            if deleted_stages > 0:
                logger.info(f"Deleted {deleted_stages} Stage records for project {project_id}")
            
            deleted_feed_items = FeedItem.query.filter_by(project_id=project_id).delete(synchronize_session=False)
            if deleted_feed_items > 0:
                logger.info(f"Deleted {deleted_feed_items} FeedItem records for project {project_id}")
            
            deleted_briefs = ProductBrief.query.filter_by(project_id=project_id).delete(synchronize_session=False)
            if deleted_briefs > 0:
                logger.info(f"Deleted {deleted_briefs} ProductBrief records for project {project_id}")
            
            deleted_specs = SpecificationArtifact.query.filter_by(project_id=project_id).delete(synchronize_session=False)
            if deleted_specs > 0:
                logger.info(f"Deleted {deleted_specs} SpecificationArtifact records for project {project_id}")
            
            deleted_channels = ChannelMapping.query.filter_by(project_id=project_id).delete(synchronize_session=False)
            if deleted_channels > 0:
                logger.info(f"Deleted {deleted_channels} ChannelMapping records for project {project_id}")
            
            # Commit all deletions at once
            db.session.commit()
            logger.info(f"Successfully committed all related data deletions for project {project_id}")
            
        except Exception as e:
            logger.error(f"Error during related data cleanup for project {project_id}: {e}")
            try:
                db.session.rollback()
            except:
                pass
            # Continue with project deletion anyway
        
        # Delete the project itself
        try:
            # Refresh the project object in case it was modified during related data deletion
            project = db.session.get(MissionControlProject, project_id)
            if project:
                db.session.delete(project)
                db.session.commit()
                logger.info(f"Successfully deleted Mission Control project: {project_name} ({project_id})")
            else:
                logger.warning(f"Project {project_id} was already deleted during related data cleanup")
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting project record {project_id}: {e}")
            
            # Final fallback - try direct SQL deletion
            try:
                logger.info(f"Attempting direct SQL deletion for project {project_id}")
                db.session.execute(text("DELETE FROM mission_control_project WHERE id = :project_id"), {"project_id": project_id})
                db.session.commit()
                logger.info(f"Successfully deleted project {project_id} using direct SQL")
            except Exception as sql_error:
                db.session.rollback()
                logger.error(f"Direct SQL deletion also failed for project {project_id}: {sql_error}")
                raise sql_error
        
        return jsonify({
            'success': True,
            'data': project_data,
            'message': f'Project "{project_name}" and all related data deleted successfully',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass
        
        error_msg = str(e)
        logger.error(f"Error deleting Mission Control project {project_id}: {error_msg}", exc_info=True)
        
        # Provide more specific error information for debugging
        if "foreign key" in error_msg.lower():
            error_msg = f"Cannot delete project due to foreign key constraints: {error_msg}"
        elif "does not exist" in error_msg.lower():
            error_msg = f"Database table missing: {error_msg}"
        else:
            error_msg = f"Database error during deletion: {error_msg}"
        
        return jsonify({
            'success': False,
            'error': error_msg,
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
        
        # Import required modules at the top of the action handling
        from sqlalchemy.orm.attributes import flag_modified
        from datetime import timedelta
        
        # Handle different actions
        if action == 'promote':
            # Move item to Define stage
            current_metadata = feed_item.meta_data or {}
            current_metadata['stage'] = 'define'
            feed_item.meta_data = current_metadata
            feed_item.updated_at = datetime.utcnow()
            
            # Mark SQLAlchemy that JSON column changed (required for PostgreSQL)
            flag_modified(feed_item, 'meta_data')
            
            logger.info(f'Promoted feed item {item_id} to Define stage')
            
        elif action == 'snooze':
            # Snooze item for 24 hours
            snooze_until = datetime.utcnow() + timedelta(hours=24)
            
            current_metadata = feed_item.meta_data or {}
            current_metadata['snoozed'] = True
            current_metadata['snoozeUntil'] = snooze_until.isoformat()
            feed_item.meta_data = current_metadata
            feed_item.updated_at = datetime.utcnow()
            
            # Mark SQLAlchemy that JSON column changed
            flag_modified(feed_item, 'meta_data')
            
            logger.info(f'Snoozed feed item {item_id} until {snooze_until}')
            
        else:
            # Default action - just update summary
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


@mission_control_bp.route('/api/specification/<item_id>', methods=['GET'])
def get_specification(item_id):
    """Get specification artifacts for a feed item"""
    try:
        project_id = request.args.get('projectId')
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'projectId parameter is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Create spec_id from item_id
        spec_id = f"spec_{item_id}"
        
        # Get all specification artifacts for this spec AND project
        specs = SpecificationArtifact.query.filter_by(
            spec_id=spec_id, 
            project_id=project_id
        ).all()
        
        if not specs:
            # No specifications exist yet - return empty structure
            return jsonify({
                'success': True,
                'data': {
                    'spec_id': spec_id,
                    'project_id': project_id,
                    'requirements': None,
                    'design': None,
                    'tasks': None,
                    'completion_status': {
                        'complete': False,
                        'total_artifacts': 0,
                        'ai_draft': 0,
                        'human_reviewed': 0,
                        'frozen': 0,
                        'ready_to_freeze': False
                    }
                },
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            })
        
        # Build specification set
        spec_set = {
            'spec_id': spec_id,
            'project_id': project_id,
            'requirements': None,
            'design': None,
            'tasks': None
        }
        
        # Organize specs by type
        for spec in specs:
            artifact_type = spec.artifact_type.value
            spec_set[artifact_type] = spec.to_dict()
        
        # Calculate completion status
        status_counts = {'ai_draft': 0, 'human_reviewed': 0, 'frozen': 0}
        for spec in specs:
            status_counts[spec.status.value] += 1
        
        completion_status = {
            'complete': len(specs) == 3,  # requirements, design, tasks
            'total_artifacts': len(specs),
            'ai_draft': status_counts['ai_draft'],
            'human_reviewed': status_counts['human_reviewed'],
            'frozen': status_counts['frozen'],
            'ready_to_freeze': (
                len(specs) == 3 and 
                status_counts['ai_draft'] == 0 and 
                status_counts['frozen'] == 0
            )
        }
        
        spec_set['completion_status'] = completion_status
        
        return jsonify({
            'success': True,
            'data': spec_set,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get specification for {item_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve specification',
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