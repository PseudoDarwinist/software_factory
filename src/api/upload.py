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
    'extracting': 0.50,  # Changed from 'analyzing' to match frontend
    'drafting': 0.75,
    'ready': 1.0
}

# File upload configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    'pdf', 'jpg', 'jpeg', 'png', 'gif',  # Original formats
    'md', 'txt', 'doc', 'docx',          # Document formats
    'csv', 'xlsx', 'xls',                # Spreadsheet formats
    'json', 'xml', 'yaml', 'yml'         # Data formats
}
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
        valid_statuses = ['active', 'reading', 'extracting', 'drafting', 'ready', 'complete', 'error']
        
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
        
        return jsonify({'data': response_data}), 201
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error uploading files: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': f'Failed to upload files: {str(e)}'}), 500


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


@upload_bp.route('/status/<session_id>', methods=['GET'])
def get_processing_status(session_id):
    """Get processing status for all files in a session"""
    try:
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get all files in the session
        files = UploadedFile.get_by_session(session_id)
        
        # Calculate simple progress
        total_files = len(files)
        if total_files == 0:
            progress = 0.0
            status = 'no_files'
        else:
            completed_files = sum(1 for f in files if f.processing_status == 'complete')
            error_files = sum(1 for f in files if f.processing_status == 'error')
            processing_files = sum(1 for f in files if f.processing_status == 'processing')
            pending_files = sum(1 for f in files if f.processing_status == 'pending')
            
            progress = (completed_files / total_files) * 100.0
            
            # Determine overall status
            if error_files > 0 and completed_files == 0:
                status = 'error'
            elif error_files > 0:
                status = 'partial_error'
            elif processing_files > 0:
                status = 'processing'
            elif pending_files > 0:
                status = 'pending'
            elif completed_files == total_files:
                status = 'complete'
            else:
                status = 'unknown'
        
        # Get file details with retry logic for errors
        file_details = []
        for file in files:
            file_info = {
                'id': str(file.id),
                'filename': file.filename,
                'file_type': file.file_type,
                'source_id': file.source_id,
                'processing_status': file.processing_status,
                'file_size': file.file_size,
                'can_retry': file.processing_status == 'error'
            }
            
            # Add validation errors if any
            if file.processing_status == 'error':
                validation_errors = file.validate_for_ai_processing()
                if validation_errors:
                    file_info['validation_errors'] = validation_errors
            
            file_details.append(file_info)
        
        response_data = {
            'session_id': session_id,
            'overall_status': status,
            'progress_percentage': round(progress, 1),
            'total_files': total_files,
            'completed_files': sum(1 for f in files if f.processing_status == 'complete'),
            'error_files': sum(1 for f in files if f.processing_status == 'error'),
            'processing_files': sum(1 for f in files if f.processing_status == 'processing'),
            'pending_files': sum(1 for f in files if f.processing_status == 'pending'),
            'files': file_details,
            'last_updated': session.updated_at.isoformat()
        }
        
        return jsonify({'data': response_data})
        
    except Exception as e:
        current_app.logger.error(f"Error getting processing status: {str(e)}")
        return jsonify({'error': 'Failed to get processing status'}), 500


