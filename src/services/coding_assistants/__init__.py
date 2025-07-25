"""
Coding Assistants Plugin System
BYOA (Bring Your Own Assistant) implementation for Software Factory
"""

from .base import CodingAssistantPlugin, AssistantCapability
from .registry import CodingAssistantRegistry
from .kiro_assistant import KiroAssistant
from .cursor_assistant import CursorAssistant
from .claude_code_assistant import ClaudeCodeAssistant

__all__ = [
    'CodingAssistantPlugin',
    'AssistantCapability', 
    'CodingAssistantRegistry',
    'KiroAssistant',
    'CursorAssistant',
    'ClaudeCodeAssistant'
]