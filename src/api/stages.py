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
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import (
        Stage, StageTransition, ProductBrief, FeedItem, 
        MissionControlProject, db
    )
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
        
        # Remove from current stage
        if from_stage:
            from_stage_obj = Stage.get_or_create_for_project(project_id, from_stage)
            from_stage_obj.remove_item(item_id)
        
        # Add to new stage
        to_stage_obj = Stage.get_or_create_for_project(project_id, target_stage)
        to_stage_obj.add_item(item_id)
        
        # Record transition
        transition = StageTransition.create(
            item_id=item_id,
            project_id=project_id,
            from_stage=from_stage,
            to_stage=target_stage,
            actor='system'  # TODO: get actual user
        )
        
        # If moving to Define stage, create a product brief
        brief = None
        if target_stage == 'define':
            brief_data = generate_product_brief_content(feed_item)
            brief = ProductBrief.create_for_item(item_id, project_id, brief_data)
            
            # Update feed item metadata
            if not feed_item.meta_data:
                feed_item.meta_data = {}
            feed_item.meta_data['stage'] = 'define'
            feed_item.updated_at = datetime.utcnow()
        
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