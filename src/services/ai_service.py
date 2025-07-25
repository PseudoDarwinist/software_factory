"""
AI Service - Unified AI integrations for Software Factory
Consolidates Goose and Model Garden integrations with consistent interfaces
"""

import os
import subprocess
import tempfile
import logging
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Custom exception for AI service errors"""
    pass


class GooseIntegration:
    """Goose AI integration with repository awareness and MCP extensions"""
    
    def __init__(self, project_path: str = None):
        self.project_path = project_path or os.getcwd()
        # Use the actual Goose binary path from installation
        self.goose_script = os.environ.get('GOOSE_SCRIPT_PATH', '/Users/chetansingh/bin/goose')
        self.logger = logging.getLogger(__name__)
        self.logger = logging.getLogger(__name__)
        
    def execute_task(self, instruction: str, business_context: Dict = None, github_repo: Dict = None) -> Dict[str, Any]:
        """Execute goose task with instruction and optional business context"""
        try:
            # Check if Goose is available
            if not self.is_available():
                logger.warning("Goose binary not found, falling back to direct API call")
                return self._fallback_to_direct_api(instruction, business_context)
            
            # Check if this is a DefineAgent prompt that should be passed through unchanged
            if ("You are a senior product manager and business analyst" in instruction and 
                "ANALYZE THE REPOSITORY FIRST" in instruction):
                logger.info("DefineAgent prompt detected in GooseIntegration - using unchanged")
                enhanced_instruction = instruction  # No enhancement for DefineAgent
            else:
                # Enhance instruction with business context if provided
                enhanced_instruction = self._enhance_instruction(instruction, business_context, github_repo)
            
            # Create temporary instruction file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(enhanced_instruction)
                instruction_file = f.name
            
            try:
                logger.info(f"Executing Goose with command: {self.goose_script} run -i - --no-session --quiet")
                logger.info(f"Working directory: {self.project_path}")
                logger.info(f"Instruction length: {len(enhanced_instruction)} characters")
                
                # Run goose with enhanced instruction using run command for non-interactive execution
                # Increase timeout for DefineAgent complex prompts
                timeout_seconds = 120 if ("You are a senior product manager" in enhanced_instruction) else 30
                
                result = subprocess.run(
                    [self.goose_script, 'run', '-i', '-', '--no-session', '--quiet'],
                    input=enhanced_instruction,
                    capture_output=True,
                    text=True,
                    cwd=self.project_path,
                    timeout=timeout_seconds  # 2 minutes for DefineAgent, 30s for others
                )
                
                logger.info(f"Goose execution completed with return code: {result.returncode}")
                logger.info(f"Stdout length: {len(result.stdout)} characters")
                logger.info(f"Stderr length: {len(result.stderr)} characters")
                if result.stderr:
                    logger.warning(f"Goose stderr: {result.stderr[:500]}...")
                if result.stdout:
                    logger.info(f"Goose stdout preview: {result.stdout[:200]}...")
                
                # Cleanup
                os.unlink(instruction_file)
                
                # Clean the output by removing Goose logging and technical info
                cleaned_output = self._clean_goose_output(result.stdout)
                
                # Debug: Log both raw and cleaned output
                logger.info(f"Raw output length: {len(result.stdout)}")
                logger.info(f"Cleaned output length: {len(cleaned_output)}")
                logger.info(f"Cleaned output preview: {cleaned_output[:300]}...")
                
                return {
                    'success': result.returncode == 0,
                    'output': cleaned_output,
                    'error': result.stderr,
                    'returncode': result.returncode,
                    'enhanced_instruction': enhanced_instruction,
                    'provider': 'goose',
                    'model': 'claude-code'
                }
                
            except subprocess.TimeoutExpired:
                logger.error("Goose task timed out after 2 minutes")
                # Cleanup
                os.unlink(instruction_file)
                return self._fallback_to_direct_api(instruction, business_context)
                
        except Exception as e:
            logger.error(f"Goose execution failed: {e}")
            return self._fallback_to_direct_api(instruction, business_context)
    
    def _fallback_to_direct_api(self, instruction: str, business_context: Dict = None) -> Dict[str, Any]:
        """Fallback to Model Garden when Goose fails"""
        logger.warning("Goose failed, attempting Model Garden fallback")
        
        try:
            # Initialize Model Garden
            model_garden = ModelGardenIntegration()
            
            # Format business context for Model Garden
            product_context = {}
            if business_context:
                product_context = {
                    'domain': business_context.get('domain', ''),
                    'useCase': business_context.get('useCase', ''),
                    'targetAudience': business_context.get('targetAudience', ''),
                    'requirements': business_context.get('requirements', '')
                }
            
            # Execute with Model Garden using a reliable model
            result = model_garden.execute_task(
                instruction=instruction,
                product_context=product_context,
                model='claude-sonnet-3.5',  # Reliable fallback model
                role='developer'  # Repository analysis role
            )
            
            if result.get('success'):
                logger.info("Model Garden fallback successful")
                return {
                    'success': True,
                    'output': result.get('response', ''),
                    'error': None,
                    'returncode': 0,
                    'provider': 'model-garden-fallback'
                }
            else:
                logger.error(f"Model Garden fallback failed: {result.get('error')}")
                return {
                    'success': False,
                    'output': '',
                    'error': f"Both Goose and Model Garden failed: {result.get('error')}",
                    'returncode': -1,
                    'provider': 'all-fallbacks-failed'
                }
                
        except Exception as e:
            logger.error(f"Model Garden fallback exception: {e}")
            
            # Try Claude Code SDK as final fallback
            try:
                from .claude_code_service import ClaudeCodeService
                claude_service = ClaudeCodeService()
                
                if claude_service.is_available():
                    logger.info("Attempting Claude Code SDK as final fallback")
                    
                    # For DefineAgent requests, use specialized method
                    if ("You are a senior product manager and business analyst" in instruction and 
                        "ANALYZE THE REPOSITORY FIRST" in instruction):
                        
                        # Extract system context and idea content from DefineAgent prompt
                        lines = instruction.split('\n')
                        system_context = ""
                        idea_content = ""
                        
                        in_system_context = False
                        in_feature_request = False
                        
                        for line in lines:
                            if "SYSTEM CONTEXT:" in line:
                                in_system_context = True
                                continue
                            elif "FEATURE REQUEST:" in line:
                                in_system_context = False
                                in_feature_request = True
                                continue
                            elif "INSTRUCTIONS:" in line:
                                in_feature_request = False
                                break
                            
                            if in_system_context:
                                system_context += line + "\n"
                            elif in_feature_request:
                                idea_content += line + "\n"
                        
                        result = claude_service.create_specification(idea_content.strip(), system_context.strip())
                    else:
                        result = claude_service.execute_task(instruction)
                    
                    if result.get('success'):
                        logger.info("Claude Code SDK fallback successful")
                        return result
                    else:
                        logger.error(f"Claude Code SDK fallback failed: {result.get('error')}")
                
            except ImportError:
                logger.warning("Claude Code SDK not available for fallback")
            except Exception as claude_e:
                logger.error(f"Claude Code SDK fallback error: {claude_e}")
            
            return {
                'success': False,
                'output': '',
                'error': f"All fallbacks failed: Goose timeout, Model Garden down, Claude Code SDK error: {str(e)}",
                'returncode': -1,
                'provider': 'all-fallbacks-failed'
            }
    
    def _enhance_instruction(self, instruction: str, business_context: Dict = None, github_repo: Dict = None) -> str:
        """Enhance instruction with context and repository information"""
        enhanced_instruction = instruction
        
        # Add business context if provided
        if business_context and any(business_context.values()):
            context_str = self._format_business_context(business_context)
            enhanced_instruction = f"""Business Context:
{context_str}

