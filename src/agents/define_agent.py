"""
Define Agent - Reacts to spec.frozen events for automatic processing.
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime

from .base import BaseAgent, AgentConfig, EventProcessingResult
from ..events.base import BaseEvent
from ..events.domain_events import SpecFrozenEvent, TasksCreatedEvent
from ..events.event_router import EventBus
from ..services.ai_service import get_ai_service


logger = logging.getLogger(__name__)


class DefineAgent(BaseAgent):
    """Agent that processes frozen specifications and generates implementation tasks using Claude/LLM."""
    
    def __init__(self, event_bus: EventBus, ai_service=None):
        config = AgentConfig(
            agent_id="define_agent",
            name="Define Agent",
            description="Processes frozen specifications and generates implementation tasks using Claude/LLM",
            event_types=["spec.frozen"],
            max_concurrent_events=3,
            timeout_seconds=600.0  # 10 minutes for complex spec processing
        )
        
        super().__init__(config, event_bus)
        self.ai_service = ai_service or get_ai_service()
    
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process spec.frozen events to generate implementation tasks."""
        logger.info(f"DefineAgent processing event {event.metadata.event_id}")
        
        if not isinstance(event, SpecFrozenEvent):
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=0.0,
                error_message="Expected SpecFrozenEvent"
            )
        
        try:
            # Extract spec information
            spec_id = event.aggregate_id
            project_id = event.project_id
            requirements = event.requirements
            design_document = event.design_document
            
            logger.info(f"Processing spec {spec_id} for project {project_id}")
            
            # Generate implementation tasks from the spec
            tasks = self._generate_implementation_tasks(
                spec_id=spec_id,
                project_id=project_id,
                requirements=requirements,
                design_document=design_document
            )
            
            # Create tasks.created event
            tasks_created_event = TasksCreatedEvent(
                task_list_id=f"tasks_{spec_id}_{int(datetime.utcnow().timestamp())}",
                spec_id=spec_id,
                project_id=project_id,
                tasks=tasks,
                correlation_id=event.metadata.correlation_id,
                actor=f"agent:{self.config.agent_id}",
                trace_id=event.metadata.trace_id
            )
            
            result_data = {
                'spec_id': spec_id,
                'project_id': project_id,
                'tasks_generated': len(tasks),
                'task_list_id': tasks_created_event.aggregate_id
            }
            
            logger.info(f"Generated {len(tasks)} tasks for spec {spec_id}")
            
            return EventProcessingResult(
                success=True,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=0.0,  # Will be calculated by base class
                result_data=result_data,
                generated_events=[tasks_created_event]
            )
            
        except Exception as e:
            logger.error(f"DefineAgent failed to process spec.frozen event: {e}")
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=0.0,
                error_message=str(e)
            )
    
    def _generate_implementation_tasks(
        self,
        spec_id: str,
        project_id: str,
        requirements: List[Dict[str, Any]],
        design_document: str
    ) -> List[Dict[str, Any]]:
        """Generate implementation tasks from requirements and design."""
        
        # If AI service is available, use it for intelligent task generation
        if self.ai_service:
            return self._generate_tasks_with_ai(
                spec_id, project_id, requirements, design_document
            )
        
        # Fallback to rule-based task generation
        return self._generate_tasks_rule_based(
            spec_id, project_id, requirements, design_document
        )
    
    def _generate_tasks_with_ai(
        self,
        spec_id: str,
        project_id: str,
        requirements: List[Dict[str, Any]],
        design_document: str
    ) -> List[Dict[str, Any]]:
        """Generate tasks using AI service (Claude/Model Garden) for intelligent analysis."""
        try:
            logger.info(f"Attempting to call AI service to generate tasks for spec {spec_id}")
            
            # Build the prompt for task generation
            prompt = self._build_task_generation_prompt({
                'spec_id': spec_id,
                'project_id': project_id,
                'requirements': requirements,
                'design_document': design_document
            })
            
            # Check if AI service is available
            if not self.ai_service:
                logger.info("No AI service available, using rule-based generation")
                return self._generate_tasks_rule_based(
                    spec_id, project_id, requirements, design_document
                )
            
            ai_response = None
            
            # Try Model Garden first (Claude)
            try:
                logger.info("Attempting task generation with Claude via Model Garden")
                result = self.ai_service.execute_model_garden_task(
                    instruction=prompt,
                    model='claude-sonnet-3.5',  # Use Sonnet as it's more reliable
                    role='developer'
                )
                
                if result['success']:
                    ai_response = result['output']
                    logger.info("✅ Successfully generated tasks using Claude via Model Garden")
                else:
                    logger.warning(f"Model Garden failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.warning(f"Model Garden call failed: {e}")
            
            # Fallback to Goose if Model Garden failed
            if not ai_response:
                try:
                    logger.info("Falling back to Goose for task generation")
                    result = self.ai_service.execute_goose_task(
                        instruction=prompt,
                        role='developer'
                    )
                    
                    if result['success']:
                        ai_response = result['output']
                        logger.info("✅ Successfully generated tasks using Goose")
                    else:
                        logger.warning(f"Goose failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.warning(f"Goose call failed: {e}")
            
            # Parse AI response if we got one
            if ai_response:
                tasks = self._parse_ai_task_response(ai_response)
                if tasks:
                    logger.info(f"🤖 AI generated {len(tasks)} tasks for spec {spec_id}")
                    return tasks
                else:
                    logger.warning("AI response could not be parsed into valid tasks")
            
            # If AI failed, fall back to rule-based generation
            logger.info("🔄 AI task generation failed, falling back to rule-based approach")
            return self._generate_tasks_rule_based(
                spec_id, project_id, requirements, design_document
            )
            
        except Exception as e:
            logger.error(f"AI task generation failed with exception: {e}")
            logger.info("🔄 Falling back to rule-based task generation")
            return self._generate_tasks_rule_based(
                spec_id, project_id, requirements, design_document
            )
    
    def _generate_tasks_rule_based(
        self,
        spec_id: str,
        project_id: str,
        requirements: List[Dict[str, Any]],
        design_document: str
    ) -> List[Dict[str, Any]]:
        """Generate tasks using rule-based approach."""
        tasks = []
        task_counter = 1
        
        # Analyze requirements to generate tasks
        for requirement in requirements:
            req_id = requirement.get('id', f'req_{task_counter}')
            user_story = requirement.get('user_story', '')
            acceptance_criteria = requirement.get('acceptance_criteria', [])
            
            # Generate tasks based on requirement type and complexity
            if 'database' in user_story.lower() or 'data' in user_story.lower():
                tasks.extend(self._generate_database_tasks(req_id, requirement, task_counter))
                task_counter += len(tasks)
            
            if 'api' in user_story.lower() or 'endpoint' in user_story.lower():
                tasks.extend(self._generate_api_tasks(req_id, requirement, task_counter))
                task_counter += len(tasks)
            
            if 'ui' in user_story.lower() or 'interface' in user_story.lower():
                tasks.extend(self._generate_ui_tasks(req_id, requirement, task_counter))
                task_counter += len(tasks)
            
            if 'test' in user_story.lower() or any('test' in criteria.lower() for criteria in acceptance_criteria):
                tasks.extend(self._generate_testing_tasks(req_id, requirement, task_counter))
                task_counter += len(tasks)
        
        # Add integration and deployment tasks
        tasks.extend(self._generate_integration_tasks(spec_id, project_id, task_counter))
        
        return tasks
    
    def _generate_database_tasks(self, req_id: str, requirement: Dict[str, Any], start_counter: int) -> List[Dict[str, Any]]:
        """Generate database-related tasks."""
        return [
            {
                'id': f'task_{start_counter}',
                'title': f'Design database schema for {req_id}',
                'description': f'Create database models and relationships for: {requirement.get("user_story", "")}',
                'type': 'database',
                'priority': 'high',
                'estimated_hours': 4,
                'requirements': [req_id],
                'dependencies': []
            },
            {
                'id': f'task_{start_counter + 1}',
                'title': f'Implement database migrations for {req_id}',
                'description': 'Create migration scripts for schema changes',
                'type': 'database',
                'priority': 'high',
                'estimated_hours': 2,
                'requirements': [req_id],
                'dependencies': [f'task_{start_counter}']
            }
        ]
    
    def _generate_api_tasks(self, req_id: str, requirement: Dict[str, Any], start_counter: int) -> List[Dict[str, Any]]:
        """Generate API-related tasks."""
        return [
            {
                'id': f'task_{start_counter}',
                'title': f'Implement API endpoints for {req_id}',
                'description': f'Create REST API endpoints for: {requirement.get("user_story", "")}',
                'type': 'api',
                'priority': 'high',
                'estimated_hours': 6,
                'requirements': [req_id],
                'dependencies': []
            },
            {
                'id': f'task_{start_counter + 1}',
                'title': f'Add API validation for {req_id}',
                'description': 'Implement request/response validation and error handling',
                'type': 'api',
                'priority': 'medium',
                'estimated_hours': 3,
                'requirements': [req_id],
                'dependencies': [f'task_{start_counter}']
            }
        ]
    
    def _generate_ui_tasks(self, req_id: str, requirement: Dict[str, Any], start_counter: int) -> List[Dict[str, Any]]:
        """Generate UI-related tasks."""
        return [
            {
                'id': f'task_{start_counter}',
                'title': f'Create UI components for {req_id}',
                'description': f'Implement user interface for: {requirement.get("user_story", "")}',
                'type': 'frontend',
                'priority': 'medium',
                'estimated_hours': 8,
                'requirements': [req_id],
                'dependencies': []
            },
            {
                'id': f'task_{start_counter + 1}',
                'title': f'Add UI interactions for {req_id}',
                'description': 'Implement user interactions and state management',
                'type': 'frontend',
                'priority': 'medium',
                'estimated_hours': 4,
                'requirements': [req_id],
                'dependencies': [f'task_{start_counter}']
            }
        ]
    
    def _generate_testing_tasks(self, req_id: str, requirement: Dict[str, Any], start_counter: int) -> List[Dict[str, Any]]:
        """Generate testing-related tasks."""
        return [
            {
                'id': f'task_{start_counter}',
                'title': f'Write unit tests for {req_id}',
                'description': f'Create comprehensive unit tests for: {requirement.get("user_story", "")}',
                'type': 'testing',
                'priority': 'high',
                'estimated_hours': 4,
                'requirements': [req_id],
                'dependencies': []
            },
            {
                'id': f'task_{start_counter + 1}',
                'title': f'Write integration tests for {req_id}',
                'description': 'Create integration tests for end-to-end functionality',
                'type': 'testing',
                'priority': 'medium',
                'estimated_hours': 6,
                'requirements': [req_id],
                'dependencies': [f'task_{start_counter}']
            }
        ]
    
    def _generate_integration_tasks(self, spec_id: str, project_id: str, start_counter: int) -> List[Dict[str, Any]]:
        """Generate integration and deployment tasks."""
        return [
            {
                'id': f'task_{start_counter}',
                'title': 'Integration testing',
                'description': 'Test all components working together',
                'type': 'integration',
                'priority': 'high',
                'estimated_hours': 8,
                'requirements': ['all'],
                'dependencies': []
            },
            {
                'id': f'task_{start_counter + 1}',
                'title': 'Performance optimization',
                'description': 'Optimize performance and resource usage',
                'type': 'optimization',
                'priority': 'medium',
                'estimated_hours': 6,
                'requirements': ['all'],
                'dependencies': [f'task_{start_counter}']
            },
            {
                'id': f'task_{start_counter + 2}',
                'title': 'Documentation',
                'description': 'Create technical documentation and user guides',
                'type': 'documentation',
                'priority': 'medium',
                'estimated_hours': 4,
                'requirements': ['all'],
                'dependencies': [f'task_{start_counter + 1}']
            }
        ]
    
    def _build_task_generation_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for AI task generation."""
        return f"""
        Generate implementation tasks for the following specification:
        
        Project ID: {context['project_id']}
        Spec ID: {context['spec_id']}
        
        Requirements:
        {json.dumps(context['requirements'], indent=2)}
        
        Design Document:
        {context['design_document']}
        
        Please generate a comprehensive list of implementation tasks that:
        1. Cover all requirements with specific, actionable tasks
        2. Include proper task dependencies and sequencing
        3. Estimate effort in hours for each task
        4. Categorize tasks by type (database, api, frontend, testing, etc.)
        5. Prioritize tasks appropriately
        6. Follow test-driven development practices
        
        Return the tasks as a JSON array with the following structure:
        {{
            "id": "task_1",
            "title": "Task title",
            "description": "Detailed description",
            "type": "task_type",
            "priority": "high|medium|low",
            "estimated_hours": 4,
            "requirements": ["req_1", "req_2"],
            "dependencies": ["task_0"]
        }}
        """
    
    def _parse_ai_task_response(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse AI response into structured tasks."""
        try:
            # Try to extract JSON from AI response
            if '```json' in ai_response:
                json_start = ai_response.find('```json') + 7
                json_end = ai_response.find('```', json_start)
                json_str = ai_response[json_start:json_end].strip()
            else:
                json_str = ai_response.strip()
            
            tasks = json.loads(json_str)
            
            # Validate task structure
            validated_tasks = []
            for i, task in enumerate(tasks):
                if isinstance(task, dict) and 'title' in task:
                    # Ensure required fields
                    validated_task = {
                        'id': task.get('id', f'ai_task_{i}'),
                        'title': task['title'],
                        'description': task.get('description', ''),
                        'type': task.get('type', 'general'),
                        'priority': task.get('priority', 'medium'),
                        'estimated_hours': task.get('estimated_hours', 4),
                        'requirements': task.get('requirements', []),
                        'dependencies': task.get('dependencies', [])
                    }
                    validated_tasks.append(validated_task)
            
            return validated_tasks
            
        except Exception as e:
            logger.error(f"Failed to parse AI task response: {e}")
            # Return empty list, will fall back to rule-based generation
            return []