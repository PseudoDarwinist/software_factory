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


@ai_bp.route('/api/goose/execute', methods=['POST'])
def goose_execute():
    """Simple Goose execution endpoint for frontend compatibility"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        instruction = data.get('instruction', data.get('prompt', ''))
        role = data.get('role', 'po')
        if not instruction:
            return jsonify({
                'success': False,
                'error': 'No instruction or prompt provided'
            }), 400

        # Get AI service
        ai_service = get_ai_service()
        if not ai_service:
            return jsonify({
                'success': False,
                'error': 'AI service not available'
            }), 500

        # Execute with Goose/Gemini - return in PO interface format
        try:
            response = ai_service.execute_goose_task(instruction, role=role)
            # Check if response indicates failure
            if isinstance(response, dict) and response.get('success') == False:
                raise Exception(f"Goose failed: {response.get('error', 'Unknown error')}")
            
            # Extract actual response content from the response dict
            if isinstance(response, dict) and 'output' in response:
                response_content = response['output']
            elif isinstance(response, dict) and 'response' in response:
                response_content = response['response']
            else:
                response_content = str(response)
            
            # Return in the format PO interface expects
            return jsonify({
                'success': True,
                'output': response_content,
                'provider': 'goose',
                'model': 'gemini-2.5-flash'
            })
        except Exception as e:
            logger.error(f"Goose execution failed: {e}")
            
            # Since Goose isn't configured, let's also call Model Garden directly as fallback
            try:
                import requests
                import json
                
                model_garden_url = 'https://quasarmarket.coforge.com/aistudio-llmrouter-api/api/v2/chat/completions'
                api_key = '4b7103fd-77b1-4db6-9ab7-a88e92a0e835'
                
                payload = {
                    "model": "claude-opus-4",
                    "messages": [
                        {
                            "role": "user", 
                            "content": instruction
                        }
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.7
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
                
                resp = requests.post(model_garden_url, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                
                result = resp.json()
                
                if 'choices' in result and len(result['choices']) > 0:
                    ai_response = result['choices'][0]['message']['content']
                    
                    return jsonify({
                        'success': True,
                        'output': ai_response,
                        'provider': 'goose-fallback',
                        'model': 'claude-opus-4'
                    })
                else:
                    raise Exception("No response from fallback API")
                    
            except Exception as direct_api_error:
                logger.error(f"Goose fallback API call failed: {direct_api_error}")
                return jsonify({
                    'success': False,
                    'error': f'Both Goose and fallback API failed: {str(direct_api_error)}'
                }), 500

    except Exception as e:
        logger.error(f"Goose execute endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@ai_bp.route('/api/model-garden/execute', methods=['POST'])
def model_garden_execute():
    """Model Garden execution endpoint for frontend compatibility - Direct API calls only"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        prompt = data.get('prompt', data.get('instruction', ''))
        model = data.get('model', 'claude-opus-4')
        role = data.get('role', 'user')
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'No prompt or instruction provided'
            }), 400

        # Call the actual Model Garden API directly for speed
        try:
            import requests
            import json
            
            model_garden_url = 'https://quasarmarket.coforge.com/aistudio-llmrouter-api/api/v2/chat/completions'
            api_key = '4b7103fd-77b1-4db6-9ab7-a88e92a0e835'
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.7
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            logger.info(f"Making direct Model Garden API call with model: {model}")
            resp = requests.post(model_garden_url, headers=headers, json=payload, timeout=45)
            resp.raise_for_status()
            
            result = resp.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                ai_response = result['choices'][0]['message']['content']
                
                logger.info(f"Model Garden API successful, response length: {len(ai_response)}")
                return jsonify({
                    'success': True,
                    'output': ai_response,
                    'provider': 'model-garden-direct',
                    'model': model,
                    'role': role
                })
            else:
                raise Exception("No response from Model Garden")
                
        except Exception as direct_api_error:
            logger.error(f"Direct Model Garden API call failed: {direct_api_error}")
            return jsonify({
                'success': False,
                'error': f'Model Garden API failed: {str(direct_api_error)}'
            }), 500

    except Exception as e:
        logger.error(f"Model Garden execute endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


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


# Legacy endpoint compatibility removed - using main goose_execute function


@ai_bp.route('/api/goose/status', methods=['GET'])
def goose_status():
    """Get Goose AI status for frontend"""
    try:
        ai_service = get_ai_service()
        if not ai_service:
            return jsonify({
                'success': False,
                'available': False,
                'error': 'AI service not available',
                'status': 'error'
            }), 500
        
        status = ai_service.get_service_status()
        goose_status = status.get('goose', {})
        
        return jsonify({
            'success': True,
            'available': goose_status.get('available', False),
            'script_path': goose_status.get('script_path', '/Users/chetansingh/bin/goose'),
            'project_path': goose_status.get('project_path', ''),
            'model': goose_status.get('model', 'claude-code'),
            'provider': goose_status.get('provider', 'claude'),
            'roles_supported': goose_status.get('roles_supported', ['po', 'business']),
            'status': 'ready' if goose_status.get('available') else 'unavailable',
            'goose_available': goose_status.get('available', False),  # Legacy compatibility
            'goose_script': goose_status.get('script_path', '/Users/chetansingh/bin/goose'),  # Legacy compatibility
            'ai_model': goose_status.get('model', 'claude-code')  # Legacy compatibility
        })
        
    except Exception as e:
        logger.error(f"Error getting Goose status: {e}")
        return jsonify({
            'success': False,
            'available': False,
            'error': str(e),
            'status': 'error',
            'goose_available': False  # Legacy compatibility
        }), 500


@ai_bp.route('/api/goose/test', methods=['POST'])
def legacy_goose_test():
    """Legacy Goose test endpoint for backward compatibility"""
    return test_goose_only()


@ai_bp.route('/api/model-garden/execute', methods=['POST'])
def legacy_model_garden_execute():
    """Legacy Model Garden endpoint for backward compatibility"""
    return execute_model_garden_task()


@ai_bp.route('/api/ai/assistant', methods=['POST'])
def ai_assistant():
    """Kiro-style context-aware AI assistant for specification help"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        query = data.get('query', '')
        context = data.get('context', {})
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'No query provided'
            }), 400
        
        # Extract context information
        spec_id = context.get('spec_id')
        artifact_type = context.get('artifact_type', 'requirements')
        current_content = context.get('current_content', '')
        
        # Use Goose directly for assistant responses (Model Garden is down)
        ai_service = get_ai_service()
        
        # Use the same enhanced Kiro-style prompt from define_agent.py
        assistant_query = f"""You are a senior product manager and business analyst with full filesystem access to analyze this repository.

CURRENT {artifact_type.upper()} CONTENT:
{current_content}

USER REQUEST:
{query}

INSTRUCTIONS:
1. **ANALYZE THE REPOSITORY FIRST**: Use your filesystem access to examine:
   - Project structure and organization patterns
   - Existing similar features and their implementation
   - Technology stack (package.json, requirements.txt, etc.)
   - Database schemas and models
   - API patterns and routing structures

2. **PROVIDE REPOSITORY-AWARE ADVICE**: Give specific suggestions that:
   - Reference actual files, classes, and patterns from the codebase
   - Follow established architectural patterns
   - Integrate with existing APIs and data models
   - Use the same technology stack and conventions

Provide actionable advice for improving this {artifact_type} specification based on your repository analysis."""
        
        # Use Goose directly without extra context to avoid timeouts
        result = ai_service.goose.execute_task(
            instruction=assistant_query,
            business_context={
                'domain': 'Software Development Lifecycle Platform',
                'useCase': f'Improve {artifact_type} specification'
            },
            github_repo={
                'connected': True,
                'name': 'Software Factory',
                'branch': 'main',
                'private': True
            }
        )
        
        if result.get('success') and result.get('output'):
            return jsonify({
                'success': True,
                'data': {
                    'response': result['output']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f"AI assistant failed: {result.get('error', 'Unknown error')}"
            }), 500
        
    except Exception as e:
        logger.error(f"Error in AI assistant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500