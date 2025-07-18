"""
Request validation utilities
"""

from functools import wraps
from flask import request, jsonify
import re


def validate_json(f):
    """Decorator to ensure request contains valid JSON"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        return f(*args, **kwargs)
    return decorated_function


def validate_required_fields(required_fields):
    """Decorator to validate required fields in JSON request"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body is required'}), 400
            
            missing_fields = []
            for field in required_fields:
                if field not in data or not data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_url(url):
    """Validate if a string is a valid URL"""
    if not url:
        return True  # Empty URLs are allowed
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def validate_project_name(name):
    """Validate project name format"""
    if not name or not isinstance(name, str):
        return False, "Project name must be a non-empty string"
    
    name = name.strip()
    if len(name) < 1:
        return False, "Project name cannot be empty"
    
    if len(name) > 100:
        return False, "Project name cannot exceed 100 characters"
    
    # Check for invalid characters
    if re.search(r'[<>:"/\\|?*]', name):
        return False, "Project name contains invalid characters"
    
    return True, None


def sanitize_string(value, max_length=None):
    """Sanitize string input by trimming and limiting length"""
    if not value or not isinstance(value, str):
        return None
    
    sanitized = value.strip()
    if not sanitized:
        return None
    
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()
    
    return sanitized