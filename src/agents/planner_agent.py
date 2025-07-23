"""
Planner Agent - Intelligent task breakdown and resource assignment
"""

import logging
import re
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from .base import BaseAgent, AgentConfig, EventProcessingResult
    from ..events.base import BaseEvent
    from ..events.domain_events import TasksCreatedEvent, SpecFrozenEvent
    from ..events.event_router import EventBus
    from ..models.specification_artifact import SpecificationArtifact, ArtifactType
    from ..models.task import Task, TaskPriority
    from ..models.base import db
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from agents.base import BaseAgent, AgentConfig, EventProcessingResult
    from events.base import BaseEvent
    from events.domain_events import TasksCreatedEvent, SpecFrozenEvent
    from events.event_router import EventBus
    from models.specification_artifact import SpecificationArtifact, ArtifactType
    from models.task import Task, TaskPriority
    from models.base import db


logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Planner Agent that subscribes to spec.frozen events and creates actionable tasks
    with intelligent resource assignment and dependency analysis.
    """
    
    def __init__(self, config: AgentConfig, event_bus: EventBus):
        super().__init__(config, event_bus)
        self.task_parsing_patterns = self._initialize_parsing_patterns()
        self.effort_estimation_rules = self._initialize_effort_rules()
        self.expertise_keywords = self._initialize_expertise_keywords()
    
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process incoming events."""
        try:
            if isinstance(event, SpecFrozenEvent):
                return self._handle_spec_frozen(event)
            else:
                logger.debug(f"PlannerAgent ignoring event type: {event.get_event_type()}")
                return EventProcessingResult(
                    success=True,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=0.0
                )
        
        except Exception as e:
            logger.error(f"PlannerAgent failed to process event {event.metadata.event_id}: {e}")
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=0.0,
                error_message=str(e)
            )
    
    def _handle_spec_frozen(self, event: SpecFrozenEvent) -> EventProcessingResult:
        """Handle spec.frozen event by parsing tasks and creating task records."""
        start_time = datetime.utcnow()
        
        try:
            spec_id = event.aggregate_id
            project_id = event.project_id
            
            logger.info(f"PlannerAgent processing spec.frozen for spec {spec_id}")
            
            # Get the tasks.md artifact
            tasks_artifact = SpecificationArtifact.query.filter_by(
                spec_id=spec_id,
                artifact_type=ArtifactType.TASKS
            ).first()
            
            if not tasks_artifact:
                logger.warning(f"No tasks artifact found for spec {spec_id}")
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    error_message="No tasks artifact found"
                )
            
            # Parse tasks from tasks.md content
            parsed_tasks = self._parse_tasks_from_markdown(tasks_artifact.content, spec_id, project_id)
            
            if not parsed_tasks:
                logger.warning(f"No tasks parsed from spec {spec_id}")
                return EventProcessingResult(
                    success=False,
                    agent_id=self.config.agent_id,
                    event_id=event.metadata.event_id,
                    event_type=event.get_event_type(),
                    processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    error_message="No tasks could be parsed"
                )
            
            # Get project context for owner suggestions
            project_context = self.get_project_context(project_id)
            
            # Enhance tasks with effort estimation and owner suggestions
            enhanced_tasks = []
            for task_data in parsed_tasks:
                enhanced_task = self._enhance_task_with_intelligence(task_data, project_context)
                enhanced_tasks.append(enhanced_task)
            
            # Create task records in database
            created_tasks = []
            for task_data in enhanced_tasks:
                try:
                    task = Task.create_task(
                        spec_id=spec_id,
                        project_id=project_id,
                        task_data=task_data,
                        created_by=self.config.agent_id
                    )
                    created_tasks.append(task)
                except Exception as e:
                    logger.error(f"Failed to create task {task_data.get('task_number')}: {e}")
            
            # Commit all tasks
            db.session.commit()
            
            # Analyze dependencies and relationships
            self._analyze_task_relationships(created_tasks)
            db.session.commit()
            
            # Create tasks.created event
            task_list_id = f"tasklist_{spec_id}_{int(datetime.utcnow().timestamp())}"
            tasks_created_event = TasksCreatedEvent(
                task_list_id=task_list_id,
                spec_id=spec_id,
                project_id=project_id,
                tasks=[task.to_dict() for task in created_tasks],
                correlation_id=event.metadata.correlation_id,
                trace_id=event.metadata.trace_id
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"PlannerAgent created {len(created_tasks)} tasks for spec {spec_id}")
            
            return EventProcessingResult(
                success=True,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=processing_time,
                result_data={
                    'spec_id': spec_id,
                    'tasks_created': len(created_tasks),
                    'task_list_id': task_list_id
                },
                generated_events=[tasks_created_event]
            )
        
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"PlannerAgent failed to process spec.frozen: {e}")
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=processing_time,
                error_message=str(e)
            )
    
    def _parse_tasks_from_markdown(self, markdown_content: str, spec_id: str, project_id: str) -> List[Dict[str, Any]]:
        """Parse tasks from markdown content using regex patterns."""
        tasks = []
        lines = markdown_content.split('\n')
        current_task = None
        
        for line in lines:
            line = line.strip()
            
            # Match task items: - [ ] 1.1 Task title
            task_match = re.match(r'^-\s*\[\s*[x\-\s]*\]\s*(\d+(?:\.\d+)?)\s+(.+)$', line)
            if task_match:
                # Save previous task if exists
                if current_task:
                    tasks.append(current_task)
                
                task_number = task_match.group(1)
                task_title = task_match.group(2).strip()
                
                current_task = {
                    'task_number': task_number,
                    'title': task_title,
                    'description': '',
                    'requirements_refs': [],
                    'details': []
                }
                continue
            
            # Match sub-bullets with details
            detail_match = re.match(r'^[\s]*[-\*]\s*(.+)$', line)
            if detail_match and current_task:
                detail = detail_match.group(1).strip()
                current_task['details'].append(detail)
                
                # Extract requirements references
                req_match = re.search(r'_Requirements?:\s*([0-9\.,\s]+)_', detail)
                if req_match:
                    req_refs = [ref.strip() for ref in req_match.group(1).split(',')]
                    current_task['requirements_refs'].extend(req_refs)
                continue
            
            # Add to description if we're in a task context
            if current_task and line and not line.startswith('#'):
                if current_task['description']:
                    current_task['description'] += '\n' + line
                else:
                    current_task['description'] = line
        
        # Don't forget the last task
        if current_task:
            tasks.append(current_task)
        
        # Post-process tasks
        processed_tasks = []
        for task in tasks:
            # Combine details into description
            if task['details']:
                details_text = '\n'.join(f"- {detail}" for detail in task['details'])
                if task['description']:
                    task['description'] += '\n\n' + details_text
                else:
                    task['description'] = details_text
            
            # Determine if this is a parent task or subtask
            task_parts = task['task_number'].split('.')
            if len(task_parts) > 1:
                # This is a subtask
                parent_number = task_parts[0]
                task['parent_task_id'] = f"{spec_id}_{parent_number}"
            
            processed_tasks.append(task)
        
        logger.info(f"Parsed {len(processed_tasks)} tasks from markdown")
        return processed_tasks
    
    def _enhance_task_with_intelligence(self, task_data: Dict[str, Any], project_context) -> Dict[str, Any]:
        """Enhance task with effort estimation and owner suggestions."""
        enhanced_task = task_data.copy()
        
        # Estimate effort based on task content
        effort_hours = self._estimate_task_effort(task_data)
        enhanced_task['effort_estimate_hours'] = effort_hours
        
        # Suggest owner based on task content and team expertise
        owner_suggestion = self._suggest_task_owner(task_data, project_context)
        if owner_suggestion:
            enhanced_task['suggested_owner'] = owner_suggestion['owner']
            enhanced_task['assignment_confidence'] = owner_suggestion['confidence']
        
        # Determine priority based on task content
        priority = self._determine_task_priority(task_data)
        enhanced_task['priority'] = priority
        
        # Extract related components and files
        components = self._extract_related_components(task_data, project_context)
        enhanced_task['related_components'] = components
        
        return enhanced_task
    
    def _estimate_task_effort(self, task_data: Dict[str, Any]) -> float:
        """Estimate task effort in hours based on content analysis."""
        title = task_data.get('title', '').lower()
        description = task_data.get('description', '').lower()
        content = f"{title} {description}"
        
        base_effort = 2.0  # Default 2 hours
        
        # Apply effort rules
        for pattern, multiplier in self.effort_estimation_rules.items():
            if re.search(pattern, content, re.IGNORECASE):
                base_effort *= multiplier
        
        # Adjust based on task complexity indicators
        complexity_indicators = [
            'implement', 'create', 'build', 'develop', 'design',
            'integrate', 'test', 'deploy', 'configure'
        ]
        
        complexity_count = sum(1 for indicator in complexity_indicators if indicator in content)
        if complexity_count > 2:
            base_effort *= 1.5
        
        # Adjust for subtasks (usually smaller)
        if '.' in task_data.get('task_number', ''):
            base_effort *= 0.7
        
        # Round to reasonable increments
        if base_effort < 1:
            return 0.5
        elif base_effort < 4:
            return round(base_effort * 2) / 2  # Round to 0.5 hour increments
        else:
            return round(base_effort)  # Round to hour increments
    
    def _suggest_task_owner(self, task_data: Dict[str, Any], project_context) -> Optional[Dict[str, Any]]:
        """Suggest task owner based on content analysis and team expertise."""
        title = task_data.get('title', '').lower()
        description = task_data.get('description', '').lower()
        content = f"{title} {description}"
        
        # Analyze content for expertise areas
        expertise_scores = {}
        for expertise, keywords in self.expertise_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > 0:
                expertise_scores[expertise] = score
        
        if not expertise_scores:
            return None
        
        # Find the highest scoring expertise area
        top_expertise = max(expertise_scores, key=expertise_scores.get)
        confidence = min(expertise_scores[top_expertise] / 5.0, 1.0)  # Max confidence of 1.0
        
        # Map expertise to team members (simplified - in real implementation,
        # this would use Git blame analysis and team expertise graphs)
        expertise_to_owner = {
            'frontend': 'frontend-dev',
            'backend': 'backend-dev',
            'database': 'backend-dev',
            'testing': 'qa-engineer',
            'devops': 'devops-engineer',
            'design': 'ui-designer',
            'documentation': 'tech-writer'
        }
        
        suggested_owner = expertise_to_owner.get(top_expertise, 'backend-dev')
        
        return {
            'owner': suggested_owner,
            'confidence': confidence,
            'expertise_area': top_expertise,
            'reasoning': f"Task content matches {top_expertise} expertise"
        }
    
    def _determine_task_priority(self, task_data: Dict[str, Any]) -> str:
        """Determine task priority based on content analysis."""
        title = task_data.get('title', '').lower()
        description = task_data.get('description', '').lower()
        content = f"{title} {description}"
        
        # High priority indicators
        high_priority_keywords = [
            'critical', 'urgent', 'security', 'bug', 'fix', 'error',
            'authentication', 'authorization', 'data loss', 'performance'
        ]
        
        # Low priority indicators
        low_priority_keywords = [
            'documentation', 'comment', 'cleanup', 'refactor',
            'optimization', 'enhancement', 'nice to have'
        ]
        
        if any(keyword in content for keyword in high_priority_keywords):
            return TaskPriority.HIGH.value
        elif any(keyword in content for keyword in low_priority_keywords):
            return TaskPriority.LOW.value
        else:
            return TaskPriority.MEDIUM.value
    
    def _extract_related_components(self, task_data: Dict[str, Any], project_context) -> List[str]:
        """Extract related system components from task content."""
        title = task_data.get('title', '').lower()
        description = task_data.get('description', '').lower()
        content = f"{title} {description}"
        
        components = []
        
        # Common component patterns
        component_patterns = {
            'api': ['api', 'endpoint', 'rest', 'graphql'],
            'database': ['database', 'db', 'sql', 'query', 'migration'],
            'frontend': ['ui', 'component', 'react', 'vue', 'angular'],
            'authentication': ['auth', 'login', 'jwt', 'token', 'session'],
            'notification': ['notification', 'email', 'slack', 'webhook'],
            'storage': ['storage', 'file', 'upload', 's3', 'blob'],
            'monitoring': ['monitoring', 'metrics', 'logging', 'alert']
        }
        
        for component, keywords in component_patterns.items():
            if any(keyword in content for keyword in keywords):
                components.append(component)
        
        return components
    
    def _analyze_task_relationships(self, tasks: List[Task]) -> None:
        """Analyze and set up task dependencies and relationships."""
        # Create a mapping of task numbers to task objects
        task_map = {task.task_number: task for task in tasks}
        
        for task in tasks:
            dependencies = []
            blocks = []
            
            # Analyze task number patterns for dependencies
            if task.task_number:
                task_parts = task.task_number.split('.')
                
                if len(task_parts) > 1:
                    # Subtask depends on parent task
                    parent_number = task_parts[0]
                    if parent_number in task_map:
                        dependencies.append(task_map[parent_number].id)
                
                # Sequential dependencies (task 2 depends on task 1)
                try:
                    current_num = float(task.task_number)
                    prev_num = str(int(current_num - 1))
                    if prev_num in task_map and prev_num != task.task_number:
                        dependencies.append(task_map[prev_num].id)
                except (ValueError, TypeError):
                    pass
            
            # Analyze content for explicit dependencies
            content = f"{task.title} {task.description}".lower()
            dependency_keywords = [
                'after', 'once', 'requires', 'depends on', 'following',
                'prerequisite', 'must complete'
            ]
            
            if any(keyword in content for keyword in dependency_keywords):
                # In a real implementation, this would use NLP to extract
                # specific task references
                pass
            
            # Update task dependencies
            if dependencies:
                task.depends_on = dependencies
            if blocks:
                task.blocks = blocks
    
    def _initialize_parsing_patterns(self) -> Dict[str, str]:
        """Initialize regex patterns for task parsing."""
        return {
            'task_item': r'^-\s*\[\s*[x\-\s]*\]\s*(\d+(?:\.\d+)?)\s+(.+)$',
            'sub_item': r'^[\s]*[-\*]\s*(.+)$',
            'requirements_ref': r'_Requirements?:\s*([0-9\.,\s]+)_',
            'completion_ref': r'_Completion:\s*(.+)_'
        }
    
    def _initialize_effort_rules(self) -> Dict[str, float]:
        """Initialize effort estimation rules."""
        return {
            r'\b(setup|configure|install)\b': 1.5,
            r'\b(implement|create|build|develop)\b': 2.0,
            r'\b(integrate|connect|sync)\b': 2.5,
            r'\b(test|testing|unit test|integration test)\b': 1.5,
            r'\b(deploy|deployment|production)\b': 2.0,
            r'\b(database|migration|schema)\b': 2.5,
            r'\b(api|endpoint|service)\b': 2.0,
            r'\b(ui|interface|component)\b': 1.8,
            r'\b(security|authentication|authorization)\b': 3.0,
            r'\b(monitoring|logging|metrics)\b': 1.5,
            r'\b(documentation|docs|readme)\b': 1.0,
            r'\b(refactor|cleanup|optimization)\b': 1.2
        }
    
    def _initialize_expertise_keywords(self) -> Dict[str, List[str]]:
        """Initialize expertise area keywords for owner suggestions."""
        return {
            'frontend': [
                'ui', 'interface', 'component', 'react', 'vue', 'angular',
                'css', 'html', 'javascript', 'typescript', 'styling'
            ],
            'backend': [
                'api', 'server', 'service', 'endpoint', 'business logic',
                'python', 'java', 'node', 'flask', 'django'
            ],
            'database': [
                'database', 'db', 'sql', 'query', 'migration', 'schema',
                'postgresql', 'mysql', 'mongodb', 'redis'
            ],
            'testing': [
                'test', 'testing', 'unit test', 'integration test',
                'e2e', 'qa', 'quality', 'validation'
            ],
            'devops': [
                'deploy', 'deployment', 'ci/cd', 'docker', 'kubernetes',
                'infrastructure', 'monitoring', 'logging'
            ],
            'design': [
                'design', 'ux', 'ui', 'mockup', 'wireframe',
                'figma', 'sketch', 'prototype'
            ],
            'documentation': [
                'documentation', 'docs', 'readme', 'guide',
                'manual', 'wiki', 'specification'
            ]
        }


def create_planner_agent(event_bus: EventBus) -> PlannerAgent:
    """Create and configure a Planner Agent."""
    config = AgentConfig(
        agent_id="planner_agent",
        name="Planner Agent",
        description="Intelligent task breakdown and resource assignment agent",
        event_types=["spec.frozen"],
        max_concurrent_events=3,
        retry_attempts=2,
        timeout_seconds=180,  # 3 minutes
        enable_dead_letter_queue=True
    )
    
    return PlannerAgent(config, event_bus)