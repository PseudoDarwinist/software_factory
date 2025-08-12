"""
System API Blueprint
REST endpoints for system status, health checks, and monitoring
"""

from flask import Blueprint, jsonify, current_app, request
from sqlalchemy import text
try:
    from ..models import BackgroundJob, SystemMap, Conversation, db
    from ..models.mission_control_project import MissionControlProject
    from ..core.database import check_database_health, get_database_statistics
    from ..core.events import create_event, EventType
    from ..services.event_bus import publish_event
except ImportError:
    from models import BackgroundJob, SystemMap, Conversation, db
    from models.mission_control_project import MissionControlProject
    from core.database import check_database_health, get_database_statistics
    from core.events import create_event, EventType
    from services.event_bus import publish_event
from datetime import datetime, timedelta
import logging
import os
import sys

# Optional psutil import for system metrics
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Redis-based event queue for phase transitions
PENDING_EVENTS_KEY = 'phase_transition_events'

def add_pending_event(event_data):
    """Add an event to the pending events queue using Redis"""
    try:
        import redis
        import json
        
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Add timestamp
        event_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Add event to Redis list
        r.lpush(PENDING_EVENTS_KEY, json.dumps(event_data))
        
        # Keep only last 10 events to prevent memory issues
        r.ltrim(PENDING_EVENTS_KEY, 0, 9)
        
        # Log what we queued for traceability
        try:
            evt_type = event_data.get('type')
            evt_project = (event_data.get('payload') or {}).get('project_id')
            logger.info(f"[PhaseQueue] Queued event type={evt_type} project_id={evt_project}")
        except Exception:
            pass
        
    except Exception as e:
        # Fallback to logging if Redis fails
        logger.warning(f"Failed to add event to Redis queue: {e}")

def get_and_clear_pending_events():
    """Get all pending events and clear the queue using Redis"""
    try:
        import redis
        import json
        
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Get all events and clear the list atomically
        pipe = r.pipeline()
        pipe.lrange(PENDING_EVENTS_KEY, 0, -1)
        pipe.delete(PENDING_EVENTS_KEY)
        results = pipe.execute()
        
        # Parse JSON events
        events = []
        for event_json in results[0]:
            try:
                events.append(json.loads(event_json))
            except json.JSONDecodeError:
                continue
        
        # Return events in chronological order (reverse since we used lpush)
        ordered = list(reversed(events))
        try:
            logger.info(f"[PhaseQueue] Drained {len(ordered)} pending events: {[e.get('type') for e in ordered]}")
        except Exception:
            pass
        return ordered
        
    except Exception as e:
        # Fallback to empty list if Redis fails
        logger.warning(f"Failed to get events from Redis queue: {e}")
        return []
import traceback

logger = logging.getLogger(__name__)

# Create blueprint
system_bp = Blueprint('system', __name__)


@system_bp.route('/api/status', methods=['GET'])
def system_status():
    """Get comprehensive system status including jobs, health, and metrics with caching"""
    try:
        from ..services.cache import get_status_cache
    except ImportError:
        from services.cache import get_status_cache
    
    try:
        cache = get_status_cache()
        
        # Check for cached status (short TTL for real-time updates)
        cached_status = cache.get('system_status')
        if cached_status:
            # Update timestamp for cached response
            cached_status['timestamp'] = datetime.utcnow().isoformat()
            cached_status['cached'] = True
            return jsonify(cached_status)
        
        # Generate fresh status data
        status_data = _generate_comprehensive_status()
        
        # Publish system status event for real-time updates
        try:
            event = create_event(
                EventType.SYSTEM_HEALTH_CHECK,
                status=status_data['status'],
                active_jobs=len(status_data['jobs']['active']),
                project_count=status_data['projects']['total_count'],
                database_status=status_data['database_health']['status'],
                uptime_seconds=status_data.get('uptime_seconds', 0),
                source="system_api"
            )
            publish_event(event)
            logger.debug(f"Published SYSTEM_HEALTH_CHECK event with status: {status_data['status']}")
        except Exception as e:
            logger.error(f"Failed to publish SYSTEM_HEALTH_CHECK event: {e}")
        
        # Cache the status data (excluding timestamp)
        cache_data = status_data.copy()
        cache_data.pop('timestamp', None)
        cache.set('system_status', cache_data, ttl=15)  # 15 second cache
        
        return jsonify(status_data)
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'error',
            'error': 'Failed to retrieve system status'
        }), 500


