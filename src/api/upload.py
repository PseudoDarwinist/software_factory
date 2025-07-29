"""
Upload API endpoints for file upload session management
"""

import os
import uuid
import requests
from datetime import datetime
from urllib.parse import urlparse
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

try:
    from ..models import db
    from ..models.upload_session import UploadSession
    from ..models.uploaded_file import UploadedFile
    from ..models.mission_control_project import MissionControlProject
except ImportError:
    from models import db
    from models.upload_session import UploadSession
    from models.uploaded_file import UploadedFile
    from models.mission_control_project import MissionControlProject

upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')

# Constants for progress tracking
PROGRESS_STAGES = {
    'reading': 0.25,
    'analyzing': 0.50,
    'drafting': 0.75,
    'ready': 1.0
}

# File upload configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif'}
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    """Extract file type from filename"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return 'unknown'


def calculate_completeness_score(session):
    """Calculate PRD completeness score based on session content"""
    # Basic completeness scoring logic
    score = {
        'goals_numbered': False,
        'risks_covered': False,
        'competitors_mentioned': 0,
        'overall_score': 0.0
    }
    
    if session.ai_analysis:
        content = session.ai_analysis.lower()
        
        # Check for numbered goals
        if any(marker in content for marker in ['1.', '2.', '3.', 'goal 1', 'goal 2']):
            score['goals_numbered'] = True
        
        # Check for risk coverage
        if any(risk in content for risk in ['accessibility', 'privacy', 'security', 'risk']):
            score['risks_covered'] = True
        
        # Count competitor mentions (simple heuristic)
        competitor_keywords = ['competitor', 'competition', 'rival', 'alternative']
        score['competitors_mentioned'] = sum(content.count(keyword) for keyword in competitor_keywords)
    
    # Calculate overall score
    completed_items = sum([
        score['goals_numbered'],
        score['risks_covered'],
        score['competitors_mentioned'] >= 2
    ])
    score['overall_score'] = completed_items / 3.0
    
    return score


@upload_bp.route('/session', methods=['POST'])
def create_session():
    """Create a new upload session"""
    try:
        data = request.get_json()
        
        if not data or 'project_id' not in data:
            return jsonify({'error': 'project_id is required'}), 400
        
        project_id = data['project_id']
        description = data.get('description', '')
        
        # Verify project exists
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Create new upload session
        session = UploadSession.create(
            project_id=project_id,
            description=description
        )
        
        db.session.commit()
        
        current_app.logger.info(f"Created upload session {session.id} for project {project_id}")
        
        return jsonify({
            'session_id': str(session.id),
            'project_id': project_id,
            'description': description,
            'status': session.status,
            'created_at': session.created_at.isoformat(),
            'progress': 0.0,
            'completeness_score': calculate_completeness_score(session)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating upload session: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create upload session'}), 500


@upload_bp.route('/session/<session_id>/status', methods=['PUT'])
def update_session_status(session_id):
    """Update session status for progress tracking"""
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'error': 'status is required'}), 400
        
        new_status = data['status']
        valid_statuses = ['active', 'reading', 'analyzing', 'drafting', 'ready', 'complete', 'error']
        
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400
        
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Update session status
        session.update_status(new_status)
        
        # Calculate progress based on status
        progress = PROGRESS_STAGES.get(new_status, 0.0)
        
        current_app.logger.info(f"Updated session {session_id} status to {new_status}")
        
        return jsonify({
            'session_id': str(session.id),
            'status': session.status,
            'progress': progress,
            'updated_at': session.updated_at.isoformat(),
            'completeness_score': calculate_completeness_score(session)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating session status: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update session status'}), 500


@upload_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session details with progress and completeness information"""
    try:
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Calculate current progress
        progress = PROGRESS_STAGES.get(session.status, 0.0)
        
        # Get file processing progress
        file_progress = session.get_processing_progress() / 100.0 if session.files else 0.0
        
        # Combine session progress with file processing progress
        combined_progress = min(progress + (file_progress * 0.25), 1.0)
        
        return jsonify({
            'session_id': str(session.id),
            'project_id': session.project_id,
            'description': session.description,
            'status': session.status,
            'progress': combined_progress,
            'file_count': session.get_file_count(),
            'completed_files': session.get_completed_file_count(),
            'error_files': session.get_error_file_count(),
            'completeness_score': calculate_completeness_score(session),
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
            'files': [file.to_dict() for file in session.files]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting session: {str(e)}")
        return jsonify({'error': 'Failed to get session'}), 500


@upload_bp.route('/session/<session_id>/ai-analysis', methods=['PUT'])
def update_ai_analysis(session_id):
    """Update AI analysis results for the session"""
    try:
        data = request.get_json()
        
        if not data or 'analysis' not in data:
            return jsonify({'error': 'analysis is required'}), 400
        
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Update AI analysis
        session.update_ai_analysis(data['analysis'])
        
        # Update status to ready if not already
        if session.status != 'ready':
            session.update_status('ready')
        
        current_app.logger.info(f"Updated AI analysis for session {session_id}")
        
        return jsonify({
            'session_id': str(session.id),
            'status': session.status,
            'progress': PROGRESS_STAGES.get(session.status, 1.0),
            'completeness_score': calculate_completeness_score(session),
            'updated_at': session.updated_at.isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating AI analysis: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update AI analysis'}), 500


@upload_bp.route('/session/<session_id>/combined-content', methods=['PUT'])
def update_combined_content(session_id):
    """Update combined content from all files in the session"""
    try:
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({'error': 'content is required'}), 400
        
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Update combined content
        session.update_combined_content(data['content'])
        
        current_app.logger.info(f"Updated combined content for session {session_id}")
        
        return jsonify({
            'session_id': str(session.id),
            'status': session.status,
            'updated_at': session.updated_at.isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating combined content: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update combined content'}), 500


def validate_url(url):
    """Validate URL format and accessibility"""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
        
        # Check if URL is accessible
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code >= 400:
            return False, f"URL not accessible (status: {response.status_code})"
        
        return True, None
    except requests.RequestException as e:
        return False, f"URL validation failed: {str(e)}"
    except Exception as e:
        return False, f"URL validation error: {str(e)}"


def fetch_url_content(url):
    """Fetch content from URL for processing"""
    try:
        response = requests.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        # Get content type
        content_type = response.headers.get('content-type', '').lower()
        
        # For now, just return text content
        if 'text' in content_type or 'html' in content_type:
            return response.text[:50000]  # Limit to 50KB
        else:
            return f"Content from {url} (type: {content_type})"
    except Exception as e:
        current_app.logger.error(f"Error fetching URL content: {str(e)}")
        return f"Error fetching content from {url}: {str(e)}"


@upload_bp.route('/files/<session_id>', methods=['POST'])
def upload_files(session_id):
    """Upload files to a session via drag-and-drop"""
    try:
        # Verify session exists
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No files selected'}), 400
        
        uploaded_files = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
            
            # Validate file
            if not allowed_file(file.filename):
                errors.append(f"File {file.filename}: Unsupported file type")
                continue
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                errors.append(f"File {file.filename}: Exceeds 10MB limit")
                continue
            
            # Secure filename
            filename = secure_filename(file.filename)
            file_type = get_file_type(filename)
            
            # Create upload directory if it doesn't exist
            upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Create file record
            file_record = UploadedFile.create(
                session_id=session_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                file_path=file_path
            )
            
            uploaded_files.append(file_record.to_dict())
        
        db.session.commit()
        
        current_app.logger.info(f"Uploaded {len(uploaded_files)} files to session {session_id}")
        
        response_data = {
            'session_id': session_id,
            'uploaded_files': uploaded_files,
            'total_uploaded': len(uploaded_files)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return jsonify(response_data), 201
        
    except Exception as e:
        current_app.logger.error(f"Error uploading files: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to upload files'}), 500


@upload_bp.route('/links/<session_id>', methods=['POST'])
def upload_links(session_id):
    """Upload links to a session via URL pasting"""
    try:
        # Verify session exists
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        data = request.get_json()
        if not data or 'urls' not in data:
            return jsonify({'error': 'No URLs provided'}), 400
        
        urls = data['urls']
        if not isinstance(urls, list) or not urls:
            return jsonify({'error': 'URLs must be provided as a non-empty list'}), 400
        
        uploaded_links = []
        errors = []
        
        for url in urls:
            if not isinstance(url, str) or not url.strip():
                errors.append(f"Invalid URL: {url}")
                continue
            
            url = url.strip()
            
            # Validate URL
            is_valid, error_msg = validate_url(url)
            if not is_valid:
                errors.append(f"URL {url}: {error_msg}")
                continue
            
            # Fetch content
            content = fetch_url_content(url)
            
            # Create a "file" record for the link
            parsed_url = urlparse(url)
            filename = f"{parsed_url.netloc}_{parsed_url.path.replace('/', '_')}.txt"
            if len(filename) > 100:
                filename = f"link_{uuid.uuid4().hex[:8]}.txt"
            
            # Create upload directory if it doesn't exist
            upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save content to file
            file_path = os.path.join(upload_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n\n{content}")
            
            file_size = len(content.encode('utf-8'))
            
            # Create file record
            file_record = UploadedFile.create(
                session_id=session_id,
                filename=filename,
                file_type='url',
                file_size=file_size,
                file_path=file_path
            )
            
            # Set extracted text immediately for URLs
            file_record.update_extracted_text(content)
            file_record.complete_processing()
            
            uploaded_links.append(file_record.to_dict())
        
        db.session.commit()
        
        current_app.logger.info(f"Uploaded {len(uploaded_links)} links to session {session_id}")
        
        response_data = {
            'session_id': session_id,
            'uploaded_links': uploaded_links,
            'total_uploaded': len(uploaded_links)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return jsonify(response_data), 201
        
    except Exception as e:
        current_app.logger.error(f"Error uploading links: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to upload links'}), 500


# Error handlers
@upload_bp.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 413


@upload_bp.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad request'}), 400


@upload_bp.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found'}), 404


@upload_bp.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500