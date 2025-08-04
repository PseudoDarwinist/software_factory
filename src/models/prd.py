"""PRD (Product Requirements Document) model for storing and versioning PRDs."""

import uuid
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import String, TypeDecorator, Text
from .base import db
from sqlalchemy import inspect

# --- internal utility ------------------------------------------------------

class StringArrayType(TypeDecorator):
    """A type that stores string arrays as JSON in SQLite and as ARRAY in PostgreSQL."""
    
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(String))
        else:
            return dialect.type_descriptor(Text)
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value  # PostgreSQL handles arrays natively
        else:
            return json.dumps(value)  # Store as JSON string in other databases
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value  # PostgreSQL returns arrays natively
        else:
            try:
                return json.loads(value)  # Parse JSON string in other databases
            except (json.JSONDecodeError, TypeError):
                return []



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
    """Model for storing Product Requirements Documents with versioning support.
    
    Each PRD is now linked to a specific FeedItem (idea) for 1:1 relationship.
    This enables idea-specific business context for spec generation.
    """
    
    __tablename__ = 'prds'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(UUID(as_uuid=True), nullable=False)
    draft_id = db.Column(UUID(as_uuid=True), nullable=False)  # Links to upload_session
    feed_item_id = db.Column(UUID(as_uuid=True), nullable=True)  # NEW: Links to specific idea
    version = db.Column(db.String(10), nullable=False)  # v0, v1, v2, etc.
    parent_version_id = db.Column(UUID(as_uuid=True), nullable=True)  # NEW: For version history
    md_uri = db.Column(db.Text, nullable=True)  # Full markdown PRD content
    json_uri = db.Column(db.Text, nullable=True)  # Structured JSON summary
    # Use custom type that handles PostgreSQL ARRAY and SQLite JSON
    sources = db.Column(StringArrayType, nullable=True)  # List of source file references
    source_files = db.Column(db.JSON, nullable=True)  # NEW: Detailed file metadata
    created_by = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, frozen
    
    # Indexes are created in migration
    
    def __repr__(self):
        return f'<PRD {self.id} v{self.version} ({self.status})>'
    
    @classmethod
    def create_draft(cls, project_id: str, draft_id: str, md_content: str = None, 
                    json_summary: Dict = None, sources: List[str] = None, 
                    created_by: str = None, feed_item_id: str = None, 
                    source_files: List[Dict] = None) -> 'PRD':
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
        
        # Convert feed_item_id if provided
        feed_item_uuid = None
        if feed_item_id:
            try:
                feed_item_uuid = uuid.UUID(feed_item_id)
            except ValueError:
                feed_item_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, feed_item_id)
        
        # Determine the next version number based on existing PRDs for this session
        existing_versions = cls.query.filter_by(draft_id=draft_uuid).with_entities(cls.version).all()
        max_version_num = -1  # Start at -1 so first version is v0
        
        for (ver,) in existing_versions:
            if ver and ver.startswith('v') and ver[1:].isdigit():
                version_num = int(ver[1:])
                max_version_num = max(max_version_num, version_num)
        
        next_version = f'v{max_version_num + 1}'
        print(f"🆕 DEBUG: Creating new draft PRD for session {draft_id} with version {next_version}")
        
        # Check if there's already a draft with this version (shouldn't happen, but safety check)
        existing_draft = cls.query.filter_by(
            draft_id=draft_uuid,
            version=next_version,
            status='draft'
        ).first()
        
        if existing_draft:
            # Update existing draft content
            print(f"🔄 DEBUG: Updating existing draft PRD {existing_draft.id} version {next_version}")
            existing_draft.md_uri = md_content
            existing_draft.json_uri = json.dumps(json_summary) if json_summary else None
            existing_draft.sources = sources or []
            existing_draft.created_by = created_by or existing_draft.created_by
            db.session.commit()
            return existing_draft
        
        # Create new draft PRD with the next version
        prd = cls(
            project_id=project_uuid,
            draft_id=draft_uuid,
            feed_item_id=feed_item_uuid,
            version=next_version,
            md_uri=md_content,
            json_uri=json.dumps(json_summary) if json_summary else None,
            sources=sources or [],
            source_files=source_files or [],
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

        # Simply freeze this PRD in place - change status from draft to frozen
        self.status = 'frozen'
        self.created_by = created_by or self.created_by
        
        db.session.commit()
        
        print(f"✅ DEBUG: Frozen PRD {self.id} at version {self.version}")
        return self
    
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
    def get_draft_for_session(cls, draft_id: str) -> Optional['PRD']:
        """Get the current draft PRD for a given upload session."""
        
        # Convert string ID to UUID, handling both UUID and non-UUID formats
        try:
            draft_uuid = uuid.UUID(draft_id)
        except ValueError:
            # If not a valid UUID, generate one based on the string
            draft_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, draft_id)
        
        return cls.query.filter_by(
            draft_id=draft_uuid,
            status='draft'
        ).first()
    
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
    
    @classmethod
    def get_for_feed_item(cls, feed_item_id: str) -> Optional['PRD']:
        """Get the current PRD for a specific FeedItem (idea)."""
        
        # Convert string ID to UUID
        try:
            feed_item_uuid = uuid.UUID(feed_item_id)
        except ValueError:
            feed_item_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, feed_item_id)
        
        return cls.query.filter_by(feed_item_id=feed_item_uuid)\
                       .order_by(cls.created_at.desc())\
                       .first()
    
    @classmethod
    def get_frozen_for_feed_item(cls, feed_item_id: str) -> Optional['PRD']:
        """Get the latest frozen PRD for a specific FeedItem."""
        
        # Convert string ID to UUID
        try:
            feed_item_uuid = uuid.UUID(feed_item_id)
        except ValueError:
            feed_item_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, feed_item_id)
        
        return cls.query.filter_by(
            feed_item_id=feed_item_uuid,
            status='frozen'
        ).order_by(cls.created_at.desc()).first()
    
    @classmethod
    def get_all_for_feed_item(cls, feed_item_id: str) -> List['PRD']:
        """Get all PRD versions for a specific FeedItem, ordered by creation date."""
        
        # Convert string ID to UUID
        try:
            feed_item_uuid = uuid.UUID(feed_item_id)
        except ValueError:
            feed_item_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, feed_item_id)
        
        return cls.query.filter_by(feed_item_id=feed_item_uuid)\
                       .order_by(cls.created_at.desc())\
                       .all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert PRD to dictionary for API responses."""
        
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'draft_id': str(self.draft_id),
            'feed_item_id': str(self.feed_item_id) if self.feed_item_id else None,
            'version': self.version,
            'parent_version_id': str(self.parent_version_id) if self.parent_version_id else None,
            'md_uri': self.md_uri,
            'json_summary': self.get_summary(),
            'sources': self.sources or [],
            'source_files': self.source_files or [],
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status
        }


def extract_prd_summary(ai_response: str, sources: List[str] = None) -> Dict[str, Any]:
    """
    Extract structured PRD summary from AI-generated content.
    
    New approach: Parse structured JSON from AI response for reliable extraction.
    Falls back to markdown parsing if JSON is not found.
    
    Args:
        ai_response: Full PRD content from AI (markdown + JSON)
        sources: List of source file references for tagging (fallback)
        
    Returns:
        Dict with structured sections and source attribution
    """
    import json
    import re
    
    # Default structure
    default_summary = {
        'problem': {'text': '', 'sources': []},
        'audience': {'text': '', 'sources': []},
        'goals': {'items': [], 'sources': []},
        'risks': {'items': [], 'sources': []},
        'competitive_scan': {'items': [], 'sources': []},
        'open_questions': {'items': [], 'sources': []}
    }
    
    if not ai_response:
        return default_summary
    
    # Try to extract structured JSON from AI response
    try:
        # Clean the response to extract JSON
        cleaned_response = ai_response.strip()
        
        # Remove markdown code blocks if present
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]  # Remove ```json
        if cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]   # Remove ```
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]  # Remove trailing ```
        
        cleaned_response = cleaned_response.strip()
        
        # Try to parse the cleaned response as JSON
        try:
            structured_data = json.loads(cleaned_response)
            
            # Extract the structured summary from the JSON
            if 'problem' in structured_data and 'audience' in structured_data:
                structured_summary = {
                    'problem': structured_data.get('problem', {}),
                    'audience': structured_data.get('audience', {}),
                    'goals': structured_data.get('goals', {}),
                    'risks': structured_data.get('risks', {}),
                    'competitive_scan': structured_data.get('competitive_scan', {}),
                    'open_questions': structured_data.get('open_questions', {})
                }
                
                # Validate and clean the structured summary
                validated_summary = default_summary.copy()
                
                for section in ['problem', 'audience', 'goals', 'risks', 'competitive_scan', 'open_questions']:
                    if section in structured_summary:
                        section_data = structured_summary[section]
                        
                        if section in ['problem', 'audience']:
                            # Text-based sections
                            if 'text' in section_data:
                                validated_summary[section]['text'] = str(section_data['text'])
                            if 'sources' in section_data and isinstance(section_data['sources'], list):
                                validated_summary[section]['sources'] = section_data['sources']
                        else:
                            # List-based sections
                            if 'items' in section_data and isinstance(section_data['items'], list):
                                validated_summary[section]['items'] = section_data['items']
                            if 'sources' in section_data and isinstance(section_data['sources'], list):
                                validated_summary[section]['sources'] = section_data['sources']
                
                return validated_summary
            else:
                raise ValueError("JSON missing required sections")
                
        except (json.JSONDecodeError, ValueError) as parse_error:
            # Try to extract JSON from within the response using regex
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    structured_data = json.loads(json_str)
                    
                    # Process the extracted JSON (same logic as above)
                    if 'problem' in structured_data and 'audience' in structured_data:
                        # Same validation logic as above
                        validated_summary = default_summary.copy()
                        
                        for section in ['problem', 'audience', 'goals', 'risks', 'competitive_scan', 'open_questions']:
                            if section in structured_data:
                                section_data = structured_data[section]
                                
                                if section in ['problem', 'audience']:
                                    if 'text' in section_data:
                                        validated_summary[section]['text'] = str(section_data['text'])
                                    if 'sources' in section_data and isinstance(section_data['sources'], list):
                                        validated_summary[section]['sources'] = section_data['sources']
                                else:
                                    if 'items' in section_data and isinstance(section_data['items'], list):
                                        validated_summary[section]['items'] = section_data['items']
                                    if 'sources' in section_data and isinstance(section_data['sources'], list):
                                        validated_summary[section]['sources'] = section_data['sources']
                        
                        return validated_summary
                        
                except json.JSONDecodeError:
                    pass
            
            # Fallback to delimiter format
            if '---STRUCTURED_SUMMARY---' in ai_response:
                json_part = ai_response.split('---STRUCTURED_SUMMARY---')[1].strip()
                
                # Extract JSON from the response
                json_match = re.search(r'\{.*\}', json_part, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    structured_summary = json.loads(json_str)
                else:
                    raise ValueError("No JSON found after delimiter")
            else:
                raise ValueError("No delimiter found")
                
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        # Log the error but don't print debug info
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to parse structured JSON, falling back to markdown parsing: {e}")
    
    # Fallback to original markdown parsing
    return _parse_markdown_summary(ai_response, sources, default_summary)


def _parse_markdown_summary(ai_response: str, sources: List[str], default_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced markdown parsing for comprehensive PRD summary extraction.
    """
    summary = default_summary.copy()
    
    # Extract Problem Statement
    problem_match = re.search(r'(?:problem statement|core problems).*?(?=##|\Z)', ai_response, re.IGNORECASE | re.DOTALL)
    if problem_match:
        problem_text = problem_match.group(0)
        # Extract key problem points
        problems = re.findall(r'[-*]\s*([^-*\n]+)', problem_text)
        if problems:
            summary['problem']['text'] = '. '.join(problems[:2])  # Take first 2 problems
            summary['problem']['sources'] = ['S1']
    
    # Extract Target Audience
    audience_match = re.search(r'(?:target audience|user personas?).*?(?=##|\Z)', ai_response, re.IGNORECASE | re.DOTALL)
    if audience_match:
        audience_text = audience_match.group(0)
        # Look for Primary/Secondary structure
        primary_match = re.search(r'\*\*primary:?\*\*\s*([^*\n]+)', audience_text, re.IGNORECASE)
        secondary_match = re.search(r'\*\*secondary:?\*\*\s*([^*\n]+)', audience_text, re.IGNORECASE)
        
        audience_parts = []
        if primary_match:
            audience_parts.append(f"Primary: {primary_match.group(1).strip()}")
        if secondary_match:
            audience_parts.append(f"Secondary: {secondary_match.group(1).strip()}")
        
        if audience_parts:
            summary['audience']['text'] = '. '.join(audience_parts)
            summary['audience']['sources'] = ['S1']
    
    # Extract Goals from Value Proposition or Business Objectives
    goals_match = re.search(r'(?:value proposition|business objectives|goals).*?(?=##|\Z)', ai_response, re.IGNORECASE | re.DOTALL)
    if goals_match:
        goals_text = goals_match.group(0)
        # Extract bullet points or numbered goals
        goals = re.findall(r'[-*]\s*([^-*\n]+)', goals_text)
        if not goals:
            # Try numbered format
            goals = re.findall(r'\d+\.\s*\*\*([^*]+)\*\*', goals_text)
        
        if goals:
            summary['goals']['items'] = goals[:3]  # Take first 3 goals
            summary['goals']['sources'] = ['S1'] * len(summary['goals']['items'])
    
    # Extract Risks from Problem Statement or dedicated Risk section
    risks_match = re.search(r'(?:risks?|challenges?|concerns?).*?(?=##|\Z)', ai_response, re.IGNORECASE | re.DOTALL)
    if risks_match:
        risks_text = risks_match.group(0)
        risks = re.findall(r'[-*]\s*([^-*\n]+)', risks_text)
        if risks:
            summary['risks']['items'] = risks[:2]  # Take first 2 risks
            summary['risks']['sources'] = ['S1'] * len(summary['risks']['items'])
    
    # Extract Competitive Analysis from Key Differentiators or Solution Overview
    comp_match = re.search(r'(?:key differentiators?|competitive|solution overview).*?(?=##|\Z)', ai_response, re.IGNORECASE | re.DOTALL)
    if comp_match:
        comp_text = comp_match.group(0)
        competitors = re.findall(r'[-*]\s*([^-*\n]+)', comp_text)
        if competitors:
            summary['competitive_scan']['items'] = competitors[:2]  # Take first 2 differentiators
            summary['competitive_scan']['sources'] = ['S1'] * len(summary['competitive_scan']['items'])
    
    # Extract Open Questions from Requirements or implied gaps
    questions_match = re.search(r'(?:requirements?|user stories).*?(?=##|\Z)', ai_response, re.IGNORECASE | re.DOTALL)
    if questions_match:
        questions_text = questions_match.group(0)
        # Look for question patterns or requirements that imply questions
        questions = []
        
        # Add some intelligent questions based on the content
        if 'enterprise security' in ai_response.lower():
            questions.append("What specific enterprise security requirements must be met?")
        if 'ai' in ai_response.lower():
            questions.append("How will the AI algorithms be trained and validated?")
        if 'mobile' in ai_response.lower():
            questions.append("What is the optimal mobile-first user experience design?")
        
        if questions:
            summary['open_questions']['items'] = questions[:3]
            summary['open_questions']['sources'] = ['S1'] * len(summary['open_questions']['items'])
    
    print(f"⚠️ Used enhanced markdown parsing")
    print(f"🔍 DEBUG: Enhanced parsing results:")
    for section, data in summary.items():
        if section in ['problem', 'audience']:
            has_content = bool(data.get('text', '').strip())
        else:
            has_content = bool(data.get('items', []))
        print(f"  - {section}: {'✅' if has_content else '❌'}")
    
    return summary