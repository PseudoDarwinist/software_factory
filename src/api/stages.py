"""
Stages API Blueprint
REST endpoints for Mission Control SDLC stage management
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
try:
    from ..models import (
        Stage, StageTransition, ProductBrief, FeedItem, 
        MissionControlProject, db
    )
    from ..events.domain_events import IdeaPromotedEvent
    from ..events.event_store import EventStore
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import (
        Stage, StageTransition, ProductBrief, FeedItem, 
        MissionControlProject, db
    )
    from events.domain_events import IdeaPromotedEvent
    from events.event_store import EventStore
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)

# Create blueprint
stages_bp = Blueprint('stages', __name__)


def _generate_design_document_core(spec_id, project_id, requirements_artifact, define_agent, provider='claude'):
    """Core design document generation logic - reusable for sync and async"""
    logger.info(f"🚀 Starting design document generation...")
    logger.info(f"   🤖 Calling DefineAgent.generate_design_document()")
    logger.info(f"   📋 Input: Requirements content ({len(requirements_artifact.content)} chars)")
    
    start_time = time.time()
    design_content = define_agent.generate_design_document(
        spec_id=spec_id,
        project_id=project_id,
        requirements_content=requirements_artifact.content,
        provider=provider
    )
    end_time = time.time()
    
    logger.info(f"✅ DefineAgent.generate_design_document() completed")
    logger.info(f"   ⏱️  Generation Time: {end_time - start_time:.2f} seconds")
    
    if not design_content:
        logger.error(f"❌ DefineAgent returned None for design content")
        raise Exception("Failed to generate design document")
    
    logger.info(f"✅ Design document generated successfully")
    if hasattr(design_content, 'content'):
        logger.info(f"   📄 Generated Content Length: {len(design_content.content)} characters")
    else:
        logger.info(f"   📄 Generated Content Type: {type(design_content)}")
    
    return design_content


def _generate_tasks_document_core(spec_id, project_id, requirements_artifact, design_artifact, define_agent, provider='claude'):
    """Core tasks document generation logic - reusable for sync and async"""
    logger.info(f"🚀 Starting tasks document generation...")
    logger.info(f"   🤖 Calling DefineAgent.generate_tasks_document()")
    logger.info(f"   📋 Input: Requirements ({len(requirements_artifact.content)} chars) + Design ({len(design_artifact.content)} chars)")
    
    start_time = time.time()
    tasks_content = define_agent.generate_tasks_document(
        spec_id=spec_id,
        project_id=project_id,
        requirements_content=requirements_artifact.content,
        design_content=design_artifact.content,
        provider=provider
    )
    end_time = time.time()
    
    logger.info(f"✅ DefineAgent.generate_tasks_document() completed")
    logger.info(f"   ⏱️  Generation Time: {end_time - start_time:.2f} seconds")
    
    if not tasks_content:
        logger.error(f"❌ DefineAgent returned None for tasks content")
        raise Exception("Failed to generate tasks document")
    
    logger.info(f"✅ Tasks document generated successfully")
    if hasattr(tasks_content, 'content'):
        logger.info(f"   📄 Generated Content Length: {len(tasks_content.content)} characters")
    else:
        logger.info(f"   📄 Generated Content Type: {type(tasks_content)}")
    
    return tasks_content


def _validate_prd_requirement(project_id, item_id):
    """
    Idea-specific PRD requirement validation.
    
    Checks for PRDs in this priority order:
    1. Idea-specific PRD (linked directly to this FeedItem)
    2. Session-based PRDs (fallback for backward compatibility)
    
    Returns:
        dict: {
            'has_prd': bool,
            'prd_status': str,  # 'missing', 'draft', 'frozen'
            'prd_type': str,    # 'idea', 'session', 'missing'
            'latest_prd': dict or None,
            'upload_sessions': list,
            'context_level': str  # Description of available context
        }
    """
    try:
        # Import PRD model
        try:
            from ..models.prd import PRD
            from ..models.upload_session import UploadSession
        except ImportError:
            from models.prd import PRD
            from models.upload_session import UploadSession
        
        # Strategy 1: Look for idea-specific PRD first (NEW ARCHITECTURE)
        idea_prd = PRD.get_for_feed_item(item_id) if item_id else None
        
        if idea_prd:
            # Found PRD specifically for this idea
            prd_status = idea_prd.status
            prd_type = 'idea'
            has_prd = idea_prd.status == 'frozen'
            
            if has_prd:
                context_level = f'Idea-specific PRD available (v{idea_prd.version}) - perfect context match'
            else:
                context_level = f'Draft idea-specific PRD (v{idea_prd.version}) - needs freezing'
            
            return {
                'has_prd': has_prd,
                'prd_status': prd_status,
                'prd_type': prd_type,
                'latest_prd': idea_prd.to_dict(),
                'upload_sessions': [],  # Not relevant for idea-specific PRDs
                'context_level': context_level,
                'total_prds': 1,
                'frozen_prds': 1 if has_prd else 0
            }
        
        # Strategy 2: Fallback to project-level session-based PRDs (BACKWARD COMPATIBILITY)
        upload_sessions = UploadSession.query.filter_by(project_id=project_id).all()
        
        project_prds = []
        all_prds = []
        
        for session in upload_sessions:
            session_prd = PRD.get_latest_for_session(str(session.id))
            if session_prd:
                all_prds.append(session_prd)
                if session_prd.status == 'frozen':
                    project_prds.append(session_prd)
        
        # Determine best available session PRD
        latest_prd = None
        prd_status = 'missing'
        prd_type = 'missing'
        context_level = 'No PRD context available - create idea-specific PRD'
        
        if project_prds:
            # Use the most recent frozen PRD
            latest_prd = max(project_prds, key=lambda p: p.created_at)
            prd_status = 'frozen'
            prd_type = 'session'
            context_level = f'Session-based PRD available (v{latest_prd.version}) - consider creating idea-specific PRD'
        elif all_prds:
            # Use the most recent PRD even if draft
            latest_prd = max(all_prds, key=lambda p: p.created_at)
            prd_status = latest_prd.status
            prd_type = 'session'
            if prd_status == 'draft':
                context_level = f'Draft session PRD (v{latest_prd.version}) - needs freezing or create idea-specific PRD'
            else:
                context_level = f'Session PRD available (v{latest_prd.version})'
        
        # For Define stage, we require at least one frozen PRD
        has_prd = latest_prd is not None and latest_prd.status == 'frozen'
        
        return {
            'has_prd': has_prd,
            'prd_status': prd_status,
            'prd_type': prd_type,
            'latest_prd': latest_prd.to_dict() if latest_prd else None,
            'upload_sessions': [{'id': str(s.id), 'description': s.description} for s in upload_sessions],
            'context_level': context_level,
            'total_prds': len(all_prds),
            'frozen_prds': len(project_prds)
        }
        
    except Exception as e:
        logger.error(f"Error validating PRD requirement: {e}")
        # Fail open - allow transition if validation fails
        return {
            'has_prd': True,
            'prd_status': 'unknown',
            'prd_type': 'unknown',
            'latest_prd': None,
            'upload_sessions': [],
            'context_level': 'PRD validation failed - allowing transition',
            'total_prds': 0,
            'frozen_prds': 0
        }


@stages_bp.route('/api/project/<project_id>/stages', methods=['GET'])
def get_project_stages(project_id):
    """Get stage data for a project"""
    try:
        # Check if project exists
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Get all stages for the project
        stages = Stage.query.filter_by(project_id=project_id).all()
        
        # Build stages data structure
        stages_data = {
            'think': [],
            'define': [],
            'plan': [],
            'build': [],
            'validate': []
        }
        
        for stage in stages:
            if stage.stage_type in stages_data:
                stages_data[stage.stage_type] = stage.item_ids or []
        
        return jsonify({
            'success': True,
            'data': stages_data,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get stages for project {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve stages',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/idea/<item_id>/move-stage', methods=['POST'])
def move_item_to_stage(item_id):
    """Move an item to a different stage"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        target_stage = data.get('targetStage')
        from_stage = data.get('fromStage')
        project_id = data.get('projectId')
        
        if not target_stage or not project_id:
            return jsonify({
                'success': False,
                'error': 'Target stage and project ID are required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Check if feed item exists
        feed_item = FeedItem.query.get(item_id)
        if not feed_item:
            return jsonify({
                'success': False,
                'error': 'Feed item not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # PRD requirement validation for Define stage
        if target_stage == 'define':
            prd_validation_result = _validate_prd_requirement(project_id, item_id)
            if not prd_validation_result['has_prd']:
                return jsonify({
                    'success': False,
                    'error': 'PRD_REQUIRED',
                    'error_details': {
                        'message': 'A Product Requirements Document (PRD) is required before moving ideas to Define stage',
                        'requirement_type': 'prd_missing',
                        'project_id': project_id,
                        'item_id': item_id,
                        'suggested_action': 'create_prd'
                    },
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0',
                }), 422  # Unprocessable Entity
        
        # Batch all operations in a single transaction
        # Remove from current stage (don't commit yet)
        if from_stage:
            from_stage_obj = Stage.get_or_create_for_project(project_id, from_stage)
            from_stage_obj.remove_item(item_id, commit=False)
        
        # Add to new stage (don't commit yet)
        to_stage_obj = Stage.get_or_create_for_project(project_id, target_stage)
        to_stage_obj.add_item(item_id, commit=False)
        
        # Record transition (don't commit yet)
        transition = StageTransition.create(
            item_id=item_id,
            project_id=project_id,
            from_stage=from_stage,
            to_stage=target_stage,
            actor='system'  # TODO: get actual user
        )
        
        # Update feed item metadata for all stage transitions (PostgreSQL JSON handling)
        from sqlalchemy.orm.attributes import flag_modified
        
        if not feed_item.meta_data:
            feed_item.meta_data = {}
        feed_item.meta_data['stage'] = target_stage
        feed_item.updated_at = datetime.utcnow()
        
        # CRITICAL: Tell SQLAlchemy that the JSON column changed (required for PostgreSQL)
        flag_modified(feed_item, 'meta_data')
        
        # If moving to Define stage, create a product brief and emit idea.promoted event
        brief = None
        if target_stage == 'define':
            # Skip ProductBrief generation for now to make drag-and-drop instant
            # brief_data = generate_product_brief_content(feed_item)
            # brief = ProductBrief.create_for_item(item_id, project_id, brief_data)
            logger.info(f"Skipping ProductBrief generation for idea {item_id} - focusing on fast UX")
            
            # Skip DefineAgent processing for now to make drag-and-drop instant
            # TODO: Move DefineAgent processing to background job
            logger.info(f"Skipping DefineAgent processing for idea {item_id} - will be handled by Create Spec button")
            
            # Skip event emission for now to make drag-and-drop instant
            # TODO: Move event emission to background job
            logger.info(f"Skipping event emission for idea {item_id} - focusing on fast UX")
        else:
            logger.info(f"Moved item {item_id} to {target_stage} stage")
        
        db.session.commit()
        
        logger.info(f"Moved item {item_id} from {from_stage} to {target_stage} in project {project_id}")
        
        response_data = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }
        
        if brief:
            response_data['data'] = {'brief': brief.to_dict()}
        
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error moving item {item_id} to stage: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to move item to stage',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/product-brief/<brief_id>', methods=['GET'])
def get_product_brief(brief_id):
    """Get a product brief by ID"""
    try:
        brief = ProductBrief.query.get(brief_id)
        if not brief:
            return jsonify({
                'success': False,
                'error': 'Product brief not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        return jsonify({
            'success': True,
            'data': brief.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get product brief {brief_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve product brief',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/product-brief/<brief_id>', methods=['PUT'])
def update_product_brief(brief_id):
    """Update a product brief"""
    try:
        brief = ProductBrief.query.get(brief_id)
        if not brief:
            return jsonify({
                'success': False,
                'error': 'Product brief not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Update brief fields
        updatable_fields = [
            'problem_statement', 'success_metrics', 'risks', 
            'competitive_analysis', 'user_stories', 'progress'
        ]
        
        updates = {}
        for field in updatable_fields:
            if field in data:
                updates[field] = data[field]
        
        if updates:
            brief.update_fields(updates)
        
        return jsonify({
            'success': True,
            'data': brief.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update product brief {brief_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update product brief',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/product-brief/<brief_id>/freeze', methods=['POST'])
def freeze_product_brief(brief_id):
    """Freeze a product brief"""
    try:
        brief = ProductBrief.query.get(brief_id)
        if not brief:
            return jsonify({
                'success': False,
                'error': 'Product brief not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        brief.freeze()
        
        return jsonify({
            'success': True,
            'data': brief.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to freeze product brief {brief_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to freeze product brief',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


# Specification Artifact endpoints
@stages_bp.route('/api/specification/<item_id>', methods=['GET'])
def get_specification(item_id):
    """Get specification artifacts for an item"""
    try:
        project_id = request.args.get('projectId')
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Import SpecificationArtifact model
        try:
            from ..models.specification_artifact import SpecificationArtifact, ArtifactType
        except ImportError:
            from models.specification_artifact import SpecificationArtifact, ArtifactType
        
        # Get all artifacts for this specification
        spec_id = f"spec_{item_id}"
        artifacts = SpecificationArtifact.get_spec_artifacts(spec_id)
        
        # Build specification set
        spec_set = {
            'spec_id': spec_id,
            'project_id': project_id,
            'requirements': None,
            'design': None,
            'tasks': None,
            'completion_status': SpecificationArtifact.get_spec_completion_status(spec_id)
        }
        
        for artifact in artifacts:
            spec_set[artifact.artifact_type.value] = artifact.to_dict()
        
        return jsonify({
            'success': True,
            'data': spec_set,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get specification for item {item_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve specification',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/specification/<spec_id>/artifact/<artifact_type>', methods=['PUT'])
def update_specification_artifact(spec_id, artifact_type):
    """Update a specification artifact"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        content = data.get('content')
        project_id = data.get('projectId')
        
        if not content or not project_id:
            return jsonify({
                'success': False,
                'error': 'Content and project ID are required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Import SpecificationArtifact model
        try:
            from ..models.specification_artifact import SpecificationArtifact, ArtifactType
        except ImportError:
            from models.specification_artifact import SpecificationArtifact, ArtifactType
        
        # Validate artifact type
        try:
            artifact_type_enum = ArtifactType(artifact_type)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid artifact type',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Get or create artifact
        artifact_id = f"{spec_id}_{artifact_type}"
        artifact = SpecificationArtifact.query.get(artifact_id)
        
        if artifact:
            # Update existing artifact
            artifact.update_content(content, 'user')  # TODO: get actual user
        else:
            # Create new artifact
            artifact = SpecificationArtifact.create_artifact(
                spec_id=spec_id,
                project_id=project_id,
                artifact_type=artifact_type_enum,
                content=content,
                created_by='user'  # TODO: get actual user
            )
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': artifact.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update specification artifact {spec_id}:{artifact_type}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to update specification artifact',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/specification/<spec_id>/artifact/<artifact_type>/review', methods=['POST'])
def mark_artifact_reviewed(spec_id, artifact_type):
    """Mark a specification artifact as human reviewed"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        project_id = data.get('projectId')
        review_notes = data.get('reviewNotes', '')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Import SpecificationArtifact model
        try:
            from ..models.specification_artifact import SpecificationArtifact
        except ImportError:
            from models.specification_artifact import SpecificationArtifact
        
        # Get artifact
        artifact_id = f"{spec_id}_{artifact_type}"
        artifact = SpecificationArtifact.query.get(artifact_id)
        
        if not artifact:
            return jsonify({
                'success': False,
                'error': 'Specification artifact not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Mark as reviewed
        artifact.mark_human_reviewed('user', review_notes)  # TODO: get actual user
        
        return jsonify({
            'success': True,
            'data': artifact.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to mark artifact as reviewed {spec_id}:{artifact_type}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark artifact as reviewed',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/idea/<item_id>/create-spec', methods=['POST'])
def create_specification(item_id):
    """Create specification from an idea by triggering DefineAgent processing"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        project_id = data.get('projectId')
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Check if feed item exists
        feed_item = FeedItem.query.get(item_id)
        if not feed_item:
            return jsonify({
                'success': False,
                'error': 'Feed item not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Import DefineAgent and events
        try:
            from ..agents.define_agent import DefineAgent
            from ..events.domain_events import IdeaPromotedEvent
            from ..events.event_store import EventStore
            from ..events.event_router import EventBus
            from ..services.ai_broker import AIBroker
        except ImportError:
            from agents.define_agent import DefineAgent
            from events.domain_events import IdeaPromotedEvent
            from events.event_store import EventStore
            from events.event_router import EventBus
            from services.ai_broker import AIBroker
        
        # Create IdeaPromotedEvent
        idea_promoted_event = IdeaPromotedEvent(
            idea_id=item_id,
            project_id=project_id,
            promoted_by='user'  # TODO: get actual user
        )
        
        # Initialize DefineAgent with proper app context
        from flask import current_app
        event_bus = EventBus()
        ai_broker = AIBroker()
        
        # Ensure AI broker has app context for database operations
        with current_app.app_context():
            ai_broker.start()  # Start the AI broker worker threads
        
        define_agent = DefineAgent(event_bus, ai_broker)
        
        # Process the event directly (synchronous for immediate feedback)
        try:
            logger.info(f"Processing idea {item_id} with DefineAgent")
            result = define_agent.process_event(idea_promoted_event)
            
            if result.success:
                logger.info(f"DefineAgent successfully processed idea {item_id}")
                
                # Store the event for audit trail
                event_store = EventStore()
                event_store.append_event(idea_promoted_event)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'spec_id': f"spec_{item_id}",
                        'processing_time': result.processing_time_seconds,
                        'artifacts_created': result.result_data.get('artifacts_created', 0) if result.result_data else 0
                    },
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0',
                })
            else:
                logger.error(f"DefineAgent failed to process idea {item_id}: {result.error_message}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to create specification: {result.error_message}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0',
                }), 500
                
        except Exception as agent_error:
            logger.error(f"Error running DefineAgent for idea {item_id}: {agent_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Failed to process idea with DefineAgent',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 500
        
    except Exception as e:
        logger.error(f"Error creating specification for idea {item_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to create specification',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/idea/<item_id>/create-spec-model-garden', methods=['POST'])
def create_specification_with_model_garden(item_id):
    """Create specification from an idea using AI Model Garden"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        project_id = data.get('projectId')
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Check if feed item exists
        feed_item = FeedItem.query.get(item_id)
        if not feed_item:
            return jsonify({
                'success': False,
                'error': 'Feed item not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Import AI service for Model Garden integration
        try:
            from ..services.ai_service import get_ai_service
            from ..events.domain_events import IdeaPromotedEvent
            from ..events.event_store import EventStore
        except ImportError:
            from services.ai_service import get_ai_service
            from events.domain_events import IdeaPromotedEvent
            from events.event_store import EventStore
        
        # Get AI service (which includes Model Garden integration)
        ai_service = get_ai_service()
        
        # Create specification using AI Model Garden
        try:
            logger.info(f"Creating specification for idea {item_id} using AI Model Garden")
            
            # Prepare context for AI Model Garden
            context = {
                'idea_title': feed_item.title,
                'idea_summary': feed_item.summary,
                'idea_content': feed_item.summary or feed_item.title,
                'project_id': project_id,
                'provider': 'model_garden'
            }
            
            # Use AI Model Garden to generate specification
            result = ai_service.execute_model_garden_task(
                instruction=f"Generate a complete software specification for this idea: {feed_item.title}\n\nDescription: {feed_item.summary}\n\nCreate requirements.md, design.md, and tasks.md documents.",
                product_context=context,
                model='claude-opus-4',  # Use your preferred model
                role='po'  # Product Owner role for specification generation
            )
            
            if result.get('success'):
                logger.info(f"AI Model Garden successfully created specification for idea {item_id}")
                
                # Store the event for audit trail
                idea_promoted_event = IdeaPromotedEvent(
                    idea_id=item_id,
                    project_id=project_id,
                    promoted_by='user'  # TODO: get actual user
                )
                event_store = EventStore()
                event_store.append_event(idea_promoted_event)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'spec_id': f"spec_{item_id}",
                        'processing_time': result.get('processing_time', 0),
                        'artifacts_created': 3,  # requirements, design, tasks
                        'provider': 'model_garden'
                    },
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0',
                })
            else:
                logger.error(f"AI Model Garden failed to create specification for idea {item_id}: {result.get('error')}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to create specification with AI Model Garden: {result.get("error", "Unknown error")}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0',
                }), 500
                
        except Exception as ai_error:
            logger.error(f"Error using AI Model Garden for idea {item_id}: {ai_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Failed to process idea with AI Model Garden',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 500
        
    except Exception as e:
        logger.error(f"Error creating specification with AI Model Garden for idea {item_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to create specification with AI Model Garden',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/specification/<spec_id>/generate-design', methods=['POST'])
def generate_design_document(spec_id):
    """Generate design document based on approved requirements"""
    try:
        logger.info(f"🎨 DESIGN GENERATION REQUESTED")
        logger.info(f"   📋 Spec ID: {spec_id}")
        logger.info(f"   🔗 Endpoint: POST /api/specification/{spec_id}/generate-design")
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        project_id = data.get('projectId')
        provider = data.get('provider', 'claude')  # Default to claude for backward compatibility
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        logger.info(f"   🏗️  Project ID: {project_id}")
        logger.info(f"   🤖 AI Provider: {provider.upper()} (synchronous call)")
        
        # Import required modules
        try:
            from ..models.specification_artifact import SpecificationArtifact, ArtifactType
            from ..agents.define_agent import DefineAgent
            from ..services.ai_broker import AIBroker
            from ..events.event_router import EventBus
        except ImportError:
            from models.specification_artifact import SpecificationArtifact, ArtifactType
            from agents.define_agent import DefineAgent
            from services.ai_broker import AIBroker
            from events.event_router import EventBus
        
        # Get requirements artifact to use as context
        logger.info(f"🔍 Looking for requirements artifact...")
        requirements_artifact = SpecificationArtifact.query.filter_by(
            spec_id=spec_id,
            artifact_type=ArtifactType.REQUIREMENTS
        ).first()
        
        if not requirements_artifact:
            logger.error(f"❌ Requirements artifact not found for spec {spec_id}")
            return jsonify({
                'success': False,
                'error': 'Requirements document not found. Generate requirements first.',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        logger.info(f"✅ Requirements artifact found")
        logger.info(f"   📄 Content Length: {len(requirements_artifact.content)} characters")
        logger.info(f"   📅 Created: {requirements_artifact.created_at}")
        logger.info(f"   👤 Created By: {requirements_artifact.created_by}")
        
        # Initialize DefineAgent
        from flask import current_app
        event_bus = EventBus()
        ai_broker = AIBroker()
        
        with current_app.app_context():
            ai_broker.start()
        
        define_agent = DefineAgent(event_bus, ai_broker)
        
        # Generate design document
        try:
            design_content = _generate_design_document_core(spec_id, project_id, requirements_artifact, define_agent, provider)
            
            return jsonify({
                'success': True,
                'data': design_content.to_dict() if hasattr(design_content, 'to_dict') else design_content,
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            })
            
        except Exception as e:
            logger.error(f"Error generating design document for spec {spec_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to generate design document',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 500
        
    except Exception as e:
        logger.error(f"Error in generate_design_document for spec {spec_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate design document',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/specification/<spec_id>/generate-tasks', methods=['POST'])
def generate_tasks_document(spec_id):
    """Generate tasks document based on approved design.
    This version streams interim text chunks over WebSocket so the
    frontend can render the document in real-time.
    """
    try:
        logger.info(f"📋 TASKS GENERATION REQUESTED")
        logger.info(f"   📋 Spec ID: {spec_id}")
        logger.info(f"   🔗 Endpoint: POST /api/specification/{spec_id}/generate-tasks")
        logger.info(f"   🌊 Mode: Streaming via WebSocket")
        
        data = request.get_json() or {}
        project_id = data.get('projectId')
        provider = data.get('provider', 'claude')  # Default to claude for backward compatibility
        
        if not project_id:
            return jsonify({'success': False, 'error': 'Project ID is required'}), 400
        
        logger.info(f"   🏗️  Project ID: {project_id}")
        logger.info(f"   🤖 AI Provider: {provider.upper()} (streaming)")

        from flask import current_app as _cur_app
        app_obj = _cur_app._get_current_object()

        # Import heavy modules once
        try:
            from ..models.specification_artifact import SpecificationArtifact, ArtifactType
            from ..agents.define_agent import DefineAgent
            from ..services.ai_broker import AIBroker
            from ..events.event_router import EventBus
        except ImportError:
            from models.specification_artifact import SpecificationArtifact, ArtifactType
            from agents.define_agent import DefineAgent
            from services.ai_broker import AIBroker
            from events.event_router import EventBus

        # Grab SocketIO instance
        socketio = app_obj.extensions.get('socketio')
        if socketio is None:
            logger.error('SocketIO not initialised')
            return jsonify({'success': False, 'error': 'WebSocket unavailable'}), 500

        # Fetch artifacts (same logic as before)
        logger.info(f"🔍 Looking for requirements and design artifacts...")
        
        requirements_artifact = SpecificationArtifact.query.filter_by(
            spec_id=spec_id,
            artifact_type=ArtifactType.REQUIREMENTS
        ).first()

        design_artifact = SpecificationArtifact.query.filter_by(
            spec_id=spec_id,
            artifact_type=ArtifactType.DESIGN
        ).first()

        if not requirements_artifact or not design_artifact:
            logger.error(f"❌ Missing artifacts - Requirements: {bool(requirements_artifact)}, Design: {bool(design_artifact)}")
            return jsonify({'success': False, 'error': 'Requirements and design docs required'}), 400
        
        logger.info(f"✅ Both artifacts found")
        logger.info(f"   📄 Requirements Length: {len(requirements_artifact.content)} characters")
        logger.info(f"   📄 Design Length: {len(design_artifact.content)} characters")

        def _bg_generate():
            try:
                with app_obj.app_context():
                    event_bus = EventBus()
                    ai_broker = AIBroker()
                    ai_broker.start()
                    define_agent = DefineAgent(event_bus, ai_broker)

                    from claude_code_sdk import query, ClaudeCodeOptions, Message, TextBlock, AssistantMessage
                    import anyio, os

                    collected: list[str] = []

                    async def _run():
                        socketio.emit('spec.tasks_start', {'spec_id': spec_id})
                        
                        # CONSTRUCT THE FULL PROMPT HERE
                        prompt_context = define_agent._prepare_tasks_context(
                            requirements_artifact.content,
                            design_artifact.content,
                            define_agent.get_project_context(project_id)
                        )
                        full_prompt = f"""You are an expert technical project manager. Your task is to create a detailed implementation plan in a `tasks.md` file based on the provided requirements and design documents.

=== APPROVED REQUIREMENTS ===
{requirements_artifact.content}

=== APPROVED DESIGN ===
{design_artifact.content}

=== PROJECT CONTEXT ===
{prompt_context}

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
                        async for message in query(
                            prompt=full_prompt,
                            options=ClaudeCodeOptions(cwd=os.getcwd())
                        ):
                            if isinstance(message, AssistantMessage):
                                for block in message.content:
                                    if isinstance(block, TextBlock):
                                        text = block.text
                                        collected.append(text)
                                        socketio.emit('spec.tasks_progress', {'spec_id': spec_id, 'delta': text})

                    try:
                        anyio.run(_run)
                        tasks_content = ''.join(collected)
                    except Exception as stream_err:
                        # Emit error to UI and fall back to non-stream generation
                        logger.error(f"Streaming tasks generation failed: {stream_err}")
                        socketio.emit('spec.tasks_error', {'spec_id': spec_id, 'error': str(stream_err)})

                        tasks_content = define_agent.generate_tasks_document(
                            spec_id=spec_id,
                            project_id=project_id,
                            requirements_content=requirements_artifact.content,
                            design_content=design_artifact.content,
                            provider=provider
                        ) or ''

                    # Store result (streamed or fallback)
                    if tasks_content:
                        define_agent._store_specifications(spec_id, project_id, {'tasks': tasks_content})

                    socketio.emit('spec.tasks_done', {'spec_id': spec_id})
            except Exception as e:
                logger.error(f"Background tasks generation fatal error: {e}")
                socketio.emit('spec.tasks_error', {'spec_id': spec_id, 'error': str(e)})

        import threading, os
        threading.Thread(target=_bg_generate, daemon=True).start()

        # Immediately inform client that generation has begun
        return '', 202
        
    except Exception as e:
        logger.error(f"Error in generate_tasks_document for spec {spec_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate tasks document',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/specification/<spec_id>/freeze', methods=['POST'])
def freeze_specification(spec_id):
    """Freeze all artifacts in a specification and emit spec.frozen event"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        project_id = data.get('projectId')
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Optional flag to re-emit the event even if the spec is already frozen.
        force_refreeze = bool(data.get('force', False))

        # Import SpecificationArtifact model and events
        try:
            from ..models.specification_artifact import SpecificationArtifact
            from ..events.domain_events import SpecFrozenEvent
            from ..events.event_store import EventStore
        except ImportError:
            from models.specification_artifact import SpecificationArtifact
            from events.domain_events import SpecFrozenEvent
            from events.event_store import EventStore
        
        # Get all artifacts for this specification
        artifacts = SpecificationArtifact.get_spec_artifacts(spec_id)
        
        if not artifacts:
            return jsonify({
                'success': False,
                'error': 'No specification artifacts found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Check if all artifacts are human reviewed
        completion_status = SpecificationArtifact.get_spec_completion_status(spec_id)
        if not completion_status['ready_to_freeze'] and not force_refreeze:
            return jsonify({
                'success': False,
                'error': 'Specification is not ready to freeze. All artifacts must be human reviewed. (Pass force=true to re-emit event for an already frozen spec).',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Freeze all artifacts
        for artifact in artifacts:
            artifact.freeze_artifact('user')  # TODO: get actual user
        
        # Emit spec.frozen event
        try:
            logger.info(f"Creating SpecFrozenEvent for spec {spec_id}")
            event = SpecFrozenEvent(
                spec_id=spec_id,
                project_id=project_id,
                frozen_by='user'  # TODO: get actual user
            )
            logger.info(f"Created event: {event.get_event_type()} with ID {event.metadata.event_id}")
            
            # Store event in database and publish to Redis
            event_store = EventStore()
            event_store.append_event(event)
            logger.info(f"Event stored successfully")
            
            # Publish to Redis for real-time updates
            try:
                import redis
                import json
                redis_client = redis.from_url('redis://localhost:6379/0', decode_responses=True)
                
                # Create event envelope for WebSocket broadcasting
                event_envelope = {
                    'id': event.metadata.event_id,
                    'timestamp': event.metadata.timestamp.isoformat(),
                    'correlation_id': event.metadata.correlation_id,
                    'event_type': event.get_event_type(),
                    'payload': event.get_payload(),
                    'source_agent': 'stages_api',
                    'project_id': project_id
                }
                
                # Publish to Redis channel for WebSocket server
                result = redis_client.publish('mission_control:events', json.dumps(event_envelope))
                
                # ALSO publish to the main event bus channel so PlannerAgent can receive it
                result2 = redis_client.publish('software_factory:events', json.dumps({
                    'event_type': 'spec.frozen',
                    'event_id': event.metadata.event_id,
                    'timestamp': time.time(),
                    'source': 'stages_api',
                    'data': {
                        'spec_id': spec_id,
                        'project_id': project_id,
                        'frozen_by': 'user'
                    },
                    'project_id': project_id
                }))
                logger.info(f"Published spec.frozen event to Redis, subscribers: {result}")
                logger.info(f"Published spec.frozen event to event bus, subscribers: {result2}")
                
            except Exception as redis_error:
                logger.error(f"Failed to publish spec.frozen event to Redis: {redis_error}")
                # Don't fail the request if Redis publishing fails
                
        except Exception as e:
            logger.error(f"Failed to emit spec.frozen event: {e}")
            # Don't fail the request if event emission fails
        
        return jsonify({
            'success': True,
            'data': {
                'spec_id': spec_id,
                'frozen_artifacts': len(artifacts),
                'completion_status': SpecificationArtifact.get_spec_completion_status(spec_id)
            },
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to freeze specification {spec_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to freeze specification',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


def generate_product_brief_content(feed_item):
    """Generate starter content for a product brief based on feed item"""
    title = feed_item.title
    summary = feed_item.summary or feed_item.title
    
    # Generate starter content based on the idea
    brief_data = {
        'problemStatement': summary,
        'successMetrics': [
            'User engagement increases by 20%',
            'Feature adoption rate above 60%'
        ],
        'risks': [
            'Technical complexity may delay delivery',
            'User learning curve for new feature'
        ],
        'competitiveAnalysis': f'Research needed on how competitors handle similar features related to: {title}',
        'userStories': [
            {
                'id': 'story-1',
                'title': f'As a user, I want {title.lower()}',
                'description': f'User story derived from: {summary}',
                'acceptanceCriteria': [
                    'Feature is discoverable in the UI',
                    'Feature works on all supported devices',
                    'Feature has proper error handling'
                ],
                'priority': 'high',
                'status': 'draft'
            }
        ],
        'progress': 0.3  # 30% complete with this starter content
    }
    
    return brief_data


def _get_prd_recommendations(prd_info):
    """Generate recommendations based on PRD status and type"""
    recommendations = []
    
    if prd_info['prd_status'] == 'missing':
        if prd_info['prd_type'] == 'missing':
            recommendations.append({
                'type': 'create_idea_prd',
                'priority': 'high',
                'message': 'Create an idea-specific PRD for precise business context',
                'action': 'Upload documents and attach to this specific idea'
            })
        else:
            recommendations.append({
                'type': 'create_prd',
                'priority': 'medium',
                'message': 'Create a PRD to provide business context',
                'action': 'Upload business documents or create PRD from scratch'
            })
    elif prd_info['prd_status'] == 'draft':
        recommendations.append({
            'type': 'freeze_prd',
            'priority': 'medium',
            'message': 'Review and freeze the draft PRD to enable spec generation',
            'action': 'Open PRD editor and click "Freeze PRD" when ready'
        })
    
    # Suggest idea-specific PRD if using session-based fallback
    if prd_info['prd_type'] == 'session' and prd_info['prd_status'] == 'frozen':
        recommendations.append({
            'type': 'upgrade_to_idea_prd',
            'priority': 'low',
            'message': 'Consider creating an idea-specific PRD for better context precision',
            'action': 'Create new PRD specifically for this idea'
        })
    
    if prd_info['total_prds'] > 1:
        recommendations.append({
            'type': 'consolidate_prds',
            'priority': 'low',
            'message': f'Multiple PRDs found ({prd_info["total_prds"]}). Consider consolidating for clarity',
            'action': 'Review PRDs and merge related content'
        })
    
    return recommendations


@stages_bp.route('/api/project/<project_id>/prd-status', methods=['GET'])
def get_project_prd_status(project_id):
    """Get PRD status for a project to support Define stage validation"""
    try:
        # Check if project exists
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Get PRD validation info
        prd_info = _validate_prd_requirement(project_id, None)  # item_id not needed for status check
        
        return jsonify({
            'success': True,
            'data': {
                'project_id': project_id,
                'has_frozen_prd': prd_info['has_prd'],
                'prd_status': prd_info['prd_status'],
                'prd_type': prd_info['prd_type'],
                'latest_prd': prd_info['latest_prd'],
                'upload_sessions': prd_info['upload_sessions'],
                'context_level': prd_info['context_level'],
                'total_prds': prd_info['total_prds'],
                'frozen_prds': prd_info['frozen_prds'],
                'can_move_to_define': prd_info['has_prd'],
                'recommendations': _get_prd_recommendations(prd_info)
            },
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Failed to get PRD status for project {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve PRD status',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/idea/<item_id>/create-prd', methods=['POST'])
def create_idea_specific_prd(item_id):
    """Create a PRD specifically for an idea/FeedItem"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        project_id = data.get('projectId')
        upload_session_id = data.get('uploadSessionId')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Check if feed item exists
        feed_item = FeedItem.query.get(item_id)
        if not feed_item:
            return jsonify({
                'success': False,
                'error': 'Feed item not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Import PRD model
        try:
            from ..models.prd import PRD
            from ..models.upload_session import UploadSession
        except ImportError:
            from models.prd import PRD
            from models.upload_session import UploadSession
        
        # Create or get upload session for this PRD
        if upload_session_id:
            session = UploadSession.query.get(upload_session_id)
            if not session:
                return jsonify({
                    'success': False,
                    'error': 'Upload session not found',
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0',
                }), 404
        else:
            # Create new upload session for this idea
            session = UploadSession.create(
                project_id=project_id,
                description=f"PRD for: {feed_item.title}"
            )
            db.session.commit()
        
        # Create idea-specific PRD
        prd = PRD.create_draft(
            project_id=project_id,
            draft_id=str(session.id),
            feed_item_id=item_id,
            md_content=f"# PRD for {feed_item.title}\n\n{feed_item.summary or 'No description provided'}",
            json_summary={
                'problem': {'text': feed_item.summary or 'Problem statement needed', 'sources': []},
                'audience': {'text': 'Target audience to be defined', 'sources': []},
                'goals': {'items': ['Define success metrics'], 'sources': []},
                'risks': {'items': ['Identify potential risks'], 'sources': []},
                'competitive_scan': {'items': ['Research competitors'], 'sources': []},
                'open_questions': {'items': ['List open questions'], 'sources': []}
            },
            created_by='mission-control-user'  # TODO: get actual user
        )
        
        logger.info(f"Created idea-specific PRD {prd.id} for FeedItem {item_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'prd': prd.to_dict(),
                'upload_session_id': str(session.id),
                'message': f'Created PRD for "{feed_item.title}"'
            },
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating idea-specific PRD for {item_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create idea-specific PRD',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


# Error handlers for this blueprint
@stages_bp.errorhandler(404)
def stage_not_found(error):
    return jsonify({
        'success': False,
        'error': 'Resource not found',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    }), 404


@stages_bp.errorhandler(400)
def stage_bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    }), 400


@stages_bp.errorhandler(SQLAlchemyError)
def stage_database_error(error):
    db.session.rollback()
    logger.error(f"Database error in stages API: {error}")
    return jsonify({
        'success': False,
        'error': 'Database operation failed',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
    }), 500


@stages_bp.route('/api/idea/<item_id>/create-spec-async', methods=['POST'])
def create_specification_async(item_id):
    """Create specification from an idea using asynchronous background job"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        project_id = data.get('projectId')
        provider = data.get('provider', 'claude')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Check if feed item exists
        feed_item = FeedItem.query.get(item_id)
        if not feed_item:
            return jsonify({
                'success': False,
                'error': 'Feed item not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        # Import spec generation service
        try:
            from ..services.spec_generation_service import get_spec_generation_service
        except ImportError:
            from services.spec_generation_service import get_spec_generation_service
        
        # Start async spec generation
        spec_service = get_spec_generation_service()
        result = spec_service.start_spec_generation(
            item_id=item_id,
            project_id=project_id,
            provider=provider
        )
        
        logger.info(f"Started async spec generation for idea {item_id}: job {result['job_id']}")
        
        return jsonify({
            'success': True,
            'data': result,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Error starting async spec generation for idea {item_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to start spec generation',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/jobs/<int:job_id>/status', methods=['GET'])
def get_job_status(job_id):
    """Get status of a background job"""
    try:
        # Import spec generation service
        try:
            from ..services.spec_generation_service import get_spec_generation_service
        except ImportError:
            from services.spec_generation_service import get_spec_generation_service
        
        spec_service = get_spec_generation_service()
        status = spec_service.get_generation_status(job_id)
        
        if status is None:
            return jsonify({
                'success': False,
                'error': 'Job not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get job status',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a background job"""
    try:
        # Import spec generation service
        try:
            from ..services.spec_generation_service import get_spec_generation_service
        except ImportError:
            from services.spec_generation_service import get_spec_generation_service
        
        spec_service = get_spec_generation_service()
        success = spec_service.cancel_generation(job_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to cancel job or job not found',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'status': 'cancelled',
                'cancelled_at': datetime.utcnow().isoformat()
            },
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to cancel job',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/async-spec-status', methods=['GET'])
def async_spec_status():
    """Debug endpoint to check async spec generation system status"""
    try:
        # Import spec generation service
        try:
            from ..services.spec_generation_service import get_spec_generation_service
            from ..services.background import get_job_manager
        except ImportError:
            from services.spec_generation_service import get_spec_generation_service
            from services.background import get_job_manager
        
        # Check if services are available
        try:
            spec_service = get_spec_generation_service()
            job_manager = get_job_manager()
            
            # Get system stats
            stats = job_manager.get_system_stats()
            
            return jsonify({
                'success': True,
                'data': {
                    'spec_service_available': True,
                    'job_manager_available': True,
                    'system_stats': stats,
                    'socketio_available': 'socketio' in current_app.extensions,
                    'timestamp': datetime.utcnow().isoformat()
                },
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            })
            
        except Exception as service_error:
            return jsonify({
                'success': False,
                'error': f'Service initialization error: {str(service_error)}',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 500
        
    except Exception as e:
        logger.error(f"Error checking async spec status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to check system status',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/jobs/active', methods=['GET'])
def get_active_jobs():
    """Get all active background jobs"""
    try:
        # Import required modules
        try:
            from ..models.background_job import BackgroundJob
        except ImportError:
            from models.background_job import BackgroundJob
        
        # Get all running jobs
        active_jobs = BackgroundJob.query.filter_by(status=BackgroundJob.STATUS_RUNNING).all()
        
        jobs_data = []
        for job in active_jobs:
            jobs_data.append({
                'id': job.id,
                'job_type': job.job_type,
                'status': job.status,
                'progress': job.progress or 0,
                'job_metadata': job.job_metadata or {},
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None
            })
        
        return jsonify({
            'success': True,
            'data': jobs_data,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Error getting active jobs: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get active jobs',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/specification/<spec_id>/generate-design-async', methods=['POST'])
def generate_design_document_async(spec_id):
    """Generate design document asynchronously using background job"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        project_id = data.get('projectId')
        provider = data.get('provider', 'claude')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Import spec generation service
        try:
            from ..services.spec_generation_service import get_spec_generation_service
        except ImportError:
            from services.spec_generation_service import get_spec_generation_service
        
        # Start async design generation
        spec_service = get_spec_generation_service()
        result = spec_service.start_design_generation(
            spec_id=spec_id,
            project_id=project_id,
            provider=provider
        )
        
        logger.info(f"Started async design generation for spec {spec_id}: job {result['job_id']}")
        
        return jsonify({
            'success': True,
            'data': result,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Error starting async design generation for spec {spec_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to start design generation',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500


@stages_bp.route('/api/specification/<spec_id>/generate-tasks-async', methods=['POST'])
def generate_tasks_document_async(spec_id):
    """Generate tasks document asynchronously using background job"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        project_id = data.get('projectId')
        provider = data.get('provider', 'claude')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Import spec generation service
        try:
            from ..services.spec_generation_service import get_spec_generation_service
        except ImportError:
            from services.spec_generation_service import get_spec_generation_service
        
        # Start async tasks generation
        spec_service = get_spec_generation_service()
        result = spec_service.start_tasks_generation(
            spec_id=spec_id,
            project_id=project_id,
            provider=provider
        )
        
        logger.info(f"Started async tasks generation for spec {spec_id}: job {result['job_id']}")
        
        return jsonify({
            'success': True,
            'data': result,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        })
        
    except Exception as e:
        logger.error(f"Error starting async tasks generation for spec {spec_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to start tasks generation',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
        }), 500