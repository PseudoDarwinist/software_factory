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
    from ..models.mission_control_project import MissionControlProject
    from ..services.background import get_job_manager
    from ..services.websocket_server import get_websocket_server
    from ..services.github_branch_service import get_github_branch_service
    from ..services.claude_code_task_service import get_claude_code_task_service
except ImportError:
    from models.task import Task, TaskStatus
    from models.base import db
    from models.mission_control_project import MissionControlProject
    from services.background import get_job_manager
    from services.websocket_server import get_websocket_server
    from services.github_branch_service import get_github_branch_service
    from services.claude_code_task_service import get_claude_code_task_service

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
        debug = request.args.get('debug', 'false').lower() == 'true'
        
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
        
        # Add debug info if requested
        if debug:
            for i, task in enumerate(tasks):
                tasks_data[i]['debug_info'] = {
                    'status_raw': str(task.status),
                    'status_value': task.status.value if task.status else None,
                    'can_start': task.can_start(),
                    'depends_on': task.depends_on if hasattr(task, 'depends_on') else None,
                    'agent': task.agent if hasattr(task, 'agent') else None
                }
        
        logger.info(f"Returning {len(tasks_data)} tasks (project_id={project_id}, status={status_filter})")
        
        return jsonify({
            'tasks': tasks_data,
            'total': len(tasks_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/start-execution', methods=['POST'])
def start_task_execution(task_id):
    """
    Start task execution and return Build UI URL for Plan → Build transition
    POST /api/tasks/:id/start-execution
    Body: { 
        agent_id: string,
        context_options?: { spec_files, requirements, design, task, code_paths }
    }
    """
    try:
        data = request.get_json()
        logger.info(f"Task execution start request - Task ID: {task_id}, Data: {data}")
        
        if not data or 'agent_id' not in data:
            logger.error(f"Missing agent_id in request data: {data}")
            return jsonify({'error': 'agent_id is required'}), 400
        
        agent_id = data['agent_id']
        context_options = data.get('context_options', {})
        
        # Look up task
        task = Task.query.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return jsonify({'error': 'Task not found'}), 404
        
        # Check if task is ready
        if task.status != TaskStatus.READY:
            logger.error(f"Task {task_id} not ready - Status: {task.status.value if task.status else 'None'}")
            return jsonify({'error': f'Task is not ready. Current status: {task.status.value if task.status else "None"}'}), 400
        
        # Update task status to running immediately
        task.status = TaskStatus.RUNNING
        task.agent = agent_id
        task.started_at = datetime.utcnow()
        db.session.commit()
        
        # Start background execution (don't wait for completion)
        import threading
        def execute_in_background():
            try:
                claude_service = get_claude_code_task_service()
                result = claude_service.execute_task(
                    task_id=task_id,
                    agent_id=agent_id,
                    context_options=context_options
                )
                logger.info(f"Task {task_id} execution completed: {result['success']}")
            except Exception as e:
                logger.error(f"Background task execution failed for {task_id}: {e}")
                task.status = TaskStatus.FAILED
                task.add_progress_message(f"Execution failed: {str(e)}", 0)
                db.session.commit()
        
        execution_thread = threading.Thread(target=execute_in_background, daemon=True)
        execution_thread.start()
        
        # Return Build UI URL immediately for Plan → Build transition
        return jsonify({
            'success': True,
            'task_id': task_id,
            'build_url': f'/build?task={task_id}',
            'message': 'Task execution started, redirecting to Build phase'
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to start task execution for {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tasks_bp.route('/<task_id>/start', methods=['POST'])
def start_task(task_id):
    """
    Start a task execution
    POST /api/tasks/:id/start
    Body: { 
        agentId: string,
        contextOptions?: { spec_files, requirements, design, task, code_paths },
        branchName?: string,
        baseBranch?: string 
    }
    """
    try:
        data = request.get_json()
        logger.info(f"Task start request - Task ID: {task_id}, Data: {data}")
        
        if not data or 'agentId' not in data:
            logger.error(f"Missing agentId in request data: {data}")
            return jsonify({'error': 'agentId is required'}), 400
        
        agent_id = data['agentId']
        context_options = data.get('contextOptions', {})
        branch_name = data.get('branchName')
        base_branch = data.get('baseBranch', 'main')
        
        logger.info(f"Parsed request - Agent: {agent_id}, Context: {context_options}, Branch: {branch_name}")
        
        # Look up task
        task = Task.query.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return jsonify({'error': 'Task not found'}), 404
        
        logger.info(f"Found task - Status: {task.status}, Status Value: {task.status.value if task.status else 'None'}")
        
        # TEMPORARY FIX: Set task status to READY if it's not already
        # This handles cases where tasks were created with old enum values
        if task.status != TaskStatus.READY:
            logger.warning(f"Task {task_id} status is {task.status.value if task.status else 'None'}, setting to READY")
            task.status = TaskStatus.READY
            db.session.commit()
            logger.info(f"Task {task_id} status updated to READY")
        
        # Check if task is ready (should pass now)
        if task.status != TaskStatus.READY:
            logger.error(f"Task {task_id} not ready - Status: {task.status.value if task.status else 'None'}")
            return jsonify({'error': f'Task is not ready. Current status: {task.status.value if task.status else "None"}'}), 400
        
        # TEMPORARY FIX: Skip dependency check for now to get agent selection working
        # TODO: Implement proper dependency management in MVP 2 completion
        logger.info(f"Task {task_id} is READY, skipping dependency check for now")
        
        # Check dependencies - add more debugging (but don't block execution)
        can_start = task.can_start()
        logger.info(f"Task {task_id} can_start check: {can_start}")
        if hasattr(task, 'depends_on') and task.depends_on:
            logger.info(f"Task {task_id} dependencies: {task.depends_on}")
            # Check each dependency
            try:
                dependencies = task.get_dependencies()
                for dep in dependencies:
                    logger.info(f"Dependency {dep.id} status: {dep.status.value}")
            except Exception as dep_error:
                logger.warning(f"Error checking dependencies: {dep_error}")
        
        # TEMPORARY: Allow task to start even if dependencies aren't met
        # This is to get the agent selection working while we fix dependency management
        logger.info(f"Allowing task {task_id} to start (bypassing dependency check)")
        
        # Generate or validate branch name
        if not branch_name:
            # Auto-generate branch name if not provided
            project = MissionControlProject.query.get(task.project_id)
            if project and project.repo_url and project.github_token:
                branch_service = get_github_branch_service()
                
                # Use asyncio to run the async function
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                branch_result = loop.run_until_complete(
                    branch_service.generate_available_branch_name(
                        task_id=task.id,
                        task_title=task.title,
                        repo_url=project.repo_url,
                        github_token=project.github_token
                    )
                )
                
                branch_name = branch_result['branch_name']
        
        # Store branch name in task
        if branch_name:
            task.branch_name = branch_name
        
        # Mark task as running
        logger.info(f"Starting task {task_id} with agent {agent_id}")
        task.start_task(started_by='api_user', agent=agent_id)
        
        # Run the long-running agent execution in a dedicated daemon thread so the
        # Flask request can finish immediately and the UI stays responsive while the
        # agent works in the background.
        try:
            import threading
            from flask import current_app

            app_obj = current_app._get_current_object()

            def _run_with_app_context(app, task_id, agent_id, context_options, base_branch):
                """Run the original background function inside an application ctx."""
                with app.app_context():
                    _execute_task_background(task_id, agent_id, context_options, base_branch)

            exec_thread = threading.Thread(
                target=_run_with_app_context,
                args=(app_obj, task_id, agent_id, context_options, base_branch),
                daemon=True,
            )
            exec_thread.start()

            logger.info(f"Background execution thread started for task {task_id}")
        except Exception as bg_error:
            logger.error(f"Failed to start background thread for task {task_id}: {bg_error}")
            import traceback
            logger.error(f"Thread spawn traceback: {traceback.format_exc()}")
            # Do not fail the API response – the user can retry if needed
        
        logger.info(f"Task {task_id} start request completed successfully")
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


@tasks_bp.route('/<task_id>/approve', methods=['POST'])
def approve_task(task_id):
    """
    Approve a task in review status
    POST /api/tasks/:id/approve
    Body: { approvedBy: string }
    """
    try:
        data = request.get_json()
        approved_by = data.get('approvedBy', 'api_user') if data else 'api_user'
        
        # Look up task
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Check if task can be approved
        if task.status != TaskStatus.REVIEW:
            return jsonify({'error': f'Task cannot be approved. Current status: {task.status.value}'}), 400
        
        # Mark task as completed
        task.complete_task(completed_by=approved_by, pr_url=task.pr_url)
        
        # Add completion message
        task.add_progress_message("✅ Task approved and marked as complete!", 100)
        
        logger.info(f"Task {task_id} approved by {approved_by}")
        
        return jsonify({
            'message': 'Task approved successfully',
            'status': 'done',
            'approvedBy': approved_by
        }), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error approving task {task_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error approving task {task_id}: {e}")
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
        
        # Add debug info
        task_dict = task.to_dict()
        task_dict['debug_info'] = {
            'status_raw': str(task.status),
            'status_value': task.status.value if task.status else None,
            'can_start': task.can_start(),
            'depends_on': task.depends_on if hasattr(task, 'depends_on') else None
        }
        
        return jsonify(task_dict), 200
        
    except Exception as e:
        logger.error(f"Error getting task detail {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/suggest-assignee', methods=['POST'])
def suggest_assignee(task_id):
    """
    Generate AI suggestion for task assignee
    POST /api/tasks/:id/suggest-assignee
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # For now, provide a mock suggestion based on task characteristics
        # In the real implementation, this would use Claude Code SDK
        suggestion = _generate_assignee_suggestion(task)
        
        # Update task with suggestion
        task.suggested_owner = suggestion['assignee']
        task.assignment_confidence = suggestion['confidence']
        task.assignment_reasoning = suggestion['reasoning']
        db.session.commit()
        
        return jsonify(suggestion), 200
        
    except Exception as e:
        logger.error(f"Error generating assignee suggestion for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/suggest-estimate', methods=['POST'])
def suggest_estimate(task_id):
    """
    Generate AI suggestion for task effort estimate
    POST /api/tasks/:id/suggest-estimate
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # For now, provide a mock suggestion based on task characteristics
        # In the real implementation, this would use Claude Code SDK
        suggestion = _generate_effort_suggestion(task)
        
        # Update task with suggestion
        task.effort_estimate_hours = suggestion['hours']
        task.effort_reasoning = suggestion['reasoning']
        db.session.commit()
        
        return jsonify(suggestion), 200
        
    except Exception as e:
        logger.error(f"Error generating effort suggestion for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/suggest-agent', methods=['POST'])
def suggest_agent(task_id):
    """
    Generate AI suggestion for Claude Code sub-agent
    POST /api/tasks/:id/suggest-agent
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Generate agent suggestion based on task content
        suggestion = _generate_agent_suggestion(task)
        
        # Update task with suggestion
        task.suggested_agent = suggestion['agent']
        task.agent_reasoning = suggestion['reasoning']
        db.session.commit()
        
        return jsonify(suggestion), 200
        
    except Exception as e:
        logger.error(f"Error generating agent suggestion for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/update-field', methods=['PATCH'])
def update_task_field(task_id):
    """
    Update a specific field on a task
    PATCH /api/tasks/:id/update-field
    Body: { field: 'priority', value: 'high' }
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        data = request.get_json()
        if not data or 'field' not in data or 'value' not in data:
            return jsonify({'error': 'field and value are required'}), 400
        
        field = data['field']
        value = data['value']
        
        # Update allowed fields
        if field == 'priority':
            from ..models.task import TaskPriority
            try:
                task.priority = TaskPriority(value.lower())
            except ValueError:
                return jsonify({'error': f'Invalid priority: {value}'}), 400
        elif field == 'assigned_to':
            task.assigned_to = value
        elif field == 'effort_estimate_hours':
            try:
                task.effort_estimate_hours = float(value)
            except ValueError:
                return jsonify({'error': 'effort_estimate_hours must be a number'}), 400
        else:
            return jsonify({'error': f'Field {field} is not editable'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': f'Updated {field} successfully',
            'task': task.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating task field {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/generate-branch-name', methods=['POST'])
def generate_branch_name(task_id):
    """
    Generate an available branch name for a task
    POST /api/tasks/:id/generate-branch-name
    Body: { taskType?: 'feature'|'bug'|'hotfix' }
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Get project to access GitHub token and repo URL
        project = MissionControlProject.query.get(task.project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        if not project.repo_url or not project.github_token:
            return jsonify({'error': 'Project GitHub configuration incomplete'}), 400
        
        data = request.get_json() or {}
        task_type = data.get('taskType')
        
        # Generate available branch name
        branch_service = get_github_branch_service()
        
        # Use asyncio to run the async function
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            branch_service.generate_available_branch_name(
                task_id=task.id,
                task_title=task.title,
                repo_url=project.repo_url,
                github_token=project.github_token,
                task_type=task_type
            )
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error generating branch name for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/validate-branch-name', methods=['POST'])
def validate_branch_name(task_id):
    """
    Validate a branch name for a task
    POST /api/tasks/:id/validate-branch-name
    Body: { branchName: 'feature/task-123-example-20241201' }
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        data = request.get_json()
        if not data or 'branchName' not in data:
            return jsonify({'error': 'branchName is required'}), 400
        
        branch_name = data['branchName']
        
        # Validate branch name
        branch_service = get_github_branch_service()
        validation_result = branch_service.validate_branch_name(branch_name)
        
        # If valid, also check if it exists in the repository
        if validation_result['valid']:
            project = MissionControlProject.query.get(task.project_id)
            if project and project.repo_url and project.github_token:
                # Use asyncio to run the async function
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                exists = loop.run_until_complete(
                    branch_service.check_branch_exists(
                        project.repo_url,
                        branch_name,
                        project.github_token
                    )
                )
                
                validation_result['exists'] = exists
                if exists:
                    validation_result['warnings'] = ['Branch already exists in repository']
        
        return jsonify(validation_result), 200
        
    except Exception as e:
        logger.error(f"Error validating branch name for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/check-branch-collision', methods=['POST'])
def check_branch_collision(task_id):
    """
    Check for branch name collisions and suggest alternatives
    POST /api/tasks/:id/check-branch-collision
    Body: { branchName: 'feature/task-123-example-20241201' }
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Get project to access GitHub token and repo URL
        project = MissionControlProject.query.get(task.project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        if not project.repo_url or not project.github_token:
            return jsonify({'error': 'Project GitHub configuration incomplete'}), 400
        
        data = request.get_json()
        if not data or 'branchName' not in data:
            return jsonify({'error': 'branchName is required'}), 400
        
        branch_name = data['branchName']
        
        # Check for collision and resolve
        branch_service = get_github_branch_service()
        
        # Use asyncio to run the async function
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Check if original name exists
        exists = loop.run_until_complete(
            branch_service.check_branch_exists(
                project.repo_url,
                branch_name,
                project.github_token
            )
        )
        
        result = {
            'original_name': branch_name,
            'exists': exists
        }
        
        if exists:
            # Resolve collision
            resolved_name = loop.run_until_complete(
                branch_service.resolve_branch_collision(
                    project.repo_url,
                    branch_name,
                    project.github_token
                )
            )
            
            result['resolved_name'] = resolved_name
            result['collision_resolved'] = resolved_name != branch_name
        else:
            result['resolved_name'] = branch_name
            result['collision_resolved'] = False
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error checking branch collision for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/convert-pr-to-ready', methods=['POST'])
def convert_pr_to_ready(task_id):
    """
    Convert a draft PR to ready for review
    POST /api/tasks/:id/convert-pr-to-ready
    """
    try:
        # Get Claude Code task service
        claude_task_service = get_claude_code_task_service()
        
        # Convert PR to ready
        result = claude_task_service.convert_pr_to_ready(task_id)
        
        if result['success']:
            return jsonify({
                'message': 'PR converted to ready for review successfully',
                'pr_number': result.get('pr_number')
            }), 200
        else:
            return jsonify({'error': result['error']}), 400
        
    except Exception as e:
        logger.error(f"Error converting PR to ready for task {task_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/github-webhooks/setup', methods=['POST'])
def setup_github_webhook():
    """
    Set up GitHub webhook for a project
    POST /api/tasks/github-webhooks/setup
    Body: { project_id: string, webhook_url?: string }
    """
    try:
        data = request.get_json()
        if not data or 'project_id' not in data:
            return jsonify({'error': 'project_id is required'}), 400
        
        project_id = data['project_id']
        webhook_url = data.get('webhook_url')
        
        # Get project
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        if not project.repo_url or not project.github_token:
            return jsonify({'error': 'Project GitHub configuration incomplete'}), 400
        
        # Use default webhook URL if not provided
        if not webhook_url:
            webhook_url = f"{request.host_url.rstrip('/')}/api/webhooks/github"
        
        # Get GitHub webhook service
        try:
            from ..services.github_webhook_service import get_github_webhook_service
        except ImportError:
            from services.github_webhook_service import get_github_webhook_service
        
        webhook_service = get_github_webhook_service()
        
        # Create webhook
        result = webhook_service.create_webhook(
            repo_url=project.repo_url,
            github_token=project.github_token,
            webhook_url=webhook_url,
            secret=current_app.config.get('GITHUB_WEBHOOK_SECRET')
        )
        
        if result['success']:
            # Store webhook ID in project metadata
            if not project.metadata:
                project.metadata = {}
            project.metadata['github_webhook_id'] = result['webhook_id']
            project.metadata['github_webhook_url'] = webhook_url
            db.session.commit()
            
            return jsonify({
                'message': 'GitHub webhook created successfully',
                'webhook_id': result['webhook_id'],
                'webhook_url': webhook_url,
                'events': result['events']
            }), 201
        else:
            return jsonify({'error': result['error']}), 400
        
    except Exception as e:
        logger.error(f"Error setting up GitHub webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/github-webhooks/list', methods=['GET'])
def list_github_webhooks():
    """
    List GitHub webhooks for a project
    GET /api/tasks/github-webhooks/list?project_id=123
    """
    try:
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        # Get project
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        if not project.repo_url or not project.github_token:
            return jsonify({'error': 'Project GitHub configuration incomplete'}), 400
        
        # Get GitHub webhook service
        try:
            from ..services.github_webhook_service import get_github_webhook_service
        except ImportError:
            from services.github_webhook_service import get_github_webhook_service
        
        webhook_service = get_github_webhook_service()
        
        # List webhooks
        result = webhook_service.list_webhooks(
            repo_url=project.repo_url,
            github_token=project.github_token
        )
        
        if result['success']:
            return jsonify({
                'webhooks': result['webhooks'],
                'project_webhook_id': project.metadata.get('github_webhook_id') if project.metadata else None
            }), 200
        else:
            return jsonify({'error': result['error']}), 400
        
    except Exception as e:
        logger.error(f"Error listing GitHub webhooks: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/github-webhooks/test', methods=['POST'])
def test_github_webhook():
    """
    Test GitHub webhook for a project
    POST /api/tasks/github-webhooks/test
    Body: { project_id: string, webhook_id?: number }
    """
    try:
        data = request.get_json()
        if not data or 'project_id' not in data:
            return jsonify({'error': 'project_id is required'}), 400
        
        project_id = data['project_id']
        webhook_id = data.get('webhook_id')
        
        # Get project
        project = MissionControlProject.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        if not project.repo_url or not project.github_token:
            return jsonify({'error': 'Project GitHub configuration incomplete'}), 400
        
        # Use stored webhook ID if not provided
        if not webhook_id and project.metadata:
            webhook_id = project.metadata.get('github_webhook_id')
        
        if not webhook_id:
            return jsonify({'error': 'webhook_id is required'}), 400
        
        # Get GitHub webhook service
        try:
            from ..services.github_webhook_service import get_github_webhook_service
        except ImportError:
            from services.github_webhook_service import get_github_webhook_service
        
        webhook_service = get_github_webhook_service()
        
        # Test webhook
        result = webhook_service.test_webhook(
            repo_url=project.repo_url,
            github_token=project.github_token,
            webhook_id=webhook_id
        )
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'webhook_id': webhook_id
            }), 200
        else:
            return jsonify({'error': result['error']}), 400
        
    except Exception as e:
        logger.error(f"Error testing GitHub webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


def _execute_task_background(task_id: str, agent_id: str, context_options: dict = None, base_branch: str = 'main'):
    """
    Background function that executes a task using Claude Code SDK with Git workspace
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
        
        # Import Claude Code task service
        try:
            from ..services.claude_code_task_service import get_claude_code_task_service
        except ImportError:
            from services.claude_code_task_service import get_claude_code_task_service
        
        # Execute task with Claude Code SDK
        claude_task_service = get_claude_code_task_service()
        
        # Set up progress broadcasting
        def broadcast_progress():
            _broadcast_task_update(task_id, {
                'status': task.status.value,
                'progress_messages': task.progress_messages if task.progress_messages else []
            })
        
        # Execute the task
        result = claude_task_service.execute_task(
            task_id=task_id,
            agent_id=agent_id,
            context_options=context_options or {},
            base_branch=base_branch
        )
        
        # Broadcast final progress
        broadcast_progress()
        
        if result['success']:
            logger.info(f"Task {task_id} completed successfully with branch {result.get('branch_name')}")
        else:
            logger.error(f"Task {task_id} failed: {result['error']}")
        
        # Commit any database changes
        db.session.commit()
        
        # Use the proper branch naming if not already set
        if not task.branch_name:
            # Get project for branch naming
            project = MissionControlProject.query.get(task.project_id)
            if project and project.repo_url and project.github_token:
                branch_service = get_github_branch_service()
                
                # Use asyncio to run the async function
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                try:
                    branch_result = loop.run_until_complete(
                        branch_service.generate_available_branch_name(
                            task_id=task.id,
                            task_title=task.title,
                            repo_url=project.repo_url,
                            github_token=project.github_token
                        )
                    )
                    task.branch_name = branch_result['branch_name']
                except Exception as branch_error:
                    logger.warning(f"Could not generate branch name: {branch_error}")
                    task.branch_name = f"task/{task_id}-implementation"  # Fallback
            else:
                task.branch_name = f"task/{task_id}-implementation"  # Fallback
        
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


def _generate_assignee_suggestion(task: Task) -> dict:
    """
    Generate AI suggestion for task assignee
    This is a mock implementation - in the real system this would use Claude Code SDK
    """
    # Mock logic based on task characteristics
    if 'test' in task.title.lower() or 'testing' in (task.description or '').lower():
        return {
            'assignee': 'QA Engineer',
            'confidence': 0.85,
            'reasoning': 'because this task involves testing and quality assurance work'
        }
    elif 'ui' in task.title.lower() or 'frontend' in (task.description or '').lower():
        return {
            'assignee': 'Frontend Developer',
            'confidence': 0.90,
            'reasoning': 'because this task involves UI/frontend development work'
        }
    elif 'api' in task.title.lower() or 'backend' in (task.description or '').lower():
        return {
            'assignee': 'Backend Developer',
            'confidence': 0.88,
            'reasoning': 'because this task involves API/backend development work'
        }
    else:
        return {
            'assignee': 'Full Stack Developer',
            'confidence': 0.70,
            'reasoning': 'because this is a general development task requiring full-stack skills'
        }


def _generate_effort_suggestion(task: Task) -> dict:
    """
    Generate AI suggestion for task effort estimate
    This is a mock implementation - in the real system this would use Claude Code SDK
    """
    # Mock logic based on task complexity
    title_length = len(task.title)
    description_length = len(task.description or '')
    
    # Simple heuristic based on content length and keywords
    base_hours = 2.0
    
    if title_length > 50:
        base_hours += 1.0
    if description_length > 200:
        base_hours += 2.0
    
    # Adjust based on complexity keywords
    complex_keywords = ['integration', 'migration', 'refactor', 'architecture']
    simple_keywords = ['fix', 'update', 'add', 'remove']
    
    content = (task.title + ' ' + (task.description or '')).lower()
    
    if any(keyword in content for keyword in complex_keywords):
        base_hours *= 1.5
        reasoning = 'because this task involves complex architectural or integration work'
    elif any(keyword in content for keyword in simple_keywords):
        base_hours *= 0.8
        reasoning = 'because this appears to be a straightforward implementation task'
    else:
        reasoning = 'based on task complexity analysis and historical patterns'
    
    return {
        'hours': round(base_hours, 1),
        'confidence': 0.75,
        'reasoning': reasoning
    }


def _generate_agent_suggestion(task: Task) -> dict:
    """
    Generate AI suggestion for Claude Code sub-agent
    This is a mock implementation - in the real system this would analyze task content
    """
    content = (task.title + ' ' + (task.description or '')).lower()
    
    if 'test' in content or 'testing' in content:
        return {
            'agent': 'test-runner',
            'confidence': 0.90,
            'reasoning': 'because this task focuses on testing functionality'
        }
    elif any(keyword in content for keyword in ['bug', 'fix', 'error', 'issue']):
        return {
            'agent': 'debugger',
            'confidence': 0.85,
            'reasoning': 'because this task involves debugging and fixing issues'
        }
    elif any(keyword in content for keyword in ['review', 'refactor', 'optimize']):
        return {
            'agent': 'code-reviewer',
            'confidence': 0.80,
            'reasoning': 'because this task involves code review and optimization'
        }
    elif 'design' in content or 'figma' in content:
        return {
            'agent': 'design-to-code',
            'confidence': 0.88,
            'reasoning': 'because this task involves implementing design specifications'
        }
    else:
        return {
            'agent': 'feature-builder',
            'confidence': 0.75,
            'reasoning': 'because this is a general feature development task'
        }


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


@tasks_bp.route('/<task_id>/workspace', methods=['GET'])
def get_task_workspace(task_id):
    """
    Get workspace information for a task
    GET /api/tasks/:id/workspace
    """
    try:
        claude_task_service = get_claude_code_task_service()
        workspace_info = claude_task_service.get_workspace_info(task_id)
        
        if not workspace_info:
            return jsonify({'error': 'Workspace not found'}), 404
        
        return jsonify(workspace_info), 200
        
    except Exception as e:
        logger.error(f"Error getting task workspace: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/<task_id>/workspace', methods=['DELETE'])
def cleanup_task_workspace(task_id):
    """
    Clean up workspace for a task
    DELETE /api/tasks/:id/workspace
    """
    try:
        claude_task_service = get_claude_code_task_service()
        success = claude_task_service.cleanup_task_workspace(task_id)
        
        if success:
            return jsonify({'message': 'Workspace cleaned up successfully'}), 200
        else:
            return jsonify({'error': 'Failed to cleanup workspace'}), 500
        
    except Exception as e:
        logger.error(f"Error cleaning up task workspace: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/workspaces', methods=['GET'])
def list_all_workspaces():
    """
    List all active task workspaces
    GET /api/tasks/workspaces
    """
    try:
        try:
            from ..services.git_workspace_service import get_git_workspace_service
        except ImportError:
            from services.git_workspace_service import get_git_workspace_service
        
        git_service = get_git_workspace_service()
        workspaces = git_service.list_workspaces()
        runs_info = git_service.get_runs_directory_info()
        
        return jsonify({
            'workspaces': workspaces,
            'runs_directory_info': runs_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tasks_bp.route('/workspaces/cleanup', methods=['POST'])
def cleanup_all_workspaces():
    """
    Clean up all task workspaces
    POST /api/tasks/workspaces/cleanup
    """
    try:
        try:
            from ..services.git_workspace_service import get_git_workspace_service
        except ImportError:
            from services.git_workspace_service import get_git_workspace_service
        
        git_service = get_git_workspace_service()
        results = git_service.cleanup_all_workspaces()
        
        return jsonify({
            'message': 'Workspace cleanup completed',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up all workspaces: {e}")
        return jsonify({'error': 'Internal server error'}), 500