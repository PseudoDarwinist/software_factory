"""
Claude Code Assistant Plugin - Integration with existing Claude Code service
"""

from typing import Dict, Any, List
from .base import CodingAssistantPlugin, AssistantCapability, AssistantRequest, AssistantResponse


class ClaudeCodeAssistant(CodingAssistantPlugin):
    """Claude Code integration using existing AI service"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("claude-code", config)
        
        self.api_key = self.config.get('api_key')
        self._ai_service = None
    
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
        return "claude-code"
    
    def is_available(self) -> bool:
        """Check if Claude Code is available via existing AI service"""
        try:
            ai_service = self._get_ai_service()
            return ai_service is not None
        except:
            return False
    
    def execute_request(self, request: AssistantRequest) -> AssistantResponse:
        """Execute request using Claude Code via existing AI service"""
        try:
            ai_service = self._get_ai_service()
            if not ai_service:
                raise Exception("AI service not available")
            
            # Format prompt for Claude Code
            formatted_prompt = self._format_prompt(request)
            
            # Use existing Goose integration (which uses Claude Code)
            result = ai_service.execute_goose_task(
                instruction=formatted_prompt,
                business_context=request.context.get('business_context'),
                github_repo=request.context.get('github_repo'),
                role=request.context.get('role', 'developer')
            )
            
            return AssistantResponse(
                success=result.get('success', False),
                content=result.get('output', ''),
                metadata={
                    'provider': result.get('provider', 'claude-code'),
                    'model': result.get('model', 'claude-code'),
                    'capability': request.capability.value
                },
                error=result.get('error')
            )
            
        except Exception as e:
            self.logger.error(f"Claude Code execution failed: {e}")
            return AssistantResponse(
                success=False,
                content="",
                metadata={},
                error=str(e)
            )
    
    def _get_ai_service(self):
        """Get the AI service instance"""
        if self._ai_service is None:
            try:
                from ..ai_service import get_ai_service
                self._ai_service = get_ai_service()
            except ImportError:
                # Fallback import
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                from ai_service import get_ai_service
                self._ai_service = get_ai_service()
        
        return self._ai_service
    
    def _format_prompt(self, request: AssistantRequest) -> str:
        """Format prompt for Claude Code based on capability"""
        
        capability_prompts = {
            AssistantCapability.CODE_GENERATION: f"""
Generate code based on the following requirements:

{request.prompt}

Please provide clean, well-documented code that follows best practices.
""",
            
            AssistantCapability.CODE_REVIEW: f"""
Review the following code and provide feedback:

{request.prompt}

Please identify potential issues, suggest improvements, and highlight best practices.
""",
            
            AssistantCapability.REFACTORING: f"""
Refactor the following code to improve its structure and maintainability:

{request.prompt}

Please provide the refactored code with explanations of the changes made.
""",
            
            AssistantCapability.DOCUMENTATION: f"""
Generate documentation for the following code:

{request.prompt}

Please provide comprehensive documentation including usage examples.
""",
            
            AssistantCapability.TESTING: f"""
Generate tests for the following code:

{request.prompt}

Please provide comprehensive test cases covering edge cases and error conditions.
""",
            
            AssistantCapability.DEBUGGING: f"""
Help debug the following issue:

{request.prompt}

Please analyze the problem and suggest solutions.
""",
            
            AssistantCapability.ARCHITECTURE_ANALYSIS: f"""
Analyze the architecture of the following system:

{request.prompt}

Please provide insights on the design patterns, potential improvements, and architectural recommendations.
""",
            
            AssistantCapability.SPEC_GENERATION: f"""
Generate a specification based on the following requirements:

{request.prompt}

Please provide a detailed specification including requirements, design, and implementation tasks.
"""
        }
        
        base_prompt = capability_prompts.get(request.capability, request.prompt)
        
        # Add context if available
        if request.context:
            context_str = "\n\nContext:\n"
            for key, value in request.context.items():
                if key not in ['business_context', 'github_repo', 'role']:
                    context_str += f"- {key}: {value}\n"
            
            if context_str.strip() != "Context:":
                base_prompt += context_str
        
        # Add file references if available
        if request.files:
            base_prompt += f"\n\nRelevant files:\n"
            for file in request.files:
                base_prompt += f"- {file}\n"
        
        return base_prompt