"""
PlannerAgent Bridge - Initialize and manage PlannerAgent lifecycle
"""

import logging
from typing import Optional

try:
    from ..services.event_bus import get_event_bus
    from ..models.task import Task, TaskStatus, TaskPriority
    from ..models.specification_artifact import SpecificationArtifact, ArtifactType
    from ..models.base import db
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.event_bus import get_event_bus
    from models.task import Task, TaskStatus, TaskPriority
    from models.specification_artifact import SpecificationArtifact, ArtifactType
    from models.base import db

logger = logging.getLogger(__name__)

# Global PlannerAgent instance
_planner_agent = None
_flask_app = None


def init_planner_agent_bridge(flask_app=None):
    """Initialize the PlannerAgent bridge and subscribe to events.

    The optional *flask_app* parameter should be the running Flask application
    instance so that the event handler can create an application context when
    it runs in a background thread.  Passing it avoids relying on
    *flask.current_app* which does not exist outside the main request thread.
    """
    global _planner_agent, _flask_app

    # Persist the Flask app reference if provided so the callback can push an
    # application context later on.
    if flask_app is not None:
        _flask_app = flask_app

    try:
        # Obtain (and lazily create) the global Redis-backed event bus.
        event_bus = get_event_bus()
        if not event_bus:
            logger.error("Redis event bus not available for PlannerAgent bridge")
            return False

        # Ensure the event bus is running; if the caller already started it
        # this is a harmless no-op, otherwise the bridge would never receive
        # events.
        try:
            event_bus.start()
        except RuntimeError:
            # "already running" – ignore
            pass

        # Subscribe to spec.frozen events so we can create tasks when a spec is
        # frozen in the Define stage.
        event_bus.subscribe('spec.frozen', _handle_spec_frozen_event)

        logger.info("PlannerAgent bridge initialized and subscribed to spec.frozen events")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize PlannerAgent bridge: {e}")
        return False


def _handle_spec_frozen_event(event_data):
    """Handle spec.frozen events from Redis and create tasks"""
    global _flask_app
    
    # Get Flask app instance if not already stored
    if not _flask_app:
        try:
            from flask import current_app
            _flask_app = current_app._get_current_object()
        except RuntimeError:
            logger.error("Flask app not available in event handler - no application context")
            return
    
    # We need to run this in Flask application context
    with _flask_app.app_context():
        try:
            logger.info(f"PlannerAgent received spec.frozen event: {event_data}")
            
            # Extract event data - event_data is an Event object, not a dict
            if hasattr(event_data, 'data'):
                # It's an Event object
                spec_id = event_data.data.get('spec_id')
                project_id = event_data.data.get('project_id') or event_data.project_id
            else:
                # It's a dict (fallback)
                payload = event_data.get('payload', {})
                spec_id = payload.get('spec_id') or payload.get('aggregate_id')
                project_id = payload.get('project_id')
            
            if not spec_id or not project_id:
                logger.error(f"Missing spec_id or project_id in event: {event_data}")
                return
            
            logger.info(f"Processing spec.frozen for spec {spec_id} in project {project_id}")
            
            # Get the tasks artifact
            tasks_artifact = SpecificationArtifact.query.filter_by(
                spec_id=spec_id,
                artifact_type=ArtifactType.TASKS
            ).first()
            
            if not tasks_artifact:
                logger.warning(f"No tasks artifact found for spec {spec_id}")
                return
            
            # Parse tasks from markdown content
            parsed_tasks = _parse_tasks_from_markdown(tasks_artifact.content, spec_id, project_id)
            
            if not parsed_tasks:
                logger.warning(f"No tasks parsed from spec {spec_id}")
                return
            
            # Create Task records (skip duplicates)
            created_tasks = []
            for task_data in parsed_tasks:
                task_id = f"{spec_id}_{task_data.get('task_number', 'unknown')}"
                
                # Check if task already exists
                existing_task = Task.query.get(task_id)
                if existing_task:
                    logger.info(f"Task {task_id} already exists, skipping")
                    continue
                
                task = Task.create_task(
                    spec_id=spec_id,
                    project_id=project_id,
                    task_data=task_data,
                    created_by='planner_agent'
                )
                created_tasks.append(task)
            
            if created_tasks:
                db.session.commit()
            
            logger.info(f"✅ Created {len(created_tasks)} tasks from spec {spec_id}")
            for task in created_tasks:
                logger.info(f"  - {task.task_number}: {task.title}")
            
        except Exception as e:
            logger.error(f"Error handling spec.frozen event: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")


