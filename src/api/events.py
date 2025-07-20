#!/usr/bin/env python3
"""
Events API Blueprint - Event Testing and Management
Provides endpoints for triggering and managing events
"""

from flask import Blueprint, request, jsonify
import logging
import time

try:
    from ..core.events import create_event, EventType, Event
    from ..services.event_bus import publish_event, get_event_bus
except ImportError:
    from core.events import create_event, EventType, Event
    from services.event_bus import publish_event, get_event_bus

logger = logging.getLogger(__name__)

events_bp = Blueprint('events', __name__, url_prefix='/api/events')


@events_bp.route('/trigger', methods=['POST'])
def trigger_event():
    """Trigger a test event"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        event_type_str = data.get('event_type', 'user.action')
        event_data = data.get('data', {})
        user_id = data.get('user_id')
        project_id = data.get('project_id')
        correlation_id = data.get('correlation_id')
        
        # Validate event type
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            return jsonify({'error': f'Invalid event type: {event_type_str}'}), 400
        
        # Create event
        event = create_event(
            event_type,
            source='api_trigger',
            user_id=user_id,
            project_id=project_id,
            correlation_id=correlation_id,
            **event_data
        )
        
        # Publish event
        success = publish_event(event)
        
        if success:
            return jsonify({
                'success': True,
                'event_id': event.event_id,
                'event_type': event.event_type,
                'timestamp': event.timestamp
            })
        else:
            return jsonify({'error': 'Failed to publish event'}), 500
            
    except Exception as e:
        logger.error(f"Error triggering event: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/test/idea', methods=['POST'])
def test_idea_created():
    """Trigger a test 'idea.created' event"""
    try:
        data = request.get_json() or {}
        
        event = create_event(
            EventType.IDEA_CREATED,
            source='api_test',
            idea_title=data.get('title', 'Test Idea'),
            description=data.get('description', 'This is a test idea created via API'),
            created_by=data.get('created_by', 'test_user'),
            tags=data.get('tags', ['test', 'api']),
            priority=data.get('priority', 'medium'),
            business_value=data.get('business_value', 'Testing event system'),
            user_id=data.get('user_id', 'test_user'),
            project_id=data.get('project_id', 'test_project')
        )
        
        success = publish_event(event)
        
        if success:
            return jsonify({
                'success': True,
                'event_id': event.event_id,
                'message': 'Test idea.created event triggered successfully'
            })
        else:
            return jsonify({'error': 'Failed to publish event'}), 500
            
    except Exception as e:
        logger.error(f"Error triggering test idea event: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/test/spec-frozen', methods=['POST'])
def test_spec_frozen():
    """Trigger a test 'spec.frozen' event"""
    try:
        data = request.get_json() or {}
        
        event = create_event(
            EventType.SPEC_FROZEN,
            source='api_test',
            spec_id=data.get('spec_id', 'test_spec_001'),
            version=data.get('version', '1.0.0'),
            frozen_by=data.get('frozen_by', 'test_pm'),
            change_summary=data.get('change_summary', 'Initial specification freeze for testing'),
            approval_required=data.get('approval_required', True),
            user_id=data.get('user_id', 'test_pm'),
            project_id=data.get('project_id', 'test_project')
        )
        
        success = publish_event(event)
        
        if success:
            return jsonify({
                'success': True,
                'event_id': event.event_id,
                'message': 'Test spec.frozen event triggered successfully'
            })
        else:
            return jsonify({'error': 'Failed to publish event'}), 500
            
    except Exception as e:
        logger.error(f"Error triggering test spec frozen event: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/test/tasks-created', methods=['POST'])
def test_tasks_created():
    """Trigger a test 'tasks.created' event"""
    try:
        data = request.get_json() or {}
        
        event = create_event(
            EventType.TASKS_CREATED,
            source='api_test',
            task_count=data.get('task_count', 5),
            created_from=data.get('created_from', 'test_spec_001'),
            assigned_to=data.get('assigned_to', 'test_developer'),
            estimated_effort=data.get('estimated_effort', '2 weeks'),
            due_date=data.get('due_date', '2024-02-01'),
            dependencies=data.get('dependencies', ['setup', 'database']),
            user_id=data.get('user_id', 'test_pm'),
            project_id=data.get('project_id', 'test_project')
        )
        
        success = publish_event(event)
        
        if success:
            return jsonify({
                'success': True,
                'event_id': event.event_id,
                'message': 'Test tasks.created event triggered successfully'
            })
        else:
            return jsonify({'error': 'Failed to publish event'}), 500
            
    except Exception as e:
        logger.error(f"Error triggering test tasks created event: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/test/ai-processing', methods=['POST'])
def test_ai_processing():
    """Trigger a test 'ai.processing.started' event"""
    try:
        data = request.get_json() or {}
        
        event = create_event(
            EventType.AI_PROCESSING_STARTED,
            source='api_test',
            process_type=data.get('process_type', 'code_generation'),
            input_data=data.get('input_data', {'task_id': 'test_task_001', 'language': 'python'}),
            processor=data.get('processor', 'goose_ai'),
            estimated_duration=data.get('estimated_duration', '5 minutes'),
            priority=data.get('priority', 'high'),
            retry_count=data.get('retry_count', 0),
            user_id=data.get('user_id', 'test_developer'),
            project_id=data.get('project_id', 'test_project')
        )
        
        success = publish_event(event)
        
        if success:
            return jsonify({
                'success': True,
                'event_id': event.event_id,
                'message': 'Test ai.processing.started event triggered successfully'
            })
        else:
            return jsonify({'error': 'Failed to publish event'}), 500
            
    except Exception as e:
        logger.error(f"Error triggering test AI processing event: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/stats', methods=['GET'])
def get_event_stats():
    """Get event bus statistics"""
    try:
        event_bus = get_event_bus()
        stats = event_bus.get_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting event stats: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/health', methods=['GET'])
def health_check():
    """Check event system health"""
    try:
        event_bus = get_event_bus()
        healthy = event_bus.health_check()
        
        return jsonify({
            'healthy': healthy,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error checking event health: {e}")
        return jsonify({'error': str(e)}), 500


@events_bp.route('/types', methods=['GET'])
def get_event_types():
    """Get all available event types"""
    try:
        event_types = [event_type.value for event_type in EventType]
        
        return jsonify({
            'success': True,
            'event_types': event_types
        })
        
    except Exception as e:
        logger.error(f"Error getting event types: {e}")
        return jsonify({'error': str(e)}), 500