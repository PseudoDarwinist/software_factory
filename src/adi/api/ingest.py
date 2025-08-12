"""
Decision Log Ingest API

Endpoints for ingesting decision logs from production applications.
Includes rate limiting, authentication, and comprehensive validation.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
import logging
import time
import hashlib
from functools import wraps
from collections import defaultdict, deque

try:
    from ..models.decision_log import DecisionLog
    from ..schemas.decision_log import validate_decision_log, sanitize_for_logging
    from ...models.base import db
except ImportError:
    try:
        from src.adi.models.decision_log import DecisionLog
        from src.adi.schemas.decision_log import validate_decision_log, sanitize_for_logging
        from src.models.base import db
    except ImportError:
        from adi.models.decision_log import DecisionLog
        from adi.schemas.decision_log import validate_decision_log, sanitize_for_logging
        from models.base import db

logger = logging.getLogger(__name__)

ingest_bp = Blueprint('adi_ingest', __name__, url_prefix='/api/adi/ingest')

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # 1 minute window
RATE_LIMIT_MAX_REQUESTS = 100  # Max requests per window per project
RATE_LIMIT_BURST_MAX = 20  # Max burst requests

# In-memory rate limiting store (in production, use Redis)
rate_limit_store = defaultdict(lambda: deque())

# Valid project tokens (in production, store in database/config)
VALID_PROJECT_TOKENS = {
    'irops-prod': 'token-irops-prod-12345',
    'customer-service': 'token-cs-67890',
    'test-project': 'token-test-abcdef'
}


def authenticate_project_token():
    """Authenticate project token from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None, 'Missing Authorization header'
    
    if not auth_header.startswith('Bearer '):
        return None, 'Invalid Authorization header format. Use: Bearer <token>'
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Find project for this token
    for project_id, valid_token in VALID_PROJECT_TOKENS.items():
        if token == valid_token:
            return project_id, None
    
    return None, 'Invalid project token'


def check_rate_limit(project_id: str) -> tuple[bool, dict]:
    """
    Check if request is within rate limits for the project.
    Returns (allowed, rate_limit_info)
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    # Get request timestamps for this project
    project_requests = rate_limit_store[project_id]
    
    # Remove old requests outside the window
    while project_requests and project_requests[0] < window_start:
        project_requests.popleft()
    
    # Check current request count
    current_count = len(project_requests)
    
    # Check burst limit (last 10 seconds)
    burst_window_start = now - 10
    burst_count = sum(1 for ts in project_requests if ts >= burst_window_start)
    
    rate_limit_info = {
        'window_requests': current_count,
        'window_limit': RATE_LIMIT_MAX_REQUESTS,
        'burst_requests': burst_count,
        'burst_limit': RATE_LIMIT_BURST_MAX,
        'window_reset_in': int(RATE_LIMIT_WINDOW - (now - (project_requests[0] if project_requests else now))),
        'retry_after': None
    }
    
    # Check burst limit first
    if burst_count >= RATE_LIMIT_BURST_MAX:
        rate_limit_info['retry_after'] = 10
        return False, rate_limit_info
    
    # Check window limit
    if current_count >= RATE_LIMIT_MAX_REQUESTS:
        rate_limit_info['retry_after'] = rate_limit_info['window_reset_in']
        return False, rate_limit_info
    
    # Add current request timestamp
    project_requests.append(now)
    
    return True, rate_limit_info


def require_auth_and_rate_limit(f):
    """Decorator to require authentication and enforce rate limiting."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Authenticate
        project_id, auth_error = authenticate_project_token()
        if auth_error:
            logger.warning(f"Authentication failed: {auth_error}")
            return jsonify({'error': auth_error}), 401
        
        # Check rate limit
        allowed, rate_info = check_rate_limit(project_id)
        if not allowed:
            logger.warning(f"Rate limit exceeded for project {project_id}: {rate_info}")
            response = jsonify({
                'error': 'Rate limit exceeded',
                'rate_limit': rate_info
            })
            if rate_info['retry_after']:
                response.headers['Retry-After'] = str(rate_info['retry_after'])
            return response, 429
        
        # Store project_id and rate_info in request context
        g.project_id = project_id
        g.rate_limit_info = rate_info
        
        return f(*args, **kwargs)
    
    return decorated_function


def log_ingestion_metrics(project_id: str, status: str, error_type: str = None, latency_ms: int = None):
    """Log ingestion metrics for monitoring."""
    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'project_id': project_id,
        'status': status,  # success, validation_error, server_error
        'error_type': error_type,
        'latency_ms': latency_ms
    }
    
    # In production, send to metrics system (Prometheus, DataDog, etc.)
    logger.info(f"Ingestion metrics: {metrics}")
    
    return metrics