Task: {instruction}

Please consider the business context above when providing your response."""

        # Add GitHub repository context if provided
        if github_repo and github_repo.get('connected'):
            enhanced_instruction += f"""

REPOSITORY CONTEXT:
- Repository: {github_repo.get('fullName', github_repo.get('name', 'Unknown'))}
- Branch: {github_repo.get('branch', 'main')}
- Visibility: {'Private' if github_repo.get('private') else 'Public'}

You have filesystem access to analyze repository files and GitHub API access for repository operations. Use these tools to:
- Analyze existing code structure and files
- Suggest code improvements and new features
- Create implementation plans based on actual codebase
- Provide repository-specific guidance and recommendations

When working with repositories, always examine the actual files to understand the codebase before making suggestions."""
        
        return enhanced_instruction
    
    def _format_business_context(self, context: Dict) -> str:
        """Format business context for Goose prompts"""
        formatted = []
        if context.get('domain'):
            formatted.append(f"Business Domain: {context['domain']}")
        if context.get('useCase'):
            formatted.append(f"Use Case: {context['useCase']}")
        if context.get('targetAudience'):
            formatted.append(f"Target Audience: {context['targetAudience']}")
        if context.get('keyRequirements'):
            formatted.append(f"Key Requirements: {context['keyRequirements']}")
        if context.get('successMetrics'):
            formatted.append(f"Success Metrics: {context['successMetrics']}")
        
        return '\n'.join(formatted)
    
    def _clean_goose_output(self, raw_output: str) -> str:
        """Clean Goose output by removing technical logging and setup info"""
        import re
        
        lines = raw_output.split('\n')
        cleaned_lines = []
        skip_until_content = True
        
        for line in lines:
            # Remove ANSI color codes first
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
            
            # Skip initial Goose setup and logging lines
            if skip_until_content:
                if (clean_line.startswith('🦆') or 
                    clean_line.startswith('🎯') or 
                    clean_line.startswith('🌐') or 
                    clean_line.startswith('starting session') or 
                    'logging to' in clean_line or 
                    'working directory' in clean_line or
                    clean_line.strip() == ''):
                    continue
                else:
                    skip_until_content = False
            
            # Skip empty lines at the start
            if not cleaned_lines and clean_line.strip() == '':
                continue
                
            cleaned_lines.append(clean_line)
        
        # Join and clean up extra whitespace
        result = '\n'.join(cleaned_lines).strip()
        
        # Remove multiple consecutive newlines
        result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)
        
        # If result is empty or too short, return a default message
        if not result or len(result.strip()) < 10:
            return "I'm ready to help! Please provide more details about what you'd like assistance with."
        
        return result
    
    def is_available(self) -> bool:
        """Check if Goose is available"""
        try:
            # Check if the binary exists and is executable
            if not os.path.exists(self.goose_script):
                return False
            
            # Try to run goose --help to verify it's working
            result = subprocess.run(
                [self.goose_script, '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False


class ModelGardenIntegration:
    """Model Garden integration with enterprise LLMs"""
    
    def __init__(self):
        self.api_url = os.environ.get('MODEL_GARDEN_API_URL', 
                                     'https://quasarmarket.coforge.com/aistudio-llmrouter-api/api/v2/chat/completions')
        self.api_key = os.environ.get('MODEL_GARDEN_API_KEY', 
                                     'b3540f69-5289-483e-91fe-942c4bfa458c')
        
        # Available models mapping
        self.available_models = {
            'claude-opus-4': 'Claude Opus 4',
            'claude-sonnet-3.5': 'Claude Sonnet 3.5',
            'gemini-2.5-flash': 'Gemini 2.5 Flash',
            'gpt-4o': 'GPT-4o'
        }
    
    def execute_task(self, instruction: str, product_context: Dict = None, model: str = 'claude-opus-4', role: str = 'po') -> Dict[str, Any]:
        """Execute AI task using Model Garden"""
        try:
            if not instruction:
                raise AIServiceError('No instruction provided')
            
            # Check if this is a DefineAgent prompt that should be passed through unchanged
            if ("You are a senior product manager and business analyst" in instruction and 
                "ANALYZE THE REPOSITORY FIRST" in instruction):
                logger.info("DefineAgent prompt detected in ModelGardenIntegration - using unchanged")
                enhanced_instruction = instruction  # No enhancement for DefineAgent
            else:
                # Enhance instruction with role and context
                enhanced_instruction = self._enhance_instruction(instruction, product_context, role)
            
            # Prepare API request
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": self.api_key
            }
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": enhanced_instruction}],
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2000
            }
            
            # Make API request
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            ai_output = result['choices'][0]['message']['content']
            
            return {
                'success': True,
                'output': ai_output,
                'model': self.available_models.get(model, model),
                'provider': 'model-garden',
                'enhanced_instruction': enhanced_instruction
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Model Garden API error: {e}")
            return {
                'success': False,
                'error': f'Model Garden API error: {str(e)}',
                'output': '',
                'provider': 'model-garden'
            }
        except Exception as e:
            logger.error(f"Model Garden execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'provider': 'model-garden'
            }
    
    def _enhance_instruction(self, instruction: str, product_context: Dict = None, role: str = 'po') -> str:
        """Enhance instruction with role and product context"""
        enhanced_instruction = f"""Role: {role.upper()}

