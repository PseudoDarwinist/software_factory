"""
Coding Assistants API - BYOA (Bring Your Own Assistant) endpoints
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

try:
    from ..services.coding_assistants import (
        get_coding_assistant_registry, 
        AssistantCapability, 
        AssistantRequest,
        initialize_default_assistants
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.coding_assistants import (
        get_coding_assistant_registry,
        AssistantCapability,
        AssistantRequest,
        initialize_default_assistants
    )

logger = logging.getLogger(__name__)

# Create coding assistants blueprint
coding_assistants_bp = Blueprint('coding_assistants', __name__)

# Initialize assistants on module load
try:
    initialize_default_assistants()
    logger.info("Default coding assistants initialized")
except Exception as e:
    logger.error(f"Failed to initialize default assistants: {e}")


@coding_assistants_bp.route('/api/assistants', methods=['GET'])
def list_assistants():
    """List all available coding assistants"""
    try:
        registry = get_coding_assistant_registry()
        status = registry.get_registry_status()
        
        return jsonify({
            'success': True,
            'assistants': status['assistants'],
            'total_assistants': status['total_assistants'],
            'available_assistants': status['available_assistants'],
            'default_assistant': status['default_assistant'],
            'capability_routing': status['capability_routing']
        })
        
    except Exception as e:
        logger.error(f"Error listing assistants: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@coding_assistants_bp.route('/api/assistants/capabilities', methods=['GET'])
def list_capabilities():
    """List all available capabilities"""
    try:
        capabilities = [
            {
                'name': cap.value,
                'display_name': cap.value.replace('_', ' ').title(),
                'description': _get_capability_description(cap)
            }
            for cap in AssistantCapability
        ]
        
        return jsonify({
            'success': True,
            'capabilities': capabilities
        })
        
    except Exception as e:
        logger.error(f"Error listing capabilities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@coding_assistants_bp.route('/api/assistants/execute', methods=['POST'])
def execute_assistant_request():
    """Execute a request using the best available assistant"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Parse request
        prompt = data.get('prompt', '')
        capability = data.get('capability', 'code_generation')
        context = data.get('context', {})
        preferred_assistant = data.get('assistant')
        project_path = data.get('project_path')
        files = data.get('files', [])
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'No prompt provided'
            }), 400
        
        # Validate capability
        try:
            capability_enum = AssistantCapability(capability)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid capability: {capability}'
            }), 400
        
        # Create request
        assistant_request = AssistantRequest(
            prompt=prompt,
            context=context,
            capability=capability_enum,
            project_path=project_path,
            files=files,
            metadata=data.get('metadata', {})
        )
        
        # Execute request
        registry = get_coding_assistant_registry()
        response = registry.execute_request(assistant_request, preferred_assistant)
        
        return jsonify({
            'success': response.success,
            'content': response.content,
            'metadata': response.metadata,
            'error': response.error,
            'suggestions': response.suggestions,
            'files_modified': response.files_modified
        })
        
    except Exception as e:
        logger.error(f"Error executing assistant request: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@coding_assistants_bp.route('/api/assistants/<assistant_name>/execute', methods=['POST'])
def execute_specific_assistant(assistant_name: str):
    """Execute a request using a specific assistant"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        registry = get_coding_assistant_registry()
        assistant = registry.get_assistant(assistant_name)
        
        if not assistant:
            return jsonify({
                'success': False,
                'error': f'Assistant {assistant_name} not found'
            }), 404
        
        if not assistant.is_available():
            return jsonify({
                'success': False,
                'error': f'Assistant {assistant_name} is not available'
            }), 503
        
        # Parse request
        prompt = data.get('prompt', '')
        capability = data.get('capability', 'code_generation')
        context = data.get('context', {})
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'No prompt provided'
            }), 400
        
        # Validate capability
        try:
            capability_enum = AssistantCapability(capability)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid capability: {capability}'
            }), 400
        
        if not assistant.supports_capability(capability_enum):
            return jsonify({
                'success': False,
                'error': f'Assistant {assistant_name} does not support {capability}'
            }), 400
        
        # Create and execute request
        assistant_request = AssistantRequest(
            prompt=prompt,
            context=context,
            capability=capability_enum,
            project_path=data.get('project_path'),
            files=data.get('files', []),
            metadata=data.get('metadata', {})
        )
        
        response = assistant.execute_request(assistant_request)
        
        return jsonify({
            'success': response.success,
            'content': response.content,
            'metadata': response.metadata,
            'error': response.error,
            'suggestions': response.suggestions,
            'files_modified': response.files_modified,
            'assistant': assistant_name
        })
        
    except Exception as e:
        logger.error(f"Error executing {assistant_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@coding_assistants_bp.route('/api/assistants/<assistant_name>/status', methods=['GET'])
def get_assistant_status(assistant_name: str):
    """Get status of a specific assistant"""
    try:
        registry = get_coding_assistant_registry()
        assistant = registry.get_assistant(assistant_name)
        
        if not assistant:
            return jsonify({
                'success': False,
                'error': f'Assistant {assistant_name} not found'
            }), 404
        
        status = assistant.get_health_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting assistant status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@coding_assistants_bp.route('/api/assistants/routing', methods=['POST'])
def configure_capability_routing():
    """Configure capability routing to specific assistants"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        registry = get_coding_assistant_registry()
        
        routing_config = data.get('routing', {})
        
        for capability_str, assistant_name in routing_config.items():
            try:
                capability = AssistantCapability(capability_str)
                registry.set_capability_routing(capability, assistant_name)
            except ValueError:
                logger.warning(f"Invalid capability in routing config: {capability_str}")
        
        return jsonify({
            'success': True,
            'message': 'Capability routing configured',
            'routing': {cap.value: assistant for cap, assistant in registry.capability_routing.items()}
        })
        
    except Exception as e:
        logger.error(f"Error configuring routing: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@coding_assistants_bp.route('/api/assistants/kiro/configure', methods=['POST'])
def configure_kiro_assistant():
    """Configure Kiro assistant integration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        registry = get_coding_assistant_registry()
        kiro_assistant = registry.get_assistant('kiro')
        
        if not kiro_assistant:
            return jsonify({
                'success': False,
                'error': 'Kiro assistant not found'
            }), 404
        
        # Update configuration
        config_updates = {}
        
        if 'mcp_server_url' in data:
            config_updates['mcp_server_url'] = data['mcp_server_url']
        
        if 'api_endpoint' in data:
            config_updates['api_endpoint'] = data['api_endpoint']
        
        if 'api_key' in data:
            config_updates['api_key'] = data['api_key']
        
        if 'workspace_path' in data:
            config_updates['workspace_path'] = data['workspace_path']
        
        # Update assistant config
        kiro_assistant.config.update(config_updates)
        
        return jsonify({
            'success': True,
            'message': 'Kiro assistant configured',
            'available': kiro_assistant.is_available(),
            'config_keys': list(kiro_assistant.config.keys())
        })
        
    except Exception as e:
        logger.error(f"Error configuring Kiro assistant: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _get_capability_description(capability: AssistantCapability) -> str:
    """Get description for a capability"""
    descriptions = {
        AssistantCapability.CODE_GENERATION: "Generate new code based on requirements",
        AssistantCapability.CODE_REVIEW: "Review existing code for quality and best practices",
        AssistantCapability.CODE_COMPLETION: "Complete partial code snippets",
        AssistantCapability.REFACTORING: "Refactor code to improve structure and maintainability",
        AssistantCapability.DOCUMENTATION: "Generate documentation for code",
        AssistantCapability.TESTING: "Generate test cases and test code",
        AssistantCapability.DEBUGGING: "Help debug issues and errors",
        AssistantCapability.ARCHITECTURE_ANALYSIS: "Analyze system architecture and design",
        AssistantCapability.SPEC_GENERATION: "Generate specifications and requirements"
    }
    return descriptions.get(capability, "No description available")