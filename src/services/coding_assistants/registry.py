"""
Coding Assistant Registry - Manages all available coding assistants
"""

import logging
from typing import Dict, List, Optional
from .base import CodingAssistantPlugin, AssistantCapability, AssistantRequest, AssistantResponse

logger = logging.getLogger(__name__)


class CodingAssistantRegistry:
    """Registry for managing coding assistant plugins"""
    
    def __init__(self):
        self.assistants: Dict[str, CodingAssistantPlugin] = {}
        self.default_assistant: Optional[str] = None
        self.capability_routing: Dict[AssistantCapability, str] = {}
    
    def register_assistant(self, assistant: CodingAssistantPlugin, is_default: bool = False):
        """Register a coding assistant"""
        self.assistants[assistant.name] = assistant
        
        if is_default or not self.default_assistant:
            self.default_assistant = assistant.name
        
        logger.info(f"Registered assistant: {assistant.name} ({assistant.provider})")
    
    def unregister_assistant(self, name: str):
        """Unregister a coding assistant"""
        if name in self.assistants:
            del self.assistants[name]
            
            if self.default_assistant == name:
                self.default_assistant = next(iter(self.assistants.keys()), None)
            
            logger.info(f"Unregistered assistant: {name}")
    
    def get_assistant(self, name: str) -> Optional[CodingAssistantPlugin]:
        """Get assistant by name"""
        return self.assistants.get(name)
    
    def get_available_assistants(self) -> List[CodingAssistantPlugin]:
        """Get all available assistants"""
        return [assistant for assistant in self.assistants.values() if assistant.is_available()]
    
    def get_assistants_for_capability(self, capability: AssistantCapability) -> List[CodingAssistantPlugin]:
        """Get assistants that support a specific capability"""
        return [
            assistant for assistant in self.assistants.values()
            if assistant.is_available() and assistant.supports_capability(capability)
        ]
    
    def set_capability_routing(self, capability: AssistantCapability, assistant_name: str):
        """Route a specific capability to a specific assistant"""
        if assistant_name in self.assistants:
            self.capability_routing[capability] = assistant_name
            logger.info(f"Routed {capability.value} to {assistant_name}")
    
    def execute_request(self, request: AssistantRequest, preferred_assistant: str = None) -> AssistantResponse:
        """Execute a request using the best available assistant"""
        
        # 1. Try preferred assistant if specified
        if preferred_assistant and preferred_assistant in self.assistants:
            assistant = self.assistants[preferred_assistant]
            if assistant.is_available() and assistant.supports_capability(request.capability):
                try:
                    return assistant.execute_request(request)
                except Exception as e:
                    logger.warning(f"Preferred assistant {preferred_assistant} failed: {e}")
        
        # 2. Try capability-specific routing
        if request.capability in self.capability_routing:
            routed_assistant = self.capability_routing[request.capability]
            if routed_assistant in self.assistants:
                assistant = self.assistants[routed_assistant]
                if assistant.is_available():
                    try:
                        return assistant.execute_request(request)
                    except Exception as e:
                        logger.warning(f"Routed assistant {routed_assistant} failed: {e}")
        
        # 3. Try all available assistants that support the capability
        capable_assistants = self.get_assistants_for_capability(request.capability)
        
        for assistant in capable_assistants:
            try:
                return assistant.execute_request(request)
            except Exception as e:
                logger.warning(f"Assistant {assistant.name} failed: {e}")
                continue
        
        # 4. Fallback to default assistant if it supports the capability
        if self.default_assistant and self.default_assistant in self.assistants:
            default = self.assistants[self.default_assistant]
            if default.is_available() and default.supports_capability(request.capability):
                try:
                    return default.execute_request(request)
                except Exception as e:
                    logger.error(f"Default assistant {self.default_assistant} failed: {e}")
        
        # 5. No assistant could handle the request
        return AssistantResponse(
            success=False,
            content="",
            metadata={},
            error=f"No available assistant supports {request.capability.value}"
        )
    
    def get_registry_status(self) -> Dict[str, any]:
        """Get status of all registered assistants"""
        status = {
            'total_assistants': len(self.assistants),
            'available_assistants': len(self.get_available_assistants()),
            'default_assistant': self.default_assistant,
            'assistants': {},
            'capability_routing': {cap.value: assistant for cap, assistant in self.capability_routing.items()}
        }
        
        for name, assistant in self.assistants.items():
            status['assistants'][name] = assistant.get_health_status()
        
        return status


# Global registry instance
_registry = CodingAssistantRegistry()


def get_coding_assistant_registry() -> CodingAssistantRegistry:
    """Get the global coding assistant registry"""
    return _registry


def initialize_default_assistants():
    """Initialize default coding assistants"""
    from .kiro_assistant import KiroAssistant
    from .cursor_assistant import CursorAssistant
    from .claude_code_assistant import ClaudeCodeAssistant
    
    registry = get_coding_assistant_registry()
    
    # Register Kiro assistant
    kiro_config = {
        'mcp_server_url': None,  # Will be configured via environment
        'api_endpoint': None,
        'workspace_path': None
    }
    registry.register_assistant(KiroAssistant(kiro_config))
    
    # Register Cursor assistant
    cursor_config = {
        'api_endpoint': None,  # Will be configured
        'api_key': None
    }
    registry.register_assistant(CursorAssistant(cursor_config))
    
    # Register Claude Code assistant
    claude_config = {
        'api_key': None  # Will use existing Claude integration
    }
    registry.register_assistant(ClaudeCodeAssistant(claude_config), is_default=True)
    
    logger.info("Initialized default coding assistants")