def _parse_tasks_from_markdown(markdown_content: str, spec_id: str, project_id: str):
    """Parse tasks from markdown content with proper decimal notation support."""
    import re
    logger.info("Starting markdown parsing with decimal notation support.")

    tasks = []
    lines = markdown_content.split('\n')
    current_task = None

    def save_current_task():
        nonlocal current_task
        if current_task:
            # Join description lines and clean up whitespace
            current_task['description'] = '\n'.join(current_task['description_lines']).strip()
            del current_task['description_lines']
            tasks.append(current_task)
            logger.debug(f"Saved task: {current_task['task_number']} - {current_task['title']}")
        current_task = None

    for line_num, line in enumerate(lines):
        if not line.strip():
            continue

        stripped_line = line.strip()

        # Match checkbox tasks with explicit numbering: - [ ] 1. Task title OR - [ ] 1.1 Task title
        # First try to match decimal notation (2.1, 2.2)
        decimal_task_match = re.match(r'-\s*\[\s*[x\s]*\]\s*(\d+\.\d+)\s+(.+)', stripped_line)
        # Then try to match simple numbering (1., 2.)
        simple_task_match = re.match(r'-\s*\[\s*[x\s]*\]\s*(\d+)\.\s*(.+)', stripped_line)
        
        explicit_task_match = decimal_task_match or simple_task_match
        
        # Match checkbox tasks without explicit numbering: - [ ] Task title
        implicit_task_match = re.match(r'-\s*\[\s*[x\s]*\]\s*(.+)', stripped_line)

        if explicit_task_match:
            # This is a task with explicit numbering (1, 1.1, 2.1, etc.)
            save_current_task()  # Save the previous task
            
            task_number_str = explicit_task_match.group(1)
            title_full = explicit_task_match.group(2).strip()
            
            # Clean up common AI artifacts
            title = re.sub(r'^\*\*User Story:\s*', '', title_full, flags=re.IGNORECASE)
            title = re.sub(r'\*\*', '', title)  # Remove bold markers
            
            # Determine parent task for decimal notation
            parent_task_id = None
            task_parts = task_number_str.split('.')
            if len(task_parts) > 1:
                # This is a sub-task (e.g., 2.1)
                parent_number = task_parts[0]
                parent_task_id = f"{spec_id}_{parent_number}"

            current_task = {
                'task_number': task_number_str,
                'title': title,
                'description_lines': [],
                'requirements_refs': [],
                'effort_estimate_hours': 1.0 if len(task_parts) > 1 else 2.0,  # Sub-tasks get smaller estimates
                'suggested_owner': 'Developer',
                'depends_on': [],
                'related_files': [],
                'related_components': [],
                'parent_task_id': parent_task_id
            }
            
        elif implicit_task_match and not explicit_task_match:
            # This is a task without explicit numbering - check if it should be parsed
            title_full = implicit_task_match.group(1).strip()
            
            # Skip if this looks like a description item rather than a task
            if (title_full.startswith('Create ') or 
                title_full.startswith('Implement ') or 
                title_full.startswith('Write ') or
                title_full.startswith('Add ') or
                title_full.startswith('Build ') or
                title_full.startswith('Test ') or
                title_full.startswith('Set up ') or
                title_full.startswith('Configure ')):
                
                # This looks like a task without explicit numbering
                save_current_task()  # Save the previous task
                
                # Auto-assign a task number
                task_number_str = str(len(tasks) + 1)
                
                # Clean up title
                title = re.sub(r'^\*\*User Story:\s*', '', title_full, flags=re.IGNORECASE)
                title = re.sub(r'\*\*', '', title)
                
                current_task = {
                    'task_number': task_number_str,
                    'title': title,
                    'description_lines': [],
                    'requirements_refs': [],
                    'effort_estimate_hours': 2.0,
                    'suggested_owner': 'Developer',
                    'depends_on': [],
                    'related_files': [],
                    'related_components': [],
                    'parent_task_id': None
                }
            else:
                # This is likely a description item, add to current task if exists
                if current_task:
                    current_task['description_lines'].append(f"• {title_full}")
        
        elif current_task and stripped_line:
            # This is additional content for the current task
            if '_Requirements:' in stripped_line:
                req_match = re.search(r'_Requirements:\s*([^_]+)_', stripped_line)
                if req_match:
                    req_refs = [f"REQ-{ref.strip().zfill(3)}" for ref in req_match.group(1).split(',')]
                    current_task['requirements_refs'].extend(req_refs)
            elif stripped_line.startswith('- '):
                # Handle bullet points in the description
                current_task['description_lines'].append(f"  {stripped_line}")
            else:
                # Handle regular description text
                current_task['description_lines'].append(stripped_line)

    save_current_task()  # Save the very last task

    logger.info(f"Decimal notation parser finished. Parsed {len(tasks)} tasks from markdown.")
    
    # Log task structure for debugging
    for task in tasks:
        parent_info = f" (parent: {task.get('parent_task_id', 'none')})" if task.get('parent_task_id') else ""
        logger.info(f"  Task {task['task_number']}: {task['title'][:50]}...{parent_info}")
    
    return tasks


def get_planner_agent():
    """Get the global PlannerAgent instance (simplified)"""
    return "planner_agent_bridge_active"


def stop_planner_agent():
    """Stop the PlannerAgent"""
    try:
        event_bus = get_event_bus()
        if event_bus:
            # Unsubscribe from events
            # Note: The current event_bus doesn't have an unsubscribe method
            # This would need to be implemented if needed
            pass
        logger.info("PlannerAgent stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping PlannerAgent: {e}")