def _generate_comprehensive_status():
    """Generate comprehensive system status data"""
    # Get active background jobs with efficient query
    active_jobs = BackgroundJob.query.filter(
        BackgroundJob.status.in_([BackgroundJob.STATUS_PENDING, BackgroundJob.STATUS_RUNNING])
    ).order_by(BackgroundJob.created_at.desc()).all()
    
    # Get recent completed jobs (last 24 hours)
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_jobs = BackgroundJob.query.filter(
        BackgroundJob.completed_at >= recent_cutoff,
        BackgroundJob.status.in_([BackgroundJob.STATUS_COMPLETED, BackgroundJob.STATUS_FAILED])
    ).order_by(BackgroundJob.completed_at.desc()).limit(10).all()
    
    # Get project status summary
    project_status = _get_project_status_summary()
    
    # Get system health
    db_health = check_database_health()
    
    # Get system metrics
    system_metrics = get_system_metrics()
    
    # Get job manager statistics
    job_manager_stats = _get_job_manager_stats()
    
    # Determine overall system status
    overall_status = _determine_overall_status(db_health, active_jobs, system_metrics)
    
    # Get update counters for polling system
    try:
        from ..models import FeedItem, MissionControlProject
    except ImportError:
        from models import FeedItem, MissionControlProject
    
    # Count recent updates (last 5 minutes) for polling detection
    recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
    
    projects_updated = MissionControlProject.query.filter(
        MissionControlProject.updated_at >= recent_cutoff
    ).count()
    
    feed_updated = FeedItem.query.filter(
        FeedItem.created_at >= recent_cutoff
    ).count()
    
    # Get pending events for polling system
    pending_events = get_and_clear_pending_events()
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'status': overall_status,
        'cached': False,
        # Fields expected by Mission Control polling system
        'projects_updated': projects_updated,
        'feed_updated': feed_updated,
        'active_jobs': len(active_jobs),
        'system_health': overall_status,
        'events': pending_events,  # Add pending events
        # Detailed status data
        'jobs': {
            'active': [job.to_dict() for job in active_jobs],
            'recent': [job.to_dict() for job in recent_jobs],
            'summary': {
                'active_count': len(active_jobs),
                'pending_count': sum(1 for job in active_jobs if job.status == BackgroundJob.STATUS_PENDING),
                'running_count': sum(1 for job in active_jobs if job.status == BackgroundJob.STATUS_RUNNING),
                'completed_24h': len([job for job in recent_jobs if job.status == BackgroundJob.STATUS_COMPLETED]),
                'failed_24h': len([job for job in recent_jobs if job.status == BackgroundJob.STATUS_FAILED])
            }
        },
        'projects': project_status,
        'database_health': db_health,
        'system_metrics': system_metrics,
        'job_manager': job_manager_stats,
        'uptime_seconds': get_uptime_seconds()
    }


