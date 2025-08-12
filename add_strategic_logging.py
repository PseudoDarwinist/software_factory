#!/usr/bin/env python3
"""
Strategic logging implementation to debug the timeout issue properly
"""

def add_upload_api_logging():
    """Add comprehensive logging to the upload API"""
    
    # Read the upload API file
    with open('src/api/upload.py', 'r') as f:
        content = f.read()
    
    # Add logging to the analyze_session_files function
    old_analyze_start = """@upload_bp.route('/session/<session_id>/analyze', methods=['POST'])
def analyze_session_files(session_id):
    \"\"\"Trigger AI analysis of all files in a session\"\"\"
    try:
        current_app.logger.info(f"Starting analysis for session {session_id}")"""
    
    new_analyze_start = """@upload_bp.route('/session/<session_id>/analyze', methods=['POST'])
def analyze_session_files(session_id):
    \"\"\"Trigger AI analysis of all files in a session\"\"\"
    try:
        print(f"🚀 [ANALYZE] Starting analysis for session {session_id}")
        current_app.logger.info(f"Starting analysis for session {session_id}")"""
    
    if old_analyze_start in content:
        content = content.replace(old_analyze_start, new_analyze_start)
    
    # Add logging for each stage
    stage_logs = [
        ("session.update_status('extracting')", "print(f\"📊 [ANALYZE] Stage: EXTRACTING - {session_id}\")"),
        ("session.update_status('ready')", "print(f\"✅ [ANALYZE] Stage: READY - {session_id}\")"),
        ("session.update_status('error')", "print(f\"❌ [ANALYZE] Stage: ERROR - {session_id}\")"),
        ("ai_broker.analyze_uploaded_files(", "print(f\"🤖 [ANALYZE] Calling AI broker for {session_id}\")\n        analysis_result = ai_broker.analyze_uploaded_files("),
        ("if analysis_result['success']:", "print(f\"🎯 [ANALYZE] AI analysis result: {analysis_result.get('success', 'unknown')} for {session_id}\")\n        if analysis_result['success']:"),
    ]
    
    for old_line, new_line in stage_logs:
        if old_line in content and new_line not in content:
            content = content.replace(old_line, new_line + "\n        " + old_line)
    
    # Write back
    with open('src/api/upload.py', 'w') as f:
        f.write(content)
    
    print("✅ Added upload API logging")

def add_ai_broker_logging():
    """Add logging to AI broker"""
    
    with open('src/services/ai_broker.py', 'r') as f:
        content = f.read()
    
    # Add logging to analyze_uploaded_files
    old_start = """def analyze_uploaded_files(self, session_id: str, files: List[Dict[str, Any]], 
                              preferred_model: str = None) -> Dict[str, Any]:
        \"\"\"
        Analyze uploaded files using AI models for PRD generation"""
    
    new_start = """def analyze_uploaded_files(self, session_id: str, files: List[Dict[str, Any]], 
                              preferred_model: str = None) -> Dict[str, Any]:
        \"\"\"
        Analyze uploaded files using AI models for PRD generation"""
    
    # Add logging to Claude analysis
    old_claude = """logger.info(f"Starting Claude analysis with {len(files)} files")"""
    new_claude = """print(f"🤖 [AI] Starting Claude analysis for session {session_id} with {len(files)} files")
        logger.info(f"Starting Claude analysis with {len(files)} files")"""
    
    if old_claude in content and new_claude not in content:
        content = content.replace(old_claude, new_claude)
    
    # Add response logging
    old_response = """logger.info(f"Sending request to Claude API...")"""
    new_response = """print(f"📡 [AI] Sending request to Claude API for session {session_id}")
        logger.info(f"Sending request to Claude API...")"""
    
    if old_response in content and new_response not in content:
        content = content.replace(old_response, new_response)
    
    # Add completion logging
    completion_log = """print(f"✅ [AI] Claude analysis completed for session {session_id} - {len(content)} chars")"""
    
    if "return {" in content and completion_log not in content:
        # Find the return statement in Claude analysis
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "'success': True," in line and "'content': content," in line:
                lines.insert(i, "            " + completion_log)
                break
        content = '\n'.join(lines)
    
    with open('src/services/ai_broker.py', 'w') as f:
        f.write(content)
    
    print("✅ Added AI broker logging")

def add_flask_app_logging():
    """Add request/response logging to Flask app"""
    
    with open('src/app.py', 'r') as f:
        content = f.read()
    
    # Add comprehensive request logging
    old_logging = """# Add minimal request logging for important endpoints
    @app.before_request
    def log_important_requests():
        if '/analyze' in request.url or '/upload' in request.url:
            logger.info(f"{request.method} {request.url}")

    @app.after_request
    def log_important_responses(response):
        if '/analyze' in request.url or '/upload' in request.url:
            logger.info(f"Response: {response.status_code}")
        return response"""
    
    new_logging = """# Add comprehensive request logging for debugging
    @app.before_request
    def log_important_requests():
        if '/analyze' in request.url or '/upload' in request.url or '/status' in request.url:
            print(f"🌐 [REQUEST] {request.method} {request.url}")
            logger.info(f"{request.method} {request.url}")

    @app.after_request
    def log_important_responses(response):
        if '/analyze' in request.url or '/upload' in request.url or '/status' in request.url:
            print(f"📤 [RESPONSE] {response.status_code} - {request.method} {request.url}")
            logger.info(f"Response: {response.status_code}")
        return response"""
    
    if old_logging in content:
        content = content.replace(old_logging, new_logging)
    
    with open('src/app.py', 'w') as f:
        f.write(content)
    
    print("✅ Added Flask app logging")

def main():
    print("🎯 Strategic Logging Implementation")
    print("=" * 50)
    
    add_upload_api_logging()
    add_ai_broker_logging()
    add_flask_app_logging()
    
    print("\n✅ All logging added!")
    print("\n📋 What you'll now see:")
    print("  🚀 [ANALYZE] - Analysis start/stages")
    print("  🤖 [AI] - AI broker operations")
    print("  🌐 [REQUEST] - HTTP requests")
    print("  📤 [RESPONSE] - HTTP responses")
    print("\n🔄 Restart your Flask server to see the logs")

if __name__ == "__main__":
    main()