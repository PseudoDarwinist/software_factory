"""
Domain event definitions for the software factory system.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from .base import DomainEvent, EventVersion


# Project Lifecycle Events

class ProjectCreatedEvent(DomainEvent):
    """Event fired when a new project is created."""
    
    def __init__(
        self,
        project_id: str,
        name: str,
        repository_url: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ):
        super().__init__(project_id, "project", **kwargs)
        self.name = name
        self.repository_url = repository_url
        self.description = description
    
    def get_event_type(self) -> str:
        return "project.created"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'name': self.name,
            'repository_url': self.repository_url,
            'description': self.description
        })
        return payload


class ProjectUpdatedEvent(DomainEvent):
    """Event fired when a project is updated."""
    
    def __init__(
        self,
        project_id: str,
        changes: Dict[str, Any],
        **kwargs
    ):
        super().__init__(project_id, "project", **kwargs)
        self.changes = changes
    
    def get_event_type(self) -> str:
        return "project.updated"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'changes': self.changes
        })
        return payload


class ProjectDeletedEvent(DomainEvent):
    """Event fired when a project is deleted."""
    
    def __init__(self, project_id: str, **kwargs):
        super().__init__(project_id, "project", **kwargs)
    
    def get_event_type(self) -> str:
        return "project.deleted"
    
    def get_version(self) -> str:
        return EventVersion.V1.value


class RepositoryProcessingStartedEvent(DomainEvent):
    """Event fired when repository processing begins."""
    
    def __init__(
        self,
        project_id: str,
        repository_url: str,
        job_id: str,
        **kwargs
    ):
        super().__init__(project_id, "project", **kwargs)
        self.repository_url = repository_url
        self.job_id = job_id
    
    def get_event_type(self) -> str:
        return "repository.processing.started"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'repository_url': self.repository_url,
            'job_id': self.job_id
        })
        return payload


class RepositoryProcessingCompletedEvent(DomainEvent):
    """Event fired when repository processing completes successfully."""
    
    def __init__(
        self,
        project_id: str,
        job_id: str,
        system_map_id: str,
        processing_time_seconds: float,
        **kwargs
    ):
        super().__init__(project_id, "project", **kwargs)
        self.job_id = job_id
        self.system_map_id = system_map_id
        self.processing_time_seconds = processing_time_seconds
    
    def get_event_type(self) -> str:
        return "repository.processing.completed"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'job_id': self.job_id,
            'system_map_id': self.system_map_id,
            'processing_time_seconds': self.processing_time_seconds
        })
        return payload


class RepositoryProcessingFailedEvent(DomainEvent):
    """Event fired when repository processing fails."""
    
    def __init__(
        self,
        project_id: str,
        job_id: str,
        error_message: str,
        error_type: str,
        **kwargs
    ):
        super().__init__(project_id, "project", **kwargs)
        self.job_id = job_id
        self.error_message = error_message
        self.error_type = error_type
    
    def get_event_type(self) -> str:
        return "repository.processing.failed"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'job_id': self.job_id,
            'error_message': self.error_message,
            'error_type': self.error_type
        })
        return payload


# AI Interaction Events

class AIRequestStartedEvent(DomainEvent):
    """Event fired when an AI request is initiated."""
    
    def __init__(
        self,
        request_id: str,
        model_type: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(request_id, "ai_request", **kwargs)
        self.model_type = model_type
        self.prompt = prompt
        self.context = context or {}
    
    def get_event_type(self) -> str:
        return "ai.request.started"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'model_type': self.model_type,
            'prompt': self.prompt,
            'context': self.context
        })
        return payload


class AIRequestCompletedEvent(DomainEvent):
    """Event fired when an AI request completes successfully."""
    
    def __init__(
        self,
        request_id: str,
        model_type: str,
        response: str,
        response_time_seconds: float,
        token_count: Optional[int] = None,
        **kwargs
    ):
        super().__init__(request_id, "ai_request", **kwargs)
        self.model_type = model_type
        self.response = response
        self.response_time_seconds = response_time_seconds
        self.token_count = token_count
    
    def get_event_type(self) -> str:
        return "ai.request.completed"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'model_type': self.model_type,
            'response': self.response,
            'response_time_seconds': self.response_time_seconds,
            'token_count': self.token_count
        })
        return payload


class AIRequestFailedEvent(DomainEvent):
    """Event fired when an AI request fails."""
    
    def __init__(
        self,
        request_id: str,
        model_type: str,
        error_message: str,
        error_type: str,
        **kwargs
    ):
        super().__init__(request_id, "ai_request", **kwargs)
        self.model_type = model_type
        self.error_message = error_message
        self.error_type = error_type
    
    def get_event_type(self) -> str:
        return "ai.request.failed"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'model_type': self.model_type,
            'error_message': self.error_message,
            'error_type': self.error_type
        })
        return payload


# Build and Deployment Events

class BuildStartedEvent(DomainEvent):
    """Event fired when a build process starts."""
    
    def __init__(
        self,
        build_id: str,
        project_id: str,
        branch: str,
        commit_hash: str,
        build_type: str = "standard",
        **kwargs
    ):
        super().__init__(build_id, "build", **kwargs)
        self.project_id = project_id
        self.branch = branch
        self.commit_hash = commit_hash
        self.build_type = build_type
    
    def get_event_type(self) -> str:
        return "build.started"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'branch': self.branch,
            'commit_hash': self.commit_hash,
            'build_type': self.build_type
        })
        return payload


class BuildCompletedEvent(DomainEvent):
    """Event fired when a build completes successfully."""
    
    def __init__(
        self,
        build_id: str,
        project_id: str,
        build_duration_seconds: float,
        artifacts: List[str],
        **kwargs
    ):
        super().__init__(build_id, "build", **kwargs)
        self.project_id = project_id
        self.build_duration_seconds = build_duration_seconds
        self.artifacts = artifacts
    
    def get_event_type(self) -> str:
        return "build.completed"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'build_duration_seconds': self.build_duration_seconds,
            'artifacts': self.artifacts
        })
        return payload


class BuildFailedEvent(DomainEvent):
    """Event fired when a build fails."""
    
    def __init__(
        self,
        build_id: str,
        project_id: str,
        error_message: str,
        build_logs: str,
        **kwargs
    ):
        super().__init__(build_id, "build", **kwargs)
        self.project_id = project_id
        self.error_message = error_message
        self.build_logs = build_logs
    
    def get_event_type(self) -> str:
        return "build.failed"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'error_message': self.error_message,
            'build_logs': self.build_logs
        })
        return payload


# Conversation and Collaboration Events

class ConversationStartedEvent(DomainEvent):
    """Event fired when a new conversation is started."""
    
    def __init__(
        self,
        conversation_id: str,
        project_id: str,
        participants: List[str],
        topic: Optional[str] = None,
        **kwargs
    ):
        super().__init__(conversation_id, "conversation", **kwargs)
        self.project_id = project_id
        self.participants = participants
        self.topic = topic
    
    def get_event_type(self) -> str:
        return "conversation.started"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'participants': self.participants,
            'topic': self.topic
        })
        return payload


class MessageSentEvent(DomainEvent):
    """Event fired when a message is sent in a conversation."""
    
    def __init__(
        self,
        message_id: str,
        conversation_id: str,
        sender: str,
        content: str,
        message_type: str = "text",
        **kwargs
    ):
        super().__init__(message_id, "message", **kwargs)
        self.conversation_id = conversation_id
        self.sender = sender
        self.content = content
        self.message_type = message_type
    
    def get_event_type(self) -> str:
        return "message.sent"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'conversation_id': self.conversation_id,
            'sender': self.sender,
            'content': self.content,
            'message_type': self.message_type
        })
        return payload


# Code Change Events

class CodeChangedEvent(DomainEvent):
    """Event fired when code changes are detected."""
    
    def __init__(
        self,
        change_id: str,
        project_id: str,
        branch: str,
        commit_hash: str,
        changed_files: List[str],
        author: str,
        **kwargs
    ):
        super().__init__(change_id, "code_change", **kwargs)
        self.project_id = project_id
        self.branch = branch
        self.commit_hash = commit_hash
        self.changed_files = changed_files
        self.author = author
    
    def get_event_type(self) -> str:
        return "code.changed"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'branch': self.branch,
            'commit_hash': self.commit_hash,
            'changed_files': self.changed_files,
            'author': self.author
        })
        return payload


# Mission Control Workflow Events

class SlackMessageReceivedEvent(DomainEvent):
    """Event fired when a Slack message is received."""
    
    def __init__(
        self,
        message_id: str,
        channel_id: str,
        project_id: str,
        content: str,
        author: str,
        **kwargs
    ):
        super().__init__(message_id, "slack_message", **kwargs)
        self.channel_id = channel_id
        self.project_id = project_id
        self.content = content
        self.author = author
    
    def get_event_type(self) -> str:
        return "slack.message.received"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'channel_id': self.channel_id,
            'project_id': self.project_id,
            'content': self.content,
            'author': self.author
        })
        return payload


class IdeaCapturedEvent(DomainEvent):
    """Event fired when an idea is captured from external sources."""
    
    def __init__(
        self,
        idea_id: str,
        project_id: str,
        content: str,
        source: str,
        tags: List[str] = None,
        severity: Optional[str] = None,
        **kwargs
    ):
        super().__init__(idea_id, "idea", **kwargs)
        self.project_id = project_id
        self.content = content
        self.source = source
        self.tags = tags or []
        self.severity = severity
    
    def get_event_type(self) -> str:
        return "idea.captured"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'content': self.content,
            'source': self.source,
            'tags': self.tags,
            'severity': self.severity
        })
        return payload


class IdeaPromotedEvent(DomainEvent):
    """Event fired when an idea is promoted to Define stage."""
    
    def __init__(
        self,
        idea_id: str,
        project_id: str,
        promoted_by: str,
        **kwargs
    ):
        super().__init__(idea_id, "idea", **kwargs)
        self.project_id = project_id
        self.promoted_by = promoted_by
    
    def get_event_type(self) -> str:
        return "idea.promoted"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'promoted_by': self.promoted_by
        })
        return payload


class SpecDraftedEvent(DomainEvent):
    """Event fired when a specification is drafted via MCP."""
    
    def __init__(
        self,
        spec_id: str,
        project_id: str,
        drafted_by: str,
        artifact_ids: List[str] = None,
        **kwargs
    ):
        super().__init__(spec_id, "spec", **kwargs)
        self.project_id = project_id
        self.drafted_by = drafted_by
        self.artifact_ids = artifact_ids or []
    
    def get_event_type(self) -> str:
        return "spec.drafted"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'drafted_by': self.drafted_by,
            'artifact_ids': self.artifact_ids
        })
        return payload


class SpecFrozenEvent(DomainEvent):
    """Event fired when a specification is frozen/finalized."""
    
    def __init__(
        self,
        spec_id: str,
        project_id: str,
        frozen_by: str,
        **kwargs
    ):
        super().__init__(spec_id, "spec", **kwargs)
        self.project_id = project_id
        self.frozen_by = frozen_by
    
    def get_event_type(self) -> str:
        return "spec.frozen"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'frozen_by': self.frozen_by
        })
        return payload


class TaskStartedEvent(DomainEvent):
    """Event fired when a task is started."""
    
    def __init__(
        self,
        task_id: str,
        project_id: str,
        task_description: str,
        assigned_to: Optional[str] = None,
        **kwargs
    ):
        super().__init__(task_id, "task", **kwargs)
        self.project_id = project_id
        self.task_description = task_description
        self.assigned_to = assigned_to
    
    def get_event_type(self) -> str:
        return "task.started"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'task_description': self.task_description,
            'assigned_to': self.assigned_to
        })
        return payload


class BuildSucceededEvent(DomainEvent):
    """Event fired when a build succeeds."""
    
    def __init__(
        self,
        build_id: str,
        project_id: str,
        pr_url: str,
        commit_hash: str,
        **kwargs
    ):
        super().__init__(build_id, "build", **kwargs)
        self.project_id = project_id
        self.pr_url = pr_url
        self.commit_hash = commit_hash
    
    def get_event_type(self) -> str:
        return "build.succeeded"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'pr_url': self.pr_url,
            'commit_hash': self.commit_hash
        })
        return payload


class QualityAnalyzedEvent(DomainEvent):
    """Event fired when quality analysis is completed."""
    
    def __init__(
        self,
        analysis_id: str,
        project_id: str,
        quality_score: float,
        recommendations: List[str],
        **kwargs
    ):
        super().__init__(analysis_id, "quality_analysis", **kwargs)
        self.project_id = project_id
        self.quality_score = quality_score
        self.recommendations = recommendations
    
    def get_event_type(self) -> str:
        return "quality.analyzed"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'quality_score': self.quality_score,
            'recommendations': self.recommendations
        })
        return payload


class UserFrictionEvent(DomainEvent):
    """Event fired when user friction is detected."""
    
    def __init__(
        self,
        friction_id: str,
        project_id: str,
        friction_points: List[Dict[str, Any]],
        user_persona: str,
        **kwargs
    ):
        super().__init__(friction_id, "user_friction", **kwargs)
        self.project_id = project_id
        self.friction_points = friction_points
        self.user_persona = user_persona
    
    def get_event_type(self) -> str:
        return "user.friction"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'friction_points': self.friction_points,
            'user_persona': self.user_persona
        })
        return payload


class PatternIdentifiedEvent(DomainEvent):
    """Event fired when a pattern is identified for learning."""
    
    def __init__(
        self,
        pattern_id: str,
        project_id: str,
        pattern_type: str,
        insights: List[str],
        **kwargs
    ):
        super().__init__(pattern_id, "pattern", **kwargs)
        self.project_id = project_id
        self.pattern_type = pattern_type
        self.insights = insights
    
    def get_event_type(self) -> str:
        return "pattern.identified"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'pattern_type': self.pattern_type,
            'insights': self.insights
        })
        return payload


# Legacy Spec and Task Events (keeping for backward compatibility)

class IdeaCreatedEvent(DomainEvent):
    """Event fired when a new idea is captured."""
    
    def __init__(
        self,
        idea_id: str,
        project_id: str,
        content: str,
        tags: List[str] = None,
        **kwargs
    ):
        super().__init__(idea_id, "idea", **kwargs)
        self.project_id = project_id
        self.content = content
        self.tags = tags or []
    
    def get_event_type(self) -> str:
        return "idea.created"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'content': self.content,
            'tags': self.tags
        })
        return payload


class TasksCreatedEvent(DomainEvent):
    """Event fired when tasks are created from a spec."""
    
    def __init__(
        self,
        task_list_id: str,
        spec_id: str,
        project_id: str,
        tasks: List[Dict[str, Any]],
        **kwargs
    ):
        super().__init__(task_list_id, "task_list", **kwargs)
        self.spec_id = spec_id
        self.project_id = project_id
        self.tasks = tasks
    
    def get_event_type(self) -> str:
        return "tasks.created"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'spec_id': self.spec_id,
            'project_id': self.project_id,
            'tasks': self.tasks
        })
        return payload


class TaskCompletedEvent(DomainEvent):
    """Event fired when a task is completed."""
    
    def __init__(
        self,
        task_id: str,
        project_id: str,
        completion_time_seconds: float,
        result: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(task_id, "task", **kwargs)
        self.project_id = project_id
        self.completion_time_seconds = completion_time_seconds
        self.result = result or {}
    
    def get_event_type(self) -> str:
        return "task.completed"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'completion_time_seconds': self.completion_time_seconds,
            'result': self.result
        })
        return payload

# PRD and Context Events

class PRDCreatedEvent(DomainEvent):
    """Event fired when a PRD is created."""
    
    def __init__(
        self,
        prd_id: str,
        project_id: str,
        feed_item_id: Optional[str] = None,
        version: str = "v0",
        created_by: Optional[str] = None,
        **kwargs
    ):
        super().__init__(prd_id, "prd", **kwargs)
        self.project_id = project_id
        self.feed_item_id = feed_item_id
        self.version = version
        self.created_by = created_by
    
    def get_event_type(self) -> str:
        return "prd.created"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'feed_item_id': self.feed_item_id,
            'version': self.version,
            'created_by': self.created_by
        })
        return payload


class PRDUpdatedEvent(DomainEvent):
    """Event fired when a PRD is updated."""
    
    def __init__(
        self,
        prd_id: str,
        project_id: str,
        old_version: str,
        new_version: str,
        changes: Dict[str, Any],
        updated_by: Optional[str] = None,
        **kwargs
    ):
        super().__init__(prd_id, "prd", **kwargs)
        self.project_id = project_id
        self.old_version = old_version
        self.new_version = new_version
        self.changes = changes
        self.updated_by = updated_by
    
    def get_event_type(self) -> str:
        return "prd.updated"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'old_version': self.old_version,
            'new_version': self.new_version,
            'changes': self.changes,
            'updated_by': self.updated_by
        })
        return payload


class PRDFrozenEvent(DomainEvent):
    """Event fired when a PRD is frozen."""
    
    def __init__(
        self,
        prd_id: str,
        project_id: str,
        version: str,
        frozen_by: Optional[str] = None,
        **kwargs
    ):
        super().__init__(prd_id, "prd", **kwargs)
        self.project_id = project_id
        self.version = version
        self.frozen_by = frozen_by
    
    def get_event_type(self) -> str:
        return "prd.frozen"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'version': self.version,
            'frozen_by': self.frozen_by
        })
        return payload


class ContextDriftDetectedEvent(DomainEvent):
    """Event fired when drift is detected between PRD and specifications."""
    
    def __init__(
        self,
        spec_id: str,
        project_id: str,
        prd_id: str,
        drift_score: float,
        drift_level: str,
        factors: Dict[str, float],
        **kwargs
    ):
        super().__init__(spec_id, "context", **kwargs)
        self.project_id = project_id
        self.prd_id = prd_id
        self.drift_score = drift_score
        self.drift_level = drift_level
        self.factors = factors
    
    def get_event_type(self) -> str:
        return "context.drift_detected"
    
    def get_version(self) -> str:
        return EventVersion.V1.value
    
    def get_payload(self) -> Dict[str, Any]:
        payload = super().get_payload()
        payload.update({
            'project_id': self.project_id,
            'prd_id': self.prd_id,
            'drift_score': self.drift_score,
            'drift_level': self.drift_level,
            'factors': self.factors
        })
        return payload