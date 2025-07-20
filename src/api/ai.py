"""
AI API Blueprint - Context-Aware AI interaction endpoints
Provides intelligent AI responses with graph relationships, vector search, and predictive insights
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any
try:
    from ..services.ai_service import get_ai_service, AIServiceError
    from ..services.context_aware_ai import get_context_aware_ai, AIContext
    from ..services.ai_agents import get_ai_agent_manager
    from ..services.distributed_cache import get_distributed_cache
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.ai_service import get_ai_service, AIServiceError
    from services.context_aware_ai import get_context_aware_ai, AIContext
    from services.ai_agents import get_ai_agent_manager
    from services.distributed_cache import get_distributed_cache

logger = logging.getLogger(__name__)

# Create AI blueprint
ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/api/ai/goose/execute', methods=['POST'])
def execute_goose_task():
    """Execute AI task using Goose + Gemini with business context and GitHub repository"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        instruction = data.get('instruction', '')
        business_context = data.get('businessContext', {})
        github_repo = data.get('githubRepo', None)
        role = data.get('role', 'business')
        
        if not instruction:
            return jsonify({
                'success': False,
                'error': 'No instruction provided'
            }), 400
        
        # Get AI service and execute task
        ai_service = get_ai_service()
        result = ai_service.execute_goose_task(instruction, business_context, github_repo, role)
        
        logger.info(f"Goose task executed for role: {role}, success: {result['success']}")
        
        return jsonify(result)
        
    except AIServiceError as e:
        logger.error(f"AI service error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'output': ''
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in Goose execution: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'output': ''
        }), 500


