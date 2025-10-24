"""
Reliable PRD Generator API Integration
Replaces existing inconsistent generation with Nautex-inspired approach
"""

import logging
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Create blueprint for reliable PRD generation
reliable_prd_bp = Blueprint('reliable_prd', __name__, url_prefix='/api/reliable-prd')


@reliable_prd_bp.route('/generate', methods=['POST'])
def generate_reliable_prd():
    """
    Generate a reliable, consistently-formatted PRD
    Replaces the inconsistent generation in prd_editor.py
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        # Extract parameters
        conversation_state = data.get('conversation_state', {})
        conversation_history = conversation_state.get('history', [])
        project_context = data.get('project_context', {})
        
        if not conversation_history:
            return jsonify({
                'success': False,
                'error': 'Conversation history is required'
            }), 400
        
        # Build conversation context
        user_responses = []
        for entry in conversation_history:
            if entry['role'] == 'user':
                user_responses.append(entry['message'])
        
        conversation_context = "\n".join([
            f"User Response {i+1}: {response}" 
            for i, response in enumerate(user_responses)
        ])
        
        # Use Nautex-inspired generator
        try:
            from ..services.nautex_inspired_generator import generate_reliable_prd
            from ..services.ai_service import get_ai_service
            
            ai_service = get_ai_service()
            if not ai_service:
                return jsonify({
                    'success': False,
                    'error': 'AI service not available'
                }), 503
            
            # Generate PRD using reliable method
            result = generate_reliable_prd(
                conversation_context=conversation_context,
                ai_service=ai_service,
                project_context=project_context
            )
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': {
                        'blocks': result['blocks'],
                        'structured_data': result['structured_data'],
                        'generation_metadata': result['metadata'],
                        'message': 'PRD generated successfully using reliable method'
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result['error'],
                    'metadata': result['metadata']
                }), 422
                
        except ImportError as e:
            logger.error(f"Could not import nautex_inspired_generator: {e}")
            return jsonify({
                'success': False,
                'error': 'Reliable generator not available'
            }), 503
        except Exception as e:
            logger.error(f"Reliable generation failed: {e}")
            return jsonify({
                'success': False,
                'error': f'Generation failed: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in reliable PRD generation endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Request processing failed'
        }), 500


@reliable_prd_bp.route('/validate', methods=['POST'])
def validate_prd_structure():
    """
    Validate PRD structure against schema
    Useful for debugging generation issues
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        prd_data = data.get('prd_data')
        if not prd_data:
            return jsonify({
                'success': False,
                'error': 'PRD data is required'
            }), 400
        
        try:
            from ..services.nautex_inspired_generator import StructuredPRD
            
            # Validate against schema
            structured_prd = StructuredPRD(**prd_data)
            
            return jsonify({
                'success': True,
                'data': {
                    'valid': True,
                    'validation_details': {
                        'user_personas_count': len(structured_prd.user_personas),
                        'user_stories_count': len(structured_prd.user_stories),
                        'functional_requirements_count': len(structured_prd.functional_requirements),
                        'diagrams_count': len(structured_prd.diagrams),
                        'implementation_phases_count': len(structured_prd.implementation_phases)
                    }
                }
            })
            
        except Exception as validation_error:
            return jsonify({
                'success': True,
                'data': {
                    'valid': False,
                    'validation_error': str(validation_error)
                }
            })
            
    except Exception as e:
        logger.error(f"Validation endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': 'Validation processing failed'
        }), 500


@reliable_prd_bp.route('/test', methods=['POST'])
def test_reliable_generation():
    """
    Test endpoint for reliable generation with sample data
    """
    try:
        # Sample conversation for testing
        test_conversation = """
User Response 1: I want to build a task management application
User Response 2: It should help teams collaborate on projects
User Response 3: Users should be able to create tasks, assign them, and track progress
User Response 4: We need real-time updates and notifications
User Response 5: The app should work on web and mobile
        """
        
        try:
            from ..services.nautex_inspired_generator import generate_reliable_prd
            from ..services.ai_service import get_ai_service
            
            ai_service = get_ai_service()
            if not ai_service:
                return jsonify({
                    'success': False,
                    'error': 'AI service not available for testing'
                }), 503
            
            result = generate_reliable_prd(
                conversation_context=test_conversation,
                ai_service=ai_service,
                project_context={'test_mode': True}
            )
            
            return jsonify({
                'success': True,
                'test_result': result,
                'message': 'Test completed - check result for generation quality'
            })
            
        except Exception as test_error:
            logger.error(f"Test generation failed: {test_error}")
            return jsonify({
                'success': False,
                'error': f'Test failed: {str(test_error)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': 'Test processing failed'
        }), 500


@reliable_prd_bp.route('/compare', methods=['POST'])
def compare_generation_methods():
    """
    Compare old vs new generation methods
    Useful for validation and improvement
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        conversation_context = data.get('conversation_context', '')
        if not conversation_context:
            return jsonify({
                'success': False,
                'error': 'Conversation context required'
            }), 400
        
        try:
            from ..services.nautex_inspired_generator import generate_reliable_prd
            from ..services.ai_service import get_ai_service
            
            ai_service = get_ai_service()
            if not ai_service:
                return jsonify({
                    'success': False,
                    'error': 'AI service not available'
                }), 503
            
            # Generate with new method
            reliable_result = generate_reliable_prd(
                conversation_context=conversation_context,
                ai_service=ai_service
            )
            
            # Try old method for comparison (import existing function)
            old_result = {'success': False, 'error': 'Old method comparison not implemented'}
            try:
                # This would call your existing generation method
                # old_result = your_existing_generation_function(conversation_context)
                pass
            except Exception as old_error:
                old_result = {'success': False, 'error': str(old_error)}
            
            return jsonify({
                'success': True,
                'comparison': {
                    'reliable_method': {
                        'success': reliable_result['success'],
                        'blocks_count': len(reliable_result.get('blocks', [])),
                        'has_structured_data': 'structured_data' in reliable_result,
                        'metadata': reliable_result.get('metadata', {})
                    },
                    'old_method': {
                        'success': old_result['success'],
                        'error': old_result.get('error'),
                        'note': 'Old method integration pending'
                    }
                },
                'recommendation': 'Use reliable method for consistent results'
            })
            
        except Exception as compare_error:
            logger.error(f"Comparison failed: {compare_error}")
            return jsonify({
                'success': False,
                'error': f'Comparison failed: {str(compare_error)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Compare endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': 'Comparison processing failed'
        }), 500