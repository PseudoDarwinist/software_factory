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

logger = logging.getLogger(__name__)

# Create blueprint
stages_bp = Blueprint('stages', __name__)


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
                'idea_content': feed_item.content,
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
        requirements_artifact = SpecificationArtifact.query.filter_by(
            spec_id=spec_id,
            artifact_type=ArtifactType.REQUIREMENTS
        ).first()
        
        if not requirements_artifact:
            return jsonify({
                'success': False,
                'error': 'Requirements document not found. Generate requirements first.',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Initialize DefineAgent
        from flask import current_app
        event_bus = EventBus()
        ai_broker = AIBroker()
        
        with current_app.app_context():
            ai_broker.start()
        
        define_agent = DefineAgent(event_bus, ai_broker)
        
        # Generate design document
        try:
            logger.info(f"Generating design document for spec {spec_id}")
            design_content = define_agent.generate_design_document(
                spec_id=spec_id,
                project_id=project_id,
                requirements_content=requirements_artifact.content
            )
            
            if not design_content:
                return jsonify({
                    'success': False,
                    'error': 'Failed to generate design document',
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0',
                }), 500
            
            # Create or update design artifact
            design_artifact_id = f"{spec_id}_design"
            design_artifact = SpecificationArtifact.query.get(design_artifact_id)
            
            if design_artifact:
                design_artifact.update_content(design_content, 'define_agent')
            else:
                design_artifact = SpecificationArtifact.create_artifact(
                    spec_id=spec_id,
                    project_id=project_id,
                    artifact_type=ArtifactType.DESIGN,
                    content=design_content,
                    created_by='define_agent'
                )
                db.session.commit()
            
            logger.info(f"Design document generated successfully for spec {spec_id}")
            
            return jsonify({
                'success': True,
                'data': design_artifact.to_dict(),
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            })
            
        except Exception as agent_error:
            logger.error(f"Error generating design document for spec {spec_id}: {agent_error}")
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
    """Generate tasks document based on approved design"""
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
        
        # Get requirements and design artifacts to use as context
        requirements_artifact = SpecificationArtifact.query.filter_by(
            spec_id=spec_id,
            artifact_type=ArtifactType.REQUIREMENTS
        ).first()
        
        design_artifact = SpecificationArtifact.query.filter_by(
            spec_id=spec_id,
            artifact_type=ArtifactType.DESIGN
        ).first()
        
        if not requirements_artifact or not design_artifact:
            return jsonify({
                'success': False,
                'error': 'Requirements and design documents must exist before generating tasks',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 400
        
        # Initialize DefineAgent
        from flask import current_app
        event_bus = EventBus()
        ai_broker = AIBroker()
        
        with current_app.app_context():
            ai_broker.start()
        
        define_agent = DefineAgent(event_bus, ai_broker)
        
        # Generate tasks document
        try:
            logger.info(f"Generating tasks document for spec {spec_id}")
            tasks_content = define_agent.generate_tasks_document(
                spec_id=spec_id,
                project_id=project_id,
                requirements_content=requirements_artifact.content,
                design_content=design_artifact.content
            )
            
            # If AI generation fails, create a basic template
            if not tasks_content:
                logger.warning(f"AI generation failed for tasks document, creating template")
                tasks_content = f"""# Implementation Plan

## Overview
This implementation plan breaks down the approved requirements and design into actionable coding tasks.

## Development Tasks

- [ ] 1. Set up project structure and core interfaces
  - Create directory structure following existing patterns
  - Define interfaces and types
  - Set up configuration files
  - _Requirements: Core system setup_

- [ ] 2. Implement data models and validation
- [ ] 2.1 Create core data model classes
  - Write data model classes following existing patterns
  - Implement validation functions
  - Create unit tests for models
  - _Requirements: Data layer implementation_

- [ ] 2.2 Create database migrations
  - Write migration scripts following existing patterns
  - Update database schemas
  - Test migration rollback procedures
  - _Requirements: Database schema updates_

- [ ] 3. Implement business logic layer
- [ ] 3.1 Create service classes
  - Implement core business logic
  - Add error handling and logging
  - Write unit tests for services
  - _Requirements: Business logic implementation_

- [ ] 3.2 Add integration with existing services
  - Connect to existing APIs and services
  - Implement data transformation logic
  - Add integration tests
  - _Requirements: System integration_

- [ ] 4. Create API endpoints
- [ ] 4.1 Implement REST API controllers
  - Create API endpoint handlers
  - Add request/response validation
  - Implement authentication/authorization
  - _Requirements: API layer implementation_

- [ ] 4.2 Add API documentation
  - Document API endpoints
  - Create API usage examples
  - Update API documentation
  - _Requirements: Documentation_

- [ ] 5. Implement user interface components
- [ ] 5.1 Create UI components
  - Build user interface components
  - Implement user interactions
  - Add client-side validation
  - _Requirements: User interface_

- [ ] 5.2 Add responsive design
  - Ensure mobile compatibility
  - Test across different browsers
  - Optimize for accessibility
  - _Requirements: User experience_

- [ ] 6. Testing and quality assurance
- [ ] 6.1 Write comprehensive tests
  - Complete unit test coverage
  - Add integration tests
  - Implement end-to-end tests
  - _Requirements: Quality assurance_

- [ ] 6.2 Performance optimization
  - Profile application performance
  - Optimize database queries
  - Implement caching strategies
  - _Requirements: Performance requirements_

- [ ] 7. Documentation and deployment
- [ ] 7.1 Complete documentation
  - Update user documentation
  - Create deployment guides
  - Document configuration options
  - _Requirements: Documentation_

- [ ] 7.2 Prepare for deployment
  - Set up deployment pipeline
  - Configure monitoring and logging
  - Perform security review
  - _Requirements: Deployment readiness_

---
*This implementation plan was generated based on the approved requirements and design. Please review and modify tasks as needed before starting development.*
"""
            
            # Create or update tasks artifact
            tasks_artifact_id = f"{spec_id}_tasks"
            tasks_artifact = SpecificationArtifact.query.get(tasks_artifact_id)
            
            if tasks_artifact:
                tasks_artifact.update_content(tasks_content, 'define_agent')
            else:
                tasks_artifact = SpecificationArtifact.create_artifact(
                    spec_id=spec_id,
                    project_id=project_id,
                    artifact_type=ArtifactType.TASKS,
                    content=tasks_content,
                    created_by='define_agent'
                )
                db.session.commit()
            
            logger.info(f"Tasks document generated successfully for spec {spec_id}")
            
            return jsonify({
                'success': True,
                'data': tasks_artifact.to_dict(),
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            })
            
        except Exception as agent_error:
            logger.error(f"Error generating tasks document for spec {spec_id}: {agent_error}")
            return jsonify({
                'success': False,
                'error': 'Failed to generate tasks document',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 500
        
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
        if not completion_status['ready_to_freeze']:
            return jsonify({
                'success': False,
                'error': 'Specification is not ready to freeze. All artifacts must be human reviewed.',
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
                logger.info(f"Published spec.frozen event to Redis, subscribers: {result}")
                
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