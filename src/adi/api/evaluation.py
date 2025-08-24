"""
Evaluation API

Endpoints for managing evaluation sets and results.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from adi.models.evaluation import EvalSet, EvalResult
from adi.services.evaluation_service import EvaluationService, EvalBlueprint, SelectCriteria, VerifyCriteria
from adi.services.eval_runner import EvalRunner
from adi.services.evaluation_analytics import EvaluationAnalytics
from src.models.base import db

logger = logging.getLogger(__name__)
evaluation_service = EvaluationService()
eval_runner = EvalRunner()
evaluation_analytics = EvaluationAnalytics()

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
        
        eval_sets = evaluation_service.get_eval_sets_by_project(project_id)
        
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
    Create a new evaluation set with intelligent case selection.
    
    Expected payload:
    {
        "project_id": "string",
        "name": "string",
        "blueprint": {
            "id": "string",
            "tag": "string",
            "select": {
                "failure_mode_tags": ["string"],
                "time_window_days": int,
                "min_cases": int,
                "max_cases": int,
                "event_types": ["string"],
                "severity_levels": ["string"],
                "status_filters": ["string"]
            },
            "verify": {
                "check_types": ["string"],
                "custom_validators": ["string"],
                "expected_outcomes": {}
            },
            "min_pass_rate": float,
            "description": "string"
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
        
        # Parse blueprint
        blueprint_data = data['blueprint']
        
        # Create selection criteria
        select_data = blueprint_data.get('select', {})
        select_criteria = SelectCriteria(
            failure_mode_tags=select_data.get('failure_mode_tags'),
            time_window_days=select_data.get('time_window_days'),
            min_cases=select_data.get('min_cases', 10),
            max_cases=select_data.get('max_cases', 100),
            event_types=select_data.get('event_types'),
            severity_levels=select_data.get('severity_levels'),
            status_filters=select_data.get('status_filters')
        )
        
        # Create verification criteria
        verify_data = blueprint_data.get('verify', {})
        verify_criteria = VerifyCriteria(
            check_types=verify_data.get('check_types', []),
            custom_validators=verify_data.get('custom_validators'),
            expected_outcomes=verify_data.get('expected_outcomes')
        )
        
        # Create blueprint
        blueprint = EvalBlueprint(
            id=blueprint_data.get('id', f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
            tag=blueprint_data.get('tag', ''),
            select=select_criteria,
            verify=verify_criteria,
            min_pass_rate=blueprint_data.get('min_pass_rate', 0.8),
            description=blueprint_data.get('description')
        )
        
        # Create eval set using service
        eval_set = evaluation_service.create_eval_set(
            project_id=data['project_id'],
            name=data['name'],
            blueprint=blueprint
        )
        
        return jsonify(eval_set.to_dict()), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
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


@evaluation_bp.route('/sets/<eval_set_id>', methods=['PUT'])
def update_eval_set(eval_set_id):
    """
    Update an evaluation set with versioning.
    
    Expected payload:
    {
        "name": "string",
        "blueprint": {
            "select": {...},
            "verify": {...},
            "min_pass_rate": float,
            "description": "string"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        eval_set = evaluation_service.update_eval_set(eval_set_id, data)
        
        return jsonify(eval_set.to_dict())
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error updating eval set {eval_set_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/sets/<eval_set_id>', methods=['DELETE'])
def delete_eval_set(eval_set_id):
    """Delete an evaluation set and all its results."""
    try:
        success = evaluation_service.delete_eval_set(eval_set_id)
        
        if not success:
            return jsonify({'error': 'Evaluation set not found'}), 404
        
        return jsonify({'message': 'Evaluation set deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting eval set {eval_set_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/sets/<eval_set_id>/history', methods=['GET'])
def get_eval_set_history(eval_set_id):
    """Get version history for an evaluation set."""
    try:
        history = evaluation_service.get_eval_set_history(eval_set_id)
        
        return jsonify({
            'eval_set_id': eval_set_id,
            'history': history,
            'count': len(history)
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting eval set history {eval_set_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/sets/<eval_set_id>/rollback', methods=['POST'])
def rollback_eval_set(eval_set_id):
    """
    Rollback an evaluation set to a previous version.
    
    Expected payload:
    {
        "version_timestamp": "string"
    }
    """
    try:
        data = request.get_json()
        if not data or 'version_timestamp' not in data:
            return jsonify({'error': 'version_timestamp is required'}), 400
        
        eval_set = evaluation_service.rollback_eval_set(eval_set_id, data['version_timestamp'])
        
        return jsonify(eval_set.to_dict())
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error rolling back eval set {eval_set_id}: {str(e)}")
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


@evaluation_bp.route('/sets/<eval_set_id>/execute', methods=['POST'])
def execute_eval_set(eval_set_id):
    """
    Execute an evaluation set.
    
    Optional payload:
    {
        "async": boolean  # Whether to run asynchronously (default: false)
    }
    """
    try:
        data = request.get_json() or {}
        run_async = data.get('async', False)
        
        if run_async:
            # TODO: Implement async execution with background jobs
            # For now, we'll run synchronously and return immediately
            logger.info(f"Async execution requested for eval set {eval_set_id}")
            
            # In a real implementation, this would submit to a job queue
            run_id = f"async_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            return jsonify({
                'message': 'Evaluation submitted for async execution',
                'run_id': run_id,
                'status': 'submitted'
            }), 202
        else:
            # Synchronous execution
            result = eval_runner.run_eval_set(eval_set_id)
            
            return jsonify({
                'run_id': result.run_id,
                'pass_rate': result.pass_rate,
                'total_cases': result.total_cases,
                'passed_cases': result.passed_cases,
                'failed_cases': result.failed_cases,
                'execution_time_ms': result.execution_time_ms,
                'pack_version': result.pack_version,
                'errors': result.errors,
                'case_results': [
                    {
                        'case_id': case.case_id,
                        'passed': case.passed,
                        'checks': case.checks,
                        'errors': case.errors,
                        'execution_time_ms': case.execution_time_ms
                    }
                    for case in result.case_results
                ]
            })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error executing eval set {eval_set_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/sets/<eval_set_id>/schedule', methods=['POST'])
def schedule_eval_set(eval_set_id):
    """
    Schedule an evaluation set for future execution.
    
    Expected payload:
    {
        "schedule_time": "2024-01-01T12:00:00Z"
    }
    """
    try:
        data = request.get_json()
        if not data or 'schedule_time' not in data:
            return jsonify({'error': 'schedule_time is required'}), 400
        
        # Parse schedule time
        try:
            schedule_time = datetime.fromisoformat(data['schedule_time'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid schedule_time format. Use ISO 8601 format.'}), 400
        
        # Check if schedule time is in the future
        if schedule_time <= datetime.utcnow():
            return jsonify({'error': 'schedule_time must be in the future'}), 400
        
        # Schedule the evaluation
        run_id = eval_runner.schedule_eval_run(eval_set_id, schedule_time)
        
        return jsonify({
            'message': 'Evaluation scheduled successfully',
            'run_id': run_id,
            'schedule_time': schedule_time.isoformat(),
            'status': 'scheduled'
        })
        
    except Exception as e:
        logger.error(f"Error scheduling eval set {eval_set_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/runs/<run_id>', methods=['GET'])
def get_eval_run_status(run_id):
    """Get the status and results of a specific evaluation run."""
    try:
        # Look up the run in the database
        eval_result = EvalResult.query.filter(EvalResult.run_id == run_id).first()
        
        if not eval_result:
            return jsonify({'error': 'Evaluation run not found'}), 404
        
        return jsonify({
            'run_id': run_id,
            'eval_set_id': str(eval_result.eval_set_id),
            'status': 'completed',
            'pass_rate': float(eval_result.pass_rate),
            'total_cases': eval_result.total_cases,
            'passed_cases': eval_result.passed_cases,
            'failed_cases': eval_result.failed_cases,
            'pack_version': eval_result.pack_version,
            'run_timestamp': eval_result.run_timestamp.isoformat() if eval_result.run_timestamp else None
        })
        
    except Exception as e:
        logger.error(f"Error getting eval run status {run_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/analytics/dashboard', methods=['GET'])
def get_evaluation_dashboard():
    """
    Get comprehensive evaluation dashboard for a project.
    
    Query parameters:
    - project_id: Project identifier (required)
    - days: Number of days to analyze (default: 30)
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        days = int(request.args.get('days', 30))
        
        dashboard = evaluation_analytics.get_evaluation_dashboard(project_id, days)
        
        return jsonify({
            'project_id': dashboard.project_id,
            'eval_sets': dashboard.eval_sets,
            'recent_results': dashboard.recent_results,
            'trend_analysis': [
                {
                    'timestamp': point.timestamp.isoformat(),
                    'pass_rate': point.pass_rate,
                    'total_cases': point.total_cases,
                    'pack_version': point.pack_version,
                    'run_id': point.run_id
                }
                for point in dashboard.trend_analysis
            ],
            'failing_cases': [
                {
                    'case_id': case.case_id,
                    'failure_count': case.failure_count,
                    'last_failure': case.last_failure.isoformat(),
                    'failure_types': case.failure_types,
                    'pack_versions': case.pack_versions,
                    'details': case.details
                }
                for case in dashboard.failing_cases
            ],
            'deployment_confidence': {
                'confidence_score': dashboard.deployment_confidence.confidence_score,
                'pass_rate_trend': dashboard.deployment_confidence.pass_rate_trend,
                'recent_pass_rate': dashboard.deployment_confidence.recent_pass_rate,
                'baseline_pass_rate': dashboard.deployment_confidence.baseline_pass_rate,
                'recommendation': dashboard.deployment_confidence.recommendation,
                'factors': dashboard.deployment_confidence.factors
            },
            'summary_stats': dashboard.summary_stats
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting evaluation dashboard: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/analytics/trends', methods=['GET'])
def get_trend_analysis():
    """
    Get trend analysis for evaluation results.
    
    Query parameters:
    - project_id: Project identifier (required)
    - eval_set_id: Optional specific eval set ID
    - days: Number of days to analyze (default: 30)
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        eval_set_id = request.args.get('eval_set_id')
        days = int(request.args.get('days', 30))
        
        trend_points = evaluation_analytics.get_trend_analysis(project_id, eval_set_id, days)
        
        return jsonify({
            'project_id': project_id,
            'eval_set_id': eval_set_id,
            'days': days,
            'trend_points': [
                {
                    'timestamp': point.timestamp.isoformat(),
                    'pass_rate': point.pass_rate,
                    'total_cases': point.total_cases,
                    'pack_version': point.pack_version,
                    'run_id': point.run_id
                }
                for point in trend_points
            ],
            'count': len(trend_points)
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting trend analysis: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/analytics/failing-cases', methods=['GET'])
def get_failing_cases_analysis():
    """
    Get analysis of failing cases.
    
    Query parameters:
    - project_id: Project identifier (required)
    - days: Number of days to analyze (default: 30)
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        days = int(request.args.get('days', 30))
        
        failing_cases = evaluation_analytics.get_failing_cases_analysis(project_id, days)
        
        return jsonify({
            'project_id': project_id,
            'days': days,
            'failing_cases': [
                {
                    'case_id': case.case_id,
                    'failure_count': case.failure_count,
                    'last_failure': case.last_failure.isoformat(),
                    'failure_types': case.failure_types,
                    'pack_versions': case.pack_versions,
                    'details': case.details
                }
                for case in failing_cases
            ],
            'count': len(failing_cases)
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting failing cases analysis: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/analytics/deployment-confidence', methods=['GET'])
def get_deployment_confidence():
    """
    Get deployment confidence metrics.
    
    Query parameters:
    - project_id: Project identifier (required)
    - pack_version: Optional specific pack version
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        pack_version = request.args.get('pack_version')
        
        confidence = evaluation_analytics.calculate_deployment_confidence(project_id, pack_version)
        
        return jsonify({
            'project_id': project_id,
            'pack_version': pack_version,
            'confidence_score': confidence.confidence_score,
            'pass_rate_trend': confidence.pass_rate_trend,
            'recent_pass_rate': confidence.recent_pass_rate,
            'baseline_pass_rate': confidence.baseline_pass_rate,
            'recommendation': confidence.recommendation,
            'factors': confidence.factors
        })
        
    except Exception as e:
        logger.error(f"Error calculating deployment confidence: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@evaluation_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the evaluation service."""
    return jsonify({
        'status': 'healthy',
        'service': 'adi_evaluation',
        'timestamp': datetime.utcnow().isoformat()
    })