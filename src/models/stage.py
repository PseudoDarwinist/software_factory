"""
Stage models for Mission Control SDLC workflow
"""

from datetime import datetime
from sqlalchemy import JSON
from .base import db


class Stage(db.Model):
    """Stage management for SDLC workflow"""
    
    __tablename__ = 'stage'
    
    # Stage types
    STAGE_THINK = 'think'
    STAGE_DEFINE = 'define'
    STAGE_PLAN = 'plan'
    STAGE_BUILD = 'build'
    STAGE_VALIDATE = 'validate'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(100), nullable=False)
    stage_type = db.Column(db.String(50), nullable=False)
    item_ids = db.Column(JSON)  # Array of feed item IDs in this stage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Stage {self.project_id}:{self.stage_type}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'projectId': self.project_id,
            'stageType': self.stage_type,
            'itemIds': self.item_ids or [],
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_or_create_for_project(cls, project_id, stage_type):
        """Get existing stage or create new one"""
        stage = cls.query.filter_by(project_id=project_id, stage_type=stage_type).first()
        if not stage:
            stage = cls(
                project_id=project_id,
                stage_type=stage_type,
                item_ids=[]
            )
            db.session.add(stage)
            db.session.commit()
        return stage
    
    def add_item(self, item_id):
        """Add item to stage"""
        if not self.item_ids:
            self.item_ids = []
        if item_id not in self.item_ids:
            self.item_ids.append(item_id)
            self.updated_at = datetime.utcnow()
            db.session.commit()
    
    def remove_item(self, item_id):
        """Remove item from stage"""
        if self.item_ids and item_id in self.item_ids:
            self.item_ids.remove(item_id)
            self.updated_at = datetime.utcnow()
            db.session.commit()


class StageTransition(db.Model):
    """Track stage transitions for audit trail"""
    
    __tablename__ = 'stage_transition'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.String(100), nullable=False)
    from_stage = db.Column(db.String(50))
    to_stage = db.Column(db.String(50), nullable=False)
    actor = db.Column(db.String(200), default='system')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<StageTransition {self.item_id}: {self.from_stage} -> {self.to_stage}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'itemId': self.item_id,
            'projectId': self.project_id,
            'fromStage': self.from_stage,
            'toStage': self.to_stage,
            'actor': self.actor,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def create(cls, item_id, project_id, from_stage, to_stage, actor='system'):
        """Create a new stage transition record"""
        transition = cls(
            item_id=item_id,
            project_id=project_id,
            from_stage=from_stage,
            to_stage=to_stage,
            actor=actor
        )
        
        db.session.add(transition)
        return transition


class ProductBrief(db.Model):
    """Product brief for Define stage items"""
    
    __tablename__ = 'product_brief'
    
    # Brief status
    STATUS_DRAFT = 'draft'
    STATUS_FROZEN = 'frozen'
    
    id = db.Column(db.String(100), primary_key=True)  # brief-{item_id}
    item_id = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.String(100), nullable=False)
    problem_statement = db.Column(db.Text)
    success_metrics = db.Column(JSON)  # Array of success metrics
    risks = db.Column(JSON)  # Array of risks
    competitive_analysis = db.Column(db.Text)
    user_stories = db.Column(JSON)  # Array of user story objects
    progress = db.Column(db.Float, default=0.0)  # Progress percentage
    status = db.Column(db.String(20), default=STATUS_DRAFT)
    version = db.Column(db.Integer, default=1)
    frozen_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProductBrief {self.id}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'itemId': self.item_id,
            'projectId': self.project_id,
            'problemStatement': self.problem_statement,
            'successMetrics': self.success_metrics or [],
            'risks': self.risks or [],
            'competitiveAnalysis': self.competitive_analysis,
            'userStories': self.user_stories or [],
            'progress': self.progress,
            'status': self.status,
            'version': self.version,
            'frozenAt': self.frozen_at.isoformat() if self.frozen_at else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_for_item(cls, item_id, project_id, brief_data):
        """Create a new product brief for a feed item"""
        brief_id = f"brief-{item_id}"
        brief = cls(
            id=brief_id,
            item_id=item_id,
            project_id=project_id,
            problem_statement=brief_data.get('problemStatement'),
            success_metrics=brief_data.get('successMetrics', []),
            risks=brief_data.get('risks', []),
            competitive_analysis=brief_data.get('competitiveAnalysis'),
            user_stories=brief_data.get('userStories', []),
            progress=brief_data.get('progress', 0.3)
        )
        
        db.session.add(brief)
        return brief
    
    def update_fields(self, updates):
        """Update brief fields"""
        for field, value in updates.items():
            if hasattr(self, field):
                setattr(self, field, value)
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def freeze(self):
        """Freeze the brief"""
        self.status = self.STATUS_FROZEN
        self.frozen_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()