@ingest_bp.route('/decision', methods=['POST'])
@require_auth_and_rate_limit
def ingest_decision_log():
    """
    Ingest a decision log from a production application.
    
    Requires:
    - Authorization: Bearer <project_token>
    - Content-Type: application/json
    
    Expected payload (validated with Pydantic):
    {
        "project_id": "string",
        "case_id": "string (must be hashed)", 
        "event": {
            "type": "string",
            "ts": "ISO datetime",
            "scope": "string",
            "attrs": {} (no PII allowed)
        },
        "decision": {
            "action": "string",
            "channel": "string", 
            "template_id": "string",
            "status": "OK|FAILED|SKIPPED",
            "latency_ms": int,
            "counts": {} (optional)
        },
        "version": {
            "app": "string",
            "policy": "string",
            "factory_pr": "string"
        },
        "links": {} (optional),
        "hashes": {} (optional),
        "schema_version": "1.0.0" (optional, defaults to current)
    }
    """
    start_time = time.time()
    project_id = g.project_id
    
    try:
        # Get and validate JSON data
        if not request.is_json:
            log_ingestion_metrics(project_id, 'validation_error', 'invalid_content_type')
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        if not data:
            log_ingestion_metrics(project_id, 'validation_error', 'no_json_data')
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate project_id matches authenticated project
        if data.get('project_id') != project_id:
            log_ingestion_metrics(project_id, 'validation_error', 'project_id_mismatch')
            return jsonify({
                'error': f'project_id in payload must match authenticated project: {project_id}'
            }), 400
        
        # Comprehensive validation using Pydantic schema
        try:
            validated_log = validate_decision_log(data)
        except ValueError as e:
            log_ingestion_metrics(project_id, 'validation_error', 'schema_validation')
            logger.warning(f"Schema validation failed for project {project_id}: {str(e)}")
            return jsonify({
                'error': 'Validation failed',
                'details': str(e)
            }), 400
        
        # Create decision log entry using validated data
        decision_log = DecisionLog(
            project_id=validated_log.project_id,
            case_id=validated_log.case_id,
            event_data=validated_log.event.model_dump(),
            decision_data=validated_log.decision.model_dump(),
            version_data=validated_log.version.model_dump(),
            links=validated_log.links,
            hashes=validated_log.hashes
        )
        
        db.session.add(decision_log)
        db.session.commit()
        
        # Calculate processing latency
        processing_latency = int((time.time() - start_time) * 1000)
        
        # Log successful ingestion
        log_ingestion_metrics(project_id, 'success', latency_ms=processing_latency)
        logger.info(f"Decision log ingested successfully: {validated_log.case_id} for project {project_id}")
        
        # Return success response with rate limit info
        response_data = {
            'status': 'success',
            'id': str(decision_log.id),
            'message': 'Decision log ingested successfully',
            'processing_latency_ms': processing_latency,
            'rate_limit': g.rate_limit_info
        }
        
        return jsonify(response_data), 201
        
    except Exception as e:
        db.session.rollback()
        processing_latency = int((time.time() - start_time) * 1000)
        log_ingestion_metrics(project_id, 'server_error', 'internal_error', processing_latency)
        
        # Log error with sanitized data for security
        sanitized_data = sanitize_for_logging(data if 'data' in locals() else {})
        logger.error(f"Error ingesting decision log for project {project_id}: {str(e)}", extra={
            'project_id': project_id,
            'sanitized_payload': sanitized_data,
            'processing_latency_ms': processing_latency
        })
        
        return jsonify({
            'error': 'Internal server error',
            'processing_latency_ms': processing_latency
        }), 500


