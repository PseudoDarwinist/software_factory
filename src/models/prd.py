"""PRD (Product Requirements Document) model for storing and versioning PRDs."""

import uuid
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)
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
    
    Args:
        ai_response: Full PRD content from AI (markdown or JSON)
        sources: List of source file references for tagging (fallback)
        
    Returns:
        Dict with structured sections and source attribution
    """
    import json
    import re
    
    # Default structure
    default_summary = {
        'problem': {'text': '', 'sources': sources or []},
        'audience': {'text': '', 'sources': sources or []},
        'goals': {'items': [], 'sources': sources or []},
        'risks': {'items': [], 'sources': sources or []},
        'competitive_scan': {'items': [], 'sources': sources or []},
        'open_questions': {'items': [], 'sources': sources or []}
    }
    
    if not ai_response:
        return default_summary
    
    # Try to parse as JSON first
    try:
        # Clean control characters that break JSON parsing
        cleaned_response = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', ai_response.strip())
        
        # Remove markdown code blocks if present
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]
        elif cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]
        
        cleaned_response = cleaned_response.strip()
        
        # Try to parse as JSON
        structured_data = json.loads(cleaned_response)
        
        # If we have the expected structure, use it
        if isinstance(structured_data, dict) and any(key in structured_data for key in ['problem', 'audience', 'goals']):
            summary = default_summary.copy()
            for field in ['problem', 'audience', 'goals', 'risks', 'competitive_scan', 'open_questions']:
                if field in structured_data:
                    summary[field] = structured_data[field]
            return summary
            
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If JSON parsing fails, create a basic summary from the content
    # This ensures we always return something useful
    summary = default_summary.copy()
    
    # Extract basic information from the content
    content_lower = ai_response.lower()
    
    # Try to extract problem statement
    problem_patterns = [
        r'(?:problem|challenge|issue).*?(?:\n\n|\n#|$)',
        r'## problem.*?(?=##|$)',
        r'# problem.*?(?=##|$)'
    ]
    
    for pattern in problem_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if match:
            problem_text = match.group(0).strip()
            # Clean up the text
            problem_text = re.sub(r'^#+\s*', '', problem_text)
            problem_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', problem_text)
            if len(problem_text) > 20:
                summary['problem']['text'] = problem_text[:200] + '...' if len(problem_text) > 200 else problem_text
                break
    
    # Extract goals/objectives
    goals_patterns = [
        r'(?:goals?|objectives?).*?(?:\n\n|\n#|$)',
        r'## (?:goals?|objectives?).*?(?=##|$)',
        r'# (?:goals?|objectives?).*?(?=##|$)'
    ]
    
    for pattern in goals_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if match:
            goals_text = match.group(0)
            # Extract bullet points or numbered items
            goals = re.findall(r'[-*]\s*([^\n]+)', goals_text)
            if not goals:
                goals = re.findall(r'\d+\.\s*([^\n]+)', goals_text)
            if goals:
                summary['goals']['items'] = goals[:3]  # Take first 3
                break
    
    return summary


def _parse_ai_json(ai_response: str) -> Dict[str, Any]:
    """Parse AI response into JSON dict, handling common wrappers and noise.

    Strategy:
    - Strip BOM/zero-width/control chars
    - Try direct json.loads
    - Extract fenced code blocks and try each
    - Extract first balanced JSON object and try it
    Raises ValueError if nothing can be parsed.
    """
    if not ai_response:
        raise ValueError("Empty AI response")

    raw = _strip_control_and_bom(ai_response.strip())

    # 1) Try direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 2) Try fenced/brace candidates
    for candidate in _find_json_blocks(raw):
        cleaned = _strip_control_and_bom(candidate.strip())
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Some providers return JSONC; remove // and /* */ comments then retry
            no_line_comments = re.sub(r"(^|\s)//.*", "", cleaned)
            no_block_comments = re.sub(r"/\*[^*]*\*+(?:[^/*][^*]*\*+)*/", "", no_line_comments, flags=re.S)
            # Remove trailing commas in objects/arrays (best-effort)
            no_trailing_commas = re.sub(r",\s*(\}|\])", r"\1", no_block_comments)
            try:
                return json.loads(no_trailing_commas)
            except Exception:
                continue

    raise ValueError("Could not parse JSON from AI response")


def _strip_control_and_bom(text: str) -> str:
    """Remove control chars, BOM and zero-width spaces that break JSON parsing."""
    if text is None:
        return ''
    # Remove UTF-8/UTF-16 BOM and common zero-width chars
    try:
        text = text.replace('\ufeff', '').replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
    except Exception:
        pass
    # Remove ASCII control characters except \t, \n, \r
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return text


def _find_json_blocks(text: str) -> List[str]:
    """Find candidate JSON blocks within a string.

    - Extract content from fenced code blocks ```/~~~ … (json/jsonc supported)
    - Also attempt to extract the first balanced JSON object
    - Heuristic: extract object that contains "full_prd"
    """
    if not text:
        return []

    candidates: List[str] = []
    s = text

    # 1) Look for fenced code blocks first (prefer those labeled json)
    fence_pattern = re.compile(r"(```|~~~)\s*([a-zA-Z0-9_\-]*)\s*\n([\s\S]*?)\1", re.MULTILINE)
    for m in fence_pattern.finditer(s):
        lang = (m.group(2) or '').lower()
        body = m.group(3).strip()
        if not body:
            continue
        if lang in ('json', 'jsonc', 'json5', 'application/json'):
            candidates.insert(0, body)
        else:
            candidates.append(body)

    # 2) Brace-balanced extraction for first object
    if not candidates:
        start = None
        depth = 0
        in_str = False
        esc = False
        for i, ch in enumerate(s):
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start is not None:
                        block = s[start:i+1].strip()
                        if block:
                            candidates.append(block)
                        break

        if not candidates:
            loose = re.search(r"\{[\s\S]*\}", s)
            if loose:
                candidates.append(loose.group(0).strip())

    # 3) Heuristic: extract JSON object that contains a target key like "full_prd"
    if '"full_prd"' in s and not any('"full_prd"' in c for c in candidates):
        idx = s.find('"full_prd"')
        # Find nearest preceding '{' and walk to matching '}'
        start = None
        for i in range(idx, -1, -1):
            if s[i] == '{':
                start = i
                break
        if start is not None:
            depth = 0
            in_str = False
            esc = False
            for j in range(start, len(s)):
                ch = s[j]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == '\\':
                        esc = True
                    elif ch == '"':
                        in_str = False
                else:
                    if ch == '"':
                        in_str = True
                    elif ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            block = s[start:j+1].strip()
                            if block:
                                candidates.insert(0, block)
                            break

    if not candidates:
        logger.warning("PRD JSON parse: no candidate blocks found")

    return candidates


