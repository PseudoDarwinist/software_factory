"""
GitHub Integration API
Provides endpoints for GitHub connectivity and repository operations
"""

import os
import logging
import requests
from flask import Blueprint, jsonify, request, current_app

github_bp = Blueprint('github', __name__, url_prefix='/api/github')
logger = logging.getLogger(__name__)


def _normalize_repo_url_for_api(url: str) -> str:
    """
    Normalize a GitHub URL to the 'owner/repo' format for API calls.
    Handles various formats like https, git@, and with/without .git.
    """
    if not url:
        return ""
    
    # Remove protocol and domain
    if url.startswith("https://github.com/"):
        url = url[19:]
    elif url.startswith("git@github.com:"):
        url = url[15:]
        
    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]
        
    return url


@github_bp.route('/status', methods=['GET'])
def get_github_status():
    """
    Check GitHub connectivity and repository access
    GET /api/github/status?project_id=xxx
    """
    try:
        try:
            from ..models.mission_control_project import MissionControlProject
        except ImportError:
            from models.mission_control_project import MissionControlProject
        
        # Get project ID from query parameter
        project_id = request.args.get('project_id')
        
        # Try to get GitHub token from project or fallback to environment
        github_token = None
        repo_url = None
        
        if project_id:
            try:
                project = MissionControlProject.query.get(project_id)
                if project:
                    github_token = project.github_token
                    repo_url = project.repo_url
            except Exception as e:
                logger.warning(f"Could not fetch project {project_id}: {e}")
        
        # Fallback to environment variables if no project token
        if not github_token:
            github_token = os.getenv('GITHUB_TOKEN')
        if not repo_url:
            repo_url = os.getenv('GITHUB_REPO_URL')
            
        if not github_token:
            return jsonify({
                'connected': False,
                'error': 'GitHub token not configured',
                'repo_accessible': False
            }), 200
        
        # Check GitHub API connectivity
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Test API access
        response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
        
        if response.status_code != 200:
            return jsonify({
                'connected': False,
                'error': 'GitHub API authentication failed',
                'repo_accessible': False
            }), 200
        
        # Check repository access
        repo_accessible = False
        base_branch = 'main'
        
        if repo_url:
            try:
                repo_path = _normalize_repo_url_for_api(repo_url)
                
                repo_response = requests.get(
                    f'https://api.github.com/repos/{repo_path}',
                    headers=headers,
                    timeout=10
                )
                
                if repo_response.status_code == 200:
                    repo_data = repo_response.json()
                    repo_accessible = True
                    base_branch = repo_data.get('default_branch', 'main')
                    # Do not re-assign repo_url here, keep the original full URL
                    pass
                
            except Exception as repo_error:
                logger.warning(f"Could not check repository access: {repo_error}")
        
        return jsonify({
            'connected': True,
            'repo_accessible': repo_accessible,
            'repo_url': repo_url,
            'base_branch': base_branch
        }), 200
        
    except requests.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        return jsonify({
            'connected': False,
            'error': 'GitHub API request failed',
            'repo_accessible': False
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking GitHub status: {e}")
        return jsonify({
            'connected': False,
            'error': 'Internal server error',
            'repo_accessible': False
        }), 500


@github_bp.route('/preflight', methods=['POST'])
def run_preflight_checks():
    """
    Run comprehensive preflight checks for a project
    POST /api/github/preflight
    Body: { "project_id": "proj-1", "github_token": "...", "repo_url": "..." }
    """
    try:
        # Import preflight service
        try:
            from ..services.preflight_service import get_preflight_service
        except ImportError:
            from services.preflight_service import get_preflight_service
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        project_id = data.get('project_id')
        github_token = data.get('github_token')
        repo_url = data.get('repo_url')
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        if not github_token:
            return jsonify({'error': 'github_token is required'}), 400
        
        if not repo_url:
            return jsonify({'error': 'repo_url is required'}), 400
        
        # Run preflight checks and update project
        preflight_service = get_preflight_service()
        results = preflight_service.update_project_connection_status(
            project_id, github_token, repo_url
        )
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Error running preflight checks: {e}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@github_bp.route('/preflight/<project_id>', methods=['GET'])
def get_preflight_status(project_id):
    """
    Get preflight status for a project
    GET /api/github/preflight/proj-1
    """
    try:
        try:
            from ..models.mission_control_project import MissionControlProject
        except ImportError:
            from models.mission_control_project import MissionControlProject
        
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # If we have stored connection status, return it
        if project.connection_status:
            return jsonify({
                'project_id': project_id,
                'connection_status': project.connection_status,
                'last_checked': project.updated_at.isoformat() if project.updated_at else None
            }), 200
        else:
            return jsonify({
                'project_id': project_id,
                'connection_status': 'Not checked',
                'last_checked': None
            }), 200
        
    except Exception as e:
        logger.error(f"Error getting preflight status: {e}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500