"""
Mock PRD endpoint for testing the Editor.js interface
"""

from flask import Blueprint, jsonify
import uuid

mock_prd_bp = Blueprint('mock_prd', __name__, url_prefix='/api/prd-editor')

@mock_prd_bp.route('/prds/<prd_id>', methods=['GET'])
def get_prd(prd_id):
    """Return mock PRD content in Editor.js format for testing"""
    
    # Mock Editor.js content - minimal structure to test the editor
    mock_content = {
        "time": 1640995200000,
        "blocks": [
            {
                "id": str(uuid.uuid4()),
                "type": "header",
                "data": {
                    "text": "Product Requirements Document",
                    "level": 1
                }
            },
            {
                "id": str(uuid.uuid4()),
                "type": "paragraph",
                "data": {
                    "text": "This is a test PRD loaded from the backend API endpoint."
                }
            },
            {
                "id": str(uuid.uuid4()),
                "type": "header",
                "data": {
                    "text": "Executive Summary",
                    "level": 2
                }
            },
            {
                "id": str(uuid.uuid4()),
                "type": "paragraph",
                "data": {
                    "text": "This document outlines the requirements for building an intelligent system. The Editor.js interface is fully functional with all plugins loaded locally."
                }
            },
            {
                "id": str(uuid.uuid4()),
                "type": "list",
                "data": {
                    "style": "unordered",
                    "items": [
                        "All Editor.js plugins are loaded from local vendor files",
                        "No CDN dependencies required",
                        "Mermaid diagrams are supported",
                        "AI chat integration is available"
                    ]
                }
            },
            {
                "id": str(uuid.uuid4()),
                "type": "header",
                "data": {
                    "text": "Technical Architecture",
                    "level": 2
                }
            },
            {
                "id": str(uuid.uuid4()),
                "type": "mermaid",
                "data": {
                    "code": "graph TD\n    A[User] --> B[Editor.js]\n    B --> C[Backend API]\n    C --> D[Database]\n    B --> E[AI Service]"
                }
            }
        ],
        "version": "2.28.2"
    }
    
    return jsonify({
        'success': True,
        'data': {
            'id': prd_id,
            'title': 'Test PRD Document',
            'editorjs_content': mock_content,
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z'
        }
    })


@mock_prd_bp.route('/prds/<prd_id>', methods=['PUT'])
def update_prd(prd_id):
    """Mock endpoint to save PRD updates"""
    return jsonify({
        'success': True,
        'data': {
            'id': prd_id,
            'message': 'PRD updated successfully'
        }
    })
