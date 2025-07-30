"""PRD (Product Requirements Document) model for storing and versioning PRDs."""

import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from .base import db
from sqlalchemy import inspect

# --- internal utility ------------------------------------------------------

def _ensure_prd_table():
    """Create the `prds` table on-the-fly during unit tests.

    The normal application boot path runs Alembic migrations, but the standalone
    unit-test fixtures use an in-memory SQLite database and call `PRD` helpers
    without running `db.create_all()`.  That caused `OperationalError: no such
    table: prds` in the test suite.  We defensively create the table once on
    first use.
    """
    try:
        # Only try to create table if we're in a test environment (SQLite)
        from flask import current_app
        if current_app and current_app.config.get('TESTING'):
            engine = db.get_engine() if hasattr(db, "get_engine") else db.engine
            if engine is None:
                return
            inspector = inspect(engine)
            if not inspector.has_table("prds"):
                # Only create metadata for this model to keep test DB minimal.
                cls_metadata = PRD.__table__.metadata  # type: ignore  # forward ref OK
                cls_metadata.create_all(bind=engine, tables=[PRD.__table__])
    except Exception:
        # In production, table should exist from migrations
        # If it doesn't, let the database operation fail naturally
        pass


class PRD(db.Model):
    """Model for storing Product Requirements Documents with versioning support."""
    
    __tablename__ = 'prds'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), nullable=False)
    draft_id = db.Column(UUID(as_uuid=True), nullable=False)  # Links to upload_session
    version = db.Column(db.String(10), nullable=False)  # v0, v1, v2, etc.
    md_uri = db.Column(db.Text, nullable=True)  # Full markdown PRD content
    json_uri = db.Column(db.Text, nullable=True)  # Structured JSON summary
    # Use JSON type instead of ARRAY for cross-database compatibility (SQLite tests)
    sources = db.Column(db.JSON, nullable=True)  # List of source file references
    created_by = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, frozen
    
    # Indexes are created in migration
    
    def __repr__(self):
        return f'<PRD {self.id} v{self.version} ({self.status})>'
    
    @classmethod
    def create_draft(cls, project_id: str, draft_id: str, md_content: str = None, 
                    json_summary: Dict = None, sources: List[str] = None, 
                    created_by: str = None) -> 'PRD':
        # Note: In production, table should exist from migrations
        # _ensure_prd_table() only needed for unit tests
        
        # Convert string IDs to UUIDs, handling both UUID and non-UUID formats
        try:
            project_uuid = uuid.UUID(project_id)
        except ValueError:
            # If not a valid UUID, generate one based on the string
            project_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, project_id)
        
        try:
            draft_uuid = uuid.UUID(draft_id)
        except ValueError:
            # If not a valid UUID, generate one based on the string
            draft_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, draft_id)
        
        prd = cls(
            project_id=project_uuid,
            draft_id=draft_uuid,
            version='v0',
            md_uri=md_content,
            json_uri=json.dumps(json_summary) if json_summary else None,
            sources=sources or [],
            created_by=created_by,
            status='draft'
        )
        
        db.session.add(prd)
        db.session.commit()
        return prd
    
    def freeze_version(self, created_by: str = None) -> 'PRD':
        # Note: In production, table should exist from migrations

        if self.status == 'frozen':
            raise ValueError(f"PRD {self.id} is already frozen at version {self.version}")

        # Determine next version number by looking at existing versions for this draft
        existing_versions = PRD.query.filter_by(draft_id=self.draft_id).with_entities(PRD.version).all()
        max_version_num = 0
        for (ver,) in existing_versions:
            if ver and ver.startswith('v') and ver[1:].isdigit():
                max_version_num = max(max_version_num, int(ver[1:]))

        next_version = f'v{max_version_num + 1}'
        
        # Create new frozen version
        frozen_prd = PRD(
            project_id=self.project_id,
            draft_id=self.draft_id,
            version=next_version,
            md_uri=self.md_uri,
            json_uri=self.json_uri,
            sources=self.sources,
            created_by=created_by or self.created_by,
            status='frozen'
        )
        
        db.session.add(frozen_prd)
        db.session.commit()
        return frozen_prd
    
    def get_summary(self) -> Dict[str, Any]:
        """Get structured summary from JSON URI."""
        
        if not self.json_uri:
            return {}
        
        try:
            return json.loads(self.json_uri)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def update_content(self, md_content: str = None, json_summary: Dict = None, 
                      sources: List[str] = None):
        """Update PRD content (only allowed for drafts)."""
        
        if self.status == 'frozen':
            raise ValueError(f"Cannot update frozen PRD {self.id}")
        
        if md_content is not None:
            self.md_uri = md_content
        
        if json_summary is not None:
            self.json_uri = json.dumps(json_summary)
        
        if sources is not None:
            self.sources = sources
        
        db.session.commit()
    
    @classmethod
    def get_latest_for_session(cls, draft_id: str) -> Optional['PRD']:
        """Get the latest PRD version for a given upload session."""
        
        # Convert string ID to UUID, handling both UUID and non-UUID formats
        try:
            draft_uuid = uuid.UUID(draft_id)
        except ValueError:
            # If not a valid UUID, generate one based on the string
            draft_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, draft_id)
        
        return cls.query.filter_by(draft_id=draft_uuid)\
                       .order_by(cls.created_at.desc())\
                       .first()
    
    @classmethod
    def get_by_version(cls, draft_id: str, version: str) -> Optional['PRD']:
        """Get specific PRD version for a given upload session."""
        
        # Convert string ID to UUID, handling both UUID and non-UUID formats
        try:
            draft_uuid = uuid.UUID(draft_id)
        except ValueError:
            # If not a valid UUID, generate one based on the string
            draft_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, draft_id)
        
        return cls.query.filter_by(
            draft_id=draft_uuid,
            version=version
        ).first()
    
    @classmethod
    def get_all_versions(cls, draft_id: str) -> List['PRD']:
        """Get all PRD versions for a given upload session, ordered by version."""
        
        # Convert string ID to UUID, handling both UUID and non-UUID formats
        try:
            draft_uuid = uuid.UUID(draft_id)
        except ValueError:
            # If not a valid UUID, generate one based on the string
            draft_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, draft_id)
        
        return cls.query.filter_by(draft_id=draft_uuid)\
                       .order_by(cls.created_at.asc())\
                       .all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert PRD to dictionary for API responses."""
        
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'draft_id': str(self.draft_id),
            'version': self.version,
            'md_uri': self.md_uri,
            'json_summary': self.get_summary(),
            'sources': self.sources or [],
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status
        }


def extract_prd_summary(ai_response: str, sources: List[str] = None) -> Dict[str, Any]:
    """
    Extract structured PRD summary from AI-generated content.
    
    Parses AI response to create 6-section summary:
    - Problem (1-2 lines)
    - Audience (1 line) 
    - Goals (3 bullets)
    - Risks (1 bullet)
    - Competitive scan (2 bullets)
    - Open questions (3 bullets)
    
    Args:
        ai_response: Full markdown PRD content from AI
        sources: List of source file references for tagging
        
    Returns:
        Dict with structured sections and source attribution
    """
    
    # Default structure
    summary = {
        'problem': {'text': '', 'sources': []},
        'audience': {'text': '', 'sources': []},
        'goals': {'items': [], 'sources': []},
        'risks': {'items': [], 'sources': []},
        'competitive_scan': {'items': [], 'sources': []},
        'open_questions': {'items': [], 'sources': []}
    }
    
    if not ai_response:
        return summary
    
    lines = ai_response.split('\n')
    current_section = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # ----------------------- header detection ---------------------------
        if line.startswith('#'):  # markdown header
            normalized = line.lstrip('#').strip().lower()
            if 'problem' in normalized:
                current_section = 'problem'
            elif 'audience' in normalized or 'target' in normalized:
                current_section = 'audience'
            elif 'goal' in normalized or 'objective' in normalized:
                current_section = 'goals'
            elif 'risk' in normalized or 'concern' in normalized:
                current_section = 'risks'
            elif 'competitive' in normalized or 'competitor' in normalized:
                current_section = 'competitive_scan'
            elif 'question' in normalized:
                current_section = 'open_questions'
            else:
                current_section = None
            continue  # go to next line

        # ----------------------- bullet detection ---------------------------
        if current_section and line.startswith(('- ', '* ', '1. ', '2. ', '3. ')):
            content = line.lstrip('- *123.').strip()

            if current_section == 'problem':
                summary['problem']['text'] += (' ' if summary['problem']['text'] else '') + content
                if sources and not summary['problem']['sources']:
                    summary['problem']['sources'] = [sources[0]]
            elif current_section == 'audience':
                summary['audience']['text'] += (' ' if summary['audience']['text'] else '') + content
                if sources and not summary['audience']['sources']:
                    summary['audience']['sources'] = [sources[0]]
            else:
                # list-based sections
                summary[current_section]['items'].append(content)
                if sources:
                    idx = (len(summary[current_section]['items']) - 1) % len(sources)
                    summary[current_section]['sources'].append(sources[idx])
    
    return summary