def require_admin_auth(f):
    """Decorator to require admin authentication for log queries."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for admin token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Admin authentication required'}), 401
        
        admin_token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # In production, validate admin token against secure store
        if admin_token != 'admin-token-12345':  # Placeholder - use secure token in production
            return jsonify({'error': 'Invalid admin token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


@ingest_bp.route('/logs', methods=['GET'])
@require_admin_auth
def query_decision_logs():
    """
    Query decision logs (admin only).
    
    Requires:
    - Authorization: Bearer <admin_token>
    
    Query parameters:
    - project_id: Filter by project ID (required)
    - window: Time window in hours (default: 24, max: 168)
    - limit: Maximum number of results (default: 100, max: 1000)
    - case_id: Filter by specific case ID (optional)
    """
    try:
        project_id = request.args.get('project_id')
        window_hours = int(request.args.get('window', 24))
        limit = int(request.args.get('limit', 100))
        case_id = request.args.get('case_id')
        
        # Validation
        if not project_id:
            return jsonify({'error': 'project_id parameter is required'}), 400
        
        if window_hours > 168:  # Max 1 week
            return jsonify({'error': 'window cannot exceed 168 hours (1 week)'}), 400
        
        if limit > 1000:  # Max 1000 results
            return jsonify({'error': 'limit cannot exceed 1000'}), 400
        
        # Calculate time window
        window_start = datetime.utcnow() - timedelta(hours=window_hours)
        
        # Build query
        query = DecisionLog.query.filter(
            DecisionLog.project_id == project_id,
            DecisionLog.created_at >= window_start
        )
        
        # Add case_id filter if provided
        if case_id:
            query = query.filter(DecisionLog.case_id == case_id)
        
        # Execute query
        logs = query.order_by(DecisionLog.created_at.desc()).limit(limit).all()
        
        # Sanitize logs for admin viewing (remove potential PII)
        sanitized_logs = []
        for log in logs:
            log_dict = log.to_dict()
            log_dict['event_data'] = sanitize_for_logging(log_dict['event_data'])
            sanitized_logs.append(log_dict)
        
        logger.info(f"Admin queried {len(logs)} decision logs for project {project_id}")
        
        return jsonify({
            'logs': sanitized_logs,
            'count': len(logs),
            'window_hours': window_hours,
            'project_id': project_id,
            'query_timestamp': datetime.utcnow().isoformat()
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error querying decision logs: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@ingest_bp.route('/rate-limit', methods=['GET'])
@require_auth_and_rate_limit
def get_rate_limit_status():
    """Get current rate limit status for the authenticated project."""
    return jsonify({
        'project_id': g.project_id,
        'rate_limit': g.rate_limit_info,
        'timestamp': datetime.utcnow().isoformat()
    })


@ingest_bp.route('/cleanup/stats', methods=['GET'])
@require_admin_auth
def get_cleanup_stats():
    """Get statistics about logs that would be cleaned up."""
    try:
        from ..services.cleanup_service import get_cleanup_service
        
        max_age_days = int(request.args.get('max_age_days', 60))
        
        if max_age_days < 1 or max_age_days > 365:
            return jsonify({'error': 'max_age_days must be between 1 and 365'}), 400
        
        service = get_cleanup_service()
        stats = service.get_cleanup_stats(max_age_days)
        
        return jsonify(stats)
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error getting cleanup stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@ingest_bp.route('/cleanup/schedule', methods=['POST'])
@require_admin_auth
def schedule_cleanup():
    """Schedule a cleanup job for expired logs."""
    try:
        from ..services.cleanup_service import get_cleanup_service
        
        data = request.get_json() or {}
        max_age_days = data.get('max_age_days', 60)
        batch_size = data.get('batch_size', 1000)
        
        # Validation
        if not isinstance(max_age_days, int) or max_age_days < 1 or max_age_days > 365:
            return jsonify({'error': 'max_age_days must be an integer between 1 and 365'}), 400
        
        if not isinstance(batch_size, int) or batch_size < 100 or batch_size > 10000:
            return jsonify({'error': 'batch_size must be an integer between 100 and 10000'}), 400
        
        service = get_cleanup_service()
        job_id = service.schedule_cleanup_job(max_age_days, batch_size)
        
        logger.info(f"Admin scheduled cleanup job {job_id} (max_age_days={max_age_days})")
        
        return jsonify({
            'job_id': job_id,
            'message': 'Cleanup job scheduled successfully',
            'max_age_days': max_age_days,
            'batch_size': batch_size
        }), 201
        
    except Exception as e:
        logger.error(f"Error scheduling cleanup job: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@ingest_bp.route('/cleanup/run', methods=['POST'])
@require_admin_auth
def run_cleanup_now():
    """Run cleanup immediately (synchronous)."""
    try:
        from ..services.cleanup_service import get_cleanup_service
        
        data = request.get_json() or {}
        max_age_days = data.get('max_age_days', 60)
        dry_run = data.get('dry_run', False)
        
        # Validation
        if not isinstance(max_age_days, int) or max_age_days < 1 or max_age_days > 365:
            return jsonify({'error': 'max_age_days must be an integer between 1 and 365'}), 400
        
        service = get_cleanup_service()
        result = service.cleanup_expired_logs(max_age_days=max_age_days, dry_run=dry_run)
        
        logger.info(f"Admin ran {'dry-run ' if dry_run else ''}cleanup: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error running cleanup: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@ingest_bp.route('/cleanup/jobs', methods=['GET'])
@require_admin_auth
def get_cleanup_jobs():
    """Get recent cleanup job results."""
    try:
        from ..services.cleanup_service import get_cleanup_service
        
        limit = int(request.args.get('limit', 10))
        if limit > 100:
            limit = 100
        
        service = get_cleanup_service()
        jobs = service.get_recent_cleanup_jobs(limit)
        
        return jsonify({
            'jobs': jobs,
            'count': len(jobs)
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error getting cleanup jobs: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@ingest_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the ingest service."""
    try:
        # Test database connectivity
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = 'unhealthy'
    
    # Check rate limiting store
    rate_limit_projects = len(rate_limit_store)
    
    # Check cleanup service
    try:
        from ..services.cleanup_service import get_cleanup_service
        service = get_cleanup_service()
        cleanup_status = 'healthy'
    except Exception as e:
        logger.error(f"Cleanup service check failed: {str(e)}")
        cleanup_status = 'unhealthy'
    
    health_status = 'healthy' if all([
        db_status == 'healthy',
        cleanup_status == 'healthy'
    ]) else 'degraded'
    
    return jsonify({
        'status': health_status,
        'service': 'adi_ingest',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'database': db_status,
            'rate_limiting': 'healthy',
            'cleanup_service': cleanup_status,
            'active_projects': rate_limit_projects
        },
        'version': '1.0.0'
    }), 200 if health_status == 'healthy' else 503