@upload_bp.route('/retry/<file_id>', methods=['POST'])
def retry_file_processing(file_id):
    """Retry processing for a failed file"""
    try:
        file_record = UploadedFile.query.get(file_id)
        if not file_record:
            return jsonify({'error': 'File not found'}), 404
        
        if file_record.processing_status != 'error':
            return jsonify({'error': 'File is not in error state'}), 400
        
        # Reset file to pending status for retry
        file_record.update_processing_status('pending')
        
        current_app.logger.info(f"Retrying processing for file {file_id}")
        
        return jsonify({
            'file_id': str(file_record.id),
            'filename': file_record.filename,
            'processing_status': file_record.processing_status,
            'message': 'File queued for retry'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrying file processing: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to retry file processing'}), 500


@upload_bp.route('/session/context/<session_id>', methods=['GET'])
def get_session_context(session_id):
    """Get AI-generated analysis and file metadata for a session"""
    try:
        # Basic access control - verify session exists and belongs to a valid project
        session = UploadSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Verify project exists (basic access control)
        project = MissionControlProject.query.get(session.project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Get all files in the session
        files = UploadedFile.get_by_session(session_id)
        
        # Create file metadata with download URLs
        file_metadata = []
        for file in files:
            file_info = {
                'id': str(file.id),
                'filename': file.filename,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'source_id': file.source_id,
                'processing_status': file.processing_status,
                'created_at': file.created_at.isoformat(),
                'download_url': f"/api/upload/files/download/{file.id}",
                'has_extracted_text': bool(file.extracted_text)
            }
            
            # Add page count for PDFs
            if file.page_count:
                file_info['page_count'] = file.page_count
            
            # Add validation errors if any
            validation_errors = file.validate_for_ai_processing()
            if validation_errors:
                file_info['validation_errors'] = validation_errors
            
            file_metadata.append(file_info)
        
        # Calculate processing statistics
        total_files = len(files)
        completed_files = sum(1 for f in files if f.processing_status == 'complete')
        error_files = sum(1 for f in files if f.processing_status == 'error')
        
        # Get PRD information for this session
        prd_info = None
        try:
            from ..models.prd import PRD
        except ImportError:
            from models.prd import PRD
        
        try:
            latest_prd = PRD.get_latest_for_session(str(session.id))
            if latest_prd:
                prd_info = {
                    'id': str(latest_prd.id),
                    'version': latest_prd.version,
                    'status': latest_prd.status,
                    'created_at': latest_prd.created_at.isoformat(),
                    'created_by': latest_prd.created_by,
                    'has_markdown': bool(latest_prd.md_uri),
                    'has_json_summary': bool(latest_prd.json_uri),
                    'sources': latest_prd.sources or []
                }
        except Exception as prd_error:
            current_app.logger.error(f"Error retrieving PRD for session {session_id}: {str(prd_error)}")
        
        # Prepare response data
        context_data = {
            'session_id': str(session.id),
            'project_id': session.project_id,
            'description': session.description,
            'status': session.status,
            'ai_model_used': session.ai_model_used,
            'ai_analysis': session.ai_analysis,
            'prd_preview': session.prd_preview,
            'combined_content': session.combined_content,
            'completeness_score': session.completeness_score or calculate_completeness_score(session),
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
            'processing_stats': {
                'total_files': total_files,
                'completed_files': completed_files,
                'error_files': error_files,
                'success_rate': (completed_files / total_files * 100) if total_files > 0 else 0
            },
            'files': file_metadata,
            'prd_info': prd_info
        }
        
        current_app.logger.info(f"Retrieved session context for {session_id}")
        
        return jsonify({'data': context_data})
        
    except Exception as e:
        current_app.logger.error(f"Error getting session context: {str(e)}")
        return jsonify({'error': 'Failed to get session context'}), 500


@upload_bp.route('/files/download/<file_id>', methods=['GET'])
def download_file(file_id):
    """Download a source file by ID"""
    try:
        # Get file record
        file_record = UploadedFile.query.get(file_id)
        if not file_record:
            return jsonify({'error': 'File not found'}), 404
        
        # Basic access control - verify session and project exist
        session = UploadSession.query.get(file_record.session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        project = MissionControlProject.query.get(session.project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Check if file exists on disk
        if not os.path.exists(file_record.file_path):
            return jsonify({'error': 'File not found on disk'}), 404
        
        # For URL files, return the extracted content as text
        if file_record.file_type == 'url':
            return jsonify({
                'file_id': str(file_record.id),
                'filename': file_record.filename,
                'file_type': 'url',
                'content': file_record.extracted_text or 'No content available',
                'source_id': file_record.source_id
            })
        
        # For binary files, return file info and base64 content for API access
        try:
            with open(file_record.file_path, 'rb') as f:
                file_content = f.read()
            
            import base64
            base64_content = base64.b64encode(file_content).decode('utf-8')
            
            return jsonify({
                'file_id': str(file_record.id),
                'filename': file_record.filename,
                'file_type': file_record.file_type,
                'file_size': file_record.file_size,
                'content': base64_content,
                'encoding': 'base64',
                'source_id': file_record.source_id
            })
            
        except Exception as e:
            current_app.logger.error(f"Error reading file {file_id}: {str(e)}")
            return jsonify({'error': 'Failed to read file'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': 'Failed to download file'}), 500


@upload_bp.route('/test-logging', methods=['GET'])
def test_logging():
    """Test endpoint to verify logging is working"""
    current_app.logger.info("🧪 TEST LOG MESSAGE - INFO level")
    current_app.logger.warning("🧪 TEST LOG MESSAGE - WARNING level")
    current_app.logger.error("🧪 TEST LOG MESSAGE - ERROR level")
    return jsonify({'message': 'Logging test complete - check server logs'})


@upload_bp.route('/session/<session_id>/analyze', methods=['POST'])
def analyze_session_files(session_id):
    """Trigger AI analysis of all files in a session"""
    try:
        print(f"🔍 DEBUG: Starting analysis for session {session_id}")
        current_app.logger.info(f"🔍 Starting analysis for session {session_id}")
        
        # Verify session exists
        print(f"🔍 DEBUG: Looking up session {session_id}")
        session = UploadSession.query.get(session_id)
        if not session:
            print(f"❌ DEBUG: Session {session_id} not found")
            current_app.logger.error(f"❌ Session {session_id} not found")
            return jsonify({'error': 'Session not found'}), 404
        
        print(f"✅ DEBUG: Found session {session_id}, project_id: {session.project_id}")
        
        # Get all files in the session (pending or complete)
        print(f"🔍 DEBUG: Getting files for session {session_id}")
        files = [f for f in session.files if f.processing_status in ['pending', 'complete']]
        print(f"✅ DEBUG: Found {len(files)} files to analyze")
        
        if not files:
            print(f"❌ DEBUG: No files to analyze")
            return jsonify({'error': 'No files to analyze'}), 400
        
        # Update session status to indicate analysis is starting
        print(f"🔍 DEBUG: Updating session status to 'extracting'")
        session.update_status('extracting')
        
        # Prepare file data for AI analysis
        file_data = []
        for file in files:
            file_data.append({
                'file_path': file.file_path,
                'file_type': file.file_type,
                'filename': file.filename,
                'source_id': file.source_id
            })
        
        # Get AI broker and analyze files
        print(f"🔍 DEBUG: Importing AI broker")
        try:
            from ..services.ai_broker import get_ai_broker
        except ImportError:
            from services.ai_broker import get_ai_broker
        
        print(f"🔍 DEBUG: Getting AI broker instance")
        ai_broker = get_ai_broker()
        
        # Get preferred model from request data
        print(f"🔍 DEBUG: Getting request data")
        data = request.get_json() or {}
        preferred_model = data.get('preferred_model', 'claude-opus-4')
        print(f"✅ DEBUG: Using model: {preferred_model}")
        
        # Analyze files
        print(f"🔍 DEBUG: Starting AI analysis with {len(file_data)} files")
        analysis_result = ai_broker.analyze_uploaded_files(
            session_id=session_id,
            files=file_data,
            preferred_model=preferred_model
        )
        print(f"✅ DEBUG: AI analysis completed, success: {analysis_result.get('success', False)}")
        
        if analysis_result['success']:
            print(f"✅ DEBUG: AI analysis successful for session {session_id}")
            current_app.logger.info(f"✅ AI analysis successful for session {session_id}")
            
            # Update session with analysis results
            print(f"🔍 DEBUG: Updating session with analysis results")
            session.update_ai_analysis(analysis_result['analysis'])
            session.update_ai_model_used(analysis_result['model_used'])
            session.update_status('ready')
            print(f"✅ DEBUG: Session updated successfully")
            
            # Generate structured PRD summary using the PRD model
            print(f"🔍 DEBUG: Importing PRD models")
            try:
                from ..models.prd import extract_prd_summary, PRD
            except ImportError:
                from models.prd import extract_prd_summary, PRD
            print(f"✅ DEBUG: PRD models imported successfully")
            
            # Extract source IDs from files for attribution
            print(f"🔍 DEBUG: Extracting source IDs from {len(files)} files")
            source_ids = [f.source_id for f in files if f.source_id]
            print(f"✅ DEBUG: Found {len(source_ids)} source IDs: {source_ids}")
            
            # Generate structured summary
            print(f"🔍 DEBUG: Generating PRD summary from analysis")
            prd_summary = extract_prd_summary(analysis_result['analysis'], source_ids)
            print(f"✅ DEBUG: PRD summary generated successfully")
            
            # Create PRD record in database
            try:
                print(f"🔄 Creating PRD record for session {session_id}, project {session.project_id}")
                current_app.logger.info(f"Creating PRD record for session {session_id}, project {session.project_id}")
                prd_record = PRD.create_draft(
                    project_id=str(session.project_id),  # Ensure string conversion
                    draft_id=str(session.id),
                    md_content=analysis_result['analysis'],  # Store full markdown content
                    json_summary=prd_summary,  # Store structured JSON summary
                    sources=source_ids,  # Link to source files for traceability
                    created_by=data.get('created_by', 'system')  # Track who created it
                )
                
                print(f"✅ Created PRD record {prd_record.id} for session {session_id}")
                current_app.logger.info(f"Created PRD record {prd_record.id} for session {session_id}")
                
            except Exception as prd_error:
                import traceback
                print(f"❌ Failed to create PRD record for session {session_id}: {str(prd_error)}")
                print(f"PRD creation traceback: {traceback.format_exc()}")
                current_app.logger.error(f"Failed to create PRD record for session {session_id}: {str(prd_error)}")
                current_app.logger.error(f"PRD creation traceback: {traceback.format_exc()}")
                # Continue processing even if PRD creation fails
                prd_record = None
            
            # Convert summary to formatted text for preview
            prd_preview_lines = []
            
            if prd_summary['problem']['text']:
                sources_str = ' '.join(prd_summary['problem']['sources']) if prd_summary['problem']['sources'] else ''
                prd_preview_lines.append(f"• Problem. {prd_summary['problem']['text']} {sources_str}".strip())
            
            if prd_summary['audience']['text']:
                sources_str = ' '.join(prd_summary['audience']['sources']) if prd_summary['audience']['sources'] else ''
                prd_preview_lines.append(f"• Audience. {prd_summary['audience']['text']} {sources_str}".strip())
            
            if prd_summary['goals']['items']:
                prd_preview_lines.append("• Goals.")
                for i, goal in enumerate(prd_summary['goals']['items'][:3]):  # Limit to 3 goals
                    source = prd_summary['goals']['sources'][i] if i < len(prd_summary['goals']['sources']) else ''
                    prd_preview_lines.append(f"  – {goal} {source}".strip())
            
            if prd_summary['risks']['items']:
                risk = prd_summary['risks']['items'][0]  # Show first risk
                source = prd_summary['risks']['sources'][0] if prd_summary['risks']['sources'] else ''
                prd_preview_lines.append(f"• Risks. {risk} {source}".strip())
            
            if prd_summary['competitive_scan']['items']:
                prd_preview_lines.append("• Competitive scan.")
                for i, comp in enumerate(prd_summary['competitive_scan']['items'][:2]):  # Limit to 2 competitors
                    source = prd_summary['competitive_scan']['sources'][i] if i < len(prd_summary['competitive_scan']['sources']) else ''
                    prd_preview_lines.append(f"  – {comp} {source}".strip())
            
            if prd_summary['open_questions']['items']:
                prd_preview_lines.append("• Open questions.")
                for i, question in enumerate(prd_summary['open_questions']['items'][:3]):  # Limit to 3 questions
                    source = prd_summary['open_questions']['sources'][i] if i < len(prd_summary['open_questions']['sources']) else ''
                    prd_preview_lines.append(f"  – {question} {source}".strip())
            
            prd_preview = '\n'.join(prd_preview_lines)
            session.update_prd_preview(prd_preview)
            
            # Calculate and update completeness score
            completeness_score = calculate_completeness_score(session)
            session.update_completeness_score(completeness_score)
            
            current_app.logger.info(f"Successfully analyzed files for session {session_id} using {analysis_result['model_used']}")
            
            response_data = {
                'session_id': str(session.id),
                'status': 'success',
                'model_used': analysis_result['model_used'],
                'processing_time': analysis_result.get('processing_time', 0),
                'tokens_used': analysis_result.get('tokens_used', 0),
                'analysis_preview': prd_preview,
                'completeness_score': completeness_score,
                'session_status': session.status,
                'prd_info': {
                    'id': str(prd_record.id) if prd_record else None,
                    'version': prd_record.version if prd_record else None,
                    'status': prd_record.status if prd_record else None,
                    'created_at': prd_record.created_at.isoformat() if prd_record else None
                } if prd_record else None
            }
            
            return jsonify({'data': response_data})
        else:
            # Analysis failed
            session.update_status('error')
            
            current_app.logger.error(f"AI analysis failed for session {session_id}: {analysis_result['error']}")
            
            response_data = {
                'session_id': str(session.id),
                'status': 'error',
                'error': analysis_result['error'],
                'session_status': session.status
            }
            
            return jsonify({'data': response_data}), 200
        
    except Exception as e:
        import traceback
        print(f"❌ DEBUG: Exception in analyze_session_files: {str(e)}")
        print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
        current_app.logger.error(f"Error analyzing session files: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Update session status to error
        try:
            session = UploadSession.query.get(session_id)
            if session:
                session.update_status('error')
        except:
            pass
        
        # Return 500 error to match what the UI is seeing
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


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