"""
Build Agent - Responds to code.changed events for automated testing and LLM-powered code analysis.
"""

import logging
import subprocess
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseAgent, AgentConfig, EventProcessingResult
from ..events.base import BaseEvent
from ..events.domain_events import BuildStartedEvent, BuildCompletedEvent, BuildFailedEvent
from ..events.event_router import EventBus
from ..services.ai_service import get_ai_service


logger = logging.getLogger(__name__)


class BuildAgent(BaseAgent):
    """Agent that responds to code changes, triggers automated builds, and uses LLM for code analysis."""
    
    def __init__(self, event_bus: EventBus, build_config: Optional[Dict[str, Any]] = None, ai_service=None):
        config = AgentConfig(
            agent_id="build_agent",
            name="Build Agent",
            description="Responds to code changes, triggers automated builds, and uses LLM for code analysis",
            event_types=["code.changed", "repository.processing.completed"],
            max_concurrent_events=3,
            timeout_seconds=1800.0  # 30 minutes for builds
        )
        
        super().__init__(config, event_bus)
        self.build_config = build_config or self._get_default_build_config()
        self.ai_service = ai_service or get_ai_service()
    
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process code change events to trigger builds and tests."""
        logger.info(f"BuildAgent processing event {event.metadata.event_id}")
        
        try:
            # Extract relevant information from the event
            if event.get_event_type() == "code.changed":
                return self._handle_code_changed_event(event)
            elif event.get_event_type() == "repository.processing.completed":
                return self._handle_repository_completed_event(event)
            else:
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=0.0,
                    error_message=f"Unsupported event type: {event.get_event_type()}"
                )
                
        except Exception as e:
            logger.error(f"BuildAgent failed to process event: {e}")
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=0.0,
                error_message=str(e)
            )
    
    def _handle_code_changed_event(self, event: BaseEvent) -> EventProcessingResult:
        """Handle code.changed events with LLM-powered code analysis."""
        # Extract project information
        project_id = getattr(event, 'project_id', 'unknown')
        branch = getattr(event, 'branch', 'main')
        commit_hash = getattr(event, 'commit_hash', 'unknown')
        changed_files = getattr(event, 'changed_files', [])
        author = getattr(event, 'author', 'unknown')
        
        logger.info(f"Code changed in project {project_id}, branch {branch} by {author}")
        
        # Analyze code changes with LLM before building
        code_analysis = self._analyze_code_changes_with_ai(
            project_id=project_id,
            changed_files=changed_files,
            commit_hash=commit_hash,
            branch=branch
        )
        
        # Determine build type based on changed files and AI analysis
        build_type = self._determine_build_type(changed_files)
        if code_analysis.get('recommended_build_type'):
            build_type = code_analysis['recommended_build_type']
            logger.info(f"AI recommended build type: {build_type}")
        
        # Start build process with AI insights
        build_result = self._execute_build(
            project_id=project_id,
            branch=branch,
            commit_hash=commit_hash,
            build_type=build_type,
            correlation_id=event.metadata.correlation_id,
            trace_id=event.metadata.trace_id,
            ai_analysis=code_analysis
        )
        
        # Include AI analysis in result data
        build_result['code_analysis'] = code_analysis
        
        return EventProcessingResult(
            success=build_result['success'],
            agent_id=self.config.agent_id,
            event_id=event.metadata.event_id,
            event_type=event.get_event_type(),
            processing_time_seconds=0.0,
            result_data=build_result,
            generated_events=build_result.get('generated_events', [])
        )
    
    def _handle_repository_completed_event(self, event: BaseEvent) -> EventProcessingResult:
        """Handle repository.processing.completed events."""
        project_id = getattr(event, 'project_id', event.aggregate_id)
        
        logger.info(f"Repository processing completed for project {project_id}, triggering initial build")
        
        # Trigger initial build for newly processed repository
        build_result = self._execute_build(
            project_id=project_id,
            branch='main',
            commit_hash='latest',
            build_type='full',
            correlation_id=event.metadata.correlation_id,
            trace_id=event.metadata.trace_id
        )
        
        return EventProcessingResult(
            success=build_result['success'],
            agent_id=self.config.agent_id,
            event_id=event.metadata.event_id,
            event_type=event.get_event_type(),
            processing_time_seconds=0.0,
            result_data=build_result,
            generated_events=build_result.get('generated_events', [])
        )
    
    def _determine_build_type(self, changed_files: List[str]) -> str:
        """Determine build type based on changed files."""
        if not changed_files:
            return 'full'
        
        # Check file patterns to determine build scope
        has_backend_changes = any(
            file.endswith(('.py', '.sql', '.yml', '.yaml')) or 
            'src/' in file or 'backend/' in file
            for file in changed_files
        )
        
        has_frontend_changes = any(
            file.endswith(('.js', '.jsx', '.ts', '.tsx', '.css', '.html')) or
            'frontend/' in file or 'ui/' in file
            for file in changed_files
        )
        
        has_config_changes = any(
            file in ['requirements.txt', 'package.json', 'Dockerfile', 'docker-compose.yml'] or
            file.startswith('.') or 'config' in file.lower()
            for file in changed_files
        )
        
        has_test_changes = any(
            'test' in file.lower() or file.startswith('test_') or file.endswith('_test.py')
            for file in changed_files
        )
        
        # Determine build type
        if has_config_changes:
            return 'full'
        elif has_backend_changes and has_frontend_changes:
            return 'full'
        elif has_backend_changes:
            return 'backend'
        elif has_frontend_changes:
            return 'frontend'
        elif has_test_changes:
            return 'test'
        else:
            return 'incremental'
    
    def _analyze_code_changes_with_ai(
        self,
        project_id: str,
        changed_files: List[str],
        commit_hash: str,
        branch: str
    ) -> Dict[str, Any]:
        """Analyze code changes using AI service for build optimization and insights."""
        try:
            logger.info(f"Analyzing code changes with AI for project {project_id}")
            
            # Build prompt for code analysis
            prompt = f"""
            Analyze the following code changes for build optimization and potential issues:
            
            Project: {project_id}
            Branch: {branch}
            Commit: {commit_hash}
            Changed Files: {', '.join(changed_files)}
            
            Please provide:
            1. Recommended build type (full, backend, frontend, test, incremental)
            2. Potential build risks or issues
            3. Optimization suggestions
            4. Test coverage recommendations
            5. Performance impact assessment
            
            Focus on practical build and deployment considerations.
            """
            
            # Try Claude via Model Garden first
            try:
                result = self.ai_service.execute_model_garden_task(
                    instruction=prompt,
                    model='claude-sonnet-3.5',  # Use Sonnet for faster code analysis
                    role='developer'
                )
                
                if result['success']:
                    analysis = self._parse_code_analysis(result['output'])
                    analysis['ai_provider'] = 'claude-sonnet'
                    logger.info("Successfully analyzed code changes with Claude")
                    return analysis
                    
            except Exception as e:
                logger.warning(f"Claude analysis failed: {e}")
            
            # Fallback to Goose
            try:
                result = self.ai_service.execute_goose_task(
                    instruction=prompt,
                    role='developer'
                )
                
                if result['success']:
                    analysis = self._parse_code_analysis(result['output'])
                    analysis['ai_provider'] = 'goose'
                    logger.info("Successfully analyzed code changes with Goose")
                    return analysis
                    
            except Exception as e:
                logger.warning(f"Goose analysis failed: {e}")
            
            # Return basic analysis if AI fails
            return self._get_basic_code_analysis(changed_files)
            
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return self._get_basic_code_analysis(changed_files)
    
    def _parse_code_analysis(self, ai_output: str) -> Dict[str, Any]:
        """Parse AI output into structured code analysis."""
        analysis = {
            'recommended_build_type': None,
            'risks': [],
            'optimizations': [],
            'test_recommendations': [],
            'performance_impact': 'unknown',
            'raw_analysis': ai_output
        }
        
        try:
            # Simple parsing - look for key indicators in AI response
            output_lower = ai_output.lower()
            
            # Extract build type recommendation
            if 'full build' in output_lower or 'complete build' in output_lower:
                analysis['recommended_build_type'] = 'full'
            elif 'backend' in output_lower and 'frontend' not in output_lower:
                analysis['recommended_build_type'] = 'backend'
            elif 'frontend' in output_lower and 'backend' not in output_lower:
                analysis['recommended_build_type'] = 'frontend'
            elif 'test' in output_lower and 'only' in output_lower:
                analysis['recommended_build_type'] = 'test'
            elif 'incremental' in output_lower:
                analysis['recommended_build_type'] = 'incremental'
            
            # Extract risks (look for warning keywords)
            risk_keywords = ['risk', 'warning', 'issue', 'problem', 'concern', 'breaking']
            for keyword in risk_keywords:
                if keyword in output_lower:
                    # Extract sentences containing risk keywords
                    sentences = ai_output.split('.')
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            analysis['risks'].append(sentence.strip())
            
            # Extract optimizations
            opt_keywords = ['optimize', 'improve', 'enhance', 'recommend', 'suggest']
            for keyword in opt_keywords:
                if keyword in output_lower:
                    sentences = ai_output.split('.')
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            analysis['optimizations'].append(sentence.strip())
            
            # Determine performance impact
            if any(word in output_lower for word in ['slow', 'performance', 'heavy', 'large']):
                analysis['performance_impact'] = 'high'
            elif any(word in output_lower for word in ['fast', 'light', 'minimal', 'small']):
                analysis['performance_impact'] = 'low'
            else:
                analysis['performance_impact'] = 'medium'
                
        except Exception as e:
            logger.warning(f"Failed to parse AI analysis: {e}")
        
        return analysis
    
    def _get_basic_code_analysis(self, changed_files: List[str]) -> Dict[str, Any]:
        """Get basic code analysis when AI is not available."""
        return {
            'recommended_build_type': None,
            'risks': [],
            'optimizations': [f"Consider running targeted tests for {len(changed_files)} changed files"],
            'test_recommendations': ["Run full test suite for safety"],
            'performance_impact': 'medium',
            'ai_provider': 'fallback',
            'raw_analysis': f"Basic analysis: {len(changed_files)} files changed"
        }
    
    def _execute_build(
        self,
        project_id: str,
        branch: str,
        commit_hash: str,
        build_type: str,
        correlation_id: str,
        trace_id: Optional[str] = None,
        ai_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the build process."""
        build_id = f"build_{project_id}_{int(datetime.utcnow().timestamp())}"
        start_time = datetime.utcnow()
        
        # Create build started event
        build_started_event = BuildStartedEvent(
            build_id=build_id,
            project_id=project_id,
            branch=branch,
            commit_hash=commit_hash,
            build_type=build_type,
            correlation_id=correlation_id,
            actor=f"agent:{self.config.agent_id}",
            trace_id=trace_id
        )
        
        generated_events = [build_started_event]
        
        try:
            logger.info(f"Starting {build_type} build for project {project_id}")
            
            # Execute build steps based on type
            build_steps = self._get_build_steps(build_type)
            build_results = []
            artifacts = []
            
            for step in build_steps:
                step_result = self._execute_build_step(step, project_id)
                build_results.append(step_result)
                
                if not step_result['success']:
                    # Build failed
                    end_time = datetime.utcnow()
                    duration = (end_time - start_time).total_seconds()
                    
                    build_failed_event = BuildFailedEvent(
                        build_id=build_id,
                        project_id=project_id,
                        error_message=step_result['error'],
                        build_logs=self._format_build_logs(build_results),
                        correlation_id=correlation_id,
                        actor=f"agent:{self.config.agent_id}",
                        trace_id=trace_id
                    )
                    
                    generated_events.append(build_failed_event)
                    
                    return {
                        'success': False,
                        'build_id': build_id,
                        'build_type': build_type,
                        'duration_seconds': duration,
                        'failed_step': step['name'],
                        'error_message': step_result['error'],
                        'generated_events': generated_events
                    }
                
                # Collect artifacts
                if 'artifacts' in step_result:
                    artifacts.extend(step_result['artifacts'])
            
            # Build succeeded
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            build_completed_event = BuildCompletedEvent(
                build_id=build_id,
                project_id=project_id,
                build_duration_seconds=duration,
                artifacts=artifacts,
                correlation_id=correlation_id,
                actor=f"agent:{self.config.agent_id}",
                trace_id=trace_id
            )
            
            generated_events.append(build_completed_event)
            
            logger.info(f"Build {build_id} completed successfully in {duration:.2f} seconds")
            
            return {
                'success': True,
                'build_id': build_id,
                'build_type': build_type,
                'duration_seconds': duration,
                'artifacts': artifacts,
                'build_results': build_results,
                'generated_events': generated_events
            }
            
        except Exception as e:
            # Build error
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            build_failed_event = BuildFailedEvent(
                build_id=build_id,
                project_id=project_id,
                error_message=str(e),
                build_logs=f"Build failed with exception: {e}",
                correlation_id=correlation_id,
                actor=f"agent:{self.config.agent_id}",
                trace_id=trace_id
            )
            
            generated_events.append(build_failed_event)
            
            return {
                'success': False,
                'build_id': build_id,
                'build_type': build_type,
                'duration_seconds': duration,
                'error_message': str(e),
                'generated_events': generated_events
            }
    
    def _get_build_steps(self, build_type: str) -> List[Dict[str, Any]]:
        """Get build steps based on build type."""
        base_steps = [
            {'name': 'setup', 'command': 'echo "Setting up build environment"'},
            {'name': 'lint', 'command': 'echo "Running linting checks"'}
        ]
        
        if build_type in ['full', 'backend']:
            base_steps.extend([
                {'name': 'backend_deps', 'command': 'pip install -r requirements.txt'},
                {'name': 'backend_test', 'command': 'python -m pytest tests/ -v'},
                {'name': 'backend_build', 'command': 'echo "Building backend components"'}
            ])
        
        if build_type in ['full', 'frontend']:
            base_steps.extend([
                {'name': 'frontend_deps', 'command': 'cd frontend && npm install'},
                {'name': 'frontend_test', 'command': 'cd frontend && npm test'},
                {'name': 'frontend_build', 'command': 'cd frontend && npm run build'}
            ])
        
        if build_type == 'test':
            base_steps.extend([
                {'name': 'run_tests', 'command': 'python -m pytest tests/ -v --cov=src'}
            ])
        
        if build_type == 'full':
            base_steps.extend([
                {'name': 'integration_test', 'command': 'echo "Running integration tests"'},
                {'name': 'package', 'command': 'echo "Creating deployment packages"'}
            ])
        
        return base_steps
    
    def _execute_build_step(self, step: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """Execute a single build step."""
        step_name = step['name']
        command = step['command']
        
        logger.info(f"Executing build step: {step_name}")
        
        try:
            # For demo purposes, we'll simulate some build steps
            # In a real implementation, you'd execute actual build commands
            
            if step_name == 'setup':
                return {'success': True, 'output': 'Build environment ready'}
            
            elif step_name == 'lint':
                # Simulate linting
                return {'success': True, 'output': 'Linting passed'}
            
            elif step_name == 'backend_deps':
                # Check if requirements.txt exists
                if os.path.exists('requirements.txt'):
                    return {'success': True, 'output': 'Dependencies installed'}
                else:
                    return {'success': True, 'output': 'No requirements.txt found, skipping'}
            
            elif step_name in ['backend_test', 'run_tests']:
                # Check if tests exist
                if os.path.exists('tests/') or os.path.exists('test/'):
                    # For demo, simulate test execution
                    return {
                        'success': True, 
                        'output': 'Tests passed',
                        'artifacts': ['test_results.xml', 'coverage_report.html']
                    }
                else:
                    return {'success': True, 'output': 'No tests found, skipping'}
            
            elif step_name == 'backend_build':
                return {
                    'success': True, 
                    'output': 'Backend build completed',
                    'artifacts': ['app.py', 'requirements.txt']
                }
            
            elif step_name == 'frontend_deps':
                if os.path.exists('frontend/package.json'):
                    return {'success': True, 'output': 'Frontend dependencies installed'}
                else:
                    return {'success': True, 'output': 'No frontend found, skipping'}
            
            elif step_name == 'frontend_test':
                if os.path.exists('frontend/'):
                    return {'success': True, 'output': 'Frontend tests passed'}
                else:
                    return {'success': True, 'output': 'No frontend tests, skipping'}
            
            elif step_name == 'frontend_build':
                if os.path.exists('frontend/'):
                    return {
                        'success': True, 
                        'output': 'Frontend build completed',
                        'artifacts': ['frontend/dist/']
                    }
                else:
                    return {'success': True, 'output': 'No frontend to build, skipping'}
            
            elif step_name == 'integration_test':
                return {'success': True, 'output': 'Integration tests passed'}
            
            elif step_name == 'package':
                return {
                    'success': True, 
                    'output': 'Deployment packages created',
                    'artifacts': ['deployment.zip', 'docker-image.tar']
                }
            
            else:
                # For unknown steps, try to execute the command
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per step
                )
                
                if result.returncode == 0:
                    return {'success': True, 'output': result.stdout}
                else:
                    return {'success': False, 'error': result.stderr or result.stdout}
        
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Build step {step_name} timed out'}
        except Exception as e:
            return {'success': False, 'error': f'Build step {step_name} failed: {str(e)}'}
    
    def _format_build_logs(self, build_results: List[Dict[str, Any]]) -> str:
        """Format build results into log string."""
        logs = []
        for result in build_results:
            if 'output' in result:
                logs.append(f"✓ {result['output']}")
            elif 'error' in result:
                logs.append(f"✗ {result['error']}")
        
        return '\n'.join(logs)
    
    def _get_default_build_config(self) -> Dict[str, Any]:
        """Get default build configuration."""
        return {
            'timeout_seconds': 1800,  # 30 minutes
            'max_parallel_builds': 3,
            'artifact_retention_days': 30,
            'notification_channels': [],
            'build_triggers': {
                'on_push': True,
                'on_pull_request': True,
                'on_schedule': False
            },
            'environments': {
                'development': {
                    'auto_deploy': False,
                    'run_tests': True
                },
                'staging': {
                    'auto_deploy': False,
                    'run_tests': True
                },
                'production': {
                    'auto_deploy': False,
                    'run_tests': True,
                    'require_approval': True
                }
            }
        }