{instruction}

Please respond as a {role} expert, providing practical, actionable insights relevant to this role in the Software Development Lifecycle."""

        if product_context and any(product_context.values()):
            context_str = self._format_product_context(product_context)
            enhanced_instruction += f"""

Product Context:
{context_str}

Please consider the product context above when providing your response."""

        return enhanced_instruction
    
    def _format_product_context(self, context: Dict) -> str:
        """Format product context for Model Garden prompts"""
        formatted = []
        if context.get('productVision'):
            formatted.append(f"Product Vision: {context['productVision']}")
        if context.get('targetUsers'):
            formatted.append(f"Target Users: {context['targetUsers']}")
        if context.get('sprintGoal'):
            formatted.append(f"Sprint Goal: {context['sprintGoal']}")
        if context.get('keyEpics'):
            formatted.append(f"Key Epics: {context['keyEpics']}")
        if context.get('acceptanceCriteria'):
            formatted.append(f"Acceptance Criteria Framework: {context['acceptanceCriteria']}")
        
        return '\n'.join(formatted)
    
    def get_available_models(self) -> Dict[str, str]:
        """Get list of available models"""
        return self.available_models
    
    def is_available(self) -> bool:
        """Check if Model Garden is available"""
        try:
            # Simple health check
            headers = {"X-API-KEY": self.api_key}
            response = requests.get(self.api_url.replace('/chat/completions', '/health'), 
                                  headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return True  # Assume available if health check fails


class AIService:
    """Unified AI service that manages both Goose and Model Garden integrations"""
    
    def __init__(self):
        self.goose = GooseIntegration()
        self.model_garden = ModelGardenIntegration()
        self.logger = logging.getLogger(__name__)
    
    def execute_goose_task(self, instruction: str, business_context: Dict = None, github_repo: Dict = None, role: str = 'business') -> Dict[str, Any]:
        """Execute task using Goose AI with repository awareness and vector context"""
        self.logger.info(f"Executing Goose task for role: {role}")
        
        # Check if this is a DefineAgent prompt that should be passed through unchanged
        if ("You are a senior product manager and business analyst" in instruction and 
            "ANALYZE THE REPOSITORY FIRST" in instruction):
            self.logger.info("DefineAgent prompt detected - passing through unchanged to GooseAI")
            self.logger.info(f"DefineAgent prompt length: {len(instruction)} characters")
            return self.goose.execute_task(instruction, business_context, github_repo)
        
        # For other requests, add role-specific context
        # Get relevant context from vector database
        vector_context = self._get_vector_context(instruction, role)
        
        # Add role-specific prompting with vector context
        enhanced_instruction = f"""Role: {role.upper()}

