"""
Kiro Assistant Plugin - Integration with Kiro IDE
"""

import os
import json
import requests
import subprocess
from typing import Dict, Any, List
from .base import CodingAssistantPlugin, AssistantCapability, AssistantRequest, AssistantResponse


class KiroAssistant(CodingAssistantPlugin):
    """Kiro IDE integration for Software Factory"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("kiro", config)
        
        # Kiro integration options
        self.mcp_server_url = self.config.get('mcp_server_url')
        self.api_endpoint = self.config.get('api_endpoint')
        self.workspace_path = self.config.get('workspace_path', os.getcwd())
        
        # Authentication
        self.api_key = self.config.get('api_key')
        self.session_token = self.config.get('session_token')
    
    @property
    def capabilities(self) -> List[AssistantCapability]:
        return [
            AssistantCapability.CODE_GENERATION,
            AssistantCapability.CODE_REVIEW,
            AssistantCapability.REFACTORING,
            AssistantCapability.DOCUMENTATION,
            AssistantCapability.TESTING,
            AssistantCapability.DEBUGGING,
            AssistantCapability.ARCHITECTURE_ANALYSIS,
            AssistantCapability.SPEC_GENERATION
        ]
    
    @property
    def provider(self) -> str:
        return "kiro"
    
    def is_available(self) -> bool:
        """Check if Kiro is available via MCP or API"""
        # Option 1: Check MCP server
        if self.mcp_server_url:
            try:
                response = requests.get(f"{self.mcp_server_url}/health", timeout=5)
                return response.status_code == 200
            except:
                pass
        
        # Option 2: Check API endpoint
        if self.api_endpoint and self.api_key:
            try:
                headers = {'Authorization': f'Bearer {self.api_key}'}
                response = requests.get(f"{self.api_endpoint}/health", headers=headers, timeout=5)
                return response.status_code == 200
            except:
                pass
        
        # Option 3: Check if Kiro CLI is available
        try:
            result = subprocess.run(['kiro', '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            pass
        
        return False
    
    def execute_request(self, request: AssistantRequest) -> AssistantResponse:
        """Execute request using Kiro"""
        try:
            # Try different integration methods in order of preference
            
            # Method 1: MCP Server (preferred)
            if self.mcp_server_url:
                return self._execute_via_mcp(request)
            
            # Method 2: API Endpoint
            if self.api_endpoint and self.api_key:
                return self._execute_via_api(request)
            
            # Method 3: CLI Interface
            return self._execute_via_cli(request)
            
        except Exception as e:
            self.logger.error(f"Kiro execution failed: {e}")
            return AssistantResponse(
                success=False,
                content="",
                metadata={},
                error=str(e)
            )
    
    def _execute_via_mcp(self, request: AssistantRequest) -> AssistantResponse:
        """Execute via MCP (Model Context Protocol) server"""
        try:
            # Format request for MCP
            mcp_request = {
                "method": "tools/call",
                "params": {
                    "name": self._get_mcp_tool_name(request.capability),
                    "arguments": {
                        "prompt": request.prompt,
                        "context": request.context,
                        "files": request.files or [],
                        "workspace_path": request.project_path or self.workspace_path
                    }
                }
            }
            
            response = requests.post(
                f"{self.mcp_server_url}/call",
                json=mcp_request,
                timeout=120  # Kiro can take time for complex requests
            )
            response.raise_for_status()
            
            result = response.json()
            
            return AssistantResponse(
                success=True,
                content=result.get('content', ''),
                metadata=result.get('metadata', {}),
                suggestions=result.get('suggestions', []),
                files_modified=result.get('files_modified', [])
            )
            
        except Exception as e:
            raise Exception(f"MCP execution failed: {e}")
    
    def _execute_via_api(self, request: AssistantRequest) -> AssistantResponse:
        """Execute via Kiro API endpoint"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            api_request = {
                "prompt": request.prompt,
                "capability": request.capability.value,
                "context": request.context,
                "workspace_path": request.project_path or self.workspace_path,
                "files": request.files or []
            }
            
            response = requests.post(
                f"{self.api_endpoint}/execute",
                headers=headers,
                json=api_request,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            
            return AssistantResponse(
                success=result.get('success', False),
                content=result.get('content', ''),
                metadata=result.get('metadata', {}),
                error=result.get('error'),
                suggestions=result.get('suggestions', []),
                files_modified=result.get('files_modified', [])
            )
            
        except Exception as e:
            raise Exception(f"API execution failed: {e}")
    
    def _execute_via_cli(self, request: AssistantRequest) -> AssistantResponse:
        """Execute via Kiro CLI"""
        try:
            # Create a temporary prompt file
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                # Format prompt with context
                formatted_prompt = self._format_prompt_for_cli(request)
                f.write(formatted_prompt)
                prompt_file = f.name
            
            try:
                # Execute Kiro CLI command
                cmd = [
                    'kiro',
                    'execute',
                    '--prompt-file', prompt_file,
                    '--capability', request.capability.value
                ]
                
                if request.project_path:
                    cmd.extend(['--workspace', request.project_path])
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=request.project_path or self.workspace_path
                )
                
                if result.returncode == 0:
                    # Parse CLI output
                    output = result.stdout.strip()
                    
                    return AssistantResponse(
                        success=True,
                        content=output,
                        metadata={'method': 'cli'},
                        suggestions=[]
                    )
                else:
                    raise Exception(f"CLI failed: {result.stderr}")
                    
            finally:
                os.unlink(prompt_file)
                
        except Exception as e:
            raise Exception(f"CLI execution failed: {e}")
    
    def _get_mcp_tool_name(self, capability: AssistantCapability) -> str:
        """Map capability to MCP tool name"""
        mapping = {
            AssistantCapability.CODE_GENERATION: "generate_code",
            AssistantCapability.CODE_REVIEW: "review_code", 
            AssistantCapability.REFACTORING: "refactor_code",
            AssistantCapability.DOCUMENTATION: "generate_docs",
            AssistantCapability.TESTING: "generate_tests",
            AssistantCapability.DEBUGGING: "debug_code",
            AssistantCapability.ARCHITECTURE_ANALYSIS: "analyze_architecture",
            AssistantCapability.SPEC_GENERATION: "generate_spec"
        }
        return mapping.get(capability, "execute_task")
    
    def _format_prompt_for_cli(self, request: AssistantRequest) -> str:
        """Format prompt for CLI execution"""
        prompt = f"# {request.capability.value.replace('_', ' ').title()}\n\n"
        prompt += f"{request.prompt}\n\n"
        
        if request.context:
            prompt += "## Context\n"
            for key, value in request.context.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"
        
        if request.files:
            prompt += "## Files\n"
            for file in request.files:
                prompt += f"- {file}\n"
            prompt += "\n"
        
        return prompt