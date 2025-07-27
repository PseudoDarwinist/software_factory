"""
Task model for storing parsed tasks from specifications
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import JSON
from .base import db


class TaskStatus(Enum):
    """Status of tasks in the workflow.

    NOTE: Values are lowercase to match the Postgres enum defined in the Alembic
    migration (see 008_add_task_execution_fields). Using different values than
    the underlying DB enum causes commit failures such as
    `invalid input value for enum taskstatus`. Keeping them aligned here
    prevents runtime 500 errors when the API attempts to transition task
    status during the start endpoint.
    """

    READY = "ready"
    RUNNING = "running"
    REVIEW = "review"
    DONE = "done"
    FAILED = "failed"


class TaskPriority(Enum):
    """Priority levels for tasks"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(db.Model):
    """
    Model for storing individual tasks parsed from specification artifacts
    Supports the Plan Stage's Kanban board functionality
    """
    
    __tablename__ = 'task'
    
    id = db.Column(db.String(100), primary_key=True)  # task_id from parsing
    spec_id = db.Column(db.String(100), nullable=False, index=True)
    project_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Task content
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    task_number = db.Column(db.String(20))  # e.g., "1.1", "2.3"
    parent_task_id = db.Column(db.String(100))  # For sub-tasks
    
    # Task metadata
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.READY, nullable=False)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    effort_estimate_hours = db.Column(db.Float)  # Estimated effort in hours
    
    # Task execution fields (required by task execution API)
    agent = db.Column(db.String(100))  # Agent assigned to execute this task
    branch_name = db.Column(db.String(200))  # Git branch for this task
    repo_url = db.Column(db.String(500))  # Repository URL
    progress_messages = db.Column(JSON, default=list)  # List of progress messages
    touched_files = db.Column(JSON, default=list)  # List of files modified by this task
    error = db.Column(db.Text)  # Error message if task failed
    
    # Assignment and ownership
    suggested_owner = db.Column(db.String(100))  # AI-suggested owner based on expertise
    assigned_to = db.Column(db.String(100))  # Actually assigned owner
    assignment_confidence = db.Column(db.Float)  # Confidence in AI suggestion (0-1)
    assignment_reasoning = db.Column(db.Text)  # AI reasoning for assignment suggestion
    
    # AI-generated suggestions and reasoning
    suggested_agent = db.Column(db.String(50))  # Suggested Claude Code sub-agent
    agent_reasoning = db.Column(db.Text)  # Reasoning for agent suggestion
    effort_reasoning = db.Column(db.Text)  # Reasoning for effort estimate
    
    # Code impact analysis
    likely_touches = db.Column(JSON)  # List of file paths/folders this task will likely modify
    goal_line = db.Column(db.String(200))  # Short goal from acceptance criteria
    
    # Requirements traceability
    requirements_refs = db.Column(JSON)  # List of requirement IDs this task addresses
    
    # Dependencies and relationships
    depends_on = db.Column(JSON)  # List of task IDs this task depends on
    blocks = db.Column(JSON)  # List of task IDs this task blocks
    
    # Context and relationships
    related_files = db.Column(JSON)  # List of file paths related to this task
    related_components = db.Column(JSON)  # List of system components
    
    # Tracking fields
    created_by = db.Column(db.String(100))  # agent_id or user_id
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Task execution tracking
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    started_by = db.Column(db.String(100))
    completed_by = db.Column(db.String(100))
    
    # Build integration
    pr_url = db.Column(db.String(500))  # Pull request URL when task generates code
    build_status = db.Column(db.String(50))  # Build status for this task
    
    # Indexes
    __table_args__ = (
        db.Index('idx_spec_project', 'spec_id', 'project_id'),
        db.Index('idx_status_priority', 'status', 'priority'),
        db.Index('idx_assigned_status', 'assigned_to', 'status'),
    )
    
    def __repr__(self):
        return f'<Task {self.task_number}: {self.title[:50]}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'spec_id': self.spec_id,
            'project_id': self.project_id,
            'title': self.title,
            'description': self.description,
            'task_number': self.task_number,
            'parent_task_id': self.parent_task_id,
            'status': self.status.value if self.status else None,
            'priority': self.priority.value if self.priority else None,
            'effort_estimate_hours': self.effort_estimate_hours,
            'suggested_owner': self.suggested_owner,
            'assigned_to': self.assigned_to,
            'assignment_confidence': self.assignment_confidence,
            'assignment_reasoning': self.assignment_reasoning,
            'suggested_agent': self.suggested_agent,
            'agent_reasoning': self.agent_reasoning,
            'effort_reasoning': self.effort_reasoning,
            'likely_touches': self.likely_touches or [],
            'goal_line': self.goal_line,
            'requirements_refs': self.requirements_refs or [],
            'depends_on': self.depends_on or [],
            'blocks': self.blocks or [],
            'related_files': self.related_files or [],
            'related_components': self.related_components or [],
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'started_by': self.started_by,
            'completed_by': self.completed_by,
            'pr_url': self.pr_url,
            'build_status': self.build_status,
            # Task execution fields
            'agent': self.agent,
            'branchName': self.branch_name,
            'repoUrl': self.repo_url,
            'progressMessages': self.progress_messages or [],
            'touchedFiles': self.touched_files or [],
            'error': self.error
        }
    
    @classmethod
    def create_task(cls, spec_id: str, project_id: str, task_data: dict, created_by: str):
        """Create a new task from parsed data"""
        task_id = f"{spec_id}_{task_data.get('task_number', 'unknown')}"
        
        task = cls(
            id=task_id,
            spec_id=spec_id,
            project_id=str(project_id),
            title=task_data.get('title', ''),
            description=task_data.get('description', ''),
            task_number=task_data.get('task_number'),
            parent_task_id=task_data.get('parent_task_id'),
            effort_estimate_hours=task_data.get('effort_estimate_hours'),
            suggested_owner=task_data.get('suggested_owner'),
            assignment_confidence=task_data.get('assignment_confidence'),
            requirements_refs=task_data.get('requirements_refs', []),
            depends_on=task_data.get('depends_on', []),
            blocks=task_data.get('blocks', []),
            related_files=task_data.get('related_files', []),
            related_components=task_data.get('related_components', []),
            created_by=created_by
        )
        
        db.session.add(task)
        return task
    
    @classmethod
    def get_spec_tasks(cls, spec_id: str):
        """Get all tasks for a specification"""
        return cls.query.filter_by(spec_id=spec_id).order_by(cls.task_number).all()
    
    @classmethod
    def get_project_tasks(cls, project_id: str, status: TaskStatus = None):
        """Get all tasks for a project, optionally filtered by status"""
        query = cls.query.filter_by(project_id=str(project_id))
        if status:
            query = query.filter_by(status=status)
        return query.order_by(cls.task_number).all()
    
    @classmethod
    def get_user_tasks(cls, user_id: str, status: TaskStatus = None):
        """Get all tasks assigned to a user"""
        query = cls.query.filter_by(assigned_to=user_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(cls.priority.desc(), cls.created_at).all()
    
    def start_task(self, started_by: str, agent: str = None):
        """Mark task as started"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.started_by = started_by
        self.updated_by = started_by
        self.updated_at = datetime.utcnow()
        if agent:
            self.agent = agent
        db.session.commit()
    
    def complete_task(self, completed_by: str, pr_url: str = None):
        """Mark task as completed"""
        self.status = TaskStatus.DONE
        self.completed_at = datetime.utcnow()
        self.completed_by = completed_by
        self.updated_by = completed_by
        self.updated_at = datetime.utcnow()
        if pr_url:
            self.pr_url = pr_url
        db.session.commit()
    
    def assign_to_user(self, user_id: str, assigned_by: str):
        """Assign task to a user"""
        self.assigned_to = user_id
        self.updated_by = assigned_by
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def update_build_status(self, build_status: str):
        """Update build status for this task"""
        self.build_status = build_status
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_dependencies(self):
        """Get task dependencies as Task objects"""
        if not self.depends_on:
            return []
        return Task.query.filter(Task.id.in_(self.depends_on)).all()
    
    def get_blocked_tasks(self):
        """Get tasks that this task blocks"""
        if not self.blocks:
            return []
        return Task.query.filter(Task.id.in_(self.blocks)).all()
    
    def get_subtasks(self):
        """Get subtasks of this task"""
        return Task.query.filter_by(parent_task_id=self.id).order_by(Task.task_number).all()
    
    def get_parent_task(self):
        """Get parent task if this is a subtask"""
        if self.parent_task_id:
            return Task.query.get(self.parent_task_id)
        return None
    
    def can_start(self):
        """Check if task can be started (all dependencies completed)"""
        if self.status != TaskStatus.READY:
            return False
        
        dependencies = self.get_dependencies()
        return all(dep.status == TaskStatus.DONE for dep in dependencies)
    
    def add_progress_message(self, message: str, percent: int = None):
        """Add a progress message to the task"""
        if not self.progress_messages:
            self.progress_messages = []
        
        progress_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'message': message
        }
        if percent is not None:
            progress_entry['percent'] = percent
            
        self.progress_messages.append(progress_entry)
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def set_error(self, error_message: str):
        """Set task error and mark as failed"""
        self.error = error_message
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def reset_for_retry(self):
        """Reset task for retry"""
        self.progress_messages = []
        self.error = None
        self.touched_files = []
        self.branch_name = None
        self.status = TaskStatus.READY
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def can_retry(self):
        """Check if task can be retried"""
        return self.status in [TaskStatus.FAILED, TaskStatus.REVIEW]
    
    def add_touched_file(self, file_path: str):
        """Add a file to the touched files list"""
        if not self.touched_files:
            self.touched_files = []
        
        if file_path not in self.touched_files:
            self.touched_files.append(file_path)
            self.updated_at = datetime.utcnow()
            db.session.commit()
    
    @classmethod
    def get_running_tasks_with_files(cls, file_paths: list):
        """Get running tasks that claim any of the specified files"""
        if not file_paths:
            return []
        
        running_tasks = cls.query.filter_by(status=TaskStatus.RUNNING).all()
        conflicting_tasks = []
        
        for task in running_tasks:
            if task.touched_files:
                for file_path in file_paths:
                    if file_path in task.touched_files:
                        conflicting_tasks.append(task)
                        break
        
        return conflicting_tasks
    
    def get_effort_summary(self):
        """Get effort summary including subtasks"""
        total_estimate = self.effort_estimate_hours or 0
        subtasks = self.get_subtasks()
        
        for subtask in subtasks:
            if subtask.effort_estimate_hours:
                total_estimate += subtask.effort_estimate_hours
        
        return {
            'total_estimate_hours': total_estimate,
            'subtask_count': len(subtasks),
            'has_estimate': self.effort_estimate_hours is not None
        }
    
    @classmethod
    def get_project_progress(cls, project_id: str):
        """Get project progress statistics"""
        tasks = cls.get_project_tasks(project_id)
        
        if not tasks:
            return {
                'total_tasks': 0,
                'ready': 0,
                'running': 0,
                'review': 0,
                'done': 0,
                'failed': 0,
                'completion_percentage': 0.0,
                'total_effort_hours': 0.0,
                'completed_effort_hours': 0.0
            }
        
        status_counts = {status.value: 0 for status in TaskStatus}
        total_effort = 0.0
        completed_effort = 0.0
        
        for task in tasks:
            status_counts[task.status.value] += 1
            
            if task.effort_estimate_hours:
                total_effort += task.effort_estimate_hours
                if task.status == TaskStatus.DONE:
                    completed_effort += task.effort_estimate_hours
        
        total_tasks = len(tasks)
        completion_percentage = (status_counts['done'] / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            'total_tasks': total_tasks,
            'ready': status_counts['ready'],
            'running': status_counts['running'],
            'review': status_counts['review'],
            'done': status_counts['done'],
            'failed': status_counts['failed'],
            'completion_percentage': completion_percentage,
            'total_effort_hours': total_effort,
            'completed_effort_hours': completed_effort,
            'effort_completion_percentage': (completed_effort / total_effort * 100) if total_effort > 0 else 0
        }