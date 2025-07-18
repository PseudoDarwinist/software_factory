"""
Conversation model
"""

from datetime import datetime
from sqlalchemy import JSON
from .base import db


class Conversation(db.Model):
    """Conversation model for storing AI chat interactions"""
    
    __tablename__ = 'conversation'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    title = db.Column(db.String(200))
    messages = db.Column(JSON)
    ai_model = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Conversation {self.id}: {self.title or "Untitled"}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'title': self.title,
            'messages': self.messages or [],
            'ai_model': self.ai_model,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'message_count': len(self.messages) if self.messages else 0
        }
    
    @classmethod
    def create_for_project(cls, project_id, title=None, ai_model=None):
        """Create a new conversation for a project"""
        conversation = cls(
            project_id=project_id,
            title=title,
            ai_model=ai_model,
            messages=[]
        )
        
        db.session.add(conversation)
        return conversation
    
    def add_message(self, role, content, metadata=None):
        """Add a message to the conversation"""
        if not self.messages:
            self.messages = []
        
        message = {
            'role': role,  # 'user', 'assistant', 'system'
            'content': content,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_message_count(self):
        """Get total number of messages in conversation"""
        return len(self.messages) if self.messages else 0
    
    def get_last_message(self):
        """Get the most recent message"""
        if not self.messages:
            return None
        return self.messages[-1]
    
    def clear_messages(self):
        """Clear all messages from conversation"""
        self.messages = []
        self.updated_at = datetime.utcnow()
        db.session.commit()