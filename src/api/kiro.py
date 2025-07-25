"""
Kiro Integration API - Simple BYOA implementation
"""

import logging
from flask import Blueprint, request, jsonify

try:
    from ..services.kiro_integration import get_kiro_integration, KiroRequest
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.kiro_integration import get_kiro_integration, KiroRequest

logger = logging.getLogger(__name__)

# Create Kiro blueprint
kiro_bp = Blueprint('kiro', __name__)


@kiro_bp.route('/api/kiro/status', methods=['GET'])
def kiro_status():
    """Check if Kiro is available"""
    try:
        kiro = get_kiro_integration()
        
        return jsonify({
            'success': True,
            'available': kiro.is_kiro_available(),
            'mcp_configured': kiro._is_mcp_configured(),
            'workspace_path': kiro.workspace_path
        })
        
    except Exception as e:
        logger.error(f"Error checking Kiro status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@kiro_bp.route('/api/kiro/execute', methods=['POST'])
def execute_with_kiro():
    """Execute a task using Kiro"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        prompt = data.get('prompt', '')
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'No prompt provided'
            }), 400
        
        # Create Kiro request
        kiro_request = KiroRequest(
            prompt=prompt,
            context=data.get('context', {}),
            workspace_path=data.get('workspace_path'),
            files=data.get('files', [])
        )
        
        # Execute with Kiro
        kiro = get_kiro_integration()
        response = kiro.execute_with_kiro(kiro_request)
        
        return jsonify({
            'success': response.success,
            'content': response.content,
            'error': response.error,
            'files_changed': response.files_changed or [],
            'provider': 'kiro'
        })
        
    except Exception as e:
        logger.error(f"Error executing with Kiro: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@kiro_bp.route('/api/kiro/setup-mcp', methods=['POST'])
def setup_kiro_mcp():
    """Setup MCP server configuration for Kiro"""
    try:
        kiro = get_kiro_integration()
        
        if kiro.setup_mcp_server():
            return jsonify({
                'success': True,
                'message': 'MCP server configured for Kiro',
                'config_path': kiro.mcp_config_path
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to setup MCP server'
            }), 500
        
    except Exception as e:
        logger.error(f"Error setting up Kiro MCP: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@kiro_bp.route('/api/kiro/test', methods=['POST'])
def test_kiro():
    """Test Kiro integration"""
    try:
        test_request = KiroRequest(
            prompt="Hello! Please confirm you're working by explaining what you can help with.",
            context={'test': True}
        )
        
        kiro = get_kiro_integration()
        response = kiro.execute_with_kiro(test_request)
        
        return jsonify({
            'success': response.success,
            'test_response': response.content,
            'error': response.error,
            'kiro_available': kiro.is_kiro_available(),
            'mcp_configured': kiro._is_mcp_configured()
        })
        
    except Exception as e:
        logger.error(f"Error testing Kiro: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500