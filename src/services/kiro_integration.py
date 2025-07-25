"""
Simple Kiro Integration for Software Factory
Focus on MCP (Model Context Protocol) integration
"""

import os
import json
import logging
import subprocess
import tempfile
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KiroRequest:
    """Simple request structure for Kiro"""
    prompt: str
    context: Dict[str, Any] = None
    workspace_path: str = None
    files: list = None


@dataclass
class KiroResponse:
    """Simple response from Kiro"""
    success: bool
    content: str
    error: Optional[str] = None
    files_changed: list = None


class KiroIntegration:
    """Simple Kiro integration for Software Factory"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or os.getcwd()
        self.mcp_config_path = os.path.join(self.workspace_path, '.kiro', 'settings', 'mcp.json')
        
    def is_kiro_available(self) -> bool:
        """Check if Kiro is available"""
        try:
            # Check if Kiro CLI is available
            result = subprocess.run(['kiro', '--version'], 
                                  capture_output=True, 
                                  timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def setup_mcp_server(self) -> bool:
        """Setup Software Factory as MCP server for Kiro"""
        try:
            # Create MCP configuration for Kiro
            mcp_config = {
                "mcpServers": {
                    "software-factory": {
                        "command": "python",
                        "args": ["-m", "src.services.mcp_server"],
                        "env": {
                            "SF_WORKSPACE": self.workspace_path,
                            "SF_API_URL": "http://localhost:8000"
                        },
                        "disabled": False,
                        "autoApprove": [
                            "generate_code",
                            "review_code", 
                            "create_spec",
                            "analyze_project"
                        ]
                    }
                }
            }
            
            # Ensure .kiro/settings directory exists
            os.makedirs(os.path.dirname(self.mcp_config_path), exist_ok=True)
            
            # Write MCP config
            with open(self.mcp_config_path, 'w') as f:
                json.dump(mcp_config, f, indent=2)
            
            logger.info(f"MCP server config created at {self.mcp_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup MCP server: {e}")
            return False
    
    def execute_with_kiro(self, request: KiroRequest) -> KiroResponse:
        """Execute a request using Kiro"""
        try:
            # Method 1: Try MCP integration (if configured)
            if self._is_mcp_configured():
                return self._execute_via_mcp(request)
            
            # Method 2: Direct CLI execution
            return self._execute_via_cli(request)
            
        except Exception as e:
            logger.error(f"Kiro execution failed: {e}")
            return KiroResponse(
                success=False,
                content="",
                error=str(e)
            )
    
    def _is_mcp_configured(self) -> bool:
        """Check if MCP is configured"""
        return os.path.exists(self.mcp_config_path)
    
    def _execute_via_mcp(self, request: KiroRequest) -> KiroResponse:
        """Execute via MCP (when Kiro connects to our MCP server)"""
        # This would be called by Kiro through MCP
        # For now, we'll simulate this by calling our own functions
        
        try:
            # Import our AI service to handle the request
            from .ai_service import get_ai_service
            
            ai_service = get_ai_service()
            
            # Format prompt for Kiro-style execution
            kiro_prompt = f"""
You are Kiro, an AI assistant helping with software development.

Context: {json.dumps(request.context or {}, indent=2)}

Task: {request.prompt}

Please provide a helpful response for this software development task.
"""
            
            # Use our existing AI service
            result = ai_service.execute_goose_task(
                instruction=kiro_prompt,
                business_context=request.context,
                role='developer'
            )
            
            return KiroResponse(
                success=result.get('success', False),
                content=result.get('output', ''),
                error=result.get('error')
            )
            
        except Exception as e:
            raise Exception(f"MCP execution failed: {e}")
    
    def _execute_via_cli(self, request: KiroRequest) -> KiroResponse:
        """Execute via Kiro CLI"""
        try:
            # Create temporary prompt file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                prompt_content = self._format_prompt_for_kiro(request)
                f.write(prompt_content)
                prompt_file = f.name
            
            try:
                # Execute Kiro CLI
                cmd = ['kiro', 'chat', '--file', prompt_file]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=request.workspace_path or self.workspace_path
                )
                
                if result.returncode == 0:
                    return KiroResponse(
                        success=True,
                        content=result.stdout.strip(),
                        files_changed=[]
                    )
                else:
                    return KiroResponse(
                        success=False,
                        content="",
                        error=result.stderr or "Kiro CLI execution failed"
                    )
                    
            finally:
                os.unlink(prompt_file)
                
        except Exception as e:
            raise Exception(f"CLI execution failed: {e}")
    
    def _format_prompt_for_kiro(self, request: KiroRequest) -> str:
        """Format prompt for Kiro"""
        prompt = f"# Software Factory Task\n\n"
        prompt += f"{request.prompt}\n\n"
        
        if request.context:
            prompt += "## Context\n"
            for key, value in request.context.items():
                prompt += f"- **{key}**: {value}\n"
            prompt += "\n"
        
        if request.files:
            prompt += "## Relevant Files\n"
            for file in request.files:
                prompt += f"- `{file}`\n"
            prompt += "\n"
        
        prompt += "Please help with this software development task.\n"
        
        return prompt


# Global instance
_kiro_integration = None


def get_kiro_integration(workspace_path: str = None) -> KiroIntegration:
    """Get global Kiro integration instance"""
    global _kiro_integration
    
    if _kiro_integration is None:
        _kiro_integration = KiroIntegration(workspace_path)
    
    return _kiro_integration


def init_kiro_integration(workspace_path: str = None) -> bool:
    """Initialize Kiro integration"""
    try:
        kiro = get_kiro_integration(workspace_path)
        
        if not kiro.is_kiro_available():
            logger.warning("Kiro CLI not available")
            return False
        
        # Setup MCP server configuration
        if kiro.setup_mcp_server():
            logger.info("Kiro integration initialized with MCP support")
        else:
            logger.info("Kiro integration initialized (CLI only)")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Kiro integration: {e}")
        return False