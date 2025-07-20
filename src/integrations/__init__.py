"""
Integration adapters for external systems.
"""

from .github_adapter import GitHubAdapter
from .jenkins_adapter import JenkinsAdapter
from .slack_adapter import SlackAdapter
from .figma_adapter import FigmaAdapter

__all__ = ['GitHubAdapter', 'JenkinsAdapter', 'SlackAdapter', 'FigmaAdapter']