{vector_context}{instruction}

Please respond as a {role} expert, providing practical, actionable insights relevant to this role in the Software Development Lifecycle."""
        
        return self.goose.execute_task(enhanced_instruction, business_context, github_repo)
    
    def execute_model_garden_task(self, instruction: str, product_context: Dict = None, model: str = 'claude-opus-4', role: str = 'po') -> Dict[str, Any]:
        """Execute task using Model Garden with vector context"""
        self.logger.info(f"Executing Model Garden task with model: {model}, role: {role}")
        
        # Check if this is a DefineAgent prompt that should be passed through unchanged
        if ("You are a senior product manager and business analyst" in instruction and 
            "ANALYZE THE REPOSITORY FIRST" in instruction):
            self.logger.info("DefineAgent prompt detected - passing through unchanged to Model Garden")
            self.logger.info(f"DefineAgent prompt length: {len(instruction)} characters")
            return self.model_garden.execute_task(instruction, product_context, model, role)
        
        # For other requests, add vector context
        # Get relevant context from vector database
        vector_context = self._get_vector_context(instruction, role)
        
        # Add vector context to instruction
        if vector_context:
            enhanced_instruction = f"{vector_context}{instruction}"
        else:
            enhanced_instruction = instruction
        
        return self.model_garden.execute_task(enhanced_instruction, product_context, model, role)
    
    def _get_vector_context(self, instruction: str, role: str = None) -> str:
        """Get relevant context from vector database for AI model calls"""
        try:
            # Import vector service
            from .vector_service import get_vector_service
            vector_service = get_vector_service()
            
            if not vector_service:
                return ""
            
            # Define document types based on role
            document_types = []
            if role in ['business', 'po']:
                document_types = ['conversation', 'system_map', 'documentation']
            elif role in ['developer', 'designer']:
                document_types = ['code_file', 'documentation', 'system_map']
            else:
                document_types = None  # Search all types
            
            # Get AI context with appropriate token limit
            context = vector_service.get_ai_context(
                query=instruction,
                max_tokens=1500,  # Leave room for instruction and response
                document_types=document_types
            )
            
            return context
            
        except Exception as e:
            self.logger.warning(f"Failed to get vector context: {e}")
            return ""
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all AI services"""
        return {
            'goose': {
                'available': self.goose.is_available(),
                'script_path': self.goose.goose_script,
                'project_path': self.goose.project_path,
                'model': 'gemini-2.5-flash',
                'provider': 'google',
                'roles_supported': ['business', 'po', 'designer', 'developer']
            },
            'model_garden': {
                'available': self.model_garden.is_available(),
                'api_url': self.model_garden.api_url,
                'models': self.model_garden.get_available_models(),
                'roles_supported': ['po', 'business', 'designer', 'developer']
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def test_integrations(self) -> Dict[str, Any]:
        """Test both AI integrations"""
        test_instruction = "Hello! Please confirm you're working properly by explaining what you can help with in software development."
        
        results = {}
        
        # Test Goose
        if self.goose.is_available():
            goose_result = self.goose.execute_task(test_instruction)
            results['goose'] = {
                'tested': True,
                'success': goose_result['success'],
                'response_length': len(goose_result.get('output', ''))
            }
        else:
            results['goose'] = {
                'tested': False,
                'success': False,
                'error': 'Goose script not found'
            }
        
        # Test Model Garden
        mg_result = self.model_garden.execute_task(test_instruction)
        results['model_garden'] = {
            'tested': True,
            'success': mg_result['success'],
            'response_length': len(mg_result.get('output', ''))
        }
        
        return {
            'test_instruction': test_instruction,
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        }


# Global AI service instance
ai_service = AIService()


def get_ai_service() -> AIService:
    """Get the global AI service instance"""
    return ai_service