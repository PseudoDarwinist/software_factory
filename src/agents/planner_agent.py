"""
Planner Agent - Triggers on tasks.created events for resource planning.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from .base import BaseAgent, AgentConfig, EventProcessingResult
from ..events.base import BaseEvent
from ..events.domain_events import TasksCreatedEvent, ProjectUpdatedEvent
from ..events.event_router import EventBus


logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Agent that analyzes created tasks and performs resource planning."""
    
    def __init__(self, event_bus: EventBus):
        config = AgentConfig(
            agent_id="planner_agent",
            name="Planner Agent",
            description="Analyzes tasks and performs resource planning and scheduling",
            event_types=["tasks.created"],
            max_concurrent_events=2,
            timeout_seconds=300.0  # 5 minutes for planning analysis
        )
        
        super().__init__(config, event_bus)
    
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process tasks.created events to perform resource planning."""
        logger.info(f"PlannerAgent processing event {event.metadata.event_id}")
        
        if not isinstance(event, TasksCreatedEvent):
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=0.0,
                error_message="Expected TasksCreatedEvent"
            )
        
        try:
            # Extract task information
            task_list_id = event.aggregate_id
            spec_id = event.spec_id
            project_id = event.project_id
            tasks = event.tasks
            
            logger.info(f"Planning resources for {len(tasks)} tasks in project {project_id}")
            
            # Perform resource planning analysis
            planning_result = self._analyze_and_plan_tasks(
                task_list_id=task_list_id,
                spec_id=spec_id,
                project_id=project_id,
                tasks=tasks
            )
            
            # Create project update event with planning information
            project_update_event = ProjectUpdatedEvent(
                project_id=project_id,
                changes={
                    'planning_analysis': planning_result,
                    'last_planned_at': datetime.utcnow().isoformat(),
                    'task_list_id': task_list_id
                },
                correlation_id=event.metadata.correlation_id,
                actor=f"agent:{self.config.agent_id}",
                trace_id=event.metadata.trace_id
            )
            
            result_data = {
                'project_id': project_id,
                'task_list_id': task_list_id,
                'total_tasks': len(tasks),
                'planning_summary': planning_result['summary']
            }
            
            logger.info(f"Completed resource planning for project {project_id}")
            
            return EventProcessingResult(
                success=True,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=0.0,  # Will be calculated by base class
                result_data=result_data,
                generated_events=[project_update_event]
            )
            
        except Exception as e:
            logger.error(f"PlannerAgent failed to process tasks.created event: {e}")
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=0.0,
                error_message=str(e)
            )
    
    def _analyze_and_plan_tasks(
        self,
        task_list_id: str,
        spec_id: str,
        project_id: str,
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze tasks and create resource planning."""
        
        # Analyze task dependencies
        dependency_analysis = self._analyze_dependencies(tasks)
        
        # Estimate timeline
        timeline_analysis = self._estimate_timeline(tasks, dependency_analysis)
        
        # Analyze resource requirements
        resource_analysis = self._analyze_resource_requirements(tasks)
        
        # Identify critical path
        critical_path = self._identify_critical_path(tasks, dependency_analysis, timeline_analysis)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            tasks, dependency_analysis, timeline_analysis, resource_analysis, critical_path
        )
        
        return {
            'task_list_id': task_list_id,
            'spec_id': spec_id,
            'project_id': project_id,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_tasks': len(tasks),
                'estimated_total_hours': timeline_analysis['total_hours'],
                'estimated_duration_days': timeline_analysis['duration_days'],
                'critical_path_tasks': len(critical_path),
                'resource_types_needed': len(resource_analysis['resource_types']),
                'high_priority_tasks': len([t for t in tasks if t.get('priority') == 'high'])
            },
            'dependency_analysis': dependency_analysis,
            'timeline_analysis': timeline_analysis,
            'resource_analysis': resource_analysis,
            'critical_path': critical_path,
            'recommendations': recommendations
        }
    
    def _analyze_dependencies(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze task dependencies and identify potential issues."""
        task_map = {task['id']: task for task in tasks}
        dependency_graph = {}
        circular_dependencies = []
        orphaned_tasks = []
        
        # Build dependency graph
        for task in tasks:
            task_id = task['id']
            dependencies = task.get('dependencies', [])
            dependency_graph[task_id] = dependencies
            
            # Check for missing dependencies
            missing_deps = [dep for dep in dependencies if dep not in task_map]
            if missing_deps:
                logger.warning(f"Task {task_id} has missing dependencies: {missing_deps}")
        
        # Detect circular dependencies
        def has_circular_dependency(task_id, visited, rec_stack):
            visited.add(task_id)
            rec_stack.add(task_id)
            
            for dep in dependency_graph.get(task_id, []):
                if dep in task_map:  # Only check existing dependencies
                    if dep not in visited:
                        if has_circular_dependency(dep, visited, rec_stack):
                            return True
                    elif dep in rec_stack:
                        circular_dependencies.append((task_id, dep))
                        return True
            
            rec_stack.remove(task_id)
            return False
        
        visited = set()
        for task_id in dependency_graph:
            if task_id not in visited:
                has_circular_dependency(task_id, visited, set())
        
        # Find orphaned tasks (no dependencies and no dependents)
        has_dependents = set()
        for deps in dependency_graph.values():
            has_dependents.update(deps)
        
        for task in tasks:
            task_id = task['id']
            if not dependency_graph.get(task_id) and task_id not in has_dependents:
                orphaned_tasks.append(task_id)
        
        return {
            'dependency_graph': dependency_graph,
            'circular_dependencies': circular_dependencies,
            'orphaned_tasks': orphaned_tasks,
            'total_dependencies': sum(len(deps) for deps in dependency_graph.values())
        }
    
    def _estimate_timeline(self, tasks: List[Dict[str, Any]], dependency_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate project timeline based on tasks and dependencies."""
        task_map = {task['id']: task for task in tasks}
        dependency_graph = dependency_analysis['dependency_graph']
        
        # Calculate earliest start times using topological sort
        earliest_start = {}
        earliest_finish = {}
        
        def calculate_earliest_times(task_id):
            if task_id in earliest_start:
                return earliest_finish[task_id]
            
            task = task_map.get(task_id)
            if not task:
                return 0
            
            estimated_hours = task.get('estimated_hours', 4)
            dependencies = dependency_graph.get(task_id, [])
            
            if not dependencies:
                earliest_start[task_id] = 0
            else:
                max_finish = 0
                for dep in dependencies:
                    if dep in task_map:
                        dep_finish = calculate_earliest_times(dep)
                        max_finish = max(max_finish, dep_finish)
                earliest_start[task_id] = max_finish
            
            earliest_finish[task_id] = earliest_start[task_id] + estimated_hours
            return earliest_finish[task_id]
        
        # Calculate for all tasks
        for task_id in task_map:
            calculate_earliest_times(task_id)
        
        total_hours = sum(task.get('estimated_hours', 4) for task in tasks)
        max_finish_time = max(earliest_finish.values()) if earliest_finish else 0
        
        # Estimate duration in days (assuming 8 hours per day, accounting for parallelization)
        duration_days = max_finish_time / 8 if max_finish_time > 0 else total_hours / 8
        
        return {
            'total_hours': total_hours,
            'duration_days': duration_days,
            'max_finish_time': max_finish_time,
            'earliest_start_times': earliest_start,
            'earliest_finish_times': earliest_finish,
            'parallelization_factor': total_hours / max_finish_time if max_finish_time > 0 else 1
        }
    
    def _analyze_resource_requirements(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze resource requirements by task type and skill."""
        resource_types = {}
        skill_requirements = {}
        priority_distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for task in tasks:
            task_type = task.get('type', 'general')
            priority = task.get('priority', 'medium')
            estimated_hours = task.get('estimated_hours', 4)
            
            # Count by type
            if task_type not in resource_types:
                resource_types[task_type] = {'count': 0, 'total_hours': 0}
            resource_types[task_type]['count'] += 1
            resource_types[task_type]['total_hours'] += estimated_hours
            
            # Map task types to skill requirements
            skills = self._map_task_type_to_skills(task_type)
            for skill in skills:
                if skill not in skill_requirements:
                    skill_requirements[skill] = {'count': 0, 'total_hours': 0}
                skill_requirements[skill]['count'] += 1
                skill_requirements[skill]['total_hours'] += estimated_hours
            
            # Priority distribution
            priority_distribution[priority] += 1
        
        return {
            'resource_types': resource_types,
            'skill_requirements': skill_requirements,
            'priority_distribution': priority_distribution,
            'peak_resource_needs': self._calculate_peak_resource_needs(tasks)
        }
    
    def _map_task_type_to_skills(self, task_type: str) -> List[str]:
        """Map task types to required skills."""
        skill_mapping = {
            'database': ['database_design', 'sql', 'data_modeling'],
            'api': ['backend_development', 'rest_api', 'python'],
            'frontend': ['frontend_development', 'javascript', 'ui_design'],
            'testing': ['test_automation', 'quality_assurance'],
            'integration': ['system_integration', 'devops'],
            'documentation': ['technical_writing'],
            'optimization': ['performance_tuning', 'system_architecture'],
            'general': ['software_development']
        }
        
        return skill_mapping.get(task_type, ['software_development'])
    
    def _calculate_peak_resource_needs(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate peak resource needs over time."""
        # This is a simplified calculation
        # In a real implementation, you'd analyze the timeline more carefully
        
        type_counts = {}
        for task in tasks:
            task_type = task.get('type', 'general')
            type_counts[task_type] = type_counts.get(task_type, 0) + 1
        
        # Assume 30% of tasks of each type might run in parallel at peak
        peak_parallel_factor = 0.3
        peak_needs = {}
        
        for task_type, count in type_counts.items():
            peak_needs[task_type] = max(1, int(count * peak_parallel_factor))
        
        return peak_needs
    
    def _identify_critical_path(
        self,
        tasks: List[Dict[str, Any]],
        dependency_analysis: Dict[str, Any],
        timeline_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identify the critical path through the project."""
        task_map = {task['id']: task for task in tasks}
        earliest_finish = timeline_analysis['earliest_finish_times']
        dependency_graph = dependency_analysis['dependency_graph']
        
        # Find the task with the latest finish time
        if not earliest_finish:
            return []
        
        max_finish_time = max(earliest_finish.values())
        critical_tasks = []
        
        # Find tasks that finish at the maximum time
        end_tasks = [task_id for task_id, finish_time in earliest_finish.items() 
                    if finish_time == max_finish_time]
        
        # Trace back through dependencies to find critical path
        def trace_critical_path(task_id, path):
            if task_id in path:  # Avoid cycles
                return
            
            path.append(task_id)
            dependencies = dependency_graph.get(task_id, [])
            
            if dependencies:
                # Find the dependency with the latest finish time
                latest_dep = max(dependencies, 
                               key=lambda dep: earliest_finish.get(dep, 0),
                               default=None)
                if latest_dep and latest_dep in task_map:
                    trace_critical_path(latest_dep, path)
        
        # Trace from each end task
        for end_task in end_tasks:
            path = []
            trace_critical_path(end_task, path)
            critical_tasks.extend(path)
        
        # Remove duplicates while preserving order
        seen = set()
        critical_path = []
        for task_id in critical_tasks:
            if task_id not in seen:
                critical_path.append(task_id)
                seen.add(task_id)
        
        return critical_path
    
    def _generate_recommendations(
        self,
        tasks: List[Dict[str, Any]],
        dependency_analysis: Dict[str, Any],
        timeline_analysis: Dict[str, Any],
        resource_analysis: Dict[str, Any],
        critical_path: List[str]
    ) -> List[Dict[str, str]]:
        """Generate planning recommendations based on analysis."""
        recommendations = []
        
        # Dependency recommendations
        if dependency_analysis['circular_dependencies']:
            recommendations.append({
                'type': 'warning',
                'category': 'dependencies',
                'message': f"Found {len(dependency_analysis['circular_dependencies'])} circular dependencies that need to be resolved"
            })
        
        if dependency_analysis['orphaned_tasks']:
            recommendations.append({
                'type': 'info',
                'category': 'dependencies',
                'message': f"Found {len(dependency_analysis['orphaned_tasks'])} orphaned tasks that could be started immediately"
            })
        
        # Timeline recommendations
        if timeline_analysis['duration_days'] > 30:
            recommendations.append({
                'type': 'warning',
                'category': 'timeline',
                'message': f"Project duration ({timeline_analysis['duration_days']:.1f} days) is quite long. Consider breaking into phases."
            })
        
        parallelization = timeline_analysis['parallelization_factor']
        if parallelization > 2:
            recommendations.append({
                'type': 'success',
                'category': 'timeline',
                'message': f"Good parallelization potential (factor: {parallelization:.1f}). Tasks can run concurrently."
            })
        
        # Resource recommendations
        high_priority_count = resource_analysis['priority_distribution']['high']
        total_tasks = len(tasks)
        if high_priority_count / total_tasks > 0.5:
            recommendations.append({
                'type': 'warning',
                'category': 'resources',
                'message': f"High percentage ({high_priority_count/total_tasks:.1%}) of tasks are high priority. Consider re-prioritizing."
            })
        
        # Critical path recommendations
        if len(critical_path) > total_tasks * 0.3:
            recommendations.append({
                'type': 'warning',
                'category': 'critical_path',
                'message': f"Critical path contains {len(critical_path)} tasks ({len(critical_path)/total_tasks:.1%} of total). Focus on these for schedule adherence."
            })
        
        # Resource type recommendations
        resource_types = resource_analysis['resource_types']
        if len(resource_types) > 5:
            recommendations.append({
                'type': 'info',
                'category': 'resources',
                'message': f"Project requires {len(resource_types)} different skill types. Ensure team has diverse capabilities."
            })
        
        return recommendations