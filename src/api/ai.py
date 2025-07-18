"""
AI API Blueprint - AI interaction endpoints for unified Flask application
Provides REST endpoints for Goose and Model Garden integrations
"""

import logging
from flask import Blueprint, request, jsonify
try:
    from ..services.ai_service import get_ai_service, AIServiceError
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.ai_service import get_ai_service, AIServiceError

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