def _get_project_status_summary():
    """Get comprehensive project status summary with caching"""
    try:
        from ..services.cache import get_status_cache
    except ImportError:
        from services.cache import get_status_cache
    
    cache = get_status_cache()
    cached_projects = cache.get('project_status_summary')
    if cached_projects:
        return cached_projects
    
    # Generate fresh project status data using Mission Control Projects
    projects = MissionControlProject.query.all()
    
    status_counts = {}
    recent_projects = []
    active_projects = []
    
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    
    for project in projects:
        # Count by system map status
        status = getattr(project, 'system_map_status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Recent projects
        if project.created_at >= recent_cutoff:
            recent_projects.append({
                'id': project.id,
                'name': project.name,
                'status': status,
                'created_at': project.created_at.isoformat() if project.created_at else None
            })
        
        # Active projects (with recent activity)
        if project.updated_at >= recent_cutoff or status in ['in_progress', 'processing']:
            active_projects.append({
                'id': project.id,
                'name': project.name,
                'status': status,
                'updated_at': project.updated_at.isoformat() if project.updated_at else None,
                'active_jobs': _get_project_active_jobs(project.id)
            })
    
    project_summary = {
        'total_count': len(projects),
        'status_counts': status_counts,
        'recent_projects': recent_projects[:5],  # Last 5 recent projects
        'active_projects': active_projects[:10],  # Top 10 active projects
        'last_updated': datetime.utcnow().isoformat()
    }
    
    # Cache for 60 seconds
    cache.set('project_status_summary', project_summary, ttl=60)
    
    return project_summary


def _get_project_active_jobs(project_id: int):
    """Get active jobs for a specific project"""
    active_jobs = BackgroundJob.query.filter(
        BackgroundJob.project_id == project_id,
        BackgroundJob.status.in_([BackgroundJob.STATUS_PENDING, BackgroundJob.STATUS_RUNNING])
    ).all()
    
    return [
        {
            'id': job.id,
            'job_type': job.job_type,
            'status': job.status,
            'progress': job.progress
        }
        for job in active_jobs
    ]


def _get_job_manager_stats():
    """Get job manager statistics with error handling"""
    try:
        try:
            from ..services.background import get_job_manager
        except ImportError:
            from services.background import get_job_manager
        job_manager = get_job_manager()
        return job_manager.get_system_stats()
    except Exception as e:
        logger.warning(f"Could not get job manager stats: {e}")
        return {
            'error': 'Job manager not available',
            'message': str(e)
        }


def _determine_overall_status(db_health, active_jobs, system_metrics):
    """Determine overall system status based on various health indicators"""
    if db_health['status'] != 'healthy':
        return 'unhealthy'
    
    # Check for too many failed jobs
    failed_jobs = sum(1 for job in active_jobs if job.status == BackgroundJob.STATUS_FAILED)
    if failed_jobs > 5:
        return 'degraded'
    
    # Check system metrics if available
    if system_metrics.get('available') and system_metrics.get('memory', {}).get('percent', 0) > 90:
        return 'degraded'
    
    if system_metrics.get('available') and system_metrics.get('cpu', {}).get('percent', 0) > 95:
        return 'degraded'
    
    return 'healthy'


@system_bp.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint for load balancers and monitoring"""
    try:
        # Quick database connectivity test
        db_health = check_database_health()
        
        if db_health['status'] == 'healthy':
            return jsonify({
                'success': True,
                'data': {
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                },
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            })
        else:
            return jsonify({
                'success': False,
                'error': db_health['message'],
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
            }), 503
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': 'Health check failed'
        }), 503


@system_bp.route('/api/metrics', methods=['GET'])
def system_metrics():
    """Get detailed system metrics and statistics"""
    try:
        # Database statistics
        db_stats = get_database_statistics()
        
        # System resource usage
        system_metrics = get_system_metrics()
        
        # Application metrics
        app_metrics = get_application_metrics()
        
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'database': db_stats,
            'system': system_metrics,
            'application': app_metrics
        })
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return jsonify({'error': 'Failed to retrieve system metrics'}), 500


@system_bp.route('/api/jobs', methods=['GET'])
def list_background_jobs():
    """Get all background jobs with filtering options"""
    try:
        # Get query parameters
        status = request.args.get('status')
        job_type = request.args.get('job_type')
        project_id = request.args.get('project_id', type=int)
        limit = min(request.args.get('limit', 50, type=int), 200)  # Max 200
        
        # Build query
        query = BackgroundJob.query
        
        # Apply filters
        if status:
            query = query.filter(BackgroundJob.status == status)
        
        if job_type:
            query = query.filter(BackgroundJob.job_type == job_type)
        
        if project_id:
            query = query.filter(BackgroundJob.project_id == project_id)
        
        # Order by most recent first and limit
        jobs = query.order_by(BackgroundJob.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'jobs': [job.to_dict() for job in jobs],
            'total_count': query.count(),
            'filters': {
                'status': status,
                'job_type': job_type,
                'project_id': project_id,
                'limit': limit
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to list background jobs: {e}")
        return jsonify({'error': 'Failed to retrieve background jobs'}), 500


@system_bp.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_background_job(job_id):
    """Get detailed information about a specific background job"""
    try:
        job = BackgroundJob.query.get_or_404(job_id)
        return jsonify(job.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get background job {job_id}: {e}")
        return jsonify({'error': 'Failed to retrieve background job'}), 500


@system_bp.route('/api/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_background_job(job_id):
    """Cancel a pending or running background job"""
    try:
        try:
            from ..services.background import get_job_manager
        except ImportError:
            from services.background import get_job_manager
        
        job = BackgroundJob.query.get_or_404(job_id)
        
        if not job.is_active():
            return jsonify({'error': 'Job is not active and cannot be cancelled'}), 400
        
        # Use job manager to cancel the job
        job_manager = get_job_manager()
        cancelled = job_manager.cancel_job(job_id)
        
        if cancelled:
            logger.info(f"Cancelled background job {job_id}")
            # Refresh job data from database
            db.session.refresh(job)
            return jsonify({
                'message': f'Job {job_id} cancelled successfully',
                'job': job.to_dict()
            })
        else:
            return jsonify({'error': 'Failed to cancel job'}), 500
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to cancel background job {job_id}: {e}")
        return jsonify({'error': 'Failed to cancel background job'}), 500


@system_bp.route('/api/jobs/<int:job_id>/retry', methods=['POST'])
def retry_background_job(job_id):
    """Retry a failed background job"""
    try:
        try:
            from ..services.background import get_job_manager
        except ImportError:
            from services.background import get_job_manager
        
        job = BackgroundJob.query.get_or_404(job_id)
        
        if job.status != BackgroundJob.STATUS_FAILED:
            return jsonify({'error': 'Only failed jobs can be retried'}), 400
        
        # Use job manager to retry the job
        job_manager = get_job_manager()
        new_job_id = job_manager.retry_job(job_id)
        
        if new_job_id:
            new_job = BackgroundJob.query.get(new_job_id)
            logger.info(f"Retried failed job {job_id} as new job {new_job_id}")
            return jsonify({
                'message': f'Job {job_id} retried as new job {new_job_id}',
                'original_job': job.to_dict(),
                'new_job': new_job.to_dict()
            })
        else:
            return jsonify({'error': 'Failed to retry job'}), 500
        
    except Exception as e:
        logger.error(f"Failed to retry background job {job_id}: {e}")
        return jsonify({'error': 'Failed to retry background job'}), 500


@system_bp.route('/api/jobs/submit', methods=['POST'])
def submit_background_job():
    """Submit a new background job"""
    try:
        try:
            from ..services.background import get_job_manager
        except ImportError:
            from services.background import get_job_manager
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        job_type = data.get('job_type')
        if not job_type:
            return jsonify({'error': 'job_type is required'}), 400
        
        # Validate job type
        valid_types = [
            BackgroundJob.TYPE_REPOSITORY_PROCESSING,
            BackgroundJob.TYPE_SYSTEM_MAP_GENERATION,
            BackgroundJob.TYPE_AI_ANALYSIS,
            BackgroundJob.TYPE_DATA_MIGRATION
        ]
        
        if job_type not in valid_types:
            return jsonify({
                'error': f'Invalid job_type. Must be one of: {", ".join(valid_types)}'
            }), 400
        
        project_id = data.get('project_id')
        if project_id:
            # Verify project exists
            project = MissionControlProject.query.get(project_id)
            if not project:
                return jsonify({'error': f'Project {project_id} not found'}), 404
        
        # Submit job
        job_manager = get_job_manager()
        job_id = job_manager.submit_job(
            job_type=job_type,
            project_id=project_id,
            **data.get('parameters', {})
        )
        
        # Get job details
        job = BackgroundJob.query.get(job_id)
        
        logger.info(f"Submitted background job {job_id} of type {job_type}")
        return jsonify({
            'message': f'Job {job_id} submitted successfully',
            'job': job.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to submit background job: {e}")
        logger.error(f"Exception details: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to submit background job: {str(e)}'}), 500


@system_bp.route('/api/projects/status', methods=['GET'])
def get_projects_status():
    """Get detailed status for all projects with real-time updates"""
    try:
        from ..services.cache import get_status_cache
    except ImportError:
        from services.cache import get_status_cache
    
    try:
        cache = get_status_cache()
        
        # Check for specific project ID filter
        project_id = request.args.get('project_id', type=int)
        include_jobs = request.args.get('include_jobs', 'true').lower() == 'true'
        
        if project_id:
            # Get specific project status
            cache_key = f'project_status_{project_id}'
            cached_status = cache.get(cache_key)
            
            if cached_status:
                cached_status['cached'] = True
                return jsonify(cached_status)
            
            project_status = _get_detailed_project_status(project_id, include_jobs)
            if project_status:
                cache.set(cache_key, project_status, ttl=30)  # 30 second cache
                project_status['cached'] = False
                return jsonify(project_status)
            else:
                return jsonify({'error': 'Project not found'}), 404
        else:
            # Get all projects status
            cached_all = cache.get('all_projects_status')
            if cached_all:
                cached_all['cached'] = True
                return jsonify(cached_all)
            
            all_projects_status = _get_all_projects_status(include_jobs)
            cache.set('all_projects_status', all_projects_status, ttl=45)  # 45 second cache
            all_projects_status['cached'] = False
            return jsonify(all_projects_status)
        
    except Exception as e:
        logger.error(f"Failed to get projects status: {e}")
        return jsonify({'error': 'Failed to retrieve projects status'}), 500


def _get_detailed_project_status(project_id: int, include_jobs: bool = True):
    """Get detailed status for a specific project"""
    project = MissionControlProject.query.get(project_id)
    if not project:
        return None
    
    project_data = {
        'id': project.id,
        'name': project.name,
        'status': getattr(project, 'system_map_status', 'unknown'),
        'created_at': project.created_at.isoformat() if project.created_at else None,
        'updated_at': project.updated_at.isoformat() if project.updated_at else None
    }
    
    if include_jobs:
        # Get all jobs for this project
        jobs = BackgroundJob.query.filter_by(project_id=project_id).order_by(
            BackgroundJob.created_at.desc()
        ).limit(20).all()
        
        project_data['jobs'] = {
            'total': len(jobs),
            'active': [job.to_dict() for job in jobs if job.is_active()],
            'recent': [job.to_dict() for job in jobs[:10]],
            'summary': {
                'pending': sum(1 for job in jobs if job.status == BackgroundJob.STATUS_PENDING),
                'running': sum(1 for job in jobs if job.status == BackgroundJob.STATUS_RUNNING),
                'completed': sum(1 for job in jobs if job.status == BackgroundJob.STATUS_COMPLETED),
                'failed': sum(1 for job in jobs if job.status == BackgroundJob.STATUS_FAILED)
            }
        }
    
    # Get system maps count
    project_data['system_maps'] = {
        'count': SystemMap.query.filter_by(project_id=project_id).count(),
        'latest': None
    }
    
    latest_map = SystemMap.query.filter_by(project_id=project_id).order_by(
        SystemMap.generated_at.desc()
    ).first()
    
    if latest_map:
        project_data['system_maps']['latest'] = {
            'id': latest_map.id,
            'generated_at': latest_map.generated_at.isoformat() if latest_map.generated_at else None
        }
    
    # Get conversations count
    project_data['conversations'] = {
        'count': Conversation.query.filter_by(project_id=project_id).count()
    }
    
    project_data['last_updated'] = datetime.utcnow().isoformat()
    
    return project_data


def _get_all_projects_status(include_jobs: bool = True):
    """Get status for all projects"""
    projects = MissionControlProject.query.order_by(MissionControlProject.updated_at.desc()).all()
    
    projects_data = []
    for project in projects:
        project_data = {
            'id': project.id,
            'name': project.name,
            'status': getattr(project, 'system_map_status', 'unknown'),
            'created_at': project.created_at.isoformat() if project.created_at else None,
            'updated_at': project.updated_at.isoformat() if project.updated_at else None
        }
        
        if include_jobs:
            # Get active jobs count only for performance
            active_jobs_count = BackgroundJob.query.filter(
                BackgroundJob.project_id == project.id,
                BackgroundJob.status.in_([BackgroundJob.STATUS_PENDING, BackgroundJob.STATUS_RUNNING])
            ).count()
            
            project_data['active_jobs_count'] = active_jobs_count
        
        projects_data.append(project_data)
    
    return {
        'projects': projects_data,
        'total_count': len(projects_data),
        'last_updated': datetime.utcnow().isoformat()
    }


@system_bp.route('/api/cache/status', methods=['GET'])
def get_cache_status():
    """Get cache statistics and status"""
    try:
        from ..services.cache import get_status_cache
        
        cache = get_status_cache()
        stats = cache.get_stats()
        
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'cache_stats': stats,
            'cache_enabled': True
        })
        
    except Exception as e:
        logger.error(f"Failed to get cache status: {e}")
        return jsonify({'error': 'Failed to retrieve cache status'}), 500


@system_bp.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all cached data"""
    try:
        from ..services.cache import get_status_cache
        
        cache = get_status_cache()
        cache.clear()
        
        logger.info("Cache cleared manually")
        return jsonify({
            'message': 'Cache cleared successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return jsonify({'error': 'Failed to clear cache'}), 500


@system_bp.route('/api/cache/clear/<cache_key>', methods=['DELETE'])
def clear_cache_key(cache_key):
    """Clear specific cache key"""
    try:
        from ..services.cache import get_status_cache
        
        cache = get_status_cache()
        deleted = cache.delete(cache_key)
        
        if deleted:
            logger.info(f"Cache key '{cache_key}' cleared manually")
            return jsonify({
                'message': f'Cache key "{cache_key}" cleared successfully',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'message': f'Cache key "{cache_key}" not found',
                'timestamp': datetime.utcnow().isoformat()
            }), 404
        
    except Exception as e:
        logger.error(f"Failed to clear cache key {cache_key}: {e}")
        return jsonify({'error': f'Failed to clear cache key: {cache_key}'}), 500


@system_bp.route('/api/config', methods=['GET'])
def get_configuration():
    """Get current application configuration (non-sensitive values only)"""
    try:
        config = {
            'debug': current_app.config.get('DEBUG', False),
            'database_type': 'sqlite' if current_app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite') else 'other',
            'max_workers': current_app.config.get('MAX_WORKERS', 4),
            'static_folder': current_app.config.get('STATIC_FOLDER', 'frontend/dist'),
            'flask_env': os.environ.get('FLASK_ENV', 'production'),
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        }
        
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'configuration': config
        })
        
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        return jsonify({'error': 'Failed to retrieve configuration'}), 500


def get_system_metrics():
    """Get system resource usage metrics"""
    if not PSUTIL_AVAILABLE:
        return {
            'available': False,
            'message': 'System metrics unavailable - psutil not installed'
        }
    
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage for current directory
        disk = psutil.disk_usage('.')
        
        # Process information
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return {
            'available': True,
            'cpu': {
                'percent': cpu_percent,
                'count': psutil.cpu_count()
            },
            'memory': {
                'total_bytes': memory.total,
                'available_bytes': memory.available,
                'used_bytes': memory.used,
                'percent': memory.percent
            },
            'disk': {
                'total_bytes': disk.total,
                'free_bytes': disk.free,
                'used_bytes': disk.used,
                'percent': (disk.used / disk.total) * 100
            },
            'process': {
                'memory_rss_bytes': process_memory.rss,
                'memory_vms_bytes': process_memory.vms,
                'pid': process.pid,
                'threads': process.num_threads()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {
            'available': False,
            'error': 'Failed to retrieve system metrics',
            'message': str(e)
        }


def get_application_metrics():
    """Get application-specific metrics"""
    try:
        from ..services.background import get_job_manager
        
        # Count active background jobs by type
        job_counts = {}
        for job_type in [BackgroundJob.TYPE_REPOSITORY_PROCESSING, 
                        BackgroundJob.TYPE_SYSTEM_MAP_GENERATION,
                        BackgroundJob.TYPE_AI_ANALYSIS, 
                        BackgroundJob.TYPE_DATA_MIGRATION]:
            job_counts[job_type] = BackgroundJob.query.filter_by(
                job_type=job_type,
                status=BackgroundJob.STATUS_RUNNING
            ).count()
        
        # Get recent activity (last hour)
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_activity = {
            'projects_created': MissionControlProject.query.filter(MissionControlProject.created_at >= recent_cutoff).count(),
            'jobs_completed': BackgroundJob.query.filter(
                BackgroundJob.completed_at >= recent_cutoff,
                BackgroundJob.status == BackgroundJob.STATUS_COMPLETED
            ).count(),
            'jobs_failed': BackgroundJob.query.filter(
                BackgroundJob.completed_at >= recent_cutoff,
                BackgroundJob.status == BackgroundJob.STATUS_FAILED
            ).count()
        }
        
        # Get job manager stats
        try:
            job_manager = get_job_manager()
            job_manager_stats = job_manager.get_system_stats()
        except Exception:
            job_manager_stats = {'error': 'Job manager not available'}
        
        return {
            'active_job_counts': job_counts,
            'recent_activity': recent_activity,
            'background_job_manager': {
                'initialized': True,
                'max_workers': current_app.config.get('MAX_WORKERS', 4),
                'stats': job_manager_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get application metrics: {e}")
        return {
            'error': 'Failed to retrieve application metrics',
            'message': str(e)
        }


def get_uptime_seconds():
    """Get application uptime in seconds"""
    if not PSUTIL_AVAILABLE:
        return None
    
    try:
        process = psutil.Process()
        create_time = process.create_time()
        uptime = datetime.now().timestamp() - create_time
        return int(uptime)
    except Exception:
        return None


@system_bp.route('/api/kanban/clear', methods=['POST'])
def clear_kanban_board():
    """Clear completed tasks and failed jobs from kanban board"""
    try:
        data = request.get_json() or {}
        clear_tasks = data.get('clear_tasks', True)
        clear_failed_jobs = data.get('clear_failed_jobs', True)
        clear_old_jobs = data.get('clear_old_jobs', False)
        
        results = {
            'cleared_tasks': 0,
            'cleared_failed_jobs': 0,
            'cleared_old_jobs': 0,
            'backups_created': []
        }
        
        # Clear completed tasks
        if clear_tasks:
            try:
                from sqlalchemy import text
                
                # Use raw SQL with correct enum case
                result = db.session.execute(text("""
                    SELECT id, title, task_number, completed_at, pr_url
                    FROM task 
                    WHERE status = 'DONE';
                """))
                
                done_tasks = result.fetchall()
                
                if done_tasks:
                    # Create backup
                    backup_data = []
                    for task in done_tasks:
                        backup_data.append({
                            'id': task.id,
                            'title': task.title,
                            'task_number': task.task_number,
                            'completed_at': str(task.completed_at),
                            'pr_url': task.pr_url
                        })
                    
                    backup_filename = f"completed_tasks_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                    
                    try:
                        import json
                        with open(backup_filename, 'w') as f:
                            json.dump(backup_data, f, indent=2, default=str)
                        results['backups_created'].append(backup_filename)
                    except Exception as backup_error:
                        logger.warning(f"Failed to create backup: {backup_error}")
                    
                    # Delete tasks using raw SQL
                    delete_result = db.session.execute(text("DELETE FROM task WHERE status = 'DONE';"))
                    results['cleared_tasks'] = delete_result.rowcount
                    logger.info(f"Cleared {results['cleared_tasks']} completed tasks")
                
            except Exception as e:
                logger.error(f"Failed to clear completed tasks: {e}")
                results['cleared_tasks'] = 0
        
        # Clear failed jobs
        if clear_failed_jobs:
            try:
                from ..models.background_job import BackgroundJob
            except ImportError:
                from models.background_job import BackgroundJob
            
            # Only clear failed jobs older than 1 hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            failed_jobs = BackgroundJob.query.filter(
                BackgroundJob.status == BackgroundJob.STATUS_FAILED,
                BackgroundJob.created_at < cutoff_time
            ).all()
            
            if failed_jobs:
                # Create backup
                backup_data = [job.to_dict() for job in failed_jobs]
                backup_filename = f"failed_jobs_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                
                try:
                    import json
                    with open(backup_filename, 'w') as f:
                        json.dump(backup_data, f, indent=2, default=str)
                    results['backups_created'].append(backup_filename)
                except Exception as backup_error:
                    logger.warning(f"Failed to create backup: {backup_error}")
                
                # Delete jobs
                for job in failed_jobs:
                    db.session.delete(job)
                
                results['cleared_failed_jobs'] = len(failed_jobs)
                logger.info(f"Cleared {len(failed_jobs)} failed jobs")
        
        # Clear old completed jobs
        if clear_old_jobs:
            try:
                from ..models.background_job import BackgroundJob
            except ImportError:
                from models.background_job import BackgroundJob
            
            # Clear completed jobs older than 7 days
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            old_jobs = BackgroundJob.query.filter(
                BackgroundJob.status == BackgroundJob.STATUS_COMPLETED,
                BackgroundJob.completed_at < cutoff_time
            ).all()
            
            if old_jobs:
                for job in old_jobs:
                    db.session.delete(job)
                
                results['cleared_old_jobs'] = len(old_jobs)
                logger.info(f"Cleared {len(old_jobs)} old completed jobs")
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Kanban board cleared successfully',
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to clear kanban board: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear kanban board',
            'details': str(e)
        }), 500


@system_bp.route('/api/kanban/status', methods=['GET'])
def get_kanban_status():
    """Get current kanban board status for clearing decisions"""
    try:
        try:
            from ..models.task import Task, TaskStatus
            from ..models.background_job import BackgroundJob
        except ImportError:
            from models.task import Task, TaskStatus
            from models.background_job import BackgroundJob
        
        # Task counts by status using raw SQL
        task_counts = {}
        result = db.session.execute(text("""
            SELECT status, COUNT(*) as count
            FROM task 
            GROUP BY status;
        """))
        
        for status, count in result.fetchall():
            task_counts[status.lower()] = count
        
        # Job counts by status
        job_counts = {}
        for status in [BackgroundJob.STATUS_PENDING, BackgroundJob.STATUS_RUNNING, 
                      BackgroundJob.STATUS_COMPLETED, BackgroundJob.STATUS_FAILED, 
                      BackgroundJob.STATUS_CANCELLED]:
            count = BackgroundJob.query.filter_by(status=status).count()
            job_counts[status] = count
        
        # Failed jobs older than 1 hour (clearable)
        clearable_failed_jobs_result = db.session.execute(text("""
            SELECT COUNT(*) FROM background_job 
            WHERE status = 'failed' 
            AND created_at < NOW() - INTERVAL '1 hour';
        """))
        clearable_failed_jobs = clearable_failed_jobs_result.scalar()
        
        # Old completed jobs (clearable)
        clearable_old_jobs_result = db.session.execute(text("""
            SELECT COUNT(*) FROM background_job 
            WHERE status = 'completed' 
            AND completed_at < NOW() - INTERVAL '7 days';
        """))
        clearable_old_jobs = clearable_old_jobs_result.scalar()
        
        # Recent activity
        recent_task_updates_result = db.session.execute(text("""
            SELECT COUNT(*) FROM task 
            WHERE updated_at >= NOW() - INTERVAL '24 hours';
        """))
        recent_task_updates = recent_task_updates_result.scalar()
        
        recent_job_updates_result = db.session.execute(text("""
            SELECT COUNT(*) FROM background_job 
            WHERE updated_at >= NOW() - INTERVAL '24 hours';
        """))
        recent_job_updates = recent_job_updates_result.scalar()
        
        return jsonify({
            'task_counts': task_counts,
            'job_counts': job_counts,
            'clearable_items': {
                'completed_tasks': task_counts.get('done', 0),
                'failed_jobs': clearable_failed_jobs,
                'old_completed_jobs': clearable_old_jobs
            },
            'recent_activity': {
                'task_updates_24h': recent_task_updates,
                'job_updates_24h': recent_job_updates
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get kanban status: {e}")
        return jsonify({
            'error': 'Failed to get kanban status',
            'details': str(e)
        }), 500


# Error handlers for this blueprint
@system_bp.errorhandler(404)
def resource_not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@system_bp.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error in system API: {error}")
    return jsonify({'error': 'Internal server error'}), 500