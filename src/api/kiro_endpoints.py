"""
Kiro API Blueprint - Endpoints for Kiro integration
Provides step-by-step spec generation using Kiro CLI with repository context
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

try:
    from ..services.kiro_integration_service import get_kiro_service
    from ..models.mission_control_project import MissionControlProject
    from ..models.base import db
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.kiro_integration_service import get_kiro_service
    from models.mission_control_project import MissionControlProject
    from models.base import db

logger = logging.getLogger(__name__)

# Create Kiro blueprint
kiro_bp = Blueprint('kiro', __name__)


@kiro_bp.route('/api/kiro/status', methods=['GET'])
def kiro_status():
    """Check if Kiro is available on the system"""
    try:
        kiro_service = get_kiro_service()
        
        is_available = kiro_service.is_available()
        version = kiro_service.get_version() if is_available else None
        
        return jsonify({
            'success': True,
            'available': is_available,
            'version': version,
            'workspace_path': kiro_service.workspace_path,
            'executable': kiro_service.kiro_executable,
            'timeout': kiro_service.timeout
        })
        
    except Exception as e:
        logger.error(f"Error checking Kiro status: {e}")
        return jsonify({
            'success': False,
            'available': False,
            'error': str(e)
        }), 500


@kiro_bp.route('/api/kiro/generate-requirements', methods=['POST'])
def generate_requirements_with_kiro():
    """Generate requirements.md using Kiro with project database lookup"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        project_id = data.get('project_id')
        idea_content = data.get('idea_content', '')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required'
            }), 400
        
        if not idea_content:
            return jsonify({
                'success': False,
                'error': 'Idea content is required'
            }), 400
        
        # Query database for project GitHub URL
        try:
            project = MissionControlProject.query.get(project_id)
            if not project:
                return jsonify({
                    'success': False,
                    'error': f'Project with ID {project_id} not found'
                }), 404
            
            github_url = project.repo_url
            if not github_url:
                return jsonify({
                    'success': False,
                    'error': 'Project does not have a GitHub repository URL configured'
                }), 400
            
        except Exception as db_error:
            logger.error(f"Database error when looking up project {project_id}: {db_error}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve project information from database'
            }), 500
        
        # Generate requirements using Kiro
        try:
            kiro_service = get_kiro_service()
            result = kiro_service.generate_requirements(github_url, idea_content)
            
            logger.info(f"Requirements generation completed for project {project_id}, success: {result.get('success')}")
            
            return jsonify(result)
            
        except Exception as kiro_error:
            logger.error(f"Kiro requirements generation failed for project {project_id}: {kiro_error}")
            return jsonify({
                'success': False,
                'error': f'Kiro requirements generation failed: {str(kiro_error)}',
                'provider': 'kiro'
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_requirements_with_kiro: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'provider': 'kiro'
        }), 500


