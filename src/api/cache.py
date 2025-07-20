"""
Cache management API endpoints
Provides cache statistics, invalidation, and session management
"""

from flask import Blueprint, request, jsonify, session
from typing import Dict, Any
import logging

try:
    from ..services.distributed_cache import (
        get_distributed_cache, get_session_manager, 
        get_cache_invalidation_service, get_cache_warming_service
    )
except ImportError:
    from services.distributed_cache import (
        get_distributed_cache, get_session_manager,
        get_cache_invalidation_service, get_cache_warming_service
    )

logger = logging.getLogger(__name__)

cache_bp = Blueprint('cache', __name__, url_prefix='/api/cache')


@cache_bp.route('/stats', methods=['GET'])
def get_cache_stats():
    """Get comprehensive cache statistics"""
    try:
        cache = get_distributed_cache()
        session_mgr = get_session_manager()
        
        stats = cache.get_stats()
        active_sessions = session_mgr.get_active_sessions()
        
        return jsonify({
            'success': True,
            'cache_stats': stats,
            'active_sessions_count': len(active_sessions),
            'session_details': [
                {
                    'session_id': s.get('session_id'),
                    'created_at': s.get('created_at'),
                    'last_accessed': s.get('last_accessed'),
                    'ip_address': s.get('ip_address')
                }
                for s in active_sessions
            ] if request.args.get('include_details') == 'true' else []
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/invalidate', methods=['POST'])
def invalidate_cache():
    """Manually invalidate cache entries"""
    try:
        data = request.get_json()
        cache = get_distributed_cache()
        
        if 'pattern' in data:
            # Invalidate by pattern
            count = cache.invalidate_pattern(
                pattern=data['pattern'],
                namespace=data.get('namespace')
            )
            return jsonify({
                'success': True,
                'invalidated_count': count,
                'pattern': data['pattern']
            })
        
        elif 'key' in data:
            # Invalidate specific key
            success = cache.delete(
                key=data['key'],
                namespace=data.get('namespace'),
                user_id=data.get('user_id')
            )
            return jsonify({
                'success': success,
                'key': data['key']
            })
        
        elif 'namespace' in data:
            # Clear entire namespace
            count = cache.clear_namespace(
                namespace=data['namespace'],
                user_id=data.get('user_id')
            )
            return jsonify({
                'success': True,
                'invalidated_count': count,
                'namespace': data['namespace']
            })
        
        else:
            return jsonify({
                'success': False,
                'error': 'Must specify pattern, key, or namespace'
            }), 400
            
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/warm', methods=['POST'])
def warm_cache():
    """Trigger cache warming"""
    try:
        data = request.get_json() or {}
        warming_service = get_cache_warming_service()
        
        if 'project_id' in data:
            # Warm specific project data
            warming_service.warm_project_data(data['project_id'])
            return jsonify({
                'success': True,
                'message': f"Cache warming triggered for project {data['project_id']}"
            })
        else:
            # Run general warming cycle
            warming_service.run_warming_cycle()
            return jsonify({
                'success': True,
                'message': 'Cache warming cycle completed'
            })
            
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """List active sessions (admin endpoint)"""
    try:
        session_mgr = get_session_manager()
        active_sessions = session_mgr.get_active_sessions()
        
        return jsonify({
            'success': True,
            'active_sessions': len(active_sessions),
            'sessions': [
                {
                    'session_id': s.get('session_id'),
                    'created_at': s.get('created_at'),
                    'last_accessed': s.get('last_accessed'),
                    'ip_address': s.get('ip_address'),
                    'user_agent': str(s.get('user_agent'))[:100] if s.get('user_agent') else None,
                    'user_data_keys': list(s.get('user_data', {}).keys())
                }
                for s in active_sessions
            ]
        })
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Delete a specific session"""
    try:
        session_mgr = get_session_manager()
        success = session_mgr.delete_session(session_id)
        
        return jsonify({
            'success': success,
            'session_id': session_id,
            'message': 'Session deleted successfully' if success else 'Session not found'
        })
        
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/sessions/current', methods=['GET'])
def get_current_session():
    """Get current session information"""
    try:
        session_mgr = get_session_manager()
        
        # Try to get session ID from various sources
        session_id = (
            request.headers.get('X-Session-ID') or
            request.args.get('session_id') or
            session.get('session_id')
        )
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'No session ID provided'
            }), 400
        
        session_data = session_mgr.get_session(session_id)
        
        if session_data:
            return jsonify({
                'success': True,
                'session': {
                    'session_id': session_data.get('session_id'),
                    'created_at': session_data.get('created_at'),
                    'last_accessed': session_data.get('last_accessed'),
                    'user_data': session_data.get('user_data', {})
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Session not found or expired'
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting current session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/sessions/current', methods=['POST'])
def create_or_update_session():
    """Create new session or update existing one"""
    try:
        data = request.get_json() or {}
        session_mgr = get_session_manager()
        
        session_id = (
            request.headers.get('X-Session-ID') or
            request.args.get('session_id') or
            session.get('session_id')
        )
        
        if session_id:
            # Update existing session
            success = session_mgr.update_session(session_id, data)
            if success:
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'action': 'updated'
                })
            else:
                # Session doesn't exist, create new one
                session_id = session_mgr.create_session(data)
                session['session_id'] = session_id
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'action': 'created'
                })
        else:
            # Create new session
            session_id = session_mgr.create_session(data)
            session['session_id'] = session_id
            return jsonify({
                'success': True,
                'session_id': session_id,
                'action': 'created'
            })
            
    except Exception as e:
        logger.error(f"Error creating/updating session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/health', methods=['GET'])
def cache_health():
    """Check cache system health"""
    try:
        cache = get_distributed_cache()
        stats = cache.get_stats()
        
        is_healthy = stats.get('redis_connected', False)
        
        return jsonify({
            'success': True,
            'healthy': is_healthy,
            'redis_connected': stats.get('redis_connected', False),
            'cache_entries': stats.get('our_cache_keys', 0),
            'l1_cache_entries': stats.get('l1_cache_entries', 0)
        }), 200 if is_healthy else 503
        
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return jsonify({
            'success': False,
            'healthy': False,
            'error': str(e)
        }), 503