def extract_summary_from_markdown(md: str, sources: List[str] = None) -> Dict[str, Any]:
    """Heuristic summary extraction from markdown when JSON isn't provided.

    Looks for common headings and bullets to populate the six UI fields.
    """
    base = lambda: {
        'problem': {'text': '', 'sources': sources or []},
        'audience': {'text': '', 'sources': sources or []},
        'goals': {'items': [], 'sources': sources or []},
        'risks': {'items': [], 'sources': sources or []},
        'competitive_scan': {'items': [], 'sources': sources or []},
        'open_questions': {'items': [], 'sources': sources or []},
    }
    if not md:
        return base()

    def section_text(title_variants: List[str]) -> str:
        patt = re.compile(r"^(#{1,6}|\*\*|__)\s*(%s)\b.*$" % ("|".join(map(re.escape, title_variants))), re.IGNORECASE | re.MULTILINE)
        m = patt.search(md)
        if not m:
            # Try plain line starts without markdown markers
            patt2 = re.compile(r"^(%s)\b.*$" % ("|".join(map(re.escape, title_variants))), re.IGNORECASE | re.MULTILINE)
            m = patt2.search(md)
        if not m:
            return ''
        start = m.end()
        # Capture until next heading or end
        next_heading = re.search(r"^#{1,6}\s|^\*\*|^__|^\w+\s*:\s*$", md[start:], re.MULTILINE)
        end = start + (next_heading.start() if next_heading else len(md) - start)
        return md[start:end].strip()

    def list_items_from(text: str, limit: int = 10) -> List[str]:
        if not text:
            return []
        items = []
        for line in text.splitlines():
            line = line.strip()
            m = re.match(r"^[-*+•]\s+(.*)$", line)
            if m:
                items.append(m.group(1).strip())
                continue
            m2 = re.match(r"^\d+[\.)\s]+(.*)$", line)
            if m2:
                items.append(m2.group(1).strip())
            if len(items) >= limit:
                break
        # If no bullets, split paragraphs/sentences
        if not items and text:
            parts = re.split(r"\n\n+|\.\s+", text)
            items = [p.strip() for p in parts if p.strip()][:limit]
        return items

    problem_text = section_text(["Problem", "Problem Statement"])[:600]
    audience_text = section_text(["Audience", "Target Audience", "User Personas"])[:600]
    goals_text = section_text(["Goals", "Objectives", "Key Goals"])[:2000]
    risks_text = section_text(["Risks", "Risk Analysis"])[:2000]
    comp_text = section_text(["Competitive Scan", "Competitive Analysis", "Competition"])[:2000]
    q_text = section_text(["Open Questions", "Questions", "Unknowns"])[:2000]

    summary = base()
    summary['problem']['text'] = problem_text.strip()
    summary['audience']['text'] = audience_text.strip()
    summary['goals']['items'] = list_items_from(goals_text)
    summary['risks']['items'] = list_items_from(risks_text)
    summary['competitive_scan']['items'] = list_items_from(comp_text)
    summary['open_questions']['items'] = list_items_from(q_text)
    return summary


def extract_prd_summary(ai_response: str, sources: List[str] = None) -> Dict[str, Any]:
    """
    Extract structured PRD summary from AI JSON response.
    
    Args:
        ai_response: JSON response from AI containing PRD structure
        sources: List of source file references for tagging
        
    Returns:
        Dict with structured sections and source attribution
    """
    import json
    import re
    
    if not ai_response:
        raise ValueError("Empty AI response")
    
    try:
        structured_data = _parse_ai_json(ai_response)
        
        # Extract and validate required fields
        summary = {}
        for field in ['problem', 'audience', 'goals', 'risks', 'competitive_scan', 'open_questions']:
            if field in structured_data:
                summary[field] = structured_data[field]
            else:
                # Provide default structure for missing fields
                if field in ['problem', 'audience']:
                    summary[field] = {'text': '', 'sources': sources or []}
                else:
                    summary[field] = {'items': [], 'sources': sources or []}
        
        return summary
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from AI: {e}")
    except Exception as e:
        raise ValueError(f"Failed to extract PRD summary: {e}")