@kiro_bp.route('/api/kiro/generate-design', methods=['POST'])
def generate_design_with_kiro():
    """Generate design.md using Kiro with context passing"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        project_id = data.get('project_id')
        idea_content = data.get('idea_content', '')
        requirements_content = data.get('requirements_content', '')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required'
            }), 400
        
        if not idea_content:
            return jsonify({
                'success': False,
                'error': 'Idea content is required'
            }), 400
        
        if not requirements_content:
            return jsonify({
                'success': False,
                'error': 'Requirements content is required for design generation'
            }), 400
        
        # Query database for project GitHub URL
        try:
            project = MissionControlProject.query.get(project_id)
            if not project:
                return jsonify({
                    'success': False,
                    'error': f'Project with ID {project_id} not found'
                }), 404
            
            github_url = project.repo_url
            if not github_url:
                return jsonify({
                    'success': False,
                    'error': 'Project does not have a GitHub repository URL configured'
                }), 400
            
        except Exception as db_error:
            logger.error(f"Database error when looking up project {project_id}: {db_error}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve project information from database'
            }), 500
        
        # Generate design using Kiro
        try:
            kiro_service = get_kiro_service()
            result = kiro_service.generate_design(github_url, idea_content, requirements_content)
            
            logger.info(f"Design generation completed for project {project_id}, success: {result.get('success')}")
            
            return jsonify(result)
            
        except Exception as kiro_error:
            logger.error(f"Kiro design generation failed for project {project_id}: {kiro_error}")
            return jsonify({
                'success': False,
                'error': f'Kiro design generation failed: {str(kiro_error)}',
                'provider': 'kiro'
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_design_with_kiro: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'provider': 'kiro'
        }), 500


@kiro_bp.route('/api/kiro/generate-tasks', methods=['POST'])
def generate_tasks_with_kiro():
    """Generate tasks.md using Kiro with full context"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        project_id = data.get('project_id')
        idea_content = data.get('idea_content', '')
        requirements_content = data.get('requirements_content', '')
        design_content = data.get('design_content', '')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID is required'
            }), 400
        
        if not idea_content:
            return jsonify({
                'success': False,
                'error': 'Idea content is required'
            }), 400
        
        if not requirements_content:
            return jsonify({
                'success': False,
                'error': 'Requirements content is required for tasks generation'
            }), 400
        
        if not design_content:
            return jsonify({
                'success': False,
                'error': 'Design content is required for tasks generation'
            }), 400
        
        # Query database for project GitHub URL
        try:
            project = MissionControlProject.query.get(project_id)
            if not project:
                return jsonify({
                    'success': False,
                    'error': f'Project with ID {project_id} not found'
                }), 404
            
            github_url = project.repo_url
            if not github_url:
                return jsonify({
                    'success': False,
                    'error': 'Project does not have a GitHub repository URL configured'
                }), 400
            
        except Exception as db_error:
            logger.error(f"Database error when looking up project {project_id}: {db_error}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve project information from database'
            }), 500
        
        # Generate tasks using Kiro
        try:
            kiro_service = get_kiro_service()
            result = kiro_service.generate_tasks(github_url, idea_content, requirements_content, design_content)
            
            logger.info(f"Tasks generation completed for project {project_id}, success: {result.get('success')}")
            
            return jsonify(result)
            
        except Exception as kiro_error:
            logger.error(f"Kiro tasks generation failed for project {project_id}: {kiro_error}")
            return jsonify({
                'success': False,
                'error': f'Kiro tasks generation failed: {str(kiro_error)}',
                'provider': 'kiro'
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_tasks_with_kiro: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'provider': 'kiro'
        }), 500


@kiro_bp.route('/api/kiro/health', methods=['GET'])
def kiro_health():
    """Check Kiro integration health"""
    try:
        kiro_service = get_kiro_service()
        
        is_available = kiro_service.is_available()
        version = kiro_service.get_version() if is_available else None
        
        # Test basic functionality if available
        test_result = None
        if is_available:
            try:
                # Simple test to verify Kiro is working
                test_result = kiro_service._execute_kiro_command("Test prompt for health check")
                test_working = test_result.get('success', False)
            except:
                test_working = False
        else:
            test_working = False
        
        health_status = {
            'kiro_available': is_available,
            'kiro_version': version,
            'kiro_executable': kiro_service.kiro_executable,
            'workspace_path': kiro_service.workspace_path,
            'test_working': test_working,
            'timeout_configured': kiro_service.timeout
        }
        
        is_healthy = is_available and test_working
        
        return jsonify({
            'success': True,
            'healthy': is_healthy,
            'status': health_status,
            'components': {
                'kiro_cli': 'operational' if is_available else 'unavailable',
                'kiro_execution': 'operational' if test_working else 'unavailable'
            }
        }), 200 if is_healthy else 503
        
    except Exception as e:
        logger.error(f"Kiro health check failed: {e}")
        return jsonify({
            'success': False,
            'healthy': False,
            'error': str(e)
        }), 503


@kiro_bp.route('/api/kiro/test', methods=['POST'])
def test_kiro_integration():
    """Test Kiro integration with a simple prompt"""
    try:
        data = request.get_json() or {}
        test_prompt = data.get('prompt', 'Hello! Please confirm you are working by responding with a brief greeting.')
        
        kiro_service = get_kiro_service()
        
        if not kiro_service.is_available():
            return jsonify({
                'success': False,
                'error': 'Kiro CLI is not available on this system',
                'available': False
            }), 503
        
        # Execute test prompt
        result = kiro_service._execute_kiro_command(test_prompt)
        
        return jsonify({
            'success': result.get('success', False),
            'test_prompt': test_prompt,
            'result': result,
            'available': True
        })
        
    except Exception as e:
        logger.error(f"Error testing Kiro integration: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'available': False
        }), 500