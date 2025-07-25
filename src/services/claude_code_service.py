"""
Claude Code SDK Integration Service
Provides Claude Code SDK as a reliable fallback for AI operations
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ClaudeCodeService:
    """Claude Code SDK integration for AI-powered development tasks"""
    
    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path or os.getcwd())
        self.logger = logging.getLogger(__name__)
        self.claude_cli_path = "/Users/chetansingh/.claude/local/claude"
        
        # Claude Code uses pro subscription auth, not API key
        self.logger.info("Claude Code uses pro subscription authentication")
        
        # Check if Claude Code CLI is available
        self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Claude Code SDK is available"""
        try:
            import claude_code_sdk
            self.logger.info("Claude Code SDK is available")
            return True
        except ImportError:
            self.logger.warning("Claude Code SDK not installed. Install with: pip install claude-code-sdk")
            return False
    
    def is_available(self) -> bool:
        """Check if Claude Code CLI can be used"""
        # Check if Claude CLI exists and is executable
        if not os.path.exists(self.claude_cli_path):
            self.logger.warning(f"Claude CLI not found at: {self.claude_cli_path}")
            return False
        
        # Check if it's executable
        if not os.access(self.claude_cli_path, os.X_OK):
            self.logger.warning(f"Claude CLI not executable at: {self.claude_cli_path}")
            return False
        
        self.logger.info(f"Claude Code SDK is available at: {self.claude_cli_path}")
        return True
    
    def execute_task_cli(self, instruction: str, context: Dict = None) -> Dict[str, Any]:
        """Execute task using Claude Code CLI directly"""
        try:
            import subprocess
            import tempfile
            
            # Create temporary file for instruction
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(instruction)
                instruction_file = f.name

            try:
                # Use JSON output so we can parse / log easily
                result = subprocess.run(
                    [self.claude_cli_path, '--print', instruction_file, '--output-format', 'text'],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True,
                    timeout=300  # 5-minute safety timeout (CLI should normally finish sooner)
                )
                
                # Cleanup temp file
                os.unlink(instruction_file)
                
                if result.returncode == 0:
                    return {
                        'success': True,
                        'output': result.stdout,
                        'error': None,
                        'returncode': 0,
                        'provider': 'claude-code-cli'
                    }
                else:
                    return {
                        'success': False,
                        'output': result.stdout,
                        'error': result.stderr,
                        'returncode': result.returncode,
                        'provider': 'claude-code-cli-failed'
                    }
                    
            except subprocess.TimeoutExpired:
                os.unlink(instruction_file)
                return {
                    'success': False,
                    'output': '',
                    'error': 'Claude Code CLI timed out after 5 minutes',
                    'returncode': -1,
                    'provider': 'claude-code-cli-timeout'
                }
            
        except Exception as e:
            self.logger.error(f"Claude Code CLI execution failed: {e}")
            return {
                'success': False,
                'output': '',
                'error': f"Claude Code CLI error: {str(e)}",
                'returncode': -1,
                'provider': 'claude-code-cli-error'
            }

    async def _execute_task_sdk_async(self, instruction: str) -> Dict[str, Any]:
        """Use claude_code_sdk for streaming execution (avoids CLI timeouts)."""
        try:
            from claude_code_sdk import query, ClaudeCodeOptions, Message, TextBlock, AssistantMessage
            import anyio, asyncio

            collected_text = []

            async def _run():
                async for message in query(
                    prompt=instruction,
                    options=ClaudeCodeOptions(cwd=self.project_path)
                ):
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                collected_text.append(block.text)

            # enforce 5-minute timeout similar to CLI
            with anyio.fail_after(300):
                await _run()

            return {
                'success': True,
                'output': ''.join(collected_text),
                'error': None,
                'returncode': 0,
                'provider': 'claude-code-sdk'
            }

        except ModuleNotFoundError:
            return {'success': False, 'error': 'claude_code_sdk not installed', 'output': '', 'returncode': -1, 'provider': 'sdk-missing'}
        except Exception as e:
            return {'success': False, 'error': str(e), 'output': '', 'returncode': -1, 'provider': 'sdk-error'}

    def execute_task(self, instruction: str, context: Dict = None) -> Dict[str, Any]:
        """Execute using SDK first (stream), then fallback to CLI"""
        import anyio

        sdk_result = anyio.run(self._execute_task_sdk_async, instruction)
        if sdk_result.get('success'):
            return sdk_result

        self.logger.warning(f"Claude Code SDK failed: {sdk_result.get('error')}. Falling back to CLI.")
        return self.execute_task_cli(instruction, context)

    # NOTE: create_specification now uses execute_task which prefers SDK first.

    def create_specification(self, idea_content: str, system_context: str = "") -> Dict[str, Any]:
        """Create specification documents using Claude Code CLI"""
        
        # Create focused prompt for Claude Code CLI
        prompt = f"""I need you to analyze this repository and create a comprehensive requirements.md document.

{system_context}

FEATURE REQUEST:
{idea_content}

TASK: Create detailed requirements.md with repository analysis

INSTRUCTIONS:
1. First, analyze the existing codebase structure
2. Understand the current architecture, patterns, and technologies  
3. Generate requirements.md following the project's conventions
4. Reference actual files and patterns from the repository
5. Ensure integration with existing APIs and data models

Please start by examining the repository structure, then generate the requirements.md document."""

        return self.execute_task(prompt)