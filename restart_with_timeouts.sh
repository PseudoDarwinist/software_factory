#!/bin/bash

# Restart script with timeout configuration for Claude Opus 4
echo "🔄 Restarting Software Factory with Claude Opus 4 timeout fixes..."

# Kill existing processes
echo "Stopping existing processes..."
pkill -f "python.*app.py" 2>/dev/null || true
sleep 2

# Export timeout environment variables
export API_TIMEOUT_MS=600000
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=4096
export MAX_THINKING_TOKENS=2048
export CLAUDE_OPUS_TIMEOUT_SECONDS=300
export DEFAULT_MODEL_TIMEOUT_SECONDS=120

echo "Environment variables set:"
echo "  API_TIMEOUT_MS=${API_TIMEOUT_MS}"
echo "  CLAUDE_CODE_MAX_OUTPUT_TOKENS=${CLAUDE_CODE_MAX_OUTPUT_TOKENS}"
echo "  CLAUDE_OPUS_TIMEOUT_SECONDS=${CLAUDE_OPUS_TIMEOUT_SECONDS}"
echo "  DEFAULT_MODEL_TIMEOUT_SECONDS=${DEFAULT_MODEL_TIMEOUT_SECONDS}"

# Start the server
echo "🚀 Starting server with timeout fixes..."
cd src && python app.py

echo "✅ Server started with Claude Opus 4 timeout optimization"
echo ""
echo "🧪 Test instructions:"
echo "1. Open http://localhost:8000 in your browser"
echo "2. Go to Sources Tray"
echo "3. Select 'Claude Opus 4' from model dropdown"
echo "4. Upload documents and click 'Make PRD'"
echo "5. Wait up to 5 minutes (this is normal for thinking models)"
echo "6. Should complete without timeout errors!"