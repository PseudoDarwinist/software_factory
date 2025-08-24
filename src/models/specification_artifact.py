"""
Specification Artifact model for storing AI-generated and human-reviewed specifications
"""

from datetime import datetime
from enum import Enum
from .base import db


# Helper mixin to get .value even when column stores Enum names
def enum_value(enum_member):
    return enum_member.value if hasattr(enum_member, 'value') else str(enum_member)


class ArtifactType(Enum):
    """Types of specification artifacts"""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    TASKS = "tasks"


class ArtifactStatus(Enum):
    """Status of specification artifacts for AI-draft vs Human-reviewed tracking"""
    AI_DRAFT = "ai_draft"
    HUMAN_REVIEWED = "human_reviewed"
    FROZEN = "frozen"


class SpecificationArtifact(db.Model):
    """
    Model for storing specification artifacts with AI-draft vs Human-reviewed tracking
    Supports the Define Agent's badge tracking system
    """
    
    __tablename__ = 'specification_artifact'
    
    id = db.Column(db.String(100), primary_key=True)  # spec_id + artifact_type (increased length)
    spec_id = db.Column(db.String(100), nullable=False, index=True)
    project_id = db.Column(db.String(100), nullable=False, index=True)
    artifact_type = db.Column(db.Enum(ArtifactType), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(ArtifactStatus), default=ArtifactStatus.AI_DRAFT, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    
    # Tracking fields
    created_by = db.Column(db.String(100))  # agent_id or user_id
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # AI generation metadata
    ai_generated = db.Column(db.Boolean, default=False, nullable=False)
    ai_model_used = db.Column(db.String(100))
    context_sources = db.Column(db.JSON)  # List of context sources used
    
    # Human review metadata
    reviewed_by = db.Column(db.String(100))
    reviewed_at = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    
    # Notion sync metadata
    notion_page_id = db.Column(db.String(100))
    notion_synced_at = db.Column(db.DateTime)
    notion_sync_status = db.Column(db.String(50))
    
    # Note: No direct relationship since we use Mission Control project IDs (strings)
    # which don't have a direct foreign key relationship
    
    # Composite unique constraint
    __table_args__ = (
        db.UniqueConstraint('spec_id', 'artifact_type', name='uq_spec_artifact'),
        db.Index('idx_project_spec', 'project_id', 'spec_id'),
        db.Index('idx_status_type', 'status', 'artifact_type'),
    )
    
    def __repr__(self):
        return f'<SpecificationArtifact {self.spec_id}:{self.artifact_type.value}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'spec_id': self.spec_id,
            'project_id': self.project_id,
            'artifact_type': enum_value(self.artifact_type),
            'content': self.content,
            'status': enum_value(self.status),
            'version': self.version,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'ai_generated': self.ai_generated,
            'ai_model_used': self.ai_model_used,
            'context_sources': self.context_sources,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_notes': self.review_notes,
            'notion_page_id': self.notion_page_id,
            'notion_synced_at': self.notion_synced_at.isoformat() if self.notion_synced_at else None,
            'notion_sync_status': self.notion_sync_status
        }
    
    @classmethod
    def create_artifact(cls, spec_id: str, project_id, artifact_type: ArtifactType,
                       content: str, created_by: str, ai_generated: bool = False,
                       ai_model_used: str = None, context_sources: list = None):
        """Create a new specification artifact"""
        artifact_id = f"{spec_id}_{artifact_type.value}"
        
        artifact = cls(
            id=artifact_id,
            spec_id=spec_id,
            project_id=str(project_id),
            artifact_type=artifact_type,
            content=content,
            created_by=created_by,
            ai_generated=ai_generated,
            ai_model_used=ai_model_used,
            context_sources=context_sources or []
        )
        
        db.session.add(artifact)
        return artifact
    
    @classmethod
    def get_spec_artifacts(cls, spec_id: str, project_id: str = None):
        """Get all artifacts for a specification, optionally filtered by project"""
        query = cls.query.filter_by(spec_id=spec_id)
        if project_id:
            query = query.filter_by(project_id=project_id)
        return query.all()
    
    @classmethod
    def get_project_specs(cls, project_id):
        """Get all specification artifacts for a project grouped by spec_id"""
        artifacts = cls.query.filter_by(project_id=str(project_id)).order_by(
            cls.spec_id, cls.artifact_type
        ).all()
        
        # Group by spec_id
        specs = {}
        for artifact in artifacts:
            if artifact.spec_id not in specs:
                specs[artifact.spec_id] = {}
            specs[artifact.spec_id][artifact.artifact_type.value] = artifact
        
        return specs
    
    def mark_human_reviewed(self, reviewed_by: str, review_notes: str = None):
        """Mark artifact as human reviewed"""
        self.status = ArtifactStatus.HUMAN_REVIEWED
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.utcnow()
        self.review_notes = review_notes
        self.updated_by = reviewed_by
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def freeze_artifact(self, frozen_by: str):
        """Freeze the artifact (final state)"""
        self.status = ArtifactStatus.FROZEN
        self.updated_by = frozen_by
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def update_content(self, new_content: str, updated_by: str, increment_version: bool = True):
        """Update artifact content"""
        self.content = new_content
        self.updated_by = updated_by
        self.updated_at = datetime.utcnow()
        
        if increment_version:
            self.version += 1
        
        # Reset review status if content changes after review
        if self.status == ArtifactStatus.HUMAN_REVIEWED:
            self.status = ArtifactStatus.AI_DRAFT
            self.reviewed_by = None
            self.reviewed_at = None
            self.review_notes = None
        
        db.session.commit()
    
    def sync_to_notion(self, notion_page_id: str, sync_status: str = "synced"):
        """Update Notion sync metadata"""
        self.notion_page_id = notion_page_id
        self.notion_synced_at = datetime.utcnow()
        self.notion_sync_status = sync_status
        db.session.commit()
    
    def get_badge_info(self):
        """Get badge information for UI display"""
        if self.status == ArtifactStatus.AI_DRAFT:
            return {
                'status': 'ai_draft',
                'color': 'yellow',
                'icon': '🟡',
                'text': 'AI Draft',
                'description': f'Generated by {self.ai_model_used or "AI"}'
            }
        elif self.status == ArtifactStatus.HUMAN_REVIEWED:
            return {
                'status': 'human_reviewed',
                'color': 'green',
                'icon': '🟢',
                'text': 'Human Reviewed',
                'description': f'Reviewed by {self.reviewed_by}'
            }
        elif self.status == ArtifactStatus.FROZEN:
            return {
                'status': 'frozen',
                'color': 'blue',
                'icon': '🔒',
                'text': 'Frozen',
                'description': 'Specification locked'
            }
        else:
            return {
                'status': 'unknown',
                'color': 'gray',
                'icon': '❓',
                'text': 'Unknown',
                'description': 'Unknown status'
            }
    
    @classmethod
    def get_spec_completion_status(cls, spec_id: str, project_id: str = None):
        """Get completion status for a specification"""
        artifacts = cls.get_spec_artifacts(spec_id, project_id)
        
        if not artifacts:
            return {
                'complete': False,
                'total_artifacts': 0,
                'ai_draft': 0,
                'human_reviewed': 0,
                'frozen': 0,
                'ready_to_freeze': False
            }
        
        status_counts = {
            'ai_draft': 0,
            'human_reviewed': 0,
            'frozen': 0
        }
        
        for artifact in artifacts:
            status_counts[artifact.status.value] += 1
        
        total = len(artifacts)
        expected_artifacts = 3  # requirements, design, tasks
        
        return {
            'complete': total == expected_artifacts,
            'total_artifacts': total,
            'ai_draft': status_counts['ai_draft'],
            'human_reviewed': status_counts['human_reviewed'],
            'frozen': status_counts['frozen'],
            'ready_to_freeze': (
                total == expected_artifacts and 
                status_counts['ai_draft'] == 0 and 
                status_counts['frozen'] == 0
            )
        }