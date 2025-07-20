"""
System API Blueprint
REST endpoints for system status, health checks, and monitoring
"""

from flask import Blueprint, jsonify, current_app, request
try:
    from ..models import BackgroundJob, Project, SystemMap, Conversation, db
    from ..core.database import check_database_health, get_database_statistics
    from ..core.events import create_event, EventType
    from ..services.event_bus import publish_event
except ImportError:
    from models import BackgroundJob, Project, SystemMap, Conversation, db
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
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'status': overall_status,
        'cached': False,
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
    
    # Generate fresh project status data
    projects = Project.query.all()
    
    status_counts = {}
    recent_projects = []
    active_projects = []
    
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    
    for project in projects:
        # Count by status
        status_counts[project.status] = status_counts.get(project.status, 0) + 1
        
        # Recent projects
        if project.created_at >= recent_cutoff:
            recent_projects.append(project.to_dict())
        
        # Active projects (with recent activity)
        if project.updated_at >= recent_cutoff or project.status in ['processing', 'running']:
            active_projects.append({
                'id': project.id,
                'name': project.name,
                'status': project.status,
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
            project = Project.query.get(project_id)
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
    project = Project.query.get(project_id)
    if not project:
        return None
    
    project_data = project.to_dict()
    
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
    projects = Project.query.order_by(Project.updated_at.desc()).all()
    
    projects_data = []
    for project in projects:
        project_data = project.to_dict()
        
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
            'projects_created': Project.query.filter(Project.created_at >= recent_cutoff).count(),
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


# Error handlers for this blueprint
@system_bp.errorhandler(404)
def resource_not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@system_bp.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error in system API: {error}")
    return jsonify({'error': 'Internal server error'}), 500