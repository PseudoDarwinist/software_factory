"""
Monitoring API endpoints for real-time system monitoring dashboard.
Provides event analytics, agent status, system health, and integration monitoring.
"""

import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from flask import Blueprint, request, jsonify, Response, stream_template
from flask_socketio import emit
from sqlalchemy import desc, func, and_, or_

try:
    from ..models.base import db
    from ..models.event_log import EventLog
    from ..models.monitoring_metrics import MonitoringMetrics, AgentStatus, SystemHealth
    from ..services.monitoring_service import MonitoringService
    from ..services.websocket_server import get_websocket_server
except ImportError:
    from models.base import db
    from models.event_log import EventLog
    from models.monitoring_metrics import MonitoringMetrics, AgentStatus, SystemHealth
    from services.monitoring_service import MonitoringService
    from services.websocket_server import get_websocket_server

logger = logging.getLogger(__name__)

# Create blueprint
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')

# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get or create monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        websocket_server = get_websocket_server()
        _monitoring_service = MonitoringService(websocket_server=websocket_server)
        if not _monitoring_service.running:
            _monitoring_service.start()
    return _monitoring_service


@monitoring_bp.route('/events', methods=['GET'])
def get_events():
    """
    Get event data with filtering and pagination.
    
    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 1000)
    - event_type: Filter by event type
    - source: Filter by event source
    - project_id: Filter by project ID
    - from_time: Start time (ISO format)
    - to_time: End time (ISO format)
    - search: Search in event data
    """
    try:
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 1000)
        event_type = request.args.get('event_type')
        source = request.args.get('source')
        project_id = request.args.get('project_id')
        from_time_str = request.args.get('from_time')
        to_time_str = request.args.get('to_time')
        search_query = request.args.get('search')
        
        # Build query
        query = EventLog.query
        
        # Apply filters
        if event_type:
            query = query.filter(EventLog.event_type == event_type)
        
        if source:
            query = query.filter(EventLog.source_agent == source)
        
        if project_id:
            query = query.filter(EventLog.project_id == project_id)
        
        # Time range filtering
        if from_time_str:
            try:
                from_time = datetime.fromisoformat(from_time_str.replace('Z', '+00:00'))
                query = query.filter(EventLog.timestamp >= from_time)
            except ValueError:
                return jsonify({'error': 'Invalid from_time format. Use ISO format.'}), 400
        
        if to_time_str:
            try:
                to_time = datetime.fromisoformat(to_time_str.replace('Z', '+00:00'))
                query = query.filter(EventLog.timestamp <= to_time)
            except ValueError:
                return jsonify({'error': 'Invalid to_time format. Use ISO format.'}), 400
        
        # Search filtering
        if search_query:
            search_filter = or_(
                EventLog.event_type.ilike(f'%{search_query}%'),
                EventLog.source_agent.ilike(f'%{search_query}%'),
                EventLog.payload.ilike(f'%{search_query}%')
            )
            query = query.filter(search_filter)
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(desc(EventLog.timestamp))
        
        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format events
        events = []
        for event in pagination.items:
            event_data = {
                'id': event.id,
                'event_id': event.event_id,
                'event_type': event.event_type,
                'source': event.source_agent,
                'project_id': event.project_id,
                'user_id': event.actor,
                'timestamp': event.timestamp.isoformat(),
                'correlation_id': event.correlation_id,
                'trace_id': event.trace_id,
                'data': event.payload_dict,
                'payload_size': len(event.payload or '{}')
            }
            events.append(event_data)
        
        return jsonify({
            'events': events,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return jsonify({'error': 'Failed to retrieve events'}), 500


@monitoring_bp.route('/events/<int:event_id>', methods=['GET'])
def get_event_detail(event_id):
    """Get detailed information for a specific event."""
    try:
        event = EventLog.query.get_or_404(event_id)
        
        event_detail = {
            'id': event.id,
            'event_id': event.event_id,
            'event_type': event.event_type,
            'source': event.source_agent,
            'project_id': event.project_id,
            'user_id': event.actor,
            'timestamp': event.timestamp.isoformat(),
            'created_at': event.created_at.isoformat(),
            'correlation_id': event.correlation_id,
            'trace_id': event.trace_id,
            'data': event.payload_dict,
            'payload_size': len(event.payload or '{}')
        }
        
        return jsonify(event_detail)
        
    except Exception as e:
        logger.error(f"Error getting event detail: {e}")
        return jsonify({'error': 'Failed to retrieve event detail'}), 500


@monitoring_bp.route('/events/analytics', methods=['GET'])
def get_event_analytics():
    """
    Get event analytics and aggregated statistics.
    
    Query Parameters:
    - hours: Time window in hours (default: 24)
    - group_by: Group by field (event_type, source, hour)
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        group_by = request.args.get('group_by', 'event_type')
        
        # Calculate time window
        from_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get monitoring service for real-time metrics
        monitoring_service = get_monitoring_service()
        event_metrics = monitoring_service.collect_event_metrics()
        
        # Get historical data from database
        query = EventLog.query.filter(EventLog.timestamp >= from_time)
        
        # Group by analysis
        if group_by == 'event_type':
            # Group by event type
            type_counts = db.session.query(
                EventLog.event_type,
                func.count(EventLog.id).label('count')
            ).filter(
                EventLog.timestamp >= from_time
            ).group_by(EventLog.event_type).all()
            
            grouped_data = {row.event_type: row.count for row in type_counts}
            
        elif group_by == 'source':
            # Group by source
            source_counts = db.session.query(
                EventLog.source_agent,
                func.count(EventLog.id).label('count')
            ).filter(
                EventLog.timestamp >= from_time
            ).group_by(EventLog.source_agent).all()
            
            grouped_data = {row.source_agent: row.count for row in source_counts}
            
        elif group_by == 'hour':
            # Group by hour
            hourly_counts = db.session.query(
                func.date_trunc('hour', EventLog.timestamp).label('hour'),
                func.count(EventLog.id).label('count')
            ).filter(
                EventLog.timestamp >= from_time
            ).group_by(func.date_trunc('hour', EventLog.timestamp)).all()
            
            grouped_data = {
                row.hour.isoformat(): row.count 
                for row in hourly_counts
            }
        else:
            grouped_data = {}
        
        # Calculate total events in time window
        total_events = query.count()
        
        # Calculate average events per hour
        avg_events_per_hour = total_events / max(hours, 1)
        
        analytics = {
            'time_window': {
                'hours': hours,
                'from_time': from_time.isoformat(),
                'to_time': datetime.utcnow().isoformat()
            },
            'summary': {
                'total_events': total_events,
                'events_per_hour': avg_events_per_hour,
                'events_per_minute': event_metrics.events_per_minute,
                'error_rate': event_metrics.error_rate
            },
            'grouped_data': grouped_data,
            'group_by': group_by,
            'real_time_metrics': {
                'events_by_type': event_metrics.events_by_type,
                'recent_events_count': len(event_metrics.recent_events)
            }
        }
        
        return jsonify(analytics)
        
    except Exception as e:
        logger.error(f"Error getting event analytics: {e}")
        return jsonify({'error': 'Failed to retrieve event analytics'}), 500


@monitoring_bp.route('/events/search', methods=['POST'])
def search_events():
    """
    Advanced event search with complex filtering.
    
    Request Body:
    {
        "filters": {
            "event_types": ["type1", "type2"],
            "sources": ["source1", "source2"],
            "project_ids": ["proj1", "proj2"],
            "time_range": {
                "from": "2024-01-01T00:00:00Z",
                "to": "2024-01-02T00:00:00Z"
            },
            "search_text": "error",
            "user_ids": ["user1", "user2"]
        },
        "pagination": {
            "page": 1,
            "per_page": 50
        },
        "sort": {
            "field": "timestamp",
            "order": "desc"
        }
    }
    """
    try:
        data = request.get_json() or {}
        filters = data.get('filters', {})
        pagination_params = data.get('pagination', {})
        sort_params = data.get('sort', {})
        
        # Build query
        query = EventLog.query
        
        # Apply filters
        if filters.get('event_types'):
            query = query.filter(EventLog.event_type.in_(filters['event_types']))
        
        if filters.get('sources'):
            query = query.filter(EventLog.source_agent.in_(filters['sources']))
        
        if filters.get('project_ids'):
            query = query.filter(EventLog.project_id.in_(filters['project_ids']))
        
        if filters.get('user_ids'):
            query = query.filter(EventLog.actor.in_(filters['user_ids']))
        
        # Time range
        time_range = filters.get('time_range', {})
        if time_range.get('from'):
            from_time = datetime.fromisoformat(time_range['from'].replace('Z', '+00:00'))
            query = query.filter(EventLog.timestamp >= from_time)
        
        if time_range.get('to'):
            to_time = datetime.fromisoformat(time_range['to'].replace('Z', '+00:00'))
            query = query.filter(EventLog.timestamp <= to_time)
        
        # Text search
        if filters.get('search_text'):
            search_text = filters['search_text']
            search_filter = or_(
                EventLog.event_type.ilike(f'%{search_text}%'),
                EventLog.source_agent.ilike(f'%{search_text}%'),
                EventLog.payload.ilike(f'%{search_text}%')
            )
            query = query.filter(search_filter)
        
        # Sorting
        sort_field = sort_params.get('field', 'timestamp')
        sort_order = sort_params.get('order', 'desc')
        
        if hasattr(EventLog, sort_field):
            field = getattr(EventLog, sort_field)
            if sort_order.lower() == 'desc':
                query = query.order_by(desc(field))
            else:
                query = query.order_by(field)
        else:
            query = query.order_by(desc(EventLog.timestamp))
        
        # Pagination
        page = pagination_params.get('page', 1)
        per_page = min(pagination_params.get('per_page', 50), 1000)
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format results
        events = []
        for event in pagination.items:
            event_data = {
                'id': event.id,
                'event_id': event.event_id,
                'event_type': event.event_type,
                'source': event.source_agent,
                'project_id': event.project_id,
                'user_id': event.actor,
                'timestamp': event.timestamp.isoformat(),
                'correlation_id': event.correlation_id,
                'trace_id': event.trace_id,
                'data': event.payload_dict
            }
            events.append(event_data)
        
        return jsonify({
            'events': events,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'filters_applied': filters,
            'sort_applied': sort_params
        })
        
    except Exception as e:
        logger.error(f"Error in advanced event search: {e}")
        return jsonify({'error': 'Failed to search events'}), 500


@monitoring_bp.route('/events/stream', methods=['GET'])
def stream_events():
    """
    Server-Sent Events (SSE) endpoint for real-time event streaming.
    Alternative to WebSocket for simple event streaming.
    """
    def event_generator():
        """Generate server-sent events."""
        try:
            monitoring_service = get_monitoring_service()
            
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            # Get recent events to start with
            event_metrics = monitoring_service.collect_event_metrics()
            for event in event_metrics.recent_events[-10:]:  # Last 10 events
                yield f"data: {json.dumps({'type': 'event', 'data': event})}\n\n"
            
            # This is a simplified implementation
            # In a real implementation, you'd need to hook into the monitoring service's
            # event stream or use a message queue for real-time updates
            
        except Exception as e:
            logger.error(f"Error in event stream: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error'})}\n\n"
    
    return Response(
        event_generator(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )


@monitoring_bp.route('/metrics', methods=['GET'])
def get_current_metrics():
    """Get current real-time metrics from monitoring service."""
    try:
        monitoring_service = get_monitoring_service()
        
        # Collect all current metrics
        event_metrics = monitoring_service.collect_event_metrics()
        agent_metrics = monitoring_service.collect_agent_metrics()
        system_health = monitoring_service.collect_system_health()
        integration_status = monitoring_service.collect_integration_status()
        
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_metrics': {
                'total_events': event_metrics.total_events,
                'events_per_minute': event_metrics.events_per_minute,
                'events_by_type': event_metrics.events_by_type,
                'average_processing_time': event_metrics.average_processing_time,
                'error_rate': event_metrics.error_rate,
                'recent_events_count': len(event_metrics.recent_events)
            },
            'agent_metrics': {
                agent_id: agent.to_dict()
                for agent_id, agent in agent_metrics.items()
            },
            'system_health': {
                'overall_score': system_health.overall_score,
                'components': system_health.components,
                'resources': system_health.resources,
                'performance': system_health.performance
            },
            'integration_status': integration_status.integrations
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting current metrics: {e}")
        return jsonify({'error': 'Failed to retrieve current metrics'}), 500


@monitoring_bp.route('/dashboard', methods=['GET'])
def get_dashboard_metrics():
    """
    Get comprehensive dashboard metrics matching the TypeScript DashboardMetrics interface.
    
    This endpoint returns mock data structured to match the frontend monitoring dashboard
    requirements, including time series data for charts and real-time metrics.
    """
    try:
        now = datetime.utcnow()
        
        # Generate time series data for the last 24 hours
        def generate_time_series(base_value, variation=0.2, points=24):
            """Generate realistic time series data."""
            data = []
            for i in range(points):
                timestamp = (now - timedelta(hours=points-1-i)).isoformat()
                # Add some random variation around base value
                value = base_value * (1 + random.uniform(-variation, variation))
                data.append({
                    'timestamp': timestamp,
                    'value': round(max(0, value), 2)
                })
            return data
        
        # Mock System Health
        system_health = {
            'overallScore': 87.5,
            'status': 'healthy',
            'components': {
                'database': {
                    'status': 'healthy',
                    'responseTime': 12.5,
                    'errorRate': 0.02,
                    'lastCheck': (now - timedelta(minutes=1)).isoformat(),
                    'message': 'All database connections healthy'
                },
                'redis': {
                    'status': 'healthy',
                    'responseTime': 3.2,
                    'errorRate': 0.0,
                    'lastCheck': (now - timedelta(minutes=1)).isoformat(),
                    'message': 'Redis cache responding normally'
                },
                'websocket': {
                    'status': 'warning',
                    'responseTime': 45.7,
                    'errorRate': 0.05,
                    'lastCheck': (now - timedelta(minutes=2)).isoformat(),
                    'message': 'Higher than normal latency detected'
                },
                'apis': {
                    'status': 'healthy',
                    'responseTime': 156.3,
                    'errorRate': 0.01,
                    'lastCheck': (now - timedelta(seconds=30)).isoformat(),
                    'message': 'API endpoints responding normally'
                }
            },
            'resources': {
                'cpuUsage': 42.8,
                'memoryUsage': 68.5,
                'diskUsage': 23.1,
                'networkLatency': 25.7
            },
            'performance': {
                'responseTime': 234.5,
                'throughput': 1250.0,
                'errorRate': 0.023
            },
            'lastUpdated': now.isoformat()
        }
        
        # Mock Event Metrics with realistic data
        recent_events = []
        event_types = ['stage.define.started', 'stage.think.completed', 'agent.build.success', 'integration.slack.message', 'system.health.check']
        
        for i in range(10):
            event_time = now - timedelta(minutes=i*5)
            recent_events.append({
                'id': f'evt_{i+1:03d}',
                'type': event_types[i % len(event_types)],
                'source': f'agent_{(i % 3) + 1}',
                'timestamp': event_time.isoformat(),
                'payload': {
                    'project_id': f'proj_{(i % 2) + 1}',
                    'user_id': f'user_{(i % 3) + 1}',
                    'duration': round(random.uniform(100, 5000), 2),
                    'status': 'success' if i % 7 != 0 else 'error'
                },
                'processingTime': round(random.uniform(50, 500), 2),
                'success': i % 7 != 0,
                'error': 'Processing timeout' if i % 7 == 0 else None
            })
        
        event_metrics = {
            'totalEvents': 15847,
            'eventsPerMinute': 12.3,
            'eventsByType': {
                'stage.define.started': 3420,
                'stage.think.completed': 3180,
                'stage.build.started': 2950,
                'agent.build.success': 2890,
                'integration.slack.message': 1876,
                'system.health.check': 1531
            },
            'averageProcessingTime': 287.5,
            'errorRate': 0.028,
            'recentEvents': recent_events,
            'lastUpdated': now.isoformat()
        }
        
        # Mock Agent Metrics
        agent_metrics = {
            'define_agent': {
                'id': 'define_agent',
                'name': 'Define Agent',
                'status': 'running',
                'metrics': {
                    'eventsProcessed': 4250,
                    'successRate': 0.965,
                    'averageProcessingTime': 1250.5,
                    'currentLoad': 23,
                    'lastActivity': (now - timedelta(minutes=2)).isoformat()
                },
                'configuration': {
                    'maxConcurrentTasks': 10,
                    'timeout': 30000,
                    'retryAttempts': 3
                },
                'logs': [
                    {
                        'timestamp': (now - timedelta(minutes=1)).isoformat(),
                        'level': 'info',
                        'message': 'Processing project definition for proj_001',
                        'metadata': {'project_id': 'proj_001', 'stage': 'analysis'}
                    },
                    {
                        'timestamp': (now - timedelta(minutes=3)).isoformat(),
                        'level': 'warn',
                        'message': 'High processing time detected',
                        'metadata': {'duration': 5400, 'threshold': 5000}
                    },
                    {
                        'timestamp': (now - timedelta(minutes=5)).isoformat(),
                        'level': 'info',
                        'message': 'Successfully completed project definition',
                        'metadata': {'project_id': 'proj_002', 'duration': 2100}
                    }
                ],
                'lastHeartbeat': (now - timedelta(seconds=45)).isoformat()
            },
            'think_agent': {
                'id': 'think_agent',
                'name': 'Think Agent',
                'status': 'running',
                'metrics': {
                    'eventsProcessed': 3875,
                    'successRate': 0.982,
                    'averageProcessingTime': 890.2,
                    'currentLoad': 15,
                    'lastActivity': (now - timedelta(minutes=1)).isoformat()
                },
                'configuration': {
                    'maxConcurrentTasks': 8,
                    'timeout': 25000,
                    'retryAttempts': 2
                },
                'logs': [
                    {
                        'timestamp': (now - timedelta(minutes=2)).isoformat(),
                        'level': 'info',
                        'message': 'Analyzing requirements for technical specification',
                        'metadata': {'project_id': 'proj_003', 'complexity': 'high'}
                    }
                ],
                'lastHeartbeat': (now - timedelta(seconds=30)).isoformat()
            },
            'build_agent': {
                'id': 'build_agent',
                'name': 'Build Agent',
                'status': 'paused',
                'metrics': {
                    'eventsProcessed': 2950,
                    'successRate': 0.891,
                    'averageProcessingTime': 3200.8,
                    'currentLoad': 0,
                    'lastActivity': (now - timedelta(hours=2)).isoformat()
                },
                'configuration': {
                    'maxConcurrentTasks': 5,
                    'timeout': 60000,
                    'retryAttempts': 1
                },
                'logs': [
                    {
                        'timestamp': (now - timedelta(hours=2)).isoformat(),
                        'level': 'info',
                        'message': 'Agent paused for maintenance',
                        'metadata': {'reason': 'scheduled_maintenance'}
                    }
                ],
                'lastHeartbeat': (now - timedelta(hours=2)).isoformat()
            }
        }
        
        # Mock Integration Status
        integration_status = {
            'slack_integration': {
                'id': 'slack_integration',
                'name': 'Slack Workspace',
                'status': 'healthy',
                'metrics': {
                    'successRate': 0.996,
                    'responseTime': 125.4,
                    'apiUsage': 847,
                    'rateLimitRemaining': 4500
                },
                'lastSuccessfulConnection': (now - timedelta(minutes=5)).isoformat(),
                'configuration': {
                    'workspace': 'software-factory',
                    'channels': ['#general', '#alerts', '#monitoring'],
                    'webhookUrl': 'https://hooks.slack.com/services/...'
                }
            },
            'github_integration': {
                'id': 'github_integration',
                'name': 'GitHub Repository',
                'status': 'healthy',
                'metrics': {
                    'successRate': 0.989,
                    'responseTime': 234.7,
                    'apiUsage': 1250,
                    'rateLimitRemaining': 4850
                },
                'lastSuccessfulConnection': (now - timedelta(minutes=1)).isoformat(),
                'configuration': {
                    'repository': 'software-factory/main',
                    'branch': 'main',
                    'autoCommit': True
                }
            },
            'ai_service': {
                'id': 'ai_service',
                'name': 'AI Service Provider',
                'status': 'warning',
                'metrics': {
                    'successRate': 0.923,
                    'responseTime': 1850.2,
                    'apiUsage': 2340,
                    'rateLimitRemaining': 1200
                },
                'lastSuccessfulConnection': (now - timedelta(minutes=8)).isoformat(),
                'lastError': 'Rate limit approaching threshold',
                'configuration': {
                    'provider': 'claude',
                    'model': 'sonnet-4',
                    'maxTokens': 4096
                }
            }
        }
        
        # Mock Active Alerts
        active_alerts = [
            {
                'id': 'alert_001',
                'type': 'warning',
                'title': 'High WebSocket Latency',
                'description': 'WebSocket response time is above normal threshold (45.7ms vs 30ms expected)',
                'source': 'websocket_monitor',
                'timestamp': (now - timedelta(minutes=15)).isoformat(),
                'acknowledged': False,
                'resolved': False,
                'metadata': {
                    'component': 'websocket',
                    'threshold': 30,
                    'current_value': 45.7,
                    'severity_score': 3
                }
            },
            {
                'id': 'alert_002',
                'type': 'warning',
                'title': 'AI Service Rate Limit Approaching',
                'description': 'AI service API usage is at 80% of rate limit (1200 remaining of 5000)',
                'source': 'integration_monitor',
                'timestamp': (now - timedelta(minutes=25)).isoformat(),
                'acknowledged': True,
                'acknowledgedBy': 'admin_user',
                'acknowledgedAt': (now - timedelta(minutes=20)).isoformat(),
                'resolved': False,
                'metadata': {
                    'integration': 'ai_service',
                    'usage_percentage': 80,
                    'remaining_calls': 1200
                }
            },
            {
                'id': 'alert_003',
                'type': 'info',
                'title': 'Build Agent Maintenance Mode',
                'description': 'Build Agent has been paused for scheduled maintenance',
                'source': 'agent_monitor',
                'timestamp': (now - timedelta(hours=2)).isoformat(),
                'acknowledged': True,
                'acknowledgedBy': 'system',
                'acknowledgedAt': (now - timedelta(hours=2)).isoformat(),
                'resolved': False,
                'metadata': {
                    'agent': 'build_agent',
                    'maintenance_type': 'scheduled',
                    'estimated_duration': 120
                }
            }
        ]
        
        # Construct the complete dashboard metrics response
        dashboard_metrics = {
            'system_health': system_health,
            'event_metrics': event_metrics,
            'agent_metrics': agent_metrics,
            'integration_status': integration_status,
            'activeAlerts': active_alerts,
            'timestamp': now.isoformat()
        }
        
        return jsonify(dashboard_metrics)
        
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        return jsonify({'error': 'Failed to retrieve dashboard metrics'}), 500


@monitoring_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring system itself."""
    try:
        # Check database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        # Check if monitoring service is running
        monitoring_service = get_monitoring_service()
        service_running = monitoring_service.running
        
        health_status = {
            'status': 'healthy' if service_running else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': 'healthy',
                'monitoring_service': 'healthy' if service_running else 'unhealthy'
            }
        }
        
        status_code = 200 if service_running else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503


# WebSocket event handlers for real-time streaming
def init_monitoring_websocket_handlers(socketio):
    """Initialize WebSocket handlers for monitoring events."""
    
    @socketio.on('monitor.subscribe')
    def handle_monitor_subscribe(data):
        """Handle subscription to monitoring events."""
        try:
            # Join monitoring room for this user
            from flask_socketio import join_room
            join_room('monitoring')
            
            # Send current metrics as initial data
            monitoring_service = get_monitoring_service()
            event_metrics = monitoring_service.collect_event_metrics()
            
            emit('monitor.initial_data', {
                'type': 'initial_metrics',
                'data': {
                    'events_per_minute': event_metrics.events_per_minute,
                    'total_events': event_metrics.total_events,
                    'recent_events': event_metrics.recent_events[-5:]  # Last 5 events
                }
            })
            
            logger.info("Client subscribed to monitoring events")
            
        except Exception as e:
            logger.error(f"Error handling monitor subscription: {e}")
            emit('monitor.error', {'message': 'Failed to subscribe to monitoring'})
    
    @socketio.on('monitor.unsubscribe')
    def handle_monitor_unsubscribe():
        """Handle unsubscription from monitoring events."""
        try:
            from flask_socketio import leave_room
            leave_room('monitoring')
            logger.info("Client unsubscribed from monitoring events")
        except Exception as e:
            logger.error(f"Error handling monitor unsubscription: {e}")


# Initialize monitoring service when blueprint is imported
def init_monitoring_api():
    """Initialize monitoring API and start monitoring service."""
    try:
        monitoring_service = get_monitoring_service()
        logger.info("Monitoring API initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize monitoring API: {e}")
        return False