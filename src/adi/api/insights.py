"""
Insights API

Endpoints for managing and retrieving insights.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging

try:
    from ..models.insight import Insight
    from ...models.base import db
except ImportError:
    try:
        from src.adi.models.insight import Insight
        from src.models.base import db
    except ImportError:
        from adi.models.insight import Insight
        from models.base import db

logger = logging.getLogger(__name__)

insights_bp = Blueprint('adi_insights', __name__, url_prefix='/api/adi/insights')


@insights_bp.route('/', methods=['GET'])
def get_insights():
    """
    Get insights for a project.
    
    Query parameters:
    - project_id: Filter by project ID (required)
    - status: Filter by status (open, converted, dismissed, resolved)
    - severity: Filter by severity (low, med, high)
    - kind: Filter by insight kind
    - limit: Maximum number of results (default: 50)
    - offset: Pagination offset (default: 0)
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        status = request.args.get('status')
        severity = request.args.get('severity')
        kind = request.args.get('kind')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Insight.query.filter(Insight.project_id == project_id)
        
        if status:
            query = query.filter(Insight.status == status)
        if severity:
            query = query.filter(Insight.severity == severity)
        if kind:
            query = query.filter(Insight.kind == kind)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        insights = query.order_by(Insight.created_at.desc()).offset(offset).limit(limit).all()
        
        return jsonify({
            'insights': [insight.to_dict() for insight in insights],
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error retrieving insights: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@insights_bp.route('/<insight_id>', methods=['GET'])
def get_insight(insight_id):
    """Get a specific insight by ID."""
    try:
        insight = Insight.query.get(insight_id)
        if not insight:
            return jsonify({'error': 'Insight not found'}), 404
        
        return jsonify(insight.to_dict())
        
    except Exception as e:
        logger.error(f"Error retrieving insight {insight_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@insights_bp.route('/<insight_id>', methods=['PATCH'])
def update_insight(insight_id):
    """
    Update an insight.
    
    Allowed updates:
    - status: Change insight status
    - tags: Add/remove tags
    """
    try:
        insight = Insight.query.get(insight_id)
        if not insight:
            return jsonify({'error': 'Insight not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Update allowed fields
        if 'status' in data:
            if data['status'] not in ['open', 'converted', 'dismissed', 'resolved']:
                return jsonify({'error': 'Invalid status'}), 400
            insight.status = data['status']
        
        if 'tags' in data:
            if not isinstance(data['tags'], list):
                return jsonify({'error': 'Tags must be a list'}), 400
            insight.tags = data['tags']
        
        insight.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Insight updated: {insight_id}")
        
        return jsonify(insight.to_dict())
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating insight {insight_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@insights_bp.route('/summary', methods=['GET'])
def get_insights_summary():
    """
    Get insights summary for a project.
    
    Query parameters:
    - project_id: Filter by project ID (required)
    - window_hours: Time window for analysis (default: 24)
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        window_hours = int(request.args.get('window_hours', 24))
        window_start = datetime.utcnow() - timedelta(hours=window_hours)
        
        # Get insights within time window
        insights = Insight.query.filter(
            Insight.project_id == project_id,
            Insight.created_at >= window_start
        ).all()
        
        # Calculate summary statistics
        total_insights = len(insights)
        by_status = {}
        by_severity = {}
        by_kind = {}
        
        for insight in insights:
            # Count by status
            by_status[insight.status] = by_status.get(insight.status, 0) + 1
            
            # Count by severity
            by_severity[insight.severity] = by_severity.get(insight.severity, 0) + 1
            
            # Count by kind
            by_kind[insight.kind] = by_kind.get(insight.kind, 0) + 1
        
        return jsonify({
            'project_id': project_id,
            'window_hours': window_hours,
            'total_insights': total_insights,
            'by_status': by_status,
            'by_severity': by_severity,
            'by_kind': by_kind,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error generating insights summary: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@insights_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the insights service."""
    return jsonify({
        'status': 'healthy',
        'service': 'adi_insights',
        'timestamp': datetime.utcnow().isoformat()
    })