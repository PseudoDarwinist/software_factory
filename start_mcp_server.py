#!/usr/bin/env python3
"""
Software Factory MCP Server Startup Script

This script starts the Software Factory MCP server with proper error handling
and environment setup.
"""

import os
import sys
import logging
from pathlib import Path

def setup_environment():
    """Setup environment for MCP server"""
    # Add project root to Python path
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Set environment variables
    os.environ.setdefault('SF_WORKSPACE', str(project_root))
    os.environ.setdefault('PYTHONPATH', str(project_root))

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import mcp
        print("✅ MCP library found")
    except ImportError:
        print("❌ MCP library not found")
        print("💡 Install with: pip install mcp")
        return False
    
    try:
        from src.mcp.server import server
        print("✅ Software Factory MCP server module found")
    except ImportError as e:
        print(f"❌ Could not import MCP server: {e}")
        print("💡 Make sure you're running from the Software Factory root directory")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🚀 Starting Software Factory MCP Server")
    print("=" * 50)
    
    # Setup environment
    setup_environment()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print("🔧 Environment setup complete")
    print("📡 Starting MCP server on stdio transport...")
    print("💡 To connect from Kiro: kiro mcp add software-factory -- python -m src.mcp.server")
    print("⏹️  Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Import and run the server
        from src.mcp.server import main as server_main
        server_main()
    except KeyboardInterrupt:
        print("\n👋 MCP server stopped by user")
    except Exception as e:
        print(f"\n❌ MCP server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()