@ai_bp.route('/api/ai/model-garden/execute', methods=['POST'])
def execute_model_garden_task():
    """Execute AI task using Model Garden (enterprise LLMs)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        instruction = data.get('instruction', '')
        product_context = data.get('productContext', {})
        model = data.get('model', 'claude-opus-4')
        role = data.get('role', 'po')
        
        if not instruction:
            return jsonify({
                'success': False,
                'error': 'No instruction provided'
            }), 400
        
        # Get AI service and execute task
        ai_service = get_ai_service()
        result = ai_service.execute_model_garden_task(instruction, product_context, model, role)
        
        logger.info(f"Model Garden task executed with model: {model}, role: {role}, success: {result['success']}")
        
        return jsonify(result)
        
    except AIServiceError as e:
        logger.error(f"AI service error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'output': ''
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in Model Garden execution: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'output': ''
        }), 500


@ai_bp.route('/api/ai/contextual', methods=['POST'])
def contextual_ai_chat():
    """Enhanced AI chat with full contextual awareness"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        user_query = data.get('query', '')
        project_id = data.get('project_id')
        conversation_id = data.get('conversation_id')
        
        if not user_query:
            return jsonify({
                'success': False,
                'error': 'No query provided'
            }), 400
        
        # Create AI context
        context_ai = get_context_aware_ai()
        ai_context = context_ai.create_context(
            user_query=user_query,
            project_id=project_id,
            conversation_id=conversation_id,
            max_context_tokens=data.get('max_context_tokens', 4000),
            include_graph_data=data.get('include_graph_data', True),
            include_vector_search=data.get('include_vector_search', True),
            include_recommendations=data.get('include_recommendations', True)
        )
        
        # Generate contextual response
        response = context_ai.generate_contextual_response(ai_context)
        
        logger.info(f"Contextual AI response generated for project {project_id}")
        
        return jsonify({
            'success': True,
            'response': response['response'],
            'context_summary': response.get('context_summary'),
            'context_tokens': response.get('context_tokens'),
            'task_type': response.get('task_type'),
            'generated_at': response.get('generated_at'),
            'project_id': project_id,
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        logger.error(f"Error in contextual AI chat: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/api/ai/agents/alerts', methods=['GET'])
def get_ai_agent_alerts():
    """Get recent alerts from AI agents"""
    try:
        project_id = request.args.get('project_id', type=int)
        hours = request.args.get('hours', default=24, type=int)
        
        agent_manager = get_ai_agent_manager()
        alerts = agent_manager.get_recent_alerts(project_id=project_id, hours=hours)
        
        # Convert alerts to dict format
        alert_data = []
        for alert in alerts:
            alert_data.append({
                'agent_type': alert.agent_type.value,
                'alert_level': alert.alert_level.value,
                'title': alert.title,
                'description': alert.description,
                'project_id': alert.project_id,
                'recommendations': alert.recommendations,
                'metadata': alert.metadata,
                'created_at': alert.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'alerts': alert_data,
            'total_alerts': len(alert_data),
            'project_id': project_id,
            'hours': hours
        })
        
    except Exception as e:
        logger.error(f"Error getting AI agent alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/api/ai/agents/status', methods=['GET'])
def get_ai_agents_status():
    """Get status of AI agents"""
    try:
        agent_manager = get_ai_agent_manager()
        
        agent_status = {}
        for agent_type, agent in agent_manager.agents.items():
            agent_status[agent_type.value] = {
                'is_active': agent.is_active,
                'agent_type': agent_type.value,
                'last_check': 'unknown'  # Could add last activity tracking
            }
        
        return jsonify({
            'success': True,
            'agents': agent_status,
            'total_agents': len(agent_status),
            'active_agents': sum(1 for status in agent_status.values() if status['is_active'])
        })
        
    except Exception as e:
        logger.error(f"Error getting AI agents status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/api/ai/context/preview', methods=['POST'])
def preview_ai_context():
    """Preview the context that would be provided to AI without generating a response"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        user_query = data.get('query', '')
        project_id = data.get('project_id')
        conversation_id = data.get('conversation_id')
        
        if not user_query:
            return jsonify({
                'success': False,
                'error': 'No query provided'
            }), 400
        
        # Create and enrich context
        context_ai = get_context_aware_ai()
        ai_context = context_ai.create_context(
            user_query=user_query,
            project_id=project_id,
            conversation_id=conversation_id,
            max_context_tokens=data.get('max_context_tokens', 4000),
            include_graph_data=data.get('include_graph_data', True),
            include_vector_search=data.get('include_vector_search', True),
            include_recommendations=data.get('include_recommendations', True)
        )
        
        enriched_context = context_ai.enrich_context(ai_context)
        
        return jsonify({
            'success': True,
            'context_summary': enriched_context.context_summary,
            'total_tokens': enriched_context.total_tokens,
            'project_context': enriched_context.project_context,
            'graph_context': enriched_context.graph_context,
            'vector_context': enriched_context.vector_context,
            'conversation_context': enriched_context.conversation_context,
            'recommendation_context': enriched_context.recommendation_context,
            'technology_context': enriched_context.technology_context
        })
        
    except Exception as e:
        logger.error(f"Error previewing AI context: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/api/ai/cache/clear', methods=['POST'])
def clear_ai_cache():
    """Clear AI-related cache entries"""
    try:
        data = request.get_json() or {}
        cache = get_distributed_cache()
        
        if 'project_id' in data:
            # Clear project-specific AI cache
            project_id = data['project_id']
            patterns = [
                f'enriched_context_{project_id}_*',
                f'ai_response_{project_id}_*'
            ]
            
            total_cleared = 0
            for pattern in patterns:
                cleared = cache.invalidate_pattern(pattern, namespace='ai_context')
                total_cleared += cleared
            
            return jsonify({
                'success': True,
                'cleared_entries': total_cleared,
                'project_id': project_id
            })
        
        else:
            # Clear all AI cache
            cleared = cache.clear_namespace('ai_context')
            
            return jsonify({
                'success': True,
                'cleared_entries': cleared,
                'scope': 'all_ai_cache'
            })
            
    except Exception as e:
        logger.error(f"Error clearing AI cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/api/ai/health', methods=['GET'])
def ai_system_health():
    """Check AI system health and capabilities"""
    try:
        # Test basic AI service
        ai_service = get_ai_service()
        
        # Test context-aware AI
        context_ai = get_context_aware_ai()
        
        # Test AI agents
        agent_manager = get_ai_agent_manager()
        
        # Test cache
        cache = get_distributed_cache()
        
        health_status = {
            'ai_service_available': ai_service is not None,
            'context_ai_available': context_ai is not None,
            'agent_manager_available': agent_manager is not None,
            'cache_available': cache is not None,
            'active_agents': len(agent_manager.agents) if agent_manager else 0
        }
        
        # Test basic functionality
        try:
            test_context = context_ai.create_context("test query", project_id=None)
            health_status['context_creation_working'] = test_context is not None
        except:
            health_status['context_creation_working'] = False
        
        is_healthy = all([
            health_status['ai_service_available'],
            health_status['context_ai_available'],
            health_status['agent_manager_available'],
            health_status['cache_available']
        ])
        
        return jsonify({
            'success': True,
            'healthy': is_healthy,
            'status': health_status,
            'components': {
                'ai_service': 'operational' if health_status['ai_service_available'] else 'unavailable',
                'context_ai': 'operational' if health_status['context_ai_available'] else 'unavailable',
                'ai_agents': f"{health_status['active_agents']} active" if health_status['agent_manager_available'] else 'unavailable',
                'cache': 'operational' if health_status['cache_available'] else 'unavailable'
            }
        }), 200 if is_healthy else 503
        
    except Exception as e:
        logger.error(f"AI system health check failed: {e}")
        return jsonify({
            'success': False,
            'healthy': False,
            'error': str(e)
        }), 503


@ai_bp.route('/api/ai/status', methods=['GET'])
def get_ai_status():
    """Get status of all AI services"""
    try:
        ai_service = get_ai_service()
        status = ai_service.get_service_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get AI service status'
        }), 500


@ai_bp.route('/api/ai/models', methods=['GET'])
def list_available_models():
    """Get list of available AI models"""
    try:
        ai_service = get_ai_service()
        
        # Get Model Garden models
        models = ai_service.model_garden.get_available_models()
        
        # Add Goose model info
        goose_info = {
            'gemini-2.5-flash': 'Gemini 2.5 Flash (via Goose)'
        }
        
        return jsonify({
            'success': True,
            'models': {
                'model_garden': models,
                'goose': goose_info
            },
            'providers': ['goose', 'model_garden']
        })
        
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get available models'
        }), 500


@ai_bp.route('/api/ai/test', methods=['POST'])
def test_ai_integrations():
    """Test all AI integrations"""
    try:
        ai_service = get_ai_service()
        test_results = ai_service.test_integrations()
        
        return jsonify({
            'success': True,
            'test_results': test_results
        })
        
    except Exception as e:
        logger.error(f"Error testing AI integrations: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to test AI integrations'
        }), 500


@ai_bp.route('/api/ai/goose/test', methods=['POST'])
def test_goose_only():
    """Test Goose integration specifically"""
    try:
        ai_service = get_ai_service()
        
        test_instruction = "Hello! Please confirm you're working properly by explaining what you can help with in software development."
        result = ai_service.execute_goose_task(test_instruction)
        
        return jsonify({
            'success': result['success'],
            'test_instruction': test_instruction,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error testing Goose integration: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Legacy endpoint compatibility (from old backend)
@ai_bp.route('/api/goose/execute', methods=['POST'])
def legacy_goose_execute():
    """Legacy endpoint for backward compatibility"""
    return execute_goose_task()


@ai_bp.route('/api/goose/status', methods=['GET'])
def legacy_goose_status():
    """Legacy Goose status endpoint for backward compatibility"""
    try:
        ai_service = get_ai_service()
        status = ai_service.get_service_status()
        goose_status = status['goose']
        
        return jsonify({
            'goose_available': goose_status['available'],
            'goose_script': goose_status['script_path'],
            'project_path': goose_status['project_path'],
            'ai_model': goose_status['model'],
            'provider': goose_status['provider'],
            'roles_supported': goose_status['roles_supported']
        })
        
    except Exception as e:
        logger.error(f"Error getting legacy Goose status: {e}")
        return jsonify({
            'goose_available': False,
            'error': str(e)
        }), 500


@ai_bp.route('/api/goose/test', methods=['POST'])
def legacy_goose_test():
    """Legacy Goose test endpoint for backward compatibility"""
    return test_goose_only()


@ai_bp.route('/api/model-garden/execute', methods=['POST'])
def legacy_model_garden_execute():
    """Legacy Model Garden endpoint for backward compatibility"""
    return execute_model_garden_task()