"""
Evaluation API

Endpoints for managing evaluation sets and results.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

try:
    from ..models.evaluation import EvalSet, EvalResult
    from ...models.base import db
except ImportError:
    try:
        from src.adi.models.evaluation import EvalSet, EvalResult
        from src.models.base import db
    except ImportError:
        from adi.models.evaluation import EvalSet, EvalResult
        from models.base import db

logger = logging.getLogger(__name__)

evaluation_bp = Blueprint('adi_evaluation', __name__, url_prefix='/api/adi/evaluation')


@evaluation_bp.route('/sets', methods=['GET'])
def get_eval_sets():
    """
    Get evaluation sets for a project.
    
    Query parameters:
    - project_id: Filter by project ID (required)
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        eval_sets = EvalSet.query.filter(EvalSet.project_id == project_id).order_by(EvalSet.created_at.desc()).all()
        
        return jsonify({
            'eval_sets': [eval_set.to_dict() for eval_set in eval_sets],
            'count': len(eval_sets)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving eval sets: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/sets', methods=['POST'])
def create_eval_set():
    """
    Create a new evaluation set.
    
    Expected payload:
    {
        "project_id": "string",
        "name": "string",
        "blueprint": {
            "id": "string",
            "tag": "string",
            "select": {},
            "verify": {},
            "min_pass_rate": float
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['project_id', 'name', 'blueprint']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate blueprint structure
        blueprint = data['blueprint']
        blueprint_required = ['id', 'tag', 'select', 'verify', 'min_pass_rate']
        for field in blueprint_required:
            if field not in blueprint:
                return jsonify({'error': f'Missing required blueprint field: {field}'}), 400
        
        # Create eval set
        eval_set = EvalSet(
            project_id=data['project_id'],
            name=data['name'],
            blueprint=blueprint
        )
        
        db.session.add(eval_set)
        db.session.commit()
        
        logger.info(f"Eval set created: {data['name']} for project {data['project_id']}")
        
        return jsonify(eval_set.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating eval set: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/sets/<eval_set_id>', methods=['GET'])
def get_eval_set(eval_set_id):
    """Get a specific evaluation set by ID."""
    try:
        eval_set = EvalSet.query.get(eval_set_id)
        if not eval_set:
            return jsonify({'error': 'Evaluation set not found'}), 404
        
        return jsonify(eval_set.to_dict())
        
    except Exception as e:
        logger.error(f"Error retrieving eval set {eval_set_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/sets/<eval_set_id>/results', methods=['GET'])
def get_eval_results(eval_set_id):
    """
    Get evaluation results for a specific eval set.
    
    Query parameters:
    - limit: Maximum number of results (default: 20)
    """
    try:
        eval_set = EvalSet.query.get(eval_set_id)
        if not eval_set:
            return jsonify({'error': 'Evaluation set not found'}), 404
        
        limit = int(request.args.get('limit', 20))
        
        results = EvalResult.query.filter(
            EvalResult.eval_set_id == eval_set_id
        ).order_by(EvalResult.run_timestamp.desc()).limit(limit).all()
        
        return jsonify({
            'eval_set_id': eval_set_id,
            'results': [result.to_dict() for result in results],
            'count': len(results)
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error retrieving eval results for {eval_set_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/results', methods=['POST'])
def create_eval_result():
    """
    Create a new evaluation result.
    
    Expected payload:
    {
        "eval_set_id": "string",
        "run_id": "string",
        "pass_rate": float,
        "total_cases": int,
        "passed_cases": int,
        "failed_cases": ["case_id1", "case_id2"],
        "pack_version": "string"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['eval_set_id', 'run_id', 'pass_rate', 'total_cases', 'passed_cases', 'failed_cases', 'pack_version']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate eval set exists
        eval_set = EvalSet.query.get(data['eval_set_id'])
        if not eval_set:
            return jsonify({'error': 'Evaluation set not found'}), 404
        
        # Create eval result
        eval_result = EvalResult(
            eval_set_id=data['eval_set_id'],
            run_id=data['run_id'],
            pass_rate=data['pass_rate'],
            total_cases=data['total_cases'],
            passed_cases=data['passed_cases'],
            failed_cases=data['failed_cases'],
            pack_version=data['pack_version']
        )
        
        db.session.add(eval_result)
        db.session.commit()
        
        logger.info(f"Eval result created: {data['run_id']} for eval set {data['eval_set_id']}")
        
        return jsonify(eval_result.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating eval result: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/results/<result_id>', methods=['GET'])
def get_eval_result(result_id):
    """Get a specific evaluation result by ID."""
    try:
        result = EvalResult.query.get(result_id)
        if not result:
            return jsonify({'error': 'Evaluation result not found'}), 404
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Error retrieving eval result {result_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the evaluation service."""
    return jsonify({
        'status': 'healthy',
        'service': 'adi_evaluation',
        'timestamp': datetime.utcnow().isoformat()
    })