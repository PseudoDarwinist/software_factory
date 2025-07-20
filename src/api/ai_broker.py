"""
AI Broker API Blueprint - REST endpoints for AI broker service
Provides intelligent model orchestration and request management
"""

import logging
from flask import Blueprint, request, jsonify
from datetime import datetime

try:
    from ..services.ai_broker import (
        get_ai_broker, AIRequest, TaskType, Priority, 
        ModelCapability, init_ai_broker
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.ai_broker import (
        get_ai_broker, AIRequest, TaskType, Priority,
        ModelCapability, init_ai_broker
    )

logger = logging.getLogger(__name__)

# Create AI broker blueprint
ai_broker_bp = Blueprint('ai_broker', __name__)


@ai_broker_bp.route('/api/ai-broker/submit', methods=['POST'])
def submit_ai_request():
    """Submit an AI request to the broker for processing"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        instruction = data.get('instruction', '')
        if not instruction:
            return jsonify({
                'success': False,
                'error': 'No instruction provided'
            }), 400
        
        # Parse task type
        task_type_str = data.get('task_type', 'general')
        try:
            task_type = TaskType(task_type_str.lower())
        except ValueError:
            task_type = TaskType.GENERAL
        
        # Parse priority
        priority_str = data.get('priority', 'normal')
        try:
            priority = Priority[priority_str.upper()]
        except KeyError:
            priority = Priority.NORMAL
        
        # Create AI request
        broker = get_ai_broker()
        ai_request = broker.create_request(
            instruction=instruction,
            task_type=task_type,
            priority=priority,
            context=data.get('context', {}),
            max_tokens=data.get('max_tokens'),
            timeout_seconds=data.get('timeout_seconds', 300.0),
            preferred_models=data.get('preferred_models', []),
            excluded_models=data.get('excluded_models', []),
            metadata=data.get('metadata', {})
        )
        
        # Submit request
        request_id = broker.submit_request(ai_request)
        
        logger.info(f"Submitted AI broker request {request_id} for task type {task_type.value}")
        
        return jsonify({
            'success': True,
            'request_id': request_id,
            'task_type': task_type.value,
            'priority': priority.name,
            'estimated_wait_time': broker.request_queue.queue.qsize() * 10  # Rough estimate
        })
        
    except Exception as e:
        logger.error(f"Failed to submit AI broker request: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/submit-sync', methods=['POST'])
def submit_ai_request_sync():
    """Submit an AI request and wait for response synchronously"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        instruction = data.get('instruction', '')
        if not instruction:
            return jsonify({
                'success': False,
                'error': 'No instruction provided'
            }), 400
        
        # Parse parameters
        task_type_str = data.get('task_type', 'general')
        try:
            task_type = TaskType(task_type_str.lower())
        except ValueError:
            task_type = TaskType.GENERAL
        
        priority_str = data.get('priority', 'normal')
        try:
            priority = Priority[priority_str.upper()]
        except KeyError:
            priority = Priority.NORMAL
        
        timeout = data.get('timeout_seconds', 300.0)
        
        # Create and submit request synchronously
        broker = get_ai_broker()
        ai_request = broker.create_request(
            instruction=instruction,
            task_type=task_type,
            priority=priority,
            context=data.get('context', {}),
            max_tokens=data.get('max_tokens'),
            timeout_seconds=timeout,
            preferred_models=data.get('preferred_models', []),
            excluded_models=data.get('excluded_models', []),
            metadata=data.get('metadata', {})
        )
        
        # Submit and wait for response
        response = broker.submit_request_sync(ai_request, timeout)
        
        logger.info(f"Completed synchronous AI broker request {response.request_id} "
                   f"using {response.model_used} in {response.processing_time:.2f}s")
        
        return jsonify({
            'success': response.success,
            'request_id': response.request_id,
            'content': response.content,
            'model_used': response.model_used,
            'provider': response.provider,
            'processing_time': response.processing_time,
            'tokens_used': response.tokens_used,
            'cost_estimate': response.cost_estimate,
            'quality_score': response.quality_score,
            'error_message': response.error_message,
            'completed_at': response.completed_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to process synchronous AI broker request: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/status/<request_id>', methods=['GET'])
def get_request_status(request_id: str):
    """Get status of a specific AI request"""
    try:
        broker = get_ai_broker()
        status = broker.get_request_status(request_id)
        
        if status is None:
            return jsonify({
                'success': False,
                'error': 'Request not found'
            }), 404
        
        return jsonify({
            'success': True,
            'request_id': request_id,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Failed to get request status for {request_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/response/<request_id>', methods=['GET'])
def get_request_response(request_id: str):
    """Get response for a completed AI request"""
    try:
        broker = get_ai_broker()
        
        if request_id not in broker.completed_requests:
            return jsonify({
                'success': False,
                'error': 'Request not found or not completed'
            }), 404
        
        response = broker.completed_requests[request_id]
        
        return jsonify({
            'success': True,
            'request_id': request_id,
            'response': {
                'success': response.success,
                'content': response.content,
                'model_used': response.model_used,
                'provider': response.provider,
                'processing_time': response.processing_time,
                'tokens_used': response.tokens_used,
                'cost_estimate': response.cost_estimate,
                'quality_score': response.quality_score,
                'error_message': response.error_message,
                'completed_at': response.completed_at.isoformat(),
                'metadata': response.metadata
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get response for {request_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/status', methods=['GET'])
def get_broker_status():
    """Get comprehensive AI broker status"""
    try:
        broker = get_ai_broker()
        status = broker.get_broker_status()
        
        return jsonify({
            'success': True,
            'broker_status': status
        })
        
    except Exception as e:
        logger.error(f"Failed to get broker status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/models', methods=['GET'])
def get_available_models():
    """Get information about available AI models"""
    try:
        broker = get_ai_broker()
        model_status = broker.model_selector.get_model_status()
        
        return jsonify({
            'success': True,
            'models': model_status,
            'capabilities': [cap.value for cap in ModelCapability],
            'task_types': [task.value for task in TaskType],
            'priorities': [priority.name.lower() for priority in Priority]
        })
        
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/queue', methods=['GET'])
def get_queue_status():
    """Get current request queue status"""
    try:
        broker = get_ai_broker()
        queue_status = broker.request_queue.get_queue_status()
        
        return jsonify({
            'success': True,
            'queue_status': queue_status
        })
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/test', methods=['POST'])
def test_ai_broker():
    """Test the AI broker with different models and task types"""
    try:
        data = request.get_json() or {}
        
        # Test parameters
        test_instruction = data.get('instruction', 
            'Hello! Please confirm you are working properly and explain your capabilities.')
        task_types_to_test = data.get('task_types', ['general', 'conversation'])
        models_to_test = data.get('models', [])
        
        broker = get_ai_broker()
        test_results = []
        
        for task_type_str in task_types_to_test:
            try:
                task_type = TaskType(task_type_str.lower())
            except ValueError:
                continue
            
            # Create test request
            test_request = broker.create_request(
                instruction=test_instruction,
                task_type=task_type,
                priority=Priority.HIGH,  # High priority for tests
                preferred_models=models_to_test if models_to_test else None,
                metadata={'test': True, 'role': 'developer'}
            )
            
            # Submit synchronously with shorter timeout
            response = broker.submit_request_sync(test_request, timeout=60.0)
            
            test_results.append({
                'task_type': task_type.value,
                'request_id': response.request_id,
                'success': response.success,
                'model_used': response.model_used,
                'provider': response.provider,
                'processing_time': response.processing_time,
                'tokens_used': response.tokens_used,
                'cost_estimate': response.cost_estimate,
                'response_length': len(response.content),
                'error_message': response.error_message
            })
        
        # Calculate summary statistics
        successful_tests = sum(1 for result in test_results if result['success'])
        total_tests = len(test_results)
        avg_response_time = sum(result['processing_time'] for result in test_results) / total_tests if total_tests > 0 else 0
        
        return jsonify({
            'success': True,
            'test_summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': successful_tests / total_tests if total_tests > 0 else 0,
                'avg_response_time': avg_response_time
            },
            'test_results': test_results,
            'test_instruction': test_instruction
        })
        
    except Exception as e:
        logger.error(f"AI broker test failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/start', methods=['POST'])
def start_broker():
    """Start the AI broker service"""
    try:
        broker = get_ai_broker()
        broker.start()
        
        return jsonify({
            'success': True,
            'message': 'AI broker service started'
        })
        
    except Exception as e:
        logger.error(f"Failed to start AI broker: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/stop', methods=['POST'])
def stop_broker():
    """Stop the AI broker service"""
    try:
        broker = get_ai_broker()
        broker.stop()
        
        return jsonify({
            'success': True,
            'message': 'AI broker service stopped'
        })
        
    except Exception as e:
        logger.error(f"Failed to stop AI broker: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_broker_bp.route('/api/ai-broker/statistics', methods=['GET'])
def get_broker_statistics():
    """Get detailed broker statistics and performance metrics"""
    try:
        broker = get_ai_broker()
        
        # Get basic statistics
        stats = broker.stats.copy()
        
        # Add model-specific statistics
        model_stats = {}
        for model_id, config in broker.model_selector.model_configs.items():
            model_stats[model_id] = {
                'total_requests': config.total_requests,
                'success_rate': config.success_rate,
                'avg_response_time': config.avg_response_time,
                'avg_quality_score': config.avg_quality_score,
                'current_load': config.current_load,
                'max_concurrent': config.max_concurrent_requests
            }
        
        # Calculate additional metrics
        if stats['total_requests'] > 0:
            stats['success_rate'] = stats['successful_requests'] / stats['total_requests']
            stats['failure_rate'] = stats['failed_requests'] / stats['total_requests']
            stats['avg_cost_per_request'] = stats['total_cost'] / stats['total_requests']
            stats['avg_tokens_per_request'] = stats['total_tokens_used'] / stats['total_requests']
        else:
            stats['success_rate'] = 0
            stats['failure_rate'] = 0
            stats['avg_cost_per_request'] = 0
            stats['avg_tokens_per_request'] = 0
        
        # Add uptime
        if stats['started_at']:
            uptime_seconds = (datetime.utcnow() - stats['started_at']).total_seconds()
            stats['uptime_seconds'] = uptime_seconds
            stats['requests_per_minute'] = (stats['total_requests'] / uptime_seconds * 60) if uptime_seconds > 0 else 0
        
        return jsonify({
            'success': True,
            'statistics': {
                'broker_stats': stats,
                'model_stats': model_stats,
                'queue_stats': broker.request_queue.get_queue_status()
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get broker statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Legacy compatibility endpoints
@ai_broker_bp.route('/api/ai/broker/submit', methods=['POST'])
def legacy_submit_request():
    """Legacy endpoint for backward compatibility"""
    return submit_ai_request()


@ai_broker_bp.route('/api/ai/broker/status', methods=['GET'])
def legacy_broker_status():
    """Legacy broker status endpoint"""
    return get_broker_status()


# Note: AI broker initialization is handled by the main Flask app
# Don't initialize here to avoid conflicts with app startup