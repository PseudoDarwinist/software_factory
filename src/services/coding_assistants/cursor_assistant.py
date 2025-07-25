"""
Cursor Assistant Plugin - Integration with Cursor IDE
"""

import requests
import subprocess
import os
from typing import Dict, Any, List
from .base import CodingAssistantPlugin, AssistantCapability, AssistantRequest, AssistantResponse


class CursorAssistant(CodingAssistantPlugin):
    """Cursor IDE integration for Software Factory"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("cursor", config)
        
        self.api_endpoint = self.config.get('api_endpoint')
        self.api_key = self.config.get('api_key')
        self.workspace_path = self.config.get('workspace_path', os.getcwd())
    
    @property
    def capabilities(self) -> List[AssistantCapability]:
        return [
            AssistantCapability.CODE_GENERATION,
            AssistantCapability.CODE_COMPLETION,
            AssistantCapability.CODE_REVIEW,
            AssistantCapability.REFACTORING,
            AssistantCapability.DEBUGGING
        ]
    
    @property
    def provider(self) -> str:
        return "cursor"
    
    def is_available(self) -> bool:
        """Check if Cursor is available"""
        # Check API endpoint
        if self.api_endpoint and self.api_key:
            try:
                headers = {'Authorization': f'Bearer {self.api_key}'}
                response = requests.get(f"{self.api_endpoint}/health", headers=headers, timeout=5)
                return response.status_code == 200
            except:
                pass
        
        # Check CLI
        try:
            result = subprocess.run(['cursor', '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            pass
        
        return False
    
    def execute_request(self, request: AssistantRequest) -> AssistantResponse:
        """Execute request using Cursor"""
        try:
            if self.api_endpoint and self.api_key:
                return self._execute_via_api(request)
            else:
                return self._execute_via_cli(request)
                
        except Exception as e:
            self.logger.error(f"Cursor execution failed: {e}")
            return AssistantResponse(
                success=False,
                content="",
                metadata={},
                error=str(e)
            )
    
    def _execute_via_api(self, request: AssistantRequest) -> AssistantResponse:
        """Execute via Cursor API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            api_request = {
                "prompt": request.prompt,
                "capability": request.capability.value,
                "context": request.context,
                "files": request.files or []
            }
            
            response = requests.post(
                f"{self.api_endpoint}/generate",
                headers=headers,
                json=api_request,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            return AssistantResponse(
                success=result.get('success', False),
                content=result.get('content', ''),
                metadata=result.get('metadata', {}),
                error=result.get('error')
            )
            
        except Exception as e:
            raise Exception(f"Cursor API execution failed: {e}")
    
    def _execute_via_cli(self, request: AssistantRequest) -> AssistantResponse:
        """Execute via Cursor CLI (limited functionality)"""
        # Cursor CLI has limited automation capabilities
        # This is a placeholder for when Cursor expands CLI features
        
        return AssistantResponse(
            success=False,
            content="",
            metadata={},
            error="Cursor CLI automation not yet supported"
        )