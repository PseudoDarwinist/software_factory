"""
Intelligent agent framework for event-driven workflow automation.
"""

from .base import BaseAgent, AgentStatus, AgentConfig
from .agent_manager import AgentManager

# Import agents that exist
try:
    from .define_agent import DefineAgent, create_define_agent
    _define_agent_available = True
except ImportError:
    _define_agent_available = False

try:
    from .capture_agent import CaptureAgent, create_capture_agent
    _capture_agent_available = True
except ImportError:
    _capture_agent_available = False

__all__ = [
    'BaseAgent',
    'AgentStatus', 
    'AgentConfig',
    'AgentManager'
]

if _define_agent_available:
    __all__.extend(['DefineAgent', 'create_define_agent'])

if _capture_agent_available:
    __all__.extend(['CaptureAgent', 'create_capture_agent'])