"""
Base classes for coding assistant plugins
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class AssistantCapability(Enum):
    """Capabilities that coding assistants can provide"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_COMPLETION = "code_completion"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DEBUGGING = "debugging"
    ARCHITECTURE_ANALYSIS = "architecture_analysis"
    SPEC_GENERATION = "spec_generation"


@dataclass
class AssistantRequest:
    """Request structure for coding assistants"""
    prompt: str
    context: Dict[str, Any]
    capability: AssistantCapability
    project_path: Optional[str] = None
    files: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AssistantResponse:
    """Response structure from coding assistants"""
    success: bool
    content: str
    metadata: Dict[str, Any]
    error: Optional[str] = None
    suggestions: Optional[List[str]] = None
    files_modified: Optional[List[str]] = None


class CodingAssistantPlugin(ABC):
    """Base class for all coding assistant plugins"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @property
    @abstractmethod
    def capabilities(self) -> List[AssistantCapability]:
        """Return list of capabilities this assistant supports"""
        pass
    
    @property
    @abstractmethod
    def provider(self) -> str:
        """Return the provider name (e.g., 'kiro', 'cursor', 'claude')"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the assistant is available and configured"""
        pass
    
    @abstractmethod
    def execute_request(self, request: AssistantRequest) -> AssistantResponse:
        """Execute a request using this assistant"""
        pass
    
    def supports_capability(self, capability: AssistantCapability) -> bool:
        """Check if this assistant supports a specific capability"""
        return capability in self.capabilities
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of this assistant"""
        return {
            'name': self.name,
            'provider': self.provider,
            'available': self.is_available(),
            'capabilities': [cap.value for cap in self.capabilities],
            'config_keys': list(self.config.keys())
        }