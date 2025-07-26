"""
Task Execution API
Provides endpoints for task lifecycle management, progress tracking, and conflict detection
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

try:
    from ..models.task import Task, TaskStatus
    from ..models.base import db
    from ..services.background import get_job_manager
    from ..services.websocket_server import get_websocket_server
except ImportError:
    from models.task import Task, TaskStatus
    from models.base import db
    from services.background import get_job_manager
    from services.websocket_server import get_websocket_server

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')
logger = logging.getLogger(__name__)

# Global flag for task cancellation
_cancelled_tasks = set()


@tasks_bp.route('', methods=['GET'])
def get_tasks():
    """
    Get all tasks, optionally filtered by project or status
    GET /api/tasks?project_id=123&status=ready
    """
    try:
        project_id = request.args.get('project_id')
        status_filter = request.args.get('status')
        
        # Build query
        query = Task.query
        
        if project_id:
            query = query.filter_by(project_id=str(project_id))
        
        if status_filter:
            try:
                status_enum = TaskStatus(status_filter.lower())
                query = query.filter_by(status=status_enum)
            except ValueError:
                return jsonify({'error': f'Invalid status: {status_filter}'}), 400
        
        # Order by task number for consistent display
        tasks = query.order_by(Task.task_number).all()
        
        # Convert to dict format
        tasks_data = [task.to_dict() for task in tasks]
        
        return jsonify({
            'tasks': tasks_data,
            'total': len(tasks_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/start', methods=['POST'])
def start_task(task_id):
    """
    Start a task execution
    POST /api/tasks/:id/start
    Body: { agentId }
    """
    try:
        data = request.get_json()
        if not data or 'agentId' not in data:
            return jsonify({'error': 'agentId is required'}), 400
        
        agent_id = data['agentId']
        
        # Look up task
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Check if task is ready
        if task.status != TaskStatus.READY:
            return jsonify({'error': f'Task is not ready. Current status: {task.status.value}'}), 400
        
        # Check dependencies
        if not task.can_start():
            return jsonify({'error': 'Task dependencies are not met'}), 400
        
        # Mark task as running
        task.start_task(started_by='api_user', agent=agent_id)
        
        # For now, execute immediately without background job to avoid issues
        # TODO: Re-enable background job execution once debugging is complete
        try:
            _execute_task_background(task_id, agent_id)
        except Exception as bg_error:
            logger.error(f"Error in background task execution: {bg_error}")
            import traceback
            logger.error(f"Background task traceback: {traceback.format_exc()}")
            # Don't fail the start request if background task fails
            pass
        
        return jsonify({'message': 'Task started successfully'}), 202
        
    except SQLAlchemyError as e:
        logger.error(f"Database error starting task {task_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error starting task {task_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/retry', methods=['POST'])
def retry_task(task_id):
    """
    Retry a failed or review task
    POST /api/tasks/:id/retry
    Body: { agentId }
    """
    try:
        data = request.get_json()
        if not data or 'agentId' not in data:
            return jsonify({'error': 'agentId is required'}), 400
        
        agent_id = data['agentId']
        
        # Look up task
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Check if task can be retried
        if not task.can_retry():
            return jsonify({'error': f'Task cannot be retried. Current status: {task.status.value}'}), 400
        
        # Reset task for retry
        task.reset_for_retry()
        task.start_task(started_by='api_user', agent=agent_id)
        
        # Remove from cancelled tasks if it was there
        _cancelled_tasks.discard(task_id)
        
        # Enqueue background job
        job_manager = get_job_manager()
        if job_manager:
            job_manager.enqueue_job(
                'task_execution',
                _execute_task_background,
                task_id=task_id,
                agent_id=agent_id
            )
        else:
            # Fallback: execute immediately (for testing)
            _execute_task_background(task_id, agent_id)
        
        return jsonify({'message': 'Task retry started successfully'}), 202
        
    except SQLAlchemyError as e:
        logger.error(f"Database error retrying task {task_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error retrying task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """
    Cancel a running task
    POST /api/tasks/:id/cancel
    """
    try:
        # Look up task
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Add to cancelled tasks set
        _cancelled_tasks.add(task_id)
        
        # Set task status to failed
        task.set_error('Task cancelled by user')
        
        # Broadcast cancellation via WebSocket
        _broadcast_task_update(task_id, {
            'status': 'failed',
            'message': 'Task cancelled by user',
            'percent': None
        })
        
        return jsonify({'message': 'Task cancelled successfully'}), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error cancelling task {task_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/context', methods=['GET'])
def get_task_context(task_id):
    """
    Get merged context for a task
    GET /api/tasks/:id/context
    """
    try:
        # Look up task
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # For now, return a stub with fixed markdown content
        # In the future, this would merge spec text, design notes, previous commits
        context = _get_task_context_stub(task)
        
        return jsonify({
            'taskId': task_id,
            'context': context,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting context for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/conflicts', methods=['GET'])
def check_conflicts():
    """
    Check for file conflicts with running tasks
    GET /api/tasks/conflicts?files=a.js,b.js
    """
    try:
        files_param = request.args.get('files', '')
        if not files_param:
            return jsonify({'conflicts': []}), 200
        
        file_paths = [f.strip() for f in files_param.split(',') if f.strip()]
        if not file_paths:
            return jsonify({'conflicts': []}), 200
        
        # Get running tasks that claim any of these files
        conflicting_tasks = Task.get_running_tasks_with_files(file_paths)
        
        conflicts = []
        for task in conflicting_tasks:
            conflicts.append({
                'taskId': task.id,
                'title': task.title,
                'agent': task.agent,
                'touchedFiles': task.touched_files or [],
                'conflictingFiles': [f for f in file_paths if f in (task.touched_files or [])]
            })
        
        return jsonify({'conflicts': conflicts}), 200
        
    except Exception as e:
        logger.error(f"Error checking conflicts: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>', methods=['GET'])
def get_task_detail(task_id):
    """
    Get complete task record
    GET /api/tasks/:id
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(task.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting task detail {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


def _execute_task_background(task_id: str, agent_id: str):
    """
    Background function that executes a task
    This is a stub implementation - in the real system this would:
    1. Gather context (spec markdown, design notes, repo URL)
    2. Create a branch
    3. Generate code with the chosen agent
    4. Run tests
    5. Create PR
    6. Report progress via WebSocket
    """
    try:
        # Check if task was cancelled
        if task_id in _cancelled_tasks:
            logger.info(f"Task {task_id} was cancelled, aborting execution")
            return
        
        # Get task from database
        task = Task.query.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found during execution")
            return
        
        # Simulate task execution with progress updates
        steps = [
            ("Gathering context...", 10),
            ("Creating branch...", 20),
            ("Analyzing requirements...", 40),
            ("Generating code...", 60),
            ("Running tests...", 80),
            ("Creating pull request...", 90),
            ("Task completed", 100)
        ]
        
        for message, percent in steps:
            # Check for cancellation
            if task_id in _cancelled_tasks:
                logger.info(f"Task {task_id} cancelled during execution")
                return
            
            # Update progress
            task.add_progress_message(message, percent)
            
            # Broadcast progress via WebSocket
            _broadcast_task_update(task_id, {
                'status': task.status.value,
                'message': message,
                'percent': percent
            })
            
            # Simulate work
            import time
            time.sleep(1)
        
        # Mark task as review (simulating successful completion)
        task.status = TaskStatus.REVIEW
        task.branch_name = f"task/{task_id}-implementation"
        task.repo_url = "https://github.com/example/repo"
        task.add_touched_file("src/example.py")
        task.add_touched_file("tests/test_example.py")
        db.session.commit()
        
        # Final broadcast
        _broadcast_task_update(task_id, {
            'status': 'review',
            'message': 'Task completed successfully',
            'percent': 100
        })
        
        # Remove from cancelled tasks
        _cancelled_tasks.discard(task_id)
        
    except Exception as e:
        logger.error(f"Error executing task {task_id}: {e}")
        
        # Mark task as failed
        try:
            task = Task.query.get(task_id)
            if task:
                task.set_error(f"Task execution failed: {str(e)}")
                
                _broadcast_task_update(task_id, {
                    'status': 'failed',
                    'message': f'Task failed: {str(e)}',
                    'percent': None
                })
        except Exception as inner_e:
            logger.error(f"Error updating failed task {task_id}: {inner_e}")


def _broadcast_task_update(task_id: str, partial_update: dict):
    """
    Broadcast a partial or full task update to subscribed clients via WebSocket.
    This function will fetch the latest full task state to ensure clients
    always have the most current data.
    """
    try:
        ws_server = get_websocket_server()
        if not ws_server:
            logger.warning("WebSocket server not available for task update broadcast.")
            return

        # Fetch the full, up-to-date task from the database
        task = Task.query.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for broadcasting update.")
            # If task was deleted, we can't send an update for it.
            # A 'task_deleted' event might be useful here in the future.
            return

        # The full task dictionary is the most reliable payload
        full_task_data = task.to_dict()

        # Emit the full task object. The client can then replace its local
        # version with this canonical one.
        ws_server.broadcast_task_progress(task_id, full_task_data)

        logger.info(f"Broadcasted full update for task {task_id} to relevant clients.")

    except Exception as e:
        logger.error(f"Error broadcasting task update for {task_id}: {e}")


def _get_task_context_stub(task: Task) -> str:
    """
    Get task context - stub implementation
    In the real system, this would merge:
    - Spec text from requirements.md, design.md, tasks.md
    - Design notes from design artifacts
    - Previous commits related to this task
    """
    context = f"""# Task Context for {task.title}

## Task Details
- **ID**: {task.id}
- **Title**: {task.title}
- **Description**: {task.description or 'No description provided'}
- **Task Number**: {task.task_number}
- **Project**: {task.project_id}
- **Spec**: {task.spec_id}

## Requirements
{task.requirements_refs or 'No specific requirements referenced'}

## Related Files
{', '.join(task.related_files or ['No files specified'])}

## Related Components
{', '.join(task.related_components or ['No components specified'])}

## Dependencies
{', '.join(task.depends_on or ['No dependencies'])}

## Context Notes
This is a stub implementation. In the full system, this would include:
- Merged specification text from requirements.md, design.md, tasks.md
- Design notes and artifacts
- Previous commit history related to this task
- Code context from related files
- Team expertise and assignment rationale

## Suggested Implementation Approach
Based on the task title and description, consider:
1. Review the related files and components
2. Understand the requirements context
3. Follow the project's coding standards
4. Ensure proper test coverage
5. Document any architectural decisions
"""
    
    return context


# WebSocket endpoint for task progress streaming
# This is handled by the WebSocket server, but we define the event structure here
def setup_task_websocket_events(socketio):
    """Setup WebSocket events for task progress streaming"""
    
    @socketio.on('subscribe_task')
    def handle_task_subscription(data):
        """Handle client subscription to task progress"""
        task_id = data.get('taskId')
        if task_id:
            # Join room for this specific task
            from flask_socketio import join_room
            join_room(f'task_{task_id}')
            logger.info(f"Client subscribed to task {task_id}")
    
    @socketio.on('unsubscribe_task')
    def handle_task_unsubscription(data):
        """Handle client unsubscription from task progress"""
        task_id = data.get('taskId')
        if task_id:
            # Leave room for this specific task
            from flask_socketio import leave_room
            leave_room(f'task_{task_id}')
            logger.info(f"Client unsubscribed from task {task_id}")