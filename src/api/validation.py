"""
API endpoints for validation run management
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

try:
    from ..models.validation_run import ValidationRun, ValidationStatus
    from ..models.base import db
except ImportError:
    from models.validation_run import ValidationRun, ValidationStatus
    from models.base import db

logger = logging.getLogger(__name__)

validation_bp = Blueprint('validation', __name__, url_prefix='/api/validation')


@validation_bp.route('/runs/<project_id>', methods=['GET'])
def get_validation_runs(project_id: str):
    """Get validation runs for a project"""
    try:
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status')
        
        query = ValidationRun.query.filter_by(project_id=project_id)
        
        if status:
            try:
                status_enum = ValidationStatus(status)
                query = query.filter_by(status=status_enum)
            except ValueError:
                return jsonify({'error': f'Invalid status: {status}'}), 400
        
        validation_runs = query.order_by(ValidationRun.started_at.desc()).limit(limit).all()
        
        return jsonify({
            'validation_runs': [run.to_dict() for run in validation_runs],
            'total': len(validation_runs)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching validation runs for project {project_id}: {e}")
        return jsonify({'error': 'Failed to fetch validation runs'}), 500


@validation_bp.route('/runs/<validation_run_id>', methods=['GET'])
def get_validation_run(validation_run_id: str):
    """Get a specific validation run"""
    try:
        validation_run = ValidationRun.query.get(validation_run_id)
        
        if not validation_run:
            return jsonify({'error': 'Validation run not found'}), 404
        
        return jsonify(validation_run.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error fetching validation run {validation_run_id}: {e}")
        return jsonify({'error': 'Failed to fetch validation run'}), 500


@validation_bp.route('/runs/<validation_run_id>/status', methods=['PUT'])
def update_validation_run_status(validation_run_id: str):
    """Update validation run status"""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        try:
            new_status = ValidationStatus(data['status'])
        except ValueError:
            return jsonify({'error': f'Invalid status: {data["status"]}'}), 400
        
        validation_run = ValidationRun.query.get(validation_run_id)
        if not validation_run:
            return jsonify({'error': 'Validation run not found'}), 404
        
        validation_run.update_status(new_status)
        
        return jsonify({
            'message': 'Status updated successfully',
            'validation_run': validation_run.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating validation run status {validation_run_id}: {e}")
        return jsonify({'error': 'Failed to update validation run status'}), 500


@validation_bp.route('/runs/<validation_run_id>/workflows', methods=['POST'])
def add_workflow_run(validation_run_id: str):
    """Add a workflow run to a validation run"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Workflow run data is required'}), 400
        
        validation_run = ValidationRun.query.get(validation_run_id)
        if not validation_run:
            return jsonify({'error': 'Validation run not found'}), 404
        
        validation_run.add_workflow_run(data)
        
        return jsonify({
            'message': 'Workflow run added successfully',
            'validation_run': validation_run.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error adding workflow run to validation run {validation_run_id}: {e}")
        return jsonify({'error': 'Failed to add workflow run'}), 500


@validation_bp.route('/projects/<project_id>/active', methods=['GET'])
def get_active_validation_runs(project_id: str):
    """Get currently active validation runs for a project"""
    try:
        active_runs = ValidationRun.get_active_validation_runs(project_id)
        
        return jsonify({
            'active_validation_runs': [run.to_dict() for run in active_runs],
            'count': len(active_runs)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching active validation runs for project {project_id}: {e}")
        return jsonify({'error': 'Failed to fetch active validation runs'}), 500


@validation_bp.route('/projects/<project_id>/latest', methods=['GET'])
def get_latest_validation_run(project_id: str):
    """Get the latest validation run for a project"""
    try:
        latest_run = ValidationRun.query.filter_by(project_id=project_id)\
                                       .order_by(ValidationRun.started_at.desc())\
                                       .first()
        
        if not latest_run:
            return jsonify({'error': 'No validation runs found for project'}), 404
        
        return jsonify(latest_run.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error fetching latest validation run for project {project_id}: {e}")
        return jsonify({'error': 'Failed to fetch latest validation run'}), 500


@validation_bp.route('/health', methods=['GET'])
def validation_health():
    """Health check endpoint for validation service"""
    try:
        # Simple health check - try to query the database
        ValidationRun.query.limit(1).all()
        
        return jsonify({
            'status': 'healthy',
            'service': 'validation',
            'timestamp': ValidationRun.query.first().created_at.isoformat() if ValidationRun.query.first() else None
        }), 200
        
    except Exception as e:
        logger.error(f"Validation service health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'validation',
            'error': str(e)
        }), 500